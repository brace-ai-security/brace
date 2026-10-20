import { FirehoseClient, PutRecordCommand } from "@aws-sdk/client-firehose";
import { randomUUID } from "node:crypto";
import { z } from "zod";
import { env } from "../config.js";

// Every audit record carries the six identity fields. Values come from RunContext, which is built
// by the HTTP layer and the worker, never from model output.
export const IdentityFields = z.object({
  accountableParty: z.string().min(1),
  operationalOwner: z.string().min(1),
  tenantId: z.string().min(1),
  agentTypeId: z.string().startsWith("sha256:"),
  agentInstanceId: z.string().uuid(),
  traceparent: z.string().regex(/^00-[0-9a-f]{32}-[0-9a-f]{16}-0[01]$/),
});

export const AuditEvent = IdentityFields.extend({
  eventId: z.string().uuid(),
  ts: z.string().datetime(),
  runId: z.string().uuid(),
  event: z.enum([
    "run.started",
    "run.stopped",
    "run.completed",
    "intent.classified",
    "model.decision",
    "tool.denied",
    "tool.approval_requested",
    "tool.executed",
    "tool.failed",
    "payment.refund",
    "peer.call",
    "reminder.sent",
  ]),
  subject: z.object({ kind: z.enum(["patient", "staff", "system"]), id: z.string() }),
  tool: z.string().optional(),
  toolUseId: z.string().optional(),
  policyVersion: z.string().optional(),
  approvalId: z.string().optional(),
  reason: z.string().optional(),
  context: z
    .object({
      tokens: z.number().int().nonnegative().nullable(),
      status: z.enum(["measured", "estimated", "unavailable"]),
      method: z.string(),
      cachedInputTokens: z.number().int().nonnegative().nullable(),
      compacted: z.boolean(),
    })
    .optional(),
  detail: z.record(z.unknown()).optional(),
});
export type AuditEvent = z.infer<typeof AuditEvent>;

const firehose = new FirehoseClient({ region: env.region });

export class AuditUnavailable extends Error {}

export const audit = {
  async record(e: Omit<AuditEvent, "eventId" | "ts">): Promise<void> {
    const full = AuditEvent.parse({ ...e, eventId: randomUUID(), ts: new Date().toISOString() });
    try {
      await firehose.send(
        new PutRecordCommand({
          DeliveryStreamName: env.auditStream,
          Record: { Data: Buffer.from(JSON.stringify(full) + "\n") },
        }),
      );
    } catch (err) {
      // Callers treat this as a hard failure: an action that cannot be audited does not run.
      throw new AuditUnavailable(`audit delivery failed: ${(err as Error).message}`);
    }
  },
};

// PHI scrubbing for anything that leaves the EHR boundary toward the model or the audit summary.
const DROP_KEYS = new Set(["ssn", "dateOfBirth", "dob", "memberId", "subscriberId", "cardNumber", "cardLast4", "address"]);
const PATTERNS: Array<[RegExp, string]> = [
  [/\b\d{3}-\d{2}-\d{4}\b/g, "[ssn]"],
  [/\b(?:\d[ -]?){13,19}\b/g, "[card]"],
  [/\b[A-Z]{3}\d{9}\b/g, "[member-id]"],
];

export function redactPhi(value: unknown): unknown {
  if (typeof value === "string") {
    return PATTERNS.reduce((s, [re, sub]) => s.replace(re, sub), value);
  }
  if (Array.isArray(value)) return value.map(redactPhi);
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      if (DROP_KEYS.has(k)) continue;
      out[k] = redactPhi(v);
    }
    return out;
  }
  return value;
}
