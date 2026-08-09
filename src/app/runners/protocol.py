"""Shared contract for orchestration runners (custom / LlamaIndex / LangChain)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from app.chat.llm import ChatMessage
from app.chat.service import Citation
from app.ingest.models import Source

RunnerMode = Literal["custom", "llamaindex", "langchain"]


@dataclass(frozen=True)
class AskResult:
    mode: RunnerMode
    question: str
    answer: str
    citations: list[Citation]
    trace: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0


@runtime_checkable
class Runner(Protocol):
    mode: RunnerMode

    async def ask(
        self,
        question: str,
        *,
        limit: int = 8,
        language: str | None = None,
        source: Source | None = None,
        history: list[ChatMessage] | None = None,
    ) -> AskResult: ...
