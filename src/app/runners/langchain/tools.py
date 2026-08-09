"""Agent tools over our existing Retriever / pgvector corpus.

Learning note
-------------
Tools are how an agent *acts*. The LLM does not search pgvector itself —
it chooses a tool + arguments; we run the tool and return text evidence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.tools import StructuredTool

from app.chat.service import Citation
from app.ingest.models import Source
from app.ingest.store import StoredChunk
from app.retrieve.service import Retriever

VALID_TIERS = frozenset({"S", "M", "L", "XL"})


def build_tools(
    retriever: Retriever,
    *,
    language: str | None,
    source: Source | None,
    limit: int,
    citations: list[Citation],
    on_tool: Callable[[dict[str, Any]], None],
) -> list[StructuredTool]:
    """Build LangChain tools closed over the shared Retriever + citation bucket."""

    async def search_docs(query: str) -> str:
        """Search Vardar Mobile / regulation docs for the query. Use for roaming,
        bills, FAQ, policies, or when you need evidence beyond a single plan card.
        Returns chunk text with doc_id tags for citations.
        """
        on_tool({"tool": "search_docs", "args": {"query": query}})
        result = await retriever.retrieve(
            query,
            limit=limit,
            language=language,
            source=source,
        )
        if not result.hits:
            return "No documents found for that query."
        _extend_citations(citations, result.hits)
        return _format_hits(result.hits)

    async def get_plan(tier: str) -> str:
        """Look up a tariff plan by exact name. Valid plans are only S, M, L, XL.
        Pass the user's tier string exactly (e.g. XXL or XS) — do not rewrite it to XL/S.
        Returns plan details, or a clear 'not offered' message for unknown names.
        """
        tier_u = str(tier).strip().upper()
        on_tool({"tool": "get_plan", "args": {"tier": tier_u}})
        if tier_u not in VALID_TIERS:
            return (
                f"Plan '{tier_u}' is NOT offered. Available plans: S, M, L, XL only. "
                f"Do not substitute another plan (e.g. do not treat XXL as XL or XS as S). "
                f"Tell the user '{tier_u}' does not exist and optionally list S/M/L/XL."
            )
        query = (
            f"тарифен план {tier_u} ценовник Вардар Мобилен {tier_u} што вклучува месечна претплата"
        )
        result = await retriever.retrieve(
            query,
            limit=max(limit, 8),
            language=language,
            source=source or "operator",
        )
        # Exact cenovnik match only — never fall back to a different tier's docs.
        preferred = [h for h in result.hits if f"cenovnik-{tier_u.lower()}-" in h.doc_id.lower()]
        if not preferred:
            return (
                f"No price-list document found for plan {tier_u}. "
                "Do not invent details or use another plan's document."
            )
        hits_sorted = sorted(
            preferred,
            key=lambda h: (0 if "2026" in h.doc_id else 1, -(h.score or 0.0)),
        )
        chosen = hits_sorted[:3]
        _extend_citations(citations, chosen)
        return _format_hits(chosen)

    async def list_plans() -> str:
        """List available Vardar Mobile tariff plans (S/M/L/XL) and high-level
        overview from FAQ / price docs.
        """
        on_tool({"tool": "list_plans", "args": {}})
        result = await retriever.retrieve(
            "тарифни планови S M L XL ценовник FAQ кои пакети",
            limit=limit,
            language=language,
            source=source or "operator",
        )
        if not result.hits:
            return "No plan overview documents found."
        _extend_citations(citations, result.hits)
        return _format_hits(result.hits)

    return [
        StructuredTool.from_function(
            coroutine=search_docs,
            name="search_docs",
            description=search_docs.__doc__ or "Search docs",
        ),
        StructuredTool.from_function(
            coroutine=get_plan,
            name="get_plan",
            description=get_plan.__doc__ or "Get plan details",
        ),
        StructuredTool.from_function(
            coroutine=list_plans,
            name="list_plans",
            description=list_plans.__doc__ or "List plans",
        ),
    ]


def _extend_citations(bucket: list[Citation], hits: list[StoredChunk]) -> None:
    seen = {(c.doc_id, c.chunk_index, c.language) for c in bucket}
    for hit in hits:
        key = (hit.doc_id, hit.chunk_index, hit.language)
        if key in seen:
            continue
        seen.add(key)
        bucket.append(
            Citation(
                doc_id=hit.doc_id,
                chunk_index=hit.chunk_index,
                title=hit.title,
                section=hit.section,
                source=hit.source,
                language=hit.language,
                score=hit.score,
            )
        )


def _format_hits(hits: list[StoredChunk]) -> str:
    parts: list[str] = []
    for hit in hits:
        section = f" | section={hit.section}" if hit.section else ""
        parts.append(f"[doc_id={hit.doc_id}] {hit.title}{section}\n{hit.text}")
    return "\n\n---\n\n".join(parts)
