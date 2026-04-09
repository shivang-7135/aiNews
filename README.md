# DailyAI

DailyAI is a FastAPI + NiceGUI application for AI/tech news intelligence.
It ingests RSS sources, processes stories through a LangGraph pipeline, serves a mobile-first feed UI, and exposes API endpoints for feed access, personalization, and operations.

## Current Status

This repository is now on the v2 architecture and includes:

- Source-first app structure under `src/dailyai`.
- FastAPI + NiceGUI unified app startup.
- LangGraph pipeline for collection, dedupe, trust/sentiment/topic tagging, and formatting.
- Streaming article briefs with LLM fallback chaining.
- SQLite default persistence, with optional Supabase backend.
- Analytics-driven personalization and profile sync codes.
- Operational admin endpoints and hidden cache/RSS admin UI.
- Deployment-ready setup for buildpack and container platforms.

## Tech Stack

- Backend: FastAPI
- UI: NiceGUI (Quasar/Vue runtime)
- Pipeline: LangGraph + LangChain
- Storage: SQLite (`aiosqlite`) by default, optional Supabase
- Scheduler: APScheduler
- Email: Resend (optional)
- Runtime: Python 3.11+

## Key Features

- Multi-country, multi-language feed slices (with normalization and fallback logic)
- Topic-aware feed tabs and category counts
- Personalized ranking using captured behavior events
- Article brief streaming endpoint with cached summaries
- Background prefetch and scheduled full refresh
- Daily email digest support
- Developer API (`/api/v1/*`) plus internal UI APIs (`/api/*`)

## Project Layout

```text
.
├── app.py                      # ASGI compatibility entrypoint (uvicorn app:app)
├── src/dailyai/
│   ├── __main__.py             # Main runtime entrypoint (uv run dailyai)
│   ├── api/                    # REST routes + middleware
│   ├── graph/                  # LangGraph state + nodes
│   ├── llm/                    # LLM provider + prompts
│   ├── services/               # News, analytics, profiles, scheduler, digest
│   ├── storage/                # sqlite/supabase backends + migration utility
│   └── ui/                     # NiceGUI pages/components/theme
├── tests/
├── requirements.txt            # Deployment dependency source of truth
├── Procfile                    # Buildpack start command
├── Dockerfile
└── render.yaml
```

## Local Development

### 1) Prepare environment

```bash
cp .env.example .env
```

Set at least one LLM provider key in `.env` (for example `OPENAI_API_KEY` or `GOOGLE_AI_KEY`).

### 2) Install dependencies

Option A (recommended for local dev):

```bash
uv sync
```

Option B (pip workflow / deployment parity):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Run the app

Primary command:

```bash
uv run dailyai
```

Compatibility command:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open: `http://localhost:8000`

## Useful Environment Variables

- Server: `HOST`, `PORT`, `DEBUG`, `APP_URL`
- Storage: `STORAGE_BACKEND`, `DB_PATH`, `SUPABASE_URL`, `SUPABASE_KEY`
- LLM: `OPENAI_API_KEY`, `GOOGLE_AI_KEY`, `GROQ_API_KEY`, `NVIDIA_API_KEY`, `HF_API_TOKEN`, `ARLIAI_API_KEY`, `OLLAMA_BASE_URL`
- Scheduling/cache: `DAILY_REFRESH_HOUR_UTC`, `DAILY_REFRESH_MINUTE_UTC`, `STARTUP_PREFETCH_*`, `CACHE_*`
- Email: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_REPLY_TO`
- Admin: `ADMIN_PASSWORD`

## API Surface

Internal/UI APIs:

- `GET /api/articles`
- `GET /api/articles/categories`
- `POST /api/articles/brief` (streaming response)
- `POST /api/analytics/events`
- `GET /api/profile/{sync_code}` and related profile routes

Developer APIs:

- `GET /api/v1/feed`
- `GET /api/v1/categories`
- `GET /api/v1/trending`

Ops/Admin APIs:

- `GET /api/admin/cache-health`
- `GET/POST/DELETE /api/admin/rss-feeds`
- `GET /api/admin/analytics`

Legal/info pages:

- `/impressum`, `/datenschutz`, `/terms`, `/api-docs`

## Testing and Quality

Run all tests:

```bash
uv run pytest -q
```

Run function health checks:

```bash
uv run pytest -q tests/test_function_health.py
```

Lint/type checks:

```bash
uv run ruff check .
uv run mypy .
```

## Storage Backends

Default backend is SQLite.

To use Supabase:

1. Set `STORAGE_BACKEND=supabase`
2. Set `SUPABASE_URL` and `SUPABASE_KEY`
3. (Optional) migrate existing SQLite data:

```bash
uv run dailyai-migrate-supabase --check-only
uv run dailyai-migrate-supabase
```

## Deployment

### Buildpack-style platforms

This repo is configured to use `requirements.txt` as dependency source for deployment.

- `Procfile` exists with:
  - `web: uvicorn app:app --host 0.0.0.0 --port $PORT`
- `uv.lock` is intentionally excluded for buildpack compatibility.

### Render

`render.yaml` is included:

- Build: `pip install -r requirements.txt`
- Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`

### Docker

```bash
docker build -t dailyai .
docker run -p 8000:8000 --env-file .env dailyai
```

## Contributing

See `CONTRIBUTING.md`.

