"""CLI: `uv run python -m app.eval --mode all`."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.chat.llm import ChatClient, OpenAIChatClient
from app.config import get_settings
from app.eval.load import default_golden_path, default_report_path, load_golden
from app.eval.run import run_eval
from app.ingest.embeddings import EmbeddingClient, OpenAIEmbeddingClient
from app.ingest.store import PgVectorStore
from app.retrieve.service import Retriever
from app.runners.protocol import RunnerMode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Golden-set benchmark across orchestration runners",
    )
    parser.add_argument(
        "--mode",
        choices=["custom", "llamaindex", "langchain", "all"],
        default="custom",
        help="Which runner(s) to score (default: custom)",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=None,
        help="Path to golden.jsonl (default: data/eval/golden.jsonl)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write report JSON (default: data/eval/latest.json)",
    )
    parser.add_argument("--limit", type=int, default=8, help="Retrieve / ask limit")
    parser.add_argument("--max-cases", type=int, default=None, help="Smoke: first N cases")
    parser.add_argument(
        "--skip-answers",
        action="store_true",
        help="Only run shared retrieval metrics (no LLM answers)",
    )
    parser.add_argument(
        "--skip-retrieval",
        action="store_true",
        help="Skip Recall@k / MRR track",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Only load/validate the golden set, then exit",
    )
    args = parser.parse_args(argv)
    return asyncio.run(_run(args))


async def _run(args: argparse.Namespace) -> int:
    golden = args.golden or default_golden_path()
    out = args.out or default_report_path()

    if args.validate:
        cases = load_golden(golden)
        from collections import Counter

        by_cat = Counter(c.category for c in cases)
        print(f"OK: {len(cases)} golden cases in {golden}")
        for cat, n in sorted(by_cat.items()):
            print(f"  {cat:10} {n}")
        return 0

    settings = get_settings()
    if not settings.openai_api_key:
        print("ERROR: OPENAI_API_KEY is empty", file=sys.stderr)
        return 1

    modes: list[RunnerMode] = (
        ["custom", "llamaindex", "langchain"] if args.mode == "all" else [args.mode]
    )

    embedder: EmbeddingClient = OpenAIEmbeddingClient(
        settings.openai_api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    llm: ChatClient = OpenAIChatClient(
        settings.openai_api_key,
        model=settings.chat_model,
    )

    store = PgVectorStore(
        settings.postgres_dsn,
        dimensions=settings.embedding_dimensions,
    )
    await store.connect()
    try:
        report = await run_eval(
            golden_path=golden,
            modes=modes,
            retriever=Retriever(store, embedder),
            llm=llm,
            limit=args.limit,
            max_cases=args.max_cases,
            skip_answers=args.skip_answers,
            skip_retrieval=args.skip_retrieval,
        )
    finally:
        await store.close()

    out.parent.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _print_summary(payload, out)
    return 0


def _print_summary(payload: dict[str, object], out: Path) -> None:
    print(f"Wrote {out}")
    retrieval = payload.get("retrieval")
    if isinstance(retrieval, dict) and retrieval.get("n"):
        print(
            "retrieval "
            f"n={retrieval['n']} k={retrieval['k']} "
            f"recall@k={retrieval['recall_at_k']:.3f} "
            f"mrr={retrieval['mrr']:.3f}"
        )
    modes = payload.get("modes")
    if not isinstance(modes, dict):
        return
    for mode, summary in modes.items():
        if not isinstance(summary, dict):
            continue
        print(
            f"{mode:10} pass={summary.get('pass_rate')} "
            f"citation={summary.get('citation_acc')} "
            f"refusal={summary.get('refusal_acc')} "
            f"p50_ms={summary.get('p50_latency_ms')}"
        )


if __name__ == "__main__":
    sys.exit(main())
