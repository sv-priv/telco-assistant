"""Grounded chat: retrieve chunks, then answer with citations."""

from __future__ import annotations

from dataclasses import dataclass

from app.chat.llm import ChatClient, ChatMessage
from app.ingest.models import Source
from app.ingest.store import StoredChunk
from app.retrieve.service import Retriever

SYSTEM_PROMPT = """\
You are a support assistant for Vardar Mobile (Вардар Мобиле), a fictional \
Macedonian mobile operator. Answer using ONLY the provided context snippets.

Rules:
- Resolve follow-ups using the conversation history (e.g. "and in L?" means \
the L plan after discussing XL).
- If the user asks broadly about Vardar Mobile / the operator and the context \
has product or FAQ snippets, give a short grounded overview of what those \
docs cover (plans, roaming, support). Do not invent company history, HQ, \
ownership, or unstated marketing claims.
- If the context is insufficient for the specific ask, say you don't have \
enough information and suggest a more concrete question (plans, roaming, bills).
- Do not invent prices, policies, or legal text.
- Prefer the customer's language when clear from the question.
- Cite sources inline like [doc_id] using the doc_id from each snippet.
- When context includes superseded/repealed law, prefer in-force sources.
"""

REWRITE_PROMPT = """\
Rewrite the latest user message as a standalone search query for a telecom \
knowledge base. Use the conversation to resolve short follow-ups \
(e.g. "a vo L" after an XL plan question → "What is included in the L plan?" / \
"Што има во тарифен план L").
When the user asks about S/M/L/XL packages (пакет/план), prefer wording like \
"тарифен план XL ценовник што вклучува" rather than only "XL пакет".
If the user asks generally about Vardar Mobile / the company / "tell me more" \
without naming a plan, search for operator overview / about FAQ / what services \
are offered — do NOT rewrite it into the previous plan tier.
Return ONLY the search query text. No quotes, no explanation.
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
        limit: int = 8,
        language: str | None = None,
        source: Source | None = None,
        history: list[ChatMessage] | None = None,
    ) -> ChatResult:
        history = history or []
        search_query = await self._standalone_query(question, history)
        retrieved = await self._retriever.retrieve(
            search_query,
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

        user_prompt = _build_user_prompt(question, hits, history)
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


def _fallback_search_query(question: str, history: list[ChatMessage]) -> str:
    prior = [m.content.strip() for m in history if m.role == "user" and m.content.strip()]
    if not prior:
        return question
    return f"{question}. Prior question: {prior[-1]}"


def _search_query(question: str, history: list[ChatMessage]) -> str:
    """Sync fallback used by unit tests / when rewrite is unavailable."""
    return _fallback_search_query(question, history)


def _build_user_prompt(
    question: str,
    hits: list[StoredChunk],
    history: list[ChatMessage],
) -> str:
    parts: list[str] = []
    if history:
        parts.append("Conversation so far:")
        for msg in history[-8:]:
            label = "User" if msg.role == "user" else "Assistant"
            parts.append(f"{label}: {msg.content}")
        parts.append("")

    parts.append("Context:")
    for i, hit in enumerate(hits, start=1):
        section = f" | section: {hit.section}" if hit.section else ""
        parts.append(
            f"[{i}] doc_id={hit.doc_id} | {hit.title}{section} | "
            f"source={hit.source} | language={hit.language}\n"
            f"{hit.text}"
        )
    parts.append(f"\nQuestion: {question}")
    return "\n\n".join(parts)
