"""Shared-retriever metrics (same for all orchestration modes)."""

from __future__ import annotations

from app.eval.models import GoldenCase, RetrievalSummary
from app.retrieve.service import Retriever


async def evaluate_retrieval(
    cases: list[GoldenCase],
    retriever: Retriever,
    *,
    k: int = 8,
) -> RetrievalSummary:
    """Recall@k / MRR over cases that expect at least one doc_id."""
    scored = [c for c in cases if c.expect_doc_ids and not c.must_refuse]
    if not scored:
        return RetrievalSummary(n=0, k=k)

    recalls: list[float] = []
    rranks: list[float] = []
    for case in scored:
        result = await retriever.retrieve(
            case.question,
            limit=k,
            language=case.language,
            source=case.source,
        )
        hit_ids = [h.doc_id for h in result.hits]
        expected = set(case.expect_doc_ids)
        hit_expected = expected.intersection(hit_ids)
        recalls.append(1.0 if hit_expected else 0.0)

        rank = None
        for i, doc_id in enumerate(hit_ids, start=1):
            if doc_id in expected:
                rank = i
                break
        rranks.append(0.0 if rank is None else 1.0 / rank)

    n = len(scored)
    return RetrievalSummary(
        n=n,
        k=k,
        recall_at_k=sum(recalls) / n,
        mrr=sum(rranks) / n,
    )
