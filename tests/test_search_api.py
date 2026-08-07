"""Search API tests (dependencies overridden; no live DB / OpenAI)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.errors import AppError
from app.ingest.store import StoredChunk
from app.main import create_app
from app.retrieve import deps
from app.retrieve.deps import get_embedder, get_store
from app.retrieve.service import Retriever, RetrieveResult


async def _empty_store() -> AsyncIterator[object]:
    yield object()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_store] = _empty_store
    app.dependency_overrides[get_embedder] = lambda: object()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_search_returns_hits(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    hit = StoredChunk(
        doc_id="op-roaming-2026",
        chunk_index=0,
        language="mk",
        source="operator",
        title="Roaming",
        section=None,
        family="roaming",
        text="Roaming zones and prices",
        score=0.91,
    )

    async def fake_retrieve(self: Retriever, query: str, **kwargs: Any) -> RetrieveResult:
        return RetrieveResult(query=query, hits=[hit])

    monkeypatch.setattr(Retriever, "retrieve", fake_retrieve)

    response = await client.post(
        "/v1/search",
        json={"query": "roaming Turkey", "limit": 3, "language": "mk"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "roaming Turkey"
    assert len(body["hits"]) == 1
    assert body["hits"][0]["doc_id"] == "op-roaming-2026"
    assert body["hits"][0]["score"] == 0.91


@pytest.mark.asyncio
async def test_search_validation_empty_query(client: AsyncClient) -> None:
    response = await client.post("/v1/search", json={"query": ""})
    assert response.status_code == 422


def test_get_embedder_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        deps,
        "get_settings",
        lambda: type("S", (), {"openai_api_key": ""})(),
    )
    with pytest.raises(AppError) as exc:
        get_embedder()
    assert exc.value.status == 503
