import { readFileSync } from "node:fs";
import { parse } from "yaml";
import { z } from "zod";
import { DynamoDBDocumentClient, UpdateCommand } from "@aws-sdk/lib-dynamodb";
import { DynamoDBClient, ConditionalCheckFailedException } from "@aws-sdk/client-dynamodb";
import type { RunContext } from "./identity.js";

const Limits = z.object({ maxUsd: z.number().positive(), maxConcurrentRuns: z.number().int().positive(), maxRunsPerHour: z.number().int().positive() });
const BudgetConfig = z.object({
  run: z.object({
    maxSteps: z.number().int().positive(),
    maxWallMs: z.number().int().positive(),
    maxInputTokens: z.number().int().positive(),
    maxOutputTokens: z.number().int().positive(),
    maxUsd: z.number().positive(),
    maxToolCallsPerMinute: z.number().int().positive(),
    maxPeerCalls: z.number().int().nonnegative(),
  }),
  quotas: z.object({ window: z.literal("day"), user: Limits, tenant: Limits, fleet: Limits }),
  onExceeded: z.literal("stop_and_notify_user"),
});
export type BudgetConfig = z.infer<typeof BudgetConfig>;

export const budgets: BudgetConfig = BudgetConfig.parse(
  parse(readFileSync(new URL("../config/budgets.yaml", import.meta.url), "utf8")),
);

export class BudgetExceeded extends Error {
  constructor(readonly limit: string, readonly observed: number, readonly max: number) {
    super(`budget ${limit} exceeded (${observed} > ${max})`);
  }
}

export class RunBudget {
  private steps = 0;
  private inTok = 0;
  private outTok = 0;
  private usd = 0;
  private peerCalls = 0;
  private callTimes: number[] = [];
  private readonly started: number;

  constructor(private readonly cfg = budgets.run, private readonly now = () => Date.now()) {
    this.started = now();
  }

  step(): void {
    this.steps += 1;
    if (this.steps > this.cfg.maxSteps) throw new BudgetExceeded("steps", this.steps, this.cfg.maxSteps);
    this.checkTime();
  }

  checkTime(): void {
    const elapsed = this.now() - this.started;
    if (elapsed > this.cfg.maxWallMs) throw new BudgetExceeded("wall_ms", elapsed, this.cfg.maxWallMs);
  }

  remainingMs(): number {
    return Math.max(0, this.cfg.maxWallMs - (this.now() - this.started));
  }

  addUsage(inputTokens: number, outputTokens: number, usd: number): void {
    this.inTok += inputTokens;
    this.outTok += outputTokens;
    this.usd += usd;
    if (this.inTok > this.cfg.maxInputTokens) throw new BudgetExceeded("input_tokens", this.inTok, this.cfg.maxInputTokens);
    if (this.outTok > this.cfg.maxOutputTokens) throw new BudgetExceeded("output_tokens", this.outTok, this.cfg.maxOutputTokens);
    if (this.usd > this.cfg.maxUsd) throw new BudgetExceeded("usd", this.usd, this.cfg.maxUsd);
  }

  toolCall(): void {
    const t = this.now();
    this.callTimes = this.callTimes.filter((x) => t - x < 60_000);
    this.callTimes.push(t);
    if (this.callTimes.length > this.cfg.maxToolCallsPerMinute) {
      throw new BudgetExceeded("tool_calls_per_minute", this.callTimes.length, this.cfg.maxToolCallsPerMinute);
    }
  }

  peerCall(): void {
    this.peerCalls += 1;
    if (this.peerCalls > this.cfg.maxPeerCalls) throw new BudgetExceeded("peer_calls", this.peerCalls, this.cfg.maxPeerCalls);
  }
}

// Shared quotas. Each reservation is one conditional UpdateItem, so concurrent replicas cannot
// overshoot a limit between a read and a write.
const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({}));
const TABLE = process.env.CONTROL_TABLE ?? "shopper-control";
type Attr = "usd" | "active" | "starts";

function scopes(ctx: RunContext, attr: Attr): Array<[string, number]> {
  const now = new Date().toISOString();
  const suffix = attr === "usd" ? `#${now.slice(0, 10)}` : attr === "starts" ? `#${now.slice(0, 13)}` : "";
  const q = budgets.quotas;
  const max = (l: z.infer<typeof Limits>) =>
    attr === "usd" ? l.maxUsd : attr === "starts" ? l.maxRunsPerHour : l.maxConcurrentRuns;
  return [
    [`quota#user#${ctx.tenantId}#${ctx.userId}${suffix}`, max(q.user)],
    [`quota#tenant#${ctx.tenantId}${suffix}`, max(q.tenant)],
    [`quota#fleet${suffix}`, max(q.fleet)],
  ];
}

const add = (pk: string, attr: Attr, delta: number, ceiling?: number) =>
  ddb.send(new UpdateCommand({
    TableName: TABLE, Key: { pk }, UpdateExpression: "ADD #a :d",
    ...(ceiling === undefined ? {} : { ConditionExpression: "attribute_not_exists(#a) OR #a <= :ceiling" }),
    ExpressionAttributeNames: { "#a": attr },
    ExpressionAttributeValues: { ":d": delta, ...(ceiling === undefined ? {} : { ":ceiling": ceiling }) },
  }));

async function reserveAll(ctx: RunContext, attr: Attr, amount: number): Promise<string[]> {
  const taken: string[] = [];
  try {
    for (const [pk, max] of scopes(ctx, attr)) {
      await add(pk, attr, amount, max - amount);
      taken.push(pk);
    }
    return taken;
  } catch (e) {
    await Promise.all(taken.map((pk) => add(pk, attr, -amount)));
    if (e instanceof ConditionalCheckFailedException) throw new BudgetExceeded(`${scopes(ctx, attr)[taken.length][0]}:${attr}`, NaN, NaN);
    throw e;
  }
}

export async function acquireRunSlot(ctx: RunContext): Promise<() => Promise<void>> {
  await reserveAll(ctx, "starts", 1);
  const taken = await reserveAll(ctx, "active", 1);
  return async () => void (await Promise.all(taken.map((pk) => add(pk, "active", -1))));
}

export async function reserveSpend(ctx: RunContext, usd: number): Promise<void> {
  await reserveAll(ctx, "usd", usd);
}
