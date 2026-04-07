"""
DailyAI — Navigation & Sidebar Components v4
Floating glass bottom nav dock + slide-in sidebar.
Uses NiceGUI ui.select for reliable dropdown handling.
"""

import asyncio

from nicegui import ui

from dailyai.config import COUNTRIES, UI_FEED_TOPICS, UI_LANGUAGES
from dailyai.ui.components.theme import COUNTRY_FLAGS


def nav_bar(active_route: str = "/", on_settings: callable = None, on_saved: callable = None):
    """Floating glass bottom navigation dock — always visible."""

    with ui.row().classes('bottom-nav'):
        with ui.element('div').classes('bottom-nav-inner'):
            _nav_btn(
                icon='explore', label='Discover',
                active=active_route == '/',
                on_click=lambda: ui.navigate.to('/'),
            )
            _nav_btn(
                icon='bookmark', label='Saved',
                active=active_route == '/saved',
                on_click=on_saved or (lambda: ui.navigate.to('/saved')),
            )
            _nav_btn(
                icon='tune', label='Settings',
                active=active_route == '/settings',
                on_click=on_settings,
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
):
    """Slide-in settings sidebar."""
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
                    ui.label('AI News Intelligence').style(
                        'font-size: 10px; font-weight: 600; color: var(--text-muted);'
                        ' letter-spacing: 0.06em; text-transform: uppercase;'
                    )
            close_btn = ui.element('button').classes('sidebar-close')
            with close_btn:
                ui.html('&#10005;')
            close_btn.on('click', lambda: ui.run_javascript('closeSidebar()'))

        # Region — using NiceGUI ui.select for reliable event handling
        with ui.element('div').classes('sidebar-section'):
            ui.html('<div class="sidebar-section-title">🌍 Region</div>')
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
            ui.html('<div class="sidebar-section-title">🌐 Language</div>')
            current_lang = app_state.get("language", "en")

            lang_select = ui.select(
                options=UI_LANGUAGES,
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
            ui.html('<div class="sidebar-section-title">📊 Sort by</div>')
            current_sort = app_state.get("sort", "relevance")
            with ui.element('div').classes('sort-group'):
                rel_btn = ui.element('button').classes(
                    f'sort-btn {"active" if current_sort == "relevance" else ""}'
                )
                with rel_btn:
                    ui.html('Relevance')
                rel_btn.props('id=sortRelevance')
                lat_btn = ui.element('button').classes(
                    f'sort-btn {"active" if current_sort == "latest" else ""}'
                )
                with lat_btn:
                    ui.html('Latest')
                lat_btn.props('id=sortLatest')
            if on_sort_change:
                async def _sort_relevance(e):
                    await _handle_sort('relevance', on_sort_change)
                async def _sort_latest(e):
                    await _handle_sort('latest', on_sort_change)
                rel_btn.on('click', _sort_relevance)
                lat_btn.on('click', _sort_latest)

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
                    ui.label('Refresh News')

        # Footer
        with ui.element('div').classes('sidebar-footer'):
            with ui.row().classes('w-full flex-wrap gap-x-4 gap-y-1 justify-center mb-3'):
                for lbl, href in [
                    ('Impressum', '/impressum'),
                    ('Datenschutz', '/datenschutz'),
                    ('AGB', '/terms'),
                    ('API Docs', '/api-docs'),
                ]:
                    ui.link(lbl, href).style(
                        'font-size: 11px; color: var(--text-muted); text-decoration: none;'
                    )
            ui.label('v3.0 · DailyAI').style('margin-bottom: 4px;')
            ui.label('Powered by AI · Built with ❤️').style('font-size: 10px; color: var(--text-muted);')


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


def topic_filter(selected: str = "🔥 Top Stories", on_change=None):
    """Horizontal scroll topic chips."""
    topics = UI_FEED_TOPICS
    with ui.scroll_area().classes('w-full h-14 mb-2'):
        with ui.row().classes('flex-nowrap gap-3 items-center py-2 px-1 h-full w-max'):
            for t in topics:
                active_class = "topic-chip-active" if t == selected else ""
                chip = ui.label(t).classes(f'topic-chip {active_class}')
                if on_change:
                    chip.on('click', lambda _, t_=t: on_change(t_))
