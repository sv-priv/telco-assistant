"""LlamaIndex runner: same Retriever/pgvector, LI QueryEngine for synthesis.

Retrieves once via the app Retriever, then uses LlamaIndex for response
synthesis only (no second embed store).
"""

from __future__ import annotations

import time
from typing import Any

from llama_index.core import get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.llms.openai import OpenAI

from app.chat.llm import ChatClient, ChatMessage
from app.chat.service import REWRITE_PROMPT, Citation, _fallback_search_query
from app.config import get_settings
from app.errors import AppError
from app.ingest.models import Source
from app.language import no_hit_answer
from app.retrieve.service import Retriever
from app.runners.llamaindex.adapters import FixedNodesRetriever, chunk_to_node
from app.runners.llamaindex.prompts import text_qa_template
from app.runners.protocol import AskResult, RunnerMode


class LlamaIndexRunner:
    mode: RunnerMode = "llamaindex"

    def __init__(self, retriever: Retriever, llm: ChatClient) -> None:
        self._retriever = retriever
        # ChatClient: follow-up rewrite only (same as Custom). Synthesis = LI OpenAI.
        self._llm = llm

    async def ask(
        self,
        question: str,
        *,
        limit: int = 8,
        language: str | None = None,
        source: Source | None = None,
        history: list[ChatMessage] | None = None,
    ) -> AskResult:
        history = history or []
        started = time.perf_counter()
        settings = get_settings()
        if not settings.openai_api_key:
            raise AppError(
                title="Missing API key",
                status=503,
                detail="OPENAI_API_KEY is not configured",
            )

        search_query = await self._standalone_query(question, history)
        trace: list[dict[str, Any]] = [
            {
                "step": "rewrite_query",
                "status": "ok" if history else "skipped",
                "query": search_query,
            }
        ]

        # One pgvector retrieve (same as Custom). Empty → hard IDK.
        retrieved = await self._retriever.retrieve(
            search_query,
            limit=limit,
            language=language,
            source=source,
        )
        if not retrieved.hits:
            return AskResult(
                mode=self.mode,
                question=question,
                answer=no_hit_answer(language),
                citations=[],
                trace=[
                    *trace,
                    {"step": "retrieve", "status": "empty"},
                    {"step": "synthesize", "status": "skipped"},
                ],
                latency_ms=(time.perf_counter() - started) * 1000,
            )

        # Hand hits to LlamaIndex as nodes — LI owns synthesis, not search.
        nodes = [chunk_to_node(hit) for hit in retrieved.hits]
        li_retriever = FixedNodesRetriever(nodes)
        llm = OpenAI(
            model=settings.chat_model,
            api_key=settings.openai_api_key,
            temperature=0.0,
        )
        synthesizer = get_response_synthesizer(
            llm=llm,
            response_mode=ResponseMode.COMPACT,
            text_qa_template=text_qa_template(language),
        )
        engine = RetrieverQueryEngine(
            retriever=li_retriever,
            response_synthesizer=synthesizer,
        )

        # aquery → fixed nodes → compact synthesize with OpenAI
        response = await engine.aquery(search_query)
        answer = str(response).strip()
        citations = _citations_from_response(response)
        trace.extend(
            [
                {
                    "step": "retrieve",
                    "status": "ok",
                    "hits": len(retrieved.hits),
                    "framework": "app.Retriever_pgvector",
                },
                {
                    "step": "synthesize",
                    "status": "ok",
                    "framework": "llamaindex_RetrieverQueryEngine",
                    "response_mode": "compact",
                },
            ]
        )
        return AskResult(
            mode=self.mode,
            question=question,
            answer=answer,
            citations=citations,
            trace=trace,
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    async def _standalone_query(
        self,
        question: str,
        history: list[ChatMessage],
    ) -> str:
        if not history:
            return question
        lines = ["Conversation:"]
        for msg in history[-6:]:
            label = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{label}: {msg.content}")
        lines.append(f"Latest: {question}")
        rewritten = await self._llm.complete(
            system=REWRITE_PROMPT,
            user="\n".join(lines),
        )
        cleaned = rewritten.strip().strip('"').strip("'")
        return cleaned or _fallback_search_query(question, history)


def _citations_from_response(response: Any) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, int, str]] = set()
    for item in getattr(response, "source_nodes", None) or []:
        meta = getattr(item.node, "metadata", {}) or {}
        doc_id = str(meta.get("doc_id") or "")
        if not doc_id:
            continue
        chunk_index = int(meta.get("chunk_index") or 0)
        language = str(meta.get("language") or "mk")
        key = (doc_id, chunk_index, language)
        if key in seen:
            continue
        seen.add(key)
        source_raw = str(meta.get("source") or "operator")
        allowed: dict[str, Source] = {
            "operator": "operator",
            "eu": "eu",
            "wb6": "wb6",
        }
        source = allowed.get(source_raw, "operator")
        score = getattr(item, "score", None)
        citations.append(
            Citation(
                doc_id=doc_id,
                chunk_index=chunk_index,
                title=str(meta.get("title") or doc_id),
                section=meta.get("section"),
                source=source,
                language=language,
                score=float(score) if score is not None else None,
            )
        )
    return citations
