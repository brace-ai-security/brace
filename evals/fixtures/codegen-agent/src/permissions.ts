import path from "node:path";
import type { CanUseTool, PermissionResult } from "@anthropic-ai/claude-agent-sdk";
import { record, redactArgs } from "./audit.js";
import { BudgetExceeded, type RunBudget } from "./budget.js";
import { config, type RoleConfig } from "./config.js";
import type { RunContext } from "./identity.js";

const FILE_TOOLS = new Set(["Read", "Edit", "Write", "Glob", "Grep"]);

export function insideWorkspace(workspace: string, candidate: string): boolean {
  const resolved = path.resolve(workspace, candidate);
  const rel = path.relative(workspace, resolved);
  return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
}

function filePathArg(input: Record<string, unknown>): string | undefined {
  const value = input.file_path ?? input.path;
  return typeof value === "string" ? value : undefined;
}

export function makeCanUseTool(
  ctx: RunContext,
  role: RoleConfig,
  workspace: string,
  budget: RunBudget,
  onAbort: (reason: Error) => void,
): CanUseTool {
  const allowed = new Set(role.tools);

  return async (toolName, input): Promise<PermissionResult> => {
    try {
      budget.onToolCall();
    } catch (err) {
      if (err instanceof BudgetExceeded) onAbort(err);
      return { behavior: "deny", message: (err as Error).message, interrupt: true };
    }

    if (!allowed.has(toolName)) {
      return { behavior: "deny", message: `${toolName} is not enabled for role ${role.name}` };
    }

    if (FILE_TOOLS.has(toolName)) {
      const p = filePathArg(input);
      if (p !== undefined && !insideWorkspace(workspace, p)) {
        return { behavior: "deny", message: `path ${p} is outside the workspace` };
      }
    }

    await record(ctx, {
      kind: "tool_call",
      tool: toolName,
      args: redactArgs(input),
      decision: "allow",
      policyVersion: config.policyVersion,
    });
    return { behavior: "allow", updatedInput: input };
  };
}
