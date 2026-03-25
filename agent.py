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

import asyncio
import json
import logging
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import feedparser
import httpx

logger = logging.getLogger("dailyai.agent")

# Phrases that indicate the LLM echoed the prompt instead of responding
_PROMPT_LEAK_MARKERS = [
    "SYSTEM:",
    "USER:",
    "RULES:",
    "OUTPUT FORMAT",
    "Output EXACTLY",
    "Each bullet starts with",
    "Stay factual",
    "No headings, no markdown",
    "respond ONLY with a valid JSON",
    "You are an expert AI news analyst",
    "You are an AI news curator agent",
    "Article data:",
    "Write the detailed brief now.",
    "Short summary:",
    "Why it matters:",
]


def _sanitize_llm_response(text: str) -> str:
    """Return empty string if the text contains prompt echo artifacts."""
    if not text:
        return ""
    # Quick heuristic: if 3+ prompt markers appear, the model echoed the prompt
    hits = sum(1 for m in _PROMPT_LEAK_MARKERS if m in text)
    if hits >= 3:
        logger.warning(f"[Sanitize] Detected prompt leakage ({hits} markers found), discarding response")
        return ""
    return text

# ---------------------------------------------------------------------------
# RSS sources  (free, no API key needed)
# ---------------------------------------------------------------------------
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl={hl}&gl={gl}&ceid={gl}:{hl}"

FEED_QUERIES = {
    "ai_core": "artificial+intelligence+OR+AI+OR+machine+learning+OR+deep+learning+OR+LLM+OR+generative+AI",
    "ai_industry": "OpenAI+OR+Google+AI+OR+Meta+AI+OR+Anthropic+OR+Mistral+OR+DeepMind+OR+Hugging+Face",
    "ai_breakthroughs": "AI+breakthrough+OR+AI+launch+OR+AI+regulation+OR+AI+startup",
    "ai_research": "AI+research+paper+OR+arXiv+AI+OR+foundation+model+benchmark",
    "ai_infra": "NVIDIA+AI+chips+OR+AI+inference+OR+datacenter+AI+OR+GPU+cluster",
    "ai_policy": "AI+Act+OR+AI+policy+OR+AI+governance+OR+AI+safety+institute",
}

SUPPORTED_OUTPUT_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "de": "German",
}

LANG_MAP: dict[str, tuple[str, str]] = {
    "US": ("en", "US"),
    "GB": ("en", "GB"),
    "IN": ("en", "IN"),
    "DE": ("de", "DE"),
    "FR": ("fr", "FR"),
    "CA": ("en", "CA"),
    "AU": ("en", "AU"),
    "JP": ("ja", "JP"),
    "KR": ("ko", "KR"),
    "CN": ("zh-Hans", "CN"),
    "BR": ("pt-BR", "BR"),
    "SG": ("en", "SG"),
    "AE": ("en", "AE"),
    "IL": ("en", "IL"),
    "GLOBAL": ("en", "US"),
}

# ---------------------------------------------------------------------------
# Tools available to the agent
# ---------------------------------------------------------------------------


async def fetch_rss_feed(
    query: str, gl: str = "US", hl: str = "en", max_items: int = 15
) -> list[dict]:
    """Fetch items from Google News RSS."""
    url = GOOGLE_NEWS_RSS.format(query=query, hl=hl, gl=gl, ceid=f"{gl}:{hl}")
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 DailyAI/1.0"})
        resp.raise_for_status()

    feed = feedparser.parse(resp.text)
    cutoff = datetime.now(UTC) - timedelta(hours=26)  # slight overlap
    items = []
    for entry in feed.entries[:max_items]:
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            from time import mktime

            published = datetime.fromtimestamp(mktime(entry.published_parsed), tz=UTC)
        if published and published < cutoff:
            continue
        items.append(
            {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "source": (
                    entry.get("source", {}).get("title", "") if hasattr(entry, "source") else ""
                ),
                "published": published.isoformat() if published else "",
            }
        )
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

    def normalize_title(title: str) -> str:
        normalized = title.lower().strip()
        # Remove common headline suffixes like "- Reuters" or "| TechCrunch"
        normalized = re.sub(
            r"\s*[\-|\|:]\s*(reuters|associated press|ap news|techcrunch|the verge|wired|forbes|bloomberg).*$",
            "",
            normalized,
        )
        normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    # Deduplicate by normalized title
    seen = set()
    unique = []
    for item in all_items:
        key = normalize_title(item["title"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


# ---------------------------------------------------------------------------
# LLM Providers — tries Google Gemini first, then HuggingFace, then Groq
# ---------------------------------------------------------------------------

# Provider 0: Google Gemini (free via AI Studio — ~1500 req/day, 1M TPM)
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

# Provider 1: HuggingFace (free serverless API)
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODELS = [
    "mistralai/Mistral-Small-24B-Instruct-2501",
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
]

# Provider 2: Groq (free, fast) — uses GROQ_API_KEY env var
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

DISABLED_PROVIDERS: set[str] = set()


def _get_ollama_config() -> tuple[str, list[str]]:
    """Return OpenAI-compatible Ollama endpoint and model list from env."""
    base = os.getenv("OLLAMA_BASE_URL", "").strip().rstrip("/")
    if not base:
        return "", []

    # Supports both http://localhost:11434 and http://localhost:11434/v1
    if not base.endswith("/v1"):
        base = f"{base}/v1"

    model_csv = os.getenv("OLLAMA_MODELS", "llama3.1:8b")
    models = [m.strip() for m in model_csv.split(",") if m.strip()]
    return f"{base}/chat/completions", models


async def _try_provider(
    url: str,
    models: list[str],
    messages: list[dict],
    token: str,
    max_tokens: int = 2048,
    provider_name: str = "",
) -> str:
    """Try a list of models on a given OpenAI-compatible endpoint."""
    if provider_name and provider_name in DISABLED_PROVIDERS:
        return ""

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for model in models:
        # Cap tokens for smaller models to avoid 413
        model_max = max_tokens
        if "8b" in model or "3b" in model:
            model_max = min(max_tokens, 2048)
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": model_max,
            "temperature": 0.3,
        }
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        content_obj = choices[0].get("message", {}).get("content", "")
                        content = content_obj if isinstance(content_obj, str) else ""
                        if content:
                            logger.info(f"[LLM] ✅ Got response from {model}")
                            return content
                elif resp.status_code == 413:
                    logger.warning(f"[LLM] {model} → 413 Payload too large, skipping")
                    continue
                elif resp.status_code == 429:
                    logger.warning(f"[LLM] {model} → 429 Rate limited, skipping")
                    continue
                elif resp.status_code == 401:
                    logger.warning(
                        f"[LLM] {model} → 401 Unauthorized. Check API key/token for this provider."
                    )
                    if provider_name:
                        DISABLED_PROVIDERS.add(provider_name)
                    return ""
                else:
                    logger.warning(f"[LLM] {model} → {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"[LLM] {model} failed: {e}")
            continue
    return ""


async def _try_gemini(
    models: list[str], messages: list[dict], api_key: str, max_tokens: int = 2048
) -> str:
    """Try Google Gemini models using the AI Studio OpenAI-compatible endpoint."""
    if "gemini" in DISABLED_PROVIDERS:
        return ""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    for model in models:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(GEMINI_API_URL, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        content_obj = choices[0].get("message", {}).get("content", "")
                        content = content_obj if isinstance(content_obj, str) else ""
                        if content:
                            logger.info(f"[LLM] ✅ Got response from {model}")
                            return content
                elif resp.status_code == 429:
                    logger.warning(f"[LLM] {model} → 429 Rate limited, skipping")
                    continue
                elif resp.status_code in (400, 401, 403):
                    logger.warning(
                        f"[LLM] {model} → {resp.status_code}. Gemini auth/permission issue. Check GOOGLE_AI_KEY."
                    )
                    DISABLED_PROVIDERS.add("gemini")
                    return ""
                else:
                    logger.warning(f"[LLM] {model} → {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"[LLM] {model} failed: {e}")
            continue
    return ""


async def _try_bytez(messages: list[dict]) -> str:
    """Try Bytez API (Mistral-7B) as primary provider."""
    bytez_key = os.getenv("BYTEZ_API_KEY", "")
    if not bytez_key:
        return ""
    if "bytez" in DISABLED_PROVIDERS:
        return ""

    try:
        from bytez import Bytez
        sdk = Bytez(bytez_key)
        model = sdk.model("mistralai/Mistral-7B-Instruct-v0.3")

        # Convert messages to a single string prompt since Bytez expects text
        prompt_parts = []
        for m in messages:
            role = m.get("role", "").upper()
            content = m.get("content", "")
            prompt_parts.append(f"{role}:\n{content}")
        prompt = "\n\n".join(prompt_parts)

        # model.run is synchronous, run in executor to avoid blocking event loop
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, model.run, prompt)

        if hasattr(results, 'error') and getattr(results, 'error', None):
            logger.warning(f"[LLM] Bytez error: {results.error}")

        if hasattr(results, 'output') and results.output:
            logger.info("[LLM] ✅ Got response from Bytez (Mistral-7B)")
            out = results.output
            if isinstance(out, list) and len(out) > 0 and isinstance(out[0], dict) and "generated_text" in out[0]:
                text = out[0]["generated_text"]
                # Bytez Mistral echoes prompt — strip everything before actual response
                # Try multiple end-of-prompt markers in priority order
                for marker in [
                    "Write the detailed brief now.",
                    "Output valid JSON only.",
                    "Return the JSON array now.",
                    "Respond ONLY with a JSON array.",
                    "ASSISTANT:",
                    "assistant:",
                ]:
                    if marker in text:
                        text = text.split(marker, 1)[-1].strip()
                        break

                # Second pass: if SYSTEM:/USER: markers are still present,
                # the model echoed the whole prompt — discard it entirely
                text = _sanitize_llm_response(text)
                return text
            raw = str(out)
            return _sanitize_llm_response(raw)
    except Exception as e:
        logger.warning(f"[LLM] Bytez failed: {e}")
    return ""



async def call_llm(messages: list[dict], hf_token: str, max_tokens: int = 2048) -> str:
    """Try Bytez first, then local Ollama, then Gemini, then HuggingFace, then Groq."""

    # Try Bytez API (Primary LLM)
    result = await _try_bytez(messages)
    if result:
        return result
    logger.warning("[LLM] Bytez failed/not configured, trying local Ollama...")

    # Try local open-source models first (Ollama, optional)
    ollama_url, ollama_models = _get_ollama_config()
    if ollama_url and ollama_models:
        result = await _try_provider(
            ollama_url,
            ollama_models,
            messages,
            token="",
            max_tokens=max_tokens,
            provider_name="ollama",
        )
        if result:
            return result
        logger.warning("[LLM] All Ollama models failed, trying cloud providers...")

    # Try Google Gemini first (most generous free tier)
    gemini_key = os.getenv("GOOGLE_AI_KEY", "")
    if gemini_key:
        result = await _try_gemini(GEMINI_MODELS, messages, gemini_key, max_tokens)
        if result:
            return result
        logger.warning("[LLM] All Gemini models failed, trying HuggingFace...")

    # Try HuggingFace
    if hf_token:
        result = await _try_provider(
            HF_API_URL,
            HF_MODELS,
            messages,
            hf_token,
            max_tokens,
            provider_name="huggingface",
        )
        if result:
            return result
        logger.warning("[LLM] All HuggingFace models failed, trying Groq...")

    # Try Groq as fallback
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        result = await _try_provider(
            GROQ_API_URL,
            GROQ_MODELS,
            messages,
            groq_key,
            max_tokens,
            provider_name="groq",
        )
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

    def __init__(self, hf_token: str | None = None):
        self.hf_token = hf_token or ""
        self.high_trust_sources = {
            "reuters",
            "associated press",
            "ap news",
            "financial times",
            "bloomberg",
            "wsj",
            "the economist",
            "nature",
            "science",
            "mit technology review",
            "arxiv",
            "the verge",
            "techcrunch",
            "wired",
            "bbc",
            "the guardian",
            "cnbc",
        }

    async def run(
        self, country_code: str, country_name: str, language_code: str = "en"
    ) -> list[dict]:
        """Execute the full agentic pipeline."""
        language_code = (language_code or "en").lower()
        if language_code not in SUPPORTED_OUTPUT_LANGUAGES:
            language_code = "en"

        # ---- Step 1: Tool call — fetch raw news ----
        logger.info(f"[Agent] Step 1: Fetching raw news for {country_name} ({country_code})")
        raw_articles = await fetch_ai_news(country_code)
        logger.info(f"[Agent] Fetched {len(raw_articles)} raw articles")

        if not raw_articles:
            logger.warning("[Agent] No raw articles found — returning empty")
            return []

        # ---- Step 2: LLM call — filter, rank, summarize ----
        logger.info("[Agent] Step 2: Sending to LLM for filtering and summarization")
        tiles = await self._llm_filter_and_summarize(raw_articles, country_name, language_code)

        # ---- Step 3: Pad with fallback when LLM returns too few tiles ----
        MIN_FEED_SIZE = 15
        if len(tiles) < MIN_FEED_SIZE:
            logger.warning(
                f"[Agent] LLM returned only {len(tiles)} tiles — padding with fallback (need {MIN_FEED_SIZE})"
            )
            # Build set of titles we already have
            existing_titles = {
                re.sub(r"\W+", " ", str(t.get("title", "")).lower()).strip()
                for t in tiles
            }
            fallback_tiles = self._fallback_process(raw_articles, language_code)
            for ft in fallback_tiles:
                norm = re.sub(r"\W+", " ", str(ft.get("title", "")).lower()).strip()
                if norm not in existing_titles:
                    tiles.append(ft)
                    existing_titles.add(norm)
                if len(tiles) >= MAX_TILES_PER_FETCH:
                    break
            logger.info(f"[Agent] After padding: {len(tiles)} tiles total")

        tiles = self._quality_rerank(tiles)
        tiles = self._enforce_topic_diversity(tiles)

        return tiles

    async def _llm_filter_and_summarize(
        self, articles: list[dict], country_name: str, language_code: str
    ) -> list[dict]:
        """Use the LLM to filter and summarize articles into tiles."""
        # Cap at 32 articles for richer candidate pool while staying below payload limits.
        capped = articles[:32]
        articles_text = "\n".join(
            f"- [{i+1}] {a['title']} (Source: {a['source']}, Link: {a['link']})"
            for i, a in enumerate(capped)
        )
        output_language = SUPPORTED_OUTPUT_LANGUAGES.get(language_code, "English")

        system_prompt = f"""You are an AI news curator agent. Your task is to analyze the following news articles and select the most important, impactful, and breaking news stories specifically about Artificial Intelligence, Machine Learning, LLMs, and AI companies.

RULES:
1. Select up to 20 most important and UNIQUE stories
2. Focus on genuinely significant AI news (breakthroughs, major product launches, regulations, funding, research papers)
3. Ignore duplicate or near-duplicate stories — pick the best version
4. Ignore clickbait, opinion pieces, or vaguely AI-related stories
5. For each selected story, provide a concise 1-2 sentence summary based on factual details from the headline context
6. Add a "why_it_matters" field — a single punchy sentence explaining why a busy AI professional should care (avoid hype)
7. Assign a category: "breakthrough", "product", "regulation", "funding", "research", "industry", or "general"
8. Assign a topic tag from: "llms", "robotics", "ai_safety", "funding", "research", "regulation", "startups", "big_tech", "open_source", "healthcare", "autonomous", "general"
9. Assign an importance score from 1-10
10. Consider relevance to {country_name} when applicable
11. Prefer trustworthy, primary reporting sources over low-credibility or duplicate aggregators
12. Return title, summary and why_it_matters in {output_language}

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

    Select and summarize the top AI news stories in {output_language}. Respond ONLY with a JSON array."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await call_llm(messages, self.hf_token, max_tokens=4096)
        return self._parse_llm_response(response, articles)

    def _source_quality_score(self, source: str) -> int:
        src = (source or "").strip().lower()
        if not src:
            return 0
        if any(trusted in src for trusted in self.high_trust_sources):
            return 2
        if "news" in src or "times" in src or "post" in src or "journal" in src:
            return 1
        return 0

    def _quality_rerank(self, tiles: list[dict]) -> list[dict]:
        now = datetime.now(UTC)

        def recency_score(published: str) -> int:
            if not published:
                return 0
            try:
                dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                age_hours = max((now - dt).total_seconds() / 3600, 0)
                if age_hours <= 8:
                    return 2
                if age_hours <= 24:
                    return 1
            except Exception:
                return 0
            return 0

        for t in tiles:
            base = int(t.get("importance", 5))
            src_bonus = self._source_quality_score(str(t.get("source", "")))
            fresh_bonus = recency_score(str(t.get("published", "")))
            t["quality_score"] = base * 10 + src_bonus * 3 + fresh_bonus

        tiles.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        return tiles[:MAX_TILES_PER_FETCH]

    def _enforce_topic_diversity(self, tiles: list[dict]) -> list[dict]:
        """Avoid over-clustering by limiting repeated topics in top slots."""
        if len(tiles) <= 6:
            return tiles

        selected: list[dict] = []
        topic_counts: dict[str, int] = {}

        for tile in tiles:
            topic = str(tile.get("topic", "general") or "general")
            cap = 3 if len(selected) < 12 else 4
            if topic_counts.get(topic, 0) < cap:
                selected.append(tile)
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            if len(selected) >= MAX_TILES_PER_FETCH:
                break

        if len(selected) < min(MAX_TILES_PER_FETCH, len(tiles)):
            existing_titles = {s.get("title", "") for s in selected}
            for tile in tiles:
                if tile.get("title", "") not in existing_titles:
                    selected.append(tile)
                if len(selected) >= MAX_TILES_PER_FETCH:
                    break

        return selected

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
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```\s*$", "", cleaned)
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
            start_idx = response.find("[")
            if start_idx != -1:
                depth = 0
                end_found = False
                for i in range(start_idx, len(response)):
                    if response[i] == "[":
                        depth += 1
                    elif response[i] == "]":
                        depth -= 1
                        if depth == 0:
                            end_found = True
                            candidate = response[start_idx : i + 1]
                            try:
                                parsed = json.loads(candidate)
                                if isinstance(parsed, list):
                                    json_str = candidate
                                    logger.info(
                                        f"[Agent] Extracted JSON array ({len(parsed)} items) via bracket matching"
                                    )
                            except json.JSONDecodeError:
                                pass
                            break

                # Method 4: Handle truncated JSON — try to recover partial array
                if not end_found and json_str is None:
                    logger.warning("[Agent] JSON array appears truncated, attempting recovery...")
                    partial = response[start_idx:]
                    # Try to find the last complete object by looking for '},'
                    # and closing the array there
                    last_complete = partial.rfind("},")
                    if last_complete == -1:
                        last_complete = partial.rfind("}")
                    if last_complete != -1:
                        candidate = partial[: last_complete + 1].rstrip(",") + "]"
                        try:
                            parsed = json.loads(candidate)
                            if isinstance(parsed, list) and len(parsed) > 0:
                                json_str = candidate
                                logger.info(
                                    f"[Agent] Recovered {len(parsed)} items from truncated JSON"
                                )
                        except json.JSONDecodeError:
                            # Try more aggressive trimming: remove last partial object
                            last_comma = partial[:last_complete].rfind("},")
                            if last_comma != -1:
                                candidate = partial[: last_comma + 1] + "]"
                                try:
                                    parsed = json.loads(candidate)
                                    if isinstance(parsed, list) and len(parsed) > 0:
                                        json_str = candidate
                                        logger.info(
                                            f"[Agent] Recovered {len(parsed)} items from truncated JSON (aggressive trim)"
                                        )
                                except json.JSONDecodeError:
                                    pass

        if json_str is None:
            logger.warning("[Agent] Could not find JSON array in LLM response")
            return []

        try:
            tiles = json.loads(json_str)
            if not isinstance(tiles, list):
                logger.warning("[Agent] Parsed JSON is not a list")
                return []

            # Template/placeholder values the LLM may echo from the prompt example
            TEMPLATE_VALUES = {
                "short headline", "source name", "url", "iso date",
                "category_name", "topic_tag", "1-2 sentence summary",
                "one punchy sentence",
            }

            def _is_template(tile: dict) -> bool:
                """Return True if a tile contains placeholder text from the prompt."""
                for field in ("title", "source", "link", "published"):
                    val = str(tile.get(field, "")).strip().lower()
                    if val in TEMPLATE_VALUES:
                        return True
                title_lower = str(tile.get("title", "")).strip().lower()
                if title_lower.startswith("short headline") or title_lower == "":
                    return True
                return False

            # Validate and clean each tile
            clean_tiles = []
            seen_titles: set[str] = set()
            for t in tiles:
                if isinstance(t, dict) and "title" in t:
                    try:
                        # Skip template/example tiles
                        if _is_template(t):
                            logger.info(f"[Agent] Filtered out template tile: {t.get('title', '')[:60]}")
                            continue

                        normalized_title = re.sub(
                            r"\W+", " ", str(t.get("title", "")).lower()
                        ).strip()
                        if normalized_title in seen_titles:
                            continue
                        seen_titles.add(normalized_title)

                        importance_raw: Any = t.get("importance", 5)
                        try:
                            importance_val = int(importance_raw)
                        except (TypeError, ValueError):
                            importance_val = 5

                        raw_summary = str(t.get("summary", ""))[:300]
                        raw_why = str(t.get("why_it_matters", ""))[:200]
                        # Reject individual fields that contain prompt leakage
                        summary_clean = _sanitize_llm_response(raw_summary) or raw_summary[:0]
                        why_clean = _sanitize_llm_response(raw_why) or raw_why[:0]

                        clean_tiles.append(
                            {
                                "title": str(t.get("title", ""))[:150],
                                "summary": summary_clean or "Tap to read the full story.",
                                "why_it_matters": why_clean or "",
                                "category": str(t.get("category", "general")).lower(),
                                "topic": str(t.get("topic", "general")).lower(),
                                "importance": min(max(importance_val, 1), 10),
                                "source": str(t.get("source", "")),
                                "link": str(t.get("link", "")),
                                "published": str(t.get("published", "")),
                                "fetched_at": datetime.now(UTC).isoformat(),
                            }
                        )
                    except (ValueError, TypeError) as e:
                        logger.warning(f"[Agent] Skipping malformed tile: {e}")
                        continue

            # Sort by importance desc
            def importance_sort_key(tile: dict[str, object]) -> int:
                value = tile.get("importance", 0)
                return value if isinstance(value, int) else 0

            clean_tiles.sort(key=importance_sort_key, reverse=True)
            logger.info(f"[Agent] Successfully parsed {len(clean_tiles)} tiles from LLM")
            return clean_tiles[:MAX_TILES_PER_FETCH]

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[Agent] Failed to parse LLM JSON: {e}")
            logger.debug(f"[Agent] JSON string was: {json_str[:300]}")

        return []

    def _fallback_process(self, articles: list[dict], language_code: str = "en") -> list[dict]:
        """Smart fallback when LLM is unavailable — assigns topics from keywords."""
        KEYWORD_TOPICS = {
            "openai": ("big_tech", "industry"),
            "google": ("big_tech", "industry"),
            "meta ": ("big_tech", "industry"),
            "anthropic": ("big_tech", "industry"),
            "mistral": ("big_tech", "industry"),
            "deepmind": ("big_tech", "research"),
            "llm": ("llms", "product"),
            "gpt": ("llms", "product"),
            "chatgpt": ("llms", "product"),
            "gemini": ("llms", "product"),
            "claude": ("llms", "product"),
            "llama": ("llms", "product"),
            "robot": ("robotics", "product"),
            "autonomous": ("autonomous", "product"),
            "regulat": ("regulation", "regulation"),
            "safety": ("ai_safety", "regulation"),
            "funding": ("funding", "funding"),
            "rais": ("funding", "funding"),
            "invest": ("funding", "funding"),
            "startup": ("startups", "funding"),
            "open source": ("open_source", "product"),
            "research": ("research", "research"),
            "paper": ("research", "research"),
            "health": ("healthcare", "product"),
        }

        fallback_why = {
            "en": "Stay informed - this story is trending in the AI community right now.",
            "hi": "जानकारी में रहें - यह स्टोरी अभी AI समुदाय में तेजी से ट्रेंड कर रही है.",
            "de": "Bleiben Sie informiert - diese Story ist gerade in der KI-Community im Trend.",
        }
        fallback_summary = {
            "en": "Reported by {source}. Tap to read the full story and get more details on this developing AI news.",
            "hi": "{source} की रिपोर्ट. पूरी स्टोरी पढ़ने और इस AI अपडेट की अधिक जानकारी के लिए टैप करें.",
            "de": "Berichtet von {source}. Tippen Sie, um die ganze Story und mehr Details zu diesem KI-Update zu lesen.",
        }
        lang = language_code if language_code in fallback_summary else "en"

        tiles = []
        for i, a in enumerate(articles[:20]):
            title_lower = a["title"].lower()
            topic, category = "general", "general"
            importance = max(7 - i // 2, 4)  # 7, 7, 6, 6, 5, 5, 4...
            for kw, (t, c) in KEYWORD_TOPICS.items():
                if kw in title_lower:
                    topic, category = t, c
                    break

            source = a.get("source", "")
            if source:
                summary = fallback_summary[lang].format(source=source)
            else:
                summary = {
                    "en": "Tap to read the full story and get more details on this AI news update.",
                    "hi": "इस AI न्यूज़ अपडेट की पूरी जानकारी के लिए पूरी स्टोरी पढ़ें.",
                    "de": "Tippen Sie, um die ganze Story und weitere Details zu diesem KI-Update zu lesen.",
                }.get(
                    lang, "Tap to read the full story and get more details on this AI news update."
                )

            tiles.append(
                {
                    "title": a["title"][:150],
                    "summary": summary,
                    "why_it_matters": fallback_why.get(lang, fallback_why["en"]),
                    "category": category,
                    "topic": topic,
                    "importance": importance,
                    "source": source,
                    "link": a.get("link", ""),
                    "published": a.get("published", ""),
                    "fetched_at": datetime.now(UTC).isoformat(),
                }
            )
        return tiles

    async def generate_topic_brief(
        self,
        *,
        title: str,
        source: str,
        link: str,
        summary: str,
        why_it_matters: str,
        topic: str,
        language_code: str = "en",
    ) -> str:
        """Generate a concise 3-5 bullet point brief for one article."""
        language_code = (language_code or "en").lower()
        output_language = SUPPORTED_OUTPUT_LANGUAGES.get(language_code, "English")

        system_prompt = f"""You are an expert AI news analyst.
Write a concise summary in {output_language}.

RULES:
1. Output EXACTLY 3 to 5 bullet points.
2. Each bullet starts with • and is 1-2 sentences max.
3. Cover: what happened, who is involved, why it matters, and what to watch next.
4. Stay factual — no hype or speculation.
5. Keep it short so readers want to click the original link for more.
6. Output plain text bullet points only. No headings, no markdown.
"""

        user_prompt = f"""Article data:
Title: {title}
Source: {source}
Topic: {topic}
Link: {link}
Short summary: {summary}
Why it matters: {why_it_matters}

Write the detailed brief now in 100 words."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await call_llm(messages, self.hf_token, max_tokens=800)
        cleaned = (response or "").strip()
        if not cleaned:
            return summary or why_it_matters or "No additional details available yet."

        # Guard: reject responses that echo the prompt back
        sanitized = _sanitize_llm_response(cleaned)
        if not sanitized:
            logger.warning("[Agent] Brief response contained prompt leakage — using fallback")
            return summary or why_it_matters or "No additional details available yet."

        return sanitized[:1200]


MAX_TILES_PER_FETCH = 20  # per refresh cycle
