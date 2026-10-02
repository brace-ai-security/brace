import { createHash, randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { createAppAuth } from "@octokit/auth-app";
import { SecretsManagerClient, GetSecretValueCommand } from "@aws-sdk/client-secrets-manager";
import { config } from "./config.js";

const pkg = JSON.parse(readFileSync("package.json", "utf8")) as { name: string; version: string };

export interface RunContext {
  readonly tenant: string;              // "<installation-id>/<owner>/<repo>"
  readonly installationId: number;
  readonly repo: { owner: string; name: string };
  readonly issueNumber: number;
  readonly accountableParty: string;    // team that owns the deployment
  readonly operationalOwner: string;    // on-call rotation
  readonly delegatedSubject: string;    // GitHub login that requested the run
  readonly agentTypeId: string;
  readonly agentInstanceId: string;
  readonly parentInstanceId?: string;
  readonly traceparent: string;
}

function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b));
    return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${canonical(v)}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

export function sha256(input: string): string {
  return createHash("sha256").update(input).digest("hex");
}

export function computeAgentTypeId(role = "implementer"): string {
  const manifest = {
    role,
    image: process.env.IMAGE_DIGEST ?? "unknown",
    harness: `${pkg.name}@${pkg.version}`,
    systemPrompt: "prompts/system.md",
    subagentPrompts: "prompts/subagents.md",
    toolPolicy: "config/tools.yaml",
    model: config.model,
    budgets: config.budgets,
  };
  return `at_${sha256(canonical(manifest)).slice(0, 32)}`;
}

export function newInstanceId(): string {
  return `ai_${randomUUID()}`;
}

export function argsDigest(args: unknown): string {
  return sha256(canonical(args));
}

const secrets = new SecretsManagerClient({});
let appKey: string | undefined;

async function appPrivateKey(): Promise<string> {
  if (!appKey) {
    const out = await secrets.send(new GetSecretValueCommand({ SecretId: "issuesmith/github-app-key" }));
    appKey = out.SecretString!;
  }
  return appKey;
}

export type InstallationPermissions = Record<string, "read" | "write">;

export const IMPLEMENTER_PERMISSIONS: InstallationPermissions = {
  contents: "write",
  pull_requests: "write",
  issues: "write",
  actions: "write",
  metadata: "read",
};

export const SUBAGENT_PERMISSIONS: InstallationPermissions = {
  contents: "read",
  metadata: "read",
};

export async function mintInstallationToken(
  ctx: Pick<RunContext, "installationId" | "repo">,
  permissions: InstallationPermissions,
): Promise<{ token: string; expiresAt: string }> {
  const auth = createAppAuth({
    appId: Number(process.env.GITHUB_APP_ID),
    privateKey: await appPrivateKey(),
  });
  const result = await auth({
    type: "installation",
    installationId: ctx.installationId,
    repositoryNames: [ctx.repo.name],
    permissions,
  });
  return { token: result.token, expiresAt: result.expiresAt };
}
