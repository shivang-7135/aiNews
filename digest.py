"""
DailyAI — Email Digest Generator
1. Welcome email (sent immediately on subscribe) with top 10 global news
2. Daily digest (sent at 8 AM UTC) with top 10 news
Uses Resend API for sending.
"""

import logging
import os
import re
from datetime import UTC, datetime

logger = logging.getLogger("dailyai.digest")

# App URL
APP_URL = os.getenv("APP_URL", "https://shark-app-96259.ondigitalocean.app")
RESEND_REPLY_TO = os.getenv("RESEND_REPLY_TO", "")
DEFAULT_FROM_EMAIL = "DailyAI <onboarding@resend.dev>"


def _resolve_from_email() -> str:
    """Return a valid Resend-compatible From value, with safe fallback."""
    raw = os.getenv("RESEND_FROM_EMAIL", "").strip()
    if not raw:
        return DEFAULT_FROM_EMAIL

    # Remove optional surrounding quotes from .env values.
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        raw = raw[1:-1].strip()

    # Accept plain email format.
    plain_email = re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", raw)
    if plain_email:
        return raw

    # Accept Name <email@example.com> format.
    named_email = re.fullmatch(r"[^<>]+<\s*([^@\s<>]+@[^@\s<>]+\.[^@\s<>]+)\s*>", raw)
    if named_email:
        return raw

    logger.warning(
        "[Email] Invalid RESEND_FROM_EMAIL='%s'. Falling back to %s. "
        "Use plain email or 'Name <email@example.com>' format.",
        raw,
        DEFAULT_FROM_EMAIL,
    )
    return DEFAULT_FROM_EMAIL


RESEND_FROM_EMAIL = _resolve_from_email()

# Category colors for email
CATEGORY_COLORS = {
    "breakthrough": "#22d3ee",
    "product": "#6366f1",
    "regulation": "#f43f5e",
    "funding": "#10b981",
    "research": "#a855f7",
    "industry": "#3b82f6",
    "general": "#f59e0b",
}


def _render_stories_html(tiles: list[dict]) -> str:
    """Render HTML rows for a list of tiles."""
    stories_html = ""
    for i, tile in enumerate(tiles[:10]):
        cat = tile.get("category", "general")
        color = CATEGORY_COLORS.get(cat, "#f59e0b")
        importance = tile.get("importance", 5)
        stars = "🔥" if importance >= 8 else "⭐" if importance >= 6 else ""
        why = tile.get("why_it_matters", "")
        why_html = (
            f'<p style="margin:6px 0 0;font-size:13px;color:#2dd4a0;font-style:italic;">💡 {why}</p>'
            if why
            else ""
        )
        link = tile.get("link", "#")
        title = tile.get("title", "")
        summary = tile.get("summary", "")
        source = tile.get("source", "")
        published = tile.get("published", "")
        pub_display = published[:10] if published else ""

        stories_html += f"""
        <tr>
          <td style="padding:16px 20px;border-bottom:1px solid #1e1e3f;">
            <div style="margin-bottom:6px;">
              <span style="background:{color}22;color:{color};font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 8px;border-radius:4px;letter-spacing:0.5px;">{cat}</span>
              <span style="font-size:12px;color:#6b6b8d;margin-left:6px;">{stars}</span>
            </div>
            <a href="{link}" style="color:#f0f0ff;font-size:15px;font-weight:600;text-decoration:none;line-height:1.4;">{i + 1}. {title}</a>
            <p style="margin:6px 0 0;font-size:13px;color:#a0a0c0;line-height:1.5;">{summary}</p>
            {why_html}
            <p style="margin:8px 0 0;font-size:11px;color:#6b6b8d;">{source} • {pub_display}</p>
          </td>
        </tr>"""
    return stories_html


def _build_email(
    subject_emoji: str,
    heading: str,
    subheading: str,
    intro_text: str,
    stories_html: str,
    date_str: str,
) -> str:
    """Build a full HTML email wrapper around the stories."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0a0a0b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0b;">
    <tr><td align="center" style="padding:20px;">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="padding:30px 20px;text-align:center;background:linear-gradient(135deg,#111113,#1e1e22);border-radius:16px 16px 0 0;border:1px solid #2a2a2e;border-bottom:none;">
            <h1 style="margin:0;color:#2dd4a0;font-size:28px;font-weight:800;">{subject_emoji} DailyAI</h1>
            <p style="margin:8px 0 0;color:#ffffff;font-size:16px;font-weight:600;">{heading}</p>
            <p style="margin:4px 0 0;color:#7a7a85;font-size:12px;">{subheading} • {date_str}</p>
          </td>
        </tr>

        <!-- Intro -->
        <tr>
          <td style="padding:20px;background:#111113;color:#b0b0b8;font-size:14px;line-height:1.6;border-left:1px solid #2a2a2e;border-right:1px solid #2a2a2e;">
            {intro_text}
          </td>
        </tr>

        <!-- Stories -->
        <tr>
          <td style="background:#111113;border-left:1px solid #2a2a2e;border-right:1px solid #2a2a2e;">
            <table width="100%" cellpadding="0" cellspacing="0">
              {stories_html}
            </table>
          </td>
        </tr>

        <!-- CTA -->
        <tr>
          <td style="padding:24px 20px;background:#111113;text-align:center;border-left:1px solid #2a2a2e;border-right:1px solid #2a2a2e;">
            <a href="{APP_URL}" style="display:inline-block;padding:14px 32px;background:#2dd4a0;color:#000;font-size:14px;font-weight:700;text-decoration:none;border-radius:12px;">
              📱 Open DailyAI App
            </a>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px;background:#0a0a0b;text-align:center;border-radius:0 0 16px 16px;border:1px solid #2a2a2e;border-top:none;">
            <p style="margin:0;font-size:11px;color:#6b6b8d;">
              Powered by AI Agent • Curated hourly from 50+ sources<br>
              <a href="{APP_URL}" style="color:#2dd4a0;text-decoration:none;">DailyAI</a> •
              Reply to this email to give feedback
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def generate_digest_html(tiles: list[dict], date_str: str = "") -> str:
    """Generate the daily digest HTML."""
    if not date_str:
        date_str = datetime.now(UTC).strftime("%B %d, %Y")
    stories = _render_stories_html(tiles)
    return _build_email(
        subject_emoji="🤖",
        heading="Your Daily AI Intelligence Brief",
        subheading="Top 10 AI stories from the past 24 hours",
        intro_text="Here are the top AI stories from the past 24 hours, curated by our AI agent. Each story is ranked by importance and categorized for quick scanning.",
        stories_html=stories,
        date_str=date_str,
    )


def generate_welcome_html(tiles: list[dict]) -> str:
    """Generate the welcome email HTML with top 10 current news."""
    date_str = datetime.now(UTC).strftime("%B %d, %Y")
    stories = _render_stories_html(tiles)
    return _build_email(
        subject_emoji="👋",
        heading="Welcome to DailyAI!",
        subheading="You're now part of the AI-informed crew",
        intro_text="Thanks for subscribing! 🎉 You'll receive the <strong>top 10 AI stories</strong> in your inbox every morning at 8 AM UTC. Here's what's trending in AI right now:",
        stories_html=stories,
        date_str=date_str,
    )


def _get_resend():
    """Get a configured resend instance, or None."""
    resend_key = os.getenv("RESEND_API_KEY", "")
    if not resend_key:
        logger.info("[Email] RESEND_API_KEY not set — skipping email send")
        return None
    try:
        import resend

        resend.api_key = resend_key
        return resend
    except ImportError:
        logger.warning("[Email] resend package not installed — skipping")
        return None


async def send_welcome_email(email: str, tiles: list[dict]):
    """Send welcome email with top 10 news immediately after subscribe."""
    resend_mod = _get_resend()
    if not resend_mod:
        return

    if not tiles:
        logger.info(f"[Welcome] No tiles available for welcome email to {email}")
        return

    html = generate_welcome_html(tiles[:10])
    try:
        payload = {
            "from": RESEND_FROM_EMAIL,
            "to": [email],
            "subject": "👋 Welcome to DailyAI — Here's today's top AI news!",
            "html": html,
        }
        if RESEND_REPLY_TO:
            payload["reply_to"] = RESEND_REPLY_TO

        response = resend_mod.Emails.send(payload)
        logger.info(f"[Welcome] ✅ Sent welcome email to {email} (response={response})")

        if "@resend.dev" in RESEND_FROM_EMAIL.lower():
            logger.warning(
                "[Welcome] Using onboarding@resend.dev. This is test mode and may only deliver to verified/test recipients. Configure RESEND_FROM_EMAIL with your verified domain for production delivery."
            )
    except Exception as e:
        logger.warning(f"[Welcome] ❌ Failed to send to {email}: {e}")


async def send_digest():
    """Send daily digest to all subscribers. Requires RESEND_API_KEY."""
    resend_mod = _get_resend()
    if not resend_mod:
        return

    # Import here to avoid circular imports
    from app import NEWS_STORE, load_subscribers, store_key

    tiles = NEWS_STORE.get(store_key("GLOBAL", "en"), [])
    if not tiles:
        logger.info("[Digest] No tiles available — skipping digest")
        return

    subscribers = load_subscribers()
    if not subscribers:
        logger.info("[Digest] No subscribers — skipping digest")
        return

    html = generate_digest_html(tiles[:10])
    date_str = datetime.now(UTC).strftime("%b %d")

    sent = 0
    for sub in subscribers:
        try:
            payload = {
                "from": RESEND_FROM_EMAIL,
                "to": [sub["email"]],
                "subject": f"🤖 DailyAI Brief — {date_str}",
                "html": html,
            }
            if RESEND_REPLY_TO:
                payload["reply_to"] = RESEND_REPLY_TO

            response = resend_mod.Emails.send(payload)
            sent += 1
            logger.info(f"[Digest] Sent to {sub['email']} (response={response})")
        except Exception as e:
            logger.warning(f"[Digest] Failed to send to {sub['email']}: {e}")

    logger.info(f"[Digest] ✅ Sent digest to {sent}/{len(subscribers)} subscribers")
