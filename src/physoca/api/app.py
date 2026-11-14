"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from physoca.api.headers import SecurityHeadersMiddleware
from physoca.api.limits import RequestSizeLimitMiddleware
from physoca.api.routes import router
from physoca.config import STATIC_DIR, Settings
from physoca.version import __version__


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = Settings.from_env()
    app = FastAPI(
        title="Physoca",
        version=__version__,
        description="Deterministic, rule-based deprescribing decision-support API.",
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(router)
    return app


app = create_app()
