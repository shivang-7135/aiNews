"""
DailyAI — Article Detail Page
"""

from nicegui import ui

from dailyai.api.routes import get_feed
from dailyai.ui.components.theme import GLOBAL_CSS


@ui.page("/article/{article_id}")
async def article_page(article_id: str):
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>")
    ui.page_title("DailyAI — Article")
    ui.dark_mode(True)

    parts = article_id.split("-")
    country = parts[0] if len(parts) >= 3 else "GLOBAL"
    language = parts[1] if len(parts) >= 3 else "en"

    article = None
    params = ui.context.client.request.query_params
    try:
        feed = await get_feed(country=country, language=language, limit=30)
        for item in feed.get("articles", []):
            if item.get("id") == article_id:
                article = item
                break
    except Exception as e:
        ui.notify(f"Failed to load article: {e}", type="negative")

    if params:
        query_article = {
            "id": article_id,
            "headline": params.get("headline", ""),
            "summary": params.get("summary", ""),
            "why_it_matters": params.get("why_it_matters", ""),
            "topic": params.get("topic", "Top Stories"),
            "source_name": params.get("source_name", "Unknown"),
            "source_trust": params.get("source_trust", "low"),
            "sentiment": params.get("sentiment", "neutral"),
            "article_url": params.get("article_url", "#"),
            "published_at": params.get("published_at", ""),
        }
        if article is None:
            article = query_article
        else:
            # Prefer clicked-card payload values when present.
            for field in (
                "headline",
                "summary",
                "why_it_matters",
                "topic",
                "source_name",
                "source_trust",
                "sentiment",
                "article_url",
                "published_at",
            ):
                value = str(query_article.get(field, "") or "").strip()
                if value:
                    article[field] = value

    if article is not None:
        article["summary"] = _short_summary(article)

    with ui.column().classes("w-full max-w-3xl mx-auto min-h-screen pb-24 sm:pb-28 px-4 pt-6"):
        with ui.row().classes("w-full items-center justify-between mb-4"):
            with ui.button(on_click=lambda: ui.navigate.to("/")).props("flat color=white"):
                ui.icon("arrow_back").style("color: var(--accent)")
                ui.label("Back to Feed").style("color: var(--accent)")
            source_url = article.get("article_url", "#") if article else "#"
            ui.button(
                "Open Source", on_click=lambda: ui.navigate.to(source_url, new_tab=True)
            ).props("flat color=accent icon=open_in_new")

        if not article:
            with ui.column().classes("w-full items-center justify-center py-20 opacity-70"):
                ui.icon("error_outline", size="52px").classes("mb-4").style(
                    "color: var(--text-muted)"
                )
                ui.label("Article not found. It may have expired from the current feed.").classes(
                    "text-secondary text-center"
                )
        else:
            with ui.card().classes("w-full glass-card p-6"):
                ui.label(article.get("topic", "Top Stories")).classes(
                    "text-[11px] font-black tracking-wider text-accent mb-2"
                )
                ui.label(article.get("headline", "")).classes(
                    "text-2xl md:text-3xl font-black leading-tight mb-3"
                )
                ui.label(article.get("summary", "")).classes(
                    "text-[15px] text-secondary leading-relaxed mb-4"
                )

                why = article.get("why_it_matters", "").strip()
                if why:
                    with ui.column().classes(
                        "w-full bg-elevated/50 p-4 rounded border border-light mb-5"
                    ):
                        ui.label("Why it matters").classes(
                            "text-[12px] font-bold text-accent uppercase tracking-wider mb-1"
                        )
                        ui.label(why).classes("text-sm text-primary italic")

                with ui.row().classes(
                    "w-full justify-between text-[12px] text-muted gap-4 flex-wrap"
                ):
                    ui.label(f"Source: {article.get('source_name', 'Unknown')}")
                    ui.label(f"Trust: {article.get('source_trust', 'low')}")
                    ui.label(f"Sentiment: {article.get('sentiment', 'neutral')}")


def _short_summary(article: dict) -> str:
    summary = str(article.get("summary", "") or "").strip()
    if summary:
        return summary

    why = str(article.get("why_it_matters", "") or "").strip()
    if why:
        return why

    source = str(article.get("source_name", "") or "Unknown source").strip()
    return f"Reported by {source}. Tap Open Source to read the full article."
