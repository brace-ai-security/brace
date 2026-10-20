"""Hard execution budgets, enforced by the harness and not by the model.

Per run: step count, wall-clock time, tokens, cost, tool-call rate, and
number of sub-agents. Sub-agents charge the parent's budget, so a child
cannot widen what the parent was given.

Across runs: daily spend and per-minute run starts per user, per tenant
(business unit), and for the whole fleet. Quotas are reserved in Postgres
inside one transaction, so concurrent runs cannot overshoot them.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal

from app.identity import RunIdentity


class BudgetExceeded(Exception):
    def __init__(self, limit: str, used, allowed):
        super().__init__(f"{limit} exceeded: used={used} allowed={allowed}")
        self.limit = limit
        self.used = used
        self.allowed = allowed


# USD per million tokens, from the provider price sheet referenced in the manifest.
PRICES = {
    "claude-sonnet-4-5-20250929": (Decimal("3.00"), Decimal("15.00")),
    "claude-haiku-4-5-20251001": (Decimal("1.00"), Decimal("5.00")),
}


@dataclass
class Budget:
    ident: RunIdentity
    max_steps: int
    max_wall_seconds: float
    max_tokens: int
    max_cost_usd: Decimal
    max_tool_calls_per_minute: int
    max_subagents: int
    quotas_daily_usd: dict[str, Decimal]
    run_starts_per_minute: dict[str, int]
    started_at: float = field(default_factory=time.monotonic)
    steps: int = 0
    tokens: int = 0
    cost_usd: Decimal = Decimal("0")
    unflushed_cost_usd: Decimal = Decimal("0")
    subagents: int = 0
    _tool_calls: deque = field(default_factory=deque)

    @classmethod
    def for_run(cls, cfg: dict, ident: RunIdentity) -> "Budget":
        run = cfg["per_run"]
        return cls(
            ident=ident,
            max_steps=int(run["max_steps"]),
            max_wall_seconds=float(run["max_wall_seconds"]),
            max_tokens=int(run["max_tokens"]),
            max_cost_usd=Decimal(str(run["max_cost_usd"])),
            max_tool_calls_per_minute=int(run["max_tool_calls_per_minute"]),
            max_subagents=int(run["max_subagents"]),
            quotas_daily_usd={k: Decimal(str(v)) for k, v in cfg["quotas_daily_usd"].items()},
            run_starts_per_minute={k: int(v) for k, v in cfg["run_starts_per_minute"].items()},
        )

    def _scopes(self) -> list[tuple[str, str]]:
        return [
            ("user", self.ident.accountable_party),
            ("tenant", self.ident.tenant),
            ("fleet", "all"),
        ]

    # --- per-run limits -------------------------------------------------

    def check_step(self) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise BudgetExceeded("max_steps", self.steps, self.max_steps)
        elapsed = time.monotonic() - self.started_at
        if elapsed > self.max_wall_seconds:
            raise BudgetExceeded("max_wall_seconds", round(elapsed, 1), self.max_wall_seconds)

    def charge_model(self, model: str, usage) -> None:
        price_in, price_out = PRICES[model]
        tokens_in = (
            int(usage.input_tokens or 0)
            + int(getattr(usage, "cache_read_input_tokens", 0) or 0)
            + int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        )
        tokens_out = int(usage.output_tokens or 0)
        self.tokens += tokens_in + tokens_out
        cost = (price_in * tokens_in + price_out * tokens_out) / Decimal(1_000_000)
        self.cost_usd += cost
        self.unflushed_cost_usd += cost
        if self.tokens > self.max_tokens:
            raise BudgetExceeded("max_tokens", self.tokens, self.max_tokens)
        if self.cost_usd > self.max_cost_usd:
            raise BudgetExceeded("max_cost_usd", self.cost_usd, self.max_cost_usd)

    def check_tool_call(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        while self._tool_calls and now - self._tool_calls[0] > 60:
            self._tool_calls.popleft()
        if len(self._tool_calls) >= self.max_tool_calls_per_minute:
            raise BudgetExceeded(
                "max_tool_calls_per_minute", len(self._tool_calls) + 1, self.max_tool_calls_per_minute
            )
        self._tool_calls.append(now)

    def check_subagent(self) -> None:
        if self.subagents >= self.max_subagents:
            raise BudgetExceeded("max_subagents", self.subagents + 1, self.max_subagents)
        self.subagents += 1

    # --- cross-run quotas -----------------------------------------------

    async def reserve_run_start(self, pool) -> None:
        async with pool.acquire() as conn:
            async with conn.transaction():
                for scope, key in self._scopes():
                    limit = self.run_starts_per_minute[scope]
                    count = await conn.fetchval(
                        """
                        INSERT INTO run_start_window (scope, key, minute, starts)
                        VALUES ($1, $2, date_trunc('minute', now()), 1)
                        ON CONFLICT (scope, key, minute)
                        DO UPDATE SET starts = run_start_window.starts + 1
                        RETURNING starts
                        """,
                        scope,
                        key,
                    )
                    if count > limit:
                        raise BudgetExceeded(f"run_starts_per_minute.{scope}", count, limit)

    async def flush(self, pool) -> None:
        """Add this run's unflushed spend to the daily quotas, or stop the run."""
        if self.unflushed_cost_usd <= 0:
            return
        amount = self.unflushed_cost_usd
        async with pool.acquire() as conn:
            async with conn.transaction():
                for scope, key in self._scopes():
                    limit = self.quotas_daily_usd[scope]
                    spent = await conn.fetchval(
                        """
                        INSERT INTO spend_quota (scope, key, day, spent_usd)
                        VALUES ($1, $2, current_date, $3)
                        ON CONFLICT (scope, key, day)
                        DO UPDATE SET spent_usd = spend_quota.spent_usd + EXCLUDED.spent_usd
                        RETURNING spent_usd
                        """,
                        scope,
                        key,
                        amount,
                    )
                    if spent > limit:
                        raise BudgetExceeded(f"quota_daily_usd.{scope}", spent, limit)
        self.unflushed_cost_usd = Decimal("0")
