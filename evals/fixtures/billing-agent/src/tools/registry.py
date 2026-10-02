"""Tool registry and dispatch."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from ..approvals import ApprovalRequired
from ..audit import AuditLog, redact
from ..identity import RunContext


@dataclass
class Tool:
    name: str
    schema: dict
    handler: Callable[[RunContext, dict], Any]
    source: str = "local"
    read_only_hint: bool = False


class ToolRegistry:
    def __init__(self, tools: dict[str, Tool], allowlist: set[str], audit: AuditLog):
        self._tools = tools
        self._allow = set(allowlist)
        self.audit = audit

    def is_allowed(self, name: str) -> bool:
        tool = self._tools.get(name)
        if tool is None:
            return False
        if name in self._allow:
            return True
        return tool.source != "local" and tool.read_only_hint

    def schemas(self) -> list[dict]:
        return [t.schema for n, t in sorted(self._tools.items()) if self.is_allowed(n)]

    def scoped(self, names: list[str]) -> "ToolRegistry":
        if not names:
            return self
        keep = {n: t for n, t in self._tools.items() if n in names}
        return ToolRegistry(keep, self._allow & set(names), self.audit)

    def dispatch(self, ctx: RunContext, name: str, args: dict, context_tokens: int | None) -> str:
        op_id = uuid.uuid4().hex
        base = {"op_id": op_id, "tool": name, "args": args, "context_tokens": context_tokens,
                "context_tokens_method": "provider_usage_input" if context_tokens is not None else "unavailable"}
        if not self.is_allowed(name):
            self.audit.record(ctx, "tool.denied", reason="not_allowed", **base)
            return json.dumps({"error": f"tool {name} is not available"})
        self.audit.record(ctx, "tool.allowed", **base)
        try:
            result = self._tools[name].handler(ctx, args)
        except ApprovalRequired as e:
            self.audit.record(ctx, "tool.approval_required", approval_request_id=e.request_id, **base)
            return json.dumps({"status": "pending_approval", "approval_request_id": e.request_id})
        except Exception as e:
            self.audit.record(ctx, "tool.error", error=f"{type(e).__name__}: {e}", **base)
            return json.dumps({"error": redact(f"{type(e).__name__}: {e}")})
        self.audit.record(ctx, "tool.result", result=result, op_id=op_id, tool=name)
        return json.dumps(redact(result), default=str)
