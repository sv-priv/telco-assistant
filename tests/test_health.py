"""Health endpoint tests (dependencies mocked; no live database)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.health import DependencyHealth
from app.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_ok_when_dependencies_up(client: AsyncClient) -> None:
    up = DependencyHealth(status="up")
    with (
        patch("app.api.health._check_postgres", new=AsyncMock(return_value=up)),
        patch("app.api.health._check_pgvector", new=AsyncMock(return_value=up)),
    ):
        response = await client.get("/v1/health")

    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert body["status"] == "ok"
    assert body["dependencies"]["postgres"]["status"] == "up"
    assert body["dependencies"]["pgvector"]["status"] == "up"


@pytest.mark.asyncio
async def test_health_degraded_when_postgres_down(client: AsyncClient) -> None:
    down = DependencyHealth(status="down", detail="connection refused")
    up = DependencyHealth(status="up")
    with (
        patch("app.api.health._check_postgres", new=AsyncMock(return_value=down)),
        patch("app.api.health._check_pgvector", new=AsyncMock(return_value=up)),
    ):
        response = await client.get("/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["postgres"]["status"] == "down"


@pytest.mark.asyncio
async def test_unknown_route_returns_problem_json(client: AsyncClient) -> None:
    response = await client.get("/v1/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 404
    assert "title" in body
    assert "detail" in body
