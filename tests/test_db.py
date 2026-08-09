"""Postgres DSN normalization for managed hosts (Render, etc.)."""

from __future__ import annotations

from app.db import asyncpg_connect_kwargs, dsn_requires_ssl, normalize_postgres_dsn


def test_normalize_postgres_scheme() -> None:
    assert normalize_postgres_dsn("postgres://u:p@h/db") == "postgresql://u:p@h/db"


def test_strips_sslmode() -> None:
    out = normalize_postgres_dsn("postgresql://u:p@h/db?sslmode=require")
    assert out == "postgresql://u:p@h/db"
    assert dsn_requires_ssl("postgresql://u:p@h/db?sslmode=require")


def test_render_host_implies_ssl() -> None:
    dsn = "postgresql://u:p@dpg-abc-a.oregon-postgres.render.com/telco"
    assert dsn_requires_ssl(dsn)
    kwargs = asyncpg_connect_kwargs(dsn)
    assert kwargs["ssl"] == "require"
    assert "sslmode" not in kwargs["dsn"]
