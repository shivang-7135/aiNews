"""
DailyAI — Email Digest Generator
Generates a styled HTML email from the top news tiles.
Optionally sends via Resend API if RESEND_API_KEY is set.
"""

import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger("dailyai.digest")

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


def generate_digest_html(tiles: list[dict], date_str: str = "") -> str:
    """Generate a styled HTML email digest from news tiles."""
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    stories_html = ""
    for i, tile in enumerate(tiles[:10]):
        cat = tile.get("category", "general")
        color = CATEGORY_COLORS.get(cat, "#f59e0b")
        importance = tile.get("importance", 5)
        stars = "🔥" if importance >= 8 else "⭐" if importance >= 6 else ""

        why = tile.get("why_it_matters", "")
        why_html = f'<p style="margin:6px 0 0;font-size:13px;color:#a78bfa;font-style:italic;">💡 {why}</p>' if why else ""

        stories_html += f"""
        <tr>
          <td style="padding:16px 20px;border-bottom:1px solid #1e1e3f;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
              <span style="background:{color}22;color:{color};font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 8px;border-radius:4px;letter-spacing:0.5px;">{cat}</span>
              <span style="font-size:12px;color:#6b6b8d;">{stars}</span>
            </div>
            <a href="{tile.get('link', '#')}" style="color:#f0f0ff;font-size:15px;font-weight:600;text-decoration:none;line-height:1.4;">{tile.get('title', '')}</a>
            <p style="margin:6px 0 0;font-size:13px;color:#a0a0c0;line-height:1.5;">{tile.get('summary', '')}</p>
            {why_html}
            <p style="margin:8px 0 0;font-size:11px;color:#6b6b8d;">{tile.get('source', '')} • {tile.get('published', '')[:10] if tile.get('published') else ''}</p>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#06061a;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#06061a;">
    <tr><td align="center" style="padding:20px;">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="padding:30px 20px;text-align:center;background:linear-gradient(135deg,#6366f1,#a855f7);border-radius:16px 16px 0 0;">
            <h1 style="margin:0;color:white;font-size:24px;font-weight:800;">🤖 DailyAI</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">Your Daily AI Intelligence Brief</p>
            <p style="margin:4px 0 0;color:rgba(255,255,255,0.6);font-size:11px;">{date_str}</p>
          </td>
        </tr>

        <!-- Intro -->
        <tr>
          <td style="padding:20px;background:#0d0d2b;color:#a0a0c0;font-size:14px;line-height:1.6;">
            Here are the top AI stories from the past 24 hours, curated by our AI agent. Each story is ranked by importance and categorized for quick scanning.
          </td>
        </tr>

        <!-- Stories -->
        <tr>
          <td style="background:#0d0d2b;">
            <table width="100%" cellpadding="0" cellspacing="0">
              {stories_html}
            </table>
          </td>
        </tr>

        <!-- CTA -->
        <tr>
          <td style="padding:24px 20px;background:#0d0d2b;text-align:center;">
            <a href="https://ainews-m369.onrender.com" style="display:inline-block;padding:12px 28px;background:linear-gradient(135deg,#6366f1,#a855f7);color:white;font-size:14px;font-weight:600;text-decoration:none;border-radius:8px;">
              📱 Open DailyAI App
            </a>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px;background:#06061a;text-align:center;border-radius:0 0 16px 16px;border-top:1px solid #1e1e3f;">
            <p style="margin:0;font-size:11px;color:#6b6b8d;">
              Powered by AI Agent • Curated hourly from 50+ sources<br>
              <a href="https://ainews-m369.onrender.com" style="color:#6366f1;text-decoration:none;">DailyAI</a> •
              Reply to this email to give feedback
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return html


async def send_digest():
    """Send daily digest to all subscribers. Requires RESEND_API_KEY."""
    resend_key = os.getenv("RESEND_API_KEY", "")
    if not resend_key:
        logger.info("[Digest] RESEND_API_KEY not set — skipping email send")
        return

    try:
        import resend
        resend.api_key = resend_key
    except ImportError:
        logger.warning("[Digest] resend package not installed — skipping")
        return

    # Import here to avoid circular imports
    from app import NEWS_STORE, load_subscribers

    tiles = NEWS_STORE.get("GLOBAL", [])
    if not tiles:
        logger.info("[Digest] No tiles available — skipping digest")
        return

    subscribers = load_subscribers()
    if not subscribers:
        logger.info("[Digest] No subscribers — skipping digest")
        return

    html = generate_digest_html(tiles[:10])
    date_str = datetime.now(timezone.utc).strftime("%b %d")

    for sub in subscribers:
        try:
            resend.Emails.send({
                "from": "DailyAI <digest@dailyai.news>",
                "to": sub["email"],
                "subject": f"🤖 DailyAI Brief — {date_str}",
                "html": html,
            })
            logger.info(f"[Digest] Sent to {sub['email']}")
        except Exception as e:
            logger.warning(f"[Digest] Failed to send to {sub['email']}: {e}")
