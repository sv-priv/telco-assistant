"""Vector retrieval: embed a query and search the store."""

from __future__ import annotations

from dataclasses import dataclass

from app.ingest.embeddings import EmbeddingClient
from app.ingest.models import Source
from app.ingest.store import StoredChunk, VectorStore
from app.retrieve.query_expand import expand_search_query, is_plan_query
from app.retrieve.ranking import rerank_hits


@dataclass(frozen=True)
class RetrieveResult:
    query: str
    hits: list[StoredChunk]


class Retriever:
    def __init__(self, store: VectorStore, embedder: EmbeddingClient) -> None:
        self._store = store
        self._embedder = embedder

    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 8,
        language: str | None = None,
        source: Source | None = None,
    ) -> RetrieveResult:
        text = expand_search_query(query.strip())
        if not text:
            return RetrieveResult(query=query, hits=[])
        # Over-fetch plan questions so cenovnik docs can surface past addon noise.
        fetch_limit = max(limit * 4, 24) if is_plan_query(text) else limit
        vectors = await self._embedder.embed_texts([text])
        hits = await self._store.search(
            vectors[0],
            limit=fetch_limit,
            language=language,
            source=source,
        )
        hits = rerank_hits(text, hits, limit=limit)
        return RetrieveResult(query=text, hits=hits)
