"""Golden eval loaders + deterministic scorers (no live LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.chat.service import Citation
from app.eval.load import default_golden_path, load_golden
from app.eval.models import CaseScore, GoldenCase
from app.eval.score import score_case, summarize_by_category, summarize_mode
from app.main import create_app
from app.runners.protocol import AskResult


def test_golden_set_loads() -> None:
    cases = load_golden(default_golden_path())
    assert len(cases) >= 50
    ids = {c.id for c in cases}
    assert "refuse_xxl_mk" in ids
    assert "plan_xl_inclusions_mk" in ids
    categories = {c.category for c in cases}
    assert {
        "plan",
        "refuse",
        "roaming",
        "billing",
        "about",
        "followup",
        "network",
        "devices",
        "contract",
        "security",
        "addon",
        "support",
    } <= categories


def test_score_citation_and_contain() -> None:
    case = GoldenCase(
        id="xl",
        question="XL?",
        category="plan",
        expect_doc_ids=("op-cenovnik-xl-2026",),
        must_contain=("150", "1799"),
    )
    result = AskResult(
        mode="custom",
        question=case.question,
        answer="XL има FUP 150 GB и чини 1.799 ден. [op-cenovnik-xl-2026]",
        citations=[
            Citation(
                doc_id="op-cenovnik-xl-2026",
                chunk_index=0,
                title="XL",
                section=None,
                source="operator",
                language="mk",
                score=0.9,
            )
        ],
        latency_ms=12.0,
    )
    scored = score_case(case, result)
    assert scored.passed
    assert summarize_mode("custom", [scored]).citation_acc == 1.0


def test_score_refuse_xxl() -> None:
    case = GoldenCase(
        id="xxl",
        question="XXL?",
        category="refuse",
        must_refuse=True,
        must_not_cite=("op-cenovnik-xl-2026",),
        must_not_contain=("1799",),
    )
    bad = AskResult(
        mode="langchain",
        question=case.question,
        answer="Еве го XL планот со 1.799 ден.",
        citations=[
            Citation(
                doc_id="op-cenovnik-xl-2026",
                chunk_index=0,
                title="XL",
                section=None,
                source="operator",
                language="mk",
                score=0.9,
            )
        ],
    )
    assert not score_case(case, bad).passed

    good = AskResult(
        mode="langchain",
        question=case.question,
        answer="Plan 'XXL' is NOT offered. Available plans: S, M, L, XL only.",
        citations=[],
    )
    assert score_case(case, good).passed


def test_summarize_by_category() -> None:
    cases = [
        GoldenCase(id="a", question="?", category="plan", expect_doc_ids=("d",)),
        GoldenCase(id="b", question="?", category="refuse", must_refuse=True),
    ]
    scores = [
        CaseScore(
            case_id="a",
            mode="custom",
            passed=True,
            checks=[],
            latency_ms=1,
            cited_doc_ids=[],
            tool_calls=0,
            answer_preview="",
        ),
        CaseScore(
            case_id="b",
            mode="custom",
            passed=False,
            checks=[],
            latency_ms=1,
            cited_doc_ids=[],
            tool_calls=0,
            answer_preview="",
        ),
    ]
    by_cat = summarize_by_category(cases, {"custom": scores})
    assert by_cat["plan"]["custom"]["pass_rate"] == 1.0
    assert by_cat["refuse"]["custom"]["passed"] == 0


def test_eval_catalog() -> None:
    client = TestClient(create_app())
    res = client.get("/v1/eval/catalog")
    assert res.status_code == 200
    body = res.json()
    assert body["n"] >= 50
    assert any(c["id"] == "plan" for c in body["categories"])
    assert any(c["category"] == "refuse" for c in body["cases"])


def test_eval_latest_404_without_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "latest.json"
    monkeypatch.setattr("app.api.eval.default_report_path", lambda: missing)
    client = TestClient(create_app())
    res = client.get("/v1/eval/latest")
    assert res.status_code == 404


def test_eval_latest_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "latest.json"
    path.write_text(
        '{"generated_at":"t","golden_path":"g","modes":{},"retrieval":null,"cases":[]}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("app.api.eval.default_report_path", lambda: path)
    client = TestClient(create_app())
    res = client.get("/v1/eval/latest")
    assert res.status_code == 200
    assert res.json()["generated_at"] == "t"
