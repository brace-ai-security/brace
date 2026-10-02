"""Search over the matter document index.

Documents are ingested by the Records team's pipeline, which owns the only write credential for
the collection. Each point carries matter_id, the principals allowed to read it, its source system,
and its ingestion time. This service holds a read-only token for the collection.
"""
from __future__ import annotations

import hashlib
import json

import redis
from qdrant_client import QdrantClient, models

from src.config import settings
from src.embeddings import embed
from src.identity import workload_token

_vcfg = settings["vector_db"]
_cache = redis.Redis.from_url(settings["cache"]["redis_url"])
_TTL = settings["cache"]["retrieval_ttl_seconds"]


def _client() -> QdrantClient:
    return QdrantClient(url=_vcfg["url"], api_key=workload_token(_vcfg["audience"]), https=True)


def _acl_filter(matter_id: str, user_id: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(key="matter_id", match=models.MatchValue(value=matter_id)),
            models.FieldCondition(key="acl_principals", match=models.MatchAny(any=[user_id, f"matter:{matter_id}"])),
            models.FieldCondition(key="status", match=models.MatchValue(value="active")),
        ]
    )


def _cache_key(query: str, top_k: int) -> str:
    normalized = " ".join(query.lower().split())
    return "ret:" + hashlib.sha256(f"{normalized}|{top_k}".encode()).hexdigest()


def search(query: str, matter_id: str, user_id: str, top_k: int | None = None) -> list[dict]:
    top_k = top_k or _vcfg["top_k"]
    key = _cache_key(query, top_k)
    cached = _cache.get(key)
    if cached is not None:
        return json.loads(cached)

    hits = _client().query_points(
        collection_name=_vcfg["collection"],
        query=embed(query),
        query_filter=_acl_filter(matter_id, user_id),
        limit=top_k,
        with_payload=True,
    ).points
    results = [
        {
            "chunk_id": str(h.id),
            "document_id": h.payload["document_id"],
            "matter_id": h.payload["matter_id"],
            "page": h.payload.get("page", 0),
            "text": h.payload["text"],
            "source": h.payload["source"],
            "ingested_at": h.payload["ingested_at"],
            "score": h.score,
        }
        for h in hits
    ]
    _cache.setex(key, _TTL, json.dumps(results))
    return results


def read_document(document_id: str, matter_id: str, user_id: str) -> list[dict]:
    points, _ = _client().scroll(
        collection_name=_vcfg["collection"],
        scroll_filter=models.Filter(
            must=[
                *_acl_filter(matter_id, user_id).must,
                models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id)),
            ]
        ),
        limit=200,
        with_payload=True,
    )
    return [
        {
            "chunk_id": str(p.id),
            "document_id": p.payload["document_id"],
            "matter_id": p.payload["matter_id"],
            "page": p.payload.get("page", 0),
            "text": p.payload["text"],
            "source": p.payload["source"],
            "ingested_at": p.payload["ingested_at"],
        }
        for p in sorted(points, key=lambda p: p.payload.get("page", 0))
    ]
