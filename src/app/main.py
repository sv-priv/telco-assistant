"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ask import router as ask_router
from app.api.chat import router as chat_router
from app.api.eval import router as eval_router
from app.api.health import router as health_router
from app.api.search import router as search_router
from app.config import get_settings
from app.errors import register_exception_handlers
from app.ingest.store import PgVectorStore

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.vector_backend == "pgvector":
        store = PgVectorStore(
            settings.postgres_dsn,
            dimensions=settings.embedding_dimensions,
        )
        try:
            await store.setup()
            logger.info("pgvector schema ready")
        except Exception:
            if settings.is_local:
                logger.exception("pgvector setup skipped (local/dev)")
            else:
                raise
        finally:
            await store.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    docs_enabled = settings.is_local
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(search_router)
    app.include_router(chat_router)
    app.include_router(ask_router)
    app.include_router(eval_router)
    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.is_local,
    )


if __name__ == "__main__":
    run()
