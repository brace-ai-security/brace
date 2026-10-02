"""Handbook search over retrieval.chunks (Postgres full-text search).

Chunks are written only by the hr-docs-ingest job (role hr_docs_ingest). Each chunk carries
source, added_at, added_by, trust, an audience, an optional expiry and a quarantine flag.
Employee-specific documents (offer letters, individual arrangements) have audience
'employee' and list the employees allowed to see them.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

import asyncpg

_SEARCH = """
SELECT c.chunk_id, c.source, c.trust, c.text,
       ts_rank(c.tsv, websearch_to_tsquery('english', $1)) AS rank
  FROM retrieval.chunks c
 WHERE c.tsv @@ websearch_to_tsquery('english', $1)
   AND NOT c.quarantined
   AND (c.expires_at IS NULL OR c.expires_at > now())
   AND (c.audience = 'all' OR (c.audience = 'employee' AND $2 = ANY (c.allowed_employees)))
 ORDER BY rank DESC
 LIMIT $3
"""


class PolicyIndex:
    def __init__(self, pool: asyncpg.Pool, top_k: int, cache_ttl: float):
        self._pool = pool
        self._top_k = top_k
        self._ttl = cache_ttl
        self._cache: dict[str, tuple[float, str, list[dict[str, Any]]]] = {}

    async def _index_version(self) -> str:
        # Bumped by ingest on every add, expiry, quarantine or permission change.
        return await self._pool.fetchval("SELECT version FROM retrieval.index_state WHERE id = 1")

    def _key(self, query: str) -> str:
        normalized = " ".join(query.lower().split())
        return hashlib.sha256(f"{self._top_k}|{normalized}".encode()).hexdigest()

    async def search(self, query: str, employee_id: str) -> list[dict[str, Any]]:
        version = await self._index_version()
        key = self._key(query)
        hit = self._cache.get(key)
        if hit and hit[1] == version and time.monotonic() - hit[0] < self._ttl:
            return hit[2]
        rows = await self._pool.fetch(_SEARCH, query, employee_id, self._top_k)
        chunks = [dict(r) for r in rows]
        self._cache[key] = (time.monotonic(), version, chunks)
        return chunks
