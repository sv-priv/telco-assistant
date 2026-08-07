"""Shared FastAPI dependencies for retrieval."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.config import get_settings
from app.errors import AppError
from app.ingest.embeddings import EmbeddingClient, OpenAIEmbeddingClient
from app.ingest.store import PgVectorStore, VectorStore


def get_embedder() -> EmbeddingClient:
    settings = get_settings()
    if not settings.openai_api_key:
        raise AppError(
            title="Missing API key",
            status=503,
            detail="OPENAI_API_KEY is not configured",
        )
    return OpenAIEmbeddingClient(
        settings.openai_api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )


async def get_store() -> AsyncIterator[VectorStore]:
    settings = get_settings()
    store = PgVectorStore(
        settings.postgres_dsn,
        dimensions=settings.embedding_dimensions,
    )
    await store.connect()
    try:
        yield store
    finally:
        await store.close()
