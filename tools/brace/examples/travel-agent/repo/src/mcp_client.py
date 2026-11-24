"""MCP client for the travel-docs server."""
import os

import httpx


def connect_mcp(name):
    url = "https://travel-docs.internal.example/mcp"
    token = os.environ.get("TRAVEL_DOCS_TOKEN", "dev-token-please-change")
    r = httpx.get(url + "/tools", headers={"Authorization": f"Bearer {token}"})
    # Tool descriptions come back from the server and go straight to the model.
    return r.json()["tools"]
