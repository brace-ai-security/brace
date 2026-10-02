from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.budget import Budget, BudgetExceeded
from app.identity import RunIdentity

CFG = {
    "per_run": {
        "max_steps": 3,
        "max_wall_seconds": 5,
        "max_tokens": 1000,
        "max_cost_usd": 0.01,
        "max_tool_calls_per_minute": 2,
        "max_subagents": 1,
    },
    "quotas_daily_usd": {"user": 1, "tenant": 2, "fleet": 3},
    "run_starts_per_minute": {"user": 1, "tenant": 2, "fleet": 3},
}


def ident() -> RunIdentity:
    return RunIdentity(
        accountable_party="user:alice@example-corp.test",
        operational_owner="team-procurement-platform",
        tenant="bu-emea",
        agent_type_id="atid-test",
        agent_instance_id="inst-test",
        trace_id="0" * 32,
        run_id="run-test",
        delegated_subject="user:alice@example-corp.test",
        agent_principal="spiffe://example-corp.test/ns/test/sa/procurement-agent",
    )


def usage(inp: int, out: int) -> SimpleNamespace:
    return SimpleNamespace(input_tokens=inp, output_tokens=out,
                           cache_read_input_tokens=0, cache_creation_input_tokens=0)


def test_step_limit():
    b = Budget.for_run(CFG, ident())
    for _ in range(3):
        b.check_step()
    with pytest.raises(BudgetExceeded) as exc:
        b.check_step()
    assert exc.value.limit == "max_steps"


def test_wall_clock_limit():
    b = Budget.for_run(CFG, ident())
    b.started_at -= 10
    with pytest.raises(BudgetExceeded) as exc:
        b.check_step()
    assert exc.value.limit == "max_wall_seconds"


def test_token_limit():
    b = Budget.for_run({**CFG, "per_run": {**CFG["per_run"], "max_cost_usd": 100}}, ident())
    with pytest.raises(BudgetExceeded) as exc:
        b.charge_model("claude-haiku-4-5-20251001", usage(900, 200))
    assert exc.value.limit == "max_tokens"


def test_cost_limit():
    b = Budget.for_run({**CFG, "per_run": {**CFG["per_run"], "max_tokens": 10_000_000}}, ident())
    with pytest.raises(BudgetExceeded) as exc:
        b.charge_model("claude-sonnet-4-5-20250929", usage(1000, 1000))
    assert exc.value.limit == "max_cost_usd"
    assert b.cost_usd > Decimal("0.01")


def test_tool_call_rate_limit():
    b = Budget.for_run(CFG, ident())
    b.check_tool_call(now=100.0)
    b.check_tool_call(now=101.0)
    with pytest.raises(BudgetExceeded) as exc:
        b.check_tool_call(now=102.0)
    assert exc.value.limit == "max_tool_calls_per_minute"
    b.check_tool_call(now=170.0)


def test_subagent_limit():
    b = Budget.for_run(CFG, ident())
    b.check_subagent()
    with pytest.raises(BudgetExceeded) as exc:
        b.check_subagent()
    assert exc.value.limit == "max_subagents"


class FakeConn:
    def __init__(self, store):
        self.store = store

    def transaction(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def fetchval(self, sql, scope, key, *rest):
        amount = rest[0] if rest else 1
        k = (scope, key, "spend" if rest else "starts")
        self.store[k] = self.store.get(k, 0) + amount
        return self.store[k]


class FakePool:
    def __init__(self):
        self.store = {}

    def acquire(self):
        return FakeConn(self.store)


async def test_run_start_quota_per_user():
    pool = FakePool()
    await Budget.for_run(CFG, ident()).reserve_run_start(pool)
    with pytest.raises(BudgetExceeded) as exc:
        await Budget.for_run(CFG, ident()).reserve_run_start(pool)
    assert exc.value.limit == "run_starts_per_minute.user"


async def test_daily_spend_quota_per_tenant_and_fleet():
    pool = FakePool()
    pool.store[("user", "user:alice@example-corp.test", "spend")] = Decimal("0")
    pool.store[("tenant", "bu-emea", "spend")] = Decimal("1.999")
    b = Budget.for_run(CFG, ident())
    b.unflushed_cost_usd = Decimal("0.01")
    with pytest.raises(BudgetExceeded) as exc:
        await b.flush(pool)
    assert exc.value.limit == "quota_daily_usd.tenant"

    pool.store[("tenant", "bu-emea", "spend")] = Decimal("0")
    pool.store[("fleet", "all", "spend")] = Decimal("2.995")
    b2 = Budget.for_run(CFG, ident())
    b2.unflushed_cost_usd = Decimal("0.01")
    with pytest.raises(BudgetExceeded) as exc:
        await b2.flush(pool)
    assert exc.value.limit == "quota_daily_usd.fleet"
