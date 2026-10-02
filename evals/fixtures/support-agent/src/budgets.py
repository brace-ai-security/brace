"""Run and tenant limits enforced by the harness, outside the model."""
import os
import time
from dataclasses import dataclass, field

import redis

_redis = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))

# USD per million tokens for the configured model.
INPUT_PRICE = 3.0
OUTPUT_PRICE = 15.0


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class RunBudget:
    max_steps: int
    max_wall_seconds: float
    max_total_tokens: int
    max_tool_calls_per_minute: int
    steps: int = 0
    tokens: int = 0
    started: float = field(default_factory=time.monotonic)
    tool_call_times: list[float] = field(default_factory=list)

    @classmethod
    def from_config(cls, cfg: dict) -> "RunBudget":
        return cls(
            max_steps=cfg["max_steps"],
            max_wall_seconds=cfg["max_wall_seconds"],
            max_total_tokens=cfg["max_total_tokens"],
            max_tool_calls_per_minute=cfg["max_tool_calls_per_minute"],
        )

    def check_step(self) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise BudgetExceeded(f"step limit {self.max_steps}")
        if time.monotonic() - self.started > self.max_wall_seconds:
            raise BudgetExceeded(f"wall clock limit {self.max_wall_seconds}s")
        if self.tokens > self.max_total_tokens:
            raise BudgetExceeded(f"token limit {self.max_total_tokens}")

    def add_tokens(self, n: int) -> None:
        self.tokens += n

    def check_tool_call(self) -> None:
        now = time.monotonic()
        self.tool_call_times = [t for t in self.tool_call_times if now - t < 60]
        if len(self.tool_call_times) >= self.max_tool_calls_per_minute:
            raise BudgetExceeded("tool call rate limit")
        self.tool_call_times.append(now)


class TenantQuota:
    """Daily spend caps per tenant and across the whole fleet, shared through Redis."""

    def __init__(self, tenant_id: str, cfg: dict):
        day = time.strftime("%Y-%m-%d")
        self.tenant_key = f"spend:{day}:tenant:{tenant_id}"
        self.fleet_key = f"spend:{day}:fleet:support-agent"
        self.tenant_cap = cfg["tenant_daily_cost_usd"]
        self.fleet_cap = cfg["fleet_daily_cost_usd"]

    def check(self) -> None:
        tenant = float(_redis.get(self.tenant_key) or 0)
        fleet = float(_redis.get(self.fleet_key) or 0)
        if tenant >= self.tenant_cap:
            raise BudgetExceeded("tenant daily spend cap")
        if fleet >= self.fleet_cap:
            raise BudgetExceeded("fleet daily spend cap")

    def add_usage(self, usage) -> None:
        cost = (usage.input_tokens * INPUT_PRICE + usage.output_tokens * OUTPUT_PRICE) / 1_000_000
        pipe = _redis.pipeline()
        pipe.incrbyfloat(self.tenant_key, cost).expire(self.tenant_key, 172800)
        pipe.incrbyfloat(self.fleet_key, cost).expire(self.fleet_key, 172800)
        pipe.execute()
