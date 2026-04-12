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
from dailyai.ui.components.theme import COUNTRY_FLAGS, GLOBAL_CSS, inject_boot_loader
from dailyai.ui.i18n import normalize_ui_language, tr

logger = logging.getLogger("dailyai.home")


@ui.page("/")
async def home_page():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>")
    # Ensure iOS safe-area-inset env vars work (needed for notch + home bar)
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0,'
        ' maximum-scale=1.0, user-scalable=no, viewport-fit=cover">'
    )
    ui.page_title("DailyAI — AI News Intelligence")
    ui.dark_mode(True)

    params = ui.context.client.request.query_params
    initial_country = str(params.get("country", "GLOBAL")).upper()
    if initial_country not in COUNTRIES:
        initial_country = "GLOBAL"

    initial_language = normalize_ui_language(str(params.get("language", "en")))
    ui.page_title(f"DailyAI — {tr(initial_language, 'ai_news_intelligence')}")

    initial_topic = str(params.get("topic", "🔥 Top Stories")).strip() or "🔥 Top Stories"
    if initial_topic not in UI_FEED_TOPICS:
        initial_topic = "🔥 Top Stories"

    # ── Kill Quasar's inline min-height AND padding-top (header offset) ──
    ui.run_javascript("""
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
    """)

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
    ui.html("""
        <div class="ambient-orb orb-1"></div>
        <div class="ambient-orb orb-2"></div>
        <div class="ambient-orb orb-3"></div>
    """)

    # ── Boot Loader ──
    # ── Detail Overlay (injected once, shared by all cards) ──
    _inject_detail_overlay_once(language=initial_language)

    inject_boot_loader(initial_language)

    # ── Main Container ──
    main_col = (
        ui.column()
        .classes("w-full max-w-screen-lg xl:max-w-screen-xl mx-auto pb-14 relative z-10")
        .style("gap: 0; padding-top: 0;")
    )

    # ── Callbacks ──
    def _build_reload_query() -> str:
        return urlencode(
            {
                "country": app_state["country"],
                "language": app_state["language"],
                "topic": app_state["topic"],
            }
        )

    def _safe_run_javascript(code: str) -> None:
        try:
            ui.run_javascript(code)
        except RuntimeError as e:
            logger.debug(f"Skipped JS call on disposed page context: {e}")

    def _sync_url_state() -> None:
        query = _build_reload_query()
        _safe_run_javascript(f"window.history.replaceState(null, '', '/?{query}')")

    def _normalize_country_selection(country: str) -> str:
        raw = str(country or "GLOBAL").strip()
        raw_upper = raw.upper()
        if raw_upper in COUNTRIES:
            return raw_upper
        for code, name in COUNTRIES.items():
            name_lower = name.lower()
            if raw.lower() == name_lower or raw.lower().endswith(name_lower):
                return code
        return "GLOBAL"

    def _normalize_language_selection(language: str) -> str:
        raw = str(language or "en").strip().lower()
        if raw in UI_LANGUAGES:
            return raw
        for code, label in UI_LANGUAGES.items():
            if raw == str(label).strip().lower():
                return code
        return "en"

    async def _set_country(country):
        """Handle country change — hard reload to cleanly swap state."""
        selected_country = _normalize_country_selection(str(country))
        if selected_country == app_state["country"]:
            _safe_run_javascript("closeSidebar()")
            return

        country_name = COUNTRIES.get(selected_country, selected_country)
        flag = COUNTRY_FLAGS.get(selected_country, "🌐")
        ui.notify(
            tr(app_state["language"], "region_notify", flag=flag, country=country_name),
            type="info",
            position="bottom",
        )

        app_state["country"] = selected_country
        query = _build_reload_query()
        _safe_run_javascript("""
            closeSidebar();
            var bl = document.getElementById('bootLoader');
            if (bl) bl.classList.remove('hidden');
        """)
        ui.navigate.to(f"/?{query}")

    async def _set_language(language):
        """Handle language change — hard reload to cleanly swap state."""
        selected_language = _normalize_language_selection(str(language))
        if selected_language == app_state["language"]:
            _safe_run_javascript("closeSidebar()")
            return

        app_state["language"] = selected_language
        lang_name = UI_LANGUAGES.get(selected_language, selected_language)
        ui.notify(
            tr(selected_language, "language_notify", language=lang_name),
            type="info",
            position="bottom",
        )

        query = _build_reload_query()

        def _js_str(text: str) -> str:
            return str(text or "").replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

        _safe_run_javascript(f"""
            closeSidebar();
            var bl = document.getElementById('bootLoader');
            if (bl) {{
                var txt = bl.querySelector('.boot-text');
                if (txt) txt.innerText = '{_js_str(tr(selected_language, "boot_loader"))}';
                bl.classList.remove('hidden');
            }}
        """)
        ui.navigate.to(f"/?{query}")

    async def _set_sort(sort_type: str):
        app_state["sort"] = sort_type
        ui.run_javascript("closeSidebar()")
        await _load_feed(app_state["topic"])

    async def _refresh_news():
        _safe_run_javascript("closeSidebar()")
        ui.notify(
            tr(app_state["language"], "refreshing_news"),
            type="info",
            position="bottom",
            timeout=1500,
        )
        try:
            from dailyai.services.news import refresh_news

            await refresh_news(app_state["country"], app_state["language"])
        except Exception:
            pass
        await _load_feed(app_state["topic"])

    def _open_sidebar():
        _safe_run_javascript("openSidebar()")

    async def _load_feed(topic: str = "🔥 Top Stories"):
        app_state["topic"] = topic
        app_state["personalized"] = topic == "For You"
        app_state["loading"] = True
        main_col.clear()

        with main_col:
            # ── Fixed Top Shell (title + locale + categories) ──
            with ui.element("div").classes("top-fixed-shell w-full"):
                with ui.element("div").classes("top-bar w-full"):
                    ui.label(tr(app_state["language"], "discover")).classes("top-bar-title")

                    country_name = COUNTRIES.get(app_state["country"], app_state["country"])
                    language_display = {
                        "en": "English",
                        "de": "Deutsch",
                    }.get(app_state["language"], app_state["language"])
                    ui.label(f"{country_name}, {language_display}").classes("top-bar-subline")

                with ui.element("div").classes("topic-rail w-full"):
                    topic_filter(
                        app_state["topic"], on_change=_load_feed, language=app_state["language"]
                    )

            # ── Skeleton Loading ──
            skeleton_container = ui.column().classes("w-full px-3 sm:px-4 md:px-6").style("gap: 0;")
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
                sort=app_state.get("sort", "relevance"),
            )
            articles = feed_data.get("articles", [])
            app_state["articles"] = articles
            app_state["total"] = int(feed_data.get("total", len(articles)))
            app_state["has_more"] = bool(feed_data.get("has_more", False))
            app_state["synthesis"] = feed_data.get("synthesis", "")
        except Exception as e:
            articles = []
            app_state["total"] = 0
            app_state["has_more"] = False
            app_state["synthesis"] = ""
            logger.error(f"Feed load error: {e}")
            ui.notify(
                tr(app_state["language"], "failed_feed", error=e),
                type="negative",
                position="bottom",
            )

        # ── Remove Skeleton & Render Feed ──
        skeleton_container.clear()
        main_col.remove(skeleton_container)

        with main_col:
            if not articles:
                # Show a helpful "still loading" message instead of just "no articles"
                with ui.column().classes("w-full items-center justify-center py-20"):
                    ui.html(
                        """
                        <div class="empty-state">
                            <div class="empty-icon">⏳</div>
                            <div class="empty-text">
                                """
                        + tr(app_state["language"], "empty_wait")
                        + """<br>
                                """
                        + tr(app_state["language"], "empty_warmup")
                        + """
                            </div>
                        </div>
                    """
                    )
            else:
                if app_state.get("synthesis") and app_state["topic"] == "For You":
                    with ui.element("div").classes("synthesis-banner"):
                        with ui.element("div").classes("synthesis-header"):
                            ui.html(
                                '<span class="material-icons" style="font-size: 16px;">auto_awesome</span>'
                            )
                            ui.label("Your Daily Briefing")
                        ui.label(app_state["synthesis"]).classes("synthesis-content")

                # Feed container — Inshorts snap-scroll on mobile, grid on desktop
                feed_container = (
                    ui.element("div")
                    .classes("w-full feed-container feed-grid px-0 sm:px-4 md:px-6")
                    .style("gap: 0;")
                )
                load_more_container = ui.element("div").classes(
                    "w-full flex flex-col items-center justify-center py-4 gap-2"
                )

                async def _load_more_page():
                    if app_state["loading_more"] or not app_state.get("has_more"):
                        return

                    app_state["loading_more"] = True
                    load_more_container.clear()
                    with load_more_container:
                        ui.label(tr(app_state["language"], "loading_more")).style(
                            "font-size: 12px; color: var(--text-muted);"
                        )

                    try:
                        next_feed = await get_feed(
                            topic="all" if topic in ("🔥 Top Stories", "For You") else topic,
                            country=app_state["country"],
                            language=app_state["language"],
                            sync_code=app_state["sync_code"] if app_state["personalized"] else "",
                            offset=len(app_state["articles"]),
                            limit=app_state["page_limit"],
                            sort=app_state.get("sort", "relevance"),
                        )
                        new_articles = next_feed.get("articles", [])

                        if new_articles:
                            start_index = len(app_state["articles"])
                            app_state["articles"].extend(new_articles)
                            app_state["total"] = int(next_feed.get("total", app_state["total"]))
                            app_state["has_more"] = bool(next_feed.get("has_more", False))

                            with feed_container:
                                overall_total = max(len(app_state["articles"]), app_state["total"])
                                for i, article in enumerate(new_articles):
                                    news_card(
                                        article,
                                        index=start_index + i,
                                        position_chip=f"{start_index + i + 1}/{overall_total}",
                                        language=app_state["language"],
                                    )
                        else:
                            app_state["has_more"] = False
                    except Exception as e:
                        logger.error(f"Load more failed: {e}")
                        ui.notify(
                            tr(app_state["language"], "failed_more", error=e),
                            type="negative",
                            position="bottom",
                        )
                    finally:
                        app_state["loading_more"] = False
                        load_more_container.clear()

                        if app_state.get("has_more"):
                            with load_more_container:
                                ui.label(
                                    tr(
                                        app_state["language"],
                                        "loaded_progress",
                                        loaded=len(app_state["articles"]),
                                        total=app_state["total"],
                                    )
                                ).style("font-size: 11px; color: var(--text-muted);")
                                ui.button(
                                    tr(app_state["language"], "load_more"), on_click=_load_more_page
                                ).classes("px-4 py-2 rounded-lg").style(
                                    "background: var(--bg-elevated); color: var(--text-primary);"
                                )

                with feed_container:
                    page_total = max(1, app_state.get("total", len(articles)) or len(articles))
                    for i, a in enumerate(articles):
                        news_card(
                            a,
                            index=i,
                            position_chip=f"{i + 1}/{page_total}",
                            language=app_state["language"],
                        )

                if app_state.get("has_more"):
                    with load_more_container:
                        ui.label(
                            tr(
                                app_state["language"],
                                "loaded_progress",
                                loaded=len(app_state["articles"]),
                                total=app_state["total"],
                            )
                        ).style("font-size: 11px; color: var(--text-muted);")
                        ui.button(
                            tr(app_state["language"], "load_more"), on_click=_load_more_page
                        ).classes("px-4 py-2 rounded-lg").style(
                            "background: var(--bg-elevated); color: var(--text-primary);"
                        )

        # ── Dismiss boot loader ──
        _safe_run_javascript("""
            setTimeout(function() {
                var bl = document.getElementById('bootLoader');
                if (bl) bl.classList.add('hidden');
            }, 400);
        """)

    # ── Sidebar & Nav (created once, outside main_col so they survive feed reloads) ──
    sidebar(
        app_state=app_state,
        on_country_change=_set_country,
        on_language_change=_set_language,
        on_sort_change=_set_sort,
        on_refresh=_refresh_news,
        language=app_state["language"],
    )

    nav_bar(
        active_route="/",
        on_settings=_open_sidebar,
        language=app_state["language"],
        country=app_state["country"],
    )

    # ── Initial Load ──
    try:
        await ui.context.client.connected()
        sync_code = await ui.run_javascript(
            'return localStorage.getItem("dailyai_sync_code") || "";', timeout=2.0
        )

        is_first_visit = False
        if not sync_code:
            # Auto-generate a sync code for anonymous personalization
            from dailyai.services.profiles import create_profile

            profile = await create_profile(
                [], country=app_state["country"], language=app_state["language"]
            )
            sync_code = profile.get("sync_code", "")
            if sync_code:
                ui.run_javascript(f'localStorage.setItem("dailyai_sync_code", "{sync_code}");')
                is_first_visit = True

        if sync_code:
            app_state["sync_code"] = str(sync_code)

        if is_first_visit:
            from dailyai.ui.components.onboarding import onboarding_dialog

            dialog = onboarding_dialog(app_state["language"], sync_code)
            dialog.open()

    except Exception:
        logger.debug("Failed to retrieve sync_code from client before initial load")

    await _load_feed(app_state["topic"])
