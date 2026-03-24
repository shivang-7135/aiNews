import json
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path

NEWS_STORE: dict[str, list[dict]] = {}
LAST_UPDATED: dict[str, str] = {}
RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)

SUBSCRIBERS_FILE = Path("subscribers.json")

AI_THOUGHTS = [
    {
        "text": "AI does not sleep, but it still needs coffee because even neural networks need a warm-up.",
        "emoji": "brain",
        "vibe": "chill",
    },
    {
        "text": "Humans took millions of years to evolve. GPT-5 took months. No pressure.",
        "emoji": "rocket",
        "vibe": "existential",
    },
    {
        "text": "The future is not human versus AI. It is human with AI versus human without AI.",
        "emoji": "bolt",
        "vibe": "motivational",
    },
]


def get_daily_thought() -> dict:
    day_of_year = datetime.now(UTC).timetuple().tm_yday
    idx = day_of_year % len(AI_THOUGHTS)
    return AI_THOUGHTS[idx]


def load_subscribers() -> list[dict]:
    if SUBSCRIBERS_FILE.exists():
        try:
            data = json.loads(SUBSCRIBERS_FILE.read_text())
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []
    return []


def save_subscribers(subs: list[dict]) -> None:
    SUBSCRIBERS_FILE.write_text(json.dumps(subs, indent=2))
