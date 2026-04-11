"""Supabase storage backend.

This backend is intentionally conservative during rollout:
- Uses Supabase REST (PostgREST) for core read/write operations.
- Falls back to SQLite for resilience when Supabase is unavailable.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import httpx

from dailyai.config import CACHE_MAX_ARTICLES, SUPABASE_KEY, SUPABASE_TIMEOUT_SECONDS, SUPABASE_URL
from dailyai.storage import sqlite

logger = logging.getLogger("dailyai.storage.supabase")

# None: unknown/unprobed, True: available, False: missing (404)
_RSS_FEEDS_TABLE_AVAILABLE: bool | None = None


def _is_http_404(exc: Exception) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404


def _mark_rss_feeds_missing(exc: Exception) -> bool:
    """Mark rss_feeds table as unavailable when Supabase returns 404.

    Returns True when the error indicates missing table and fallback should be used.
    """
    global _RSS_FEEDS_TABLE_AVAILABLE
    if not _is_http_404(exc):
        return False

    if _RSS_FEEDS_TABLE_AVAILABLE is not False:
        logger.warning(
            "Supabase table 'rss_feeds' returned 404. "
            "Using sqlite fallback for RSS feed operations until restart."
        )
    _RSS_FEEDS_TABLE_AVAILABLE = False
    return True


def is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _headers(*, prefer: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


async def _request(
    method: str,
    table: str,
    *,
    params: dict[str, str] | None = None,
    json_body: dict | list | None = None,
    prefer: str | None = None,
    expect_json: bool = True,
):
    base_url = SUPABASE_URL.rstrip("/")
    url = f"{base_url}/rest/v1/{table}"

    headers = _headers(prefer=prefer)
    if json_body is not None:
        headers["Content-Type"] = "application/json"

    timeout = httpx.Timeout(SUPABASE_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            method,
            url,
            params=params,
            json=json_body,
            headers=headers,
        )
        response.raise_for_status()

        if not expect_json:
            return None
        if not response.content:
            return []
        return response.json()


def _coerce_json_field(value, default):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


async def _fallback(func_name: str, *args, **kwargs):
    logger.warning(f"Supabase fallback to sqlite for {func_name}")
    func = getattr(sqlite, func_name)
    return await func(*args, **kwargs)


async def get_db():
    if not is_configured():
        return await _fallback("get_db")
    return {"backend": "supabase", "url": SUPABASE_URL}


async def close_db():
    if not is_configured():
        await _fallback("close_db")


# -- Articles ---------------------------------------------------------


async def save_articles(store_key: str, articles: list[dict]) -> None:
    if not is_configured():
        await _fallback("save_articles", store_key, articles)
        return

    try:
        await _request(
            "DELETE",
            "articles",
            params={"store_key": f"eq.{store_key}"},
            prefer="return=minimal",
            expect_json=False,
        )

        if not articles:
            return

        rows: list[dict] = []
        for article in articles:
            rows.append(
                {
                    "store_key": store_key,
                    "title": article.get("title", ""),
                    "summary": article.get("summary", ""),
                    "why_it_matters": article.get("why_it_matters", ""),
                    "category": article.get("category", "general"),
                    "topic": article.get("topic", "general"),
                    "importance": int(article.get("importance", 5)),
                    "source": article.get("source", ""),
                    "source_trust": article.get("source_trust", "low"),
                    "sentiment": article.get("sentiment", "neutral"),
                    "story_thread": article.get("story_thread", ""),
                    "link": article.get("link", ""),
                    "published": article.get("published", ""),
                    "fetched_at": article.get("fetched_at", datetime.now(UTC).isoformat()),
                }
            )

        await _request(
            "POST",
            "articles",
            params={"on_conflict": "store_key,title"},
            json_body=rows,
            prefer="resolution=merge-duplicates,return=minimal",
            expect_json=False,
        )
    except Exception as exc:
        logger.error(f"Supabase save_articles failed: {exc}", exc_info=True)
        await _fallback("save_articles", store_key, articles)


async def get_articles(store_key: str) -> list[dict]:
    if not is_configured():
        return await _fallback("get_articles", store_key)

    try:
        rows = await _request(
            "GET",
            "articles",
            params={
                "store_key": f"eq.{store_key}",
                "select": "*",
                "order": "importance.desc",
            },
        )
        return rows or []
    except Exception as exc:
        logger.error(f"Supabase get_articles failed: {exc}", exc_info=True)
        return await _fallback("get_articles", store_key)


async def get_all_store_keys() -> list[str]:
    if not is_configured():
        return await _fallback("get_all_store_keys")

    try:
        rows = await _request("GET", "articles", params={"select": "store_key"})
        keys = sorted({str(row.get("store_key", "")) for row in rows or [] if row.get("store_key")})
        return keys
    except Exception as exc:
        logger.error(f"Supabase get_all_store_keys failed: {exc}", exc_info=True)
        return await _fallback("get_all_store_keys")


async def get_articles_count(store_key: str) -> int:
    if not is_configured():
        return await _fallback("get_articles_count", store_key)

    try:
        rows = await _request(
            "GET",
            "articles",
            params={"store_key": f"eq.{store_key}", "select": "id"},
        )
        return len(rows or [])
    except Exception as exc:
        logger.error(f"Supabase get_articles_count failed: {exc}", exc_info=True)
        return await _fallback("get_articles_count", store_key)


# -- Profiles ---------------------------------------------------------


async def save_profile(profile: dict) -> None:
    if not is_configured():
        await _fallback("save_profile", profile)
        return

    payload = {
        "sync_code": profile["sync_code"],
        "preferred_topics": profile.get("preferred_topics", []),
        "country": profile.get("country", "GLOBAL"),
        "language": profile.get("language", "en"),
        "signals": profile.get("signals", {}),
        "bookmarks": profile.get("bookmarks", []),
        "analytics": profile.get("analytics", {}),
        "created_at": profile.get("created_at", datetime.now(UTC).isoformat()),
        "last_active": profile.get("last_active", datetime.now(UTC).isoformat()),
    }

    try:
        await _request(
            "POST",
            "profiles",
            json_body=payload,
            prefer="resolution=merge-duplicates,return=minimal",
            expect_json=False,
        )
    except Exception as exc:
        logger.error(f"Supabase save_profile failed: {exc}", exc_info=True)
        await _fallback("save_profile", profile)


async def get_profile(sync_code: str) -> dict | None:
    if not is_configured():
        return await _fallback("get_profile", sync_code)

    try:
        rows = await _request(
            "GET",
            "profiles",
            params={"sync_code": f"eq.{sync_code}", "select": "*", "limit": "1"},
        )
        if not rows:
            return None

        profile = dict(rows[0])
        profile["preferred_topics"] = _coerce_json_field(profile.get("preferred_topics"), [])
        profile["signals"] = _coerce_json_field(profile.get("signals"), {})
        profile["bookmarks"] = _coerce_json_field(profile.get("bookmarks"), [])
        profile["analytics"] = _coerce_json_field(profile.get("analytics"), {})
        return profile
    except Exception as exc:
        logger.error(f"Supabase get_profile failed: {exc}", exc_info=True)
        return await _fallback("get_profile", sync_code)


async def get_all_profiles() -> list[dict]:
    if not is_configured():
        return await _fallback("get_all_profiles")

    try:
        rows = await _request("GET", "profiles", params={"select": "*"})
        profiles = []
        for row in rows or []:
            profile = dict(row)
            profile["preferred_topics"] = _coerce_json_field(profile.get("preferred_topics"), [])
            profile["signals"] = _coerce_json_field(profile.get("signals"), {})
            profile["bookmarks"] = _coerce_json_field(profile.get("bookmarks"), [])
            profile["analytics"] = _coerce_json_field(profile.get("analytics"), {})
            profiles.append(profile)
        return profiles
    except Exception as exc:
        logger.error(f"Supabase get_all_profiles failed: {exc}", exc_info=True)
        return await _fallback("get_all_profiles")


# -- Subscribers ------------------------------------------------------


async def save_subscriber(subscriber: dict) -> None:
    if not is_configured():
        await _fallback("save_subscriber", subscriber)
        return

    payload = {
        "email": subscriber["email"],
        "topics": subscriber.get("topics", []),
        "country": subscriber.get("country", "GLOBAL"),
        "language": subscriber.get("language", "en"),
        "subscribed_at": subscriber.get("subscribed_at", datetime.now(UTC).isoformat()),
        "updated_at": subscriber.get("updated_at", datetime.now(UTC).isoformat()),
        "is_active": bool(subscriber.get("is_active", True)),
    }

    try:
        await _request(
            "POST",
            "subscribers",
            json_body=payload,
            prefer="resolution=merge-duplicates,return=minimal",
            expect_json=False,
        )
    except Exception as exc:
        logger.error(f"Supabase save_subscriber failed: {exc}", exc_info=True)
        await _fallback("save_subscriber", subscriber)


async def get_subscriber(email: str) -> dict | None:
    if not is_configured():
        return await _fallback("get_subscriber", email)

    try:
        rows = await _request(
            "GET",
            "subscribers",
            params={"email": f"eq.{email}", "select": "*", "limit": "1"},
        )
        if not rows:
            return None

        sub = dict(rows[0])
        sub["topics"] = _coerce_json_field(sub.get("topics"), [])
        sub["is_active"] = bool(sub.get("is_active", True))
        return sub
    except Exception as exc:
        logger.error(f"Supabase get_subscriber failed: {exc}", exc_info=True)
        return await _fallback("get_subscriber", email)


async def get_all_subscribers() -> list[dict]:
    if not is_configured():
        return await _fallback("get_all_subscribers")

    try:
        rows = await _request(
            "GET",
            "subscribers",
            params={"is_active": "eq.true", "select": "*"},
        )
        result = []
        for row in rows or []:
            sub = dict(row)
            sub["topics"] = _coerce_json_field(sub.get("topics"), [])
            sub["is_active"] = bool(sub.get("is_active", True))
            result.append(sub)
        return result
    except Exception as exc:
        logger.error(f"Supabase get_all_subscribers failed: {exc}", exc_info=True)
        return await _fallback("get_all_subscribers")


async def get_subscriber_count() -> int:
    if not is_configured():
        return await _fallback("get_subscriber_count")

    try:
        rows = await _request(
            "GET",
            "subscribers",
            params={"is_active": "eq.true", "select": "id"},
        )
        return len(rows or [])
    except Exception as exc:
        logger.error(f"Supabase get_subscriber_count failed: {exc}", exc_info=True)
        return await _fallback("get_subscriber_count")


# -- Metadata ---------------------------------------------------------


async def set_metadata(key: str, value: str) -> None:
    if not is_configured():
        await _fallback("set_metadata", key, value)
        return

    try:
        await _request(
            "POST",
            "metadata",
            json_body={"key": key, "value": value},
            prefer="resolution=merge-duplicates,return=minimal",
            expect_json=False,
        )
    except Exception as exc:
        logger.error(f"Supabase set_metadata failed: {exc}", exc_info=True)
        await _fallback("set_metadata", key, value)


async def get_metadata(key: str) -> str | None:
    if not is_configured():
        return await _fallback("get_metadata", key)

    try:
        rows = await _request(
            "GET",
            "metadata",
            params={"key": f"eq.{key}", "select": "value", "limit": "1"},
        )
        if not rows:
            return None
        return rows[0].get("value")
    except Exception as exc:
        logger.error(f"Supabase get_metadata failed: {exc}", exc_info=True)
        return await _fallback("get_metadata", key)


async def get_all_metadata() -> dict[str, str]:
    if not is_configured():
        return await _fallback("get_all_metadata")

    try:
        rows = await _request("GET", "metadata", params={"select": "key,value"})
        return {
            str(row.get("key", "")): str(row.get("value") or "")
            for row in rows or []
            if row.get("key")
        }
    except Exception as exc:
        logger.error(f"Supabase get_all_metadata failed: {exc}", exc_info=True)
        return await _fallback("get_all_metadata")


async def get_cache_health() -> dict:
    if not is_configured():
        return await _fallback("get_cache_health")

    try:
        article_rows = await _request(
            "GET",
            "articles",
            params={"select": "store_key,importance,fetched_at,created_at"},
        )
        total_articles = len(article_rows or [])

        per_key_map: dict[str, dict] = {}
        per_country: dict[str, int] = {}

        for row in article_rows or []:
            key = str(row.get("store_key", ""))
            if not key:
                continue

            if key not in per_key_map:
                per_key_map[key] = {
                    "store_key": key,
                    "article_count": 0,
                    "max_importance": 0,
                    "last_cached_at": "",
                }

            entry = per_key_map[key]
            entry["article_count"] += 1
            entry["max_importance"] = max(
                entry["max_importance"], int(row.get("importance", 0) or 0)
            )

            fetched_at = str(row.get("fetched_at") or row.get("created_at") or "")
            if fetched_at and (not entry["last_cached_at"] or fetched_at > entry["last_cached_at"]):
                entry["last_cached_at"] = fetched_at

            country = key.split("::", 1)[0] if "::" in key else key
            per_country[country] = per_country.get(country, 0) + 1

        metadata_rows = await _request("GET", "metadata", params={"select": "key,value"})
        last_refresh_by_key: dict[str, str] = {}
        prune_stats = {
            "last_at": "",
            "last_deleted": 0,
            "total_deleted": 0,
            "runs": 0,
        }

        for row in metadata_rows or []:
            meta_key = str(row.get("key", ""))
            value = str(row.get("value") or "")

            if meta_key.startswith("last_updated:"):
                last_refresh_by_key[meta_key.replace("last_updated:", "", 1)] = value
                continue

            if meta_key == "cache_prune_last_at":
                prune_stats["last_at"] = value
            elif meta_key == "cache_prune_last_deleted":
                prune_stats["last_deleted"] = int(value or "0")
            elif meta_key == "cache_prune_total_deleted":
                prune_stats["total_deleted"] = int(value or "0")
            elif meta_key == "cache_prune_runs":
                prune_stats["runs"] = int(value or "0")

        return {
            "cache_limit": CACHE_MAX_ARTICLES,
            "total_articles": total_articles,
            "total_store_keys": len(per_key_map),
            "per_store_key": sorted(per_key_map.values(), key=lambda item: item["store_key"]),
            "per_country": per_country,
            "prune": prune_stats,
            "last_refresh_by_store_key": last_refresh_by_key,
        }
    except Exception as exc:
        logger.error(f"Supabase get_cache_health failed: {exc}", exc_info=True)
        return await _fallback("get_cache_health")


# -- User Events (Analytics) -----------------------------------------


async def save_events(events: list[dict]) -> None:
    if not is_configured():
        await _fallback("save_events", events)
        return

    try:
        rows = []
        for e in events:
            rows.append(
                {
                    "session_id": e.get("session_id", ""),
                    "sync_code": e.get("sync_code", ""),
                    "event_type": e.get("event_type", ""),
                    "article_id": e.get("article_id", ""),
                    "topic": e.get("topic", ""),
                    "category": e.get("category", ""),
                    "value": float(e.get("value", 0)),
                    "metadata": e.get("metadata", {}),
                }
            )
        if rows:
            await _request(
                "POST",
                "user_events",
                json_body=rows,
                prefer="return=minimal",
                expect_json=False,
            )
    except Exception as exc:
        logger.error(f"Supabase save_events failed: {exc}", exc_info=True)
        await _fallback("save_events", events)


async def get_events(session_id: str, limit: int = 500) -> list[dict]:
    if not is_configured():
        return await _fallback("get_events", session_id, limit)

    try:
        rows = await _request(
            "GET",
            "user_events",
            params={
                "session_id": f"eq.{session_id}",
                "select": "*",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )
        for row in rows or []:
            row["metadata"] = _coerce_json_field(row.get("metadata"), {})
        return rows or []
    except Exception as exc:
        logger.error(f"Supabase get_events failed: {exc}", exc_info=True)
        return await _fallback("get_events", session_id, limit)


async def get_events_by_sync_code(sync_code: str, limit: int = 1000) -> list[dict]:
    if not is_configured():
        return await _fallback("get_events_by_sync_code", sync_code, limit)

    try:
        rows = await _request(
            "GET",
            "user_events",
            params={
                "sync_code": f"eq.{sync_code}",
                "select": "*",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )
        for row in rows or []:
            row["metadata"] = _coerce_json_field(row.get("metadata"), {})
        return rows or []
    except Exception as exc:
        logger.error(f"Supabase get_events_by_sync_code failed: {exc}", exc_info=True)
        return await _fallback("get_events_by_sync_code", sync_code, limit)


async def get_event_counts() -> dict:
    if not is_configured():
        return await _fallback("get_event_counts")

    try:
        rows = await _request(
            "GET",
            "user_events",
            params={"select": "event_type"},
        )
        counts: dict[str, int] = {}
        for row in rows or []:
            et = row.get("event_type", "")
            counts[et] = counts.get(et, 0) + 1
        return counts
    except Exception as exc:
        logger.error(f"Supabase get_event_counts failed: {exc}", exc_info=True)
        return await _fallback("get_event_counts")


# -- User Topic Scores -----------------------------------------------


async def save_topic_scores(
    session_id: str, sync_code: str, scores: dict[str, float], event_counts: dict[str, int]
) -> None:
    if not is_configured():
        await _fallback("save_topic_scores", session_id, sync_code, scores, event_counts)
        return

    try:
        rows = []
        for topic, score in scores.items():
            rows.append(
                {
                    "session_id": session_id,
                    "sync_code": sync_code,
                    "topic": topic,
                    "score": score,
                    "event_count": event_counts.get(topic, 0),
                }
            )
        if rows:
            await _request(
                "POST",
                "user_topic_scores",
                params={"on_conflict": "session_id,topic"},
                json_body=rows,
                prefer="resolution=merge-duplicates,return=minimal",
                expect_json=False,
            )
    except Exception as exc:
        logger.error(f"Supabase save_topic_scores failed: {exc}", exc_info=True)
        await _fallback("save_topic_scores", session_id, sync_code, scores, event_counts)


async def get_topic_scores(session_id: str) -> dict[str, float]:
    if not is_configured():
        return await _fallback("get_topic_scores", session_id)

    try:
        rows = await _request(
            "GET",
            "user_topic_scores",
            params={
                "session_id": f"eq.{session_id}",
                "select": "topic,score",
                "order": "score.desc",
            },
        )
        return {row["topic"]: float(row["score"]) for row in rows or []}
    except Exception as exc:
        logger.error(f"Supabase get_topic_scores failed: {exc}", exc_info=True)
        return await _fallback("get_topic_scores", session_id)


async def get_topic_scores_by_sync_code(sync_code: str) -> dict[str, float]:
    if not is_configured():
        return await _fallback("get_topic_scores_by_sync_code", sync_code)

    try:
        rows = await _request(
            "GET",
            "user_topic_scores",
            params={
                "sync_code": f"eq.{sync_code}",
                "select": "topic,score",
            },
        )
        totals: dict[str, float] = {}
        for row in rows or []:
            t = row["topic"]
            totals[t] = totals.get(t, 0) + float(row["score"])
        return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))
    except Exception as exc:
        logger.error(f"Supabase get_topic_scores_by_sync_code failed: {exc}", exc_info=True)
        return await _fallback("get_topic_scores_by_sync_code", sync_code)


# -- RSS Feeds (Admin) ------------------------------------------------


async def save_rss_feed(
    country_code: str, feed_key: str, query: str, is_active: bool = True
) -> None:
    global _RSS_FEEDS_TABLE_AVAILABLE
    if not is_configured():
        await _fallback("save_rss_feed", country_code, feed_key, query, is_active)
        return

    if _RSS_FEEDS_TABLE_AVAILABLE is False:
        await _fallback("save_rss_feed", country_code, feed_key, query, is_active)
        return

    try:
        await _request(
            "POST",
            "rss_feeds",
            params={"on_conflict": "country_code,feed_key"},
            json_body={
                "country_code": country_code,
                "feed_key": feed_key,
                "query": query,
                "is_active": is_active,
            },
            prefer="resolution=merge-duplicates,return=minimal",
            expect_json=False,
        )
        _RSS_FEEDS_TABLE_AVAILABLE = True
    except Exception as exc:
        if _mark_rss_feeds_missing(exc):
            await _fallback("save_rss_feed", country_code, feed_key, query, is_active)
            return
        logger.error(f"Supabase save_rss_feed failed: {exc}", exc_info=True)
        await _fallback("save_rss_feed", country_code, feed_key, query, is_active)


async def get_rss_feeds(country_code: str | None = None) -> list[dict]:
    global _RSS_FEEDS_TABLE_AVAILABLE
    if not is_configured():
        return await _fallback("get_rss_feeds", country_code)

    if _RSS_FEEDS_TABLE_AVAILABLE is False:
        return await _fallback("get_rss_feeds", country_code)

    try:
        params = {"select": "*", "order": "country_code,feed_key"}
        if country_code:
            params["country_code"] = f"eq.{country_code}"
        rows = await _request("GET", "rss_feeds", params=params)
        _RSS_FEEDS_TABLE_AVAILABLE = True
        return rows or []
    except Exception as exc:
        if _mark_rss_feeds_missing(exc):
            return await _fallback("get_rss_feeds", country_code)
        logger.error(f"Supabase get_rss_feeds failed: {exc}", exc_info=True)
        return await _fallback("get_rss_feeds", country_code)


async def delete_rss_feed(country_code: str, feed_key: str) -> bool:
    global _RSS_FEEDS_TABLE_AVAILABLE
    if not is_configured():
        return await _fallback("delete_rss_feed", country_code, feed_key)

    if _RSS_FEEDS_TABLE_AVAILABLE is False:
        return await _fallback("delete_rss_feed", country_code, feed_key)

    try:
        await _request(
            "DELETE",
            "rss_feeds",
            params={
                "country_code": f"eq.{country_code}",
                "feed_key": f"eq.{feed_key}",
            },
            prefer="return=minimal",
            expect_json=False,
        )
        _RSS_FEEDS_TABLE_AVAILABLE = True
        return True
    except Exception as exc:
        if _mark_rss_feeds_missing(exc):
            return await _fallback("delete_rss_feed", country_code, feed_key)
        logger.error(f"Supabase delete_rss_feed failed: {exc}", exc_info=True)
        return await _fallback("delete_rss_feed", country_code, feed_key)
