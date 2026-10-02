"""Structured audit events to stdout; Fluent Bit ships them to the audit index (write-only role)."""
import json
import sys
from datetime import datetime, timezone

from opentelemetry import trace

from src.telemetry import identity_attrs


def record(instance_id: str, user: str, event: str, details: dict) -> None:
    ctx = trace.get_current_span().get_span_context()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **identity_attrs(instance_id, user),
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
        "details": details,
    }
    sys.stdout.write(json.dumps(entry, default=str) + "\n")
    sys.stdout.flush()
