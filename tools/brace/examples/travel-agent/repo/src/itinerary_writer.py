"""Sub-agent that writes the final itinerary text."""
import anthropic

from src.tools import registry


def write_itinerary(messages, ctx):
    client = anthropic.Anthropic()
    # Meant to be text-only, but it is handed the full tool registry.
    tools = registry.all_tools()
    return client.messages.create(model=ctx.model, tools=tools, messages=messages)
