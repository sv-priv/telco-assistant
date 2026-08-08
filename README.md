# telco-assistant

Grounded RAG chat over a **fictional / synthetic** Macedonian mobile operator
(**Vardar Mobile**) plus a thin EU / WB6 regulation layer.

> **Demo only.** Vardar Mobile is not a real carrier. Plans, prices, and
> policies are synthetic training data for this project. Not affiliated with
> any real telecom operator.

**This repo is for local / portfolio use.** There is no hosted public demo.
The chat API is unauthenticated — do not expose it to the internet without
auth and rate limits.

## Stack

- Python 3.12 · [uv](https://github.com/astral-sh/uv)
- FastAPI · Pydantic v2
- PostgreSQL + [pgvector](https://github.com/pgvector/pgvector)
- ruff · mypy · pytest · pre-commit

## Quick start

```bash
uv sync --group dev
cp .env.example .env   # set OPENAI_API_KEY
docker compose up -d
uv run uvicorn app.main:app --app-dir src --reload --port 8000
curl -s http://localhost:8000/v1/health | jq

# UI (Next.js) — separate terminal
cd web && cp -n .env.example .env.local && npm run dev
# open http://localhost:3000
```

Postgres listens on host port **5433**. API on **8000**, UI on **3000**.

```bash
# ingest (embeddings → pgvector)
uv run python -m app.ingest --embed --source operator --lang mk
```

## Checks

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv run pytest -n auto
```

## Corpus

Under `data/corpus/`. See [`SOURCES.md`](data/corpus/SOURCES.md).

| Layer | Path |
|-------|------|
| Operator (primary, MK+EN) | `data/corpus/operator/` |
| EU | `data/corpus/eu/` |
| WB6 | `data/corpus/wb6/` |

```bash
python data/scripts/generate_corpus.py   # regenerate operator docs
bash scripts_fetch_eu_corpus.sh          # re-fetch EUR-Lex HTML
```

## Layout

```
src/app/           FastAPI API + ingest / retrieve / chat
web/               Next.js UI
tests/
data/corpus/       markdown knowledge base
data/scripts/      operator corpus generator
docker-compose.yml local Postgres + pgvector
```

## Search / chat

```bash
uv run uvicorn app.main:app --app-dir src --reload --port 8000

curl -s http://localhost:8000/v1/search -H 'content-type: application/json' \
  -d '{"query":"роаминг во Турција","limit":5,"language":"mk"}' | jq

curl -s http://localhost:8000/v1/chat -H 'content-type: application/json' \
  -d '{"question":"роаминг во Турција","language":"mk"}' | jq

uv run python -m app.retrieve "роаминг во Турција" --lang mk
```

## Status

| Area | State |
|------|--------|
| Ingest → pgvector | Working |
| Dense retrieval + grounded chat API | Working |
| Next.js UI (`web/`) | Working (local) |
| Follow-up rewrite / plan query helpers | Working |
| Hybrid BM25 + RRF | Not yet |
| Golden eval set | Not yet |
| API auth / rate limits | Not yet (local demo only) |

## License

- **Code:** [MIT](LICENSE)
- **Operator corpus:** synthetic demo content (see `data/corpus/SOURCES.md`)
- **EU text:** CC BY 4.0 — attribution in `SOURCES.md`
