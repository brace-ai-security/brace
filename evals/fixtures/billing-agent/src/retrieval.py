"""Collection-policy search over the per-tenant pgvector store."""
from __future__ import annotations

import os

import httpx
import psycopg
from pgvector.psycopg import register_vector

from .identity import RunContext

EMBED_URL = "http://embedder.ml.svc.cluster.local:8000/v1/embed"


class PolicySearch:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or os.environ["POLICY_DSN"]
        self.http = httpx.Client(timeout=10.0)

    def _embed(self, text: str) -> list[float]:
        r = self.http.post(EMBED_URL, json={"input": text[:2000]})
        r.raise_for_status()
        return r.json()["embedding"]

    def search(self, ctx: RunContext, args: dict) -> dict:
        query = str(args["query"])[:500]
        vec = self._embed(query)
        with psycopg.connect(self.dsn, autocommit=False) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, true)", (ctx.tenant_id,))
                cur.execute(
                    """
                    SELECT id, source_uri, trust_level, added_at, content
                      FROM policy_chunks
                     WHERE tenant_id = %s
                       AND status = 'active'
                       AND (expires_at IS NULL OR expires_at > now())
                     ORDER BY embedding <=> %s
                     LIMIT 5
                    """,
                    (ctx.tenant_id, vec),
                )
                rows = cur.fetchall()
        return {
            "results": [
                {
                    "chunk_id": r[0],
                    "source": r[1],
                    "trust": r[2],
                    "added_at": r[3].isoformat(),
                    "text": f"<untrusted source=\"{r[1]}\">{r[4]}</untrusted>",
                }
                for r in rows
            ]
        }
