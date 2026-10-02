import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parse } from "yaml";

export const ROOT = process.env.CLINIC_AGENT_ROOT ?? process.cwd();

export interface Policy {
  version: string;
  highImpactTools: string[];
  approval: { ttlSeconds: number; approverRoles: string[]; table: string };
}

export interface AllowlistEntry {
  tool: string;
  reason: string;
}

export interface Budgets {
  run: {
    maxTurns: number;
    maxWallMs: number;
    maxInputTokens: number;
    maxOutputTokens: number;
    maxCostUsd: number;
    maxToolCalls: number;
    maxToolCallsPerMinute: number;
    maxPeerCalls: number;
  };
  quotas: {
    perSubjectDailyUsd: number;
    perTenantDailyUsd: number;
    fleetDailyUsd: number;
    perTenantToolCallsPerMinute: number;
    fleetToolCallsPerMinute: number;
  };
  pricingUsdPerMTok: Record<string, { input: number; output: number; cacheRead: number; cacheWrite: number }>;
  onExceed: "handoff_to_staff";
}

function loadYaml<T>(rel: string): T {
  return parse(readFileSync(join(ROOT, rel), "utf8")) as T;
}

export const policy = loadYaml<Policy>("config/policy.yaml");
export const allowlist = loadYaml<{ role: string; tools: AllowlistEntry[] }>("config/tools.allowlist.yaml");
export const budgets = loadYaml<Budgets>("config/budgets.yaml");
export const manifest = JSON.parse(readFileSync(join(ROOT, "release/manifest.json"), "utf8"));

export const AGENT_MODEL = "claude-sonnet-4-5-20250929";
export const CLASSIFIER_MODEL = "claude-haiku-4-5-20251001";

export const env = {
  region: process.env.AWS_REGION ?? "us-west-2",
  controlTable: process.env.CONTROL_TABLE ?? "clinic-agent-control",
  budgetTable: process.env.BUDGET_TABLE ?? "clinic-agent-budgets",
  auditStream: process.env.AUDIT_STREAM ?? "clinic-agent-audit",
  smsSigningSecretArn: process.env.SMS_SIGNING_SECRET_ARN ?? "",
  chatJwksUrl: process.env.CHAT_JWKS_URL ?? "https://auth.northbay-clinics.example/.well-known/jwks.json",
  chatIssuer: process.env.CHAT_ISSUER ?? "https://auth.northbay-clinics.example/",
  eligibilityUrl: process.env.ELIGIBILITY_URL ?? "https://eligibility.partners.northbay-clinics.example/a2a",
  eligibilityIssuer: process.env.ELIGIBILITY_ISSUER ?? "https://eligibility.partners.northbay-clinics.example",
  tokenExchangeUrl: process.env.TOKEN_EXCHANGE_URL ?? "https://sts.northbay-clinics.example/oauth2/token",
  accountableParty: "northbay-clinic-group:patient-access",
  operationalOwner: "team:agent-platform",
};
