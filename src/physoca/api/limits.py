"""Request size and rate-limiting middleware."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests larger than max_bytes."""

    def __init__(self, app: Callable[..., object], max_bytes: int = 256 * 1024) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: Callable[[Request], object]) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            return JSONResponse({"detail": "Request body too large"}, status_code=413)
        return await call_next(request)  # type: ignore[misc, no-any-return]


class LocalRateLimiter:
    """Simple sliding-window rate limiter per client IP."""

    def __init__(self, max_requests: int = 120, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, client_ip: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        recent = [t for t in self._hits[client_ip] if t > cutoff]
        if len(recent) >= self.max_requests:
            self._hits[client_ip] = recent
            return False
        recent.append(now)
        self._hits[client_ip] = recent
        return True
