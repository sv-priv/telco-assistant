#!/usr/bin/env python3
"""EUR-Lex HTML → markdown with ## article/recital headings.

  python scripts/convert_eurlex.py
  python scripts/convert_eurlex.py --check
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

EU = Path("data/corpus/eu")

# Known metadata per instrument. Keeps status/effective_date out of the parser.
META = {
    "32022R0612": {
        "title": "Regulation (EU) 2022/612 on roaming on public mobile communications networks (recast)",
        "family": "regulation", "effective_date": "2022-07-01", "status": "in_force",
    },
    "32012R0531": {
        "title": "Regulation (EU) 531/2012 on roaming on public mobile communications networks",
        "family": "regulation", "effective_date": "2012-07-01", "status": "repealed",
    },
    "32018L1972": {
        "title": "Directive (EU) 2018/1972 establishing the European Electronic Communications Code",
        "family": "directive", "effective_date": "2018-12-20", "status": "in_force",
    },
    "32015R2120": {
        "title": "Regulation (EU) 2015/2120 on open internet access",
        "family": "regulation", "effective_date": "2015-11-29", "status": "in_force",
    },
}

SKIP_TAGS = {"script", "style", "head", "nav", "noscript"}


@dataclass
class Section:
    kind: str          # recital | article | annex
    ref: str           # "Recital 12" | "Article 8" | "Annex I"
    title: str = ""
    parts: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        out, seen = [], set()
        for p in self.parts:
            p = re.sub(r"\s+", " ", EurLexParser._norm(p)).strip()
            if len(p) > 1 and p not in seen:
                seen.add(p)
                out.append(p)
        return "\n\n".join(out)


class EurLexParser(HTMLParser):
    """Walks the document, opening a Section whenever it meets a known div id."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sections: list[Section] = []
        self._cur: Section | None = None
        self._depth = 0          # div depth since the current section opened
        self._skip = 0
        self._cls: str | None = None
        self._buf: list[str] = []
        self._in_cell = False

    # ── helpers
    @staticmethod
    def _norm(t: str) -> str:
        """EUR-Lex mixes NBSP (\xa0) with regular spaces, inconsistently between
        documents. Left alone this silently breaks exact-match on references:
        'Article 5' never equals 'Article\xa05'."""
        return re.sub(r"[\u00a0\u202f\u2009\u200b]", " ", t)

    # Amending regulations quote the text they insert into another instrument.
    # EUR-Lex marks it with the same oj-ti-art class, so '‘Article 19' inside
    # Article 7 of 2015/2120 was overwriting the real ref and swallowing 25KB of
    # amending text under an article number that does not exist in that
    # regulation. Citing it would be citing nothing.
    _QUOTES = "‘’“”„«»'\""

    def _flush(self) -> None:
        txt = re.sub(r"[ \t]+", " ", self._norm("".join(self._buf))).strip()
        self._buf = []
        if not txt or self._cur is None:
            return
        if self._cls == "oj-ti-art":
            if txt[0] in self._QUOTES:
                self._cur.parts.append(txt)  # quoted insert, keep the id-derived ref
            else:
                self._cur.ref = txt
        elif self._cls == "oj-sti-art":
            if txt[0] not in self._QUOTES:
                self._cur.title = txt
            else:
                self._cur.parts.append(txt)
        else:
            self._cur.parts.append(txt)

    def _open(self, kind: str, ref: str) -> None:
        self._flush()
        self._cur = Section(kind=kind, ref=ref)
        self.sections.append(self._cur)
        self._depth = 0

    # ── HTMLParser interface
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in SKIP_TAGS:
            self._skip += 1
            return
        if self._skip:
            return
        a = dict(attrs)
        if tag == "div":
            did = a.get("id") or ""
            if m := re.fullmatch(r"rct_(\d+)", did):
                self._open("recital", f"Recital {int(m.group(1))}")
                return
            if m := re.fullmatch(r"art_(\w+)", did):
                self._open("article", f"Article {m.group(1)}")
                return
            if m := re.fullmatch(r"anx_(\w+)", did):
                self._open("annex", f"Annex {m.group(1)}")
                return
            if self._cur:
                self._depth += 1
        elif tag in ("p", "span", "td", "th", "li"):
            self._flush()
            self._cls = a.get("class")
            self._in_cell = tag in ("td", "th")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag in ("p", "span", "td", "th", "li"):
            if self._in_cell and self._buf:
                self._buf.append(" · ")
                self._in_cell = False
                return
            self._flush()
            self._cls = None
        elif tag == "div" and self._cur:
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip and self._cur is not None:
            self._buf.append(data)

    def close(self) -> None:  # type: ignore[override]
        self._flush()
        super().close()


def convert(path: Path) -> tuple[str, dict[str, int]]:
    celex, lang = path.stem.split("-")
    meta = META.get(celex, {"title": celex, "family": "regulation",
                            "effective_date": "1970-01-01", "status": "unknown"})

    p = EurLexParser()
    p.feed(path.read_text(encoding="utf-8", errors="replace"))
    p.close()

    keep = [s for s in p.sections if len(s.text) > 40]
    counts = {k: sum(1 for s in keep if s.kind == k) for k in ("recital", "article", "annex")}

    lines = [
        "---",
        f"doc_id: {celex}",
        f"title: {meta['title']}",
        "source: eur-lex",
        "authority: eu",
        f"family: {meta['family']}",
        f"language: {lang}",
        f"effective_date: {meta['effective_date']}",
        f"status: {meta['status']}",
        f"celex: {celex}",
        f"url: https://eur-lex.europa.eu/legal-content/{lang.upper()}/TXT/?uri=CELEX:{celex}",
        "licence: CC-BY-4.0",
        "---",
        "",
        f"# {meta['title']}",
        "",
    ]
    for s in keep:
        head = f"## {s.ref}" + (f" — {s.title}" if s.title else "")
        lines += [head, "", s.text, ""]
    return "\n".join(lines), counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report counts, write nothing")
    a = ap.parse_args()

    files = sorted(EU.glob("*.html"))
    if not files:
        print(f"No HTML in {EU}")
        return 1

    print(f"{'file':<24}{'recitals':>10}{'articles':>10}{'annexes':>9}{'chars out':>12}")
    print("-" * 65)
    for f in files:
        md, c = convert(f)
        print(f"{f.name:<24}{c['recital']:>10}{c['article']:>10}{c['annex']:>9}{len(md):>12,}")
        if not a.check:
            (f.with_suffix(".md")).write_text(md, encoding="utf-8")

    if a.check:
        print("\nCheck only. Re-run without --check to write .md files.")
    else:
        print(f"\nWrote {len(files)} markdown files alongside the HTML.")
        print("The HTML stays as the source of truth; the .md is derived.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
