"""
DailyAI — NiceGUI App Entry Point
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from nicegui import ui

from dailyai.api.middleware import register_middleware
from dailyai.api.routes import router as api_router

# Import pages to register them
from dailyai.ui.pages import article, cache_admin, home, sections  # noqa: F401

# Resolve directories relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # src/dailyai/ui -> project root
_STATIC_DIR = _PROJECT_ROOT / "static"
_TEMPLATES_DIR = _PROJECT_ROOT / "templates"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with NiceGUI."""
    app = FastAPI(title="DailyAI v2", version="2.0.0")

    # Register API routes
    app.include_router(api_router)

    # Register middleware
    register_middleware(app)

    # Mount static assets for cover images etc
    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    # Serve legal / info pages from templates
    _TEMPLATE_ROUTES = {
        'impressum': 'impressum.html',
        'datenschutz': 'datenschutz.html',
        'terms': 'terms.html',
        'api-docs': 'api_docs.html',
    }

    def _make_template_handler(path):
        async def _handler():
            return HTMLResponse(path.read_text(encoding='utf-8'))
        return _handler

    for route_name, filename in _TEMPLATE_ROUTES.items():
        tpl_path = _TEMPLATES_DIR / filename
        if tpl_path.exists():
            app.get(f"/{route_name}")(_make_template_handler(tpl_path))

    # Configure NiceGUI on the FastAPI instance
    ui.run_with(
        app,
        title="DailyAI",
        favicon="📰",
        dark=True,
        tailwind=True,
    )

    return app
