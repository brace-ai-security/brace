"""Execution audit graph.

Every step of a run is one row in ``audit_events``. Rows link to their parent
step, so a run can be rebuilt as a tree: run -> model decision -> proposed
tool call -> authorization decision -> result or error. Writes are
synchronous and are made before the action they describe; if the write
fails, the caller raises and the action does not run.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from opentelemetry import trace

from app.context_size import ContextMeasure
from app.identity import IDENTITY_FIELDS, RunIdentity
from app.redact import redact_value

EVENT_KINDS = {
    "run_started",
    "run_finished",
    "run_halted",
    "model_decision",
    "tool_proposed",
    "authz_decision",
    "approval_requested",
    "approval_decided",
    "tool_result",
    "tool_error",
    "tool_denied",
    "budget_exceeded",
    "subagent_started",
    "subagent_finished",
    "background_job",
}

_INSERT = """
INSERT INTO audit_events (
    node_id, parent_node_id, run_id, ts, kind,
    accountable_party, operational_owner, tenant,
    agent_type_id, agent_instance_id, trace_id, span_id,
    delegated_subject, agent_principal, parent_instance_id,
    policy_version, approval_id, operation_id,
    context_tokens, context_method, context_compacted,
    payload
) VALUES (
    $1, $2, $3, $4, $5,
    $6, $7, $8,
    $9, $10, $11, $12,
    $13, $14, $15,
    $16, $17, $18,
    $19, $20, $21,
    $22::jsonb
)
"""


def summarize_args(args: dict[str, Any]) -> dict[str, Any]:
    """Key arguments for the record, with secrets and account numbers redacted."""
    return {k: redact_value(v) for k, v in args.items()}


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def record(
    pool,
    ident: RunIdentity,
    *,
    kind: str,
    payload: dict[str, Any] | None = None,
    parent: str | None = None,
    context: ContextMeasure | None = None,
    policy_version: str | None = None,
    approval_id: str | None = None,
    operation_id: str | None = None,
) -> str:
    if kind not in EVENT_KINDS:
        raise ValueError(f"unknown audit kind {kind}")
    for name in IDENTITY_FIELDS:
        if not getattr(ident, name):
            raise ValueError(f"audit record missing {name}")
    span_ctx = trace.get_current_span().get_span_context()
    span_id = format(span_ctx.span_id, "016x") if span_ctx.is_valid else None
    node_id = f"node-{uuid.uuid4()}"
    measure = context or ContextMeasure.unavailable()
    await pool.execute(
        _INSERT,
        node_id,
        parent,
        ident.run_id,
        datetime.now(timezone.utc),
        kind,
        ident.accountable_party,
        ident.operational_owner,
        ident.tenant,
        ident.agent_type_id,
        ident.agent_instance_id,
        ident.trace_id,
        span_id,
        ident.delegated_subject,
        ident.agent_principal,
        ident.parent_instance_id,
        policy_version,
        approval_id,
        operation_id,
        measure.tokens,
        measure.method,
        measure.compacted,
        json.dumps(redact_value(payload or {}), default=str),
    )
    return node_id
