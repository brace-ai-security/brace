"""Procurement agent run loop.

Graph: model turn -> (tool calls -> gate -> integration)* -> model turn ...
Every edge writes an audit node before the next step runs. Budgets are
checked before each model turn and each tool call.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

from opentelemetry import trace

from app import audit, killswitch
from app.budget import Budget, BudgetExceeded
from app.context_size import ContextMeasure, measure_context
from app.gate import PolicyGate
from app.identity import RunIdentity
from app.redact import redact_for_model
from app.tools import ToolRegistry, build_registry

log = logging.getLogger(__name__)
tracer = trace.get_tracer("procurement.loop")

COMPACT_AFTER_MESSAGES = 40
KEEP_RECENT_MESSAGES = 12


@dataclass
class AgentDeps:
    settings: Any
    pool: Any
    gate: PolicyGate
    erp: Any
    slack: Any
    broker: Any
    extractor: Any = None
    _budgets: dict[str, Budget] = field(default_factory=dict)
    _contexts: dict[str, ContextMeasure] = field(default_factory=dict)

    def current_budget(self, ident: RunIdentity) -> Budget:
        return self._budgets[ident.run_id]

    def current_context(self, ident: RunIdentity) -> ContextMeasure:
        return self._contexts.get(ident.agent_instance_id, ContextMeasure.unavailable())

    def erp_scope_for(self, operation: str) -> str:
        scopes = self.settings.policy["erp"]["operation_scopes"]
        return scopes.get(operation, "erp.read")

    async def execute_tool(self, ident, registry: ToolRegistry, use, parent: str, ctx: ContextMeasure) -> dict:
        self._contexts[ident.agent_instance_id] = ctx
        proposed = await audit.record(
            self.pool, ident, kind="tool_proposed", parent=parent, context=ctx,
            payload={"tool": use.name, "tool_use_id": use.id, "args": audit.summarize_args(use.input)},
        )
        tool = registry.get(use.name)
        if tool is None:
            await audit.record(
                self.pool, ident, kind="tool_denied", parent=proposed, context=ctx,
                policy_version=self.gate.version, payload={"reason": "tool not in role allowlist"},
            )
            return _error(use.id, f"tool {use.name} is not available to this agent")

        decision = await self.gate.authorize(ident, tool, use.input)
        authz = await audit.record(
            self.pool, ident, kind="authz_decision", parent=proposed, context=ctx,
            policy_version=decision.policy_version, approval_id=decision.approval_id,
            payload={"allow": decision.allow, "reason": decision.reason, "pending": decision.pending},
        )
        if not decision.allow:
            if decision.pending:
                return _error(use.id, f"approval requested ({decision.approval_id}); do not retry until approved")
            return _error(use.id, f"denied: {decision.reason}")

        operation_id = f"op-{hashlib.sha256((authz + use.id).encode()).hexdigest()[:24]}"
        try:
            with tracer.start_as_current_span(f"execute_tool {use.name}") as span:
                for k, v in ctx.otel_attributes().items():
                    span.set_attribute(k, v)
                output = await tool.invoke(use.input, ident)
        except BudgetExceeded:
            raise
        except Exception as exc:
            await audit.record(
                self.pool, ident, kind="tool_error", parent=authz, context=ctx,
                policy_version=decision.policy_version, approval_id=decision.approval_id,
                operation_id=operation_id,
                payload={"error_type": type(exc).__name__, "error": str(exc)[:500]},
            )
            return _error(use.id, f"{use.name} failed: {type(exc).__name__}")

        await audit.record(
            self.pool, ident, kind="tool_result", parent=authz, context=ctx,
            policy_version=decision.policy_version, approval_id=decision.approval_id,
            operation_id=operation_id,
            payload={"result_sha256": audit.digest(output), "result": output},
        )
        return {"type": "tool_result", "tool_use_id": use.id, "content": redact_for_model(output)}


def _error(tool_use_id: str, message: str) -> dict:
    return {"type": "tool_result", "tool_use_id": tool_use_id, "is_error": True, "content": message}


def _compact(messages: list[dict]) -> tuple[list[dict], bool]:
    if len(messages) <= COMPACT_AFTER_MESSAGES:
        return messages, False
    head, tail = messages[:1], messages[-KEEP_RECENT_MESSAGES:]
    while tail and tail[0]["role"] != "assistant":
        tail = tail[1:]
    note = {"role": "user", "content": "[earlier tool exchanges were removed to save space]"}
    return head + [note] + tail, True


class ProcurementAgent:
    def __init__(self, *, client, deps: AgentDeps, system_prompt: str, role: str = "procurement"):
        self.client = client
        self.deps = deps
        self.system_prompt = system_prompt
        self.role = role

    async def run(self, ident: RunIdentity, task: str) -> str | None:
        pool = self.deps.pool
        await killswitch.assert_running(pool, ident.tenant)
        budget = Budget.for_run(self.deps.settings.budgets, ident)
        await budget.reserve_run_start(pool)
        self.deps._budgets[ident.run_id] = budget
        registry = build_registry(self.role, ident, self.deps)

        run_node = await audit.record(
            pool, ident, kind="run_started",
            payload={"task_sha256": hashlib.sha256(task.encode()).hexdigest(), "tools": registry.names()},
        )
        messages: list[dict[str, Any]] = [{"role": "user", "content": task}]
        try:
            while True:
                budget.check_step()
                messages, compacted = _compact(messages)
                request = {
                    "model": self.deps.settings.model_id,
                    "system": self.system_prompt,
                    "messages": messages,
                    "tools": registry.schemas(),
                    "max_tokens": 4096,
                }
                ctx = await measure_context(self.client, request, compacted)
                response = await self.client.messages.create(**request)
                budget.charge_model(self.deps.settings.model_id, response.usage)
                await budget.flush(pool)
                ctx = ctx.finalize(response.usage)
                decision = await audit.record(
                    pool, ident, kind="model_decision", parent=run_node, context=ctx,
                    payload={
                        "requested_model": request["model"],
                        "served_model": response.model,
                        "stop_reason": response.stop_reason,
                        "proposed_tools": [b.name for b in response.content if b.type == "tool_use"],
                    },
                )
                messages.append({"role": "assistant", "content": response.content})
                uses = [b for b in response.content if b.type == "tool_use"]
                if not uses:
                    final = "".join(b.text for b in response.content if b.type == "text")
                    await audit.record(pool, ident, kind="run_finished", parent=run_node, context=ctx,
                                       payload={"final_sha256": audit.digest(final)})
                    return final
                results = []
                for use in uses:
                    budget.check_tool_call()
                    results.append(await self.deps.execute_tool(ident, registry, use, decision, ctx))
                messages.append({"role": "user", "content": results})
        except BudgetExceeded as exc:
            await audit.record(
                pool, ident, kind="budget_exceeded", parent=run_node,
                payload={"limit": exc.limit, "used": str(exc.used), "allowed": str(exc.allowed)},
            )
            await self.deps.slack.post(
                channel="#procurement-agent-ops",
                text=f"Run {ident.run_id} ({ident.tenant}) stopped: {exc.limit} exceeded.",
            )
            return None
        finally:
            self.deps._budgets.pop(ident.run_id, None)
