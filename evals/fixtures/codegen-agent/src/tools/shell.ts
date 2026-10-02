import { spawn } from "node:child_process";
import { tool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
import type { RunBudget } from "../budget.js";

const ALLOWED_PROGRAMS = new Set(["npm", "npx", "node", "yarn", "pnpm", "jest", "vitest", "tsc", "eslint", "prettier"]);
const MAX_OUTPUT = 64 * 1024;

function sandboxEnv(workspace: string): NodeJS.ProcessEnv {
  return {
    PATH: "/usr/local/bin:/usr/bin:/bin",
    HOME: workspace,
    CI: "true",
    NODE_ENV: "test",
    npm_config_cache: `${workspace}/.npm`,
    HTTPS_PROXY: process.env.HTTPS_PROXY,
    NO_PROXY: process.env.NO_PROXY,
  };
}

export function shellTools(workspace: string, budget: RunBudget) {
  const runCommand = tool(
    "run_command",
    "Run a project command (install, build, lint, test) in the workspace, e.g. `npm test -- --runInBand`.",
    { command: z.string().min(1).max(1000) },
    async ({ command }) => {
      const program = command.trim().split(/\s+/)[0];
      if (!ALLOWED_PROGRAMS.has(program)) {
        return { content: [{ type: "text", text: `${program} is not an allowed program` }], isError: true };
      }
      const timeout = Math.min(10 * 60_000, budget.remainingMs());
      const result = await new Promise<{ code: number | null; out: string }>((resolve) => {
        const child = spawn(command, { cwd: workspace, env: sandboxEnv(workspace), shell: true, timeout });
        let out = "";
        const collect = (chunk: Buffer) => {
          if (out.length < MAX_OUTPUT) out += chunk.toString("utf8");
        };
        child.stdout.on("data", collect);
        child.stderr.on("data", collect);
        child.on("close", (code) => resolve({ code, out: out.slice(0, MAX_OUTPUT) }));
      });
      return {
        content: [{ type: "text", text: `exit ${result.code}\n${result.out}` }],
        isError: result.code !== 0,
      };
    },
  );
  return [runCommand];
}
