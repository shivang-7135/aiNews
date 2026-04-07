"""
DailyAI — Main Feed Page v4
Inshorts-style mobile snap-scroll, warm vibrant design,
boot loader, sidebar, and floating nav.
Server-first architecture: frontend only reads from DB.
"""

import logging
from urllib.parse import urlencode

from nicegui import ui

from dailyai.api.routes import get_feed
from dailyai.config import COUNTRIES, UI_FEED_TOPICS, UI_LANGUAGES
from dailyai.ui.components.nav_bar import nav_bar, sidebar, topic_filter
from dailyai.ui.components.news_card import _inject_detail_overlay_once, news_card, skeleton_card
from dailyai.ui.components.theme import COUNTRY_FLAGS, GLOBAL_CSS

logger = logging.getLogger("dailyai.home")


@ui.page('/')
async def home_page():
    ui.add_head_html(f'<style>{GLOBAL_CSS}</style>')
    # Ensure iOS safe-area-inset env vars work (needed for notch + home bar)
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0,'
        ' maximum-scale=1.0, user-scalable=no, viewport-fit=cover">'
    )
    ui.page_title('DailyAI — AI News Intelligence')
    ui.dark_mode(True)

    params = ui.context.client.request.query_params
    initial_country = str(params.get('country', 'GLOBAL')).upper()
    if initial_country not in COUNTRIES:
        initial_country = 'GLOBAL'

    initial_language = str(params.get('language', 'en')).lower()
    if initial_language not in UI_LANGUAGES:
        initial_language = 'en'

    initial_topic = str(params.get('topic', '🔥 Top Stories')).strip() or '🔥 Top Stories'
    if initial_topic not in UI_FEED_TOPICS:
        initial_topic = '🔥 Top Stories'

    # ── Kill Quasar's inline min-height AND padding-top (header offset) ──
    ui.run_javascript('''
        function fixQuasarSpacing() {
            document.querySelectorAll('.q-layout, .q-page, .q-page-container').forEach(function(el) {
                el.style.minHeight = '0px';
                el.style.padding = '0px';
                el.style.paddingTop = '0px';
            });
        }
        fixQuasarSpacing();
        // Quasar re-applies inline styles on resize/update — watch & kill
        var _qObs = new MutationObserver(function(mutations) {
            mutations.forEach(function(m) {
                if (m.type === 'attributes' && m.attributeName === 'style') {
                    var t = m.target;
                    if (t.classList.contains('q-layout') || t.classList.contains('q-page') || t.classList.contains('q-page-container')) {
                        if (parseInt(t.style.minHeight) > 10) t.style.minHeight = '0px';
                        if (parseInt(t.style.paddingTop) > 0) t.style.paddingTop = '0px';
                        if (parseInt(t.style.padding) > 0) t.style.padding = '0px';
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
        "topic": initial_topic,
        "loading": True,
        "articles": [],
        "total": 0,
        "has_more": False,
        "loading_more": False,
        "country": initial_country,
        "language": initial_language,
        "sync_code": "",
        "personalized": False,
        "sort": "relevance",
        "page_limit": 15,
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
    def _build_reload_query() -> str:
        return urlencode({
            'country': app_state["country"],
            'language': app_state["language"],
            'topic': app_state["topic"],
        })

    def _reload_page_with_state() -> None:
        query = _build_reload_query()
        ui.run_javascript(f"window.location.href='/?{query}'")

    async def _set_country(country):
        """Handle country change — expects a plain string value from ui.select."""
        selected_country = (str(country) or "GLOBAL").upper()
        if selected_country not in COUNTRIES:
            selected_country = "GLOBAL"
        app_state["country"] = selected_country
        ui.run_javascript('closeSidebar()')
        country_name = COUNTRIES.get(selected_country, selected_country)
        flag = COUNTRY_FLAGS.get(selected_country, "🌐")
        ui.notify(
            f'Region: {flag} {country_name}',
            type='info', position='bottom',
        )
        _reload_page_with_state()

    async def _set_language(language):
        """Handle language change — expects a plain string value from ui.select."""
        selected_language = (str(language) or "en").lower()
        if selected_language not in UI_LANGUAGES:
            selected_language = 'en'
        app_state["language"] = selected_language
        ui.run_javascript('closeSidebar()')
        lang_name = UI_LANGUAGES.get(selected_language, selected_language)
        ui.notify(f'Language: {lang_name}', type='info', position='bottom')
        _reload_page_with_state()

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

    async def _load_feed(topic: str = "🔥 Top Stories"):
        app_state["topic"] = topic
        app_state["personalized"] = topic == "For You"
        app_state["loading"] = True
        main_col.clear()

        with main_col:
            # ── Top Bar (scrolls with content, NOT sticky) ──
            with ui.element('div').classes('top-bar'):
                with ui.element('div').classes('top-bar-brand'):
                    ui.html('<img src="/static/logo.png" class="top-bar-logo-img" alt="DailyAI">')
                    ui.label('DailyAI').classes('top-bar-title')
                with ui.element('div').classes('top-bar-right'):
                    country_name = COUNTRIES.get(app_state["country"], app_state["country"])
                    flag = COUNTRY_FLAGS.get(app_state["country"], "🌐")
                    lang_name = UI_LANGUAGES.get(app_state["language"], app_state["language"]).upper()
                    ui.label(f'{flag} {country_name} · {lang_name}').style(
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

        # ── Fetch Data (READ ONLY from DB — no LLM calls) ──
        try:
            feed_data = await get_feed(
                topic="all" if topic in ("🔥 Top Stories", "For You") else topic,
                country=app_state["country"],
                language=app_state["language"],
                sync_code=app_state["sync_code"] if app_state["personalized"] else "",
                limit=app_state["page_limit"],
            )
            articles = feed_data.get("articles", [])
            app_state["articles"] = articles
            app_state["total"] = int(feed_data.get("total", len(articles)))
            app_state["has_more"] = bool(feed_data.get("has_more", False))
        except Exception as e:
            articles = []
            app_state["total"] = 0
            app_state["has_more"] = False
            logger.error(f"Feed load error: {e}")
            ui.notify(f"Failed to load feed: {e}", type="negative", position="bottom")

        # ── Remove Skeleton & Render Feed ──
        skeleton_container.clear()
        main_col.remove(skeleton_container)

        with main_col:
            if not articles:
                # Show a helpful "still loading" message instead of just "no articles"
                with ui.column().classes('w-full items-center justify-center py-20'):
                    ui.html('''
                        <div class="empty-state">
                            <div class="empty-icon">⏳</div>
                            <div class="empty-text">
                                News is being curated by our AI...<br>
                                The server is warming up. Please refresh in a moment.
                            </div>
                        </div>
                    ''')
            else:
                # Feed container — Inshorts snap-scroll on mobile, grid on desktop
                feed_container = ui.element('div').classes(
                    'w-full feed-container feed-grid px-0 sm:px-4 md:px-6'
                ).style('gap: 0;')
                load_more_container = ui.element('div').classes(
                    'w-full flex flex-col items-center justify-center py-4 gap-2'
                )

                async def _load_more_page():
                    if app_state["loading_more"] or not app_state.get("has_more"):
                        return

                    app_state["loading_more"] = True
                    load_more_container.clear()
                    with load_more_container:
                        ui.label('Loading more stories...').style('font-size: 12px; color: var(--text-muted);')

                    try:
                        next_feed = await get_feed(
                            topic="all" if topic in ("🔥 Top Stories", "For You") else topic,
                            country=app_state["country"],
                            language=app_state["language"],
                            sync_code=app_state["sync_code"] if app_state["personalized"] else "",
                            offset=len(app_state["articles"]),
                            limit=app_state["page_limit"],
                        )
                        new_articles = next_feed.get("articles", [])

                        if new_articles:
                            start_index = len(app_state["articles"])
                            app_state["articles"].extend(new_articles)
                            app_state["total"] = int(next_feed.get("total", app_state["total"]))
                            app_state["has_more"] = bool(next_feed.get("has_more", False))

                            with feed_container:
                                batch_total = max(1, len(new_articles))
                                for i, article in enumerate(new_articles):
                                    news_card(
                                        article,
                                        index=start_index + i,
                                        position_chip=f'{i + 1}/{batch_total}',
                                    )
                        else:
                            app_state["has_more"] = False
                    except Exception as e:
                        logger.error(f"Load more failed: {e}")
                        ui.notify(f"Failed to load more stories: {e}", type='negative', position='bottom')
                    finally:
                        app_state["loading_more"] = False
                        load_more_container.clear()

                        if app_state.get("has_more"):
                            with load_more_container:
                                ui.label(
                                    f'{len(app_state["articles"])} of {app_state["total"]} loaded'
                                ).style('font-size: 11px; color: var(--text-muted);')
                                ui.button('Load More', on_click=_load_more_page).classes(
                                    'px-4 py-2 rounded-lg'
                                ).style('background: var(--bg-elevated); color: var(--text-primary);')

                with feed_container:
                    page_total = max(1, len(articles))
                    for i, a in enumerate(articles):
                        news_card(a, index=i, position_chip=f'{i + 1}/{page_total}')

                if app_state.get("has_more"):
                    with load_more_container:
                        ui.label(
                            f'{len(app_state["articles"])} of {app_state["total"]} loaded'
                        ).style('font-size: 11px; color: var(--text-muted);')
                        ui.button('Load More', on_click=_load_more_page).classes(
                            'px-4 py-2 rounded-lg'
                        ).style('background: var(--bg-elevated); color: var(--text-primary);')

        # ── Dismiss boot loader ──
        ui.run_javascript('''
            setTimeout(function() {
                var bl = document.getElementById('bootLoader');
                if (bl) bl.classList.add('hidden');
            }, 400);
        ''')

    # ── Sidebar & Nav (created once, outside main_col so they survive feed reloads) ──
    sidebar(
        app_state=app_state,
        on_country_change=_set_country,
        on_language_change=_set_language,
        on_sort_change=_set_sort,
        on_refresh=_refresh_news,
    )

    nav_bar(
        active_route='/',
        on_settings=_open_sidebar,
    )

    # ── Initial Load ──
    await _load_feed(app_state["topic"])
