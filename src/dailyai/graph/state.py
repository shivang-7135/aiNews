"""
DailyAI — LangGraph Pipeline State
TypedDict defining the data that flows through each graph node.
"""

from __future__ import annotations

from typing import TypedDict


class PipelineState(TypedDict):
    """State object passed through the LangGraph news pipeline.

    Each node reads from and writes to specific keys.
    The graph runtime handles state merging between nodes.
    """

    # ── Input ───────────────────────────────────────────────────────
    country_code: str
    country_name: str
    language: str

    # ── Stage outputs ───────────────────────────────────────────────
    raw_articles: list[dict]       # collector → deduplicator
    deduplicated: list[dict]       # deduplicator → curator
    curated: list[dict]            # curator → trust
    trust_scored: list[dict]       # trust → sentiment
    sentiment_tagged: list[dict]   # sentiment → threader
    threaded: list[dict]           # threader → personalizer

    # ── Personalization context ─────────────────────────────────────
    user_sync_code: str            # Optional: for personalized ranking
    user_profile: dict | None      # Loaded profile data

    # ── Output ──────────────────────────────────────────────────────
    final_feed: list[dict]         # The finished, ranked feed

    # ── Observability ───────────────────────────────────────────────
    errors: list[str]              # Error messages from any node
    node_timings: dict[str, float] # Performance tracking per node
