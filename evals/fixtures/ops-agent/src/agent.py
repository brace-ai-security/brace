"""Tool loop. Runs until the model stops asking for tools."""
import uuid
from pathlib import Path

import anthropic
import yaml

from src import audit
from src.checkpoint import save_checkpoint
from src.tools.registry import TOOL_SCHEMAS, dispatch

ROOT = Path(__file__).resolve().parent.parent
CONFIG = yaml.safe_load((ROOT / "config" / "agent.yaml").read_text())
SYSTEM = (ROOT / "prompts" / "system.md").read_text()

client = anthropic.Anthropic()


def run(goal: str, requester: str, run_id: str | None = None, messages: list | None = None) -> str:
    run_id = run_id or str(uuid.uuid4())
    messages = messages or [{"role": "user", "content": goal}]

    while True:
        response = client.messages.create(
            model=CONFIG["model"]["id"],
            max_tokens=CONFIG["model"]["max_output_tokens"],
            system=SYSTEM,
            messages=messages,
            tools=TOOL_SCHEMAS,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            summary = "".join(b.text for b in response.content if b.type == "text")
            audit.post_summary(run_id, requester, goal, summary)
            return summary

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = dispatch(block.name, block.input, run_id=run_id)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output[:20000]})
        messages.append({"role": "user", "content": results})
        save_checkpoint(run_id, requester, goal, messages)
