"""SQLite -> Supabase migration utility.

Usage examples:
- uv run dailyai-migrate-supabase --write-schema-only
- uv run dailyai-migrate-supabase --check-only
- uv run dailyai-migrate-supabase
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Iterable

import httpx

from dailyai.config import SUPABASE_KEY, SUPABASE_TIMEOUT_SECONDS, SUPABASE_URL
from dailyai.storage import sqlite

logger = logging.getLogger("dailyai.storage.migrate")

REQUIRED_TABLES = ("articles", "profiles", "subscribers", "metadata", "user_events", "user_topic_scores")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "supabase" / "bootstrap.sql"


def _chunked(items: list[dict], size: int = 250) -> Iterable[list[dict]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _build_headers(*, prefer: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _read_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        return response.text

    if isinstance(payload, dict):
        code = payload.get("code")
        message = payload.get("message") or payload.get("hint") or payload.get("details")
        return f"{code}: {message}" if code else str(message)

    return str(payload)


class SupabaseRestClient:
    def __init__(self, url: str, key: str, timeout_seconds: float) -> None:
        self.base_url = url.rstrip("/")
        self.key = key
        self.timeout = httpx.Timeout(timeout_seconds)

    def _table_url(self, table: str) -> str:
        return f"{self.base_url}/rest/v1/{table}"

    async def request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict | list | None = None,
        prefer: str | None = None,
        raise_for_status: bool = True,
    ) -> httpx.Response:
        headers = _build_headers(prefer=prefer)
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                self._table_url(table),
                params=params,
                json=json_body,
                headers=headers,
            )

        if raise_for_status:
            response.raise_for_status()
        return response

    async def table_exists(self, table: str) -> bool:
        response = await self.request(
            "GET",
            table,
            params={"select": "*", "limit": "1"},
            raise_for_status=False,
        )

        if response.status_code < 300:
            return True

        message = _read_error_message(response).lower()
        if "does not exist" in message or "42p01" in message:
            return False

        response.raise_for_status()
        return False

    async def count_rows(self, table: str, *, filters: dict[str, str] | None = None) -> int:
        params = {"select": "*"}
        if filters:
            params.update(filters)

        response = await self.request(
            "HEAD",
            table,
            params=params,
            prefer="count=exact",
            raise_for_status=False,
        )
        if response.status_code < 300:
            content_range = response.headers.get("content-range", "")
            if "/" in content_range:
                count_part = content_range.rsplit("/", 1)[-1]
                if count_part.isdigit():
                    return int(count_part)

        rows = await self.request("GET", table, params=params)
        return len(rows.json() or [])

    async def delete_where(self, table: str, filters: dict[str, str]) -> None:
        await self.request(
            "DELETE",
            table,
            params=filters,
            prefer="return=minimal",
            raise_for_status=True,
        )

    async def insert_rows(self, table: str, rows: list[dict], *, on_conflict: str | None = None) -> int:
        if not rows:
            return 0

        inserted = 0
        prefer = "resolution=merge-duplicates,return=minimal" if on_conflict else "return=minimal"

        for batch in _chunked(rows):
            params: dict[str, str] | None = None
            if on_conflict:
                params = {"on_conflict": on_conflict}

            await self.request(
                "POST",
                table,
                params=params,
                json_body=batch,
                prefer=prefer,
                raise_for_status=True,
            )
            inserted += len(batch)

        return inserted


async def _sqlite_snapshot() -> dict:
    await sqlite.get_db()

    store_keys = await sqlite.get_all_store_keys()
    articles_by_key: dict[str, list[dict]] = {}
    total_articles = 0
    for key in store_keys:
        rows = await sqlite.get_articles(key)
        articles_by_key[key] = rows
        total_articles += len(rows)

    profiles = await sqlite.get_all_profiles()
    subscribers = await sqlite.get_all_subscribers()
    metadata = await sqlite.get_all_metadata()
    user_events = await sqlite.get_all_events()
    user_topic_scores = await sqlite.get_all_topic_scores()

    return {
        "store_keys": store_keys,
        "articles_by_key": articles_by_key,
        "total_articles": total_articles,
        "profiles": profiles,
        "subscribers": subscribers,
        "metadata": metadata,
        "user_events": user_events,
        "user_topic_scores": user_topic_scores,
    }


def _article_row(store_key: str, row: dict) -> dict:
    return {
        "store_key": store_key,
        "title": row.get("title", ""),
        "summary": row.get("summary", ""),
        "why_it_matters": row.get("why_it_matters", ""),
        "category": row.get("category", "general"),
        "topic": row.get("topic", "general"),
        "importance": int(row.get("importance", 5)),
        "source": row.get("source", ""),
        "source_trust": row.get("source_trust", "low"),
        "sentiment": row.get("sentiment", "neutral"),
        "story_thread": row.get("story_thread", ""),
        "link": row.get("link", ""),
        "published": row.get("published", ""),
        "fetched_at": row.get("fetched_at", ""),
        "created_at": row.get("created_at"),
    }


def _profile_row(row: dict) -> dict:
    return {
        "sync_code": row.get("sync_code", ""),
        "preferred_topics": row.get("preferred_topics", []),
        "country": row.get("country", "GLOBAL"),
        "language": row.get("language", "en"),
        "signals": row.get("signals", {}),
        "bookmarks": row.get("bookmarks", []),
        "analytics": row.get("analytics", {}),
        "created_at": row.get("created_at"),
        "last_active": row.get("last_active"),
    }


def _subscriber_row(row: dict) -> dict:
    return {
        "email": row.get("email", "").strip().lower(),
        "topics": row.get("topics", []),
        "country": row.get("country", "GLOBAL"),
        "language": row.get("language", "en"),
        "subscribed_at": row.get("subscribed_at"),
        "updated_at": row.get("updated_at"),
        "is_active": bool(row.get("is_active", True)),
    }


def _metadata_rows(meta: dict[str, str]) -> list[dict]:
    return [{"key": key, "value": value} for key, value in meta.items()]


def _user_events_row(row: dict) -> dict:
    return {
        "session_id": row.get("session_id", ""),
        "sync_code": row.get("sync_code", ""),
        "event_type": row.get("event_type", ""),
        "article_id": row.get("article_id", ""),
        "topic": row.get("topic", "general"),
        "category": row.get("category", "general"),
        "value": float(row.get("value", 0.0)),
        "metadata": row.get("metadata", {}),
        "created_at": row.get("created_at"),
    }

def _user_topic_scores_row(row: dict) -> dict:
    return {
        "session_id": row.get("session_id", ""),
        "sync_code": row.get("sync_code", ""),
        "topic": row.get("topic", ""),
        "score": float(row.get("score", 0.0)),
        "event_count": int(row.get("event_count", 0)),
        "updated_at": row.get("updated_at"),
    }

def write_schema_file(path: Path) -> Path:
    source = DEFAULT_SCHEMA_PATH
    if not source.exists():
        raise FileNotFoundError(f"Bootstrap schema not found at {source}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return path


async def run_migration(args: argparse.Namespace) -> int:
    schema_path = Path(args.schema_path).resolve()
    if args.write_schema or args.write_schema_only:
        written_path = write_schema_file(schema_path)
        print(f"Wrote Supabase bootstrap SQL: {written_path}")

    if args.write_schema_only:
        return 0

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Missing SUPABASE_URL or SUPABASE_KEY. Configure .env first.")
        return 2

    client = SupabaseRestClient(
        url=SUPABASE_URL,
        key=SUPABASE_KEY,
        timeout_seconds=SUPABASE_TIMEOUT_SECONDS,
    )

    if not args.skip_table_check:
        missing_tables: list[str] = []
        for table in REQUIRED_TABLES:
            exists = await client.table_exists(table)
            if not exists:
                missing_tables.append(table)

        if missing_tables:
            print("Supabase is missing required tables:")
            for table in missing_tables:
                print(f"- {table}")
            print(f"Apply SQL from: {schema_path}")
            return 2

    if args.check_only:
        print("Supabase preflight checks passed.")
        return 0

    snapshot = await _sqlite_snapshot()
    print(
        "SQLite snapshot:\n"
        f"articles={snapshot['total_articles']}, "
        f"profiles={len(snapshot['profiles'])}, "
        f"subscribers={len(snapshot['subscribers'])}, "
        f"metadata={len(snapshot['metadata'])}, "
        f"user_events={len(snapshot.get('user_events', []))}, "
        f"user_topic_scores={len(snapshot.get('user_topic_scores', []))}"
    )

    inserted_articles = 0
    for store_key in snapshot["store_keys"]:
        await client.delete_where("articles", {"store_key": f"eq.{store_key}"})
        article_rows = [_article_row(store_key, row) for row in snapshot["articles_by_key"][store_key]]
        inserted_articles += await client.insert_rows("articles", article_rows)

    profile_rows = [_profile_row(row) for row in snapshot["profiles"]]
    inserted_profiles = await client.insert_rows("profiles", profile_rows, on_conflict="sync_code")

    subscriber_rows = [_subscriber_row(row) for row in snapshot["subscribers"]]
    inserted_subscribers = await client.insert_rows(
        "subscribers",
        subscriber_rows,
        on_conflict="email",
    )

    metadata_rows = _metadata_rows(snapshot["metadata"])
    inserted_metadata = await client.insert_rows("metadata", metadata_rows, on_conflict="key")

    user_events_rows = [_user_events_row(row) for row in snapshot.get("user_events", [])]
    inserted_user_events = await client.insert_rows("user_events", user_events_rows)

    user_topic_scores_rows = [_user_topic_scores_row(row) for row in snapshot.get("user_topic_scores", [])]
    inserted_user_topic_scores = await client.insert_rows(
        "user_topic_scores",
        user_topic_scores_rows,
        on_conflict="session_id, sync_code, topic"
    )

    remote_articles = await client.count_rows("articles")
    remote_profiles = await client.count_rows("profiles")
    remote_subscribers = await client.count_rows("subscribers", filters={"is_active": "eq.true"})
    remote_metadata = await client.count_rows("metadata")
    remote_user_events = await client.count_rows("user_events")
    remote_user_topic_scores = await client.count_rows("user_topic_scores")

    print("Migration complete:")
    print(f"- inserted_articles={inserted_articles}, remote_articles={remote_articles}")
    print(f"- inserted_profiles={inserted_profiles}, remote_profiles={remote_profiles}")
    print(f"- inserted_subscribers={inserted_subscribers}, remote_active_subscribers={remote_subscribers}")
    print(f"- inserted_metadata={inserted_metadata}, remote_metadata={remote_metadata}")
    print(f"- inserted_user_events={inserted_user_events}, remote_user_events={remote_user_events}")
    print(f"- inserted_user_topic_scores={inserted_user_topic_scores}, remote_user_topic_scores={remote_user_topic_scores}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate DailyAI SQLite data to Supabase")
    parser.add_argument(
        "--schema-path",
        default=str(DEFAULT_SCHEMA_PATH),
        help="Path to write/read Supabase bootstrap SQL",
    )
    parser.add_argument(
        "--write-schema",
        action="store_true",
        help="Write bootstrap SQL to --schema-path before checks/migration",
    )
    parser.add_argument(
        "--write-schema-only",
        action="store_true",
        help="Only write bootstrap SQL and exit",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only validate Supabase connectivity/table availability and exit",
    )
    parser.add_argument(
        "--skip-table-check",
        action="store_true",
        help="Skip required table existence checks",
    )
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    parser = build_parser()
    args = parser.parse_args()
    exit_code = asyncio.run(run_migration(args))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
