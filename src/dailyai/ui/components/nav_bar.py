"""
DailyAI — Navigation & Sidebar Components v3
Floating glass bottom nav dock + slide-in sidebar.
Warm vibrant golden accent design.
"""

import asyncio

from nicegui import ui

from dailyai.config import COUNTRIES, SUPPORTED_LANGUAGES
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

        # Region
        with ui.element('div').classes('sidebar-section'):
            ui.html('<div class="sidebar-section-title">🌍 Region</div>')
            country_options = {
                code: f"{COUNTRY_FLAGS.get(code, '🏳️')} {name}"
                for code, name in COUNTRIES.items()
            }
            country_el = ui.element('select').classes('sidebar-select')
            country_el.props('id=sidebarCountry')
            with country_el:
                for code, display in country_options.items():
                    opt = ui.element('option')
                    opt.props(f'value="{code}"')
                    if code == app_state.get("country", "GLOBAL"):
                        opt.props('selected')
                    with opt:
                        ui.html(display)
            if on_country_change:
                async def _on_country_change(e):
                    await _handle_select_change(e, on_country_change)
                country_el.on('change', _on_country_change)

        # Language
        with ui.element('div').classes('sidebar-section'):
            ui.html('<div class="sidebar-section-title">🌐 Language</div>')
            lang_el = ui.element('select').classes('sidebar-select')
            lang_el.props('id=sidebarLanguage')
            with lang_el:
                for code, name in SUPPORTED_LANGUAGES.items():
                    opt = ui.element('option')
                    opt.props(f'value="{code}"')
                    if code == app_state.get("language", "en"):
                        opt.props('selected')
                    with opt:
                        ui.html(name)
            if on_language_change:
                async def _on_language_change(e):
                    await _handle_select_change(e, on_language_change)
                lang_el.on('change', _on_language_change)

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


async def _handle_select_change(e, callback):
    value = None
    if hasattr(e, 'args') and e.args:
        raw = e.args
        # Native HTML select 'change' event: args can be a dict, list, or string
        if isinstance(raw, dict):
            value = raw.get('value', raw.get('target', {}).get('value', ''))
            if isinstance(value, dict):
                value = str(value)
        elif isinstance(raw, list) and raw:
            value = str(raw[0])
        elif isinstance(raw, str):
            value = raw
        else:
            value = str(raw)
    elif hasattr(e, 'value'):
        value = e.value
    if value and callback:
        value = str(value).strip()
        if asyncio.iscoroutinefunction(callback):
            await callback(value)
        else:
            callback(value)


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


async def _wrap_async(fn):
    if asyncio.iscoroutinefunction(fn):
        await fn()
    else:
        fn()


def topic_filter(selected: str = "Top Stories", on_change=None):
    """Horizontal scroll topic chips."""
    topics = ["For You", "Top Stories", "AI Models", "Business", "Research", "Tools", "Tech & Science"]
    with ui.scroll_area().classes('w-full h-14 mb-2'):
        with ui.row().classes('flex-nowrap gap-3 items-center py-2 px-1 h-full w-max'):
            for t in topics:
                active_class = "topic-chip-active" if t == selected else ""
                chip = ui.label(t).classes(f'topic-chip {active_class}')
                if on_change:
                    chip.on('click', lambda _, t_=t: on_change(t_))
