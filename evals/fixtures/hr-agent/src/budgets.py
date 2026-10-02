"""Hard limits enforced by the harness, outside the model."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import asyncpg

from .audit import RunContext


class BudgetExceeded(Exception):
    def __init__(self, limit: str):
        super().__init__(limit)
        self.limit = limit


@dataclass
class RunBudget:
    cfg: dict[str, Any]
    pricing: dict[str, float]
    started: float = field(default_factory=time.monotonic)
    steps: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    tool_calls: deque = field(default_factory=deque)

    def check_step(self) -> None:
        if self.steps >= self.cfg["max_steps"]:
            raise BudgetExceeded("max_steps")
        if time.monotonic() - self.started > self.cfg["max_wall_seconds"]:
            raise BudgetExceeded("max_wall_seconds")
        if self.tokens >= self.cfg["max_total_tokens"]:
            raise BudgetExceeded("max_total_tokens")
        if self.cost_usd >= self.cfg["max_cost_usd"]:
            raise BudgetExceeded("max_cost_usd")
        self.steps += 1

    def remaining_seconds(self) -> float:
        return max(0.0, self.cfg["max_wall_seconds"] - (time.monotonic() - self.started))

    def record_usage(self, usage: Any) -> tuple[int, float]:
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
        tokens_in = usage.input_tokens + cache_read + cache_write
        tokens = tokens_in + usage.output_tokens
        cost = (
            (usage.input_tokens + cache_write) * self.pricing["input_per_mtok"]
            + cache_read * self.pricing["cache_read_per_mtok"]
            + usage.output_tokens * self.pricing["output_per_mtok"]
        ) / 1_000_000
        self.tokens += tokens
        self.cost_usd += cost
        return tokens, cost

    def check_tool_call(self) -> None:
        now = time.monotonic()
        while self.tool_calls and now - self.tool_calls[0] > 60:
            self.tool_calls.popleft()
        if len(self.tool_calls) >= self.cfg["max_tool_calls_per_minute"]:
            raise BudgetExceeded("max_tool_calls_per_minute")
        self.tool_calls.append(now)

    def check_subagent(self, started_so_far: int) -> None:
        if started_so_far >= self.cfg["max_subagents"]:
            raise BudgetExceeded("max_subagents")


_WINDOW = "to_timestamp(floor(extract(epoch FROM now()) / $3) * $3)"

_RESERVE_RUN = f"""
INSERT INTO quota.usage (scope, key, window_start, runs, tokens, cost_usd)
VALUES ($1, $2, {_WINDOW}, 1, 0, 0)
ON CONFLICT (scope, key, window_start) DO UPDATE
   SET runs = quota.usage.runs + 1
 WHERE quota.usage.runs + 1 <= $4
   AND quota.usage.tokens < $5
   AND quota.usage.cost_usd < $6
RETURNING runs
"""

_RECORD_USAGE = f"""
INSERT INTO quota.usage (scope, key, window_start, runs, tokens, cost_usd)
VALUES ($1, $2, {_WINDOW}, 0, $4, $5)
ON CONFLICT (scope, key, window_start) DO UPDATE
   SET tokens = quota.usage.tokens + EXCLUDED.tokens,
       cost_usd = quota.usage.cost_usd + EXCLUDED.cost_usd
RETURNING tokens, cost_usd
"""


class QuotaStore:
    """Per-user, per-tenant and fleet-wide quotas, shared by every replica."""

    def __init__(self, pool: asyncpg.Pool, quotas: list[dict[str, Any]]):
        self._pool = pool
        self._quotas = quotas

    def _key(self, scope: str, ctx: RunContext) -> str:
        return {"user": ctx.subject, "tenant": ctx.tenant, "fleet": "all"}[scope]

    async def reserve_run(self, ctx: RunContext) -> None:
        async with self._pool.acquire() as conn, conn.transaction():
            for q in self._quotas:
                row = await conn.fetchrow(
                    _RESERVE_RUN, q["scope"], self._key(q["scope"], ctx), q["window_seconds"],
                    q["max_runs"], q["max_tokens"], q["max_cost_usd"],
                )
                if row is None:
                    raise BudgetExceeded(f"quota:{q['scope']}")

    async def record_usage(self, ctx: RunContext, tokens: int, cost_usd: float) -> None:
        """Usage already spent is always recorded; the run stops once any window is over its limit."""
        exceeded: str | None = None
        async with self._pool.acquire() as conn, conn.transaction():
            for q in self._quotas:
                row = await conn.fetchrow(
                    _RECORD_USAGE, q["scope"], self._key(q["scope"], ctx), q["window_seconds"], tokens, cost_usd
                )
                if row["tokens"] >= q["max_tokens"] or row["cost_usd"] >= q["max_cost_usd"]:
                    exceeded = exceeded or f"quota:{q['scope']}"
        if exceeded:
            raise BudgetExceeded(exceeded)
