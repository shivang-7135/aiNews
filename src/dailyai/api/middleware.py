"""
DailyAI — API Middleware
Security headers, CORS, and rate limiting.
"""

import logging
import secrets

from fastapi import FastAPI, Request, Response

logger = logging.getLogger("dailyai.api.middleware")


def register_middleware(app: FastAPI):
    """Register security middleware on the FastAPI app."""

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # CORS for API routes
        if request.url.path.startswith("/api/"):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"

        return response
