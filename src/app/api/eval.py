"""Serve golden catalog + latest scoreboard artifact."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.errors import AppError
from app.eval.load import default_golden_path, default_report_path, load_golden

router = APIRouter(tags=["eval"], dependencies=[Depends(require_api_key)])


@router.get("/v1/eval/catalog")
async def eval_catalog() -> dict[str, Any]:
    """Category taxonomy + case list from golden.jsonl (no LLM run needed)."""
    path = default_golden_path()
    try:
        cases = load_golden(path)
    except FileNotFoundError as exc:
        raise AppError(
            title="Golden set missing",
            status=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise AppError(
            title="Golden set invalid",
            status=500,
            detail=str(exc),
        ) from exc

    counts = Counter(c.category for c in cases)
    return {
        "golden_path": "data/eval/golden.jsonl",
        "n": len(cases),
        "categories": [{"id": cat, "n": counts[cat]} for cat in sorted(counts.keys())],
        "cases": [
            {
                "id": c.id,
                "category": c.category,
                "tags": list(c.tags),
                "q": c.question,
                "language": c.language,
                "must_refuse": c.must_refuse,
            }
            for c in cases
        ],
    }


@router.get("/v1/eval/latest")
async def eval_latest() -> dict[str, Any]:
    path = default_report_path()
    if not path.is_file():
        raise AppError(
            title="Eval report missing",
            status=404,
            detail=("No data/eval/latest.json yet. Run: uv run python -m app.eval --mode all"),
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AppError(
            title="Eval report invalid",
            status=500,
            detail=f"Could not parse {path.name}",
        ) from exc
    if not isinstance(payload, dict):
        raise AppError(
            title="Eval report invalid",
            status=500,
            detail="Report root must be a JSON object",
        )
    # Never expose absolute workstation paths from a prior local run.
    payload["golden_path"] = "data/eval/golden.jsonl"
    return payload
