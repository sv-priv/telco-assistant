"""Configuration loading tests (Secrets Manager via moto)."""

from __future__ import annotations

import json

import boto3
import pytest
from moto import mock_aws

from app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_builds_dsn_from_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "telco")
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("SECRETS_MANAGER_SECRET_ID", raising=False)

    settings = Settings()
    assert settings.postgres_user == "user"
    assert settings.postgres_password == "pass"
    assert settings.postgres_dsn == "postgresql://user:pass@db:5432/telco"
    assert settings.openai_api_key == "sk-test"


def test_settings_postgres_dsn_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://user:pass@db:5432/telco")
    monkeypatch.setenv("POSTGRES_USER", "ignored")
    monkeypatch.delenv("SECRETS_MANAGER_SECRET_ID", raising=False)

    settings = Settings()
    assert settings.postgres_dsn == "postgresql://user:pass@db:5432/telco"


@mock_aws
def test_settings_overlay_from_secrets_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    region = "eu-west-1"
    client = boto3.client("secretsmanager", region_name=region)
    client.create_secret(
        Name="telco/app",
        SecretString=json.dumps(
            {
                "OPENAI_API_KEY": "sk-from-sm",
                "POSTGRES_DSN": "postgresql://sm:sm@db:5432/telco",
            }
        ),
    )

    monkeypatch.setenv("SECRETS_MANAGER_SECRET_ID", "telco/app")
    monkeypatch.setenv("AWS_REGION", region)
    monkeypatch.setenv("AWS_DEFAULT_REGION", region)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("POSTGRES_DSN", raising=False)

    settings = get_settings()
    assert settings.openai_api_key == "sk-from-sm"
    assert settings.postgres_dsn == "postgresql://sm:sm@db:5432/telco"
