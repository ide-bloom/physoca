"""Security and cache-control headers."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach security headers and no-store caching on review endpoints."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], object]) -> Response:
        response: Response = await call_next(request)  # type: ignore[misc]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path in ("/api/review", "/review"):
            response.headers["Cache-Control"] = "no-store"
        return response
