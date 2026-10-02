import { createHash, randomBytes, randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";

const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));

export type AgentRole = "shopper" | "price-watch";

export interface RunContext {
  runId: string;
  agentInstanceId: string;
  agentTypeId: string;
  tenantId: string;
  userId: string;
  accountableParty: string;
  operationalOwner: string;
  traceparent: string;
  role: AgentRole;
  subjectToken?: string; // the user's access token; used only as subject_token in token exchange
  abort: AbortController;
}

export const AGENT_TYPE_ID = createHash("sha256")
  .update(`${pkg.name}@${pkg.version}`)
  .digest("hex")
  .slice(0, 32);

const OPERATIONAL_OWNER = process.env.OPERATIONAL_OWNER ?? "agent-platform-oncall";
const INSTANCE_PREFIX = process.env.ECS_TASK_ID ?? "local";

function newTraceparent(): string {
  return `00-${randomBytes(16).toString("hex")}-${randomBytes(8).toString("hex")}-01`;
}

export function newRunContext(claims: { sub: string; tenant: string }, role: AgentRole, subjectToken?: string): RunContext {
  const runId = randomUUID();
  return {
    runId,
    agentInstanceId: `${INSTANCE_PREFIX}/${runId}`,
    agentTypeId: AGENT_TYPE_ID,
    tenantId: claims.tenant,
    userId: claims.sub,
    accountableParty: `tenant:${claims.tenant}`,
    operationalOwner: OPERATIONAL_OWNER,
    traceparent: newTraceparent(),
    role,
    subjectToken,
    abort: new AbortController(),
  };
}
