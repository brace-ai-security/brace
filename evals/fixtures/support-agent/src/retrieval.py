"""Help-center article search over Qdrant."""
import os

import anthropic
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant.support.svc:6333")
COLLECTION = "kb_articles"

_qdrant = QdrantClient(url=QDRANT_URL)


def _embed(text: str) -> list[float]:
    from src.embeddings import embed  # voyage-3 via HTTP

    return embed(text)


def search_kb(query: str, top_k: int = 5) -> list[str]:
    hits = _qdrant.search(collection_name=COLLECTION, query_vector=_embed(query), limit=top_k)
    return [h.payload["text"] for h in hits]


def upsert_article(article_id: str, text: str, tenant_id: str, source_url: str) -> None:
    """Called by the help-center sync job and by the /kb/import endpoint."""
    _qdrant.upsert(
        collection_name=COLLECTION,
        points=[
            PointStruct(
                id=article_id,
                vector=_embed(text),
                payload={"text": text, "tenant_id": tenant_id, "source_url": source_url},
            )
        ],
    )
