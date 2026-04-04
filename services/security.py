import secrets
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from services.config import CSRF_COOKIE_NAME, SECURITY_CSP
from services.store import RATE_LIMIT_BUCKETS


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if xff:
        return xff
    return request.client.host if request.client else "unknown"


def _api_limit_for(path: str, method: str) -> tuple[int, int] | None:
    if not path.startswith("/api/"):
        return None
    if path.startswith("/api/refresh"):
        return (4, 60)
    if path.startswith("/api/subscribe"):
        return (10, 60)
    if path.startswith("/api/articles/brief"):
        return (20, 60)
    if path.startswith("/api/profile/") and path.endswith("/signal"):
        return (30, 60)
    if path.startswith("/api/profile/") and path.endswith("/analytics"):
        return (20, 60)
    if method.upper() == "POST":
        return (45, 60)
    return (240, 60)


def _expected_origin(request: Request) -> str:
    host = request.headers.get("host", "")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return f"{proto}://{host}" if host else ""


def ensure_csrf_cookie(request: Request, response) -> None:
    if request.cookies.get(CSRF_COOKIE_NAME):
        return
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=secrets.token_urlsafe(24),
        max_age=7 * 24 * 60 * 60,
        path="/",
        samesite="lax",
        secure=(request.headers.get("x-forwarded-proto", request.url.scheme) == "https"),
        httponly=False,
    )


def register_security_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_and_rate_limit_middleware(request: Request, call_next):
        if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith(
            "/api/"
        ):
            # Exempt analytics endpoint — sendBeacon() cannot send custom headers
            is_analytics = "/analytics" in request.url.path

            origin = request.headers.get("origin", "")
            expected_origin = _expected_origin(request)
            if origin and expected_origin and origin != expected_origin:
                return JSONResponse({"error": "Invalid request origin."}, status_code=403)

            if not is_analytics:
                cookie_token = request.cookies.get(CSRF_COOKIE_NAME, "")
                header_token = request.headers.get("x-csrf-token", "")
                if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
                    return JSONResponse({"error": "Security token missing or invalid."}, status_code=403)

        limit_cfg = _api_limit_for(request.url.path, request.method)
        if limit_cfg:
            max_requests, window_seconds = limit_cfg
            now = time.time()
            bucket_key = f"{_client_ip(request)}:{request.method.upper()}:{request.url.path}"
            bucket = RATE_LIMIT_BUCKETS[bucket_key]

            while bucket and now - bucket[0] > window_seconds:
                bucket.popleft()

            if len(bucket) >= max_requests:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                response = JSONResponse(
                    {"error": "Too many requests. Please slow down."},
                    status_code=429,
                )
                response.headers["Retry-After"] = str(retry_after)
                response.headers["X-RateLimit-Limit"] = str(max_requests)
                response.headers["X-RateLimit-Remaining"] = "0"
                return response

            bucket.append(now)

        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = SECURITY_CSP
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"

        return response
