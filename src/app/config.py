"""App settings from env / `.env`, optional AWS Secrets Manager overlay."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Annotated, Any, Literal, Self
from urllib.parse import quote_plus

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

logger = logging.getLogger(__name__)

VectorBackend = Literal["pgvector", "memory"]


def build_postgres_dsn(
    *,
    user: str,
    password: str,
    host: str,
    port: int,
    db: str,
) -> str:
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "telco-assistant"
    environment: str = "local"

    postgres_user: str = "telco"
    postgres_password: str = "telco"
    postgres_host: str = "localhost"
    postgres_port: int = 5433  # host; container is 5432
    postgres_db: str = "telco"
    postgres_dsn: str = ""  # if set, overrides the fields above

    vector_backend: VectorBackend = "pgvector"

    aws_region: str = "eu-west-1"
    secrets_manager_secret_id: str | None = None

    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    chat_model: str = "gpt-4o-mini"

    # name → secret. Env: JSON object or "demo:secret,ci:other" / bare "secret".
    # NoDecode: pydantic-settings would otherwise json.loads before our validator.
    api_keys: Annotated[dict[str, str], NoDecode] = Field(default_factory=dict)
    rate_limit_per_minute: int = 60
    # Comma-separated or JSON list. Browser origins allowed for CORS.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    # Only trust X-Forwarded-For when True (behind a known reverse proxy).
    trust_proxy: bool = False

    @field_validator("api_keys", mode="before")
    @classmethod
    def _parse_api_keys(cls, value: Any) -> dict[str, str]:
        if value is None or value == "":
            return {}
        if isinstance(value, dict):
            return {str(k): str(v) for k, v in value.items() if str(v)}
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return {}
            if text.startswith("{"):
                parsed = json.loads(text)
                if not isinstance(parsed, dict):
                    raise ValueError("API_KEYS JSON must be an object")
                return {str(k): str(v) for k, v in parsed.items() if str(v)}
            out: dict[str, str] = {}
            for part in text.split(","):
                item = part.strip()
                if not item:
                    continue
                if ":" in item:
                    name, secret = item.split(":", 1)
                    name, secret = name.strip(), secret.strip()
                    if name and secret:
                        out[name] = secret
                else:
                    out[item] = item
            return out
        raise TypeError("API_KEYS must be a dict, JSON object, or name:key list")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                parsed = json.loads(text)
                if not isinstance(parsed, list):
                    raise ValueError("CORS_ORIGINS JSON must be a list")
                return [str(v).strip() for v in parsed if str(v).strip()]
            return [part.strip() for part in text.split(",") if part.strip()]
        raise TypeError("CORS_ORIGINS must be a list or comma-separated string")

    @model_validator(mode="after")
    def _resolve_postgres_dsn(self) -> Self:
        if self.postgres_dsn:
            return self
        self.postgres_dsn = build_postgres_dsn(
            user=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            db=self.postgres_db,
        )
        return self

    @model_validator(mode="after")
    def _require_api_keys_outside_local(self) -> Self:
        env = self.environment.strip().lower()
        if env not in ("local", "dev", "test", "ci") and not self.api_keys:
            raise ValueError("API_KEYS must be set when ENVIRONMENT is not local/dev/test/ci")
        return self

    @property
    def is_local(self) -> bool:
        return self.environment.strip().lower() in ("local", "dev", "test", "ci")


def _load_from_secrets_manager(secret_id: str, region: str) -> dict[str, Any]:
    import boto3

    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_id)
    payload = response.get("SecretString") or "{}"
    data: dict[str, Any] = json.loads(payload)
    return data


_PART_FIELDS = (
    "postgres_user",
    "postgres_password",
    "postgres_host",
    "postgres_port",
    "postgres_db",
)


@lru_cache
def get_settings() -> Settings:
    """Cached settings."""
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
        "postgres_user": "postgres_user",
        "POSTGRES_USER": "postgres_user",
        "postgres_password": "postgres_password",
        "POSTGRES_PASSWORD": "postgres_password",
        "postgres_host": "postgres_host",
        "POSTGRES_HOST": "postgres_host",
        "postgres_port": "postgres_port",
        "POSTGRES_PORT": "postgres_port",
        "postgres_db": "postgres_db",
        "POSTGRES_DB": "postgres_db",
        "openai_api_key": "openai_api_key",
        "OPENAI_API_KEY": "openai_api_key",
        "vector_backend": "vector_backend",
        "VECTOR_BACKEND": "vector_backend",
        "api_keys": "api_keys",
        "API_KEYS": "api_keys",
        "rate_limit_per_minute": "rate_limit_per_minute",
        "RATE_LIMIT_PER_MINUTE": "rate_limit_per_minute",
    }
    for secret_key, field_name in key_map.items():
        if secret_key in secret and secret[secret_key]:
            overlays[field_name] = secret[secret_key]

    if not overlays:
        return base

    updated = base.model_copy(update=overlays)
    if "postgres_dsn" not in overlays and any(k in overlays for k in _PART_FIELDS):
        updated = updated.model_copy(
            update={
                "postgres_dsn": build_postgres_dsn(
                    user=updated.postgres_user,
                    password=updated.postgres_password,
                    host=updated.postgres_host,
                    port=int(updated.postgres_port),
                    db=updated.postgres_db,
                )
            }
        )
    return updated
