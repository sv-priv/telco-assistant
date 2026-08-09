"""Execute golden cases against one or more runners and build a report."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.chat.llm import ChatClient
from app.eval.load import load_golden
from app.eval.models import CaseScore, EvalReport, GoldenCase
from app.eval.retrieve_metrics import evaluate_retrieval
from app.eval.score import score_case, score_error, summarize_by_category, summarize_mode
from app.retrieve.service import Retriever
from app.runners.protocol import RunnerMode
from app.runners.registry import get_runner


async def run_eval(
    *,
    golden_path: Path,
    modes: list[RunnerMode],
    retriever: Retriever,
    llm: ChatClient,
    limit: int = 8,
    max_cases: int | None = None,
    skip_answers: bool = False,
    skip_retrieval: bool = False,
) -> EvalReport:
    cases = load_golden(golden_path)
    if max_cases is not None:
        cases = cases[:max_cases]

    report = EvalReport(
        generated_at=datetime.now(UTC).isoformat(),
        # Repo-relative path only (avoid leaking absolute workstation paths).
        golden_path="data/eval/golden.jsonl",
    )
    print(
        f"eval: {len(cases)} cases × modes={','.join(modes)}",
        flush=True,
    )

    if not skip_retrieval:
        print("eval: retrieval metrics…", flush=True)
        report.retrieval = await evaluate_retrieval(cases, retriever, k=limit)
        if report.retrieval.n:
            print(
                f"eval: retrieval n={report.retrieval.n} "
                f"recall@k={report.retrieval.recall_at_k:.3f} "
                f"mrr={report.retrieval.mrr:.3f}",
                flush=True,
            )

    case_rows: dict[str, dict[str, Any]] = {
        c.id: {
            "id": c.id,
            "category": c.category,
            "tags": list(c.tags),
            "q": c.question,
            "modes": {},
        }
        for c in cases
    }

    scores_by_mode: dict[RunnerMode, list[CaseScore]] = {}
    if not skip_answers:
        for mode in modes:
            scores = await _run_mode(
                mode,
                cases,
                retriever=retriever,
                llm=llm,
                limit=limit,
            )
            scores_by_mode[mode] = scores
            report.modes[mode] = summarize_mode(mode, scores)
            for score in scores:
                case_rows[score.case_id]["modes"][mode] = _case_score_dict(score)
        report.by_category = summarize_by_category(cases, scores_by_mode)

    report.cases = list(case_rows.values())
    return report


async def _run_mode(
    mode: RunnerMode,
    cases: list[GoldenCase],
    *,
    retriever: Retriever,
    llm: ChatClient,
    limit: int,
) -> list[CaseScore]:
    runner = get_runner(mode, retriever=retriever, llm=llm)
    scores: list[CaseScore] = []
    total = len(cases)
    print(f"eval: mode={mode} ({total} cases)", flush=True)
    for i, case in enumerate(cases, start=1):
        try:
            result = await runner.ask(
                case.question,
                limit=limit,
                language=case.language,
                source=case.source,
                history=list(case.history) or None,
            )
            scored = score_case(case, result)
        except Exception as exc:  # noqa: BLE001 — eval must continue
            scored = score_error(case, mode, exc)
        scores.append(scored)
        mark = "ok" if scored.passed else "FAIL"
        print(
            f"  [{i}/{total}] {mode} {case.id} {mark} " f"{scored.latency_ms:.0f}ms",
            file=sys.stderr,
            flush=True,
        )
    return scores


def _case_score_dict(score: CaseScore) -> dict[str, Any]:
    return {
        "passed": score.passed,
        "latency_ms": round(score.latency_ms, 1),
        "cited_doc_ids": score.cited_doc_ids,
        "tool_calls": score.tool_calls,
        "checks": [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in score.checks],
        "answer_preview": score.answer_preview,
        "error": score.error,
    }
