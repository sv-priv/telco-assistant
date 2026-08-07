"""Retriever unit tests (fake embeddings + in-memory store)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.ingest.embeddings import FakeEmbeddingClient
from app.ingest.models import Chunk
from app.ingest.store import InMemoryVectorStore
from app.retrieve.service import Retriever


def _chunk(text: str, *, doc_id: str, language: str = "mk") -> Chunk:
    return Chunk(
        doc_id=doc_id,
        title=doc_id,
        source="operator",
        authority="operator",
        family="faq",
        language=language,
        effective_date=date(2026, 1, 1),
        status="in_force",
        path=Path("x.md"),
        chunk_index=0,
        section=None,
        text=text,
    )


@pytest.mark.asyncio
async def test_retrieve_ranks_relevant_chunk_first() -> None:
    store = InMemoryVectorStore()
    embedder = FakeEmbeddingClient(dimensions=32)
    await store.setup()
    chunks = [
        _chunk("roaming prices in Turkey and world zone", doc_id="roam"),
        _chunk("Skopje city coverage map", doc_id="cov"),
    ]
    vectors = await embedder.embed_texts([c.text for c in chunks])
    await store.upsert(chunks, vectors)

    result = await Retriever(store, embedder).retrieve(
        "Turkey roaming prices",
        limit=2,
    )
    assert len(result.hits) == 2
    assert result.hits[0].doc_id == "roam"


@pytest.mark.asyncio
async def test_retrieve_language_filter() -> None:
    store = InMemoryVectorStore()
    embedder = FakeEmbeddingClient(dimensions=32)
    await store.setup()
    chunks = [
        _chunk("same topic mk", doc_id="d", language="mk"),
        _chunk("same topic en", doc_id="d", language="en"),
    ]
    vectors = await embedder.embed_texts([c.text for c in chunks])
    await store.upsert(chunks, vectors)

    result = await Retriever(store, embedder).retrieve("same topic", language="en")
    assert len(result.hits) == 1
    assert result.hits[0].language == "en"
