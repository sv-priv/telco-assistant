"""Load golden JSONL cases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, cast

from app.chat.llm import ChatMessage
from app.eval.models import EVAL_CATEGORIES, EvalCategory, GoldenCase

SourceLit = Literal["operator", "eu", "wb6"]


def default_golden_path() -> Path:
    # src/app/eval/load.py → repo root
    return Path(__file__).resolve().parents[3] / "data" / "eval" / "golden.jsonl"


def default_report_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "eval" / "latest.json"


def load_golden(path: Path) -> list[GoldenCase]:
    if not path.is_file():
        raise FileNotFoundError(f"Golden set not found: {path}")
    cases: list[GoldenCase] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON") from exc
            cases.append(_parse_case(payload, path=path, line_no=line_no))
    if not cases:
        raise ValueError(f"Golden set is empty: {path}")
    return cases


def _parse_case(payload: dict[str, Any], *, path: Path, line_no: int) -> GoldenCase:
    case_id = str(payload.get("id") or "").strip()
    question = str(payload.get("q") or payload.get("question") or "").strip()
    category_raw = str(payload.get("category") or "").strip()
    if not case_id or not question:
        raise ValueError(f"{path}:{line_no}: each case needs id and q")
    if category_raw not in EVAL_CATEGORIES:
        raise ValueError(
            f"{path}:{line_no}: category must be one of "
            f"{sorted(EVAL_CATEGORIES)}, got {category_raw!r}"
        )
    category = cast(EvalCategory, category_raw)

    source_raw = payload.get("source", "operator")
    source: SourceLit | None
    if source_raw is None:
        source = None
    elif source_raw in ("operator", "eu", "wb6"):
        source = cast(SourceLit, source_raw)
    else:
        raise ValueError(f"{path}:{line_no}: bad source {source_raw!r}")

    history_raw = payload.get("history") or []
    history: list[ChatMessage] = []
    for item in history_raw:
        role = item.get("role")
        content = item.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            raise ValueError(f"{path}:{line_no}: bad history entry")
        history.append(ChatMessage(role=role, content=content))

    return GoldenCase(
        id=case_id,
        question=question,
        category=category,
        language=_opt_str(payload.get("lang") or payload.get("language")),
        source=source,
        tags=tuple(str(t) for t in (payload.get("tags") or [])),
        expect_doc_ids=tuple(str(x) for x in (payload.get("expect_doc_ids") or [])),
        must_contain=tuple(str(x) for x in (payload.get("must_contain") or [])),
        must_not_contain=tuple(str(x) for x in (payload.get("must_not_contain") or [])),
        must_not_cite=tuple(str(x) for x in (payload.get("must_not_cite") or [])),
        must_refuse=bool(payload.get("must_refuse", False)),
        history=tuple(history),
    )


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
