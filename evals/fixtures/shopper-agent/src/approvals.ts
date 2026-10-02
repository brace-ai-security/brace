import { createHmac, randomUUID, timingSafeEqual } from "node:crypto";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand, PutCommand } from "@aws-sdk/lib-dynamodb";
import type { RunContext } from "./identity.js";

const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({}));
const TABLE = process.env.APPROVALS_TABLE ?? "shopper-approvals";
const KEY = Buffer.from(process.env.APPROVAL_HMAC_KEY ?? "", "base64");
const TTL_MS = 15 * 60_000;

export interface CartSummary {
  retailer: string;
  cartId: string;
  items: Array<{ title: string; sku: string; qty: number; price: number }>;
  total: number;
  currency: string;
  shipTo: string;
}

export type ActorSnapshot = Omit<RunContext, "abort" | "role" | "subjectToken">;

export interface Approval {
  id: string;
  actor: ActorSnapshot;
  userId: string;
  tenantId: string;
  retailer: string;
  cartId: string;
  summary: CartSummary;
  status: "pending" | "approved" | "denied" | "used";
  approvedBy?: string;
  approvedAt?: string;
  expiresAt: number;
  sig: string;
}

function sign(a: Pick<Approval, "id" | "userId" | "tenantId" | "retailer" | "cartId" | "expiresAt">): string {
  return createHmac("sha256", KEY)
    .update([a.id, a.userId, a.tenantId, a.retailer, a.cartId, a.expiresAt].join("|"))
    .digest("hex");
}

export async function createApproval(ctx: RunContext, summary: CartSummary): Promise<Approval> {
  const base = {
    id: randomUUID(),
    userId: ctx.userId,
    tenantId: ctx.tenantId,
    retailer: summary.retailer,
    cartId: summary.cartId,
    expiresAt: Date.now() + TTL_MS,
  };
  const { abort: _a, role: _r, subjectToken: _s, ...actor } = ctx;
  const approval: Approval = { ...base, actor, summary, status: "pending", sig: sign(base) };
  await ddb.send(new PutCommand({ TableName: TABLE, Item: approval }));
  return approval;
}

export async function recordDecision(id: string, userId: string, approve: boolean): Promise<Approval> {
  const { Item } = await ddb.send(new GetCommand({ TableName: TABLE, Key: { id } }));
  const a = Item as Approval | undefined;
  if (!a || a.userId !== userId) throw new Error("approval not found");
  if (a.status !== "pending") throw new Error(`approval is ${a.status}`);
  const updated: Approval = {
    ...a,
    status: approve ? "approved" : "denied",
    approvedBy: userId,
    approvedAt: new Date().toISOString(),
  };
  await ddb.send(new PutCommand({ TableName: TABLE, Item: updated }));
  return updated;
}

export async function loadValidApproval(ctx: RunContext, id: string, retailer: string, cartId: string): Promise<Approval> {
  const { Item } = await ddb.send(new GetCommand({ TableName: TABLE, Key: { id } }));
  const a = Item as Approval | undefined;
  if (!a) throw new Error("unknown approval");
  const expected = Buffer.from(sign(a), "hex");
  if (!timingSafeEqual(expected, Buffer.from(a.sig, "hex"))) throw new Error("approval signature mismatch");
  if (a.userId !== ctx.userId || a.tenantId !== ctx.tenantId) throw new Error("approval belongs to another user");
  if (a.retailer !== retailer || a.cartId !== cartId) throw new Error("approval is for a different cart");
  if (Date.now() > a.expiresAt) throw new Error("approval expired");
  if (a.status !== "approved") throw new Error(`approval is ${a.status}`);
  return a;
}

export async function markUsed(a: Approval): Promise<void> {
  await ddb.send(new PutCommand({ TableName: TABLE, Item: { ...a, status: "used", usedAt: new Date().toISOString() } }));
}
