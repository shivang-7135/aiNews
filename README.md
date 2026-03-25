# DailyAI - AI News Aggregator

DailyAI is a mobile-first AI news app that curates and summarizes AI headlines into
concise, actionable bullet points. It supports language & region personalization,
anonymous profile sync, local caching, and a PWA install flow.

## Key Features

- **Scroll-first feed** — 15-30 curated AI headlines per session
- **3-5 bullet point summaries** — tap any card to get key takeaways
- **Anonymous recommendations** — Sync Code (e.g. `Swift-Horizon-51`) personalizes your feed without login
- **Topic onboarding** — pick your interests, change them anytime from sidebar
- **Multi-language** — English, Hindi, German
- **Multi-region** — Global + 20+ country feeds
- **Offline-friendly** — articles cached to JSON on disk + localStorage in browser
- **PWA** — installable, service worker caching, version-safe cache resets

## Core User Flow

1. Open app → animated 3-step guide (Scroll / Tap / Save)
2. Pick topics → get a Sync Code for anonymous cross-device sync
3. Scroll feed → articles ranked by your preferences + importance
4. Tap a card → see 3-5 bullet points + link to original article
5. Save useful items → review in Saved tab

## Local Setup

### 1. Install Dependencies

```bash
cd DailyAInews
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Set values you need:

```dotenv
HF_API_TOKEN=hf_xxx
PORT=8000
BYTEZ_API_KEY=...

# Optional
GROQ_API_KEY=gsk_xxx
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL="DailyAI <news@your-verified-domain.com>"
RESEND_REPLY_TO="support@your-verified-domain.com"
GOOGLE_AI_KEY=...
```

Important:

- Do not commit real keys to git.
- Rotate any key that was ever pushed publicly.

### 3. Run App

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

## Deployment Workflow

### Recommended: Render

1. Push latest code to your repo.
2. Create or update Render Web Service.
3. Set build command:

```bash
pip install -r requirements.txt
```

4. Set start command:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

5. Add environment variables in Render dashboard.

### Optional: Railway

1. Connect repo.
2. Add required environment variables.
3. Deploy.

### Optional: Docker

```bash
docker build -t dailyai .
docker run -p 8000:8000 --env-file .env dailyai
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/articles` | Fetch curated feed (supports `sync_code` for personalization) |
| POST | `/api/articles/brief` | Generate 3-5 bullet point summary for an article |
| POST | `/api/refresh/{country_code}` | Force refresh news for a country |
| GET | `/api/version` | Current app version (for cache invalidation) |
| POST | `/api/subscribe` | Subscribe to email digest |
| GET | `/api/subscribers/count` | Subscriber count |
| POST | `/api/profile/new` | Create anonymous profile with topic preferences |
| GET | `/api/profile/{sync_code}` | Get profile by sync code |
| PUT | `/api/profile/{sync_code}` | Update profile preferences |
| POST | `/api/profile/{sync_code}/signal` | Record implicit signal (tap/save/skip) |
| GET | `/api/countries` | Available country codes |
| GET | `/api/languages` | Available languages |

## Project Structure

```text
DailyAInews/
├── app.py                    # FastAPI routes
├── agent.py                  # LLM-powered news curation + brief generation
├── services/
│   ├── config.py             # Topics, countries, MAX_TILES
│   ├── news_core.py          # Feed fetching, JSON persistence, personalization
│   ├── profiles.py           # Anonymous profiles, sync codes, signal tracking
│   ├── security.py           # CSRF, CSP, rate limiting
│   └── store.py              # In-memory news store
├── templates/
│   └── index.html            # Main SPA template
├── static/
│   ├── app.js                # Frontend logic
│   ├── styles.css            # Design system
│   ├── sw.js                 # Service worker
│   └── manifest.json         # PWA manifest
├── articles_cache.json       # Persisted article cache (auto-generated)
├── profiles.json             # User profiles (auto-generated)
├── digest.py                 # Email digest sender
├── requirements.txt
└── Dockerfile
```

## Tech Stack

- Backend: FastAPI, APScheduler, Pydantic
- Frontend: Vanilla JS, HTML, CSS, PWA
- LLM: Bytez (Mistral-7B), with Ollama/Gemini/Groq/HuggingFace fallbacks
- News source: RSS aggregation + AI ranking pipeline
- Deployment: Render, Railway, Docker

## Troubleshooting

### App stuck on "Loading latest stories"

1. Confirm deployment completed and new version is live.
2. Open /api/version and verify version changed.
3. Reload once to allow cache reset and service worker refresh.
4. Verify environment keys are present in deployment platform.
5. Check backend logs for fetch or model provider failures.

### Subscriber emails not delivered

1. Verify Resend domain is validated.
2. Ensure RESEND_FROM_EMAIL uses verified domain.
3. Confirm API key is active and not restricted.

## License

MIT
