"""Approval requests for actions the agent may not take on its own."""
from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import asdict, dataclass

import redis

from src.config import settings

_r = redis.Redis.from_url(settings["memory"]["redis_url"])
APPROVAL_TTL_SECONDS = 1800


@dataclass
class Approval:
    approval_id: str
    matter_id: str
    instance_id: str
    operation: str
    args_digest: str
    summary: str
    requested_by: str
    status: str = "pending"
    approved_by: str | None = None
    approved_at: float | None = None
    expires_at: float | None = None


def _digest(args: dict) -> str:
    return hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()


def request(matter_id: str, instance_id: str, operation: str, args: dict, summary: str, requested_by: str) -> Approval:
    appr = Approval(
        approval_id="apr_" + secrets.token_urlsafe(12),
        matter_id=matter_id,
        instance_id=instance_id,
        operation=operation,
        args_digest=_digest(args),
        summary=summary,
        requested_by=requested_by,
    )
    _r.set(f"approval:{appr.approval_id}", json.dumps(asdict(appr)))
    return appr


def approve(approval_id: str, approver_id: str, approver_role: str) -> Approval:
    raw = _r.get(f"approval:{approval_id}")
    if raw is None:
        raise KeyError(approval_id)
    appr = Approval(**json.loads(raw))
    if approver_role != "partner":
        raise PermissionError("only a partner on the matter may approve")
    if approver_id == appr.requested_by:
        raise PermissionError("requester cannot approve their own request")
    appr.status = "approved"
    appr.approved_by = approver_id
    appr.approved_at = time.time()
    appr.expires_at = appr.approved_at + APPROVAL_TTL_SECONDS
    _r.set(f"approval:{approval_id}", json.dumps(asdict(appr)))
    return appr


def is_approved(approval_id: str, matter_id: str, operation: str) -> bool:
    raw = _r.get(f"approval:{approval_id}")
    if raw is None:
        return False
    appr = Approval(**json.loads(raw))
    return appr.status == "approved" and appr.matter_id == matter_id and appr.operation == operation
