"""Travel agent main loop (fictional fixture)."""
import anthropic

from src.itinerary_writer import write_itinerary
from src.mcp_client import connect_mcp
from src.tools import registry


def run(request, ctx):
    client = anthropic.Anthropic()
    tools = registry.all_tools()
    tools += connect_mcp("travel-docs")
    messages = [{"role": "user", "content": request}]
    while True:
        reply = client.messages.create(model=ctx.model, tools=tools, messages=messages)
        if reply.stop_reason != "tool_use":
            break
        messages += registry.run_calls(reply, ctx)
    return write_itinerary(messages, ctx)
