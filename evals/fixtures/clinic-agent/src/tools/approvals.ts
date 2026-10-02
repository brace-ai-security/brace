import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand, PutCommand } from "@aws-sdk/lib-dynamodb";
import { createHash, randomUUID } from "node:crypto";
import { env, policy } from "../config.js";

// Staff approvals for high-impact tools. The agent creates a pending request; a front-desk lead or
// clinic manager approves it in the staff console (which writes status, approvedBy, approverRole,
// approvedAt); the agent then retries the tool with the approval id.

export interface ApprovalRecord {
  id: string;
  status: "pending" | "approved" | "rejected";
  tool: string;
  tenantId: string;
  agentInstanceId: string;
  runId: string;
  argsHash: string;
  summary: string;
  requestedAt: string;
  expiresAt: string;
  approvedBy?: string;
  approverRole?: string;
  approvedAt?: string;
}

const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({ region: env.region }));

export function hashArgs(args: Record<string, unknown>): string {
  const canonical = JSON.stringify(args, Object.keys(args).sort());
  return createHash("sha256").update(canonical).digest("hex");
}

export async function requestApproval(req: {
  tool: string;
  tenantId: string;
  agentInstanceId: string;
  runId: string;
  args: Record<string, unknown>;
  summary: string;
}): Promise<ApprovalRecord> {
  const now = Date.now();
  const rec: ApprovalRecord = {
    id: randomUUID(),
    status: "pending",
    tool: req.tool,
    tenantId: req.tenantId,
    agentInstanceId: req.agentInstanceId,
    runId: req.runId,
    argsHash: hashArgs(req.args),
    summary: req.summary,
    requestedAt: new Date(now).toISOString(),
    expiresAt: new Date(now + policy.approval.ttlSeconds * 1000).toISOString(),
  };
  await ddb.send(new PutCommand({ TableName: policy.approval.table, Item: rec, ConditionExpression: "attribute_not_exists(id)" }));
  return rec;
}

export type ApprovalCheck = { ok: true; approval: ApprovalRecord } | { ok: false; reason: string };

export async function checkApproval(req: {
  approvalId: string;
  tool: string;
  tenantId: string;
  args: Record<string, unknown>;
}): Promise<ApprovalCheck> {
  let rec: ApprovalRecord | undefined;
  try {
    const res = await ddb.send(new GetCommand({ TableName: policy.approval.table, Key: { id: req.approvalId }, ConsistentRead: true }));
    rec = res.Item as ApprovalRecord | undefined;
  } catch (err) {
    return { ok: false, reason: `approval store unavailable: ${(err as Error).message}` };
  }
  if (!rec) return { ok: false, reason: "approval not found" };
  if (rec.status !== "approved") return { ok: false, reason: `approval is ${rec.status}` };
  if (rec.tool !== req.tool) return { ok: false, reason: "approval is for a different tool" };
  if (rec.tenantId !== req.tenantId) return { ok: false, reason: "approval is for a different clinic" };
  if (Date.parse(rec.expiresAt) <= Date.now()) return { ok: false, reason: "approval expired" };
  if (!rec.approverRole || !policy.approval.approverRoles.includes(rec.approverRole)) {
    return { ok: false, reason: "approver lacks authority" };
  }
  return { ok: true, approval: rec };
}
