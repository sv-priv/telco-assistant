"""Light post-retrieval ranking for plan / package questions."""

from __future__ import annotations

import re

from app.ingest.store import StoredChunk
from app.retrieve.query_expand import is_plan_query, plan_tiers

_ADDON_RE = re.compile(
    r"dodatok|addon|додатен|додаток|roaming-pack|roam-pack|пакет-за-роаминг",
    re.I,
)
_CENOVNIK_RE = re.compile(r"cenovnik|ценовник", re.I)


def rerank_hits(query: str, hits: list[StoredChunk], *, limit: int) -> list[StoredChunk]:
    """Boost price-list plan docs; demote addons when the question is about plans."""
    if not hits or not is_plan_query(query):
        return hits[:limit]

    tiers = {t.lower() for t in plan_tiers(query)}
    scored: list[tuple[float, int, StoredChunk]] = []
    for index, hit in enumerate(hits):
        scored.append((_adjusted_score(hit, tiers), index, hit))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [hit for _, _, hit in scored[:limit]]


def _adjusted_score(hit: StoredChunk, tiers: set[str]) -> float:
    score = hit.score if hit.score is not None else 0.0
    doc = hit.doc_id.lower()
    title = hit.title.lower()
    blob = f"{doc} {title}"

    if hit.family == "price" or _CENOVNIK_RE.search(blob):
        score += 0.10
    if hit.family == "faq" and ("plan" in doc or "пакет" in title or "план" in title):
        score += 0.04
    if _ADDON_RE.search(blob):
        score -= 0.12

    if tiers:
        for tier in tiers:
            if f"-{tier}-" in f"-{doc}-" or f" {tier}" in f" {title}" or title.endswith(tier):
                score += 0.14
                break
        else:
            # Asking about a specific tier — soft-penalize other plan price lists
            if hit.family == "price" and _CENOVNIK_RE.search(blob):
                score -= 0.03

    # Prefer current-year price lists when present in the candidate pool
    if "2026" in doc and (hit.family == "price" or _CENOVNIK_RE.search(blob)):
        score += 0.05
    elif re.search(r"202[0-5]", doc) and hit.family == "price":
        score -= 0.04

    return score
