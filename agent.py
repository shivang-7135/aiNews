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
# LLM Providers — tries HuggingFace first, then Groq (both free)
# ---------------------------------------------------------------------------

# Provider 1: HuggingFace router
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODELS = [
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "mistralai/Mistral-Small-24B-Instruct-2501",
]

# Provider 2: Groq (free, fast) — uses GROQ_API_KEY env var
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]


async def _try_provider(url: str, models: list[str], messages: list[dict],
                        token: str, max_tokens: int = 2048) -> str:
    """Try a list of models on a given OpenAI-compatible endpoint."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for model in models:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        if content:
                            logger.info(f"[LLM] ✅ Got response from {model}")
                            return content
                else:
                    logger.warning(f"[LLM] {model} → {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"[LLM] {model} failed: {e}")
            continue
    return ""


async def call_llm(messages: list[dict], hf_token: str, max_tokens: int = 2048) -> str:
    """Try HuggingFace first, then Groq as fallback."""
    import os

    # Try HuggingFace
    if hf_token:
        result = await _try_provider(HF_API_URL, HF_MODELS, messages, hf_token, max_tokens)
        if result:
            return result
        logger.warning("[LLM] All HuggingFace models failed, trying Groq...")

    # Try Groq as fallback
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        result = await _try_provider(GROQ_API_URL, GROQ_MODELS, messages, groq_key, max_tokens)
        if result:
            return result

    logger.error("[LLM] All providers failed")
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
6. Add a "why_it_matters" field — a single punchy sentence explaining why a busy AI professional should care
7. Assign a category: "breakthrough", "product", "regulation", "funding", "research", "industry", or "general"
8. Assign a topic tag from: "llms", "robotics", "ai_safety", "funding", "research", "regulation", "startups", "big_tech", "open_source", "healthcare", "autonomous", "general"
9. Assign an importance score from 1-10
10. Consider relevance to {country_name} when applicable

OUTPUT FORMAT — respond ONLY with a valid JSON array, no extra text:
[
  {{
    "title": "Short headline",
    "summary": "1-2 sentence summary of why this matters",
    "why_it_matters": "One punchy sentence on why a busy professional should care",
    "category": "category_name",
    "topic": "topic_tag",
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

        response = await call_llm(messages, self.hf_token, max_tokens=4096)
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
            cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```\s*$', '', cleaned)
            cleaned = cleaned.strip()

        # Method 2: Try direct parse of cleaned response
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                json_str = cleaned
        except json.JSONDecodeError:
            pass

        # Method 3: Find the first '[' and its matching ']' using bracket counting
        if json_str is None:
            start_idx = response.find('[')
            if start_idx != -1:
                depth = 0
                end_found = False
                for i in range(start_idx, len(response)):
                    if response[i] == '[':
                        depth += 1
                    elif response[i] == ']':
                        depth -= 1
                        if depth == 0:
                            end_found = True
                            candidate = response[start_idx:i + 1]
                            try:
                                parsed = json.loads(candidate)
                                if isinstance(parsed, list):
                                    json_str = candidate
                                    logger.info(f"[Agent] Extracted JSON array ({len(parsed)} items) via bracket matching")
                            except json.JSONDecodeError:
                                pass
                            break

                # Method 4: Handle truncated JSON — try to recover partial array
                if not end_found and json_str is None:
                    logger.warning("[Agent] JSON array appears truncated, attempting recovery...")
                    partial = response[start_idx:]
                    # Try to find the last complete object by looking for '},'
                    # and closing the array there
                    last_complete = partial.rfind('},')
                    if last_complete == -1:
                        last_complete = partial.rfind('}')
                    if last_complete != -1:
                        candidate = partial[:last_complete + 1].rstrip(',') + ']'
                        try:
                            parsed = json.loads(candidate)
                            if isinstance(parsed, list) and len(parsed) > 0:
                                json_str = candidate
                                logger.info(f"[Agent] Recovered {len(parsed)} items from truncated JSON")
                        except json.JSONDecodeError:
                            # Try more aggressive trimming: remove last partial object
                            last_comma = partial[:last_complete].rfind('},')
                            if last_comma != -1:
                                candidate = partial[:last_comma + 1] + ']'
                                try:
                                    parsed = json.loads(candidate)
                                    if isinstance(parsed, list) and len(parsed) > 0:
                                        json_str = candidate
                                        logger.info(f"[Agent] Recovered {len(parsed)} items from truncated JSON (aggressive trim)")
                                except json.JSONDecodeError:
                                    pass

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
                            "why_it_matters": str(t.get("why_it_matters", ""))[:200],
                            "category": str(t.get("category", "general")).lower(),
                            "topic": str(t.get("topic", "general")).lower(),
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
        """Smart fallback when LLM is unavailable — assigns topics from keywords."""
        KEYWORD_TOPICS = {
            "openai": ("big_tech", "industry"), "google": ("big_tech", "industry"),
            "meta ": ("big_tech", "industry"), "anthropic": ("big_tech", "industry"),
            "mistral": ("big_tech", "industry"), "deepmind": ("big_tech", "research"),
            "llm": ("llms", "product"), "gpt": ("llms", "product"),
            "chatgpt": ("llms", "product"), "gemini": ("llms", "product"),
            "claude": ("llms", "product"), "llama": ("llms", "product"),
            "robot": ("robotics", "product"), "autonomous": ("autonomous", "product"),
            "regulat": ("regulation", "regulation"), "safety": ("ai_safety", "regulation"),
            "funding": ("funding", "funding"), "rais": ("funding", "funding"),
            "invest": ("funding", "funding"), "startup": ("startups", "funding"),
            "open source": ("open_source", "product"), "research": ("research", "research"),
            "paper": ("research", "research"), "health": ("healthcare", "product"),
        }

        tiles = []
        for i, a in enumerate(articles[:12]):
            title_lower = a["title"].lower()
            topic, category = "general", "general"
            importance = max(7 - i // 2, 4)  # 7, 7, 6, 6, 5, 5, 4...
            for kw, (t, c) in KEYWORD_TOPICS.items():
                if kw in title_lower:
                    topic, category = t, c
                    break

            source = a.get("source", "")
            summary = f"Reported by {source}. Tap to read the full story and get more details on this developing AI news." if source else "Tap to read the full story and get more details on this AI news update."

            tiles.append({
                "title": a["title"][:150],
                "summary": summary,
                "why_it_matters": "Stay informed — this story is trending in the AI community right now.",
                "category": category,
                "topic": topic,
                "importance": importance,
                "source": source,
                "link": a.get("link", ""),
                "published": a.get("published", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })
        return tiles


MAX_TILES_PER_FETCH = 12  # per refresh cycle; total cap is 24 in app.py
