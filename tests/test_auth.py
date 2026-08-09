"""API key auth + rate limit."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.chat import get_chat_llm
from app.auth import reset_rate_limiter
from app.config import get_settings
from app.main import create_app
from app.retrieve.deps import get_embedder, get_store


@pytest.fixture(autouse=True)
def _clear() -> None:
    get_settings.cache_clear()
    reset_rate_limiter()
    yield
    get_settings.cache_clear()
    reset_rate_limiter()


async def _empty_store() -> AsyncIterator[object]:
    yield object()


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncClient]:
    monkeypatch.setenv("API_KEYS", "demo:test-secret")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "100")
    get_settings.cache_clear()

    app = create_app()
    app.dependency_overrides[get_store] = _empty_store
    app.dependency_overrides[get_embedder] = lambda: object()
    app.dependency_overrides[get_chat_llm] = lambda: object()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ask_requires_api_key(client: AsyncClient) -> None:
    res = await client.post("/v1/ask", json={"question": "hi", "mode": "custom"})
    assert res.status_code == 401
    assert "X-API-Key" in res.json()["detail"]


@pytest.mark.asyncio
async def test_ask_rejects_bad_key(client: AsyncClient) -> None:
    res = await client.post(
        "/v1/ask",
        json={"question": "hi", "mode": "custom"},
        headers={"X-API-Key": "wrong"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_eval_catalog_accepts_valid_key(
    client: AsyncClient,
) -> None:
    res = await client.get(
        "/v1/eval/catalog",
        headers={"X-API-Key": "test-secret"},
    )
    assert res.status_code == 200
    assert res.json()["n"] >= 1


@pytest.mark.asyncio
async def test_health_stays_public(client: AsyncClient) -> None:
    res = await client.get("/v1/health")
    # May be degraded without real postgres, but not 401.
    assert res.status_code != 401


@pytest.mark.asyncio
async def test_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEYS", "demo:limit-key")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    reset_rate_limiter()

    app = create_app()
    app.dependency_overrides[get_store] = _empty_store
    app.dependency_overrides[get_embedder] = lambda: object()
    app.dependency_overrides[get_chat_llm] = lambda: object()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"X-API-Key": "limit-key"}
        assert (await ac.get("/v1/eval/catalog", headers=headers)).status_code == 200
        assert (await ac.get("/v1/eval/catalog", headers=headers)).status_code == 200
        third = await ac.get("/v1/eval/catalog", headers=headers)
        assert third.status_code == 429
    app.dependency_overrides.clear()


def test_parse_api_keys_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEYS", "demo:abc,ci:xyz")
    monkeypatch.delenv("SECRETS_MANAGER_SECRET_ID", raising=False)
    get_settings.cache_clear()
    from app.config import Settings

    s = Settings()
    assert s.api_keys == {"demo": "abc", "ci": "xyz"}
