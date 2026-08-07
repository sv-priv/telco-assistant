"""Load corpus markdown into Document objects."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from datetime import date, datetime
from pathlib import Path

from app.ingest.models import Document, Source

DEFAULT_CORPUS_ROOT = Path("data/corpus")

SKIP_NAMES = frozenset(
    {
        "SOURCES.md",
        "ARTICLE-INDEX.md",
    }
)

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """Split flat `key: value` frontmatter from the body."""
    match = _FRONTMATTER_RE.match(raw)
    if match is None:
        return {}, raw.lstrip("\n")

    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, match.group(2).lstrip("\n")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None


def _source_from_path(path: Path, corpus_root: Path) -> Source:
    try:
        rel = path.relative_to(corpus_root)
    except ValueError:
        rel = path
    top = rel.parts[0] if rel.parts else ""
    if top == "operator":
        return "operator"
    if top == "eu":
        return "eu"
    if top == "wb6":
        return "wb6"
    raise ValueError(f"Unknown corpus layer for {path}")


def _document_from_markdown(path: Path, corpus_root: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    source = _source_from_path(path, corpus_root)

    # Files without frontmatter (e.g. wb6/wbagreement.md) still load.
    doc_id = meta.get("doc_id") or path.stem
    title = meta.get("title") or _title_from_body(body) or path.stem
    language = meta.get("language") or _guess_language(path)
    status = meta.get("status") or "in_force"
    authority = meta.get("authority") or source
    family = meta.get("family") or path.parent.name

    known = {
        "doc_id",
        "title",
        "source",
        "authority",
        "family",
        "language",
        "effective_date",
        "status",
    }
    extras = {k: v for k, v in meta.items() if k not in known}

    # Prefer path-derived source over frontmatter typos, but keep declared source in extras.
    declared = meta.get("source")
    if declared and declared not in {"operator", "eu", "wb6", "eur-lex"}:
        extras["declared_source"] = declared
    if declared == "eur-lex":
        # Normalise EUR-Lex label to our Source literal.
        pass

    return Document(
        doc_id=doc_id,
        title=title,
        source=source,
        authority=authority,
        family=family,
        language=language,
        effective_date=_parse_date(meta.get("effective_date")),
        status=status,
        path=path.resolve(),
        body=body,
        extras=extras,
    )


def _title_from_body(body: str) -> str | None:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _guess_language(path: Path) -> str:
    name = path.stem.lower()
    if name.endswith("-mk") or name.endswith("_mk"):
        return "mk"
    if name.endswith("-en") or name.endswith("_en"):
        return "en"
    if name.endswith("-nl") or name.endswith("_nl"):
        return "nl"
    return "und"


def iter_corpus_files(
    corpus_root: Path = DEFAULT_CORPUS_ROOT,
    *,
    sources: Iterable[Source] | None = None,
) -> Iterator[Path]:
    root = corpus_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Corpus root not found: {root}")

    wanted = set(sources) if sources is not None else None
    for path in sorted(root.rglob("*.md")):
        if path.name in SKIP_NAMES:
            continue
        try:
            source = _source_from_path(path, root)
        except ValueError:
            continue
        if wanted is not None and source not in wanted:
            continue
        yield path


def load_documents(
    corpus_root: Path = DEFAULT_CORPUS_ROOT,
    *,
    sources: Iterable[Source] | None = None,
    languages: Iterable[str] | None = None,
) -> list[Document]:
    """Load markdown files under corpus_root."""
    root = corpus_root.resolve()
    lang_filter = {lang.lower() for lang in languages} if languages is not None else None

    docs: list[Document] = []
    for path in iter_corpus_files(root, sources=sources):
        doc = _document_from_markdown(path, root)
        if lang_filter is not None and doc.language.lower() not in lang_filter:
            continue
        docs.append(doc)
    return docs
