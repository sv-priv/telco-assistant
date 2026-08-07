"""Chunking tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.ingest.chunking import chunk_by_headings, chunk_document, chunk_whole_document
from app.ingest.models import Document


def _doc(**kwargs: object) -> Document:
    base: dict[str, object] = {
        "doc_id": "demo",
        "title": "Demo",
        "source": "operator",
        "authority": "operator",
        "family": "faq",
        "language": "en",
        "effective_date": date(2026, 1, 1),
        "status": "in_force",
        "path": Path("demo.md"),
        "body": "",
    }
    base.update(kwargs)
    return Document(**base)  # type: ignore[arg-type]


def test_operator_is_one_chunk() -> None:
    doc = _doc(
        source="operator",
        body="# Title\n\n## One\n\nHello\n\n## Two\n\nWorld\n",
    )
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].section is None
    assert "Hello" in chunks[0].text and "World" in chunks[0].text


def test_eu_splits_on_articles() -> None:
    doc = _doc(
        source="eu",
        doc_id="32022R0612",
        family="regulation",
        body=(
            "# Regulation\n\n"
            "## Recital 1\n\n"
            "Background text.\n\n"
            "## Article 1 — Subject matter\n\n"
            "This Regulation lays down rules.\n\n"
            "## Article 2 — Definitions\n\n"
            "'roaming' means …\n"
        ),
    )
    chunks = chunk_by_headings(doc)
    sections = [c.section for c in chunks]
    assert "Recital 1" in sections
    assert "Article 1 — Subject matter" in sections
    assert "Article 2 — Definitions" in sections
    assert chunks[0].doc_id == "32022R0612"


def test_oversized_section_is_windowed() -> None:
    long = "word " * 2000  # well over 3000 chars
    doc = _doc(
        source="eu",
        body=f"# Reg\n\n## Article 99\n\n{long}\n",
    )
    chunks = chunk_by_headings(doc, max_chars=1000, overlap=100)
    article_chunks = [c for c in chunks if c.section == "Article 99"]
    assert len(article_chunks) > 1
    assert all(c.char_count <= 1100 for c in article_chunks)


def test_whole_document_helper() -> None:
    doc = _doc(body="Only body")
    chunks = chunk_whole_document(doc)
    assert len(chunks) == 1
    assert chunks[0].text == "Only body"
