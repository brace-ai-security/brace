import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BudgetExceeded, RunBudget, type QuotaStore } from "../src/agent/budget.js";
import type { Budgets } from "../src/config.js";

class MemoryQuotaStore implements QuotaStore {
  used = new Map<string, number>();
  async add(key: string, amount: number, max: number) {
    const cur = this.used.get(key) ?? 0;
    if (cur + amount > max) return { ok: false, used: cur };
    this.used.set(key, cur + amount);
    return { ok: true, used: cur + amount };
  }
}

const MODEL = "claude-sonnet-4-5-20250929";

function small(overrides: Partial<Budgets["run"]> = {}, quotas: Partial<Budgets["quotas"]> = {}): Budgets {
  return {
    run: {
      maxTurns: 3,
      maxWallMs: 1000,
      maxInputTokens: 10_000,
      maxOutputTokens: 1_000,
      maxCostUsd: 1,
      maxToolCalls: 5,
      maxToolCallsPerMinute: 4,
      maxPeerCalls: 1,
      ...overrides,
    },
    quotas: {
      perSubjectDailyUsd: 100,
      perTenantDailyUsd: 100,
      fleetDailyUsd: 100,
      perTenantToolCallsPerMinute: 100,
      fleetToolCallsPerMinute: 100,
      ...quotas,
    },
    pricingUsdPerMTok: { [MODEL]: { input: 3, output: 15, cacheRead: 0.3, cacheWrite: 3.75 } },
    onExceed: "handoff_to_staff",
  };
}

const scope = { tenantId: "nb-castro", subjectId: "phone:+14155550199" };
const usage = (i: number, o: number) => ({ input_tokens: i, output_tokens: o });

async function expectLimit(p: Promise<unknown> | (() => unknown), limit: string) {
  try {
    await (typeof p === "function" ? p() : p);
  } catch (e) {
    expect(e).toBeInstanceOf(BudgetExceeded);
    expect((e as BudgetExceeded).limit).toBe(limit);
    return;
  }
  throw new Error(`expected ${limit} to be exceeded`);
}

describe("RunBudget hard limits", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("stops at the turn limit", async () => {
    const b = new RunBudget(small(), new MemoryQuotaStore(), scope);
    b.turn();
    b.turn();
    b.turn();
    await expectLimit(() => b.turn(), "turns");
    expect(b.signal.aborted).toBe(true);
  });

  it("aborts in-flight work at the wall-clock limit", async () => {
    const b = new RunBudget(small(), new MemoryQuotaStore(), scope);
    vi.advanceTimersByTime(1001);
    expect(b.signal.aborted).toBe(true);
    expect((b.signal.reason as BudgetExceeded).limit).toBe("wall_time");
  });

  it("stops on input tokens, output tokens, and run cost", async () => {
    await expectLimit(new RunBudget(small(), new MemoryQuotaStore(), scope).recordUsage(usage(10_001, 1), MODEL), "input_tokens");
    await expectLimit(new RunBudget(small(), new MemoryQuotaStore(), scope).recordUsage(usage(1, 1_001), MODEL), "output_tokens");
    await expectLimit(
      new RunBudget(small({ maxCostUsd: 0.01, maxInputTokens: 1e9 }), new MemoryQuotaStore(), scope).recordUsage(usage(5_000, 0), MODEL),
      "run_cost",
    );
  });

  it("counts cached input toward the token limit", async () => {
    const b = new RunBudget(small(), new MemoryQuotaStore(), scope);
    await expectLimit(b.recordUsage({ input_tokens: 10, output_tokens: 1, cache_read_input_tokens: 10_000 }, MODEL), "input_tokens");
  });

  it("stops on total tool calls, tool-call rate, and peer calls", async () => {
    const b1 = new RunBudget(small({ maxToolCallsPerMinute: 100 }), new MemoryQuotaStore(), scope);
    for (let i = 0; i < 5; i++) await b1.toolCall("ehr__search_slots");
    await expectLimit(b1.toolCall("ehr__search_slots"), "tool_calls");

    const b2 = new RunBudget(small({ maxToolCalls: 100 }), new MemoryQuotaStore(), scope);
    for (let i = 0; i < 4; i++) await b2.toolCall("ehr__search_slots");
    await expectLimit(b2.toolCall("ehr__search_slots"), "tool_call_rate");

    const b3 = new RunBudget(small(), new MemoryQuotaStore(), scope);
    await b3.toolCall("insurance__check_eligibility");
    await expectLimit(b3.toolCall("insurance__check_eligibility"), "peer_calls");
  });

  it("enforces per-subject, per-tenant, and fleet spend across many small runs", async () => {
    const store = new MemoryQuotaStore();
    const cfg = small({}, { perSubjectDailyUsd: 0.05 });
    // Each run spends about $0.03, well under its own run_cost limit.
    await new RunBudget(cfg, store, scope).recordUsage(usage(5_000, 1_000), MODEL);
    await expectLimit(new RunBudget(cfg, store, scope).recordUsage(usage(5_000, 1_000), MODEL), "subject_daily_cost");

    const tStore = new MemoryQuotaStore();
    const tCfg = small({}, { perTenantDailyUsd: 0.05 });
    await new RunBudget(tCfg, tStore, { ...scope, subjectId: "a" }).recordUsage(usage(5_000, 1_000), MODEL);
    await expectLimit(new RunBudget(tCfg, tStore, { ...scope, subjectId: "b" }).recordUsage(usage(5_000, 1_000), MODEL), "tenant_daily_cost");

    const fStore = new MemoryQuotaStore();
    const fCfg = small({}, { fleetDailyUsd: 0.05 });
    await new RunBudget(fCfg, fStore, { tenantId: "nb-castro", subjectId: "a" }).recordUsage(usage(5_000, 1_000), MODEL);
    await expectLimit(
      new RunBudget(fCfg, fStore, { tenantId: "nb-oakland", subjectId: "b" }).recordUsage(usage(5_000, 1_000), MODEL),
      "fleet_daily_cost",
    );
  });

  it("enforces per-tenant and fleet tool-call rates across runs", async () => {
    const store = new MemoryQuotaStore();
    const cfg = small({}, { perTenantToolCallsPerMinute: 3 });
    for (let i = 0; i < 3; i++) await new RunBudget(cfg, store, scope).toolCall("ehr__search_slots");
    await expectLimit(new RunBudget(cfg, store, scope).toolCall("ehr__search_slots"), "tenant_tool_rate");

    const fStore = new MemoryQuotaStore();
    const fCfg = small({}, { fleetToolCallsPerMinute: 2 });
    await new RunBudget(fCfg, fStore, { tenantId: "nb-castro", subjectId: "a" }).toolCall("ehr__search_slots");
    await new RunBudget(fCfg, fStore, { tenantId: "nb-fremont", subjectId: "b" }).toolCall("ehr__search_slots");
    await expectLimit(new RunBudget(fCfg, fStore, { tenantId: "nb-oakland", subjectId: "c" }).toolCall("ehr__search_slots"), "fleet_tool_rate");
  });

  it("fails the run when the shared quota store is unavailable", async () => {
    const broken: QuotaStore = { add: async () => Promise.reject(new Error("throttled")) };
    await expect(new RunBudget(small(), broken, scope).toolCall("ehr__search_slots")).rejects.toThrow("throttled");
  });
});
