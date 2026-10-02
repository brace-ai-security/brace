import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, UpdateCommand } from "@aws-sdk/lib-dynamodb";
import type { Budgets } from "../config.js";
import { env } from "../config.js";

export type LimitName =
  | "turns"
  | "wall_time"
  | "input_tokens"
  | "output_tokens"
  | "run_cost"
  | "tool_calls"
  | "tool_call_rate"
  | "peer_calls"
  | "subject_daily_cost"
  | "tenant_daily_cost"
  | "fleet_daily_cost"
  | "tenant_tool_rate"
  | "fleet_tool_rate";

export class BudgetExceeded extends Error {
  constructor(public limit: LimitName, public used: number, public max: number) {
    super(`budget exceeded: ${limit} (${used} > ${max})`);
  }
}

// Shared counters across runs and pods. add() must be atomic and refuse to go past max.
export interface QuotaStore {
  add(key: string, amount: number, max: number, ttlSeconds: number): Promise<{ ok: boolean; used: number }>;
}

export class DynamoQuotaStore implements QuotaStore {
  private ddb = DynamoDBDocumentClient.from(new DynamoDBClient({ region: env.region }));
  async add(key: string, amount: number, max: number, ttlSeconds: number) {
    try {
      const res = await this.ddb.send(
        new UpdateCommand({
          TableName: env.budgetTable,
          Key: { pk: key },
          UpdateExpression: "ADD used :n SET expiresAt = if_not_exists(expiresAt, :exp)",
          ConditionExpression: "attribute_not_exists(used) OR used <= :room",
          ExpressionAttributeValues: {
            ":n": amount,
            ":room": max - amount,
            ":exp": Math.floor(Date.now() / 1000) + ttlSeconds,
          },
          ReturnValues: "UPDATED_NEW",
        }),
      );
      return { ok: true, used: Number(res.Attributes?.used ?? amount) };
    } catch (err) {
      if ((err as { name?: string }).name === "ConditionalCheckFailedException") return { ok: false, used: max };
      throw err;
    }
  }
}

export interface Usage {
  input_tokens: number;
  output_tokens: number;
  cache_read_input_tokens?: number | null;
  cache_creation_input_tokens?: number | null;
}

const day = () => new Date().toISOString().slice(0, 10);
const minute = () => new Date().toISOString().slice(0, 16);

export class RunBudget {
  readonly abort = new AbortController();
  private started = Date.now();
  private timer: NodeJS.Timeout;
  private turns = 0;
  private inTok = 0;
  private outTok = 0;
  private cost = 0;
  private toolCalls = 0;
  private toolTimes: number[] = [];
  private peerCalls = 0;

  constructor(
    private b: Budgets,
    private store: QuotaStore,
    private scope: { tenantId: string; subjectId: string },
    private now: () => number = Date.now,
  ) {
    this.started = this.now();
    this.timer = setTimeout(
      () => this.abort.abort(new BudgetExceeded("wall_time", this.b.run.maxWallMs, this.b.run.maxWallMs)),
      this.b.run.maxWallMs,
    );
  }

  get signal(): AbortSignal {
    return this.abort.signal;
  }

  dispose(): void {
    clearTimeout(this.timer);
  }

  private check(limit: LimitName, used: number, max: number): void {
    if (used > max) {
      const e = new BudgetExceeded(limit, used, max);
      this.abort.abort(e);
      throw e;
    }
  }

  private checkWall(): void {
    this.check("wall_time", this.now() - this.started, this.b.run.maxWallMs);
  }

  turn(): void {
    this.checkWall();
    this.turns += 1;
    this.check("turns", this.turns, this.b.run.maxTurns);
  }

  async recordUsage(u: Usage, model: string): Promise<void> {
    const price = this.b.pricingUsdPerMTok[model];
    if (!price) throw new Error(`no pricing for model ${model}`);
    const cacheRead = u.cache_read_input_tokens ?? 0;
    const cacheWrite = u.cache_creation_input_tokens ?? 0;
    const callCost =
      (u.input_tokens * price.input +
        u.output_tokens * price.output +
        cacheRead * price.cacheRead +
        cacheWrite * price.cacheWrite) /
      1_000_000;

    this.inTok += u.input_tokens + cacheRead + cacheWrite;
    this.outTok += u.output_tokens;
    this.cost += callCost;
    this.check("input_tokens", this.inTok, this.b.run.maxInputTokens);
    this.check("output_tokens", this.outTok, this.b.run.maxOutputTokens);
    this.check("run_cost", this.cost, this.b.run.maxCostUsd);

    const q = this.b.quotas;
    await this.shared("subject_daily_cost", `cost#subject#${this.scope.subjectId}#${day()}`, callCost, q.perSubjectDailyUsd, 86400);
    await this.shared("tenant_daily_cost", `cost#tenant#${this.scope.tenantId}#${day()}`, callCost, q.perTenantDailyUsd, 86400);
    await this.shared("fleet_daily_cost", `cost#fleet#${day()}`, callCost, q.fleetDailyUsd, 86400);
  }

  async toolCall(tool: string): Promise<void> {
    this.checkWall();
    this.toolCalls += 1;
    this.check("tool_calls", this.toolCalls, this.b.run.maxToolCalls);

    const t = this.now();
    this.toolTimes = this.toolTimes.filter((x) => t - x < 60_000);
    this.toolTimes.push(t);
    this.check("tool_call_rate", this.toolTimes.length, this.b.run.maxToolCallsPerMinute);

    if (tool.startsWith("insurance__")) {
      this.peerCalls += 1;
      this.check("peer_calls", this.peerCalls, this.b.run.maxPeerCalls);
    }

    const q = this.b.quotas;
    await this.shared("tenant_tool_rate", `rate#tenant#${this.scope.tenantId}#${minute()}`, 1, q.perTenantToolCallsPerMinute, 120);
    await this.shared("fleet_tool_rate", `rate#fleet#${minute()}`, 1, q.fleetToolCallsPerMinute, 120);
  }

  private async shared(limit: LimitName, key: string, amount: number, max: number, ttl: number): Promise<void> {
    const r = await this.store.add(key, amount, max, ttl);
    if (!r.ok) {
      const e = new BudgetExceeded(limit, r.used + amount, max);
      this.abort.abort(e);
      throw e;
    }
  }
}
