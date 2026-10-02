"""Main accounts-receivable agent loop."""
from __future__ import annotations

import datetime as dt

import anthropic
import redis

from .approvals import ApprovalClient
from .audit import AuditLog
from .budget import BudgetExceeded, Limits, RunBudget, SpendQuota
from .control import ControlFlag, Halted
from .drafter import Drafter
from .identity import ROOT, RunContext
from .mcp_client import AccountingMCP
from .memory import NegotiationMemory
from .retrieval import PolicySearch
from .tools.comms import Comms
from .tools.invoices import InvoiceStore
from .tools.payments import Payments
from .tools.registry import Tool, ToolRegistry

_SYSTEM = (ROOT / "prompts" / "system.md").read_text()


def _schema(name: str, description: str, props: dict, required: list[str]) -> dict:
    return {"name": name, "description": description,
            "input_schema": {"type": "object", "properties": props, "required": required, "additionalProperties": False}}


S = {"type": "string"}
I = {"type": "integer"}


class Deps:
    def __init__(self, cfg: dict, control: ControlFlag, mcp: AccountingMCP):
        self.cfg = cfg
        self.control = control
        self.mcp = mcp
        self.client = anthropic.Anthropic(max_retries=2)
        self.audit = AuditLog(cfg["audit"]["collector_url"], cfg["agent"]["policy_version"])
        self.redis = redis.Redis.from_url(cfg["memory"]["redis_url"])
        self.quota = SpendQuota(self.redis, cfg["budgets"]["quotas"])
        self.invoices = InvoiceStore()
        self.approvals = ApprovalClient(cfg["approvals"]["base_url"])
        self.memory = NegotiationMemory(self.redis, cfg["memory"]["note_ttl_days"])
        self.policy = PolicySearch()
        self.drafter = Drafter(cfg, self.client, self.audit, control)


def build_registry(deps: Deps, budget: RunBudget, tenant_name: str) -> ToolRegistry:
    pay = Payments(deps.cfg, deps.invoices, deps.approvals, budget)
    comms = Comms(deps.cfg, budget)
    tools: dict[str, Tool] = {}

    def add(schema: dict, handler) -> None:
        tools[schema["name"]] = Tool(schema["name"], schema, handler)

    add(_schema("lookup_invoices", "List open overdue invoices.",
                {"min_days_overdue": I, "sort": S, "limit": I}, []), deps.invoices.lookup_tool)
    add(_schema("get_invoice", "Get one invoice with its payment.", {"invoice_id": S}, ["invoice_id"]),
        deps.invoices.get_tool)
    add(_schema("issue_refund", "Refund part or all of a paid invoice.",
                {"invoice_id": S, "amount_cents": I, "reason": S}, ["invoice_id", "amount_cents", "reason"]),
        pay.issue_refund)
    add(_schema("issue_credit", "Apply an account credit for a customer.",
                {"customer_id": S, "amount_cents": I, "currency": S, "invoice_id": S, "reason": S,
                 "tenant_id": {"type": "string", "description": "Parent account for consolidated billing."}},
                ["customer_id", "amount_cents", "reason"]), pay.issue_credit)
    add(_schema("send_reminder", "Email a payment reminder to a customer contact.",
                {"to": S, "subject": S, "body_html": S}, ["to", "subject", "body_html"]), comms.send_reminder)
    add(_schema("open_ticket", "Open a support ticket.",
                {"subject": S, "body": S, "priority": S, "invoice_id": S}, ["subject", "body"]), comms.open_ticket)
    add(_schema("search_policy", "Search this tenant's collection policy.", {"query": S}, ["query"]),
        deps.policy.search)
    add(_schema("recall_negotiation", "Recall notes from past negotiations with a contact.",
                {"contact_email": S}, ["contact_email"]), deps.memory.recall)
    add(_schema("save_negotiation_note", "Record what was agreed with a contact.",
                {"contact_email": S, "note": S}, ["contact_email", "note"]), deps.memory.save)

    for name, (schema, handler, ro) in deps.mcp.handlers(budget.http_timeout).items():
        tools[name] = Tool(name, schema, handler, source=f"mcp:{deps.mcp.server_id}", read_only_hint=ro)

    registry = ToolRegistry(tools, set(deps.cfg["tools"]["allowlist"]), deps.audit)

    def draft_letter(ctx: RunContext, args: dict) -> dict:
        letter = deps.drafter.run(ctx, registry, budget, str(args["brief"])[:4000], tenant_name)
        return {"letter_markdown": letter}

    tools["draft_letter"] = Tool("draft_letter", _schema(
        "draft_letter", "Have the drafting assistant write a formal letter.", {"brief": S}, ["brief"]), draft_letter)
    return registry


def run(ctx: RunContext, task: str, tenant_name: str, deps: Deps) -> dict:
    cfg = deps.cfg
    budget = RunBudget(Limits(**cfg["budgets"]["per_run"]), cfg["pricing"], deps.quota,
                       ctx.accountable_party, ctx.tenant_id)
    registry = build_registry(deps, budget, tenant_name)
    system = _SYSTEM.format(tenant_name=tenant_name, today=dt.date.today().isoformat())
    messages = [{"role": "user", "content": f"<untrusted source=\"task\">{task}</untrusted>"}]
    deps.audit.record(ctx, "run.started", model=cfg["agent"]["model"], task=task)
    try:
        while True:
            deps.control.check()
            budget.check_turn()
            resp = deps.client.messages.create(
                model=cfg["agent"]["model"],
                max_tokens=cfg["agent"]["max_output_tokens"],
                system=system,
                tools=registry.schemas(),
                messages=messages,
                timeout=budget.http_timeout(180),
            )
            budget.charge_usage(resp.usage)
            context_tokens = (resp.usage.input_tokens + (resp.usage.cache_read_input_tokens or 0)
                              + (resp.usage.cache_creation_input_tokens or 0))
            deps.audit.record(ctx, "model.response", stop_reason=resp.stop_reason, context_tokens=context_tokens,
                              served_model=resp.model, output_tokens=resp.usage.output_tokens)
            messages.append({"role": "assistant", "content": resp.content})
            calls = [b for b in resp.content if b.type == "tool_use"]
            if not calls:
                text = "".join(b.text for b in resp.content if b.type == "text")
                deps.audit.record(ctx, "run.completed", turns=budget.turns, cost_usd=round(budget.cost, 4))
                return {"status": "completed", "summary": text}
            results = []
            for call in calls:
                deps.control.check()
                budget.charge_tool_call()
                out = registry.dispatch(ctx, call.name, call.input, context_tokens)
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": out})
            messages.append({"role": "user", "content": results})
    except BudgetExceeded as e:
        deps.audit.record(ctx, "run.budget_exceeded", limit=e.limit, turns=budget.turns, cost_usd=budget.cost)
        return {"status": "stopped", "reason": str(e)}
    except Halted:
        deps.audit.record(ctx, "run.halted", turns=budget.turns)
        return {"status": "halted"}
