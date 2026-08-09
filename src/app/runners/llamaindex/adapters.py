"""Bridge our pgvector Retriever into LlamaIndex's BaseRetriever."""

from __future__ import annotations

import asyncio
from typing import Any

from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode

from app.ingest.models import Source
from app.ingest.store import StoredChunk
from app.retrieve.service import Retriever


class TelcoLlamaRetriever(BaseRetriever):
    """LlamaIndex retriever adapter → app.retrieve.service.Retriever."""

    def __init__(
        self,
        retriever: Retriever,
        *,
        limit: int = 8,
        language: str | None = None,
        source: Source | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._retriever = retriever
        self._limit = limit
        self._language = language
        self._source = source

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        # Sync path (rarely used by us — runner calls aquery → _aretrieve).
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._aretrieve(query_bundle))
        raise RuntimeError("TelcoLlamaRetriever: use async aquery/aretrieve")

    async def _aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        result = await self._retriever.retrieve(
            query_bundle.query_str,
            limit=self._limit,
            language=self._language,
            source=self._source,
        )
        return [_chunk_to_node(hit) for hit in result.hits]


def chunk_to_node(hit: StoredChunk) -> NodeWithScore:
    """Map StoredChunk → LlamaIndex TextNode + score (metadata keeps citations)."""
    node = TextNode(
        text=hit.text,
        id_=f"{hit.doc_id}:{hit.chunk_index}:{hit.language}",
        metadata={
            "doc_id": hit.doc_id,
            "chunk_index": hit.chunk_index,
            "title": hit.title,
            "section": hit.section,
            "source": hit.source,
            "language": hit.language,
            "family": hit.family,
        },
    )
    score = float(hit.score) if hit.score is not None else 0.0
    return NodeWithScore(node=node, score=score)


# Back-compat alias used inside TelcoLlamaRetriever
_chunk_to_node = chunk_to_node


class FixedNodesRetriever(BaseRetriever):
    """Return a precomputed node list (one retrieve, then LI synthesizes)."""

    def __init__(self, nodes: list[NodeWithScore], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._nodes = nodes

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        _ = query_bundle
        return list(self._nodes)

    async def _aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        _ = query_bundle
        return list(self._nodes)
