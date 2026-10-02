import { readFileSync } from "node:fs";
import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { createSdkMcpServer, query, tool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
import { record } from "./audit.js";
import type { RunBudget } from "./budget.js";
import { config, roleConfig } from "./config.js";
import {
  computeAgentTypeId,
  mintInstallationToken,
  newInstanceId,
  sha256,
  SUBAGENT_PERMISSIONS,
  type RunContext,
} from "./identity.js";
import { buildMcpServers } from "./mcp/servers.js";
import { makeCanUseTool } from "./permissions.js";
import { shellTools } from "./tools/shell.js";

const s3 = new S3Client({});
const prompts = readFileSync("prompts/subagents.md", "utf8").split(/^## /m);

function rolePrompt(role: string): string {
  const section = prompts.find((p) => p.startsWith(role));
  if (!section) throw new Error(`no prompt for ${role}`);
  return section;
}

async function storeParentPrompt(child: RunContext, prompt: string): Promise<string> {
  const key = `parent-prompts/${child.parentInstanceId}/${child.agentInstanceId}.txt`;
  await s3.send(
    new PutObjectCommand({
      Bucket: config.promptBucket,
      Key: key,
      Body: prompt,
      ServerSideEncryption: "aws:kms",
      SSEKMSKeyId: process.env.PROMPT_KMS_KEY_ID,
    }),
  );
  return key;
}

export function delegateTool(parent: RunContext, workspace: string, budget: RunBudget) {
  return tool(
    "delegate",
    "Ask a sub-agent for help. `reviewer` reviews the current diff; `test_writer` adds or fixes tests.",
    { role: z.enum(["reviewer", "test_writer"]), prompt: z.string().min(1).max(8000) },
    async ({ role, prompt }) => {
      budget.onSubagent();
      const childBudget = budget.child();
      const child: RunContext = {
        ...parent,
        agentTypeId: computeAgentTypeId(role),
        agentInstanceId: newInstanceId(),
        parentInstanceId: parent.agentInstanceId,
      };
      const promptKey = await storeParentPrompt(child, prompt);
      await record(child, { kind: "subagent_spawn", detail: `role=${role} prompt=s3://${config.promptBucket}/${promptKey} sha256=${sha256(prompt)}` });

      const scoped = await mintInstallationToken(parent, SUBAGENT_PERMISSIONS);
      const env = { ...process.env, GITHUB_READ_TOKEN: scoped.token };
      const abort = new AbortController();
      const role_ = roleConfig(role);

      const q = query({
        prompt,
        options: {
          model: config.model,
          systemPrompt: rolePrompt(role),
          cwd: workspace,
          env,
          settingSources: [],
          maxTurns: childBudget.limits.maxTurns,
          abortController: abort,
          mcpServers: {
            ...buildMcpServers(env),
            agent: createSdkMcpServer({ name: "agent", version: "1.0.0", tools: shellTools(workspace, childBudget) }),
          },
          canUseTool: makeCanUseTool(child, role_, workspace, childBudget, (e) => abort.abort(e)),
        },
      });

      let answer = "";
      try {
        for await (const msg of q) {
          childBudget.observe(msg);
          if (msg.type === "result") {
            answer = msg.subtype === "success" ? msg.result : `sub-agent ended: ${msg.subtype}`;
          }
        }
      } catch (err) {
        abort.abort(err);
        await record(child, { kind: "budget", outcome: "error", detail: (err as Error).message });
        return { content: [{ type: "text", text: `sub-agent stopped: ${(err as Error).message}` }], isError: true };
      }
      return { content: [{ type: "text", text: answer }] };
    },
  );
}
