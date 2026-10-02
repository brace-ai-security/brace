"""Operator stop control.

Operators halt the fleet or one business unit by setting a row in
``control_flags`` with the ``procurement_ops`` database role (see
ops/README in the platform runbook). The agent's own database role has
SELECT only on this table, so the agent cannot clear or delay a halt.
"""
from __future__ import annotations


class AgentHalted(Exception):
    pass


_QUERY = """
SELECT scope, reason, set_by, set_at
FROM control_flags
WHERE halted
  AND (scope = 'fleet' OR scope = $1)
ORDER BY CASE WHEN scope = 'fleet' THEN 0 ELSE 1 END
LIMIT 1
"""


async def assert_running(pool, tenant: str) -> None:
    row = await pool.fetchrow(_QUERY, f"tenant:{tenant}")
    if row is not None:
        raise AgentHalted(
            f"halted by {row['set_by']} at {row['set_at'].isoformat()} "
            f"(scope={row['scope']}): {row['reason']}"
        )
