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
        fetch_limit = max(limit * 4, 24) if is_plan_query(text) else max(limit * 2, 12)
        vectors = await self._embedder.embed_texts([text])
        hits = await self._store.search(
            vectors[0],
            limit=fetch_limit,
            language=language,
            source=source,
        )
        # UI language is answer preference — if that slice is empty/weak, search both.
        if language is not None and _needs_language_fallback(hits, limit=limit):
            broader = await self._store.search(
                vectors[0],
                limit=fetch_limit,
                language=None,
                source=source,
            )
            hits = _merge_hits(hits, broader)
        hits = rerank_hits(text, hits, limit=limit)
        return RetrieveResult(query=text, hits=hits)


def _needs_language_fallback(hits: list[StoredChunk], *, limit: int) -> bool:
    if not hits:
        return True
    # Very weak top hit → try the other language slice too.
    top = hits[0].score
    return top is not None and top < 0.35 and len(hits) < limit


def _merge_hits(
    primary: list[StoredChunk],
    secondary: list[StoredChunk],
) -> list[StoredChunk]:
    seen: set[tuple[str, int, str]] = {(h.doc_id, h.chunk_index, h.language) for h in primary}
    merged = list(primary)
    for hit in secondary:
        key = (hit.doc_id, hit.chunk_index, hit.language)
        if key in seen:
            continue
        seen.add(key)
        merged.append(hit)
    return merged
