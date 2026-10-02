import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { tool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
import type { RunContext } from "../identity.js";

const run = promisify(execFile);

const PROTECTED_BRANCHES = new Set(["main", "master", "develop", "release", "production"]);
const FORCE_FLAGS = new Set(["--force", "--force-with-lease", "--force-if-includes"]);
const PUSH_FLAGS = new Set(["--set-upstream", "-u", "--no-verify", "--force", "-f", "--force-with-lease", "--tags"]);

function authArgs(token: string): string[] {
  const basic = Buffer.from(`x-access-token:${token}`).toString("base64");
  return ["-c", `http.https://github.com/.extraheader=AUTHORIZATION: basic ${basic}`];
}

export function gitTools(ctx: RunContext, workspace: string, token: () => string) {
  const gitCommit = tool(
    "git_commit",
    "Stage all changes in the workspace and create a commit on the current branch.",
    { message: z.string().min(1).max(2000) },
    async ({ message }) => {
      await run("git", ["add", "--all"], { cwd: workspace });
      const { stdout } = await run(
        "git",
        ["-c", "user.name=issuesmith[bot]", "-c", "user.email=issuesmith[bot]@users.noreply.github.com", "commit", "-m", message],
        { cwd: workspace },
      );
      return { content: [{ type: "text", text: stdout }] };
    },
  );

  const gitPush = tool(
    "git_push",
    "Push a branch to origin. Use a refspec such as `agent/123-fix-parser` or `HEAD:agent/123-fix-parser`.",
    {
      refspec: z.string().min(1).max(200),
      flags: z.array(z.string()).max(4).default([]),
    },
    async ({ refspec, flags }) => {
      const target = refspec.includes(":") ? refspec.split(":")[1] : refspec;
      if (PROTECTED_BRANCHES.has(target)) {
        return { content: [{ type: "text", text: `refusing to push to protected branch ${target}` }], isError: true };
      }
      if (flags.some((f) => FORCE_FLAGS.has(f))) {
        return { content: [{ type: "text", text: "force pushes are not allowed" }], isError: true };
      }
      if (flags.some((f) => !PUSH_FLAGS.has(f))) {
        return { content: [{ type: "text", text: `unsupported flag in ${flags.join(" ")}` }], isError: true };
      }
      const { stdout, stderr } = await run("git", [...authArgs(token()), "push", ...flags, "origin", refspec], {
        cwd: workspace,
        timeout: 120_000,
      });
      return { content: [{ type: "text", text: `${stdout}${stderr}` }] };
    },
  );

  return [gitCommit, gitPush];
}
