"""Letter-drafting sub-agent."""
from __future__ import annotations

import hashlib
import json

import anthropic

from .audit import AuditLog
from .budget import RunBudget
from .control import ControlFlag
from .identity import ROOT, RunContext, compute_agent_type_id
from .tools.registry import ToolRegistry

_PROMPT = (ROOT / "prompts" / "letter_drafter.md").read_text()


class Drafter:
    def __init__(self, cfg: dict, client: anthropic.Anthropic, audit: AuditLog, control: ControlFlag):
        self.cfg = cfg["drafter"]
        self.client = client
        self.audit = audit
        self.control = control
        self.type_id = compute_agent_type_id(self.cfg["model"])

    def run(self, ctx: RunContext, parent_registry: ToolRegistry, budget: RunBudget,
            brief: str, tenant_name: str) -> str:
        budget.charge_subagent()
        child = ctx.child(self.type_id)
        registry = parent_registry.scoped(self.cfg["tools"])
        self.audit.record(
            child, "subagent.spawned",
            model=self.cfg["model"],
            parent_prompt=brief,
            parent_prompt_sha256=hashlib.sha256(brief.encode()).hexdigest(),
        )
        messages = [{"role": "user", "content": brief}]
        for _ in range(self.cfg["max_turns"]):
            self.control.check()
            budget.check_turn()
            resp = self.client.messages.create(
                model=self.cfg["model"],
                max_tokens=2048,
                system=_PROMPT.format(tenant_name=tenant_name),
                tools=registry.schemas(),
                messages=messages,
                timeout=budget.http_timeout(120),
            )
            budget.charge_usage(resp.usage)
            messages.append({"role": "assistant", "content": resp.content})
            calls = [b for b in resp.content if b.type == "tool_use"]
            if not calls:
                text = "".join(b.text for b in resp.content if b.type == "text")
                self.audit.record(child, "subagent.completed", output_chars=len(text))
                return text
            results = []
            for call in calls:
                self.control.check()
                budget.charge_tool_call()
                out = registry.dispatch(child, call.name, call.input, resp.usage.input_tokens)
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": out})
            messages.append({"role": "user", "content": results})
        self.audit.record(child, "subagent.turn_limit")
        return json.dumps({"error": "drafter did not finish"})
