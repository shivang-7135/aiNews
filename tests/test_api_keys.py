"""
DailyAI API Key Tests — Validate key generation, rate limiting, and field filtering.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from services.api_keys import (
    TIERS,
    _hash_key,
    check_rate_limit,
    create_api_key,
    filter_fields_for_tier,
    validate_api_key,
)


@pytest.fixture(autouse=True)
def clean_api_keys(tmp_path, monkeypatch):
    """Use a temp file for API keys during tests."""
    import services.api_keys as mod

    test_file = tmp_path / "api_keys.json"
    monkeypatch.setattr(mod, "API_KEYS_FILE", test_file)
    # Clear rate buckets
    mod._rate_buckets.clear()
    yield
    if test_file.exists():
        test_file.unlink()


class TestAPIKeyCreation:
    def test_create_free_key(self):
        result = create_api_key("Test App", "test@example.com", "free")
        assert result["api_key"].startswith("dai_")
        assert result["tier"] == "free"
        assert result["daily_limit"] == 100

    def test_create_key_with_invalid_tier_defaults_to_free(self):
        result = create_api_key("Test", "test@x.com", "premium_ultra")
        assert result["tier"] == "free"

    def test_key_prefix_is_masked(self):
        result = create_api_key("Test", "test@x.com")
        assert result["key_prefix"].endswith("...")
        assert len(result["key_prefix"]) == 15  # 12 chars + "..."


class TestAPIKeyValidation:
    def test_valid_key(self):
        result = create_api_key("Test", "test@x.com")
        record = validate_api_key(result["api_key"])
        assert record is not None
        assert record["tier"] == "free"

    def test_invalid_key(self):
        assert validate_api_key("dai_nonexistent_key") is None

    def test_non_dai_prefix_rejected(self):
        assert validate_api_key("sk_some_other_key") is None

    def test_empty_key_rejected(self):
        assert validate_api_key("") is None
        assert validate_api_key(None) is None


class TestRateLimiting:
    def test_within_limit(self):
        key_hash = _hash_key("test_key")
        allowed, remaining, limit = check_rate_limit(key_hash, "free")
        assert allowed is True
        assert remaining == 99
        assert limit == 100

    def test_exceeds_limit(self):
        key_hash = _hash_key("test_key_2")
        # Exhaust the limit
        for _ in range(100):
            check_rate_limit(key_hash, "free")
        allowed, remaining, limit = check_rate_limit(key_hash, "free")
        assert allowed is False
        assert remaining == 0

    def test_pro_tier_higher_limit(self):
        key_hash = _hash_key("pro_key")
        allowed, remaining, limit = check_rate_limit(key_hash, "pro")
        assert limit == 10_000
        assert allowed is True


class TestFieldFiltering:
    def test_free_tier_basic_fields(self):
        article = {
            "id": "1",
            "headline": "Test",
            "summary": "Test",
            "source_name": "X",
            "category": "general",
            "topic": "general",
            "importance": 5,
            "article_url": "http://x",
            "published_at": "2026-01-01",
            "why_it_matters": "Secret pro field",
            "source_trust": "high",
            "sentiment": "bullish",
            "story_thread": "Thread",
            "thread_count": 5,
        }
        filtered = filter_fields_for_tier(article, "free")
        assert "headline" in filtered
        assert "summary" in filtered
        assert "why_it_matters" not in filtered
        assert "source_trust" not in filtered
        assert "sentiment" not in filtered

    def test_pro_tier_full_fields(self):
        article = {
            "id": "1",
            "headline": "Test",
            "why_it_matters": "Important",
            "source_trust": "high",
            "sentiment": "bullish",
            "story_thread": "Thread",
            "thread_count": 3,
        }
        filtered = filter_fields_for_tier(article, "pro")
        assert "why_it_matters" in filtered
        assert "source_trust" in filtered
        assert "sentiment" in filtered
        assert "story_thread" in filtered
        assert "thread_count" in filtered

    def test_enterprise_same_as_pro(self):
        article = {"source_trust": "high", "sentiment": "bullish"}
        filtered = filter_fields_for_tier(article, "enterprise")
        assert "source_trust" in filtered
        assert "sentiment" in filtered


class TestTierConfiguration:
    def test_all_tiers_defined(self):
        assert "free" in TIERS
        assert "pro" in TIERS
        assert "enterprise" in TIERS

    def test_free_cheaper_than_pro(self):
        assert TIERS["free"]["daily_limit"] < TIERS["pro"]["daily_limit"]

    def test_pro_cheaper_than_enterprise(self):
        assert TIERS["pro"]["daily_limit"] < TIERS["enterprise"]["daily_limit"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
