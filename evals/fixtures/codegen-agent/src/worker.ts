import { execFile } from "node:child_process";
import { mkdir, readFile } from "node:fs/promises";
import { promisify } from "node:util";
import { Worker, type Job } from "bullmq";
import { context, propagation, trace } from "@opentelemetry/api";
import { createSdkMcpServer, query } from "@anthropic-ai/claude-agent-sdk";
import { record } from "./audit.js";
import { BudgetExceeded, RunBudget, acquireRunSlot, chargeSpend } from "./budget.js";
import { config, roleConfig } from "./config.js";
import { IMPLEMENTER_PERMISSIONS, mintInstallationToken, type RunContext } from "./identity.js";
import { isHalted, RunHalted } from "./killswitch.js";
import { verifyToolFingerprints } from "./mcp/fingerprint.js";
import { buildMcpServers } from "./mcp/servers.js";
import { loadConventions, memoryTools } from "./memory.js";
import { makeCanUseTool } from "./permissions.js";
import { delegateTool } from "./subagents.js";
import { gitTools } from "./tools/git.js";
import { githubTools } from "./tools/github.js";
import { shellTools } from "./tools/shell.js";

const exec = promisify(execFile);
const tracer = trace.getTracer("issuesmith");

export interface RunJob {
  ctx: RunContext;
  issue: { title: string; body: string };
}

async function cloneWorkspace(ctx: RunContext, token: string): Promise<string> {
  const dir = `${config.workspaceRoot}/${ctx.agentInstanceId}`;
  await mkdir(dir, { recursive: true });
  const basic = Buffer.from(`x-access-token:${token}`).toString("base64");
  await exec(
    "git",
    [
      "-c", `http.https://github.com/.extraheader=AUTHORIZATION: basic ${basic}`,
      "clone", "--depth=50", `https://github.com/${ctx.repo.owner}/${ctx.repo.name}.git`, dir,
    ],
    { timeout: 5 * 60_000 },
  );
  return dir;
}

async function runIssue(job: Job<RunJob>): Promise<void> {
  const { ctx, issue } = job.data;
  const release = await acquireRunSlot(ctx.delegatedSubject, ctx.installationId, config.quotas);
  try {
    await execute(ctx, issue);
  } finally {
    await release();
  }
}

async function execute(ctx: RunContext, issue: RunJob["issue"]): Promise<void> {
  const budget = new RunBudget(config.budgets);
  const abort = new AbortController();
  const wallClock = setTimeout(
    () => abort.abort(new BudgetExceeded("wall_clock", `${config.budgets.maxWallMs}ms`)),
    config.budgets.maxWallMs,
  );

  const minted = await mintInstallationToken(ctx, IMPLEMENTER_PERMISSIONS);
  process.env.GITHUB_TOKEN = minted.token;
  const token = () => process.env.GITHUB_TOKEN!;

  await record(ctx, { kind: "run_start", detail: `issue #${ctx.issueNumber}` });
  const workspace = await cloneWorkspace(ctx, minted.token);

  const external = buildMcpServers(process.env);
  await verifyToolFingerprints(external);

  const systemPrompt = [
    await readFile("prompts/system.md", "utf8"),
    "## Repository conventions (from earlier runs)",
    await loadConventions(ctx),
  ].join("\n\n");

  const agentServer = createSdkMcpServer({
    name: "agent",
    version: "1.0.0",
    tools: [
      ...shellTools(workspace, budget),
      ...gitTools(ctx, workspace, token),
      ...githubTools(ctx, budget, token),
      ...memoryTools(ctx),
      delegateTool(ctx, workspace, budget),
    ],
  });

  const q = query({
    prompt: `Issue #${ctx.issueNumber}: ${issue.title}\n\n${issue.body}`,
    options: {
      model: config.model,
      systemPrompt,
      cwd: workspace,
      settingSources: [],
      maxTurns: config.budgets.maxTurns,
      abortController: abort,
      disallowedTools: ["Bash", "WebFetch", "WebSearch", "Task", "NotebookEdit"],
      mcpServers: { ...external, agent: agentServer },
      canUseTool: makeCanUseTool(ctx, roleConfig("implementer"), workspace, budget, (e) => abort.abort(e)),
    },
  });

  let outcome = "completed";
  try {
    for await (const msg of q) {
      budget.observe(msg);
      if (msg.type === "assistant" && (await isHalted(ctx, token()))) {
        throw new RunHalted(`halted by ${config.haltLabel}`);
      }
      if (msg.type === "result") outcome = msg.subtype;
    }
  } catch (err) {
    outcome = (err as Error).message;
    abort.abort(err);
    await record(ctx, { kind: err instanceof RunHalted ? "halt" : "budget", outcome: "error", detail: outcome });
  } finally {
    clearTimeout(wallClock);
    await chargeSpend(ctx.delegatedSubject, ctx.installationId, budget.spentUsd());
    await record(ctx, { kind: "run_end", detail: outcome });
  }
}

new Worker<RunJob>(
  "issuesmith-runs",
  async (job) => {
    const parent = propagation.extract(context.active(), { traceparent: job.data.ctx.traceparent });
    return context.with(parent, () =>
      tracer.startActiveSpan("issuesmith.run", async (span) => {
        span.setAttributes({
          "gen_ai.agent.id": job.data.ctx.agentInstanceId,
          "issuesmith.agent_type_id": job.data.ctx.agentTypeId,
          "issuesmith.tenant": job.data.ctx.tenant,
        });
        try {
          await runIssue(job);
        } finally {
          span.end();
        }
      }),
    );
  },
  { connection: { url: process.env.REDIS_URL }, concurrency: 1 },
);
