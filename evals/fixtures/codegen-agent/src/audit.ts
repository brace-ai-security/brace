import { randomUUID } from "node:crypto";
import { config } from "./config.js";
import type { RunContext } from "./identity.js";

export interface AuditEvent {
  kind: "run_start" | "run_end" | "tool_call" | "tool_result" | "approval" | "subagent_spawn" | "halt" | "budget";
  tool?: string;
  args?: unknown;
  decision?: "allow" | "deny";
  policyVersion?: string;
  approvalId?: string;
  outcome?: "ok" | "error";
  detail?: string;
}

function identityFields(ctx: RunContext) {
  return {
    accountable_party: ctx.accountableParty,
    operational_owner: ctx.operationalOwner,
    tenant: ctx.tenant,
    agent_type_id: ctx.agentTypeId,
    agent_instance_id: ctx.agentInstanceId,
    parent_instance_id: ctx.parentInstanceId ?? null,
    delegated_subject: ctx.delegatedSubject,
    traceparent: ctx.traceparent,
  };
}

export async function record(ctx: RunContext, event: AuditEvent): Promise<void> {
  const body = {
    event_id: randomUUID(),
    ts: new Date().toISOString(),
    ...event,
    ...identityFields(ctx),
  };
  const res = await fetch(config.auditEndpoint, {
    method: "POST",
    headers: { "content-type": "application/json", traceparent: ctx.traceparent },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(5_000),
  });
  if (!res.ok) throw new Error(`audit write failed: ${res.status}`);
}

const SECRET_KEYS = /token|secret|password|authorization|api[_-]?key/i;

export function redactArgs(args: unknown): unknown {
  if (!args || typeof args !== "object") return args;
  return Object.fromEntries(
    Object.entries(args as Record<string, unknown>).map(([k, v]) => [k, SECRET_KEYS.test(k) ? "[redacted]" : v]),
  );
}
