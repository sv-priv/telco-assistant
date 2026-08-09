"""API key auth + in-memory rate limiting for /v1 routes."""

from __future__ import annotations

import time
from collections import deque
from typing import Annotated

from fastapi import Header, Request

from app.config import get_settings
from app.errors import AppError

_WINDOW_S = 60.0


class _RateLimiter:
    """Sliding-window limiter (process-local; use a shared store behind multiple replicas)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}

    def allow(self, identity: str, *, limit: int) -> bool:
        if limit <= 0:
            return True
        now = time.monotonic()
        bucket = self._hits.setdefault(identity, deque())
        while bucket and now - bucket[0] > _WINDOW_S:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


_limiter = _RateLimiter()


def reset_rate_limiter() -> None:
    """Test helper."""
    _limiter._hits.clear()


def _client_ip(request: Request, *, trust_proxy: bool) -> str:
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
) -> str | None:
    """Validate API key when configured; apply per-key (or IP) rate limit.

    Returns the key name (or None when auth is open / local without keys).
    """
    settings = get_settings()
    keys = settings.api_keys

    if keys:
        if not x_api_key or x_api_key not in keys.values():
            raise AppError(
                title="Unauthorized",
                status=401,
                detail="Missing or invalid X-API-Key header",
            )
        key_name = next(name for name, secret in keys.items() if secret == x_api_key)
        identity = f"key:{key_name}"
    else:
        # Open mode for local/dev only (production requires API_KEYS via Settings).
        key_name = None
        identity = f"ip:{_client_ip(request, trust_proxy=settings.trust_proxy)}"

    if not _limiter.allow(identity, limit=settings.rate_limit_per_minute):
        raise AppError(
            title="Rate limit exceeded",
            status=429,
            detail=(f"Too many requests. Limit is {settings.rate_limit_per_minute} per minute."),
        )
    return key_name
