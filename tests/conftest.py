"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from app.auth import reset_rate_limiter
from app.config import get_settings


@pytest.fixture(autouse=True)
def _default_open_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep most tests open-auth unless they set API_KEYS themselves."""
    monkeypatch.setenv("API_KEYS", "")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1000")
    get_settings.cache_clear()
    reset_rate_limiter()
    yield
    get_settings.cache_clear()
    reset_rate_limiter()
