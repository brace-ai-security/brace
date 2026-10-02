"""Append-only audit records. Every record carries the six identity fields."""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

import asyncpg
from opentelemetry import trace

from .redact import redact_obj

log = logging.getLogger("hr_agent.audit")


@dataclass(frozen=True)
class RunContext:
    """Built by the harness from verified identity. Never from model output."""

    run_id: str
    agent_instance_id: str
    agent_type_id: str
    tenant: str
    subject: str              # employee whose authority is being used (verified SSO token)
    accountable_party: str
    operational_owner: str
    agent_principal: str      # workload identity of this agent


class AuditUnavailable(Exception):
    pass


_INSERT = """
INSERT INTO audit.events (
    event_id, ts, event_type, run_id, step_id, parent_step_id,
    accountable_party, operational_owner, tenant, agent_type_id, agent_instance_id,
    trace_id, span_id, traceparent,
    delegated_subject, agent_principal,
    tool, operation_target, decision, reason, policy_version, approval_id,
    args_redacted, result_redacted, context_tokens, context_tokens_method, model_requested, model_served
) VALUES (
    $1, now(), $2, $3, $4, $5,
    $6, $7, $8, $9, $10,
    $11, $12, $13,
    $14, $15,
    $16, $17, $18, $19, $20, $21,
    $22::jsonb, $23::jsonb, $24, $25, $26, $27
)
"""


class AuditWriter:
    def __init__(self, pool: asyncpg.Pool, policy_version: str):
        self._pool = pool
        self._policy_version = policy_version

    async def record(
        self,
        ctx: RunContext,
        event_type: str,
        *,
        step_id: str | None = None,
        parent_step_id: str | None = None,
        tool: str | None = None,
        target: str | None = None,
        decision: str | None = None,
        reason: str | None = None,
        approval_id: str | None = None,
        args: Any = None,
        result: Any = None,
        context_tokens: int | None = None,
        context_tokens_method: str | None = None,
        model_requested: str | None = None,
        model_served: str | None = None,
    ) -> str:
        span_ctx = trace.get_current_span().get_span_context()
        if not span_ctx.is_valid:
            raise AuditUnavailable("no active trace context")
        trace_id = format(span_ctx.trace_id, "032x")
        span_id = format(span_ctx.span_id, "016x")
        traceparent = f"00-{trace_id}-{span_id}-{span_ctx.trace_flags:02x}"
        event_id = str(uuid.uuid4())
        try:
            await self._pool.execute(
                _INSERT,
                event_id, event_type, ctx.run_id, step_id, parent_step_id,
                ctx.accountable_party, ctx.operational_owner, ctx.tenant, ctx.agent_type_id, ctx.agent_instance_id,
                trace_id, span_id, traceparent,
                ctx.subject, ctx.agent_principal,
                tool, target, decision, reason, self._policy_version, approval_id,
                json.dumps(redact_obj(args)), json.dumps(redact_obj(result)),
                context_tokens, context_tokens_method, model_requested, model_served,
                timeout=2.0,
            )
        except Exception as exc:  # any failure to persist stops the run
            log.error("audit write failed", extra={"event_type": event_type, "run_id": ctx.run_id})
            raise AuditUnavailable(str(type(exc).__name__)) from exc
        return event_id
