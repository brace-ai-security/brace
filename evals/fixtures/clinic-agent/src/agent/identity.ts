import { createHash, randomUUID } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { ROOT, AGENT_MODEL, CLASSIFIER_MODEL, env } from "../config.js";

// agent-type-id = sha256 over a fixed, ordered manifest of identity-defining inputs.
// Each input is written as "<label>\0<bytes>\0" so that inputs cannot run together.
const CONFIG_FILES = ["config/policy.yaml", "config/tools.allowlist.yaml", "config/budgets.yaml"];

export interface TypeIdInputs {
  imageDigest: string;
  harnessVersion: string;
  harnessGitSha: string;
}

export function typeIdManifest(inputs: TypeIdInputs): Array<[string, Buffer]> {
  const parts: Array<[string, Buffer]> = [
    ["image", Buffer.from(inputs.imageDigest)],
    ["harness.version", Buffer.from(inputs.harnessVersion)],
    ["harness.gitSha", Buffer.from(inputs.harnessGitSha)],
  ];
  const promptDir = join(ROOT, "prompts");
  const promptFiles = readdirSync(promptDir)
    .filter((f) => f.endsWith(".txt"))
    .sort();
  for (const f of promptFiles) {
    parts.push([`prompt:${f}`, readFileSync(join(promptDir, f))]);
  }
  parts.push(["model.agent", Buffer.from(AGENT_MODEL)]);
  parts.push(["model.classifier", Buffer.from(CLASSIFIER_MODEL)]);
  for (const f of CONFIG_FILES) {
    parts.push([`config:${f}`, readFileSync(join(ROOT, f))]);
  }
  return parts;
}

export function computeAgentTypeId(inputs: TypeIdInputs): string {
  const h = createHash("sha256");
  for (const [label, bytes] of typeIdManifest(inputs)) {
    h.update(label);
    h.update("\0");
    h.update(bytes);
    h.update("\0");
  }
  return `sha256:${h.digest("hex")}`;
}

// One instance id per process. Pods are the unit an operator contains.
export const AGENT_INSTANCE_ID = randomUUID();

let AGENT_TYPE_ID = "";
export function setAgentTypeId(id: string): void {
  AGENT_TYPE_ID = id;
}

export interface Subject {
  kind: "patient" | "staff" | "system";
  id: string;
}

export interface Logger {
  info(obj: object, msg?: string): void;
  warn(obj: object, msg?: string): void;
  error(obj: object, msg?: string): void;
}

export interface RunContext {
  runId: string;
  tenantId: string;
  subject: Subject;
  channel: "sms" | "webchat" | "reminder";
  traceparent: string;
  log: Logger;
  identity(): {
    accountableParty: string;
    operationalOwner: string;
    tenantId: string;
    agentTypeId: string;
    agentInstanceId: string;
    traceparent: string;
  };
  workloadToken(): Promise<string>;
}

// Projected service-account token (audience: the group STS), rotated by the kubelet.
const WORKLOAD_TOKEN_PATH = process.env.WORKLOAD_TOKEN_PATH ?? "/var/run/secrets/tokens/sts-token";

export function newRunContext(init: {
  tenantId: string;
  subject: Subject;
  channel: RunContext["channel"];
  traceparent?: string;
  log: Logger;
}): RunContext {
  const runId = randomUUID();
  const traceparent = init.traceparent ?? `00-${randomUUID().replace(/-/g, "")}-${randomUUID().replace(/-/g, "").slice(0, 16)}-01`;
  return {
    runId,
    tenantId: init.tenantId,
    subject: init.subject,
    channel: init.channel,
    traceparent,
    log: init.log,
    identity: () => ({
      accountableParty: env.accountableParty,
      operationalOwner: env.operationalOwner,
      tenantId: init.tenantId,
      agentTypeId: AGENT_TYPE_ID,
      agentInstanceId: AGENT_INSTANCE_ID,
      traceparent,
    }),
    workloadToken: async () => readFileSync(WORKLOAD_TOKEN_PATH, "utf8").trim(),
  };
}
