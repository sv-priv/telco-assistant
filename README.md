# telco-assistant

Production-shaped RAG assistant for telecom support: grounded answers over
operator documentation and regulation, with citations, controlled refusals, and
comparable orchestration backends.

The product surface is **Vardar Mobile** — a bilingual (Macedonian / English)
demo operator with a synthetic product catalogue, plus a thin layer of real EU
and Western Balkans roaming regulation. Vardar Mobile is not a real carrier and
is not affiliated with any telecom operator.

## Why this exists

Most “chat over docs” demos stop at calling an LLM. This project treats the
assistant as a service:

- **Ingest → embed → retrieve → answer**, with the same corpus behind every path
- **Grounding**: answers must follow retrieved context; missing evidence becomes
  an explicit no-hit / refusal, not a guess
- **Orchestration as a variable**: Custom RAG, LlamaIndex, and LangChain share
  one retriever and one evaluation set so differences are measurable
- **Quality is measured**: a golden JSONL suite scores retrieval and answers
  (citations, must-contain, refusal behaviour) — not vibes

## Architecture

```text
Corpus (MD) ──► ingest / chunk / embed ──► PostgreSQL + pgvector
                                              │
Question ──► rewrite (follow-ups) ──► Retriever ──► runners
                                        │            ├─ custom
                                        │            ├─ llamaindex
                                        │            └─ langchain (tools)
                                        ▼
                              FastAPI (/v1/ask, /chat, /search, /eval)
                                        │
                              Next.js UI (BFF proxies + API key)
```

| Layer | Responsibility |
|-------|----------------|
| `src/app/ingest` | Load markdown, chunk, embed, upsert |
| `src/app/retrieve` | Dense retrieval over pgvector |
| `src/app/runners` | Custom / LlamaIndex / LangChain over the same retriever |
| `src/app/eval` | Golden-set runner + metrics + scoreboard artifact |
| `src/app/api` | Versioned REST (`/v1/...`), auth, rate limits |
| `web/` | Chat UI, runner picker, eval scoreboard |

## Stack

- **API:** Python 3.12, FastAPI, Pydantic v2, asyncpg
- **Store:** PostgreSQL + [pgvector](https://github.com/pgvector/pgvector)
- **LLM:** OpenAI embeddings + chat (configurable models)
- **Orchestration:** first-party RAG, LlamaIndex QueryEngine, LangChain tools
- **UI:** Next.js (server routes hold the API key; browser never sees it)
- **Tooling:** uv, ruff, mypy (strict), pytest, pre-commit, GitHub Actions

## Quick start

```bash
uv sync --group dev
cp .env.example .env          # set OPENAI_API_KEY
docker compose up -d          # Postgres + pgvector on :5433

uv run uvicorn app.main:app --app-dir src --reload --port 8000
uv run python -m app.ingest --embed --source operator --lang mk

cd web && cp -n .env.example .env.local && npm install && npm run dev
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| UI | http://localhost:3000 |
| Health | `GET /v1/health` |

Ask via API (when `API_KEYS` is set):

```bash
curl -s http://localhost:8000/v1/ask \
  -H 'content-type: application/json' \
  -H 'X-API-Key: <key>' \
  -d '{"question":"роаминг во Турција","language":"mk","mode":"custom"}'
```

## Evaluation

Offline golden set: [`data/eval/golden.jsonl`](data/eval/golden.jsonl)
(~80 cases across plans, roaming, billing, refusals, follow-ups, and more —
see [`CATEGORIES.md`](data/eval/CATEGORIES.md)).

```bash
uv run python -m app.eval --validate          # schema only
uv run python -m app.eval --skip-answers      # retrieval metrics
uv run python -m app.eval --mode all          # full compare → data/eval/latest.json
```

Scoreboard: UI at `/eval`, or `GET /v1/eval/latest`. Pass criteria are
deterministic (expected `doc_id`s, `must_contain`, refusal flags).

## Corpus

| Layer | Path | Notes |
|-------|------|--------|
| Operator | `data/corpus/operator/` | Synthetic MK + EN product docs |
| EU | `data/corpus/eu/` | EUR-Lex (CC BY 4.0) |
| WB6 | `data/corpus/wb6/` | Regional roaming texts |

Licensing and provenance: [`data/corpus/SOURCES.md`](data/corpus/SOURCES.md).

## Auth and configuration

Protected routes require `X-API-Key` when `API_KEYS` is configured.
Non-local environments refuse to start without keys; OpenAPI docs are disabled
outside local/dev. The Next app proxies `/api/*` to FastAPI with a server-side
key (`TELCO_API_KEY` — never `NEXT_PUBLIC_`).

See [`.env.example`](.env.example) and [`web/.env.example`](web/.env.example)
for `CORS_ORIGINS`, rate limits, and optional AWS Secrets Manager.

## Deploy (Render)

Blueprint: [`render.yaml`](render.yaml) — Postgres (pgvector), API (Docker),
Next.js UI.

1. Push this repo to GitHub.
2. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint** →
   select the repo.
3. When prompted, set:
   - `OPENAI_API_KEY`
   - `API_KEYS` — e.g. `demo:<long-random-secret>`
   - `TELCO_API_KEY` — the **same secret** after the colon (not the `demo:` prefix)
4. Wait for `telco-api` and `telco-web` to go live.
5. **Ingest embeddings** (one-off Shell on `telco-api`, after the first deploy):

```bash
uv run python -m app.ingest --embed --source operator
# optional regulation layer:
# uv run python -m app.ingest --embed --source eu --source wb6 --lang en
```

Open the `telco-web` URL. Chat will fail until ingest finishes.

## Development

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv run pytest -n auto
```

## License

- **Code:** [MIT](LICENSE)
- **Operator corpus:** synthetic demo content — see `SOURCES.md`
- **EU text:** CC BY 4.0 — attribution in `SOURCES.md`
