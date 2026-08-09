"""Search / retrieval HTTP API."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import require_api_key
from app.ingest.embeddings import EmbeddingClient
from app.ingest.models import Source
from app.ingest.store import VectorStore
from app.language import AppLanguage
from app.retrieve.deps import get_embedder, get_store
from app.retrieve.service import Retriever

router = APIRouter(tags=["search"], dependencies=[Depends(require_api_key)])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=50)
    language: AppLanguage | None = None
    source: Literal["operator", "eu", "wb6"] | None = None


class SearchHit(BaseModel):
    doc_id: str
    chunk_index: int
    language: str
    source: Source
    title: str
    section: str | None
    family: str
    score: float | None
    text: str


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


@router.post("/v1/search", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    store: Annotated[VectorStore, Depends(get_store)],
    embedder: Annotated[EmbeddingClient, Depends(get_embedder)],
) -> SearchResponse:
    retriever = Retriever(store, embedder)
    result = await retriever.retrieve(
        body.query,
        limit=body.limit,
        language=body.language,
        source=body.source,
    )
    return SearchResponse(
        query=result.query,
        hits=[
            SearchHit(
                doc_id=hit.doc_id,
                chunk_index=hit.chunk_index,
                language=hit.language,
                source=hit.source,
                title=hit.title,
                section=hit.section,
                family=hit.family,
                score=hit.score,
                text=hit.text,
            )
            for hit in result.hits
        ],
    )
