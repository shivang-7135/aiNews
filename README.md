# DailyAI — AI News Aggregator 🤖📰

A mobile-friendly, agentic AI news application that fetches, filters, and summarizes breaking AI news from around the world — updated every hour.

## ✨ Features

- **🌍 Country-based news** — Select your region to get localized AI news
- **🌐 3-language support** — Read summaries in English, Hindi, or German
- **🤖 Agentic AI pipeline** — Uses HuggingFace LLM to filter, rank, and summarize news
- **🎯 Higher-quality ranking** — Source trust + recency + topic diversity for better top stories
- **⏰ Hourly updates** — Automatic background refresh every hour
- **📱 PWA / Mobile-ready** — Install on Android as an app via "Add to Home Screen"
- **🎨 Premium dark UI** — Glassmorphism, animations, responsive design
- **📡 24 rolling tiles** — Max 24 news stories, oldest auto-replaced
- **🔄 Smart fallback** — Works even without LLM (basic mode)

## 🚀 Quick Start

### 1. Clone & Setup
```bash
cd DailyAInews
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Dev Quality Setup (Recommended)
```bash
pip install -r requirements-dev.txt
pre-commit install
```

Run quality checks locally:
```bash
# Format + lint + types + security
black --check .
ruff check .
isort --check-only .
mypy .
bandit -q -r . -c bandit.yaml
```

Auto-fix style/lint issues:
```bash
ruff check . --fix
ruff format .
```

### 2. Configure API Token (Optional but recommended)
```bash
cp .env.example .env
# Edit .env and add your HuggingFace token
# Get one free at: https://huggingface.co/settings/tokens
```

> **Note:** The app works without a token (uses RSS fallback), but the LLM
> filtering/summarization needs a HuggingFace token for best results.

### 3. Run Locally
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Email Setup (Resend)
If emails are not being delivered to other subscribers, configure these environment variables:

```bash
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL="DailyAI <news@your-verified-domain.com>"
RESEND_REPLY_TO="support@your-verified-domain.com"  # optional
```

Important: `onboarding@resend.dev` is meant for testing and may not deliver to arbitrary recipients. For production delivery, verify your domain in Resend and use that sender in `RESEND_FROM_EMAIL`.

Open **http://localhost:8000** on your phone or browser.

### 4. Install on Android
1. Open the URL in Chrome on your phone
2. Tap the **⋮** menu → **"Add to Home Screen"**
3. The app will behave like a native app!

## ☁️ Deploy to Cloud (Free)

### Option A: Render.com (Recommended)
1. Push code to GitHub
2. Go to [render.com](https://render.com) → New **Web Service**
3. Connect repo, set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Environment Variable:** `HF_API_TOKEN=hf_your_token`
4. Deploy! Free tier keeps app running ✅

### Option B: Railway.app
1. Push to GitHub  
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
3. Add env var `HF_API_TOKEN`
4. Auto-deploys!

### Option C: Docker
```bash
docker build -t dailyai .
docker run -p 8000:8000 -e HF_API_TOKEN=hf_xxx dailyai
```

## 🏗️ Architecture

```
┌──────────────────────────────────────────────┐
│              DailyAI App                      │
│                                              │
│  ┌─────────┐    ┌──────────┐    ┌─────────┐ │
│  │ FastAPI  │◄──►│  Agent   │◄──►│  LLM    │ │
│  │ Server   │    │ Pipeline │    │ (HF API)│ │
│  └────┬─────┘    └────┬─────┘    └─────────┘ │
│       │               │                      │
│  ┌────▼─────┐    ┌────▼─────┐               │
│  │ Templates│    │ RSS Feed │               │
│  │ (Jinja2) │    │ (Google) │               │
│  └──────────┘    └──────────┘               │
│                                              │
│  ┌─────────────────────────────┐            │
│  │ APScheduler (hourly refresh)│            │
│  └─────────────────────────────┘            │
└──────────────────────────────────────────────┘
```

## 📁 Project Structure

```
DailyAInews/
├── app.py              # FastAPI server + scheduler
├── agent.py            # Agentic news pipeline (LLM + RSS tools)
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container deployment
├── .env.example        # Environment config template
├── templates/
│   └── index.html      # Jinja2 HTML template
└── static/
    ├── styles.css      # Premium dark mode CSS
    ├── app.js          # Frontend logic
    ├── manifest.json   # PWA manifest
    └── sw.js           # Service worker
```

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11 + FastAPI |
| LLM | HuggingFace Inference API (Qwen/Mixtral/Llama) |
| News Source | Google News RSS (no API key) |
| Frontend | Vanilla HTML/CSS/JS + PWA |
| Scheduler | APScheduler |
| Deployment | Docker / Render / Railway |

## 📝 License

MIT — use however you like!
