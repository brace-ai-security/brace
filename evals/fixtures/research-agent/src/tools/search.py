import json
import os

import httpx


def web_search(query: str) -> str:
    resp = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query[:300], "count": 8},
        headers={"X-Subscription-Token": os.environ["BRAVE_API_KEY"], "Accept": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("web", {}).get("results", [])
    return json.dumps([{"title": r.get("title", "")[:200], "url": r.get("url", ""),
                        "snippet": r.get("description", "")[:500]} for r in results])
