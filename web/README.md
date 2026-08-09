# web

Next.js UI for telco-assistant.

```bash
cp .env.example .env.local
npm install
npm run dev
```

Set server-only env (never `NEXT_PUBLIC_` for secrets):

- `TELCO_API_URL` — FastAPI base URL (default `http://localhost:8000`)
- `TELCO_API_KEY` — must match a value in backend `API_KEYS`

The browser calls same-origin `/api/*`; the Next server proxies to FastAPI with
`X-API-Key`.
