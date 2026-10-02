"""Tool loop with hard limits enforced by the harness."""
import time
import uuid
from pathlib import Path

import anthropic
import yaml

from src.audit import record
from src.quota import RunLimitReached, charge_user_run
from src.telemetry import identity_attrs, tracer
from src.tools import TOOL_SCHEMAS, TOOLS

ROOT = Path(__file__).resolve().parent.parent
CONFIG = yaml.safe_load((ROOT / "config" / "agent.yaml").read_text())
SYSTEM = (ROOT / "prompts" / "system.md").read_text()
B = CONFIG["budgets"]

client = anthropic.Anthropic()


def _halted() -> bool:
    try:
        return Path(CONFIG["halt_file"]).read_text().strip() == "1"
    except OSError:
        return True  # flag unreadable: stop


def run(question: str, user: str) -> str:
    instance_id = str(uuid.uuid4())
    charge_user_run(user, B["user_daily_runs"])
    started, tokens, tool_calls = time.monotonic(), 0, 0
    messages = [{"role": "user", "content": question}]

    with tracer.start_as_current_span("invoke_agent research-agent") as root:
        for attr, value in identity_attrs(instance_id, user).items():
            root.set_attribute(attr, value)

        for step in range(B["max_steps"]):
            if _halted():
                record(instance_id, user, "halted", {})
                return "Stopped by operator."
            if time.monotonic() - started > B["max_wall_seconds"] or tokens > B["max_total_tokens"]:
                record(instance_id, user, "budget_exceeded", {"tokens": tokens})
                return "This question needs more research than one run allows."

            resp = client.messages.create(
                model=CONFIG["model"]["id"], max_tokens=CONFIG["model"]["max_output_tokens"],
                system=SYSTEM, messages=messages, tools=TOOL_SCHEMAS,
            )
            tokens += resp.usage.input_tokens + resp.usage.output_tokens
            messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason != "tool_use":
                record(instance_id, user, "answer", {"steps": step + 1, "tokens": tokens})
                return "".join(b.text for b in resp.content if b.type == "text")

            results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                with tracer.start_as_current_span(f"execute_tool {block.name}") as span:
                    for attr, value in identity_attrs(instance_id, user).items():
                        span.set_attribute(attr, value)
                    span.set_attribute("gen_ai.tool.name", block.name)
                    span.set_attribute("agent.context.size", resp.usage.input_tokens)
                    span.set_attribute("agent.context.size.method", "measured")
                    tool_calls += 1
                    if block.name not in TOOLS or tool_calls > B["max_tool_calls"] or _halted():
                        span.set_attribute("agent.decision", "deny")
                        record(instance_id, user, "tool_denied", {"tool": block.name, "args": block.input})
                        results.append({"type": "tool_result", "tool_use_id": block.id,
                                        "content": "Denied.", "is_error": True})
                        continue
                    span.set_attribute("agent.decision", "allow")
                    record(instance_id, user, "tool_call", {"tool": block.name, "args": block.input})
                    try:
                        out = TOOLS[block.name](**block.input)
                        record(instance_id, user, "tool_result", {"tool": block.name, "bytes": len(out)})
                    except Exception as exc:
                        out = f"Error: {type(exc).__name__}"
                        record(instance_id, user, "tool_error", {"tool": block.name, "error": str(exc)})
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": f"<untrusted_web_content source=\"{block.name}\">\n{out}\n</untrusted_web_content>"})
            messages.append({"role": "user", "content": results})

        record(instance_id, user, "budget_exceeded", {"reason": "max_steps"})
        return "This question needs more research than one run allows."
