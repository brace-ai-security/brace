"""The tool loop for one ticket."""
import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import anthropic
import yaml

from src import audit, policy
from src.agent_type_id import agent_type_id
from src.budgets import BudgetExceeded, RunBudget, TenantQuota
from src.killswitch import halted
from src.mcp_client import MCPHub
from src.retrieval import search_kb
from src.telemetry import action_span
from src.tools import LOCAL_TOOLS, LOCAL_TOOL_SCHEMAS

ROOT = Path(__file__).resolve().parent.parent
CONFIG = yaml.safe_load((ROOT / "config" / "agent.yaml").read_text())
SYSTEM_TEMPLATE = (ROOT / "prompts" / "system.md").read_text()

client = anthropic.Anthropic()


@dataclass
class RunResult:
    run_id: str
    final_text: str


def build_system_prompt(company_name: str, context_blocks: list[str]) -> str:
    return SYSTEM_TEMPLATE.format(
        company_name=company_name,
        internal_api_key=os.environ["INTERNAL_API_KEY"],
        context="\n\n".join(context_blocks),
    )


async def run_ticket(event, tenant_id: str, user_token) -> RunResult:
    run_id = str(uuid.uuid4())
    identity = {
        "accountable_party": CONFIG["agent"]["accountable_party"],
        "operational_owner": CONFIG["agent"]["operational_owner"],
        "tenant": tenant_id,
        "agent_type_id": agent_type_id(),
        "agent_instance_id": run_id,
    }
    budget = RunBudget.from_config(CONFIG["budgets"])
    quota = TenantQuota(tenant_id, CONFIG["budgets"])

    # Help-center articles and earlier tool results are given to the model as context.
    context_blocks = [f"KB: {doc}" for doc in search_kb(event.subject + "\n" + event.body)]
    messages = [{"role": "user", "content": f"Ticket #{event.ticket_id}: {event.subject}\n\n{event.body}"}]

    async with MCPHub(user_token) as hub:
        tools = LOCAL_TOOL_SCHEMAS + await hub.anthropic_tools()
        while True:
            if halted():
                return RunResult(run_id, "halted by operator")
            try:
                budget.check_step()
                quota.check()
            except BudgetExceeded as exc:
                audit.record(identity, "budget_exceeded", {"reason": str(exc)})
                return RunResult(run_id, "escalated: budget exceeded")

            response = client.messages.create(
                model=CONFIG["model"]["id"],
                max_tokens=CONFIG["model"]["max_output_tokens"],
                system=build_system_prompt(event.subdomain, context_blocks),
                messages=messages,
                tools=tools,
            )
            budget.add_tokens(response.usage.input_tokens + response.usage.output_tokens)
            quota.add_usage(response.usage)

            if response.stop_reason != "tool_use":
                text = "".join(b.text for b in response.content if b.type == "text")
                audit.record(identity, "final_answer", {"ticket_id": event.ticket_id})
                return RunResult(run_id, text)

            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                budget.check_tool_call()
                with action_span(identity, block.name, response.usage.input_tokens) as span:
                    if not policy.allowed(block.name, block.input):
                        tool_results.append(
                            {"type": "tool_result", "tool_use_id": block.id,
                             "content": "That action is not available.", "is_error": True}
                        )
                        continue
                    if block.name in LOCAL_TOOLS:
                        output = LOCAL_TOOLS[block.name](**block.input)
                    else:
                        output = await hub.call(block.name, block.input)
                    span.set_attribute("tool.result.size", len(output))
                    audit.record(identity, "tool_call", {"tool": block.name, "args": block.input})
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
                context_blocks.append(f"Result of {block.name}: {output}")
            messages.append({"role": "user", "content": tool_results})
