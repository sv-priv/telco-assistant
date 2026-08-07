"""Grounded chat: retrieve chunks, then answer with citations."""

from __future__ import annotations

from dataclasses import dataclass

from app.chat.llm import ChatClient
from app.ingest.models import Source
from app.ingest.store import StoredChunk
from app.retrieve.service import Retriever

SYSTEM_PROMPT = """\
You are a support assistant for Vardar Mobile (Вардар Мобиле), a fictional \
Macedonian mobile operator. Answer using ONLY the provided context snippets.

Rules:
- If the context is insufficient, say you don't have enough information.
- Do not invent prices, policies, or legal text.
- Prefer the customer's language when clear from the question.
- Cite sources inline like [doc_id] using the doc_id from each snippet.
- When context includes superseded/repealed law, prefer in-force sources.
"""


@dataclass(frozen=True)
class Citation:
    doc_id: str
    chunk_index: int
    title: str
    section: str | None
    source: Source
    language: str
    score: float | None


@dataclass(frozen=True)
class ChatResult:
    question: str
    answer: str
    citations: list[Citation]
    hits: list[StoredChunk]


class ChatService:
    def __init__(self, retriever: Retriever, llm: ChatClient) -> None:
        self._retriever = retriever
        self._llm = llm

    async def ask(
        self,
        question: str,
        *,
        limit: int = 5,
        language: str | None = None,
        source: Source | None = None,
    ) -> ChatResult:
        retrieved = await self._retriever.retrieve(
            question,
            limit=limit,
            language=language,
            source=source,
        )
        hits = retrieved.hits
        if not hits:
            return ChatResult(
                question=question,
                answer=("I don't have enough information in the knowledge base to answer that."),
                citations=[],
                hits=[],
            )

        user_prompt = _build_user_prompt(question, hits)
        answer = await self._llm.complete(system=SYSTEM_PROMPT, user=user_prompt)
        citations = [
            Citation(
                doc_id=hit.doc_id,
                chunk_index=hit.chunk_index,
                title=hit.title,
                section=hit.section,
                source=hit.source,
                language=hit.language,
                score=hit.score,
            )
            for hit in hits
        ]
        return ChatResult(
            question=question,
            answer=answer,
            citations=citations,
            hits=hits,
        )


def _build_user_prompt(question: str, hits: list[StoredChunk]) -> str:
    parts = ["Context:"]
    for i, hit in enumerate(hits, start=1):
        section = f" | section: {hit.section}" if hit.section else ""
        parts.append(
            f"[{i}] doc_id={hit.doc_id} | {hit.title}{section} | "
            f"source={hit.source} | language={hit.language}\n"
            f"{hit.text}"
        )
    parts.append(f"\nQuestion: {question}")
    return "\n\n".join(parts)
