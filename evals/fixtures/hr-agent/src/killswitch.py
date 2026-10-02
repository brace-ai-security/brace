"""Stop control. Flags live in control.stop_flags, which the agent's DB role can only read.

Operators set flags with the hr_agent_operator role (see README "Stopping the agent").
The tool gateway reads the same table, so a stopped instance is refused there too.
"""
from __future__ import annotations

import asyncio
import logging

import asyncpg

from .audit import RunContext

log = logging.getLogger("hr_agent.stop")

_QUERY = """
SELECT reason FROM control.stop_flags
WHERE active
  AND (   scope = 'fleet'
       OR (scope = 'agent_type'     AND value = $1)
       OR (scope = 'agent_instance' AND value = $2)
       OR (scope = 'subject'        AND value = $3)
       OR (scope = 'agent_principal' AND value = $4))
LIMIT 1
"""


class Stopped(Exception):
    pass


class StopControl:
    def __init__(self, pool: asyncpg.Pool, poll_seconds: float):
        self._pool = pool
        self._poll = poll_seconds

    async def reason(self, ctx: RunContext) -> str | None:
        try:
            row = await self._pool.fetchrow(
                _QUERY, ctx.agent_type_id, ctx.agent_instance_id, ctx.subject, ctx.agent_principal, timeout=1.0
            )
        except Exception:
            return "stop store unreachable"
        return row["reason"] if row else None

    async def raise_if_stopped(self, ctx: RunContext) -> None:
        why = await self.reason(ctx)
        if why:
            raise Stopped(why)

    async def watch(self, ctx: RunContext, task: asyncio.Task) -> None:
        """Cancel the run task, including any in-flight model or tool call, once a flag appears."""
        while not task.done():
            why = await self.reason(ctx)
            if why:
                log.warning("stop flag observed", extra={"run_id": ctx.run_id, "reason": why})
                task.cancel(msg=f"stopped: {why}")
                return
            await asyncio.sleep(self._poll)
