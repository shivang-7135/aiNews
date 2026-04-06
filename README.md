<div align="center">
  <img src="/static/icons/icon-192x192.png" alt="DailyAI Logo" width="100"/>
  <h1>DailyAI v2 (LangGraph Edition)</h1>
  <p><strong>A startup-grade AI News Intelligence Platform powered by LangGraph, FastAPI, and NiceGUI.</strong></p>
  <p>
    <a href="#features">Features</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#quickstart">Quickstart</a> •
    <a href="#developer-api">Developer API</a>
  </p>
</div>

---

DailyAI is a professional intelligence platform that aggregates, curates, and ranks the most important AI news daily. Version 2 is completely rebuilt around a **LangGraph agentic pipeline** and a **Python-only NiceGUI frontend**, managed entirely by `uv`.

## 🚀 Features

- **Agentic Pipeline (LangGraph)**: Modular, observable pipeline that collects, deduplicates, curates (via LLM), scores trust, tags sentiment, and threads stories.
- **Cascading LLM Fallbacks**: Uses LangChain `with_fallbacks()` to seamlessly switch between Gemini, Groq, NVIDIA, HuggingFace, and Ollama to ensure near 100% uptime.
- **Python-Only UI (NiceGUI)**: Premium glassmorphism design, fully responsive (mobile/desktop), and PWA-ready without a single line of JavaScript or HTML.
- **Intelligence Signals**: Includes Source Trust Scoring (Verified/Known/Unrated), Sentiment Analysis (Bullish/Bearish/Neutral), and Story Threading.
- **Privacy-First Personalization**: Generates anonymous "Sync Codes" (e.g. `Swift-Falcon-42`) to track topics and implicit signals without requiring intrusive logins.
- **Zero-Config DB**: Powered by async SQLite for fast local persistence, ready for Supabase cloud sync.
- **Developer API**: Open REST API (`/api/v1/feed`) for integration into external apps.

## 🏗️ Architecture

```mermaid
graph LR
    START((Start)) --> COLLECT[Collect News (RSS)]
    COLLECT --> DEDUPE[Deduplicate]
    DEDUPE --> CURATE[LLM Curate & Summarize]
    CURATE --> TRUST[Source Trust Scoring]
    TRUST --> SENTIMENT[Sentiment Analysis]
    SENTIMENT --> THREAD[Story Threading]
    THREAD --> PERSONALIZE{User Profile?}
    PERSONALIZE -->|Yes| RANK_PERSONAL[Personalize Rank]
    PERSONALIZE -->|No| RANK_DEFAULT[Quality Rank]
    RANK_PERSONAL --> FORMAT[Format for UI]
    RANK_DEFAULT --> FORMAT
    FORMAT --> END((End))
```

The system is split into distinct layers:
1. **Frontend (NiceGUI)**: `src/dailyai/ui/`
2. **REST API (FastAPI)**: `src/dailyai/api/`
3. **Core Pipeline (LangGraph)**: `src/dailyai/graph/`
4. **LLM Abstraction (LangChain)**: `src/dailyai/llm/`
5. **Storage (SQLite/Supabase)**: `src/dailyai/storage/`

## 🛠️ Quickstart

DailyAI v2 uses [uv](https://github.com/astral-sh/uv) for lightning-fast Python package management.

### 1. Prerequisites
- Python 3.11+
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### 2. Setup
Clone the repository, configure your API keys, and run.

```bash
git clone https://github.com/shivang/DailyAInews.git
cd DailyAInews

# Copy the example environment variables
cp .env.example .env

# Edit .env and add at least one LLM key (e.g. GOOGLE_AI_KEY or GROQ_API_KEY)
nano .env

# Run the app (uv will auto-install dependencies and start the Uvicorn server)
uv run dailyai
```

The application will start on `http://localhost:8000`.

## 🌐 Developer API

The platform exposes a public Developer API for fetching the curated feed.

**Endpoint**:
`GET /api/v1/feed?topic=all&country=GLOBAL&language=en&limit=15`

**Response format**:
```json
{
  "total": 15,
  "articles": [
    {
      "id": "GLOBAL-en-0",
      "headline": "OpenAI announces GPT-5 development schedule",
      "summary": "The next generation foundation model targets Q4 release...",
      "why_it_matters": "Will reset the benchmark for all major AI applications.",
      "importance": 9,
      "topic": "AI Models",
      "source_name": "Reuters",
      "source_trust": "high",
      "sentiment": "bullish",
      "story_thread": "GPT-5 Launch",
      "thread_count": 3
    }
  ]
}
```

## 📜 Roadmap
- **v2.1**: Smart Alerts & Topic Deep-Dives
- **v2.2**: Pro Tier (Stripe) & Slack/Discord Integration
- **v3.0**: Custom Source Plugins & Advanced Recommendations

## 📄 License
MIT License
