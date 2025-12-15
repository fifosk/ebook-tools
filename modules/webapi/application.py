"""Application factory for the FastAPI backend."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import logging
import os
import re
import shutil
from pathlib import Path
import socket

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

from modules import config_manager as cfg
from modules import load_environment

from .admin_routes import router as admin_router
from .routers.audio import router as audio_router
from .routers.create_book import router as create_book_router
from .routers.library import router as library_router
from .routers.subtitles import router as subtitles_router
from .routers.assistant import router as assistant_router
from .auth_routes import router as auth_router
from .routers.reading_beds import admin_router as reading_beds_admin_router
from .routers.reading_beds import router as reading_beds_router
from modules.audio.config import load_media_config

from .dependencies import configure_media_services, get_runtime_context_provider
from .routes.media_routes import (
    register_exception_handlers as register_media_exception_handlers,
    router as media_router,
    jobs_timing_router,
)
from .routes import router, storage_router
from .routers.video import router as video_router
from modules.services.file_locator import FileLocator

load_environment()

LOGGER = logging.getLogger(__name__)

# Default origins considered safe for local development convenience.
DEFAULT_LOCAL_ORIGINS = (
    "http://localhost",
    "http://127.0.0.1",
    "https://localhost",
    "https://127.0.0.1",
)
DEFAULT_DEVSERVER_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://localhost:5173",
    "https://127.0.0.1:5173",
)

# Additional headers that should be explicitly allowed/exposed for media
# streaming support.
RANGE_REQUEST_HEADERS = ("Range",)
RANGE_RESPONSE_HEADERS = ("Accept-Ranges", "Content-Length", "Content-Range")

_STARTUP_RUNTIME_CONTEXT: cfg.RuntimeContext | None = None
_EMPTY_JOB_PRUNE_LIMIT = 200


def _initialise_tmp_workspace() -> None:
    """Ensure the API tmp directory is prepared before serving requests."""

    global _STARTUP_RUNTIME_CONTEXT
    if _STARTUP_RUNTIME_CONTEXT is not None:
        return

    provider = get_runtime_context_provider()
    resolved = provider.resolve_config()
    context = provider.build_context(resolved, {})

    if context.is_tmp_ramdisk:
        cfg.register_tmp_dir_preservation(context.tmp_dir)
        LOGGER.info("Mounted RAM disk for temporary workspace at %s", context.tmp_dir)

    _STARTUP_RUNTIME_CONTEXT = context


def _teardown_tmp_workspace() -> None:
    """Release the tmp directory resources when the API stops."""

    global _STARTUP_RUNTIME_CONTEXT
    context = _STARTUP_RUNTIME_CONTEXT
    if context is None:
        return

    try:
        if context.is_tmp_ramdisk:
            cfg.release_tmp_dir_preservation(context.tmp_dir)
            cfg.cleanup_environment(context)
            LOGGER.info(
                "Unmounted RAM disk for temporary workspace at %s", context.tmp_dir
            )
    finally:
        _STARTUP_RUNTIME_CONTEXT = None


def _directory_contains_payload(path: Path) -> bool:
    """Return True when ``path`` has any files or symlinks beneath it."""

    for child in path.rglob("*"):
        try:
            if child.is_file() or child.is_symlink():
                return True
        except OSError:
            continue
    return False


def _cleanup_empty_job_folders(storage_root: Path | None = None) -> int:
    """
    Remove empty job directories under the storage root.

    Returns the number of directories removed.
    """

    try:
        root = storage_root or FileLocator().storage_root
    except Exception:  # pragma: no cover - defensive logging
        LOGGER.warning("Unable to resolve storage root while pruning empty jobs", exc_info=True)
        return 0

    if not root.exists() or not root.is_dir():
        return 0

    removed = 0
    for index, entry in enumerate(root.iterdir()):
        if _EMPTY_JOB_PRUNE_LIMIT and index >= _EMPTY_JOB_PRUNE_LIMIT:
            break
        if not entry.is_dir():
            continue
        try:
            if _directory_contains_payload(entry):
                continue
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.debug("Skipping job folder %s due to inspection error", entry, exc_info=True)
            continue

        try:
            shutil.rmtree(entry)
            removed += 1
        except FileNotFoundError:
            continue
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.warning("Failed to prune empty job folder %s", entry, exc_info=True)
            continue

    if removed:
        LOGGER.info("Pruned %s empty job folder(s) from %s", removed, root)
    return removed


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


def _default_devserver_origins() -> list[str]:
    """Return the default dev server origins, including the local IP if available."""

    origins = set(DEFAULT_LOCAL_ORIGINS) | set(DEFAULT_DEVSERVER_ORIGINS)

    def _collect_candidate_ips() -> set[str]:
        ips: set[str] = set()
        # Preferred approach: infer the outbound interface IP without sending data.
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
                sock.connect(("8.8.8.8", 80))
                candidate = sock.getsockname()[0]
                if candidate:
                    ips.add(candidate)
        except OSError:
            pass

        # Fallbacks for environments where outbound routing is blocked (common on LAN/dev setups).
        for host in filter(None, {socket.gethostname(), socket.getfqdn()}):
            try:
                for entry in socket.getaddrinfo(host, None, family=socket.AF_INET):
                    candidate = entry[4][0]
                    if candidate:
                        ips.add(candidate)
            except OSError:
                continue

        try:
            _, _, candidates = socket.gethostbyname_ex(socket.gethostname())
            for candidate in candidates:
                if candidate:
                    ips.add(candidate)
        except OSError:
            pass

        return {ip for ip in ips if ip not in {"127.0.0.1", "0.0.0.0"}}

    for local_ip in _collect_candidate_ips():
        origins.add(f"http://{local_ip}")
        origins.add(f"http://{local_ip}:5173")
        origins.add(f"https://{local_ip}")
        origins.add(f"https://{local_ip}:5173")

    return sorted(origins)


def _parse_cors_origins(raw_value: str | None) -> tuple[list[str], bool]:
    """Return the allowed origins and whether credentials are supported."""

    if raw_value is None:
        return _default_devserver_origins(), True

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
        allow_headers=["*"] + list(RANGE_REQUEST_HEADERS),
        expose_headers=list(RANGE_RESPONSE_HEADERS),
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

    register_media_exception_handlers(app)

    @app.on_event("startup")
    async def _prepare_runtime() -> None:
        try:
            _initialise_tmp_workspace()
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Failed to initialize temporary workspace")

        try:
            media_config = cfg.load_configuration(verbose=False)
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Failed to load media configuration; using defaults")
            configure_media_services(config=None)
        else:
            configure_media_services(config=media_config)

        try:
            load_media_config()
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Failed to parse supplemental media configuration")
        try:
            _cleanup_empty_job_folders()
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Failed to prune empty job folders on startup")

    @app.on_event("shutdown")
    async def _cleanup_runtime() -> None:
        try:
            _teardown_tmp_workspace()
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Failed to clean up temporary workspace")
        try:
            _cleanup_empty_job_folders()
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Failed to prune empty job folders on shutdown")

    _configure_cors(app)

    @app.get("/_health", tags=["health"])
    def healthcheck() -> dict[str, str]:
        """Simple healthcheck endpoint for smoke-testing the server."""

        return {"status": "ok"}

    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
    app.include_router(audio_router)
    app.include_router(create_book_router)
    app.include_router(library_router)
    app.include_router(media_router)
    app.include_router(jobs_timing_router)
    app.include_router(video_router, prefix="/api/video", tags=["video"])
    app.include_router(subtitles_router)
    app.include_router(reading_beds_router)
    app.include_router(reading_beds_admin_router)
    app.include_router(assistant_router)
    app.include_router(router, prefix="/api/pipelines", tags=["pipelines"])
    app.include_router(router, prefix="/pipelines", tags=["pipelines"], include_in_schema=False)
    app.include_router(storage_router, prefix="/storage", tags=["storage"])

    static_enabled = _configure_static_assets(app)
    if not static_enabled:
        @app.get("/", tags=["health"])
        def root_healthcheck() -> dict[str, str]:
            return {"status": "ok"}

    return app
