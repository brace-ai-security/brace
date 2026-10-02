import os

import httpx


def embed(text: str) -> list[float]:
    resp = httpx.post(
        "https://api.voyageai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {os.environ['VOYAGE_API_KEY']}"},
        json={"input": [text[:8000]], "model": "voyage-3"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]
