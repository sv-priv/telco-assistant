"""LangChain tool wrappers over in-memory retrieval (no OpenAI agent loop)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.chat.service import Citation
from app.ingest.embeddings import FakeEmbeddingClient
from app.ingest.models import Chunk
from app.ingest.store import InMemoryVectorStore
from app.retrieve.service import Retriever
from app.runners.langchain.tools import build_tools


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
async def test_get_plan_tool_returns_cenovnik_text() -> None:
    store = InMemoryVectorStore()
    embedder = FakeEmbeddingClient(dimensions=32)
    await store.setup()
    chunks = [
        _chunk(
            "тарифен план XL ценовник Вардар Мобилен XL 150GB 1799",
            doc_id="op-cenovnik-xl-2026",
        )
    ]
    vectors = await embedder.embed_texts([c.text for c in chunks])
    await store.upsert(chunks, vectors)

    citations: list[Citation] = []
    events: list[dict[str, object]] = []
    tools = build_tools(
        Retriever(store, embedder),
        language="mk",
        source="operator",
        limit=5,
        citations=citations,
        on_tool=events.append,
    )
    get_plan = next(t for t in tools if t.name == "get_plan")
    text = await get_plan.ainvoke({"tier": "XL"})
    assert "150GB" in text or "1799" in text
    assert citations
    assert citations[0].doc_id == "op-cenovnik-xl-2026"
    assert events[0]["tool"] == "get_plan"


@pytest.mark.asyncio
async def test_get_plan_rejects_xxl_without_aliasing_to_xl() -> None:
    store = InMemoryVectorStore()
    embedder = FakeEmbeddingClient(dimensions=32)
    await store.setup()
    chunks = [
        _chunk(
            "тарифен план XL ценовник Вардар Мобилен XL 150GB 1799",
            doc_id="op-cenovnik-xl-2026",
        )
    ]
    vectors = await embedder.embed_texts([c.text for c in chunks])
    await store.upsert(chunks, vectors)

    citations: list[Citation] = []
    tools = build_tools(
        Retriever(store, embedder),
        language="mk",
        source="operator",
        limit=5,
        citations=citations,
        on_tool=lambda _e: None,
    )
    get_plan = next(t for t in tools if t.name == "get_plan")
    text = await get_plan.ainvoke({"tier": "XXL"})
    assert "NOT offered" in text
    assert "do not treat XXL as XL" in text.lower() or "Do not substitute" in text
    assert "150GB" not in text
    assert citations == []
