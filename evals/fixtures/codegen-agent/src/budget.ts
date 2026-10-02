import { Redis } from "ioredis";
import type { SDKMessage } from "@anthropic-ai/claude-agent-sdk";
import type { Budgets, Quotas } from "./config.js";

const USD_PER_MTOK = { input: 3, output: 15, cacheWrite: 3.75, cacheRead: 0.3 };

interface Usage {
  input_tokens: number;
  output_tokens: number;
  cache_creation_input_tokens?: number | null;
  cache_read_input_tokens?: number | null;
}

function estimateCost(u: Usage): number {
  return (
    (u.input_tokens * USD_PER_MTOK.input +
      u.output_tokens * USD_PER_MTOK.output +
      (u.cache_creation_input_tokens ?? 0) * USD_PER_MTOK.cacheWrite +
      (u.cache_read_input_tokens ?? 0) * USD_PER_MTOK.cacheRead) /
    1_000_000
  );
}

export class BudgetExceeded extends Error {
  constructor(public readonly limit: string, detail: string) {
    super(`budget exceeded: ${limit} (${detail})`);
  }
}

export class RunBudget {
  private turns = 0;
  private tokens = 0;
  private costUsd = 0;
  private subagents = 0;
  private callTimes: number[] = [];
  private readonly startedAt = Date.now();

  constructor(readonly limits: Budgets, private readonly parent?: RunBudget) {}

  onTurn(): void {
    this.turns += 1;
    if (this.turns > this.limits.maxTurns) throw new BudgetExceeded("turns", `${this.turns}`);
    this.checkWallClock();
  }

  onUsage(inputTokens: number, outputTokens: number, costUsd: number): void {
    this.tokens += inputTokens + outputTokens;
    this.costUsd += costUsd;
    this.parent?.onUsage(inputTokens, outputTokens, costUsd);
    if (this.tokens > this.limits.maxTokens) throw new BudgetExceeded("tokens", `${this.tokens}`);
    if (this.costUsd > this.limits.maxCostUsd) throw new BudgetExceeded("cost", this.costUsd.toFixed(2));
  }

  onToolCall(): void {
    const now = Date.now();
    this.callTimes = this.callTimes.filter((t) => now - t < 60_000);
    this.callTimes.push(now);
    if (this.callTimes.length > this.limits.maxToolCallsPerMinute) {
      throw new BudgetExceeded("tool_rate", `${this.callTimes.length}/min`);
    }
    this.parent?.onToolCall();
    this.checkWallClock();
  }

  observe(msg: SDKMessage): void {
    if (msg.type === "assistant") {
      const u = msg.message.usage as Usage;
      this.onTurn();
      this.onUsage(u.input_tokens + (u.cache_creation_input_tokens ?? 0) + (u.cache_read_input_tokens ?? 0), u.output_tokens, estimateCost(u));
    }
  }

  spentUsd(): number {
    return this.costUsd;
  }

  onSubagent(): void {
    this.subagents += 1;
    if (this.subagents > this.limits.maxSubagents) throw new BudgetExceeded("subagents", `${this.subagents}`);
  }

  remainingMs(): number {
    return Math.max(0, this.limits.maxWallMs - (Date.now() - this.startedAt));
  }

  child(): RunBudget {
    return new RunBudget(
      {
        ...this.limits,
        maxTurns: Math.min(20, this.limits.maxTurns - this.turns),
        maxWallMs: this.remainingMs(),
        maxTokens: this.limits.maxTokens - this.tokens,
        maxCostUsd: this.limits.maxCostUsd - this.costUsd,
        maxSubagents: 0,
      },
      this,
    );
  }

  private checkWallClock(): void {
    if (this.remainingMs() === 0) throw new BudgetExceeded("wall_clock", `${this.limits.maxWallMs}ms`);
  }
}

const redis = new Redis(process.env.REDIS_URL ?? "redis://redis.agents:6379");
const day = () => new Date().toISOString().slice(0, 10);
const hour = () => new Date().toISOString().slice(0, 13);

const keys = (user: string, installationId: number) => ({
  userRuns: `quota:runs:${day()}:user:${user}`,
  userCost: `quota:cost:${day()}:user:${user}`,
  instRuns: `quota:runs:${hour()}:inst:${installationId}`,
  instCost: `quota:cost:${day()}:inst:${installationId}`,
  fleetCost: `quota:cost:${day()}:fleet`,
  fleetActive: "quota:fleet:active",
});

async function counter(key: string, ttl: number): Promise<number> {
  const n = await redis.incr(key);
  await redis.expire(key, ttl);
  return n;
}

async function spent(key: string): Promise<number> {
  return Number((await redis.get(key)) ?? 0);
}

export async function acquireRunSlot(user: string, installationId: number, q: Quotas): Promise<() => Promise<void>> {
  const k = keys(user, installationId);

  if ((await counter(k.userRuns, 86_400)) > q.runsPerUserPerDay) throw new BudgetExceeded("user_daily_runs", user);
  if ((await counter(k.instRuns, 3_600)) > q.runsPerInstallationPerHour) throw new BudgetExceeded("installation_hourly_runs", `${installationId}`);
  if ((await spent(k.userCost)) >= q.costPerUserPerDayUsd) throw new BudgetExceeded("user_daily_cost", user);
  if ((await spent(k.instCost)) >= q.costPerInstallationPerDayUsd) throw new BudgetExceeded("installation_daily_cost", `${installationId}`);
  if ((await spent(k.fleetCost)) >= q.fleetCostPerDayUsd) throw new BudgetExceeded("fleet_daily_cost", "fleet");

  const active = await redis.incr(k.fleetActive);
  if (active > q.fleetConcurrentRuns) {
    await redis.decr(k.fleetActive);
    throw new BudgetExceeded("fleet_concurrency", `${active}`);
  }
  return async () => {
    await redis.decr(k.fleetActive);
  };
}

export async function chargeSpend(user: string, installationId: number, costUsd: number): Promise<void> {
  const k = keys(user, installationId);
  for (const key of [k.userCost, k.instCost, k.fleetCost]) {
    await redis.incrbyfloat(key, costUsd);
    await redis.expire(key, 86_400);
  }
}
