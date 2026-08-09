"""Ask API — multi-runner scaffold."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.chat import get_chat_llm
from app.chat.service import ChatResult, ChatService, Citation
from app.main import create_app
from app.retrieve.deps import get_embedder, get_store


async def _empty_store() -> AsyncIterator[object]:
    yield object()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_store] = _empty_store
    app.dependency_overrides[get_embedder] = lambda: object()
    app.dependency_overrides[get_chat_llm] = lambda: object()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ask_custom_mode(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask(self: ChatService, question: str, **kwargs: Any) -> ChatResult:
        return ChatResult(
            question=question,
            answer="custom ok",
            citations=[
                Citation(
                    doc_id="op-roaming-2026",
                    chunk_index=0,
                    title="Roaming",
                    section=None,
                    source="operator",
                    language="mk",
                    score=0.9,
                )
            ],
            hits=[],
        )

    monkeypatch.setattr(ChatService, "ask", fake_ask)

    response = await client.post(
        "/v1/ask",
        json={"question": "roaming", "mode": "custom", "language": "mk"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "custom"
    assert body["answer"] == "custom ok"
    assert body["trace"][0]["step"] == "custom_rag"


@pytest.mark.asyncio
async def test_ask_llamaindex_mode(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.runners.llamaindex.runner import LlamaIndexRunner
    from app.runners.protocol import AskResult

    async def fake_ask(self: LlamaIndexRunner, question: str, **kwargs: Any) -> AskResult:
        return AskResult(
            mode="llamaindex",
            question=question,
            answer="li ok",
            citations=[],
            trace=[{"step": "synthesize", "status": "ok"}],
            latency_ms=1.0,
        )

    monkeypatch.setattr(LlamaIndexRunner, "ask", fake_ask)

    response = await client.post(
        "/v1/ask",
        json={"question": "anything", "mode": "llamaindex"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "llamaindex"
    assert body["answer"] == "li ok"


@pytest.mark.asyncio
async def test_ask_langchain_mode(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.runners.langchain.runner import LangChainRunner
    from app.runners.protocol import AskResult

    async def fake_ask(self: LangChainRunner, question: str, **kwargs: Any) -> AskResult:
        return AskResult(
            mode="langchain",
            question=question,
            answer="agent ok",
            citations=[],
            trace=[
                {"step": "tool_call", "tool": "get_plan", "args": {"tier": "XL"}},
                {"step": "agent_finish", "status": "ok"},
            ],
            latency_ms=2.0,
        )

    monkeypatch.setattr(LangChainRunner, "ask", fake_ask)

    response = await client.post(
        "/v1/ask",
        json={"question": "anything", "mode": "langchain"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "langchain"
    assert body["answer"] == "agent ok"
    assert body["trace"][0]["tool"] == "get_plan"
