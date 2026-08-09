"""Baseline runner: existing grounded ChatService pipeline."""

from __future__ import annotations

import time

from app.chat.llm import ChatClient, ChatMessage
from app.chat.service import ChatService
from app.ingest.models import Source
from app.retrieve.service import Retriever
from app.runners.protocol import AskResult, RunnerMode


class CustomRunner:
    mode: RunnerMode = "custom"

    def __init__(self, retriever: Retriever, llm: ChatClient) -> None:
        self._chat = ChatService(retriever, llm)

    async def ask(
        self,
        question: str,
        *,
        limit: int = 8,
        language: str | None = None,
        source: Source | None = None,
        history: list[ChatMessage] | None = None,
    ) -> AskResult:
        started = time.perf_counter()
        result = await self._chat.ask(
            question,
            limit=limit,
            language=language,
            source=source,
            history=history,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        return AskResult(
            mode=self.mode,
            question=result.question,
            answer=result.answer,
            citations=result.citations,
            trace=[{"step": "custom_rag", "status": "ok"}],
            latency_ms=latency_ms,
        )
