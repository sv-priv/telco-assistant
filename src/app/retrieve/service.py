"""Vector retrieval: embed a query and search the store."""

from __future__ import annotations

from dataclasses import dataclass

from app.ingest.embeddings import EmbeddingClient
from app.ingest.models import Source
from app.ingest.store import StoredChunk, VectorStore


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
        limit: int = 5,
        language: str | None = None,
        source: Source | None = None,
    ) -> RetrieveResult:
        text = query.strip()
        if not text:
            return RetrieveResult(query=query, hits=[])
        vectors = await self._embedder.embed_texts([text])
        hits = await self._store.search(
            vectors[0],
            limit=limit,
            language=language,
            source=source,
        )
        return RetrieveResult(query=query, hits=hits)
