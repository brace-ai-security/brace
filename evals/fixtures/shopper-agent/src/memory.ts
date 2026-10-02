import { randomUUID } from "node:crypto";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DeleteCommand, DynamoDBDocumentClient, GetCommand, PutCommand, QueryCommand, UpdateCommand } from "@aws-sdk/lib-dynamodb";
import { z } from "zod";
import { lastContext, currentStep } from "./loop.js";
import type { ContextMeasure } from "./telemetry.js";
import { pageFor } from "./tools/browser.js";
import type { ToolDef } from "./tools/registry.js";

const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({}));
const TABLE = process.env.MEMORY_TABLE ?? "shopper-memory";
const UNVERIFIED_TTL_MS = 30 * 24 * 3600_000;

export interface MemoryEntry {
  pk: string; // tenant#<tenantId>#user#<userId>
  sk: string; // pref#<uuid>
  kind: "size" | "brand" | "budget" | "address" | "notes";
  value: string;
  trust: "user_stated" | "verified" | "unverified";
  writtenBy: { agentInstanceId: string; agentTypeId: string; runId: string };
  writtenRunId: string;
  source: { type: "page"; url: string } | { type: "user_goal"; runId: string };
  sourceUrl?: string; // set for page sources, indexed by "by-source"
  sourceTurn: number;
  contextAtWrite: ContextMeasure;
  createdAt: string;
  expiresAt?: number;
  quarantined: boolean;
}

export const partition = (tenantId: string, userId: string) => `tenant#${tenantId}#user#${userId}`;

export async function readEntries(tenantId: string, userId: string): Promise<MemoryEntry[]> {
  const out = await ddb.send(new QueryCommand({
    TableName: TABLE,
    KeyConditionExpression: "pk = :pk AND begins_with(sk, :p)",
    FilterExpression: "quarantined = :f AND (attribute_not_exists(expiresAt) OR expiresAt > :now)",
    ExpressionAttributeValues: { ":pk": partition(tenantId, userId), ":p": "pref#", ":f": false, ":now": Date.now() },
  }));
  return (out.Items ?? []) as MemoryEntry[];
}

// Incident tooling: every entry written from a given page, or by a given run.
export async function findEntries(by: { sourceUrl: string } | { runId: string }): Promise<MemoryEntry[]> {
  const [index, key, value] = "sourceUrl" in by ? ["by-source", "sourceUrl", by.sourceUrl] : ["by-run", "writtenRunId", by.runId];
  const out = await ddb.send(new QueryCommand({
    TableName: TABLE, IndexName: index,
    KeyConditionExpression: `${key} = :v`, ExpressionAttributeValues: { ":v": value },
  }));
  return (out.Items ?? []) as MemoryEntry[];
}

export async function quarantine(e: Pick<MemoryEntry, "pk" | "sk">, reason: string, by: string): Promise<void> {
  await ddb.send(new UpdateCommand({
    TableName: TABLE, Key: { pk: e.pk, sk: e.sk },
    UpdateExpression: "SET quarantined = :t, quarantineReason = :r, quarantinedBy = :b, quarantinedAt = :at",
    ExpressionAttributeValues: { ":t": true, ":r": reason, ":b": by, ":at": new Date().toISOString() },
  }));
}

export async function purge(e: Pick<MemoryEntry, "pk" | "sk">): Promise<void> {
  await ddb.send(new DeleteCommand({ TableName: TABLE, Key: { pk: e.pk, sk: e.sk } }));
}

export async function loadRetailerSessions(tenantId: string, userId: string): Promise<any> {
  const out = await ddb.send(new GetCommand({ TableName: TABLE, Key: { pk: partition(tenantId, userId), sk: "retailer-sessions" } }));
  return out.Item?.storageState ?? { cookies: [], origins: [] };
}

export const memoryTools: ToolDef[] = [
  {
    id: "builtin:recall_preferences",
    description: "Load saved sizes, brands, budget, addresses, and notes for the user or a linked household member.",
    input: z.object({ member: z.object({ tenantId: z.string(), userId: z.string() }).optional() }),
    async run(ctx, { member }) {
      const who = member ?? { tenantId: ctx.tenantId, userId: ctx.userId };
      return (await readEntries(who.tenantId, who.userId)).map((e) => ({ kind: e.kind, value: e.value, trust: e.trust }));
    },
  },
  {
    id: "builtin:remember_preference",
    description: "Save a preference. Use when the user states one, or when a page confirms a size or fit detail for this user.",
    input: z.object({
      kind: z.enum(["size", "brand", "budget", "address", "notes"]),
      value: z.string().min(1).max(400),
      fromPage: z.boolean().default(false),
    }),
    async run(ctx, { kind, value, fromPage }) {
      const sourceUrl = fromPage ? (await pageFor(ctx)).url() : undefined;
      const item: MemoryEntry = {
        pk: partition(ctx.tenantId, ctx.userId),
        sk: `pref#${randomUUID()}`,
        kind, value,
        trust: fromPage ? "verified" : "user_stated",
        writtenBy: { agentInstanceId: ctx.agentInstanceId, agentTypeId: ctx.agentTypeId, runId: ctx.runId },
        writtenRunId: ctx.runId,
        source: sourceUrl ? { type: "page", url: sourceUrl } : { type: "user_goal", runId: ctx.runId },
        sourceUrl,
        sourceTurn: currentStep(ctx.runId),
        contextAtWrite: lastContext(ctx.runId),
        createdAt: new Date().toISOString(),
        expiresAt: fromPage ? Date.now() + UNVERIFIED_TTL_MS : undefined,
        quarantined: false,
      };
      await ddb.send(new PutCommand({ TableName: TABLE, Item: item }));
      return { saved: item.sk };
    },
  },
];
