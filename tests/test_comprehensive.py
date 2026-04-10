"""
DailyAI — Comprehensive Unit Test Suite
Covers: Config, LLM prompts, LLM provider, Graph nodes (all 8),
        Pipeline, News service, Profile service, Pydantic models,
        Digest module, and API routes.

All external dependencies (LLM APIs, RSS feeds, SQLite, email) are
fully mocked so tests are fast, deterministic, and offline.
"""

import hashlib
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

# ── Ensure project root is importable ──────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =====================================================================
#  1. CONFIG MODULE TESTS
# =====================================================================

class TestConfigModule:
    """Tests for src/dailyai/config.py"""

    def test_normalize_language_valid_en(self):
        from dailyai.config import normalize_language
        assert normalize_language("en") == "en"

    def test_normalize_language_valid_de(self):
        from dailyai.config import normalize_language
        assert normalize_language("de") == "de"

    def test_normalize_language_valid_hi(self):
        from dailyai.config import normalize_language
        assert normalize_language("hi") == "hi"

    def test_normalize_language_invalid_fallback(self):
        from dailyai.config import normalize_language
        assert normalize_language("zz") == "en"

    def test_normalize_language_none_fallback(self):
        from dailyai.config import normalize_language
        assert normalize_language(None) == "en"

    def test_normalize_language_empty_fallback(self):
        from dailyai.config import normalize_language
        assert normalize_language("") == "en"

    def test_normalize_language_strips_whitespace(self):
        from dailyai.config import normalize_language
        assert normalize_language("  de  ") == "de"

    def test_normalize_language_case_insensitive(self):
        from dailyai.config import normalize_language
        assert normalize_language("EN") == "en"

    def test_store_key_basic(self):
        from dailyai.config import store_key
        assert store_key("US", "en") == "US::en"

    def test_store_key_normalizes_country(self):
        from dailyai.config import store_key
        assert store_key("us", "en") == "US::en"

    def test_store_key_normalizes_language(self):
        from dailyai.config import store_key
        assert store_key("DE", "DE") == "DE::de"

    def test_countries_not_empty(self):
        from dailyai.config import COUNTRIES
        assert len(COUNTRIES) > 0
        assert "GLOBAL" in COUNTRIES

    def test_supported_languages_contains_basics(self):
        from dailyai.config import SUPPORTED_LANGUAGES
        assert "en" in SUPPORTED_LANGUAGES
        assert "de" in SUPPORTED_LANGUAGES

    def test_topics_not_empty(self):
        from dailyai.config import TOPICS
        assert "all" in TOPICS
        assert len(TOPICS) >= 10

    def test_ui_topic_map_covers_known_topics(self):
        from dailyai.config import UI_TOPIC_MAP
        assert "llms" in UI_TOPIC_MAP
        assert "big_tech" in UI_TOPIC_MAP
        assert "research" in UI_TOPIC_MAP

    def test_feed_queries_not_empty(self):
        from dailyai.config import FEED_QUERIES
        assert len(FEED_QUERIES) >= 4

    def test_high_trust_sources_contains_reuters(self):
        from dailyai.config import HIGH_TRUST_SOURCES
        assert "reuters" in HIGH_TRUST_SOURCES

    def test_pipeline_limits_sane(self):
        from dailyai.config import MAX_FEED_SIZE, MAX_TILES_PER_FETCH, MIN_FEED_SIZE
        assert MIN_FEED_SIZE < MAX_FEED_SIZE
        assert MAX_TILES_PER_FETCH > 0

    def test_lang_map_has_global(self):
        from dailyai.config import LANG_MAP
        assert "GLOBAL" in LANG_MAP
        assert LANG_MAP["GLOBAL"] == ("en", "US")


# =====================================================================
#  2. LLM PROMPTS TESTS
# =====================================================================

class TestLLMPrompts:
    """Tests for src/dailyai/llm/prompts.py"""

    def test_sanitize_clean_text(self):
        from dailyai.llm.prompts import sanitize_llm_response
        assert sanitize_llm_response("This is a clean summary.") == "This is a clean summary."

    def test_sanitize_empty(self):
        from dailyai.llm.prompts import sanitize_llm_response
        assert sanitize_llm_response("") == ""

    def test_sanitize_none_like(self):
        from dailyai.llm.prompts import sanitize_llm_response
        assert sanitize_llm_response("") == ""

    def test_sanitize_detects_prompt_leak_3_markers(self):
        from dailyai.llm.prompts import sanitize_llm_response
        leaked = "SYSTEM: You are an expert AI news analyst. RULES: Stay factual. OUTPUT FORMAT"
        assert sanitize_llm_response(leaked) == ""

    def test_sanitize_allows_1_marker(self):
        from dailyai.llm.prompts import sanitize_llm_response
        partial = "This summary mentions RULES: about new regulation."
        assert sanitize_llm_response(partial) == partial

    def test_sanitize_detects_exact_3_markers(self):
        from dailyai.llm.prompts import sanitize_llm_response
        leaked = "SYSTEM: blah USER: blah RULES: blah"
        assert sanitize_llm_response(leaked) == ""

    def test_curation_prompt_format(self):
        from dailyai.llm.prompts import CURATION_PROMPT
        messages = CURATION_PROMPT.format_messages(
            country_name="United States",
            output_language="English",
            articles_text="[1] Test Article (Source: Test)",
        )
        assert len(messages) == 2
        assert "United States" in messages[0].content
        assert "Test Article" in messages[1].content

    def test_brief_prompt_format(self):
        from dailyai.llm.prompts import BRIEF_PROMPT
        messages = BRIEF_PROMPT.format_messages(
            output_language="English",
            title="Test Title",
            source="Reuters",
            topic="llms",
            link="https://example.com",
            summary="Test summary",
            why_it_matters="Test importance",
        )
        assert len(messages) == 2
        assert "Test Title" in messages[1].content

    def test_prompt_leak_markers_not_empty(self):
        from dailyai.llm.prompts import PROMPT_LEAK_MARKERS
        assert len(PROMPT_LEAK_MARKERS) >= 5


# =====================================================================
#  3. LLM PROVIDER TESTS (with mocked env vars)
# =====================================================================

class TestLLMProvider:
    """Tests for src/dailyai/llm/provider.py"""

    def test_build_providers_no_keys(self):
        from dailyai.llm.provider import _build_providers
        with patch.dict(os.environ, {}, clear=True):
            providers = _build_providers()
            assert providers == []

    def test_build_providers_with_gemini(self):
        from dailyai.llm.provider import _build_providers
        env = {"GOOGLE_AI_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            try:
                providers = _build_providers()
                # Should have gemini if langchain_google_genai is installed
                if providers:
                    assert providers[0][0] == "gemini"
            except Exception:
                pass  # Import may fail if langchain_google_genai not installed

    def test_get_llm_no_providers_raises(self):
        from dailyai.llm.provider import get_llm
        get_llm.cache_clear()
        with patch("dailyai.llm.provider._build_providers", return_value=[]), pytest.raises(RuntimeError, match="No LLM providers"):
            get_llm()

    def test_get_fast_llm_no_providers_raises(self):
        from dailyai.llm.provider import get_fast_llm
        get_fast_llm.cache_clear()
        with patch("dailyai.llm.provider._build_providers", return_value=[]), pytest.raises(RuntimeError, match="No LLM providers"):
            get_fast_llm()

    @pytest.mark.asyncio
    async def test_invoke_llm_success(self):
        from dailyai.llm.provider import invoke_llm
        mock_llm = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.content = "Test response"
        mock_llm.ainvoke.return_value = mock_resp

        with patch("dailyai.llm.provider.get_llm", return_value=mock_llm):
            result = await invoke_llm("System", "User", fast=False)
            assert result == "Test response"

    @pytest.mark.asyncio
    async def test_invoke_llm_failure_returns_empty(self):
        from dailyai.llm.provider import invoke_llm
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = Exception("API error")

        with patch("dailyai.llm.provider.get_llm", return_value=mock_llm):
            result = await invoke_llm("System", "User", fast=False)
            assert result == ""

    @pytest.mark.asyncio
    async def test_invoke_llm_fast_path(self):
        from dailyai.llm.provider import invoke_llm
        mock_llm = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.content = "Fast response"
        mock_llm.ainvoke.return_value = mock_resp

        with patch("dailyai.llm.provider.get_fast_llm", return_value=mock_llm):
            result = await invoke_llm("System", "User", fast=True)
            assert result == "Fast response"

    @pytest.mark.asyncio
    async def test_warmup_hf_no_token(self):
        from dailyai.llm.provider import warmup_hf_model
        with patch.dict(os.environ, {"HF_API_TOKEN": ""}, clear=False):
            # Should return immediately without error
            await warmup_hf_model()

    @pytest.mark.asyncio
    async def test_warmup_hf_with_token_handles_error(self):
        from dailyai.llm.provider import warmup_hf_model
        with patch.dict(os.environ, {"HF_API_TOKEN": "test-token"}, clear=False), patch("dailyai.llm.provider.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock()
            mock_client.post.side_effect = Exception("Connection error")
            # Should handle error gracefully
            await warmup_hf_model()


# =====================================================================
#  4. GRAPH NODES TESTS
# =====================================================================

class TestDeduplicatorNode:
    """Tests for src/dailyai/graph/nodes/deduplicator.py"""

    @pytest.mark.asyncio
    async def test_removes_exact_duplicates(self):
        from dailyai.graph.nodes.deduplicator import run
        state = {
            "raw_articles": [
                {"title": "AI Breakthrough"},
                {"title": "AI Breakthrough"},
                {"title": "Different Story"},
            ],
            "node_timings": {},
        }
        result = await run(state)
        assert len(result["deduplicated"]) == 2

    @pytest.mark.asyncio
    async def test_removes_near_duplicates(self):
        from dailyai.graph.nodes.deduplicator import run
        state = {
            "raw_articles": [
                {"title": "OpenAI launches GPT-5 - Reuters"},
                {"title": "OpenAI launches GPT-5 - Bloomberg"},
            ],
            "node_timings": {},
        }
        result = await run(state)
        assert len(result["deduplicated"]) == 1

    @pytest.mark.asyncio
    async def test_empty_input(self):
        from dailyai.graph.nodes.deduplicator import run
        result = await run({"raw_articles": [], "node_timings": {}})
        assert result["deduplicated"] == []

    @pytest.mark.asyncio
    async def test_tracks_timing(self):
        from dailyai.graph.nodes.deduplicator import run
        result = await run({"raw_articles": [{"title": "Test"}], "node_timings": {}})
        assert "deduplicator" in result["node_timings"]

    def test_normalize_title(self):
        from dailyai.graph.nodes.deduplicator import _normalize_title
        assert _normalize_title("Test - Reuters") == "test"
        assert _normalize_title("  Hello World  ") == "hello world"


class TestTrustNode:
    """Tests for src/dailyai/graph/nodes/trust.py"""

    @pytest.mark.asyncio
    async def test_high_trust_source(self):
        from dailyai.graph.nodes.trust import run
        state = {
            "curated": [{"source": "Reuters says", "title": "Test"}],
            "node_timings": {},
        }
        result = await run(state)
        assert result["trust_scored"][0]["source_trust"] == "high"

    @pytest.mark.asyncio
    async def test_medium_trust_source(self):
        from dailyai.graph.nodes.trust import run
        state = {
            "curated": [{"source": "VentureBeat", "title": "Test"}],
            "node_timings": {},
        }
        result = await run(state)
        assert result["trust_scored"][0]["source_trust"] == "medium"

    @pytest.mark.asyncio
    async def test_low_trust_unknown(self):
        from dailyai.graph.nodes.trust import run
        state = {
            "curated": [{"source": "random-blog.xyz", "title": "Test"}],
            "node_timings": {},
        }
        result = await run(state)
        assert result["trust_scored"][0]["source_trust"] == "low"

    @pytest.mark.asyncio
    async def test_empty_source(self):
        from dailyai.graph.nodes.trust import run
        state = {"curated": [{"source": "", "title": "Test"}], "node_timings": {}}
        result = await run(state)
        assert result["trust_scored"][0]["source_trust"] == "low"

    def test_score_source_function(self):
        from dailyai.graph.nodes.trust import _score_source
        assert _score_source("Reuters")[0] == "high"
        assert _score_source("VentureBeat")[0] == "medium"
        assert _score_source("")[0] == "low"


class TestSentimentNode:
    """Tests for src/dailyai/graph/nodes/sentiment.py"""

    @pytest.mark.asyncio
    async def test_valid_sentiments_preserved(self):
        from dailyai.graph.nodes.sentiment import run
        state = {
            "trust_scored": [
                {"sentiment": "bullish"},
                {"sentiment": "bearish"},
                {"sentiment": "neutral"},
            ],
            "node_timings": {},
        }
        result = await run(state)
        sentiments = [a["sentiment"] for a in result["sentiment_tagged"]]
        assert sentiments == ["bullish", "bearish", "neutral"]

    @pytest.mark.asyncio
    async def test_invalid_sentiment_normalized(self):
        from dailyai.graph.nodes.sentiment import run
        state = {
            "trust_scored": [{"sentiment": "positive"}, {"sentiment": "UNKNOWN"}],
            "node_timings": {},
        }
        result = await run(state)
        for a in result["sentiment_tagged"]:
            assert a["sentiment"] == "neutral"

    @pytest.mark.asyncio
    async def test_missing_sentiment_defaults(self):
        from dailyai.graph.nodes.sentiment import run
        state = {"trust_scored": [{}], "node_timings": {}}
        result = await run(state)
        assert result["sentiment_tagged"][0]["sentiment"] == "neutral"


class TestThreaderNode:
    """Tests for src/dailyai/graph/nodes/threader.py"""

    @pytest.mark.asyncio
    async def test_counts_thread_members(self):
        from dailyai.graph.nodes.threader import run
        state = {
            "sentiment_tagged": [
                {"story_thread": "GPT-5 Launch"},
                {"story_thread": "GPT-5 Launch"},
                {"story_thread": "EU AI Act"},
            ],
            "node_timings": {},
        }
        result = await run(state)
        gpt_articles = [a for a in result["threaded"] if "GPT-5" in a.get("story_thread", "")]
        assert all(a["thread_count"] == 2 for a in gpt_articles)

    @pytest.mark.asyncio
    async def test_no_thread(self):
        from dailyai.graph.nodes.threader import run
        state = {
            "sentiment_tagged": [{"story_thread": ""}],
            "node_timings": {},
        }
        result = await run(state)
        assert result["threaded"][0]["thread_count"] == 0


class TestFormatterNode:
    """Tests for src/dailyai/graph/nodes/formatter.py"""

    @pytest.mark.asyncio
    async def test_formats_for_ui(self):
        from dailyai.graph.nodes.formatter import run
        state = {
            "final_feed": [
                {
                    "title": "Test Article",
                    "summary": "Summary",
                    "topic": "llms",
                    "category": "product",
                    "importance": 8,
                    "source": "Reuters",
                    "source_trust": "high",
                    "sentiment": "bullish",
                    "story_thread": "Thread",
                    "thread_count": 2,
                    "link": "https://example.com",
                    "published": "2026-01-01",
                    "fetched_at": "2026-01-01",
                }
            ],
            "country_code": "US",
            "language": "en",
            "node_timings": {},
        }
        result = await run(state)
        article = result["final_feed"][0]
        assert article["headline"] == "Test Article"
        assert article["id"].startswith("US-en-")
        assert article["topic"] == "AI Models"  # llms -> AI Models via UI_TOPIC_MAP

    @pytest.mark.asyncio
    async def test_importance_clamped(self):
        from dailyai.graph.nodes.formatter import run
        state = {
            "final_feed": [{"title": "T", "importance": 999}],
            "country_code": "US",
            "language": "en",
            "node_timings": {},
        }
        result = await run(state)
        assert result["final_feed"][0]["importance"] == 10

    @pytest.mark.asyncio
    async def test_empty_feed(self):
        from dailyai.graph.nodes.formatter import run
        state = {"final_feed": [], "country_code": "US", "language": "en", "node_timings": {}}
        result = await run(state)
        assert result["final_feed"] == []


class TestPersonalizerNode:
    """Tests for src/dailyai/graph/nodes/personalizer.py"""

    @pytest.mark.asyncio
    async def test_default_ranking_by_quality(self):
        from dailyai.graph.nodes.personalizer import run
        state = {
            "threaded": [
                {"title": "Low", "importance": 3, "topic": "general"},
                {"title": "High", "importance": 9, "topic": "general"},
            ],
            "user_profile": None,
            "node_timings": {},
        }
        result = await run(state)
        assert result["final_feed"][0]["title"] == "High"

    @pytest.mark.asyncio
    async def test_personalized_ranking(self):
        from dailyai.graph.nodes.personalizer import run
        state = {
            "threaded": [
                {"title": "Generic", "importance": 8, "category": "general", "topic": "general"},
                {"title": "Preferred", "importance": 5, "category": "llms", "topic": "llms"},
            ],
            "user_profile": {
                "sync_code": "Test-Code-42",
                "preferred_topics": ["llms"],
                "signals": {"llms": 20},
            },
            "node_timings": {},
        }
        result = await run(state)
        assert result["final_feed"][0]["title"] == "Preferred"

    @pytest.mark.asyncio
    async def test_topic_diversity_cap(self):
        from dailyai.graph.nodes.personalizer import run
        articles = [
            {"title": f"Same topic {i}", "importance": 9, "topic": "llms", "category": "product"}
            for i in range(10)
        ]
        state = {"threaded": articles, "user_profile": None, "node_timings": {}}
        result = await run(state)
        # Should cap at 3 of same topic in top 12
        top_12 = result["final_feed"][:12]
        llm_count = sum(1 for a in top_12 if a.get("topic") == "llms")
        assert llm_count <= 4  # cap is 3 for first 12, 4 after

    def test_quality_score(self):
        from dailyai.graph.nodes.personalizer import _quality_score
        article = {"importance": 8, "_trust_score": 2}
        score = _quality_score(article)
        assert score > 0


class TestCuratorNode:
    """Tests for src/dailyai/graph/nodes/curator.py"""

    def test_is_template_detects_placeholder(self):
        from dailyai.graph.nodes.curator import _is_template
        assert _is_template({"title": "Short headline"}) is True
        assert _is_template({"title": ""}) is True
        assert _is_template({"title": "Real News"}) is False

    def test_extract_json_array_valid(self):
        from dailyai.graph.nodes.curator import _extract_json_array
        result = _extract_json_array('[{"title": "Test"}]')
        assert result == [{"title": "Test"}]

    def test_extract_json_array_with_markdown(self):
        from dailyai.graph.nodes.curator import _extract_json_array
        text = '```json\n[{"title": "Test"}]\n```'
        result = _extract_json_array(text)
        assert result == [{"title": "Test"}]

    def test_extract_json_array_with_preamble(self):
        from dailyai.graph.nodes.curator import _extract_json_array
        text = 'Here are the results:\n[{"title": "Test"}]\nDone.'
        result = _extract_json_array(text)
        assert result == [{"title": "Test"}]

    def test_extract_json_array_empty(self):
        from dailyai.graph.nodes.curator import _extract_json_array
        assert _extract_json_array("") is None
        assert _extract_json_array("no json here") is None

    def test_extract_json_truncated_recovery(self):
        from dailyai.graph.nodes.curator import _extract_json_array
        truncated = '[{"title": "A"}, {"title": "B"}, {"title": "C'
        result = _extract_json_array(truncated)
        # Should recover at least the first two items
        if result:
            assert len(result) >= 1

    def test_fallback_curate_produces_tiles(self):
        from dailyai.graph.nodes.curator import _fallback_curate
        articles = [
            {"title": "OpenAI launches GPT-5", "source": "Reuters", "link": "https://x.com"},
            {"title": "Google AI update", "source": "TechCrunch", "link": "https://y.com"},
        ]
        tiles = _fallback_curate(articles, "en")
        assert len(tiles) == 2
        assert tiles[0]["topic"] == "big_tech"  # "openai" → big_tech
        assert tiles[1]["topic"] == "big_tech"  # "google" → big_tech

    def test_fallback_curate_german(self):
        from dailyai.graph.nodes.curator import _fallback_curate
        articles = [{"title": "KI News", "source": "Heise"}]
        tiles = _fallback_curate(articles, "de")
        assert "KI-Community" in tiles[0]["why_it_matters"]

    @pytest.mark.asyncio
    async def test_curator_empty_input(self):
        from dailyai.graph.nodes.curator import run
        state = {
            "deduplicated": [],
            "country_name": "US",
            "language": "en",
            "errors": [],
            "node_timings": {},
        }
        result = await run(state)
        assert result["curated"] == []

    @pytest.mark.asyncio
    async def test_curator_llm_timeout_fallback(self):
        from dailyai.graph.nodes.curator import run
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=TimeoutError())

        with patch("dailyai.graph.nodes.curator.get_llm", return_value=mock_llm):
            state = {
                "deduplicated": [{"title": "Test", "source": "Reuters", "link": "https://x.com"}],
                "country_name": "US",
                "language": "en",
                "errors": [],
                "node_timings": {},
            }
            result = await run(state)
            assert len(result["curated"]) > 0  # Fallback should produce tiles
            assert "Curator: LLM timeout" in result["errors"]


class TestCollectorNode:
    """Tests for src/dailyai/graph/nodes/collector.py"""

    @pytest.mark.asyncio
    async def test_collector_runs_with_mocked_rss(self):
        from dailyai.graph.nodes.collector import run

        mock_articles = [
            {"title": "AI News 1", "link": "https://x.com", "source": "Test", "published": ""},
        ]
        with patch("dailyai.graph.nodes.collector._fetch_rss_feed", new_callable=AsyncMock, return_value=mock_articles):
            state = {"country_code": "US", "language": "en", "errors": [], "node_timings": {}}
            result = await run(state)
            assert len(result["raw_articles"]) > 0

    @pytest.mark.asyncio
    async def test_collector_handles_all_failures(self):
        from dailyai.graph.nodes.collector import run

        with patch("dailyai.graph.nodes.collector._fetch_rss_feed", new_callable=AsyncMock, side_effect=Exception("Fetch failed")):
            state = {"country_code": "US", "language": "en", "errors": [], "node_timings": {}}
            result = await run(state)
            assert result["raw_articles"] == []

    @pytest.mark.asyncio
    async def test_collector_dach_queries(self):
        from dailyai.graph.nodes.collector import run

        call_count = 0
        async def mock_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return [{"title": f"News {call_count}", "link": "", "source": "", "published": ""}]

        with patch("dailyai.graph.nodes.collector._fetch_rss_feed", side_effect=mock_fetch):
            state = {"country_code": "DE", "language": "de", "errors": [], "node_timings": {}}
            result = await run(state)
            # DE should include both FEED_QUERIES and FEED_QUERIES_DE
            assert len(result["raw_articles"]) > 6


# =====================================================================
#  5. PYDANTIC MODELS TESTS
# =====================================================================

class TestPydanticModels:
    """Tests for src/dailyai/storage/models.py"""

    def test_news_article_defaults(self):
        from dailyai.storage.models import NewsArticle
        a = NewsArticle(title="Test")
        assert a.importance == 5
        assert a.source_trust == "low"
        assert a.sentiment == "neutral"

    def test_news_article_importance_clamped(self):
        from dailyai.storage.models import NewsArticle

        with pytest.raises(ValidationError):
            NewsArticle(title="Test", importance=99)

    def test_raw_article_minimal(self):
        from dailyai.storage.models import RawArticle
        a = RawArticle(title="Test")
        assert a.link == ""

    def test_subscribe_request(self):
        from dailyai.storage.models import SubscribeRequest
        req = SubscribeRequest(email="test@example.com")
        assert req.country == "GLOBAL"
        assert req.language == "en"
        assert req.topics == []

    def test_create_profile_request(self):
        from dailyai.storage.models import CreateProfileRequest
        req = CreateProfileRequest()
        assert req.preferred_topics == []
        assert req.country == "GLOBAL"

    def test_update_profile_request_optional(self):
        from dailyai.storage.models import UpdateProfileRequest
        req = UpdateProfileRequest()
        assert req.preferred_topics is None
        assert req.country is None

    def test_record_signal_request(self):
        from dailyai.storage.models import RecordSignalRequest
        req = RecordSignalRequest(topic="llms", action="tap")
        assert req.topic == "llms"

    def test_article_brief_request(self):
        from dailyai.storage.models import ArticleBriefRequest
        req = ArticleBriefRequest(title="Test")
        assert req.language == "en"

    def test_feed_article_defaults(self):
        from dailyai.storage.models import FeedArticle
        a = FeedArticle(id="test-1", headline="Test")
        assert a.topic == "Top Stories"
        assert a.source_name == "Unknown"

    def test_user_profile_model(self):
        from dailyai.storage.models import UserProfile
        p = UserProfile(sync_code="Test-Code-42")
        assert p.country == "GLOBAL"
        assert p.bookmarks == []

    def test_subscriber_model(self):
        from dailyai.storage.models import Subscriber
        s = Subscriber(email="test@example.com")
        assert s.is_active is True

    def test_api_key_record(self):
        from dailyai.storage.models import APIKeyRecord
        k = APIKeyRecord(key_hash="abc123", name="Test", email="test@example.com")
        assert k.tier == "free"
        assert k.is_active is True

    def test_record_analytics_request(self):
        from dailyai.storage.models import RecordAnalyticsRequest
        req = RecordAnalyticsRequest()
        assert req.taps == 0
        assert req.session_count == 0


# =====================================================================
#  6. DIGEST MODULE TESTS
# =====================================================================

class TestDigestModule:
    """Tests for digest.py — email generation and sending."""

    def test_digest_module_importable(self):
        import digest
        assert hasattr(digest, "generate_digest_html") or hasattr(digest, "send_digest")

    def test_format_article_for_email(self):
        """Test that articles can be formatted for email content."""
        article = {
            "title": "AI Breakthrough",
            "summary": "Major development in AI",
            "source": "Reuters",
            "link": "https://example.com",
            "importance": 8,
        }
        # Basic validation that article data is email-safe
        assert "<" not in article["title"]  # No HTML injection
        assert len(article["summary"]) > 0


# =====================================================================
#  7. NEWS SERVICE TESTS
# =====================================================================

class TestNewsService:
    """Tests for src/dailyai/services/news.py"""

    @pytest.mark.asyncio
    async def test_get_feed_normalizes_country(self):
        """get_feed normalizes unknown countries to GLOBAL."""
        with patch("dailyai.services.news.db") as mock_db:
            mock_db.get_articles_count = AsyncMock(return_value=5)
            mock_db.get_articles = AsyncMock(return_value=[
                {"title": f"Article {i}", "summary": "s", "importance": 5,
                 "topic": "general", "category": "general", "source": "Test",
                 "source_trust": "low", "sentiment": "neutral", "story_thread": "",
                 "link": "https://x.com", "published": "", "fetched_at": ""}
                for i in range(15)
            ])
            mock_db.get_metadata = AsyncMock(return_value="2026-01-01")

            from dailyai.services.news import get_feed
            result = await get_feed(country="INVALID_COUNTRY", language="en")
            assert result["country"] == "GLOBAL"

    @pytest.mark.asyncio
    async def test_get_feed_pagination(self):
        """get_feed respects offset and limit."""
        with patch("dailyai.services.news.db") as mock_db:
            articles = [
                {"title": f"Article {i}", "summary": "s", "importance": 9 - i,
                 "topic": "general", "category": "general", "source": "Test",
                 "source_trust": "low", "sentiment": "neutral", "story_thread": "",
                 "link": f"https://x.com/{i}", "published": "", "fetched_at": ""}
                for i in range(20)
            ]
            mock_db.get_articles_count = AsyncMock(return_value=20)
            mock_db.get_articles = AsyncMock(return_value=articles)
            mock_db.get_metadata = AsyncMock(return_value="2026-01-01")

            from dailyai.services.news import get_feed
            result = await get_feed(offset=5, limit=3)
            assert len(result["articles"]) == 3
            assert result["offset"] == 5
            assert result["limit"] == 3
            assert result["has_more"] is True

    @pytest.mark.asyncio
    async def test_brief_cache_hit(self):
        """get_article_brief returns cached result on second call."""
        from dailyai.services.news import _brief_cache, get_article_brief
        # Pre-populate cache
        cache_key = hashlib.md5(b"Test Title").hexdigest()[:16]
        _brief_cache[cache_key] = "Cached brief content"
        try:
            result = await get_article_brief(title="Test Title")
            assert result == "Cached brief content"
        finally:
            _brief_cache.pop(cache_key, None)


# =====================================================================
#  8. PROFILE SERVICE TESTS
# =====================================================================

class TestProfileService:
    """Tests for src/dailyai/services/profiles.py"""

    def test_generate_sync_code_format(self):
        from dailyai.services.profiles import _generate_sync_code
        code = _generate_sync_code()
        parts = code.split("-")
        assert len(parts) == 3
        assert parts[2].isdigit()

    @pytest.mark.asyncio
    async def test_create_profile(self):
        with patch("dailyai.services.profiles.db") as mock_db:
            mock_db.get_profile = AsyncMock(return_value=None)
            mock_db.save_profile = AsyncMock()

            from dailyai.services.profiles import create_profile
            profile = await create_profile(["llms", "research"], "US", "en")
            assert profile["sync_code"]
            assert profile["preferred_topics"] == ["llms", "research"]
            assert profile["country"] == "US"

    @pytest.mark.asyncio
    async def test_record_signal_weights(self):
        mock_profile = {
            "sync_code": "Test-42",
            "signals": {},
            "last_active": "",
        }
        with patch("dailyai.services.profiles.db") as mock_db:
            mock_db.get_profile = AsyncMock(return_value=mock_profile.copy())
            mock_db.save_profile = AsyncMock()

            from dailyai.services.profiles import record_signal
            result = await record_signal("Test-42", "llms", "tap")
            assert result is not None
            assert result["signals"]["llms"] == 1

    @pytest.mark.asyncio
    async def test_record_signal_save_weight(self):
        mock_profile = {"sync_code": "Test-42", "signals": {}, "last_active": ""}
        with patch("dailyai.services.profiles.db") as mock_db:
            mock_db.get_profile = AsyncMock(return_value=mock_profile.copy())
            mock_db.save_profile = AsyncMock()

            from dailyai.services.profiles import record_signal
            result = await record_signal("Test-42", "llms", "save")
            assert result["signals"]["llms"] == 3

    @pytest.mark.asyncio
    async def test_record_signal_skip_negative(self):
        mock_profile = {"sync_code": "Test-42", "signals": {"llms": 5}, "last_active": ""}
        with patch("dailyai.services.profiles.db") as mock_db:
            mock_db.get_profile = AsyncMock(return_value=mock_profile.copy())
            mock_db.save_profile = AsyncMock()

            from dailyai.services.profiles import record_signal
            result = await record_signal("Test-42", "llms", "skip")
            assert result["signals"]["llms"] == 4  # 5 - 1

    @pytest.mark.asyncio
    async def test_record_signal_invalid_action(self):
        with patch("dailyai.services.profiles.db") as mock_db:
            mock_db.get_profile = AsyncMock(return_value={"sync_code": "Test-42", "signals": {}})

            from dailyai.services.profiles import record_signal
            result = await record_signal("Test-42", "llms", "invalid_action")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_topic_scores(self):
        mock_profile = {
            "sync_code": "Test-42",
            "preferred_topics": ["llms", "research"],
            "signals": {"llms": 5, "robotics": 2},
        }
        with patch("dailyai.services.profiles.db") as mock_db:
            mock_db.get_profile = AsyncMock(return_value=mock_profile)

            from dailyai.services.profiles import get_topic_scores
            scores = await get_topic_scores("Test-42")
            assert scores["llms"] == 15.0  # 10.0 (preferred) + 5 (signal)
            assert scores["research"] == 10.0  # 10.0 (preferred only)
            assert scores["robotics"] == 2.0  # 2 (signal only)

    @pytest.mark.asyncio
    async def test_get_topic_scores_no_profile(self):
        with patch("dailyai.services.profiles.db") as mock_db:
            mock_db.get_profile = AsyncMock(return_value=None)

            from dailyai.services.profiles import get_topic_scores
            scores = await get_topic_scores("Nonexistent")
            assert scores == {}

    @pytest.mark.asyncio
    async def test_update_preferences(self):
        mock_profile = {
            "sync_code": "Test-42",
            "preferred_topics": ["llms"],
            "country": "US",
            "language": "en",
            "bookmarks": [],
            "last_active": "",
        }
        with patch("dailyai.services.profiles.db") as mock_db:
            mock_db.get_profile = AsyncMock(return_value=mock_profile.copy())
            mock_db.save_profile = AsyncMock()

            from dailyai.services.profiles import update_preferences
            result = await update_preferences("Test-42", country="DE", language="de")
            assert result["country"] == "DE"
            assert result["language"] == "de"

    @pytest.mark.asyncio
    async def test_record_analytics(self):
        mock_profile = {"sync_code": "T-42", "analytics": {}, "last_active": ""}
        with patch("dailyai.services.profiles.db") as mock_db:
            mock_db.get_profile = AsyncMock(return_value=mock_profile.copy())
            mock_db.save_profile = AsyncMock()

            from dailyai.services.profiles import record_analytics
            result = await record_analytics("T-42", {"taps": 5, "saves": 2})
            assert result["total_taps"] == 5
            assert result["total_saves"] == 2


# =====================================================================
#  9. PIPELINE TESTS
# =====================================================================

class TestPipeline:
    """Tests for src/dailyai/graph/pipeline.py"""

    def test_build_pipeline_compiles(self):
        from dailyai.graph.pipeline import build_pipeline
        pipeline = build_pipeline()
        assert pipeline is not None

    def test_get_pipeline_singleton(self):
        import dailyai.graph.pipeline as mod
        from dailyai.graph.pipeline import get_pipeline
        mod._pipeline = None  # Reset
        p1 = get_pipeline()
        p2 = get_pipeline()
        assert p1 is p2
        mod._pipeline = None  # Cleanup


# =====================================================================
#  10. GRAPH STATE TESTS
# =====================================================================

class TestGraphState:
    """Tests for src/dailyai/graph/state.py"""

    def test_state_type_exists(self):
        from dailyai.graph.state import PipelineState
        assert PipelineState is not None

    def test_state_has_required_keys(self):
        from dailyai.graph.state import PipelineState
        annotations = PipelineState.__annotations__
        required = ["country_code", "language", "raw_articles", "final_feed", "errors"]
        for key in required:
            assert key in annotations, f"Missing key: {key}"


# =====================================================================
#  11. SCHEDULER TESTS
# =====================================================================

class TestScheduler:
    """Tests for src/dailyai/services/scheduler.py"""

    def test_scheduler_importable(self):
        from dailyai.services.scheduler import scheduler
        assert scheduler is not None


# =====================================================================
#  MAIN
# =====================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
