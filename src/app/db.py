"""Postgres DSN helpers (Render DATABASE_URL, SSL)."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def normalize_postgres_dsn(dsn: str) -> str:
    """Accept postgres:// or postgresql://; strip libpq sslmode for asyncpg."""
    text = dsn.strip()
    if text.startswith("postgres://"):
        text = "postgresql://" + text[len("postgres://") :]
    parsed = urlparse(text)
    query = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() != "sslmode"
    ]
    return urlunparse(parsed._replace(query=urlencode(query)))


def dsn_requires_ssl(dsn: str) -> bool:
    """True when the URL asks for SSL or looks like a managed host."""
    lower = dsn.lower()
    if "sslmode=require" in lower or "sslmode=verify" in lower or "ssl=true" in lower:
        return True
    host = (urlparse(dsn).hostname or "").lower()
    return host.endswith(".render.com") or "amazonaws.com" in host


def asyncpg_connect_kwargs(dsn: str) -> dict[str, Any]:
    """Kwargs for asyncpg.connect / create_pool."""
    normalized = normalize_postgres_dsn(dsn)
    kwargs: dict[str, Any] = {"dsn": normalized}
    if dsn_requires_ssl(dsn) or dsn_requires_ssl(normalized):
        kwargs["ssl"] = "require"
    return kwargs
