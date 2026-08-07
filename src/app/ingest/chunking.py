"""Chunk documents: operator = whole file; eu/wb6 = split on ## (+ size cap)."""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.ingest.models import Chunk, Document

# Soft cap for a single section before we window-split it.
DEFAULT_MAX_CHARS = 3000
DEFAULT_OVERLAP = 200

_H2_RE = re.compile(r"^## .+$", re.MULTILINE)


def _chunk_from_doc(
    doc: Document,
    *,
    chunk_index: int,
    section: str | None,
    text: str,
) -> Chunk:
    return Chunk(
        doc_id=doc.doc_id,
        title=doc.title,
        source=doc.source,
        authority=doc.authority,
        family=doc.family,
        language=doc.language,
        effective_date=doc.effective_date,
        status=doc.status,
        path=doc.path,
        chunk_index=chunk_index,
        section=section,
        text=text.strip(),
        extras=dict(doc.extras),
    )


def _window_split(text: str, *, max_chars: int, overlap: int) -> list[str]:
    """Split long text into overlapping character windows."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # Prefer breaking on a paragraph or space near the end.
        if end < len(text):
            window = text[start:end]
            break_at = max(window.rfind("\n\n"), window.rfind("\n"), window.rfind(" "))
            if break_at > max_chars // 2:
                end = start + break_at
        piece = text[start:end].strip()
        if piece:
            parts.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return parts


def _split_on_h2(body: str) -> list[tuple[str | None, str]]:
    """Return (section_heading | None, text) parts from markdown body."""
    body = body.strip()
    if not body:
        return []

    matches = list(_H2_RE.finditer(body))
    if not matches:
        return [(None, body)]

    parts: list[tuple[str | None, str]] = []
    # Preamble before the first ## (often the H1 title)
    preamble = body[: matches[0].start()].strip()
    if preamble:
        parts.append((None, preamble))

    for i, match in enumerate(matches):
        heading = match.group(0)[3:].strip()  # drop leading "## "
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_text = body[start:end].strip()
        if section_text:
            parts.append((heading, section_text))
    return parts


def chunk_whole_document(doc: Document) -> list[Chunk]:
    """One chunk = whole operator file."""
    text = doc.body.strip()
    if not text:
        return []
    return [_chunk_from_doc(doc, chunk_index=0, section=None, text=text)]


def chunk_by_headings(
    doc: Document,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """One chunk per ## section (window if too long)."""
    chunks: list[Chunk] = []
    index = 0
    for section, text in _split_on_h2(doc.body):
        windows = _window_split(text, max_chars=max_chars, overlap=overlap)
        for window in windows:
            chunks.append(_chunk_from_doc(doc, chunk_index=index, section=section, text=window))
            index += 1
    return chunks


def chunk_document(
    doc: Document,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """Chunk using the policy for doc.source."""
    if doc.source == "operator":
        return chunk_whole_document(doc)
    return chunk_by_headings(doc, max_chars=max_chars, overlap=overlap)


def chunk_documents(
    docs: Iterable[Document],
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in docs:
        chunks.extend(chunk_document(doc, max_chars=max_chars, overlap=overlap))
    return chunks
