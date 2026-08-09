"""ChatService tests (fake LLM + in-memory retrieval)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.chat.llm import ChatMessage, FakeChatClient
from app.chat.service import ChatService, _search_query
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
async def test_ask_no_hits_uses_mk_copy() -> None:
    store = InMemoryVectorStore()
    embedder = FakeEmbeddingClient(dimensions=32)
    await store.setup()
    service = ChatService(Retriever(store, embedder), FakeChatClient())
    result = await service.ask("непознато прашање xyz", language="mk")
    assert "Немам" in result.answer
    assert result.citations == []


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


def test_fallback_search_query_keeps_prior_topic() -> None:
    history = [
        ChatMessage(role="user", content="What is included in the XL plan?"),
        ChatMessage(role="assistant", content="XL includes…"),
    ]
    q = _search_query("a vo L", history)
    assert "a vo L" in q
    assert "XL plan" in q


@pytest.mark.asyncio
async def test_ask_rewrites_followup_then_answers() -> None:
    store = InMemoryVectorStore()
    embedder = FakeEmbeddingClient(dimensions=32)
    await store.setup()
    # Include rewrite terms so FakeEmbeddingClient can retrieve the chunk.
    chunks = [
        _chunk(
            "Што има во тарифен план L: 50GB and costs 1299 den.",
            doc_id="op-cenovnik-l",
        )
    ]
    vectors = await embedder.embed_texts([c.text for c in chunks])
    await store.upsert(chunks, vectors)

    # Fake LLM returns rewrite first, then the grounded answer.
    llm = FakeChatClient()
    replies = iter(
        [
            "Што има во тарифен план L",
            "L има 50GB [op-cenovnik-l].",
        ]
    )

    async def sequenced(*, system: str, user: str) -> str:
        llm.last_system = system
        llm.last_user = user
        return next(replies)

    llm.complete = sequenced  # type: ignore[method-assign]

    service = ChatService(Retriever(store, embedder), llm)
    result = await service.ask(
        "a vo L?",
        history=[
            ChatMessage(role="user", content="What is in XL?"),
            ChatMessage(role="assistant", content="XL has 150GB."),
        ],
    )
    assert "50GB" in result.answer or "op-cenovnik-l" in result.answer
    assert llm.last_user is not None
    assert "Conversation so far" in llm.last_user


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
