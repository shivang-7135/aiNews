"""Function-level health checks.

This file is intentionally focused on pure/helper functions so each test result
maps to a single function behavior. Run this when you want a quick function
status report without running the full suite.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

import digest
import pytest

from dailyai.config import normalize_language, store_key
from dailyai.graph.nodes.deduplicator import _normalize_title
from dailyai.graph.nodes.personalizer import _quality_score
from dailyai.graph.nodes.trust import _score_source
from dailyai.llm.prompts import sanitize_llm_response
from dailyai.services.profiles import _generate_sync_code
from dailyai.services.news import get_prefetch_pairs
from dailyai.ui.components.theme import get_category_image


@dataclass
class FunctionCheck:
    name: str
    call: Callable[[], Any]
    validate: Callable[[Any], bool]
    expected: str


def _is_sync_code(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]+-[A-Za-z]+-[0-9]{2}", value))


FUNCTION_CHECKS: list[FunctionCheck] = [
    FunctionCheck(
        name="config.normalize_language trims + lowercases",
        call=lambda: normalize_language(" EN "),
        validate=lambda result: result == "en",
        expected="'en'",
    ),
    FunctionCheck(
        name="config.normalize_language falls back to en",
        call=lambda: normalize_language("unknown-language"),
        validate=lambda result: result == "en",
        expected="'en'",
    ),
    FunctionCheck(
        name="config.store_key normalizes country + language",
        call=lambda: store_key("us", "DE"),
        validate=lambda result: result == "US::de",
        expected="'US::de'",
    ),
    FunctionCheck(
        name="prompts.sanitize_llm_response blocks prompt leakage",
        call=lambda: sanitize_llm_response("SYSTEM: x RULES: y OUTPUT FORMAT z"),
        validate=lambda result: result == "",
        expected="empty string",
    ),
    FunctionCheck(
        name="prompts.sanitize_llm_response keeps clean content",
        call=lambda: sanitize_llm_response("Clean summary about an AI launch."),
        validate=lambda result: result == "Clean summary about an AI launch.",
        expected="same clean sentence",
    ),
    FunctionCheck(
        name="deduplicator._normalize_title strips source suffix",
        call=lambda: _normalize_title("OpenAI launches GPT-5 - Reuters"),
        validate=lambda result: result == "openai launches gpt5",
        expected="'openai launches gpt5'",
    ),
    FunctionCheck(
        name="trust._score_source marks Reuters as high",
        call=lambda: _score_source("Reuters"),
        validate=lambda result: result == ("high", 2),
        expected="('high', 2)",
    ),
    FunctionCheck(
        name="trust._score_source marks generic journal as medium",
        call=lambda: _score_source("AI Journal"),
        validate=lambda result: result == ("medium", 1),
        expected="('medium', 1)",
    ),
    FunctionCheck(
        name="personalizer._quality_score uses base + trust",
        call=lambda: _quality_score({"importance": 8, "_trust_score": 2, "published": ""}),
        validate=lambda result: result == 86.0,
        expected="86.0",
    ),
    FunctionCheck(
        name="profiles._generate_sync_code returns Adjective-Noun-Number",
        call=_generate_sync_code,
        validate=lambda result: _is_sync_code(result),
        expected="pattern '<Word>-<Word>-<2 digits>'",
    ),
    FunctionCheck(
        name="digest.generate_digest_html renders key fields",
        call=lambda: digest.generate_digest_html(
            [
                {
                    "category": "general",
                    "importance": 8,
                    "why_it_matters": "Major AI impact",
                    "link": "https://example.com",
                    "title": "Test Headline",
                    "summary": "Test Summary",
                    "source": "Reuters",
                    "published": "2026-04-07",
                }
            ],
            "April 07, 2026",
        ),
        validate=lambda result: (
            isinstance(result, str)
            and "DailyAI" in result
            and "Test Headline" in result
            and "April 07, 2026" in result
        ),
        expected="HTML containing DailyAI, headline, and date",
    ),
    FunctionCheck(
        name="news.get_prefetch_pairs includes global and DE locale",
        call=get_prefetch_pairs,
        validate=lambda result: ("GLOBAL", "en") in result and ("DE", "de") in result,
        expected="pairs containing ('GLOBAL','en') and ('DE','de')",
    ),
    FunctionCheck(
        name="theme.get_category_image returns deterministic category path",
        call=lambda: get_category_image("research", "GLOBAL-en-abc123"),
        validate=lambda result: isinstance(result, str) and len(result) > 0,
        expected="Valid image URL or path string"
    ),
]


@pytest.mark.parametrize("check", FUNCTION_CHECKS, ids=lambda c: c.name)
def test_function_health_checks(check: FunctionCheck) -> None:
    """Run one health check per function for clear pass/fail reporting."""
    result = check.call()
    assert check.validate(result), (
        f"Function check failed: {check.name}\n"
        f"Expected: {check.expected}\n"
        f"Actual: {result!r}"
    )
