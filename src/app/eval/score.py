"""Deterministic scorers — you define pass criteria in the golden set."""

from __future__ import annotations

import re
import statistics
from collections.abc import Iterable

from app.eval.models import CaseScore, CheckResult, GoldenCase, ModeSummary
from app.runners.protocol import AskResult, RunnerMode

_NON_ALNUM = re.compile(r"[^0-9a-zа-яёќѓѕжчш]+", re.IGNORECASE)

_REFUSAL_MARKERS = (
    "not offered",
    "does not exist",
    "doesn't exist",
    "is not offered",
    "isn't offered",
    "not available",
    "no such plan",
    "не постои",
    "не е понуден",
    "не е понудена",
    "не нудиме",
    "не нуди",
    "немаме таков",
    "нема таков",
    "не е достапен",
    "не е достапна",
    "немаме план",
    "не понудуваме",
)


def score_case(case: GoldenCase, result: AskResult) -> CaseScore:
    cited = _cited_ids(result)
    answer = result.answer or ""
    checks: list[CheckResult] = []

    if case.expect_doc_ids:
        ok = any(doc_id in cited or f"[{doc_id}]" in answer for doc_id in case.expect_doc_ids)
        checks.append(
            CheckResult(
                name="citation",
                passed=ok,
                detail=(
                    f"expected one of {list(case.expect_doc_ids)}; cited={cited}"
                    if not ok
                    else "ok"
                ),
            )
        )

    if case.must_not_cite:
        bad = [d for d in case.must_not_cite if d in cited]
        checks.append(
            CheckResult(
                name="must_not_cite",
                passed=not bad,
                detail=f"forbidden cited: {bad}" if bad else "ok",
            )
        )

    if case.must_refuse:
        has_marker = any(m in answer.lower() for m in _REFUSAL_MARKERS)
        checks.append(
            CheckResult(
                name="refusal",
                passed=has_marker,
                detail="no refusal marker in answer" if not has_marker else "ok",
            )
        )

    if case.must_contain:
        missing = [s for s in case.must_contain if not _text_has(answer, s)]
        checks.append(
            CheckResult(
                name="must_contain",
                passed=not missing,
                detail=f"missing {missing}" if missing else "ok",
            )
        )

    if case.must_not_contain:
        found = [s for s in case.must_not_contain if _text_has(answer, s)]
        checks.append(
            CheckResult(
                name="must_not_contain",
                passed=not found,
                detail=f"forbidden text present: {found}" if found else "ok",
            )
        )

    if not checks:
        checks.append(
            CheckResult(
                name="citation",
                passed=False,
                detail="case has no scorable fields",
            )
        )

    passed = all(c.passed for c in checks)
    preview = " ".join(answer.split())
    if len(preview) > 180:
        preview = preview[:177] + "…"

    return CaseScore(
        case_id=case.id,
        mode=result.mode,
        passed=passed,
        checks=checks,
        latency_ms=result.latency_ms,
        cited_doc_ids=cited,
        tool_calls=_tool_call_count(result),
        answer_preview=preview,
    )


def score_error(case: GoldenCase, mode: RunnerMode, exc: BaseException) -> CaseScore:
    return CaseScore(
        case_id=case.id,
        mode=mode,
        passed=False,
        checks=[
            CheckResult(name="citation", passed=False, detail=f"runner error: {exc}"),
        ],
        latency_ms=0.0,
        cited_doc_ids=[],
        tool_calls=0,
        answer_preview="",
        error=str(exc),
    )


def summarize_by_category(
    cases: list[GoldenCase],
    scores_by_mode: dict[RunnerMode, list[CaseScore]],
) -> dict[str, dict[str, dict[str, float | int]]]:
    """category → mode → {n, passed, pass_rate}."""
    case_cat = {c.id: c.category for c in cases}
    out: dict[str, dict[str, dict[str, float | int]]] = {}
    for mode, scores in scores_by_mode.items():
        for score in scores:
            cat = case_cat.get(score.case_id, "plan")
            bucket = out.setdefault(cat, {}).setdefault(
                mode, {"n": 0, "passed": 0, "pass_rate": 0.0}
            )
            bucket["n"] = int(bucket["n"]) + 1
            if score.passed:
                bucket["passed"] = int(bucket["passed"]) + 1
    for cat_modes in out.values():
        for stats in cat_modes.values():
            n = int(stats["n"])
            stats["pass_rate"] = (int(stats["passed"]) / n) if n else 0.0
    return dict(sorted(out.items()))


def summarize_mode(mode: RunnerMode, scores: Iterable[CaseScore]) -> ModeSummary:
    items = list(scores)
    summary = ModeSummary(mode=mode, n=len(items), passed=sum(1 for s in items if s.passed))
    if summary.n:
        summary.pass_rate = summary.passed / summary.n

    citation = [s for s in items if _has_check(s, "citation")]
    summary.citation_n = len(citation)
    summary.citation_ok = sum(1 for s in citation if _check_ok(s, "citation"))
    if summary.citation_n:
        summary.citation_acc = summary.citation_ok / summary.citation_n

    refusal = [s for s in items if _has_check(s, "refusal")]
    summary.refusal_n = len(refusal)
    summary.refusal_ok = sum(1 for s in refusal if _check_ok(s, "refusal"))
    if summary.refusal_n:
        summary.refusal_acc = summary.refusal_ok / summary.refusal_n

    contain = [s for s in items if _has_check(s, "must_contain")]
    summary.contain_n = len(contain)
    summary.contain_ok = sum(1 for s in contain if _check_ok(s, "must_contain"))
    if summary.contain_n:
        summary.contain_acc = summary.contain_ok / summary.contain_n

    latencies = sorted(s.latency_ms for s in items if s.error is None)
    if latencies:
        summary.p50_latency_ms = float(statistics.median(latencies))
        idx = min(len(latencies) - 1, max(0, int(round(0.95 * (len(latencies) - 1)))))
        summary.p95_latency_ms = float(latencies[idx])

    if items:
        summary.avg_tool_calls = sum(s.tool_calls for s in items) / len(items)

    return summary


def _text_has(haystack: str, needle: str) -> bool:
    if needle.lower() in haystack.lower():
        return True
    # "1799" matches "1.799 ден" etc.
    return _NON_ALNUM.sub("", needle.lower()) in _NON_ALNUM.sub("", haystack.lower())


def _cited_ids(result: AskResult) -> list[str]:
    seen: list[str] = []
    for c in result.citations:
        if c.doc_id not in seen:
            seen.append(c.doc_id)
    return seen


def _tool_call_count(result: AskResult) -> int:
    return sum(1 for step in result.trace if step.get("tool"))


def _has_check(score: CaseScore, name: str) -> bool:
    return any(c.name == name for c in score.checks)


def _check_ok(score: CaseScore, name: str) -> bool:
    for c in score.checks:
        if c.name == name:
            return c.passed
    return False
