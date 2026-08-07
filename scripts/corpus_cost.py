#!/usr/bin/env python3
"""Rough corpus cost: text-embedding-3-small + gpt-4o-mini.

  python scripts/corpus_cost.py
  python scripts/corpus_cost.py --k 5 --answer-tokens 500
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import tiktoken
except ImportError:
    sys.exit("pip install tiktoken")

CORPUS = Path("data/corpus")
SKIP = {"SOURCES.md", "ARTICLE-INDEX.md"}

# Model -> (encoding, USD per million input, USD per million output)
# Verified against OpenAI's pricing page, August 2026. Re-check before quoting.
EMBED_MODEL = "text-embedding-3-small"
EMBED_ENCODING = "cl100k_base"
EMBED_USD_PER_M = 0.02

CHAT_MODEL = "gpt-4o-mini"
CHAT_ENCODING = "o200k_base"
CHAT_IN_USD_PER_M = 0.15
CHAT_OUT_USD_PER_M = 0.60

CONTEXT_WINDOW = 128_000

# Tokens spent per query that are not retrieved chunks: system prompt, tool
# schemas, the question itself, conversation so far. Measure yours and replace.
PROMPT_OVERHEAD = 1_200


def lang_of(p: Path) -> str:
    return "mk" if p.stem.endswith("-mk") else "en"


def money(v: float) -> str:
    """Costs here span six orders of magnitude, so a fixed precision lies."""
    if v >= 100:
        return f"${v:,.0f}"
    if v >= 1:
        return f"${v:,.2f}"
    if v >= 0.01:
        return f"${v:.3f}"
    return f"${v:.5f}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=5, help="chunks retrieved per query")
    ap.add_argument("--chunk-tokens", type=int, default=512, help="max tokens per chunk")
    ap.add_argument("--answer-tokens", type=int, default=500, help="expected output length")
    ap.add_argument("--queries-per-day", type=int, default=1000)
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    a = ap.parse_args()

    files = [f for f in sorted(a.corpus.rglob("*.md")) if f.name not in SKIP]
    if not files:
        sys.exit(f"no markdown under {a.corpus}")

    try:
        embed_enc = tiktoken.get_encoding(EMBED_ENCODING)
        chat_enc = tiktoken.get_encoding(CHAT_ENCODING)
    except Exception as e:  # noqa: BLE001
        sys.exit(
            f"could not load tokenizer: {e}\n"
            "tiktoken needs to download its vocabulary once. If the network is "
            "blocked, pre-fetch it and set TIKTOKEN_CACHE_DIR."
        )

    chars: dict[tuple[str, str], int] = defaultdict(int)
    e_toks: dict[tuple[str, str], int] = defaultdict(int)
    c_toks: dict[tuple[str, str], int] = defaultdict(int)
    count: dict[tuple[str, str], int] = defaultdict(int)
    sections: list[int] = []

    for f in files:
        layer = f.relative_to(a.corpus).parts[0]
        key = (layer, lang_of(f))
        text = f.read_text(encoding="utf-8", errors="replace")
        chars[key] += len(text)
        e_toks[key] += len(embed_enc.encode(text))
        c_toks[key] += len(chat_enc.encode(text))
        count[key] += 1

        body = re.sub(r"^---.*?^---\n", "", text, flags=re.S | re.M)
        for sec in re.split(r"^## ", body, flags=re.M)[1:]:
            if len(sec.strip()) > 20:
                sections.append(len(embed_enc.encode(sec)))

    E = sum(e_toks.values())
    C = sum(c_toks.values())

    # ── per layer and language ────────────────────────────────────────────
    print(f"CORPUS  {len(files)} files under {a.corpus}\n")
    print(f"{'layer':<11}{'lang':>5}{'files':>7}{'chars':>12}"
          f"{'cl100k':>10}{'o200k':>10}{'c/t mk-en':>11}")
    print("-" * 66)
    for key in sorted(e_toks, key=lambda k: -e_toks[k]):
        layer, lang = key
        print(f"{layer:<11}{lang:>5}{count[key]:>7}{chars[key]:>12,}"
              f"{e_toks[key]:>10,}{c_toks[key]:>10,}"
              f"{chars[key] / e_toks[key]:>11.2f}")
    print("-" * 66)
    print(f"{'TOTAL':<11}{'':>5}{len(files):>7}{sum(chars.values()):>12,}{E:>10,}{C:>10,}\n")

    # ── the fertility gap, which is why Macedonian costs more ─────────────
    per_lang_c: dict[str, int] = defaultdict(int)
    per_lang_t: dict[str, int] = defaultdict(int)
    for (layer, lang), t in e_toks.items():
        per_lang_c[lang] += chars[(layer, lang)]
        per_lang_t[lang] += t
    print("CHARS PER TOKEN, measured with cl100k_base")
    for lang in sorted(per_lang_t):
        print(f"  {lang}: {per_lang_c[lang] / per_lang_t[lang]:.2f}")
    if len(per_lang_t) > 1 and "mk" in per_lang_t and "en" in per_lang_t:
        mk = per_lang_c["mk"] / per_lang_t["mk"]
        en = per_lang_c["en"] / per_lang_t["en"]
        print(f"  Macedonian costs {en / mk:.1f}x the tokens of English per character.")
    print()

    # ── one-off ingest cost ───────────────────────────────────────────────
    ingest = E / 1e6 * EMBED_USD_PER_M
    print(f"INGEST  {EMBED_MODEL}")
    print(f"  {E:,} tokens x {money(EMBED_USD_PER_M)}/M = {money(ingest)}")
    print("  Paid once per full re-index. Changing the chunking re-pays it.\n")

    # ── per-query cost ────────────────────────────────────────────────────
    retrieved = a.k * a.chunk_tokens
    q_in = retrieved + PROMPT_OVERHEAD
    q_cost = q_in / 1e6 * CHAT_IN_USD_PER_M + a.answer_tokens / 1e6 * CHAT_OUT_USD_PER_M

    stuffed_in = C + PROMPT_OVERHEAD
    s_cost = stuffed_in / 1e6 * CHAT_IN_USD_PER_M + a.answer_tokens / 1e6 * CHAT_OUT_USD_PER_M

    print(f"PER QUERY  {CHAT_MODEL}  (in {money(CHAT_IN_USD_PER_M)}/M, "
          f"out {money(CHAT_OUT_USD_PER_M)}/M)")
    print(f"  {'':<22}{'input':>10}{'output':>9}{'cost':>12}")
    print(f"  {'RAG, k=' + str(a.k):<22}{q_in:>10,}{a.answer_tokens:>9,}{money(q_cost):>12}")
    print(f"  {'whole corpus':<22}{stuffed_in:>10,}{a.answer_tokens:>9,}{money(s_cost):>12}")
    print(f"  {'ratio':<22}{'':>10}{'':>9}{s_cost / q_cost:>11.0f}x\n")

    # ── annualised ────────────────────────────────────────────────────────
    n = a.queries_per_day * 365
    print(f"AT {a.queries_per_day:,} QUERIES/DAY")
    print(f"  RAG           {money(q_cost * n)}/year  (+ {money(ingest)} ingest)")
    print(f"  whole corpus  {money(s_cost * n)}/year")
    print(f"  saved         {money((s_cost - q_cost) * n)}/year\n")

    # ── does it even fit ──────────────────────────────────────────────────
    ratio = C / CONTEXT_WINDOW
    print(f"FIT  {C:,} tokens against a {CONTEXT_WINDOW:,} window = {ratio:.1f}x")
    if ratio > 1:
        print("  Does not fit. Retrieval is a constraint, not a preference.")
    elif ratio > 0.4:
        print("  Fits, but leaves little room. Retrieval is still the safer choice.")
    else:
        print("  Fits comfortably. Consider prompt caching instead of a vector store.")
    print()

    # ── chunk sizing, against the embedding tokenizer ─────────────────────
    if sections:
        vals = sorted(sections)

        def q(p: float) -> int:
            return vals[min(len(vals) - 1, int(len(vals) * p))]

        print(f"SECTIONS  {len(vals):,}, measured with {EMBED_ENCODING}")
        print(f"  p50 {q(.50):>5}   p75 {q(.75):>5}   p90 {q(.90):>5}"
              f"   p99 {q(.99):>5}   max {max(vals):>6}")
        over = sum(1 for v in vals if v > a.chunk_tokens)
        under = sum(1 for v in vals if v < 50)
        print(f"  over {a.chunk_tokens}: {over:,} ({over / len(vals) * 100:.1f}%) need splitting")
        print(f"  under 50:  {under:,} ({under / len(vals) * 100:.1f}%) worth merging")
        est_chunks = sum(max(1, -(-v // a.chunk_tokens)) for v in vals)
        print(f"  estimated chunks at {a.chunk_tokens} tokens: {est_chunks:,}")

    print("\nThese are measured, not estimated. Put the TOTAL and the FIT line in "
          "the README.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
