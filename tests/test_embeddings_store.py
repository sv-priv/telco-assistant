"""Embedding + vector store tests (no network, no Postgres)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.ingest.embeddings import FakeEmbeddingClient
from app.ingest.models import Chunk
from app.ingest.pipeline import run_ingest
from app.ingest.store import InMemoryVectorStore


def _chunk(text: str, *, doc_id: str = "d1", index: int = 0, language: str = "mk") -> Chunk:
    return Chunk(
        doc_id=doc_id,
        title="T",
        source="operator",
        authority="operator",
        family="faq",
        language=language,
        effective_date=date(2026, 1, 1),
        status="in_force",
        path=Path("x.md"),
        chunk_index=index,
        section=None,
        text=text,
    )


@pytest.mark.asyncio
async def test_fake_embeddings_are_deterministic() -> None:
    client = FakeEmbeddingClient(dimensions=16)
    a = await client.embed_texts(["hello"])
    b = await client.embed_texts(["hello"])
    c = await client.embed_texts(["other"])
    assert a == b
    assert a[0] != c[0]
    assert len(a[0]) == 16


@pytest.mark.asyncio
async def test_memory_store_upsert_and_search() -> None:
    store = InMemoryVectorStore()
    embedder = FakeEmbeddingClient(dimensions=16)
    await store.setup()

    chunks = [
        _chunk("roaming in Turkey costs extra", doc_id="a"),
        _chunk("coverage in Skopje is strong", doc_id="b"),
    ]
    vectors = await embedder.embed_texts([c.text for c in chunks])
    assert await store.upsert(chunks, vectors) == 2
    assert await store.count() == 2

    query = (await embedder.embed_texts(["Turkey roaming charges"]))[0]
    hits = await store.search(query, limit=1)
    assert hits[0].doc_id == "a"


@pytest.mark.asyncio
async def test_run_ingest_with_fixture_corpus(tmp_path: Path) -> None:
    op = tmp_path / "operator" / "faq"
    op.mkdir(parents=True)
    (op / "demo-mk.md").write_text(
        "---\n"
        "doc_id: op-demo\n"
        "title: Demo\n"
        "source: operator\n"
        "authority: operator\n"
        "family: faq\n"
        "language: mk\n"
        "effective_date: 2026-01-01\n"
        "status: in_force\n"
        "---\n\n"
        "# Demo\n\nRoaming FAQ body.\n",
        encoding="utf-8",
    )

    store = InMemoryVectorStore()
    embedder = FakeEmbeddingClient(dimensions=16)
    result = await run_ingest(store, embedder, corpus_root=tmp_path, sources=["operator"])
    assert result.documents == 1
    assert result.chunks == 1
    assert result.upserted == 1
    assert result.store_count == 1
