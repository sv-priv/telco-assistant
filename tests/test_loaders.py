"""Loader tests against a tiny fixture tree."""

from __future__ import annotations

from pathlib import Path

from app.ingest.loaders import load_documents

FIXTURE = """\
---
doc_id: op-demo
title: Demo plan
source: operator
authority: operator
family: price
language: mk
effective_date: 2026-01-01
status: in_force
---

# Demo plan

Body text for loading.
"""


def test_load_documents_normalises_frontmatter(tmp_path: Path) -> None:
    op = tmp_path / "operator" / "price"
    op.mkdir(parents=True)
    (op / "op-demo-mk.md").write_text(FIXTURE, encoding="utf-8")
    (tmp_path / "SOURCES.md").write_text("# skip\n", encoding="utf-8")

    docs = load_documents(tmp_path)

    assert len(docs) == 1
    doc = docs[0]
    assert doc.doc_id == "op-demo"
    assert doc.title == "Demo plan"
    assert doc.source == "operator"
    assert doc.language == "mk"
    assert doc.family == "price"
    assert doc.status == "in_force"
    assert doc.effective_date is not None
    assert doc.effective_date.isoformat() == "2026-01-01"
    assert "Body text for loading." in doc.body
    assert doc.body.lstrip().startswith("# Demo plan")


def test_load_documents_handles_missing_frontmatter(tmp_path: Path) -> None:
    wb = tmp_path / "wb6"
    wb.mkdir()
    (wb / "wbagreement.md").write_text("# Regional deal\n\nClause one.\n", encoding="utf-8")

    docs = load_documents(tmp_path, sources=["wb6"])

    assert len(docs) == 1
    assert docs[0].doc_id == "wbagreement"
    assert docs[0].source == "wb6"
    assert docs[0].title == "Regional deal"


def test_language_filter(tmp_path: Path) -> None:
    op = tmp_path / "operator" / "faq"
    op.mkdir(parents=True)
    (op / "a-mk.md").write_text(
        "---\ndoc_id: a\ntitle: A\nsource: operator\nauthority: operator\n"
        "family: faq\nlanguage: mk\neffective_date: 2026-01-01\nstatus: in_force\n---\n\n# A\n",
        encoding="utf-8",
    )
    (op / "b-en.md").write_text(
        "---\ndoc_id: b\ntitle: B\nsource: operator\nauthority: operator\n"
        "family: faq\nlanguage: en\neffective_date: 2026-01-01\nstatus: in_force\n---\n\n# B\n",
        encoding="utf-8",
    )

    docs = load_documents(tmp_path, languages=["mk"])
    assert [d.doc_id for d in docs] == ["a"]
