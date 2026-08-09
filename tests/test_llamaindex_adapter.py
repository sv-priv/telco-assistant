"""Unit tests for LlamaIndex BYO-retriever adapter (no OpenAI calls)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from llama_index.core.schema import QueryBundle

from app.ingest.embeddings import FakeEmbeddingClient
from app.ingest.models import Chunk
from app.ingest.store import InMemoryVectorStore
from app.retrieve.service import Retriever
from app.runners.llamaindex.adapters import TelcoLlamaRetriever


def _chunk(text: str, *, doc_id: str) -> Chunk:
    return Chunk(
        doc_id=doc_id,
        title=doc_id,
        source="operator",
        authority="operator",
        family="price",
        language="mk",
        effective_date=date(2026, 1, 1),
        status="in_force",
        path=Path("x.md"),
        chunk_index=0,
        section=None,
        text=text,
    )


@pytest.mark.asyncio
async def test_telco_llama_retriever_returns_nodes() -> None:
    store = InMemoryVectorStore()
    embedder = FakeEmbeddingClient(dimensions=32)
    await store.setup()
    chunks = [
        _chunk(
            "тарифен план XL ценовник 150GB",
            doc_id="op-cenovnik-xl-2026",
        )
    ]
    vectors = await embedder.embed_texts([c.text for c in chunks])
    await store.upsert(chunks, vectors)

    adapter = TelcoLlamaRetriever(
        Retriever(store, embedder),
        limit=3,
        language="mk",
    )
    nodes = await adapter._aretrieve(QueryBundle(query_str="XL ценовник"))
    assert nodes
    assert nodes[0].node.metadata["doc_id"] == "op-cenovnik-xl-2026"
    assert "150GB" in nodes[0].node.get_content()
