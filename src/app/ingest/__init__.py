"""Ingestion package: load → chunk → embed → store."""

from app.ingest.chunking import chunk_document, chunk_documents
from app.ingest.embeddings import EmbeddingClient, FakeEmbeddingClient, OpenAIEmbeddingClient
from app.ingest.loaders import load_documents
from app.ingest.models import Chunk, Document
from app.ingest.pipeline import IngestResult, run_ingest
from app.ingest.store import InMemoryVectorStore, PgVectorStore, VectorStore

__all__ = [
    "Chunk",
    "Document",
    "EmbeddingClient",
    "FakeEmbeddingClient",
    "IngestResult",
    "InMemoryVectorStore",
    "OpenAIEmbeddingClient",
    "PgVectorStore",
    "VectorStore",
    "chunk_document",
    "chunk_documents",
    "load_documents",
    "run_ingest",
]
