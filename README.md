# telco-assistant

RAG assistant over a synthetic Macedonian operator (**Vardar Mobile**) plus a
small EU / WB6 regulation layer.

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
```

Postgres listens on host port **5433**.

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
src/app/           FastAPI app + ingest
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

Ingest, vector search, and grounded chat API work. Next: UI / eval / hybrid.

## License

Operator docs are synthetic. EU text: CC BY 4.0 — see `SOURCES.md`.
