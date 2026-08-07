#!/usr/bin/env python3
"""Token counts over data/corpus (tiktoken).

  python scripts/count_tokens.py
  python scripts/count_tokens.py --encoding o200k_base
  python scripts/count_tokens.py --sections
"""

from __future__ import annotations

import argparse
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

try:
    import tiktoken
except ImportError:
    sys.exit("pip install tiktoken")


class HFEncoder:
    """HuggingFace tokenizer with a tiktoken-like .encode()."""

    def __init__(self, name: str) -> None:
        try:
            from transformers import AutoTokenizer
        except ImportError:
            sys.exit("pip install transformers  (needed for --hf)")
        self.tok = AutoTokenizer.from_pretrained(name)

    def encode(self, text: str) -> list[int]:
        return self.tok.encode(text, add_special_tokens=False)

CORPUS = Path("data/corpus")
SKIP = {"SOURCES.md", "ARTICLE-INDEX.md"}

# The ratios used for estimation up to now, so we can report the error.
ASSUMED = {"en": 4.1, "mk": 2.1, "nl": 4.3}


def lang_of(p: Path) -> str:
    for suffix in ("mk", "nl", "en"):
        if p.stem.endswith(f"-{suffix}"):
            return suffix
    return "en"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--encoding", default="cl100k_base",
                    help="cl100k_base (embeddings) or o200k_base (gpt-4o)")
    ap.add_argument("--sections", action="store_true", help="per-section size distribution")
    ap.add_argument("--hf", metavar="MODEL",
                    help="use a HuggingFace tokenizer instead, e.g. BAAI/bge-m3 "
                         "or intfloat/multilingual-e5-large")
    a = ap.parse_args()

    if a.hf:
        enc = HFEncoder(a.hf)
        print(f"tokenizer: {a.hf} (HuggingFace)\n")
    else:
        enc = tiktoken.get_encoding(a.encoding)
        print(f"tokenizer: {a.encoding} (tiktoken)\n")

    files = [f for f in sorted(CORPUS.rglob("*.md")) if f.name not in SKIP]
    if not files:
        return sys.exit(f"no markdown under {CORPUS}")

    chars = defaultdict(int)
    toks = defaultdict(int)
    count = defaultdict(int)
    sections: list[tuple[str, str, int]] = []

    for f in files:
        layer = f.relative_to(CORPUS).parts[0]
        lang = lang_of(f)
        text = f.read_text(encoding="utf-8", errors="replace")
        n = len(enc.encode(text))
        key = (layer, lang)
        chars[key] += len(text)
        toks[key] += n
        count[key] += 1

        if a.sections:
            body = re.sub(r"^---.*?^---\n", "", text, flags=re.S | re.M)
            for sec in re.split(r"^## ", body, flags=re.M)[1:]:
                if len(sec.strip()) > 20:
                    sections.append((layer, lang, len(enc.encode(sec))))

    # ── per layer and language
    print(f"{'layer':<12}{'lang':>5}{'files':>7}{'chars':>12}{'tokens':>10}"
          f"{'c/t':>7}{'assumed':>9}{'err':>7}")
    print("-" * 71)
    tot_t = tot_c = 0
    for key in sorted(toks, key=lambda k: -toks[k]):
        layer, lang = key
        c, t = chars[key], toks[key]
        ratio = c / t
        est = c / ASSUMED[lang]
        err = (est - t) / t * 100
        tot_t += t
        tot_c += c
        print(f"{layer:<12}{lang:>5}{count[key]:>7}{c:>12,}{t:>10,}"
              f"{ratio:>7.2f}{ASSUMED[lang]:>9.1f}{err:>+6.0f}%")
    print("-" * 71)
    print(f"{'TOTAL':<12}{'':>5}{len(files):>7}{tot_c:>12,}{tot_t:>10,}\n")

    # ── measured chars per token, by language
    print("MEASURED chars per token")
    per_lang_c = defaultdict(int)
    per_lang_t = defaultdict(int)
    for (layer, lang), t in toks.items():
        per_lang_c[lang] += chars[(layer, lang)]
        per_lang_t[lang] += t
    for lang in sorted(per_lang_t):
        real = per_lang_c[lang] / per_lang_t[lang]
        print(f"  {lang}: {real:.2f}   (I assumed {ASSUMED[lang]}, "
              f"off by {(ASSUMED[lang]-real)/real*100:+.0f}%)")

    print(f"\n{tot_t:,} tokens = {tot_t/128_000:.1f}x a 128K context window")
    if not a.hf:
        print(f"embedding cost, text-embedding-3-small: ${tot_t/1e6*0.02:.3f}")
    else:
        print("self-hosted: no per-token cost")

    # ── section distribution, for chunk sizing
    if a.sections and sections:
        vals = sorted(s[2] for s in sections)
        q = lambda p: vals[min(len(vals) - 1, int(len(vals) * p))]  # noqa: E731
        print(f"\nSECTION SIZES ({len(vals):,} sections)")
        print(f"  p50 {st.median(vals):>6.0f}   p75 {q(.75):>6.0f}   p90 {q(.90):>6.0f}"
              f"   p99 {q(.99):>6.0f}   max {max(vals):>6.0f}")
        for cap in (256, 384, 512, 768, 1024):
            over = sum(1 for v in vals if v > cap)
            print(f"  over {cap:>4}: {over:>5} ({over/len(vals)*100:4.1f}%)")

    print("\nPut the TOTAL in the README. It is the number that justifies retrieval.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
