"""
DailyAI — Navigation & Sidebar Components v4
Floating glass bottom nav dock + slide-in sidebar.
Uses NiceGUI ui.select for reliable dropdown handling.
"""

import asyncio
from urllib.parse import urlencode

from nicegui import ui

from dailyai.config import COUNTRIES, UI_FEED_TOPICS, UI_LANGUAGES
from dailyai.ui.components.theme import COUNTRY_FLAGS
from dailyai.ui.i18n import normalize_ui_language, tr


def nav_bar(
    active_route: str = "/",
    on_settings: callable = None,
    on_saved: callable = None,
    language: str = "en",
    country: str = "GLOBAL",
):
    """Floating glass bottom navigation dock — always visible."""

    lang = normalize_ui_language(language)
    query = urlencode({"country": country, "language": lang})
    discover_route = f'/?{query}'
    saved_route = f'/saved?{query}'
    settings_route = f'/settings?{query}'

    with ui.row().classes('bottom-nav'), ui.element('div').classes('bottom-nav-inner'):
        _nav_btn(
            icon='explore', label=tr(lang, 'discover'),
            active=active_route == '/',
            on_click=lambda: ui.navigate.to(discover_route),
        )
        _nav_btn(
            icon='bookmark', label=tr(lang, 'saved'),
            active=active_route == '/saved',
            on_click=on_saved or (lambda: ui.navigate.to(saved_route)),
        )
        _nav_btn(
            icon='tune', label=tr(lang, 'settings'),
            active=active_route == '/settings',
            on_click=on_settings or (lambda: ui.navigate.to(settings_route)),
        )


def _nav_btn(icon: str, label: str, active: bool, on_click=None, is_fab=False):
    classes = 'nav-btn'
    if is_fab:
        classes += ' nav-btn-fab'
    if active:
        classes += ' active'
    btn = ui.element('button').classes(classes)
    with btn:
        ui.icon(icon, size='20px')
        ui.label(label)
    if on_click:
        btn.on('click', lambda e: on_click() if not asyncio.iscoroutinefunction(on_click) else asyncio.create_task(on_click()))


def sidebar(
    app_state: dict,
    on_country_change=None,
    on_language_change=None,
    on_sort_change=None,
    on_refresh=None,
    on_close=None,
    language: str = "en",
):
    """Slide-in settings sidebar."""
    lang = normalize_ui_language(language)
    ui.add_head_html('''
    <script>
    function openSidebar() {
        document.getElementById('sidebarBackdrop')?.classList.add('show');
        document.getElementById('sidebarPanel')?.classList.add('show');
    }
    function closeSidebar() {
        document.getElementById('sidebarBackdrop')?.classList.remove('show');
        document.getElementById('sidebarPanel')?.classList.remove('show');
    }
    </script>
    ''')

    backdrop = ui.element('div').classes('sidebar-backdrop')
    backdrop.props('id=sidebarBackdrop')
    backdrop.on('click', lambda: ui.run_javascript('closeSidebar()'))

    panel = ui.element('div').classes('sidebar-panel')
    panel.props('id=sidebarPanel')
    with panel:
        # Header
        with ui.element('div').classes('sidebar-section').style(
            'display: flex; align-items: center; justify-content: space-between;'
        ):
            with ui.row().classes('items-center gap-2'):
                ui.label('⚡').style('font-size: 24px;')
                with ui.column().classes('gap-0'):
                    ui.label('DailyAI').style(
                        'font-size: 18px; font-weight: 800; letter-spacing: -0.02em;'
                        ' color: var(--text-primary); line-height: 1;'
                    )
                    ui.label(tr(lang, 'ai_news_intelligence')).style(
                        'font-size: 10px; font-weight: 600; color: var(--text-muted);'
                        ' letter-spacing: 0.06em; text-transform: uppercase;'
                    )
            close_btn = ui.element('button').classes('sidebar-close')
            with close_btn:
                ui.html('&#10005;')
            close_btn.on('click', lambda: ui.run_javascript('closeSidebar()'))

        # Region — using NiceGUI ui.select for reliable event handling
        with ui.element('div').classes('sidebar-section'):
            ui.html(f'<div class="sidebar-section-title">🌍 {tr(lang, "region")}</div>')
            country_options = {
                code: f"{COUNTRY_FLAGS.get(code, '🏳️')} {name}"
                for code, name in COUNTRIES.items()
            }
            current_country = app_state.get("country", "GLOBAL")

            country_select = ui.select(
                options=country_options,
                value=current_country,
                label=None,
            ).classes('sidebar-nicegui-select w-full').props('dark dense outlined')

            if on_country_change:
                async def _on_country(e):
                    val = e.value if hasattr(e, 'value') else str(e)
                    if asyncio.iscoroutinefunction(on_country_change):
                        await on_country_change(val)
                    else:
                        on_country_change(val)
                country_select.on_value_change(_on_country)

        # Language — using NiceGUI ui.select for reliable event handling
        with ui.element('div').classes('sidebar-section'):
            ui.html(f'<div class="sidebar-section-title">🌐 {tr(lang, "language")}</div>')
            current_lang = app_state.get("language", "en")
            language_options = (
                {"en": "Englisch", "de": "Deutsch"}
                if lang == "de"
                else UI_LANGUAGES
            )

            lang_select = ui.select(
                options=language_options,
                value=current_lang,
                label=None,
            ).classes('sidebar-nicegui-select w-full').props('dark dense outlined')

            if on_language_change:
                async def _on_language(e):
                    val = e.value if hasattr(e, 'value') else str(e)
                    if asyncio.iscoroutinefunction(on_language_change):
                        await on_language_change(val)
                    else:
                        on_language_change(val)
                lang_select.on_value_change(_on_language)

        # Sort
        with ui.element('div').classes('sidebar-section'):
            ui.html(f'<div class="sidebar-section-title">📊 {tr(lang, "sort_by")}</div>')
            current_sort = app_state.get("sort", "relevance")
            with ui.element('div').classes('sort-group'):
                rel_btn = ui.element('button').classes(
                    f'sort-btn {"active" if current_sort == "relevance" else ""}'
                )
                with rel_btn:
                    ui.html(tr(lang, 'relevance'))
                rel_btn.props('id=sortRelevance')
                lat_btn = ui.element('button').classes(
                    f'sort-btn {"active" if current_sort == "latest" else ""}'
                )
                with lat_btn:
                    ui.html(tr(lang, 'latest'))
                lat_btn.props('id=sortLatest')
            if on_sort_change:
                async def _sort_relevance(e):
                    await _handle_sort('relevance', on_sort_change)
                async def _sort_latest(e):
                    await _handle_sort('latest', on_sort_change)
                rel_btn.on('click', _sort_relevance)
                lat_btn.on('click', _sort_latest)

        # Sync Code
        with ui.element('div').classes('sidebar-section'):
            ui.html(f'<div class="sidebar-section-title">🔄 {tr(lang, "sync_code", fallback="Sync Code")}</div>')
            ui.label(tr(lang, "sync_code_desc", fallback="Use this code to sync your personalization across devices.")).style("font-size: 11px; color: var(--text-muted); margin-bottom: 8px;")
            
            with ui.row().classes("w-full items-center justify-between p-2 mb-4").style("background: var(--bg-card); border-radius: 8px; border: 1px solid var(--border-ghost);"):
                current_code_label = ui.label("Loading...").style("font-size: 13px; font-weight: 700; letter-spacing: 0.05em; color: var(--text-primary);")
                ui.button(icon="content_copy", on_click=lambda: ui.run_javascript('navigator.clipboard.writeText(localStorage.getItem("dailyai_sync_code") || "");') or ui.notify("Copied!")).props("flat round dense color=primary").tooltip("Copy")

            ui.label("Switch Sync Code").style("font-size: 12px; font-weight: bold; margin-bottom: 4px;")
            sync_code_input = ui.input(placeholder="Enter existing code...").classes("w-full").props("dark outlined dense clearable")
            
            async def _apply_code():
                new_code = str(sync_code_input.value or "").strip()
                if new_code:
                    ui.run_javascript(f'localStorage.setItem("dailyai_sync_code", "{new_code}");')
                    current_code_label.set_text(new_code)
                    sync_code_input.value = ""
                    ui.notify("Sync code updated!", type="positive")
                    ui.run_javascript('closeSidebar()')
                    if on_refresh:
                        if asyncio.iscoroutinefunction(on_refresh):
                            await on_refresh()
                        else:
                            on_refresh()
                    else:
                        ui.navigate.to(f'/?{urlencode({"country": current_country, "language": current_lang})}')

            ui.button("Apply Code", on_click=_apply_code).classes("w-full mt-3").props("color=accent dense")

            # Load code after UI mounts
            async def _load_sync_code():
                try:
                    c = await ui.run_javascript('return localStorage.getItem("dailyai_sync_code") || "";', timeout=2.0)
                    if c:
                        current_code_label.set_text(c)
                except Exception:
                    pass
            ui.timer(0.2, _load_sync_code, once=True)

        # AI Persona
        with ui.element('div').classes('sidebar-section'):
            ui.html(f'<div class="sidebar-section-title">{tr(lang, "your_ai_persona", fallback="👤 Your AI Persona")}</div>')
            ui.label(tr(lang, "persona_description", fallback="This is how we understand your interests. You can manually edit this instruction to fine-tune your bespoke briefings.")).style("font-size: 11px; color: var(--text-muted); margin-bottom: 8px;")
            persona_input = ui.textarea(tr(lang, "persona_textarea", fallback="Persona")).classes("w-full mb-2").props("dark outlined autogrow maxlength=200")

            async def _load_persona():
                try:
                    c = await ui.run_javascript('return localStorage.getItem("dailyai_sync_code");', timeout=2.0)
                    if c:
                        from dailyai.services.profiles import get_profile
                        from dailyai.storage.backend import get_metadata
                        
                        custom = await get_metadata(f"custom_persona:{c}")
                        if custom:
                            persona_input.value = custom
                        else:
                            profile = await get_profile(c)
                            if profile and profile.get("preferred_topics"):
                                prefs = profile.get("preferred_topics", [])
                                persona_input.value = f"Explicitly likes: {', '.join(prefs[:4])}."
                            else:
                                persona_input.value = ""
                except Exception:
                    pass
            
            ui.timer(0.5, _load_persona, once=True)

            async def _save_persona():
                try:
                    c = await ui.run_javascript('return localStorage.getItem("dailyai_sync_code");', timeout=2.0)
                    if c and persona_input.value is not None:
                        from dailyai.services.profiles import set_custom_persona
                        await set_custom_persona(c, str(persona_input.value))
                        ui.notify(tr(lang, "persona_saved", fallback="Persona saved! Refresh feeds to apply."), type="positive")
                except Exception as e:
                    ui.notify(tr(lang, "persona_error", fallback=f"Error saving persona: {e}", error=e), type="negative")
            
            ui.button(tr(lang, "save_persona", fallback="Save Persona"), on_click=_save_persona).classes("w-full mt-2").props("color=primary dense")

        # Actions
        with ui.element('div').classes('sidebar-section'):
            if on_refresh:
                refresh_btn = ui.element('button').classes('sidebar-action-btn primary')
                async def _on_refresh(e):
                    if asyncio.iscoroutinefunction(on_refresh):
                        await on_refresh()
                    else:
                        on_refresh()
                refresh_btn.on('click', _on_refresh)
                with refresh_btn:
                    ui.icon('refresh', size='18px')
                    ui.label(tr(lang, 'refresh_news'))

        # Footer
        with ui.element('div').classes('sidebar-footer'):
            with ui.row().classes('w-full flex-wrap gap-x-4 gap-y-1 justify-center mb-3'):
                for lbl_key, href in [
                    ('impressum', '/impressum'),
                    ('datenschutz', '/datenschutz'),
                    ('agb', '/terms'),
                    ('api_docs', '/api-docs'),
                ]:
                    ui.link(tr(lang, lbl_key), href).style(
                        'font-size: 11px; color: var(--text-muted); text-decoration: none;'
                    )
            ui.label(tr(lang, 'version_label')).style('margin-bottom: 4px;')
            ui.label(tr(lang, 'powered_by')).style('font-size: 10px; color: var(--text-muted);')


async def _handle_sort(sort_type, callback):
    js = f"""
    document.getElementById('sortRelevance').classList.toggle('active', '{sort_type}' === 'relevance');
    document.getElementById('sortLatest').classList.toggle('active', '{sort_type}' === 'latest');
    """
    ui.run_javascript(js)
    if asyncio.iscoroutinefunction(callback):
        await callback(sort_type)
    else:
        callback(sort_type)


def topic_filter(selected: str = "🔥 Top Stories", on_change=None, language: str = "en"):
    """Horizontal scroll topic chips."""
    lang = normalize_ui_language(language)
    topics = UI_FEED_TOPICS
    label_map = {
        "For You": tr(lang, 'topic_for_you'),
        "🔥 Top Stories": tr(lang, 'topic_top_stories'),
        "🤖 AI Models": tr(lang, 'topic_ai_models'),
        "💼 Business": tr(lang, 'topic_business'),
        "🔬 Research": tr(lang, 'topic_research'),
        "🛠 Tools": tr(lang, 'topic_tools'),
        "⚖️ Regulation": tr(lang, 'topic_regulation'),
        "💰 Funding": tr(lang, 'topic_funding'),
    }
    with ui.element('div').classes('w-full relative mb-1 hide-scb topic-chip-scroll').style('z-index: 220;'), ui.row().classes('flex-nowrap gap-3 items-center px-2 w-max topic-chip-row'):
        for t in topics:
            active_class = "topic-chip-active" if t == selected else ""
            chip = ui.label(label_map.get(t, t)).classes(f'topic-chip {active_class}')
            if on_change:
                chip.on('click', lambda _, t_=t: on_change(t_))
