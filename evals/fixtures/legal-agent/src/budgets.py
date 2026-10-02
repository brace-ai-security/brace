"""Run budgets and shared quotas, enforced by the harness around every model and tool call."""
from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass, field

import redis

from src.config import settings

_cfg = settings["budgets"]
_redis = redis.Redis.from_url(settings["cache"]["redis_url"])


class BudgetExceeded(RuntimeError):
    def __init__(self, limit: str):
        super().__init__(limit)
        self.limit = limit


@dataclass
class RunBudget:
    user_id: str
    matter_id: str
    started: float = field(default_factory=time.monotonic)
    steps: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    subagents: int = 0
    _tool_calls: deque = field(default_factory=deque)

    def check_time(self) -> None:
        if time.monotonic() - self.started > _cfg["max_run_seconds"]:
            raise BudgetExceeded("run_seconds")

    def on_step(self) -> None:
        self.steps += 1
        if self.steps > _cfg["max_graph_steps"]:
            raise BudgetExceeded("graph_steps")
        self.check_time()

    def on_tool_call(self) -> None:
        now = time.monotonic()
        while self._tool_calls and now - self._tool_calls[0] > 60:
            self._tool_calls.popleft()
        if len(self._tool_calls) >= _cfg["max_tool_calls_per_minute"]:
            raise BudgetExceeded("tool_call_rate")
        self._tool_calls.append(now)
        self.check_time()

    def on_subagent(self) -> None:
        self.subagents += 1
        if self.subagents > _cfg["max_subagents"]:
            raise BudgetExceeded("subagents")

    def reserve_model_call(self, prompt_tokens: int, max_completion: int, usd_estimate: float) -> None:
        """Check before the call that the worst case fits every limit."""
        self.check_time()
        if self.prompt_tokens + prompt_tokens > _cfg["max_prompt_tokens_per_run"]:
            raise BudgetExceeded("prompt_tokens")
        if self.completion_tokens + max_completion > _cfg["max_completion_tokens_per_run"]:
            raise BudgetExceeded("completion_tokens")
        if self.cost_usd + usd_estimate > _cfg["max_cost_usd_per_run"]:
            raise BudgetExceeded("run_cost")
        _charge_quotas(self.user_id, self.matter_id, usd_estimate)

    def settle_model_call(self, prompt_tokens: int, completion_tokens: int, usd: float) -> None:
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.cost_usd += usd


_RATE_LUA = """
local limits = cjson.decode(ARGV[1])
for i, key in ipairs(KEYS) do
  local cur = tonumber(redis.call('GET', key) or '0')
  if cur + 1 > tonumber(limits[i]) then return i end
end
for i, key in ipairs(KEYS) do
  redis.call('INCR', key)
  redis.call('EXPIRE', key, 120)
end
return 0
"""
_rate_script = _redis.register_script(_RATE_LUA)


def admit_run(user_id: str, matter_id: str) -> None:
    """Atomically count a new run against per-user, per-matter, and fleet per-minute run rates."""
    minute = time.strftime("%Y%m%d%H%M", time.gmtime())
    r = _cfg["rates"]
    keys = [f"rate:user:{user_id}:{minute}", f"rate:matter:{matter_id}:{minute}", f"rate:fleet:{minute}"]
    hit = _rate_script(keys=keys, args=[json.dumps([r["per_user_runs_per_minute"],
                                                    r["per_matter_runs_per_minute"],
                                                    r["fleet_runs_per_minute"]])])
    if hit:
        raise BudgetExceeded(["user_rate", "matter_rate", "fleet_rate"][int(hit) - 1])


_QUOTA_LUA = """
local limits = cjson.decode(ARGV[2])
for i, key in ipairs(KEYS) do
  local cur = tonumber(redis.call('GET', key) or '0')
  if cur + tonumber(ARGV[1]) > tonumber(limits[i]) then return i end
end
for i, key in ipairs(KEYS) do
  redis.call('INCRBYFLOAT', key, ARGV[1])
  redis.call('EXPIRE', key, 172800)
end
return 0
"""
_quota_script = _redis.register_script(_QUOTA_LUA)


def _charge_quotas(user_id: str, matter_id: str, usd: float) -> None:
    """Atomically charge per-user, per-matter, and fleet daily spend, or refuse."""
    day = time.strftime("%Y%m%d", time.gmtime())
    q = _cfg["quotas"]
    keys = [f"quota:user:{user_id}:{day}", f"quota:matter:{matter_id}:{day}", f"quota:fleet:{day}"]
    limits = [q["per_user_daily_usd"], q["per_matter_daily_usd"], q["fleet_daily_usd"]]
    hit = _quota_script(keys=keys, args=[f"{usd:.6f}", json.dumps(limits)])
    if hit:
        raise BudgetExceeded(["user_daily", "matter_daily", "fleet_daily"][int(hit) - 1])
