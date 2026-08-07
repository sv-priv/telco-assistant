"""End-to-end ingest: load → chunk → embed → upsert."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.ingest.chunking import chunk_documents
from app.ingest.embeddings import EmbeddingClient
from app.ingest.loaders import DEFAULT_CORPUS_ROOT, load_documents
from app.ingest.models import Source
from app.ingest.store import VectorStore


@dataclass(frozen=True)
class IngestResult:
    documents: int
    chunks: int
    upserted: int
    store_count: int


async def run_ingest(
    store: VectorStore,
    embedder: EmbeddingClient,
    *,
    corpus_root: Path = DEFAULT_CORPUS_ROOT,
    sources: list[Source] | None = None,
    languages: list[str] | None = None,
) -> IngestResult:
    docs = load_documents(corpus_root, sources=sources, languages=languages)
    chunks = chunk_documents(docs)
    await store.setup()

    texts = [c.text for c in chunks]
    embeddings = await embedder.embed_texts(texts)
    upserted = await store.upsert(chunks, embeddings)

    return IngestResult(
        documents=len(docs),
        chunks=len(chunks),
        upserted=upserted,
        store_count=await store.count(),
    )
