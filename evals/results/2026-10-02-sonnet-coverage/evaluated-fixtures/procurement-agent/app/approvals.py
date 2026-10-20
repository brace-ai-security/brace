"""Approval requests and decisions for high-impact operations.

Requests are posted to the business unit's approvals channel in Slack with
the full argument summary. Approvers decide with the Slack buttons; the
interactive callback is signature-checked in main.py and then calls
``decide``. Approver authority is checked against the role map in policy.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.audit import digest, summarize_args
from app.identity import RunIdentity


@dataclass(frozen=True)
class Approval:
    id: str
    approver: str
    approver_role: str
    expires_at: datetime


class ApproverNotAuthorized(Exception):
    pass


class ApprovalStore:
    def __init__(self, pool, policy: dict, notifier):
        self.pool = pool
        self.ttl = timedelta(minutes=int(policy["approvals"]["ttl_minutes"]))
        self.approver_roles: dict[str, list[str]] = policy["approvals"]["approver_roles"]
        self.notifier = notifier

    async def request(self, ident: RunIdentity, tool: str, target: str, args: dict[str, Any]) -> str:
        approval_id = f"apr-{uuid.uuid4()}"
        expires_at = datetime.now(timezone.utc) + self.ttl
        await self.pool.execute(
            """
            INSERT INTO approvals (
                id, tool, target, args_sha256, args_summary, tenant,
                requested_by_instance, requested_by_run, delegated_subject,
                status, requested_at, expires_at
            ) VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9, 'pending', now(), $10)
            """,
            approval_id,
            tool,
            target,
            digest(args),
            json.dumps(summarize_args(args)),
            ident.tenant,
            ident.agent_instance_id,
            ident.run_id,
            ident.delegated_subject,
            expires_at,
        )
        await self.notifier.post_approval_request(
            tenant=ident.tenant,
            approval_id=approval_id,
            tool=tool,
            target=target,
            summary=summarize_args(args),
            expires_at=expires_at,
        )
        return approval_id

    async def find_valid(self, ident: RunIdentity, tool: str, target: str) -> Approval | None:
        row = await self.pool.fetchrow(
            """
            SELECT id, approver, approver_role, expires_at
            FROM approvals
            WHERE tool = $1
              AND target = $2
              AND tenant = $3
              AND status = 'approved'
              AND expires_at > now()
            ORDER BY decided_at DESC
            LIMIT 1
            """,
            tool,
            target,
            ident.tenant,
        )
        if row is None:
            return None
        if row["approver_role"] not in self.approver_roles.get(tool, []):
            return None
        return Approval(row["id"], row["approver"], row["approver_role"], row["expires_at"])

    async def decide(self, approval_id: str, approver: str, approver_role: str, approve: bool) -> None:
        row = await self.pool.fetchrow(
            "SELECT tool, status, expires_at FROM approvals WHERE id = $1", approval_id
        )
        if row is None or row["status"] != "pending":
            raise ValueError("approval is not pending")
        if row["expires_at"] <= datetime.now(timezone.utc):
            raise ValueError("approval request expired")
        if approver_role not in self.approver_roles.get(row["tool"], []):
            raise ApproverNotAuthorized(f"{approver_role} cannot approve {row['tool']}")
        await self.pool.execute(
            """
            UPDATE approvals
            SET status = $2, approver = $3, approver_role = $4, decided_at = now()
            WHERE id = $1 AND status = 'pending'
            """,
            approval_id,
            "approved" if approve else "rejected",
            approver,
            approver_role,
        )
