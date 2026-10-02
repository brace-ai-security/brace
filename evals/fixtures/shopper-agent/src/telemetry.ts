import { randomUUID } from "node:crypto";
import type { RunContext } from "./identity.js";

export type ContextMeasure =
  | { method: "measured"; inputTokens: number; cachedReadTokens: number; cacheWriteTokens: number; compacted: boolean }
  | { method: "estimated"; inputTokens: number; estimator: string; compacted: boolean }
  | { method: "unavailable"; reason: string };

export interface AuditEvent {
  kind: "run_start" | "model_call" | "tool_call" | "tool_denied" | "tool_error" | "approval" | "budget_stop" | "run_end";
  step: number;
  name?: string;
  args?: unknown;
  outcome?: string;
  approvalId?: string;
  policyVersion?: number;
  model?: { requested: string; served?: string; role: string };
  context?: ContextMeasure;
}

// Context size is counted as the provider reports it on the request that produced the decision:
// input_tokens + cache_read_input_tokens + cache_creation_input_tokens. Compaction is recorded
// when the loop has dropped earlier turns. A missing usage block is "unavailable", never 0.
export function measureContext(usage: any, compacted: boolean): ContextMeasure {
  if (!usage || typeof usage.input_tokens !== "number") {
    return { method: "unavailable", reason: "provider returned no usage block" };
  }
  const cachedRead = usage.cache_read_input_tokens ?? 0;
  const cacheWrite = usage.cache_creation_input_tokens ?? 0;
  return {
    method: "measured",
    inputTokens: usage.input_tokens + cachedRead + cacheWrite,
    cachedReadTokens: cachedRead,
    cacheWriteTokens: cacheWrite,
    compacted,
  };
}

const REDACT_KEYS = new Set(["paymentToken", "cardToken", "password", "authorization"]);

function redact(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(redact);
  if (v && typeof v === "object") {
    return Object.fromEntries(
      Object.entries(v as Record<string, unknown>).map(([k, x]) => [k, REDACT_KEYS.has(k) ? "[redacted]" : redact(x)]),
    );
  }
  return v;
}

export function audit(ctx: RunContext, ev: AuditEvent, lastContext?: ContextMeasure): void {
  const record = {
    eventId: randomUUID(),
    ts: new Date().toISOString(),
    runId: ctx.runId,
    accountableParty: ctx.accountableParty,
    operationalOwner: ctx.operationalOwner,
    tenantId: ctx.tenantId,
    delegatedSubject: ctx.userId,
    agentTypeId: ctx.agentTypeId,
    agentInstanceId: ctx.agentInstanceId,
    traceparent: ctx.traceparent,
    ...ev,
    args: redact(ev.args),
    // Every action carries the context size of the model decision that proposed it.
    context: ev.context ?? lastContext ?? { method: "unavailable", reason: "no model decision in this run yet" },
  };
  process.stdout.write(JSON.stringify(record) + "\n");
}
