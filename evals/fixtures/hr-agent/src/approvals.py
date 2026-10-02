"""Approval records for consequential tool calls.

An approval is bound to one agent instance, one operation, one target and the SHA-256 of
the canonical arguments. Only the employee on whose behalf the run acts may approve, they
see a rendered description of the exact action, and each approval is consumed once.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from typing import Any

import asyncpg

from .audit import RunContext


class ApprovalInvalid(Exception):
    pass


def args_digest(args: dict[str, Any]) -> str:
    canonical = json.dumps(args, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def describe(operation: str, target: str, args: dict[str, Any]) -> str:
    if operation == "hris/file_leave_request":
        return (f"Submit a {args['leave_type']} leave request from {args['start_date']} to {args['end_date']} "
                f"for {target}. Your manager will be asked to approve it in HRIS.")
    if operation == "helpdesk/create_ticket":
        return f"Send this summary to an HR advisor ({args['category']}):\n\n{args['summary']}"
    raise ValueError(operation)


class ApprovalStore:
    def __init__(self, pool: asyncpg.Pool, ttl_seconds: int):
        self._pool = pool
        self._ttl = timedelta(seconds=ttl_seconds)

    async def request(self, ctx: RunContext, operation: str, target: str, args: dict[str, Any], tool_use_id: str) -> tuple[str, str]:
        approval_id = str(uuid.uuid4())
        text = describe(operation, target, args)
        await self._pool.execute(
            """INSERT INTO approvals.grants
                 (approval_id, run_id, agent_instance_id, subject, operation, target, args_sha256, args,
                  tool_use_id, description, requested_at, expires_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, now(), now() + $11)""",
            approval_id, ctx.run_id, ctx.agent_instance_id, ctx.subject, operation, target,
            args_digest(args), json.dumps(args), tool_use_id, text, self._ttl,
        )
        return approval_id, text

    async def confirm(self, approval_id: str, approver: str) -> None:
        """Called from the employee's authenticated session. Approver must be the run's subject."""
        row = await self._pool.fetchrow(
            """UPDATE approvals.grants SET approved_by = $2, approved_at = now()
                WHERE approval_id = $1 AND subject = $2 AND approved_at IS NULL AND expires_at > now()
                RETURNING approval_id""",
            approval_id, approver,
        )
        if row is None:
            raise ApprovalInvalid("not found, expired, already decided, or approver lacks authority")

    async def consume(self, ctx: RunContext, approval_id: str, operation: str, target: str, args: dict[str, Any]) -> dict[str, Any]:
        """Atomically mark the approval used. Every binding is re-checked in the same statement."""
        row = await self._pool.fetchrow(
            """UPDATE approvals.grants SET used_at = now()
                WHERE approval_id = $1
                  AND used_at IS NULL
                  AND approved_at IS NOT NULL
                  AND approved_by = subject
                  AND expires_at > now()
                  AND agent_instance_id = $2
                  AND subject = $3
                  AND operation = $4
                  AND target = $5
                  AND args_sha256 = $6
                RETURNING approval_id, approved_by, approved_at, expires_at""",
            approval_id, ctx.agent_instance_id, ctx.subject, operation, target, args_digest(args),
        )
        if row is None:
            raise ApprovalInvalid("approval does not match this action, was used, or expired")
        return dict(row)

    async def pending(self, approval_id: str) -> dict[str, Any] | None:
        row = await self._pool.fetchrow(
            "SELECT run_id, operation, target, args, tool_use_id FROM approvals.grants WHERE approval_id = $1",
            approval_id,
        )
        if row is None:
            return None
        out = dict(row)
        out["args"] = json.loads(out["args"])
        return out
