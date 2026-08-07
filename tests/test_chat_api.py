"""Chat API tests (dependencies overridden)."""

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
async def test_chat_endpoint(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask(self: ChatService, question: str, **kwargs: Any) -> ChatResult:
        return ChatResult(
            question=question,
            answer="Roaming in Turkey is world-zone priced [op-roaming-2026].",
            citations=[
                Citation(
                    doc_id="op-roaming-2026",
                    chunk_index=0,
                    title="Roaming",
                    section=None,
                    source="operator",
                    language="mk",
                    score=0.88,
                )
            ],
            hits=[],
        )

    monkeypatch.setattr(ChatService, "ask", fake_ask)

    response = await client.post(
        "/v1/chat",
        json={"question": "roaming Turkey", "language": "mk"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "Turkey" in body["answer"]
    assert body["citations"][0]["doc_id"] == "op-roaming-2026"


@pytest.mark.asyncio
async def test_chat_validation(client: AsyncClient) -> None:
    response = await client.post("/v1/chat", json={"question": ""})
    assert response.status_code == 422
