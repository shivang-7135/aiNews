"""
DailyAI — Main Feed Page v3
Inshorts-style mobile snap-scroll, warm vibrant design,
boot loader, sidebar, and floating nav.
"""

import asyncio
import logging

from nicegui import ui

from dailyai.api.routes import get_feed
from dailyai.config import COUNTRIES, SUPPORTED_LANGUAGES, UI_TOPIC_MAP
from dailyai.ui.components.nav_bar import nav_bar, sidebar, topic_filter
from dailyai.ui.components.news_card import _inject_detail_overlay_once, news_card, skeleton_card
from dailyai.ui.components.theme import GLOBAL_CSS

logger = logging.getLogger("dailyai.home")


@ui.page('/')
async def home_page():
    ui.add_head_html(f'<style>{GLOBAL_CSS}</style>')
    ui.page_title('DailyAI — AI News Intelligence')
    ui.dark_mode(True)

    # ── Kill Quasar's inline min-height (it re-applies via Vue reactivity) ──
    ui.run_javascript('''
        function fixQuasarSpacing() {
            document.querySelectorAll('.q-layout, .q-page, .q-page-container').forEach(function(el) {
                el.style.minHeight = '0px';
                el.style.padding = '0px';
            });
        }
        fixQuasarSpacing();
        // Quasar re-applies inline styles on resize/update — watch for it
        var _qObs = new MutationObserver(function(mutations) {
            mutations.forEach(function(m) {
                if (m.type === 'attributes' && m.attributeName === 'style') {
                    var t = m.target;
                    if (t.classList.contains('q-layout') || t.classList.contains('q-page') || t.classList.contains('q-page-container')) {
                        if (parseInt(t.style.minHeight) > 10) {
                            t.style.minHeight = '0px';
                        }
                    }
                }
            });
        });
        _qObs.observe(document.getElementById('app') || document.body, {
            attributes: true, attributeFilter: ['style'], subtree: true
        });
    ''')

    # ── State ──
    app_state = {
        "topic": "Top Stories",
        "loading": True,
        "articles": [],
        "country": "GLOBAL",
        "language": "en",
        "sync_code": "",
        "personalized": False,
        "sort": "relevance",
    }

    # ── Ambient Orbs ──
    ui.html('''
        <div class="ambient-orb orb-1"></div>
        <div class="ambient-orb orb-2"></div>
        <div class="ambient-orb orb-3"></div>
    ''')

    # ── Boot Loader ──
    # ── Detail Overlay (injected once, shared by all cards) ──
    _inject_detail_overlay_once()

    ui.html('''
        <div class="boot-loader" id="bootLoader">
            <div class="boot-spinner"></div>
            <div class="boot-text">Curating your AI intelligence...</div>
        </div>
    ''')

    # ── Main Container ──
    main_col = ui.column().classes(
        'w-full max-w-screen-lg xl:max-w-screen-xl mx-auto'
        ' pb-16 relative z-10'
    ).style('gap: 0; padding-top: 0;')

    # ── Callbacks ──
    async def _set_country(country: str):
        app_state["country"] = (country or "GLOBAL").upper()
        ui.run_javascript('closeSidebar()')
        ui.notify(
            f'Region: {COUNTRIES.get(app_state["country"], app_state["country"])}',
            type='info', position='bottom',
        )
        await _load_feed(app_state["topic"])

    async def _set_language(language: str):
        app_state["language"] = (language or "en").lower()
        ui.run_javascript('closeSidebar()')
        lang_name = SUPPORTED_LANGUAGES.get(app_state["language"], app_state["language"])
        ui.notify(f'Language: {lang_name}', type='info', position='bottom')
        await _load_feed(app_state["topic"])

    async def _set_sort(sort_type: str):
        app_state["sort"] = sort_type

    async def _refresh_news():
        ui.run_javascript('closeSidebar()')
        ui.notify('Refreshing news...', type='info', position='bottom', timeout=1500)
        try:
            from dailyai.services.news import refresh_news
            await refresh_news(app_state["country"], app_state["language"])
        except Exception:
            pass
        await _load_feed(app_state["topic"])

    def _open_sidebar():
        ui.run_javascript('openSidebar()')

    async def _load_feed(topic: str = "Top Stories"):
        app_state["topic"] = topic
        if topic == "For You":
            app_state["personalized"] = True
        app_state["loading"] = True
        main_col.clear()

        with main_col:
            # ── Top Bar (scrolls with content, NOT sticky) ──
            with ui.element('div').classes('top-bar'):
                with ui.element('div').classes('top-bar-brand'):
                    ui.label('⚡').classes('top-bar-logo')
                    ui.label('DailyAI').classes('top-bar-title')
                with ui.element('div').classes('top-bar-right'):
                    mode = app_state["country"]
                    if app_state["personalized"] and app_state["sync_code"]:
                        mode = 'Personalized'
                    lang_label = app_state["language"].upper()
                    ui.label(f'{mode} · {lang_label}').style(
                        'font-size: 11px; font-weight: 600; color: var(--text-muted);'
                        ' padding: 4px 10px; border-radius: 999px;'
                        ' background: var(--bg-elevated);'
                    )

            # ── Trust Signal ──
            ui.html('''
                <div class="trust-signal">
                    🛡️ AI-curated from 50+ sources · Updated every hour
                </div>
            ''')

            # ── Topic Filter ──
            topic_filter(app_state["topic"], on_change=_load_feed)

            # ── Skeleton Loading ──
            skeleton_container = ui.column().classes('w-full px-3 sm:px-4 md:px-6').style('gap: 0;')
            with skeleton_container:
                for _ in range(3):
                    skeleton_card()

        # ── Fetch Data ──
        try:
            feed_data = await get_feed(
                topic="all" if topic in ("Top Stories", "For You") else topic,
                country=app_state["country"],
                language=app_state["language"],
                sync_code=app_state["sync_code"] if app_state["personalized"] else "",
                limit=20,
            )
            articles = feed_data.get("articles", [])
            app_state["articles"] = articles
        except Exception as e:
            articles = []
            logger.error(f"Feed load error: {e}")
            ui.notify(f"Failed to load feed: {e}", type="negative", position="bottom")

        # ── Remove Skeleton & Render Feed ──
        skeleton_container.clear()
        main_col.remove(skeleton_container)

        with main_col:
            if not articles:
                with ui.column().classes('w-full items-center justify-center py-20'):
                    ui.html('''
                        <div class="empty-state">
                            <div class="empty-icon">📭</div>
                            <div class="empty-text">
                                No articles found for this selection.<br>
                                Try changing your region or topic.
                            </div>
                        </div>
                    ''')
            else:
                # Feed container — Inshorts snap-scroll on mobile, grid on desktop
                feed_container = ui.element('div').classes(
                    'w-full feed-container feed-grid px-0 sm:px-4 md:px-6'
                ).style('gap: 0;')

                with feed_container:
                    for i, a in enumerate(articles):
                        news_card(a, index=i)

            # ── Sidebar ──
            sidebar(
                app_state=app_state,
                on_country_change=_set_country,
                on_language_change=_set_language,
                on_sort_change=_set_sort,
                on_refresh=_refresh_news,
            )

            # ── Bottom Nav ──
            nav_bar(
                active_route='/',
                on_settings=_open_sidebar,
            )

        # ── Dismiss boot loader ──
        ui.run_javascript('''
            setTimeout(function() {
                var bl = document.getElementById('bootLoader');
                if (bl) bl.classList.add('hidden');
            }, 400);
        ''')

    # ── Initial Load ──
    await _load_feed()
