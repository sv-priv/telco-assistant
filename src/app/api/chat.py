"""Chat HTTP API."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import require_api_key
from app.chat.llm import ChatClient, ChatMessage, OpenAIChatClient
from app.chat.service import ChatService
from app.config import get_settings
from app.errors import AppError
from app.ingest.embeddings import EmbeddingClient
from app.ingest.models import Source
from app.ingest.store import VectorStore
from app.language import AppLanguage
from app.retrieve.deps import get_embedder, get_store
from app.retrieve.service import Retriever

router = APIRouter(tags=["chat"], dependencies=[Depends(require_api_key)])


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    limit: int = Field(default=8, ge=1, le=20)
    language: AppLanguage | None = None
    source: Literal["operator", "eu", "wb6"] | None = None
    history: list[HistoryMessage] = Field(default_factory=list, max_length=16)


class CitationOut(BaseModel):
    doc_id: str
    chunk_index: int
    title: str
    section: str | None
    source: Source
    language: str
    score: float | None


class ChatResponse(BaseModel):
    question: str
    answer: str
    citations: list[CitationOut]


def get_chat_llm() -> ChatClient:
    settings = get_settings()
    if not settings.openai_api_key:
        raise AppError(
            title="Missing API key",
            status=503,
            detail="OPENAI_API_KEY is not configured",
        )
    return OpenAIChatClient(settings.openai_api_key, model=settings.chat_model)


@router.post("/v1/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    store: Annotated[VectorStore, Depends(get_store)],
    embedder: Annotated[EmbeddingClient, Depends(get_embedder)],
    llm: Annotated[ChatClient, Depends(get_chat_llm)],
) -> ChatResponse:
    service = ChatService(Retriever(store, embedder), llm)
    result = await service.ask(
        body.question,
        limit=body.limit,
        language=body.language,
        source=body.source,
        history=[ChatMessage(role=m.role, content=m.content) for m in body.history],
    )
    return ChatResponse(
        question=result.question,
        answer=result.answer,
        citations=[
            CitationOut(
                doc_id=c.doc_id,
                chunk_index=c.chunk_index,
                title=c.title,
                section=c.section,
                source=c.source,
                language=c.language,
                score=c.score,
            )
            for c in result.citations
        ],
    )
