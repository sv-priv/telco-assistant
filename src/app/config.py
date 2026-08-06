"""Application settings.

Local development reads environment variables and an optional `.env` file.
In production, set `SECRETS_MANAGER_SECRET_ID` to overlay values from AWS
Secrets Manager (IAM role; no secrets in the image or repository).
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

VectorBackend = Literal["pgvector", "memory"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "telco-assistant"
    environment: str = "local"

    # Host port 5433 maps to container 5432 (see docker-compose.yml).
    postgres_dsn: str = "postgresql://telco:telco@localhost:5433/telco"

    vector_backend: VectorBackend = "pgvector"

    aws_region: str = "eu-west-1"
    secrets_manager_secret_id: str | None = None

    openai_api_key: str = ""

    api_keys: dict[str, str] = Field(default_factory=dict)


def _load_from_secrets_manager(secret_id: str, region: str) -> dict[str, Any]:
    import boto3

    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_id)
    payload = response.get("SecretString") or "{}"
    data: dict[str, Any] = json.loads(payload)
    return data


@lru_cache
def get_settings() -> Settings:
    """Return cached settings, optionally overlaid from Secrets Manager."""
    base = Settings()
    if not base.secrets_manager_secret_id:
        return base

    try:
        secret = _load_from_secrets_manager(base.secrets_manager_secret_id, base.aws_region)
    except Exception:
        logger.exception("Failed to load secrets from Secrets Manager; using env/defaults")
        return base

    overlays: dict[str, Any] = {}
    key_map = {
        "postgres_dsn": "postgres_dsn",
        "POSTGRES_DSN": "postgres_dsn",
        "openai_api_key": "openai_api_key",
        "OPENAI_API_KEY": "openai_api_key",
        "vector_backend": "vector_backend",
        "VECTOR_BACKEND": "vector_backend",
    }
    for secret_key, field_name in key_map.items():
        if secret_key in secret and secret[secret_key]:
            overlays[field_name] = secret[secret_key]

    if not overlays:
        return base
    return base.model_copy(update=overlays)
