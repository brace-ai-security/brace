"""Execution audit.

Every step of a run is written as a node in an execution graph: proposals, tool calls,
authorization decisions, approvals, results, and errors. Records go to the audit topic, which is
write-only for this service's identity; the security team owns read and retention.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from opentelemetry import trace

from src.config import settings
from src.identity import AGENT_TYPE_ID

_tracer = trace.get_tracer("counsel-research")

REQUIRED = (
    "accountable_party",
    "operational_owner",
    "tenant",
    "agent_type_id",
    "agent_instance_id",
    "trace_id",
)

STEP_KINDS = {"proposal", "tool_call", "decision", "approval", "result", "error", "context"}


class AuditUnavailable(RuntimeError):
    pass


@dataclass
class RunContext:
    """Identity for one run. Built by the harness from the verified session, never from model output."""

    instance_id: str
    tenant: str  # matter id
    delegated_subject: str  # the lawyer whose authority the run uses
    trace_id: str
    span_id: str
    accountable_party: str = settings["service"]["accountable_party"]
    operational_owner: str = settings["service"]["operational_owner"]
    agent_type_id: str = AGENT_TYPE_ID
    policy_version: str = settings["service"]["policy_version"]
    last_step: str | None = None
    steps: list[str] = field(default_factory=list)

    def identity(self) -> dict[str, str]:
        return {
            "accountable_party": self.accountable_party,
            "operational_owner": self.operational_owner,
            "tenant": self.tenant,
            "agent_type_id": self.agent_type_id,
            "agent_instance_id": self.instance_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "delegated_subject": self.delegated_subject,
        }


class AuditSink:
    def __init__(self, producer):
        self._producer = producer

    def write(self, record: dict[str, Any]) -> None:
        missing = [k for k in REQUIRED if not record.get(k)]
        if missing:
            raise AuditUnavailable(f"audit record missing {missing}")
        try:
            fut = self._producer.send("agent-audit", json.dumps(record).encode())
            fut.get(timeout=5)
        except Exception as exc:  # delivery failure must stop the step that needed it
            raise AuditUnavailable("audit delivery failed") from exc


_sink: AuditSink | None = None


def configure(producer) -> None:
    global _sink
    _sink = AuditSink(producer)


def step(ctx: RunContext, kind: str, name: str, *, parent: str | None = None, **data: Any) -> str:
    """Record one step and return its id. Raises AuditUnavailable if it cannot be recorded."""
    if kind not in STEP_KINDS:
        raise ValueError(kind)
    if _sink is None:
        raise AuditUnavailable("audit sink not configured")
    step_id = str(uuid.uuid4())
    record = {
        **ctx.identity(),
        "step_id": step_id,
        "parent_step_id": parent or ctx.last_step,
        "kind": kind,
        "name": name,
        "policy_version": ctx.policy_version,
        "ts": time.time(),
        **data,
    }
    _sink.write(record)
    ctx.last_step = step_id
    ctx.steps.append(step_id)
    return step_id
