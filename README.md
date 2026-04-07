# DailyAI — Agentic News Intelligence

DailyAI is a modern, high-performance web application that aggregates, categorizes, and curates AI and technology news from 50+ global sources. It leverages a novel "agentic pipeline" architecture to autonomously process feeds, filter noise, and generate tailored, real-time intelligence briefs.

## Architecture

The project has transitioned from a basic procedural setup into a scalable startup architecture, utilizing the following core stack:

- **Frontend / UI**: [**NiceGUI**](https://nicegui.io/)
  - An entirely Python-based UI framework built on top of Vue/Quasar.
  - Enables zero-compilation mobile-first responsive design, delivering a premium "app-like" experience directly through standard Python.
  - UI styled globally via pure CSS injections inside `src/dailyai/ui/components/theme.py`, utilizing custom scrollbar overrides, glassmorphism, and ambient gradients.

- **Backend Framework**: **FastAPI**
  - Serves as the high-throughput asynchronous foundation.
  - Powers Server-Sent Events (SSE) streaming (`StreamingResponse`) which delivers real-time AI briefs to the frontend seamlessly.

- **AI Pipeline**: [**LangGraph**](https://langchain-ai.github.io/langgraph/)
  - Replaces monolithic LLM calls with a resilient graphed state machine (`src/dailyai/graph/pipeline.py`).
  - Manages fetching, de-duplication, quality grading, and content categorization.
  - Supports multiple LLM providers (Gemini, Groq, OpenAI) synchronously via intelligent fallbacks.

- **Storage Layer**: **SQLite / `aiosqlite`**
  - Eliminates slow JSON flat files by using an asynchronous, zero-config relational database (`dailyai.db`) for storing structured feeds, profiles, analytics, and persistent AI Brief caches.

- **Dependency & Task Management**: [**uv**](https://github.com/astral-sh/uv)
  - Blazing-fast dependency injection and environment resolution replacing standard `pip` workflows.

## Core Features
1. **Real-Time Streaming Briefs**: AI summaries do not block. They type out line-by-line dynamically on the frontend.
2. **Parallel Startup Optimization**: Feeds for `GLOBAL` and regional metrics are fetched asynchronously with `asyncio.gather` for significantly reduced load times.
3. **Database Caching Strategy**: LLM outputs and RSS feeds are rotated efficiently to ensure maximum API rate-limit preservation.
4. **Mobile First Typography**: In-shorts style scrolling cards displaying high-quality, lightweight compressed image assets from Unsplash.

## Getting Started

1. Set your target API keys in a `.env` file (e.g. `OPENAI_API_KEY`, `GOOGLE_AI_KEY`).
2. Run the application via `uv`:
   ```bash
   uv run uvicorn app:app --reload
   ```
3. Open mobile or desktop browser to `http://localhost:8000`.
