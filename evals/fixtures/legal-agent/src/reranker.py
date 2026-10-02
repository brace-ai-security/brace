"""Hosted reranker client."""
from __future__ import annotations

import os

import httpx
import yaml

from src.config import ROOT
from src.inbound import check_rerank

_rec = yaml.safe_load((ROOT / "models" / "reranker.yaml").read_text())


def rerank(query: str, chunks: list[dict]) -> list[dict]:
    if not chunks:
        return []
    resp = httpx.post(
        _rec["endpoint"],
        headers={"Authorization": f"Bearer {os.environ['RERANK_API_KEY']}"},
        json={
            "model": _rec["model_id"],
            "query": query,
            "documents": [c["text"] for c in chunks],
            "top_n": _rec["top_n"],
        },
        timeout=_rec["timeout_seconds"],
    )
    resp.raise_for_status()
    parsed = check_rerank(resp.content, len(chunks))
    return [chunks[r.index] | {"rerank_score": r.relevance_score} for r in parsed.results]
