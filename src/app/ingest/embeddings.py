"""Embedding clients (OpenAI + fake)."""

from __future__ import annotations

import hashlib
import math
import struct
from typing import Protocol, runtime_checkable

from openai import AsyncOpenAI


@runtime_checkable
class EmbeddingClient(Protocol):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """One vector per input text, same order."""
        ...


class OpenAIEmbeddingClient:
    """OpenAI embeddings API."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        batch_size: int = 64,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIEmbeddingClient")
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            response = await self._client.embeddings.create(
                model=self._model,
                input=batch,
                dimensions=self._dimensions,
            )
            ordered = sorted(response.data, key=lambda item: item.index)
            out.extend([list(item.embedding) for item in ordered])
        return out


class FakeEmbeddingClient:
    """Deterministic vectors for tests."""

    def __init__(self, dimensions: int = 32) -> None:
        self._dimensions = dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [_fake_vector(text, self._dimensions) for text in texts]


def _fake_vector(text: str, dimensions: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    seed = digest
    while len(values) < dimensions:
        seed = hashlib.sha256(seed).digest()
        for i in range(0, len(seed), 4):
            if len(values) >= dimensions:
                break
            (n,) = struct.unpack_from(">I", seed, i)
            values.append((n / 0xFFFFFFFF) * 2.0 - 1.0)
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]
