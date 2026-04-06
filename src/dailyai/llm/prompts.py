"""
DailyAI — Centralized Prompt Templates
All LLM prompts in one place using LangChain ChatPromptTemplate.
Easy to tune, version, and A/B test.
"""

from langchain_core.prompts import ChatPromptTemplate

# ── News Curation Prompt ────────────────────────────────────────────

CURATION_SYSTEM = """You are an AI news curator agent. Your task is to analyze the following news articles and select the most important, impactful, and breaking news stories specifically about Artificial Intelligence, Machine Learning, LLMs, and AI companies.

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
13. Assign a sentiment: "bullish" (positive/optimistic for AI industry), "bearish" (negative/concerning), or "neutral"
14. Assign a story_thread — a short label (3-5 words max) grouping related articles about the same event/topic. E.g. "OpenAI GPT-5 Launch", "EU AI Act", "NVIDIA Earnings". Different articles about the same event MUST share the same story_thread.

OUTPUT FORMAT — respond ONLY with a valid JSON array, no extra text:
[
  {{
    "title": "Short headline",
    "summary": "1-2 sentence summary of why this matters",
    "why_it_matters": "One punchy sentence on why a busy professional should care",
    "category": "category_name",
    "topic": "topic_tag",
    "importance": 8,
    "sentiment": "bullish",
    "story_thread": "Short Thread Label",
    "source": "Source name",
    "link": "URL",
    "published": "ISO date"
  }}
]"""

CURATION_HUMAN = """Here are the raw articles to analyze:

{articles_text}

Select and summarize the top AI news stories in {output_language}. Respond ONLY with a JSON array."""

CURATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", CURATION_SYSTEM),
    ("human", CURATION_HUMAN),
])


# ── Article Brief Prompt ────────────────────────────────────────────

BRIEF_SYSTEM = """You are an expert AI news analyst.
Write a concise summary in {output_language}.

RULES:
1. Output EXACTLY 3 to 5 bullet points.
2. Each bullet starts with • and is 1-2 sentences max.
3. Cover: what happened, who is involved, why it matters, and what to watch next.
4. Stay factual — no hype or speculation.
5. Keep it short so readers want to click the original link for more.
6. Output plain text bullet points only. No headings, no markdown."""

BRIEF_HUMAN = """Article data:
Title: {title}
Source: {source}
Topic: {topic}
Link: {link}
Short summary: {summary}
Why it matters: {why_it_matters}

Write the detailed brief now in 100 words."""

BRIEF_PROMPT = ChatPromptTemplate.from_messages([
    ("system", BRIEF_SYSTEM),
    ("human", BRIEF_HUMAN),
])


# ── Prompt Leak Detection ──────────────────────────────────────────

PROMPT_LEAK_MARKERS: list[str] = [
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


def sanitize_llm_response(text: str) -> str:
    """Return empty string if the text contains prompt echo artifacts."""
    if not text:
        return ""
    hits = sum(1 for m in PROMPT_LEAK_MARKERS if m in text)
    if hits >= 3:
        return ""
    return text
