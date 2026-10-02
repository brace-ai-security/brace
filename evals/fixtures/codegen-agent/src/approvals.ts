import pg from "pg";
import { Signer } from "@aws-sdk/rds-signer";
import { record } from "./audit.js";
import { argsDigest, type RunContext } from "./identity.js";

export type GatedOperation = "create_pull_request" | "trigger_workflow";

export interface GatedAction {
  operation: GatedOperation;
  target: string;
  args: Record<string, unknown>;
  summary: string; // what the approver sees: title, files changed, diff stat, workflow inputs
}

export class ApprovalDenied extends Error {}

const signer = new Signer({
  hostname: process.env.APPROVALS_DB_HOST!,
  port: 5432,
  username: "issuesmith_worker",
});

async function db(): Promise<pg.Client> {
  const client = new pg.Client({
    host: process.env.APPROVALS_DB_HOST,
    database: "approvals",
    user: "issuesmith_worker",
    password: await signer.getAuthToken(),
    ssl: { rejectUnauthorized: true },
  });
  await client.connect();
  return client;
}

export async function requestApproval(ctx: RunContext, action: GatedAction): Promise<string> {
  const client = await db();
  try {
    const res = await client.query(
      `INSERT INTO approvals (agent_instance_id, tenant, operation, target, args_sha256, args_json, summary, requested_by)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id`,
      [
        ctx.agentInstanceId,
        ctx.tenant,
        action.operation,
        action.target,
        argsDigest(action.args),
        JSON.stringify(action.args),
        action.summary,
        ctx.delegatedSubject,
      ],
    );
    return res.rows[0].id as string;
  } finally {
    await client.end();
  }
}

export async function awaitDecision(id: string, timeoutMs: number): Promise<"approved" | "rejected" | "expired"> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const client = await db();
    try {
      const res = await client.query(`SELECT status FROM approvals WHERE id = $1`, [id]);
      const status = res.rows[0]?.status as string | undefined;
      if (status === "approved" || status === "rejected") return status;
    } finally {
      await client.end();
    }
    await new Promise((r) => setTimeout(r, 10_000));
  }
  return "expired";
}

export async function consumeApproval(ctx: RunContext, id: string, action: GatedAction): Promise<{ approver: string }> {
  const client = await db();
  try {
    const res = await client.query(
      `UPDATE approvals a
          SET consumed_at = now(), consumed_by = $2
        WHERE a.id = $1
          AND a.status = 'approved'
          AND a.consumed_at IS NULL
          AND a.expires_at > now()
          AND a.agent_instance_id = $2
          AND a.tenant = $3
          AND a.operation = $4
          AND a.target = $5
          AND a.args_sha256 = $6
          AND EXISTS (SELECT 1 FROM approvers p
                       WHERE p.login = a.approver AND p.tenant = a.tenant AND p.operation = a.operation)
        RETURNING a.approver`,
      [id, ctx.agentInstanceId, ctx.tenant, action.operation, action.target, argsDigest(action.args)],
    );
    if (res.rowCount !== 1) {
      await record(ctx, { kind: "approval", approvalId: id, decision: "deny", detail: "no matching unused approval" });
      throw new ApprovalDenied(`approval ${id} does not cover this action`);
    }
    await record(ctx, { kind: "approval", approvalId: id, decision: "allow", detail: `approver=${res.rows[0].approver}` });
    return { approver: res.rows[0].approver as string };
  } finally {
    await client.end();
  }
}

export async function withApproval<T>(
  ctx: RunContext,
  action: GatedAction,
  waitMs: number,
  recheck: () => Promise<void>,
  execute: (approvalId: string) => Promise<T>,
): Promise<T> {
  const id = await requestApproval(ctx, action);
  const decision = await awaitDecision(id, waitMs);
  if (decision !== "approved") throw new ApprovalDenied(`approval ${id} ${decision}`);
  await consumeApproval(ctx, id, action);
  await recheck();
  return execute(id);
}
