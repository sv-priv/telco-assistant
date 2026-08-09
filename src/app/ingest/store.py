"""Vector stores (pgvector + in-memory)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import asyncpg

from app.db import asyncpg_connect_kwargs
from app.ingest.models import Chunk, Source


@dataclass(frozen=True)
class StoredChunk:
    doc_id: str
    chunk_index: int
    language: str
    source: Source
    title: str
    section: str | None
    family: str
    text: str
    score: float | None = None


@runtime_checkable
class VectorStore(Protocol):
    async def setup(self) -> None: ...

    async def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int: ...

    async def delete_by_doc(self, doc_id: str, *, language: str | None = None) -> int: ...

    async def count(self) -> int: ...

    async def search(
        self,
        query_embedding: list[float],
        *,
        limit: int = 5,
        language: str | None = None,
        source: Source | None = None,
    ) -> list[StoredChunk]: ...


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


class InMemoryVectorStore:
    """In-memory cosine store for tests."""

    def __init__(self) -> None:
        self._rows: list[tuple[Chunk, list[float]]] = []

    async def setup(self) -> None:
        return None

    async def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        for chunk, emb in zip(chunks, embeddings, strict=True):
            self._rows = [
                row
                for row in self._rows
                if not (
                    row[0].doc_id == chunk.doc_id
                    and row[0].language == chunk.language
                    and row[0].chunk_index == chunk.chunk_index
                )
            ]
            self._rows.append((chunk, emb))
        return len(chunks)

    async def delete_by_doc(self, doc_id: str, *, language: str | None = None) -> int:
        before = len(self._rows)
        self._rows = [
            row
            for row in self._rows
            if row[0].doc_id != doc_id or (language is not None and row[0].language != language)
        ]
        return before - len(self._rows)

    async def count(self) -> int:
        return len(self._rows)

    async def search(
        self,
        query_embedding: list[float],
        *,
        limit: int = 5,
        language: str | None = None,
        source: Source | None = None,
    ) -> list[StoredChunk]:
        scored: list[tuple[float, Chunk]] = []
        for chunk, emb in self._rows:
            if language is not None and chunk.language != language:
                continue
            if source is not None and chunk.source != source:
                continue
            scored.append((_cosine(query_embedding, emb), chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            StoredChunk(
                doc_id=chunk.doc_id,
                chunk_index=chunk.chunk_index,
                language=chunk.language,
                source=chunk.source,
                title=chunk.title,
                section=chunk.section,
                family=chunk.family,
                text=chunk.text,
                score=score,
            )
            for score, chunk in scored[:limit]
        ]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class PgVectorStore:
    """Postgres + pgvector."""

    def __init__(self, dsn: str, *, dimensions: int = 1536) -> None:
        self._dsn = dsn
        self._dimensions = dimensions
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                min_size=1,
                max_size=5,
                **asyncpg_connect_kwargs(self._dsn),
            )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def setup(self) -> None:
        await self.connect()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    id BIGSERIAL PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    chunk_index INT NOT NULL,
                    language TEXT NOT NULL,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    section TEXT,
                    family TEXT NOT NULL,
                    authority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    effective_date DATE,
                    path TEXT NOT NULL,
                    text TEXT NOT NULL,
                    embedding vector({self._dimensions}) NOT NULL,
                    UNIQUE (doc_id, language, chunk_index)
                )
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
                ON chunks USING hnsw (embedding vector_cosine_ops)
                """
            )

    async def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        if not chunks:
            return 0
        await self.connect()
        assert self._pool is not None

        rows = [
            (
                chunk.doc_id,
                chunk.chunk_index,
                chunk.language,
                chunk.source,
                chunk.title,
                chunk.section,
                chunk.family,
                chunk.authority,
                chunk.status,
                chunk.effective_date,
                str(chunk.path),
                chunk.text,
                _vector_literal(emb),
            )
            for chunk, emb in zip(chunks, embeddings, strict=True)
        ]
        async with self._pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO chunks (
                    doc_id, chunk_index, language, source, title, section,
                    family, authority, status, effective_date, path, text, embedding
                ) VALUES (
                    $1, $2, $3, $4, $5, $6,
                    $7, $8, $9, $10, $11, $12, $13::vector
                )
                ON CONFLICT (doc_id, language, chunk_index) DO UPDATE SET
                    title = EXCLUDED.title,
                    section = EXCLUDED.section,
                    family = EXCLUDED.family,
                    authority = EXCLUDED.authority,
                    status = EXCLUDED.status,
                    effective_date = EXCLUDED.effective_date,
                    path = EXCLUDED.path,
                    text = EXCLUDED.text,
                    embedding = EXCLUDED.embedding
                """,
                rows,
            )
        return len(rows)

    async def delete_by_doc(self, doc_id: str, *, language: str | None = None) -> int:
        await self.connect()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            if language is None:
                result = await conn.execute("DELETE FROM chunks WHERE doc_id = $1", doc_id)
            else:
                result = await conn.execute(
                    "DELETE FROM chunks WHERE doc_id = $1 AND language = $2",
                    doc_id,
                    language,
                )
        # asyncpg returns status like "DELETE 3"
        return int(result.split()[-1])

    async def count(self) -> int:
        await self.connect()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            value = await conn.fetchval("SELECT COUNT(*) FROM chunks")
        return int(value or 0)

    async def search(
        self,
        query_embedding: list[float],
        *,
        limit: int = 5,
        language: str | None = None,
        source: Source | None = None,
    ) -> list[StoredChunk]:
        await self.connect()
        assert self._pool is not None
        clauses = ["TRUE"]
        args: list[object] = [_vector_literal(query_embedding), limit]
        # $1 = embedding, $2 = limit
        if language is not None:
            args.append(language)
            clauses.append(f"language = ${len(args)}")
        if source is not None:
            args.append(source)
            clauses.append(f"source = ${len(args)}")
        where = " AND ".join(clauses)
        sql = f"""
            SELECT doc_id, chunk_index, language, source, title, section, family, text,
                   1 - (embedding <=> $1::vector) AS score
            FROM chunks
            WHERE {where}
            ORDER BY embedding <=> $1::vector
            LIMIT $2
        """
        async with self._pool.acquire() as conn:
            records = await conn.fetch(sql, *args)
        return [
            StoredChunk(
                doc_id=r["doc_id"],
                chunk_index=r["chunk_index"],
                language=r["language"],
                source=r["source"],
                title=r["title"],
                section=r["section"],
                family=r["family"],
                text=r["text"],
                score=float(r["score"]) if r["score"] is not None else None,
            )
            for r in records
        ]
