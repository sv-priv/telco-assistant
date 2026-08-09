# telco-assistant

Grounded RAG chat over a **demo** Macedonian mobile operator (**Vardar Mobile**)
plus a thin EU / WB6 regulation layer.

> Vardar Mobile is not a real carrier. Plans, prices, and policies are synthetic
> product data for this project and are not affiliated with any telecom operator.

Before any public expose, set `API_KEYS` + Next `TELCO_API_KEY` (see Auth below)
and set `ENVIRONMENT` to something other than `local`/`dev`.

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

## Eval / scoreboard

Offline golden-set benchmark across orchestration runners (same corpus):

```bash
# validate cases only
uv run python -m app.eval --validate

# retrieval metrics only (embeddings + pgvector, no chat LLM answers)
uv run python -m app.eval --skip-answers

# full compare → writes data/eval/latest.json
uv run python -m app.eval --mode all
```

Then open the UI scoreboard at [http://localhost:3000/eval](http://localhost:3000/eval)
or `GET /v1/eval/latest`. Pass criteria live in `data/eval/golden.jsonl`
(expected `doc_id`s, refusal, must_contain).
Cases are grouped by `category` (see [`data/eval/CATEGORIES.md`](data/eval/CATEGORIES.md));
the report includes `by_category` pass rates.

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

## Languages

API `language` is `mk` | `en` (optional). Chat UI toggle sets it and updates
`<html lang>`. No-hit / grounding prompts follow that language. EU and WB6
docs are **English-first** — see [`data/corpus/SOURCES.md`](data/corpus/SOURCES.md).

## Auth (API key + proxy)

Protected routes (`/v1/ask`, `/v1/chat`, `/v1/search`, `/v1/eval/*`) require
`X-API-Key` when `API_KEYS` is set. `/v1/health` stays public.
Non-local `ENVIRONMENT` values **require** `API_KEYS` (app will refuse to start
without them). OpenAPI `/docs` is disabled outside local/dev.

```bash
# .env
ENVIRONMENT=local
API_KEYS=demo:replace-with-a-long-random-secret
RATE_LIMIT_PER_MINUTE=60
CORS_ORIGINS=http://localhost:3000,https://your-frontend.example
# TRUST_PROXY=true   # only behind a known reverse proxy

# web/.env.local (server-only — not NEXT_PUBLIC_)
TELCO_API_URL=http://localhost:8000
TELCO_API_KEY=replace-with-a-long-random-secret
```

The browser calls same-origin Next routes (`/api/ask`, `/api/eval/...`); the
Next server adds the key when proxying to FastAPI. Empty `API_KEYS` is allowed
only for `local` / `dev` / `test` / `ci`.

```bash
curl -s http://localhost:8000/v1/ask \
  -H 'content-type: application/json' \
  -H 'X-API-Key: replace-with-a-long-random-secret' \
  -d '{"question":"роаминг во Турција","language":"mk","mode":"custom"}' | jq
```

## Search / chat

```bash
uv run uvicorn app.main:app --app-dir src --reload --port 8000

curl -s http://localhost:8000/v1/search \
  -H 'content-type: application/json' \
  -H 'X-API-Key: replace-with-a-long-random-secret' \
  -d '{"query":"роаминг во Турција","limit":5,"language":"mk"}' | jq

curl -s http://localhost:8000/v1/chat \
  -H 'content-type: application/json' \
  -H 'X-API-Key: replace-with-a-long-random-secret' \
  -d '{"question":"роаминг во Турција","language":"mk"}' | jq

uv run python -m app.retrieve "роаминг во Турција" --lang mk
```

## Deploy checklist

1. Set `ENVIRONMENT=production` (or `staging`) and a strong `API_KEYS` value.
2. Match Next `TELCO_API_KEY` to that secret; keep it server-only.
3. Set `CORS_ORIGINS` to your real frontend origin(s).
4. Set `TRUST_PROXY=true` only if a reverse proxy sets `X-Forwarded-For`.
5. Do not publish Postgres (`5433`) to the public internet.
6. Rotate away from example secrets (`dev-local-telco-key`, default DB password).
7. Put a rate limit / WAF in front of the Next app — `/api/ask` spends LLM tokens.
8. Re-ingest after corpus edits: `uv run python -m app.ingest --embed …`

## License

- **Code:** [MIT](LICENSE)
- **Operator corpus:** synthetic demo content (see `data/corpus/SOURCES.md`)
- **EU text:** CC BY 4.0 — attribution in `SOURCES.md`
