"""
DailyAI — NiceGUI App Entry Point
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from nicegui import app as nicegui_app
from nicegui import ui

from dailyai.api.middleware import register_middleware
from dailyai.api.routes import router as api_router

# Import pages to register them
from dailyai.ui.pages import article, home, sections  # noqa: F401

# Resolve static directory relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # src/dailyai/ui -> project root
_STATIC_DIR = _PROJECT_ROOT / "static"


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

    # Configure NiceGUI on the FastAPI instance
    ui.run_with(
        app,
        title="DailyAI",
        favicon="📰",
        dark=True,
        tailwind=True,
    )

    return app
