import httpx

from src.config import settings

_EMBED_URL = "http://embeddings.models.svc.cluster.local:8000/v1/embeddings"


def embed(text: str) -> list[float]:
    resp = httpx.post(
        _EMBED_URL,
        json={"model": settings["embeddings"]["model"], "input": text[:8000]},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]
