"""Tool registry shared by the agent and its sub-agent."""
from src.tools import flights, notify, profile

TOOLS = {
    "search_flights": flights.search_flights,
    "book_flight": flights.book_flight,
    "get_traveler_profile": profile.get_traveler_profile,
    "send_itinerary": notify.send_itinerary,
}


def all_tools():
    return [{"name": n} for n in TOOLS]


def run_calls(reply, ctx):
    return [TOOLS[c.name](ctx=ctx, **c.input) for c in reply.content if c.type == "tool_use"]
