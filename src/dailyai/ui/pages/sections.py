"""
DailyAI — Placeholder Section Pages
"""

from nicegui import ui

from dailyai.ui.components.nav_bar import nav_bar
from dailyai.ui.components.theme import GLOBAL_CSS


def _coming_soon_page(title: str, active_route: str):
    ui.add_head_html(f'<style>{GLOBAL_CSS}</style>')
    ui.page_title(f'DailyAI — {title}')
    ui.dark_mode(True)

    with ui.column().classes('w-full max-w-3xl mx-auto min-h-screen pb-24 sm:pb-28 px-4 pt-6'):
        ui.label(title).classes('text-3xl font-black mb-3')
        ui.label('This section is coming soon. Use Home to browse today\'s feed.').classes('text-secondary mb-6')
        ui.button('Go to Home', on_click=lambda: ui.navigate.to('/')).props('color=accent icon=home')

    nav_bar(active_route=active_route)


@ui.page('/trending')
async def trending_page():
    _coming_soon_page('Trending', '/trending')


@ui.page('/saved')
async def saved_page():
    _coming_soon_page('Saved', '/saved')


@ui.page('/profile')
async def profile_page():
    _coming_soon_page('Profile', '/profile')
