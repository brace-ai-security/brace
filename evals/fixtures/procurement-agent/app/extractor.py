"""Line-item extraction sub-agent.

The parent procurement agent delegates structured extraction to a smaller
model. The child runs under its own instance id, links to its parent in the
audit graph, charges the parent's budget, and gets the extractor tool role.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from opentelemetry import trace

from app import audit
from app.budget import Budget
from app.context_size import measure_context
from app.identity import RunIdentity
from app.redact import redact_for_model
from app.tools import build_registry

log = logging.getLogger(__name__)
tracer = trace.get_tracer("procurement.extractor")

EXTRACTOR_ROLE = "line_item_extractor"
MAX_TURNS = 4

LINE_ITEMS_SCHEMA_KEYS = {"sku", "description", "quantity", "unit_price_cents", "currency"}


class ExtractionFailed(Exception):
    pass


class LineItemExtractor:
    def __init__(self, *, client, settings, deps, system_prompt: str):
        self.client = client
        self.settings = settings
        self.deps = deps
        self.system_prompt = system_prompt

    async def extract(self, parent: RunIdentity, doc_id: str, budget: Budget) -> list[dict[str, Any]]:
        budget.check_subagent()
        ident = parent.child(role=EXTRACTOR_ROLE)
        registry = build_registry(EXTRACTOR_ROLE, ident, self.deps)
        task = f"Extract every line item from document {doc_id}. Return JSON only."

        with tracer.start_as_current_span("gen_ai.invoke_agent line_item_extractor") as span:
            span.set_attribute("gen_ai.agent.id", ident.agent_instance_id)
            span.set_attribute("procurement.parent_instance_id", parent.agent_instance_id)
            start_node = await audit.record(
                self.deps.pool,
                ident,
                kind="subagent_started",
                payload={
                    "role": EXTRACTOR_ROLE,
                    "doc_id": doc_id,
                    "parent_prompt_ref": format(span.get_span_context().span_id, "016x"),
                    "tools": registry.names(),
                },
            )

            messages: list[dict[str, Any]] = [{"role": "user", "content": task}]
            for _turn in range(MAX_TURNS):
                budget.check_step()
                request = {
                    "model": self.settings.extractor_model_id,
                    "system": self.system_prompt,
                    "messages": messages,
                    "tools": registry.schemas(),
                    "max_tokens": 4096,
                }
                ctx = await measure_context(self.client, request, compacted=False)
                response = await self.client.messages.create(**request)
                budget.charge_model(self.settings.extractor_model_id, response.usage)
                await budget.flush(self.deps.pool)
                ctx = ctx.finalize(response.usage)
                decision = await audit.record(
                    self.deps.pool, ident, kind="model_decision", parent=start_node, context=ctx,
                    payload={"requested_model": request["model"], "served_model": response.model,
                             "stop_reason": response.stop_reason},
                )
                messages.append({"role": "assistant", "content": response.content})
                uses = [b for b in response.content if b.type == "tool_use"]
                if not uses:
                    text = "".join(b.text for b in response.content if b.type == "text")
                    items = _parse_items(text)
                    await audit.record(
                        self.deps.pool, ident, kind="subagent_finished", parent=start_node,
                        payload={"items": len(items)},
                    )
                    return items
                results = []
                for use in uses:
                    budget.check_tool_call()
                    results.append(await self.deps.execute_tool(ident, registry, use, decision, ctx))
                messages.append({"role": "user", "content": results})

        raise ExtractionFailed(f"no result after {MAX_TURNS} turns")


def _parse_items(text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExtractionFailed("extractor returned non-JSON output") from exc
    if not isinstance(data, list) or len(data) > 500:
        raise ExtractionFailed("extractor output must be a list of at most 500 items")
    items = []
    for raw in data:
        if not isinstance(raw, dict) or not set(raw) <= LINE_ITEMS_SCHEMA_KEYS:
            raise ExtractionFailed("unexpected line-item fields")
        items.append({k: redact_for_model(v) if isinstance(v, str) else v for k, v in raw.items()})
    return items
