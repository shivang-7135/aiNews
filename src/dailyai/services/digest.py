"""
DailyAI — Email Digest Service
Daily AI brief and welcome emails via Resend API.
"""

import logging
from datetime import UTC, datetime

from dailyai.config import APP_URL, RESEND_API_KEY, RESEND_FROM_EMAIL, RESEND_REPLY_TO

logger = logging.getLogger("dailyai.services.digest")

CATEGORY_COLORS = {
    "breakthrough": "#22d3ee", "product": "#6366f1", "regulation": "#f43f5e",
    "funding": "#10b981", "research": "#a855f7", "industry": "#3b82f6",
    "general": "#f59e0b",
}


def _render_stories_html(tiles: list[dict]) -> str:
    stories = ""
    for i, tile in enumerate(tiles[:10]):
        cat = tile.get("category", "general")
        color = CATEGORY_COLORS.get(cat, "#f59e0b")
        importance = tile.get("importance", 5)
        stars = "🔥" if importance >= 8 else "⭐" if importance >= 6 else ""
        why = tile.get("why_it_matters", "")
        why_html = (
            f'<p style="margin:6px 0 0;font-size:13px;color:#2dd4a0;font-style:italic;">💡 {why}</p>'
            if why else ""
        )
        title = tile.get("title", tile.get("headline", ""))
        link = tile.get("link", tile.get("article_url", "#"))
        summary = tile.get("summary", "")
        source = tile.get("source", tile.get("source_name", ""))
        published = tile.get("published", tile.get("published_at", ""))
        pub_display = published[:10] if published else ""

        stories += f"""
        <tr>
          <td style="padding:16px 20px;border-bottom:1px solid #1e1e3f;">
            <div style="margin-bottom:6px;">
              <span style="background:{color}22;color:{color};font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 8px;border-radius:4px;">{cat}</span>
              <span style="font-size:12px;color:#6b6b8d;margin-left:6px;">{stars}</span>
            </div>
            <a href="{link}" style="color:#f0f0ff;font-size:15px;font-weight:600;text-decoration:none;">{i+1}. {title}</a>
            <p style="margin:6px 0 0;font-size:13px;color:#a0a0c0;line-height:1.5;">{summary}</p>
            {why_html}
            <p style="margin:8px 0 0;font-size:11px;color:#6b6b8d;">{source} • {pub_display}</p>
          </td>
        </tr>"""
    return stories


def _build_email(subject_emoji: str, heading: str, subheading: str,
                 intro_text: str, stories_html: str, date_str: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0a0a0b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0b;">
    <tr><td align="center" style="padding:20px;">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
        <tr><td style="padding:30px 20px;text-align:center;background:linear-gradient(135deg,#111113,#1e1e22);border-radius:16px 16px 0 0;border:1px solid #2a2a2e;border-bottom:none;">
            <h1 style="margin:0;color:#2dd4a0;font-size:28px;font-weight:800;">{subject_emoji} DailyAI</h1>
            <p style="margin:8px 0 0;color:#ffffff;font-size:16px;font-weight:600;">{heading}</p>
            <p style="margin:4px 0 0;color:#7a7a85;font-size:12px;">{subheading} • {date_str}</p>
        </td></tr>
        <tr><td style="padding:20px;background:#111113;color:#b0b0b8;font-size:14px;line-height:1.6;border-left:1px solid #2a2a2e;border-right:1px solid #2a2a2e;">{intro_text}</td></tr>
        <tr><td style="background:#111113;border-left:1px solid #2a2a2e;border-right:1px solid #2a2a2e;"><table width="100%" cellpadding="0" cellspacing="0">{stories_html}</table></td></tr>
        <tr><td style="padding:24px 20px;background:#111113;text-align:center;border-left:1px solid #2a2a2e;border-right:1px solid #2a2a2e;">
            <a href="{APP_URL}" style="display:inline-block;padding:14px 32px;background:#2dd4a0;color:#000;font-size:14px;font-weight:700;text-decoration:none;border-radius:12px;">📱 Open DailyAI App</a>
        </td></tr>
        <tr><td style="padding:20px;background:#0a0a0b;text-align:center;border-radius:0 0 16px 16px;border:1px solid #2a2a2e;border-top:none;">
            <p style="margin:0;font-size:11px;color:#6b6b8d;">Powered by LangGraph Agent • Curated hourly from 50+ sources<br>
              <a href="{APP_URL}" style="color:#2dd4a0;text-decoration:none;">DailyAI</a>
            </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


async def send_welcome_email(email: str, tiles: list[dict]):
    """Send welcome email with top news."""
    if not RESEND_API_KEY:
        return
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        date_str = datetime.now(UTC).strftime("%B %d, %Y")
        stories = _render_stories_html(tiles[:10])
        html = _build_email("👋", "Welcome to DailyAI!",
                           "You're now part of the AI-informed crew",
                           "Thanks for subscribing! 🎉 You'll receive the <strong>top 10 AI stories</strong> in your inbox every morning.",
                           stories, date_str)
        payload: dict = {"from": RESEND_FROM_EMAIL, "to": [email],
                "subject": "👋 Welcome to DailyAI — Here's today's top AI news!", "html": html}
        if RESEND_REPLY_TO:
            payload["reply_to"] = RESEND_REPLY_TO
        resend.Emails.send(payload)
        logger.info(f"Welcome email sent to {email}")
    except Exception as e:
        logger.warning(f"Failed to send welcome email to {email}: {e}")


async def send_digest():
    """Send daily digest to all subscribers."""
    if not RESEND_API_KEY:
        return
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        from dailyai.config import store_key
        from dailyai.storage.backend import get_all_subscribers, get_articles

        tiles = await get_articles(store_key("GLOBAL", "en"))
        if not tiles:
            return
        subs = await get_all_subscribers()
        if not subs:
            return

        date_str = datetime.now(UTC).strftime("%b %d")
        stories = _render_stories_html(tiles[:10])
        html = _build_email("🤖", "Your Daily AI Intelligence Brief",
                           "Top 10 AI stories from the past 24 hours",
                           "Curated by our AI agent, ranked by importance.",
                           stories, datetime.now(UTC).strftime("%B %d, %Y"))

        sent = 0
        for sub in subs:
            try:
                payload: dict = {"from": RESEND_FROM_EMAIL, "to": [sub["email"]],
                        "subject": f"🤖 DailyAI Brief — {date_str}", "html": html}
                if RESEND_REPLY_TO:
                    payload["reply_to"] = RESEND_REPLY_TO
                resend.Emails.send(payload)
                sent += 1
            except Exception as e:
                logger.warning(f"Failed to send digest to {sub['email']}: {e}")

        logger.info(f"Digest sent to {sent}/{len(subs)} subscribers")
    except Exception as e:
        logger.error(f"Digest job failed: {e}")
