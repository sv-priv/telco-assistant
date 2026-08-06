# telco-assistant

Work-in-progress assistant for a fictional Macedonian mobile operator
(**Вардар Мобиле / Vardar Mobile**). The main knowledge base is a large
**synthetic** operator corpus (plans, roaming, devices, billing, campaigns,
support) in Macedonian and English. A smaller layer of real public regulation
(EU acquis + Western Balkans roaming) sits underneath for policy-style
questions. Safety-gated account tools and evaluation come in later phases.

**Current status:** Phase 0 scaffold is in place (FastAPI health, Postgres +
pgvector, lint/type/test CI). Corpus documents are in the repo. Ingestion,
retrieval, chat, and the agent loop are not implemented yet.

## Stack

- Python 3.12 · [uv](https://github.com/astral-sh/uv)
- FastAPI · Pydantic v2 · pydantic-settings
- PostgreSQL with [pgvector](https://github.com/pgvector/pgvector)
- ruff · mypy (strict) · pytest · pre-commit

## Quick start

```bash
uv sync --group dev
cp .env.example .env
docker compose up -d
uv run uvicorn app.main:app --app-dir src --reload --port 8000
curl -s http://localhost:8000/v1/health | jq
```

Postgres is on host port **5433** (container 5432) so it does not collide with a
local Postgres on 5432.

Expected: HTTP 200 with `postgres` and `pgvector` both `up`.

## Checks

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv run pytest -n auto
```

## Corpus

Documents live under `data/corpus/`. Licensing and provenance:
[`data/corpus/SOURCES.md`](data/corpus/SOURCES.md).

| Layer | Path | Role |
|-------|------|------|
| **Operator (primary)** | `data/corpus/operator/` | Synthetic Vardar Mobile docs (MK + EN) — plans, roaming, devices, billing, FAQ, etc. |
| Western Balkans | `data/corpus/wb6/` | Regional roaming agreement (supporting) |
| EU acquis | `data/corpus/eu/` | Small EUR-Lex set (EN + NL) for regulatory grounding |

The operator layer is generated from a single catalogue so prices and terms stay
consistent across hundreds of files:

```bash
python data/scripts/generate_corpus.py
```

Optional: re-download the EU HTML (already committed):

```bash
bash scripts_fetch_eu_corpus.sh
```

## Layout

```
src/app/                 FastAPI application (health, config, errors)
tests/                   unit tests (no live database required)
data/corpus/operator/    primary synthetic operator knowledge base
data/corpus/eu/          supporting EU regulation (small)
data/corpus/wb6/         supporting regional roaming text
data/scripts/            operator catalogue + corpus generator
docker-compose.yml       local Postgres + pgvector
docker/init-pgvector.sql enables the vector extension on first boot
```

## Roadmap (high level)

1. **Done** — project scaffold, health checks, local Postgres/pgvector, corpus
2. **Next** — ingestion (chunking, embeddings, vector store)
3. Hybrid retrieval + evaluation harness
4. Chat API with grounding and citations
5. Agent loop, tool tiers, approval gates
6. Streaming UI, observability, deploy notes

## License notes

Operator documents are **synthetic**: invented carrier, prices, and promotions;
not copied from a real operator. EU documents are reused under CC BY 4.0 as
described in `SOURCES.md`.
