# DailyAI - AI News Aggregator

DailyAI is a mobile-first AI news app that turns raw headlines into quick decisions.
It supports language and region personalization, role-based reading lens, local caching,
and a PWA install flow.

## What Is Updated In This Workflow

- Discover-first UX with vertical card feed
- Top-level settings for language, region, lens, sort, appearance, and refresh
- Saved view with save and unsave controls
- Build-aware cache reset during deployment updates
- Service worker versioning and stale cache cleanup

## Core User Flow

1. Open app and land in Discover feed.
2. Choose language, region, and lens from Settings.
3. Scroll one card at a time and open sheet for details.
4. Save useful items and review them in Saved tab.
5. Refresh feed manually or let backend hourly refresh keep data warm.

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

# Optional LLM fallback
GROQ_API_KEY=gsk_xxx

# Optional email digest delivery
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL="DailyAI <news@your-verified-domain.com>"
RESEND_REPLY_TO="support@your-verified-domain.com"

# Optional model provider keys if used by your services
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

## Cache and Update Strategy

The app now includes a build-safe cache rollout to avoid old frontend bundles
causing stuck loading states after deployment.

- HTML sets versioned URLs for styles, script, and manifest via app version.
- App compares deployed build marker and performs first-load cache reset.
- Client clears local feed caches, Cache Storage entries, and old service workers.
- Service worker uses versioned cache names and removes old caches on activate.

If a user still sees stale UI after deploy, hard refresh once.

## API Endpoints

- GET /api/articles
- POST /api/articles/brief
- POST /api/refresh/{country_code}
- GET /api/version
- POST /api/subscribe
- GET /api/subscribers/count

## Project Structure

```text
DailyAInews/
|- app.py
|- services/
|  |- config.py
|  |- news_core.py
|  |- security.py
|  |- store.py
|- templates/
|  |- index.html
|- static/
|  |- app.js
|  |- styles.css
|  |- sw.js
|  |- manifest.json
|- digest.py
|- requirements.txt
|- Dockerfile
```

## Tech Stack

- Backend: FastAPI, APScheduler
- Frontend: Vanilla JS, HTML, CSS, PWA
- News source: RSS aggregation and AI ranking pipeline
- Deployment: Render, Railway, Docker

## Troubleshooting

### App stuck on Loading latest stories

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
