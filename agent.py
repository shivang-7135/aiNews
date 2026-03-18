"""
Agentic News Pipeline
---------------------
This module implements a simple agentic loop:
  1. TOOL: fetch_ai_news  — pulls AI-related headlines from Google News RSS
  2. TOOL: fetch_tech_news — pulls broader tech news that may include AI
  3. LLM:  filter & summarize — the HuggingFace model acts as the "brain"
         that decides which stories matter and writes concise summaries.

The agent uses a ReAct-style loop (Reason → Act → Observe) powered by
HuggingFace Inference API (free tier, using Qwen/Qwen2.5-72B-Instruct or
mistralai/Mixtral-8x7B-Instruct-v0.1).
"""

import json
import re
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
import feedparser

logger = logging.getLogger("dailyai.agent")

# ---------------------------------------------------------------------------
# RSS sources  (free, no API key needed)
# ---------------------------------------------------------------------------
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl={hl}&gl={gl}&ceid={gl}:{hl}"

FEED_QUERIES = {
    "ai_core": "artificial+intelligence+OR+AI+OR+machine+learning+OR+deep+learning+OR+LLM+OR+generative+AI",
    "ai_industry": "OpenAI+OR+Google+AI+OR+Meta+AI+OR+Anthropic+OR+Mistral+OR+DeepMind+OR+Hugging+Face",
    "ai_breakthroughs": "AI+breakthrough+OR+AI+launch+OR+AI+regulation+OR+AI+startup",
}

LANG_MAP: dict[str, tuple[str, str]] = {
    "US": ("en", "US"), "GB": ("en", "GB"), "IN": ("en", "IN"),
    "DE": ("de", "DE"), "FR": ("fr", "FR"), "CA": ("en", "CA"),
    "AU": ("en", "AU"), "JP": ("ja", "JP"), "KR": ("ko", "KR"),
    "CN": ("zh-Hans", "CN"), "BR": ("pt-BR", "BR"), "SG": ("en", "SG"),
    "AE": ("en", "AE"), "IL": ("en", "IL"), "GLOBAL": ("en", "US"),
}

# ---------------------------------------------------------------------------
# Tools available to the agent
# ---------------------------------------------------------------------------

async def fetch_rss_feed(query: str, gl: str = "US", hl: str = "en", max_items: int = 15) -> list[dict]:
    """Fetch items from Google News RSS."""
    url = GOOGLE_NEWS_RSS.format(query=query, hl=hl, gl=gl, ceid=f"{gl}:{hl}")
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 DailyAI/1.0"})
        resp.raise_for_status()

    feed = feedparser.parse(resp.text)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=26)  # slight overlap
    items = []
    for entry in feed.entries[:max_items]:
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            from time import mktime
            published = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
        if published and published < cutoff:
            continue
        items.append({
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "source": entry.get("source", {}).get("title", "") if hasattr(entry, "source") else "",
            "published": published.isoformat() if published else "",
        })
    return items


async def fetch_ai_news(country_code: str) -> list[dict]:
    """Fetch AI-specific news from multiple query angles."""
    hl, gl = LANG_MAP.get(country_code, ("en", "US"))
    all_items = []
    tasks = [fetch_rss_feed(q, gl=gl, hl=hl) for q in FEED_QUERIES.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, list):
            all_items.extend(r)

    # Deduplicate by title
    seen = set()
    unique = []
    for item in all_items:
        key = item["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


# ---------------------------------------------------------------------------
# HuggingFace LLM call  (new router.huggingface.co endpoint)
# Uses OpenAI-compatible chat completions format
# Docs: https://huggingface.co/docs/inference-providers
# ---------------------------------------------------------------------------
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"

# Models available on HF free serverless tier (tried in order)
HF_MODELS = [
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
]

async def call_llm(messages: list[dict], hf_token: str, max_tokens: int = 2048) -> str:
    """Call HuggingFace Inference Providers API with fallback models."""
    headers = {"Content-Type": "application/json"}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    for model in HF_MODELS:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(HF_API_URL, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    # OpenAI-compatible response format
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
                    return ""
                else:
                    logger.warning(f"Model {model} returned {resp.status_code}: {resp.text[:300]}")
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            continue

    logger.error("All HF models failed")
    return ""


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------
class NewsAgent:
    """
    A simple agentic pipeline that:
    1. Uses tools to fetch raw news
    2. Sends them to an LLM to filter, rank, and summarize
    3. Returns structured tiles
    """

    def __init__(self, hf_token: str = ""):
        self.hf_token = hf_token

    async def run(self, country_code: str, country_name: str) -> list[dict]:
        """Execute the full agentic pipeline."""

        # ---- Step 1: Tool call — fetch raw news ----
        logger.info(f"[Agent] Step 1: Fetching raw news for {country_name} ({country_code})")
        raw_articles = await fetch_ai_news(country_code)
        logger.info(f"[Agent] Fetched {len(raw_articles)} raw articles")

        if not raw_articles:
            logger.warning("[Agent] No raw articles found — returning empty")
            return []

        # ---- Step 2: LLM call — filter, rank, summarize ----
        logger.info("[Agent] Step 2: Sending to LLM for filtering and summarization")
        tiles = await self._llm_filter_and_summarize(raw_articles, country_name)

        # ---- Step 3: Fallback — if LLM fails, do basic processing ----
        if not tiles:
            logger.warning("[Agent] LLM filtering failed — using fallback processing")
            tiles = self._fallback_process(raw_articles)

        return tiles

    async def _llm_filter_and_summarize(self, articles: list[dict], country_name: str) -> list[dict]:
        """Use the LLM to filter and summarize articles into tiles."""
        articles_text = "\n".join(
            f"- [{i+1}] {a['title']} (Source: {a['source']}, Published: {a['published']}, Link: {a['link']})"
            for i, a in enumerate(articles[:40])  # cap input
        )

        system_prompt = f"""You are an AI news curator agent. Your task is to analyze the following news articles and select the most important, impactful, and breaking news stories specifically about Artificial Intelligence, Machine Learning, LLMs, and AI companies.

RULES:
1. Select up to 12 most important and UNIQUE stories
2. Focus on genuinely significant AI news (breakthroughs, major product launches, regulations, funding, research papers)
3. Ignore duplicate or near-duplicate stories — pick the best version
4. Ignore clickbait, opinion pieces, or vaguely AI-related stories
5. For each selected story, provide a concise 1-2 sentence summary
6. Assign a category: "breakthrough", "product", "regulation", "funding", "research", "industry", or "general"
7. Assign an importance score from 1-10
8. Consider relevance to {country_name} when applicable

OUTPUT FORMAT — respond ONLY with a valid JSON array, no extra text:
[
  {{
    "title": "Short headline",
    "summary": "1-2 sentence summary of why this matters",
    "category": "category_name",
    "importance": 8,
    "source": "Source name",
    "link": "URL",
    "published": "ISO date"
  }}
]"""

        user_prompt = f"""Here are the raw articles to analyze:

{articles_text}

Select and summarize the top AI news stories. Respond ONLY with a JSON array."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await call_llm(messages, self.hf_token)
        return self._parse_llm_response(response, articles)

    def _parse_llm_response(self, response: str, original_articles: list[dict]) -> list[dict]:
        """Parse the LLM JSON response into tile dicts."""
        if not response:
            logger.warning("[Agent] LLM returned empty response")
            return []

        logger.info(f"[Agent] Raw LLM response (first 500 chars): {response[:500]}")

        # Try to extract JSON array from response
        json_str = None

        # Method 1: Strip markdown code fences if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            # Remove ```json ... ``` or ``` ... ```
            cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```\s*$', '', cleaned)

        # Method 2: Try direct parse of cleaned response
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                json_str = cleaned
        except json.JSONDecodeError:
            pass

        # Method 3: Regex to find JSON array
        if json_str is None:
            json_match = re.search(r'\[\s*\{.*?\}\s*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()

        if json_str is None:
            logger.warning(f"[Agent] Could not find JSON array in LLM response")
            return []

        try:
            tiles = json.loads(json_str)
            if not isinstance(tiles, list):
                logger.warning("[Agent] Parsed JSON is not a list")
                return []

            # Validate and clean each tile
            clean_tiles = []
            for t in tiles:
                if isinstance(t, dict) and "title" in t:
                    try:
                        clean_tiles.append({
                            "title": str(t.get("title", ""))[:150],
                            "summary": str(t.get("summary", ""))[:300],
                            "category": str(t.get("category", "general")).lower(),
                            "importance": min(max(int(t.get("importance", 5)), 1), 10),
                            "source": str(t.get("source", "")),
                            "link": str(t.get("link", "")),
                            "published": str(t.get("published", "")),
                            "fetched_at": datetime.now(timezone.utc).isoformat(),
                        })
                    except (ValueError, TypeError) as e:
                        logger.warning(f"[Agent] Skipping malformed tile: {e}")
                        continue

            # Sort by importance desc
            clean_tiles.sort(key=lambda x: x["importance"], reverse=True)
            logger.info(f"[Agent] Successfully parsed {len(clean_tiles)} tiles from LLM")
            return clean_tiles[:MAX_TILES_PER_FETCH]

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[Agent] Failed to parse LLM JSON: {e}")
            logger.debug(f"[Agent] JSON string was: {json_str[:300]}")

        return []

    def _fallback_process(self, articles: list[dict]) -> list[dict]:
        """Basic fallback when LLM is unavailable — just clean and return top articles."""
        tiles = []
        for a in articles[:12]:
            tiles.append({
                "title": a["title"][:150],
                "summary": f"From {a['source']}" if a["source"] else "AI news update",
                "category": "general",
                "importance": 5,
                "source": a.get("source", ""),
                "link": a.get("link", ""),
                "published": a.get("published", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })
        return tiles


MAX_TILES_PER_FETCH = 12  # per refresh cycle; total cap is 24 in app.py
