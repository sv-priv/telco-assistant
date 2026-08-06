"""Liveness and dependency health checks."""

from __future__ import annotations

import asyncio
from typing import Literal

import asyncpg
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(tags=["health"])

DependencyStatus = Literal["up", "down", "skipped"]


class DependencyHealth(BaseModel):
    status: DependencyStatus
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    dependencies: dict[str, DependencyHealth]


async def _check_postgres(dsn: str) -> DependencyHealth:
    try:
        conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=2.0)
    except Exception as exc:  # noqa: BLE001
        return DependencyHealth(status="down", detail=str(exc))
    try:
        await conn.fetchval("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        return DependencyHealth(status="down", detail=str(exc))
    finally:
        await conn.close()
    return DependencyHealth(status="up")


async def _check_pgvector(dsn: str) -> DependencyHealth:
    """Return up when the Postgres `vector` extension is installed."""
    try:
        conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=2.0)
    except Exception as exc:  # noqa: BLE001
        return DependencyHealth(status="down", detail=str(exc))
    try:
        present = await conn.fetchval("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        if present is None:
            return DependencyHealth(
                status="down",
                detail="extension 'vector' not installed",
            )
    except Exception as exc:  # noqa: BLE001
        return DependencyHealth(status="down", detail=str(exc))
    finally:
        await conn.close()
    return DependencyHealth(status="up")


@router.get("/v1/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    postgres, pgvector = await asyncio.gather(
        _check_postgres(settings.postgres_dsn),
        _check_pgvector(settings.postgres_dsn),
    )
    dependencies = {"postgres": postgres, "pgvector": pgvector}
    degraded = any(dep.status == "down" for dep in dependencies.values())
    return HealthResponse(
        status="degraded" if degraded else "ok",
        service=settings.app_name,
        dependencies=dependencies,
    )
