"""Agent loop for the HR helpdesk."""
from __future__ import annotations

import json
import logging
import pathlib
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from anthropic import AsyncAnthropic
from opentelemetry import trace

from .approvals import ApprovalInvalid, ApprovalStore
from .audit import AuditWriter, RunContext
from .budgets import BudgetExceeded, QuotaStore, RunBudget
from .gateway_client import GatewayClient, ToolDenied, ToolError
from .killswitch import StopControl
from .redact import redact
from .retrieval import PolicyIndex
from .tools import ToolRegistry, ToolSpec
from .validation import ValidationRejected, validate_chunk, validate_tool_args, validate_tool_output

log = logging.getLogger("hr_agent.loop")
tracer = trace.get_tracer("hr_agent")

SYSTEM_PROMPT = (pathlib.Path(__file__).resolve().parent.parent / "prompts" / "system.md").read_text()


@dataclass
class RunState:
    messages: list[dict[str, Any]]
    budget: RunBudget
    subject_token: str
    status: str = "running"
    reply: str | None = None
    pending_approval: dict[str, Any] | None = None
    last_step: str | None = None
    subagents_started: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


class Agent:
    def __init__(self, cfg: dict[str, Any], registry: ToolRegistry, llm: AsyncAnthropic, gateway: GatewayClient,
                 index: PolicyIndex, approvals: ApprovalStore, quotas: QuotaStore, audit: AuditWriter, stop: StopControl):
        self.cfg, self.registry, self.llm, self.gateway = cfg, registry, llm, gateway
        self.index, self.approvals, self.quotas, self.audit, self.stop = index, approvals, quotas, audit, stop

    def new_state(self, user_text: str, subject_token: str) -> RunState:
        budget = RunBudget(self.cfg["budgets"]["run"], self.cfg["pricing"])
        return RunState(messages=[{"role": "user", "content": user_text}], budget=budget, subject_token=subject_token)

    async def run(self, ctx: RunContext, state: RunState) -> RunState:
        with tracer.start_as_current_span("agent.run", attributes={"agent.instance.id": ctx.agent_instance_id}):
            try:
                await self._loop(ctx, state)
            except BudgetExceeded as exc:
                await self.audit.record(ctx, "budget_stop", decision="stop", reason=exc.limit, parent_step_id=state.last_step)
                state.status, state.reply = "stopped", "I've reached the limit for this conversation. An HR advisor can help further."
            return state

    async def _loop(self, ctx: RunContext, state: RunState) -> None:
        model = self.cfg["model"]
        while True:
            await self.stop.raise_if_stopped(ctx)
            state.budget.check_step()
            step_id = str(uuid.uuid4())
            with tracer.start_as_current_span("gen_ai.chat", attributes={"gen_ai.request.model": model["id"]}):
                resp = await self.llm.messages.create(
                    model=model["id"], system=SYSTEM_PROMPT, max_tokens=model["max_output_tokens"],
                    temperature=model["temperature"], tools=self.registry.model_schemas(), messages=state.messages,
                    timeout=state.budget.remaining_seconds(),
                )
                tokens, cost = state.budget.record_usage(resp.usage)
                ctx_tokens = resp.usage.input_tokens + (resp.usage.cache_read_input_tokens or 0) + (resp.usage.cache_creation_input_tokens or 0)
                await self.audit.record(
                    ctx, "model_call", step_id=step_id, parent_step_id=state.last_step,
                    context_tokens=ctx_tokens, context_tokens_method="measured:provider_usage_input+cache_read+cache_write",
                    model_requested=model["id"], model_served=resp.model, result={"stop_reason": resp.stop_reason},
                )
                await self.quotas.record_usage(ctx, tokens, cost)
            state.last_step = step_id
            state.messages.append({"role": "assistant", "content": [b.model_dump() for b in resp.content]})
            if resp.stop_reason != "tool_use":
                state.status = "done"
                state.reply = "".join(b.text for b in resp.content if b.type == "text")
                return
            results = []
            for block in (b for b in resp.content if b.type == "tool_use"):
                result = await self._handle_tool(ctx, state, step_id, block.id, block.name, block.input)
                if result is None:  # paused for employee approval
                    return
                results.append(result)
            state.messages.append({"role": "user", "content": results})

    async def _handle_tool(self, ctx: RunContext, state: RunState, parent: str, tool_use_id: str,
                           name: str, args: Any) -> dict[str, Any] | None:
        step_id = str(uuid.uuid4())
        await self.audit.record(ctx, "proposed_action", step_id=step_id, parent_step_id=parent, tool=name, args=args)
        spec = self.registry.get(name)
        if spec is None:
            await self.audit.record(ctx, "authz_decision", step_id=step_id, tool=name, decision="deny", reason="tool not in allowlist")
            return _tool_result(tool_use_id, "This tool is not available.", error=True)
        target = spec.target(ctx.subject)
        state.budget.check_tool_call()
        try:
            args = validate_tool_args(spec, args)
        except ValidationRejected as exc:
            await self.audit.record(ctx, "authz_decision", step_id=step_id, tool=spec.qualified, target=target,
                                    decision="deny", reason=exc.reason, args=args)
            return _tool_result(tool_use_id, f"Invalid arguments: {exc.reason}", error=True)
        if spec.approval == "subject":
            approval_id, text = await self.approvals.request(ctx, spec.qualified, target, args, tool_use_id)
            await self.audit.record(ctx, "approval_requested", step_id=step_id, tool=spec.qualified, target=target,
                                    decision="hold", approval_id=approval_id, args=args)
            state.status = "awaiting_approval"
            state.pending_approval = {"approval_id": approval_id, "description": text}
            return None
        await self.audit.record(ctx, "authz_decision", step_id=step_id, tool=spec.qualified, target=target, decision="allow")
        return await self._execute(ctx, state, step_id, tool_use_id, spec, target, args, approval_id=None)

    async def resume_with_approval(self, ctx: RunContext, state: RunState, approval_id: str) -> RunState:
        with tracer.start_as_current_span("agent.resume", attributes={"agent.instance.id": ctx.agent_instance_id}):
            pending = await self.approvals.pending(approval_id)
            if pending is None or pending["run_id"] != ctx.run_id:
                raise ApprovalInvalid("unknown approval for this run")
            spec = self.registry.by_qualified(pending["operation"])
            step_id = str(uuid.uuid4())
            try:
                await self.stop.raise_if_stopped(ctx)
                args = validate_tool_args(spec, pending["args"])
                target = spec.target(ctx.subject)
                await self._recheck_state(ctx, state, spec, args)
                grant = await self.approvals.consume(ctx, approval_id, spec.qualified, target, args)
            except (ApprovalInvalid, ValidationRejected, ToolDenied, ToolError) as exc:
                await self.audit.record(ctx, "authz_decision", step_id=step_id, tool=pending["operation"],
                                        decision="deny", reason=str(exc), approval_id=approval_id)
                state.status, state.reply = "done", "That action can no longer be carried out as approved."
                return state
            await self.audit.record(ctx, "approval_used", step_id=step_id, parent_step_id=state.last_step,
                                    tool=spec.qualified, target=target, decision="allow", approval_id=approval_id,
                                    result={"approved_by": grant["approved_by"], "approved_at": grant["approved_at"].isoformat()})
            result = await self._execute(ctx, state, step_id, pending["tool_use_id"], spec, target, args, approval_id=approval_id)
            state.messages.append({"role": "user", "content": [result]})
            state.status, state.pending_approval = "running", None
            return await self.run(ctx, state)

    async def _recheck_state(self, ctx: RunContext, state: RunState, spec: ToolSpec, args: dict[str, Any]) -> None:
        """Re-read the resource the action depends on, at execution time."""
        if spec.qualified != "hris/file_leave_request" or args["leave_type"] == "unpaid":
            return
        balance_spec = self.registry.get("get_leave_balance")
        bal = await self.gateway.call(balance_spec, {"leave_type": args["leave_type"]}, ctx, state.subject_token,
                                      operation_id=str(uuid.uuid4()))
        bal = validate_tool_output(balance_spec, bal, self.cfg["limits"]["max_tool_output_bytes"])
        days = (date.fromisoformat(args["end_date"]) - date.fromisoformat(args["start_date"])).days + 1
        if days <= 0 or bal["balance_days"] < days:
            raise ApprovalInvalid("leave balance no longer covers the request")

    async def _execute(self, ctx: RunContext, state: RunState, step_id: str, tool_use_id: str, spec: ToolSpec,
                       target: str, args: dict[str, Any], approval_id: str | None) -> dict[str, Any]:
        operation_id = approval_id or str(uuid.uuid4())
        with tracer.start_as_current_span(f"execute_tool {spec.qualified}", attributes={"gen_ai.tool.name": spec.name}):
            try:
                if spec.kind == "local":
                    raw = await self.index.search(args["query"], ctx.subject)
                    max_chars = self.cfg["retrieval"]["max_chunk_chars"]
                    clean: Any = []
                    for chunk in raw:
                        try:
                            clean.append(validate_chunk(chunk, max_chars))
                        except ValidationRejected as exc:
                            await self.audit.record(ctx, "content_held", step_id=step_id, tool=spec.qualified,
                                                    decision="hold", reason=exc.reason, result={"chunk_id": chunk["chunk_id"]})
                else:
                    raw = await self.gateway.call(spec, args, ctx, state.subject_token, operation_id=operation_id)
                    clean = validate_tool_output(spec, raw, self.cfg["limits"]["max_tool_output_bytes"])
            except ToolDenied as exc:
                await self.audit.record(ctx, "tool_denied", step_id=step_id, tool=spec.qualified, target=target,
                                        decision="deny", reason=exc.reason, approval_id=approval_id, args=args)
                return _tool_result(tool_use_id, "The request was refused by policy.", error=True)
            except ToolError as exc:
                await self.audit.record(ctx, "tool_error", step_id=step_id, tool=spec.qualified, target=target,
                                        decision="error", reason=f"status {exc.status}", approval_id=approval_id,
                                        args=args, result={"detail": exc.detail})
                log.warning("tool error", extra={"tool": spec.qualified, "detail": redact(exc.detail)})
                return _tool_result(tool_use_id, f"{spec.name} failed: {exc.detail}", error=True)
            except ValidationRejected as exc:
                await self.audit.record(ctx, "content_held", step_id=step_id, tool=spec.qualified, target=target,
                                        decision="hold", reason=exc.reason, approval_id=approval_id)
                return _tool_result(tool_use_id, "The tool returned data that could not be used.", error=True)
        await self.audit.record(ctx, "tool_result", step_id=step_id, tool=spec.qualified, target=target,
                                decision="ok", approval_id=approval_id, args=args, result=clean)
        envelope = {"source": spec.qualified, "trust": "untrusted_data", "data": clean}
        return _tool_result(tool_use_id, json.dumps(envelope, ensure_ascii=False))


def _tool_result(tool_use_id: str, content: str, error: bool = False) -> dict[str, Any]:
    return {"type": "tool_result", "tool_use_id": tool_use_id, "content": content, "is_error": error}
