"""Application factory for the FastAPI backend."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

from modules import load_environment

from .routes import router

load_environment()

LOGGER = logging.getLogger(__name__)

# Default Vite dev server origins for local development convenience.
DEFAULT_DEVSERVER_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


@dataclass(frozen=True)
class StaticAssetsConfig:
    """Configuration for serving the bundled single-page application."""

    directory: Path
    index_file: str
    mount_path: str


class SPAStaticFiles(StaticFiles):
    """Static file handler that falls back to the configured index file."""

    def __init__(self, *args, index_file: str = "index.html", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._index_file = index_file

    async def get_response(self, path: str, scope: Scope) -> Response:  # type: ignore[override]
        response = await super().get_response(path, scope)
        if response.status_code == 404:
            return await super().get_response(self._index_file, scope)
        return response


def _normalise_mount_path(value: str | None) -> str:
    if not value:
        return "/"
    if not value.startswith("/"):
        value = f"/{value}"
    if len(value) > 1 and value.endswith("/"):
        value = value.rstrip("/")
    return value


def _parse_cors_origins(raw_value: str | None) -> tuple[list[str], bool]:
    """Return the allowed origins and whether credentials are supported."""

    if raw_value is None:
        return list(DEFAULT_DEVSERVER_ORIGINS), True

    tokens = [token.strip() for token in re.split(r"[\s,]+", raw_value) if token.strip()]
    if not tokens:
        return [], False
    if "*" in tokens:
        return ["*"], False
    return tokens, True


def _resolve_static_assets_config() -> StaticAssetsConfig | None:
    """Determine whether to serve the bundled SPA and, if so, how."""

    root_value = os.environ.get("EBOOK_API_STATIC_ROOT")
    if root_value is not None and not root_value.strip():
        return None

    if root_value is None:
        root_path = Path(__file__).resolve().parents[2] / "web" / "dist"
    else:
        root_path = Path(root_value).expanduser().resolve()

    if not root_path.is_dir():
        return None

    index_file = os.environ.get("EBOOK_API_STATIC_INDEX", "index.html")
    index_path = root_path / index_file
    if not index_path.is_file():
        LOGGER.warning(
            "Static assets directory '%s' does not contain '%s'; SPA routing may fail.",
            root_path,
            index_file,
        )

    mount_path = _normalise_mount_path(os.environ.get("EBOOK_API_STATIC_MOUNT", "/"))
    return StaticAssetsConfig(directory=root_path, index_file=index_file, mount_path=mount_path)


def _configure_cors(app: FastAPI) -> None:
    allowed_origins, allow_credentials = _parse_cors_origins(os.environ.get("EBOOK_API_CORS_ORIGINS"))
    if not allowed_origins:
        LOGGER.info("CORS middleware disabled; no allowed origins configured.")
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _configure_static_assets(app: FastAPI) -> bool:
    config = _resolve_static_assets_config()
    if config is None:
        return False

    app.mount(
        config.mount_path,
        SPAStaticFiles(directory=str(config.directory), html=True, check_dir=False, index_file=config.index_file),
        name="spa",
    )
    LOGGER.info("Serving static assets from %s at '%s'", config.directory, config.mount_path)
    return True


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    app = FastAPI(title="ebook-tools API", version="0.1.0")

    _configure_cors(app)

    @app.get("/_health", tags=["health"])
    def healthcheck() -> dict[str, str]:
        """Simple healthcheck endpoint for smoke-testing the server."""

        return {"status": "ok"}

    app.include_router(router, prefix="/pipelines", tags=["pipelines"])

    static_enabled = _configure_static_assets(app)
    if not static_enabled:
        @app.get("/", tags=["health"])
        def root_healthcheck() -> dict[str, str]:
            return {"status": "ok"}

    return app
