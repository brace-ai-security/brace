import { readFileSync } from "node:fs";
import { parse } from "yaml";

export interface Budgets {
  maxTurns: number;
  maxWallMs: number;
  maxTokens: number;
  maxCostUsd: number;
  maxToolCallsPerMinute: number;
  maxSubagents: number;
}

export interface Quotas {
  runsPerUserPerDay: number;
  costPerUserPerDayUsd: number;
  runsPerInstallationPerHour: number;
  costPerInstallationPerDayUsd: number;
  fleetConcurrentRuns: number;
  fleetCostPerDayUsd: number;
}

export interface RoleConfig {
  name: string;
  tools: string[];
}

const toolsFile = parse(readFileSync("config/tools.yaml", "utf8")) as {
  policyVersion: string;
  roles: Record<string, { tools: { name: string; reason: string }[] }>;
};

export const config = {
  model: process.env.AGENT_MODEL ?? "claude-sonnet-4-5",
  workspaceRoot: process.env.WORKSPACE_ROOT ?? "/workspace",
  memoryBucket: process.env.MEMORY_BUCKET ?? "acme-issuesmith-memory",
  promptBucket: process.env.PROMPT_BUCKET ?? "acme-issuesmith-prompts",
  auditEndpoint: process.env.AUDIT_ENDPOINT ?? "http://audit-collector.observability:4318/v1/logs",
  approvalsConsoleUrl: "https://approvals.internal.acme-corp.com",
  haltLabel: "issuesmith:halt",
  policyVersion: toolsFile.policyVersion,
  budgets: {
    maxTurns: 60,
    maxWallMs: 45 * 60_000,
    maxTokens: 2_000_000,
    maxCostUsd: 15,
    maxToolCallsPerMinute: 30,
    maxSubagents: 4,
  } satisfies Budgets,
  quotas: {
    runsPerUserPerDay: 20,
    costPerUserPerDayUsd: 60,
    runsPerInstallationPerHour: 30,
    costPerInstallationPerDayUsd: 200,
    fleetConcurrentRuns: 25,
    fleetCostPerDayUsd: 2500,
  } satisfies Quotas,
};

export function roleConfig(role: string): RoleConfig {
  const entry = toolsFile.roles[role];
  if (!entry) throw new Error(`unknown role ${role}`);
  return { name: role, tools: entry.tools.map((t) => t.name) };
}
