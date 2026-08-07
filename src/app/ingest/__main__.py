"""CLI: `python -m app.ingest` [--chunk] [--embed] [--fake-embeddings]."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter
from pathlib import Path

from app.config import get_settings
from app.ingest.chunking import chunk_documents
from app.ingest.embeddings import EmbeddingClient, FakeEmbeddingClient, OpenAIEmbeddingClient
from app.ingest.loaders import DEFAULT_CORPUS_ROOT, load_documents
from app.ingest.models import Chunk, Document, Source
from app.ingest.pipeline import run_ingest
from app.ingest.store import InMemoryVectorStore, PgVectorStore, VectorStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load, chunk, and embed corpus markdown")
    parser.add_argument("--root", type=Path, default=DEFAULT_CORPUS_ROOT)
    parser.add_argument(
        "--source",
        action="append",
        choices=["operator", "eu", "wb6"],
        help="Restrict to a corpus layer (repeatable)",
    )
    parser.add_argument(
        "--lang",
        action="append",
        help="Language filter, e.g. mk / en (repeatable)",
    )
    parser.add_argument("--chunk", action="store_true", help="Chunk and print stats")
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Embed chunks and upsert into the vector store",
    )
    parser.add_argument(
        "--fake-embeddings",
        action="store_true",
        help="Deterministic fake embeddings (no API key)",
    )
    parser.add_argument(
        "--memory-store",
        action="store_true",
        help="In-memory store instead of pgvector",
    )
    parser.add_argument("--sample", type=int, default=5)
    args = parser.parse_args(argv)

    sources: list[Source] | None = list(args.source) if args.source else None
    docs = load_documents(args.root, sources=sources, languages=args.lang)

    by_source: Counter[str] = Counter(d.source for d in docs)
    by_lang: Counter[str] = Counter(d.language for d in docs)

    print(f"Loaded {len(docs)} documents from {args.root}")
    print("By source:", dict(sorted(by_source.items())))
    print("By language:", dict(sorted(by_lang.items())))

    if not args.chunk and not args.embed:
        _print_doc_samples(docs, args.sample)
        return 0

    chunks = chunk_documents(docs)
    by_chunk_source: Counter[str] = Counter(c.source for c in chunks)
    print(f"Chunked into {len(chunks)} chunks", dict(sorted(by_chunk_source.items())))

    if args.chunk and not args.embed:
        _print_chunk_samples(chunks, args.sample)
        return 0

    return asyncio.run(_embed(args, sources))


async def _embed(args: argparse.Namespace, sources: list[Source] | None) -> int:
    settings = get_settings()

    embedder: EmbeddingClient
    if args.fake_embeddings:
        embedder = FakeEmbeddingClient(dimensions=settings.embedding_dimensions)
    else:
        if not settings.openai_api_key:
            print(
                "ERROR: OPENAI_API_KEY is empty.\n"
                "  Add it to .env, or re-run with --fake-embeddings for a dry run.",
                file=sys.stderr,
            )
            return 1
        embedder = OpenAIEmbeddingClient(
            settings.openai_api_key,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )

    store: VectorStore
    pg_store: PgVectorStore | None = None
    if args.memory_store or settings.vector_backend == "memory":
        store = InMemoryVectorStore()
    else:
        pg_store = PgVectorStore(
            settings.postgres_dsn,
            dimensions=settings.embedding_dimensions,
        )
        store = pg_store

    try:
        label = (
            "FakeEmbeddingClient"
            if isinstance(embedder, FakeEmbeddingClient)
            else settings.embedding_model
        )
        print(f"Embedding with {label} → {type(store).__name__}")
        result = await run_ingest(
            store,
            embedder,
            corpus_root=args.root,
            sources=sources,
            languages=args.lang,
        )
    finally:
        if pg_store is not None:
            await pg_store.close()

    print(
        f"Done: documents={result.documents} chunks={result.chunks} "
        f"upserted={result.upserted} store_count={result.store_count}"
    )
    return 0


def _print_doc_samples(docs: list[Document], sample: int) -> None:
    if sample <= 0 or not docs:
        return
    print(f"Sample documents ({min(sample, len(docs))}):")
    for doc in docs[:sample]:
        print(f"  - {doc.doc_id} [{doc.source}/{doc.language}] chars={doc.char_count}")


def _print_chunk_samples(chunks: list[Chunk], sample: int) -> None:
    if sample <= 0 or not chunks:
        return
    print(f"Sample chunks ({min(sample, len(chunks))}):")
    for chunk in chunks[:sample]:
        preview = " ".join(chunk.text.split())[:120]
        print(
            f"  - {chunk.doc_id}[{chunk.chunk_index}] "
            f"section={chunk.section!r} chars={chunk.char_count}"
        )
        print(f"      {preview!r}…")


if __name__ == "__main__":
    sys.exit(main())
