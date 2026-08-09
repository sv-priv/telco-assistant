"""Bilingual helpers + API language validation."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.chat import get_chat_llm
from app.language import grounding_system_prompt, no_hit_answer
from app.main import create_app
from app.retrieve.deps import get_embedder, get_store


def test_no_hit_mk_and_en() -> None:
    assert "Немам" in no_hit_answer("mk")
    assert "don't have enough" in no_hit_answer("en").lower()
    assert no_hit_answer(None) == no_hit_answer("en")


def test_grounding_prompt_forces_language() -> None:
    mk = grounding_system_prompt("mk")
    en = grounding_system_prompt("en")
    assert "Macedonian" in mk
    assert "Answer in English" in en


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
async def test_ask_rejects_unknown_language(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/ask",
        json={"question": "hi", "mode": "custom", "language": "de"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_rejects_unknown_language(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/search",
        json={"query": "hi", "language": "fr"},
    )
    assert response.status_code == 422
