"""Execution budgets enforced by the harness."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone

import redis


class BudgetExceeded(Exception):
    def __init__(self, limit: str, detail: str = ""):
        super().__init__(f"{limit} exceeded {detail}".strip())
        self.limit = limit


@dataclass(frozen=True)
class Limits:
    max_turns: int
    max_wall_seconds: float
    max_tokens: int
    max_cost_usd: float
    max_tool_calls_per_minute: int
    max_subagents: int


class SpendQuota:
    """Daily spend counters per principal, per tenant, and fleet-wide."""

    def __init__(self, r: redis.Redis, quotas: dict):
        self.r = r
        self.q = quotas

    def _keys(self, principal: str, tenant: str) -> list[tuple[str, float]]:
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        return [
            (f"spend:{day}:principal:{principal}", self.q["principal_daily_usd"]),
            (f"spend:{day}:tenant:{tenant}", self.q["tenant_daily_usd"]),
            (f"spend:{day}:fleet", self.q["fleet_daily_usd"]),
        ]

    def check(self, principal: str, tenant: str) -> None:
        for key, cap in self._keys(principal, tenant):
            if float(self.r.get(key) or 0) >= cap:
                raise BudgetExceeded("daily_quota", key)

    def add(self, principal: str, tenant: str, usd: float) -> None:
        pipe = self.r.pipeline()
        for key, _ in self._keys(principal, tenant):
            pipe.incrbyfloat(key, usd)
            pipe.expire(key, 172800)
        pipe.execute()


class RunBudget:
    def __init__(self, limits: Limits, pricing: dict, quota: SpendQuota, principal: str, tenant: str):
        self.limits = limits
        self.pricing = pricing
        self.quota = quota
        self.principal = principal
        self.tenant = tenant
        self.started = time.monotonic()
        self.turns = 0
        self.tokens = 0
        self.cost = 0.0
        self.subagents = 0
        self._calls: deque[float] = deque()

    def remaining_seconds(self) -> float:
        return max(0.0, self.limits.max_wall_seconds - (time.monotonic() - self.started))

    def check_turn(self) -> None:
        self.turns += 1
        if self.turns > self.limits.max_turns:
            raise BudgetExceeded("max_turns")
        if self.remaining_seconds() <= 0:
            raise BudgetExceeded("max_wall_seconds")
        if self.tokens >= self.limits.max_tokens:
            raise BudgetExceeded("max_tokens")
        if self.cost >= self.limits.max_cost_usd:
            raise BudgetExceeded("max_cost_usd")
        self.quota.check(self.principal, self.tenant)

    def charge_usage(self, usage) -> None:
        p = self.pricing
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
        usd = (
            usage.input_tokens * p["input_per_mtok"]
            + usage.output_tokens * p["output_per_mtok"]
            + cache_read * p["cache_read_per_mtok"]
            + cache_write * p["cache_write_per_mtok"]
        ) / 1_000_000
        self.tokens += usage.input_tokens + usage.output_tokens + cache_read + cache_write
        self.cost += usd
        self.quota.add(self.principal, self.tenant, usd)
        if self.tokens > self.limits.max_tokens:
            raise BudgetExceeded("max_tokens")
        if self.cost > self.limits.max_cost_usd:
            raise BudgetExceeded("max_cost_usd")

    def charge_tool_call(self) -> None:
        now = time.monotonic()
        while self._calls and now - self._calls[0] > 60:
            self._calls.popleft()
        if len(self._calls) >= self.limits.max_tool_calls_per_minute:
            raise BudgetExceeded("max_tool_calls_per_minute")
        self._calls.append(now)
        if self.remaining_seconds() <= 0:
            raise BudgetExceeded("max_wall_seconds")

    def charge_subagent(self) -> None:
        if self.subagents >= self.limits.max_subagents:
            raise BudgetExceeded("max_subagents")
        self.subagents += 1

    def http_timeout(self, cap: float = 30.0) -> float:
        remaining = self.remaining_seconds()
        if remaining <= 0:
            raise BudgetExceeded("max_wall_seconds")
        return min(cap, remaining)
