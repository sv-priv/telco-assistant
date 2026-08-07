"""ChatService tests (fake LLM + in-memory retrieval)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.chat.llm import FakeChatClient
from app.chat.service import ChatService
from app.ingest.embeddings import FakeEmbeddingClient
from app.ingest.models import Chunk
from app.ingest.store import InMemoryVectorStore
from app.retrieve.service import Retriever


def _chunk(text: str, *, doc_id: str) -> Chunk:
    return Chunk(
        doc_id=doc_id,
        title=doc_id,
        source="operator",
        authority="operator",
        family="roaming",
        language="mk",
        effective_date=date(2026, 1, 1),
        status="in_force",
        path=Path("x.md"),
        chunk_index=0,
        section=None,
        text=text,
    )


@pytest.mark.asyncio
async def test_ask_returns_answer_and_citations() -> None:
    store = InMemoryVectorStore()
    embedder = FakeEmbeddingClient(dimensions=32)
    await store.setup()
    chunks = [_chunk("Роаминг во Турција е во светска зона.", doc_id="op-roaming-2026")]
    vectors = await embedder.embed_texts([c.text for c in chunks])
    await store.upsert(chunks, vectors)

    llm = FakeChatClient(reply="Турција е светска зона [op-roaming-2026].")
    service = ChatService(Retriever(store, embedder), llm)
    result = await service.ask("Колку чини роаминг во Турција?")

    assert "Турција" in result.answer
    assert len(result.citations) == 1
    assert result.citations[0].doc_id == "op-roaming-2026"
    assert llm.last_user is not None
    assert "op-roaming-2026" in llm.last_user


@pytest.mark.asyncio
async def test_ask_with_no_hits() -> None:
    store = InMemoryVectorStore()
    embedder = FakeEmbeddingClient(dimensions=32)
    await store.setup()
    llm = FakeChatClient(reply="should not be called")
    service = ChatService(Retriever(store, embedder), llm)
    result = await service.ask("anything")
    assert result.citations == []
    assert "enough information" in result.answer.lower()
    assert llm.last_user is None
