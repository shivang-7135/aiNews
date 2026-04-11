"""
DailyAI — Article Detail Page
"""

import json
from contextlib import suppress

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


@ui.page("/s/{share_id}")
async def shortlink_landing(share_id: str):
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>")
    ui.page_title("DailyAI — Bridging...")
    ui.dark_mode(True)

    from dailyai.storage.backend import get_metadata

    data_str = await get_metadata(f"share:{share_id}")
    data = None
    if data_str:
        with suppress(Exception):
            data = json.loads(data_str)

    if not data:
        with ui.column().classes("w-full items-center justify-center min-h-screen py-20 opacity-70"):
            ui.icon("broken_image", size="52px").classes("mb-4").style("color: var(--text-muted)")
            ui.label("Link expired or invalid.").classes("text-secondary text-center")
            ui.button("Go to DailyAI", on_click=lambda: ui.navigate.to("/")).props("outline color=accent mt-4")
        return
        
    url = data.get("url", "/")
    title = data.get("title", "")
    source = data.get("source", "")
    
    ui.add_head_html("""
        <style>
        @keyframes pulse-glow {
            0% { box-shadow: 0 0 0 0 rgba(255, 184, 0, 0.4); }
            70% { box-shadow: 0 0 0 20px rgba(255, 184, 0, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 184, 0, 0); }
        }
        .splash-card {
            background: rgba(26, 29, 38, 0.65);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 184, 0, 0.15);
            border-radius: 24px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
        .splash-progress {
            height: 4px; border-radius: 2px; background: rgba(255,255,255,0.1); overflow: hidden; position: relative;
        }
        .splash-progress::after {
            content: ''; position: absolute; top:0; left:0; height:100%; width:0%;
            background: linear-gradient(90deg, #FFB800, #FF5500);
            border-radius: 2px;
            animation: progress-fill 2.5s cubic-bezier(0.1, 0.7, 0.1, 1) forwards;
        }
        @keyframes progress-fill {
            to { width: 100%; }
        }
        .shimmer-text {
            background: linear-gradient(90deg, #FFB800, #FFF, #FFB800);
            background-size: 200% auto;
            color: transparent;
            -webkit-background-clip: text;
            background-clip: text;
            animation: text-shimmer 3s linear infinite;
        }
        @keyframes text-shimmer {
            to { background-position: 200% center; }
        }
        </style>
    """)
    
    with ui.column().classes("w-full min-h-screen items-center justify-center p-4 bg-gradient-to-br from-[#0f111a] via-[#1a1d26] to-[#0a0a0f] relative overflow-hidden"):
        # Decorative blur orbs
        ui.label("").classes("absolute top-[-20%] left-[-10%] w-96 h-96 bg-accent opacity-10 rounded-full blur-[100px] pointer-events-none")
        ui.label("").classes("absolute bottom-[-20%] right-[-10%] w-96 h-96 bg-primary opacity-[0.03] rounded-full blur-[100px] pointer-events-none")
        
        with ui.column().classes("splash-card w-full max-w-[420px] p-8 md:p-10 items-center text-center transform transition-all duration-700 hover:scale-[1.02]"):
            
            # Logo / Brand
            with ui.row().classes("items-center justify-center gap-3 mb-8 w-full"):
                ui.icon("bolt", size="28px").classes("text-accent").style("animation: pulse-glow 2s infinite; border-radius: 50%;")
                ui.label("DailyAI").classes("text-2xl font-black text-white tracking-widest uppercase")
            
            # News Details
            if source:
                ui.label(source).classes("text-[10px] font-bold text-accent uppercase tracking-[0.2em] mb-3 px-3 py-1 border border-accent/30 rounded-full bg-accent/10")
            
            if title:
                ui.label(title).classes("text-[22px] md:text-2xl font-bold text-white leading-[1.3] mb-8 line-clamp-4 max-w-sm")
            
            # Progress visualization
            with ui.column().classes("w-full mb-6"):
                ui.html("<div class='splash-progress w-full'></div>")
                
            ui.label("Bridging to original source...").classes("text-xs font-medium shimmer-text tracking-widest uppercase mb-6")
            
            ui.button("Jump Now", on_click=lambda: ui.navigate.to(url)).props("flat rounded color=white").classes(
                "w-full bg-white/5 hover:bg-white/10 text-white font-bold tracking-wider transition-colors duration-300"
            )
        
    ui.add_head_html(f'''
        <script>
            setTimeout(function() {{ window.location.href = "{url}"; }}, 2500);
        </script>
        <noscript>
            <meta http-equiv="refresh" content="2;url={url}">
        </noscript>
    ''')
