# telco-assistant

RAG and agentic assistant over EU telecom regulation (EUR-Lex), with account tools
against a mock CRM, tiered safety gates on state-changing actions, and a measured
evaluation harness.

## Stack

- Python 3.12 · [uv](https://github.com/astral-sh/uv)
- FastAPI · Pydantic v2 · pydantic-settings
- PostgreSQL with [pgvector](https://github.com/pgvector/pgvector)
- ruff · mypy (strict) · pytest · pre-commit

## Vector backend

Retrieval is behind a `VectorStore` Protocol. The default implementation is
**pgvector** (one Postgres service). An in-memory store is used in tests.
Additional backends can be added later and selected with `VECTOR_BACKEND`
without changing call sites.

## Quick start

```bash
uv sync --group dev
cp .env.example .env
docker compose up -d
uv run uvicorn app.main:app --app-dir src --reload --port 8000
curl -s http://localhost:8000/v1/health | jq
```

Postgres is published on host port **5433** (container 5432) to avoid colliding
with a local Postgres install.

`GET /v1/health` should return HTTP 200 with `postgres` and `pgvector` status `up`.

## Checks

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv run pytest -n auto
```

## Layout

```
src/app/                 application package
tests/                   unit tests (no live database required)
docker-compose.yml       local Postgres + pgvector
docker/init-pgvector.sql enables the vector extension on first boot
```

## Workflow

One branch per phase, Conventional Commits, one PR per phase (squash merge).
Do not commit directly to `main`.
