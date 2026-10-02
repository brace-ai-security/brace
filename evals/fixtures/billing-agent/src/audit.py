"""Audit events and redaction."""
from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any

import httpx

from .identity import RunContext

log = logging.getLogger("billing_agent.audit")

_SECRET_PATTERNS = [
    re.compile(r"sk-ant-api03-[A-Za-z0-9_\-]{80,}"),
    re.compile(r"sk_live_[A-Za-z0-9]{24,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9\-_\.=]+"),
    re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
    re.compile(r"postgres(?:ql)?://[^\s'\"]+"),
]


def redact(value: Any) -> Any:
    if isinstance(value, str):
        for pat in _SECRET_PATTERNS:
            value = pat.sub("[REDACTED]", value)
        return value
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


class AuditLog:
    def __init__(self, collector_url: str, policy_version: str):
        self.url = collector_url
        self.policy_version = policy_version
        self.http = httpx.Client(timeout=5.0)

    def record(self, ctx: RunContext, event: str, **fields: Any) -> str:
        event_id = uuid.uuid4().hex
        body = {
            "event_id": event_id,
            "event": event,
            "ts": time.time(),
            "policy_version": self.policy_version,
            "accountable_party": ctx.accountable_party,
            "operational_owner": ctx.operational_owner,
            "tenant_id": ctx.tenant_id,
            "agent_type_id": ctx.agent_type_id,
            "agent_instance_id": ctx.agent_instance_id,
            "parent_instance_id": ctx.parent_instance_id,
            "trace_id": ctx.trace_id,
            **redact(fields),
        }
        try:
            r = self.http.post(self.url, json=body)
            r.raise_for_status()
        except httpx.HTTPError:
            log.exception("audit delivery failed for %s (%s)", event, event_id)
        return event_id
