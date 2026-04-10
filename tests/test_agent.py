"""
DailyAI Agent Tests — Negative Testing & Edge Cases

Tests the LLM response parsing, source trust scoring, prompt leakage
sanitization, and fallback mechanisms.
"""

import json
import os
import sys
from datetime import UTC, datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from agent import NewsAgent, _sanitize_llm_response


class TestSanitizeLLMResponse:
    """Test prompt leakage / system prompt echo sanitization on fields."""

    def test_clean_text_passes_through(self):
        assert _sanitize_llm_response("OpenAI launches GPT-5") == "OpenAI launches GPT-5"

    def test_handles_none(self):
        assert _sanitize_llm_response(None) == ""

    def test_handles_empty_string(self):
        assert _sanitize_llm_response("") == ""

    def test_strips_whitespace(self):
        result = _sanitize_llm_response("  OpenAI launches GPT-5  ")
        assert result.strip() == "OpenAI launches GPT-5"

    def test_preserves_unicode(self):
        result = _sanitize_llm_response("Künstliche Intelligenz — Durchbruch!")
        assert "Künstliche" in result


class TestSourceTrustScoring:
    """Test source quality scoring and trust tier classification."""

    def setup_method(self):
        self.agent = NewsAgent()

    def test_high_trust_sources(self):
        assert self.agent._source_quality_score("Reuters") == 2
        assert self.agent._source_quality_score("TechCrunch") == 2
        assert self.agent._source_quality_score("BBC News") == 2

    def test_german_high_trust_sources(self):
        assert self.agent._source_quality_score("Heise Online") == 2
        assert self.agent._source_quality_score("Golem.de") == 2
        assert self.agent._source_quality_score("Handelsblatt") == 2
        assert self.agent._source_quality_score("Der Spiegel") == 2
        assert self.agent._source_quality_score("FAZ") == 2

    def test_medium_trust_sources(self):
        assert self.agent._source_quality_score("VentureBeat") == 1
        assert self.agent._source_quality_score("ZDNet") == 1
        assert self.agent._source_quality_score("Ars Technica") == 1

    def test_unknown_sources(self):
        assert self.agent._source_quality_score("random-blog.xyz") == 0
        assert self.agent._source_quality_score("") == 0

    def test_trust_tier_high(self):
        assert self.agent._source_trust_tier("Reuters") == "high"

    def test_trust_tier_medium(self):
        assert self.agent._source_trust_tier("VentureBeat") == "medium"

    def test_trust_tier_low(self):
        assert self.agent._source_trust_tier("unknown-blog") == "low"

    def test_trust_tier_empty(self):
        assert self.agent._source_trust_tier("") == "low"


class TestLLMResponseParsing:
    """Test the agent's ability to parse malformed LLM responses."""

    def setup_method(self):
        self.agent = NewsAgent()

    def test_valid_json_response(self):
        valid_json = json.dumps([{
            "title": "GPT-5 Released",
            "summary": "OpenAI launches GPT-5",
            "why_it_matters": "Major AI milestone",
            "category": "breakthrough",
            "topic": "llms",
            "importance": 9,
            "sentiment": "bullish",
            "story_thread": "OpenAI GPT-5",
            "source": "TechCrunch",
            "link": "https://example.com",
            "published": "2026-01-01"
        }])
        articles = [{"title": "GPT-5", "source": "TC", "link": "https://tc.com"}]
        result = self.agent._parse_llm_response(valid_json, articles)
        assert len(result) == 1
        assert result[0]["title"] == "GPT-5 Released"
        assert result[0]["source_trust"] == "high"  # TechCrunch is high trust
        assert result[0]["sentiment"] == "bullish"
        assert result[0]["story_thread"] == "OpenAI GPT-5"

    def test_empty_response(self):
        result = self.agent._parse_llm_response("", [])
        assert result == []

    def test_none_response(self):
        result = self.agent._parse_llm_response(None, [])
        assert result == []

    def test_invalid_json_fallback(self):
        result = self.agent._parse_llm_response("this is not json at all!", [])
        assert isinstance(result, list)

    def test_json_with_markdown_wrapper(self):
        wrapped = '```json\n[{"title":"Test","summary":"s","category":"general","topic":"general","importance":5,"source":"x","link":"http://x","published":"2026-01-01"}]\n```'
        articles = [{"title": "Test", "source": "x", "link": "http://x"}]
        result = self.agent._parse_llm_response(wrapped, articles)
        assert len(result) >= 1

    def test_sentiment_validation(self):
        """Invalid sentiment values should default to neutral."""
        valid_json = json.dumps([{
            "title": "Test",
            "summary": "Test",
            "category": "general",
            "topic": "general",
            "importance": 5,
            "sentiment": "super_positive",  # invalid
            "source": "Test",
            "link": "http://test.com",
            "published": "2026-01-01"
        }])
        result = self.agent._parse_llm_response(valid_json, [{"title": "t", "source": "t", "link": "http://t"}])
        if result:
            assert result[0]["sentiment"] == "neutral"


class TestFallbackProcessing:
    """Test the fallback tile generation for when LLM fails."""

    def setup_method(self):
        self.agent = NewsAgent()

    def test_fallback_creates_tiles(self):
        articles = [
            {"title": "Test Article", "source": "Reuters", "link": "http://r.com", "published": "2026-01-01"},
            {"title": "Another Article", "source": "BBC", "link": "http://bbc.com", "published": "2026-01-01"},
        ]
        tiles = self.agent._fallback_process(articles, "en")
        assert len(tiles) == 2
        assert tiles[0]["title"] == "Test Article"

    def test_fallback_includes_trust(self):
        articles = [
            {"title": "Reuters Story", "source": "Reuters", "link": "http://r.com", "published": "2026-01-01"},
        ]
        tiles = self.agent._fallback_process(articles, "en")
        assert tiles[0]["source_trust"] == "high"
        assert tiles[0]["sentiment"] == "neutral"
        assert tiles[0]["story_thread"] == ""

    def test_fallback_empty_input(self):
        tiles = self.agent._fallback_process([], "en")
        assert tiles == []


class TestQualityRerank:
    """Test the quality reranking logic."""

    def setup_method(self):
        self.agent = NewsAgent()

    def test_rerank_prioritizes_importance(self):
        tiles = [
            {"title": "Low", "importance": 3, "source": "a", "published": datetime.now(UTC).isoformat()},
            {"title": "High", "importance": 9, "source": "Reuters", "published": datetime.now(UTC).isoformat()},
        ]
        result = self.agent._quality_rerank(tiles)
        assert result[0]["title"] == "High"

    def test_rerank_handles_empty(self):
        assert self.agent._quality_rerank([]) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
