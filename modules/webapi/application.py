"""Application factory for the FastAPI backend."""

from __future__ import annotations

from fastapi import FastAPI

from .routes import router


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    app = FastAPI(title="ebook-tools API", version="0.1.0")
    app.include_router(router, prefix="/pipelines", tags=["pipelines"])
    return app
