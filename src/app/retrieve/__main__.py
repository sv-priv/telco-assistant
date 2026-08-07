"""CLI: `python -m app.retrieve "how much is roaming in Turkey?"`."""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.config import get_settings
from app.ingest.embeddings import EmbeddingClient, FakeEmbeddingClient, OpenAIEmbeddingClient
from app.ingest.models import Source
from app.ingest.store import InMemoryVectorStore, PgVectorStore, VectorStore
from app.retrieve.service import Retriever


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vector search over ingested chunks")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--lang", default=None)
    parser.add_argument(
        "--source",
        choices=["operator", "eu", "wb6"],
        default=None,
    )
    parser.add_argument("--fake-embeddings", action="store_true")
    parser.add_argument("--memory-store", action="store_true")
    args = parser.parse_args(argv)
    return asyncio.run(_run(args))


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()

    embedder: EmbeddingClient
    if args.fake_embeddings:
        embedder = FakeEmbeddingClient(dimensions=settings.embedding_dimensions)
    else:
        if not settings.openai_api_key:
            print("ERROR: OPENAI_API_KEY is empty", file=sys.stderr)
            return 1
        embedder = OpenAIEmbeddingClient(
            settings.openai_api_key,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )

    pg: PgVectorStore | None = None
    store: VectorStore
    if args.memory_store or settings.vector_backend == "memory":
        mem = InMemoryVectorStore()
        await mem.setup()
        store = mem
    else:
        pg = PgVectorStore(
            settings.postgres_dsn,
            dimensions=settings.embedding_dimensions,
        )
        store = pg
        await pg.connect()

    source: Source | None = args.source
    try:
        result = await Retriever(store, embedder).retrieve(
            args.query,
            limit=args.limit,
            language=args.lang,
            source=source,
        )
    finally:
        if pg is not None:
            await pg.close()

    print(f"query: {result.query!r}  hits={len(result.hits)}")
    for i, hit in enumerate(result.hits, start=1):
        preview = " ".join(hit.text.split())[:140]
        print(
            f"{i}. score={hit.score:.4f}  {hit.doc_id}[{hit.chunk_index}] "
            f"{hit.source}/{hit.language}  {hit.title}"
        )
        if hit.section:
            print(f"   section: {hit.section}")
        print(f"   {preview}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
