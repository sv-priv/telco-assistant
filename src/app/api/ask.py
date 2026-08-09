"""Multi-runner ask API — pick orchestration mode, same corpus underneath."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.chat import CitationOut, HistoryMessage, get_chat_llm
from app.auth import require_api_key
from app.chat.llm import ChatClient, ChatMessage
from app.ingest.embeddings import EmbeddingClient
from app.ingest.store import VectorStore
from app.language import AppLanguage
from app.retrieve.deps import get_embedder, get_store
from app.retrieve.service import Retriever
from app.runners.protocol import RunnerMode
from app.runners.registry import get_runner

router = APIRouter(tags=["ask"], dependencies=[Depends(require_api_key)])


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    mode: RunnerMode = "custom"
    limit: int = Field(default=8, ge=1, le=20)
    language: AppLanguage | None = None
    source: Literal["operator", "eu", "wb6"] | None = None
    history: list[HistoryMessage] = Field(default_factory=list, max_length=16)


class AskResponse(BaseModel):
    mode: RunnerMode
    question: str
    answer: str
    citations: list[CitationOut]
    trace: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: float = 0.0


@router.post("/v1/ask", response_model=AskResponse)
async def ask(
    body: AskRequest,
    store: Annotated[VectorStore, Depends(get_store)],
    embedder: Annotated[EmbeddingClient, Depends(get_embedder)],
    llm: Annotated[ChatClient, Depends(get_chat_llm)],
) -> AskResponse:
    runner = get_runner(
        body.mode,
        retriever=Retriever(store, embedder),
        llm=llm,
    )
    result = await runner.ask(
        body.question,
        limit=body.limit,
        language=body.language,
        source=body.source,
        history=[ChatMessage(role=m.role, content=m.content) for m in body.history],
    )
    return AskResponse(
        mode=result.mode,
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
        trace=result.trace,
        latency_ms=result.latency_ms,
    )
