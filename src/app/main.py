"""FastAPI application entrypoint."""

from __future__ import annotations

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


def create_app() -> FastAPI:
    settings = get_settings()
    docs_enabled = settings.is_local
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
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
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_local,
    )


if __name__ == "__main__":
    run()
