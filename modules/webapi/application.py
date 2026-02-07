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
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send
from urllib.parse import urlparse
from fastapi.staticfiles import StaticFiles

from modules import config_manager as cfg
from modules import load_environment
from modules.core.storage_config import configure_hf_environment

# Configure HuggingFace environment early, before any HF imports
configure_hf_environment()

from .admin_routes import router as admin_router
from .config_routes import router as config_router
from .system_routes import router as system_router
from .routers.audio import router as audio_router
from .routers.create_book import router as create_book_router
from .routers.exports import router as exports_router
from .routers.library import router as library_router
from .routers.subtitles import router as subtitles_router
from .routers.assistant import router as assistant_router
from .routers.bookmarks import router as bookmarks_router
from .routers.resume import router as resume_router
from .auth_routes import router as auth_router
from .routers.reading_beds import admin_router as reading_beds_admin_router
from .routers.reading_beds import router as reading_beds_router
from .routes.notification_routes import router as notification_router
from modules.audio.config import load_media_config

from .dependencies import (
    configure_media_services,
    get_notification_service,
    get_pipeline_job_manager,
    get_runtime_context_provider,
)
from .routes.media_routes import (
    register_exception_handlers as register_media_exception_handlers,
    router as media_router,
    jobs_timing_router,
)
from .routes import router, storage_router
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


_EXPORT_MAX_AGE_SECONDS = 24 * 60 * 60  # 1 day


def _cleanup_stale_exports(
    exports_root: Path | None = None,
    max_age_seconds: float = _EXPORT_MAX_AGE_SECONDS,
) -> int:
    """Remove old or orphaned export artifacts.

    Removes:
    - Any export directory/zip/json older than *max_age_seconds* (default 1 day).
    - Orphaned staging directories whose companion .zip is missing.
    - Orphaned .json metadata files whose companion .zip is missing.

    Returns the number of entries removed.
    """
    import time

    try:
        root = exports_root or FileLocator().storage_root / "exports"
    except Exception:  # pragma: no cover - defensive logging
        LOGGER.warning("Unable to resolve exports root while cleaning stale exports", exc_info=True)
        return 0

    if not root.exists() or not root.is_dir():
        return 0

    now = time.time()
    removed = 0
    for entry in root.iterdir():
        try:
            age = now - entry.stat().st_mtime
            is_old = age > max_age_seconds

            if entry.is_dir():
                zip_path = root / f"{entry.name}.zip"
                if is_old or not zip_path.exists():
                    shutil.rmtree(entry)
                    removed += 1
            elif entry.suffix == ".zip":
                if is_old:
                    entry.unlink()
                    removed += 1
                    # Also remove companion .json and staging dir
                    entry.with_suffix(".json").unlink(missing_ok=True)
                    companion_dir = root / entry.stem
                    if companion_dir.is_dir():
                        shutil.rmtree(companion_dir)
                    removed += 1
            elif entry.suffix == ".json":
                zip_path = entry.with_suffix(".zip")
                if is_old or not zip_path.exists():
                    entry.unlink()
                    removed += 1
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.warning("Failed to clean stale export %s", entry, exc_info=True)
            continue

    if removed:
        LOGGER.info("Cleaned %s stale export artifact(s) from %s", removed, root)
    return removed


# Directories at the storage root that are NOT job folders.
_NON_JOB_DIRS = frozenset({
    "bookmarks", "cache", "covers", "ebooks", "exports",
    "library", "reading_beds", "resume", "test-integration",
})


def _cleanup_orphaned_job_folders(storage_root: Path | None = None) -> int:
    """Remove storage folders for jobs that no longer exist in the job store.

    A folder is considered orphaned when it lives under the storage root,
    is not a known non-job directory, and has no ``metadata/job.json``
    (i.e. it is not tracked by the job persistence layer).

    Returns the number of directories removed.
    """
    from modules.jobs.persistence import list_job_ids

    try:
        root = storage_root or FileLocator().storage_root
    except Exception:  # pragma: no cover - defensive logging
        LOGGER.warning("Unable to resolve storage root while cleaning orphaned jobs", exc_info=True)
        return 0

    if not root.exists() or not root.is_dir():
        return 0

    known_ids = set(list_job_ids())
    removed = 0
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if entry.name in _NON_JOB_DIRS:
            continue
        if entry.name in known_ids:
            continue
        try:
            shutil.rmtree(entry)
            removed += 1
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.warning("Failed to remove orphaned job folder %s", entry, exc_info=True)
            continue

    if removed:
        LOGGER.info("Removed %s orphaned job folder(s) from %s", removed, root)
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

    def _collect_candidate_hosts() -> set[str]:
        hosts: set[str] = set()
        for host in filter(None, {socket.gethostname(), socket.getfqdn()}):
            trimmed = host.strip()
            if not trimmed:
                continue
            normalized = trimmed.lower()
            hosts.add(normalized)
            if "." in normalized:
                short = normalized.split(".", 1)[0].strip()
                if short:
                    hosts.add(short)
        return hosts

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

    for host in _collect_candidate_hosts():
        origins.add(f"http://{host}")
        origins.add(f"http://{host}:5173")
        origins.add(f"https://{host}")
        origins.add(f"https://{host}:5173")

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


def _normalize_origin(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return None
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _normalize_host(value: str | None) -> str | None:
    if not value:
        return None
    host = value.strip().lower()
    if not host:
        return None
    if host.startswith("["):
        end = host.find("]")
        if end >= 0:
            return host[1:end]
        return host
    if ":" in host:
        return host.split(":", 1)[0]
    return host


class DynamicCORSMiddleware:
    """CORS middleware with a host-based fallback for paired UI/API origins."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        allowed_origins: list[str],
        allow_credentials: bool,
        allow_methods: list[str],
        allow_headers: list[str],
        expose_headers: list[str],
    ) -> None:
        self.app = app
        self.allowed_origins = {_normalize_origin(origin) for origin in allowed_origins}
        self.allowed_origins.discard(None)
        self.allow_all_origins = "*" in allowed_origins
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods
        self.allow_headers = allow_headers
        self.expose_headers = expose_headers

    def _origin_allowed(self, origin: str, headers: Headers) -> bool:
        normalized = _normalize_origin(origin)
        if normalized is None:
            return False
        if self.allow_all_origins:
            return True
        if normalized in self.allowed_origins:
            return True

        origin_host = _normalize_host(urlparse(normalized).hostname)
        request_host = _normalize_host(headers.get("host"))
        if not origin_host or not request_host:
            return False
        if origin_host == request_host:
            return True
        if request_host.startswith("api."):
            return origin_host == request_host[len("api.") :]
        if request_host.startswith("api-"):
            return origin_host == request_host[len("api-") :]
        return False

    def _apply_cors_headers(self, headers: MutableHeaders, origin: str) -> None:
        headers["Access-Control-Allow-Origin"] = origin
        if self.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"
        if self.expose_headers:
            headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
        vary = headers.get("Vary")
        if not vary:
            headers["Vary"] = "Origin"
        elif "origin" not in {value.strip().lower() for value in vary.split(",")}:
            headers["Vary"] = f"{vary}, Origin"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        origin = headers.get("origin")
        if not origin or not self._origin_allowed(origin, headers):
            await self.app(scope, receive, send)
            return

        is_preflight = (
            scope["method"] == "OPTIONS"
            and "access-control-request-method" in headers
        )
        if is_preflight:
            response = Response(status_code=204)
            response_headers = response.headers
            self._apply_cors_headers(response_headers, origin)
            if self.allow_methods:
                if "*" in self.allow_methods:
                    response_headers["Access-Control-Allow-Methods"] = headers.get(
                        "access-control-request-method", ""
                    )
                else:
                    response_headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
            if self.allow_headers:
                if "*" in self.allow_headers:
                    response_headers["Access-Control-Allow-Headers"] = headers.get(
                        "access-control-request-headers", ""
                    )
                else:
                    response_headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
            if "Access-Control-Max-Age" not in response_headers:
                response_headers["Access-Control-Max-Age"] = "600"
            await response(scope, receive, send)
            return

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                self._apply_cors_headers(response_headers, origin)
            await send(message)

        await self.app(scope, receive, send_wrapper)


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
        DynamicCORSMiddleware,
        allowed_origins=allowed_origins,
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
        try:
            _cleanup_stale_exports()
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Failed to clean stale exports on startup")
        try:
            _cleanup_orphaned_job_folders()
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Failed to clean orphaned job folders on startup")

        # Wire up push notification callback
        try:
            notification_service = get_notification_service()
            if notification_service.is_enabled:
                job_manager = get_pipeline_job_manager()
                job_manager.set_notification_callback(
                    notification_service.notify_job_completed
                )
                LOGGER.info("Push notifications enabled for job completion events")
            else:
                LOGGER.debug("Push notifications disabled (APNs not configured)")
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.debug("Failed to configure push notifications", exc_info=True)

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
    app.include_router(config_router, prefix="/api/admin", tags=["config"])
    app.include_router(system_router, prefix="/api/admin", tags=["system"])
    app.include_router(audio_router)
    app.include_router(create_book_router)
    app.include_router(library_router)
    app.include_router(media_router)
    app.include_router(jobs_timing_router)
    app.include_router(subtitles_router)
    app.include_router(reading_beds_router)
    app.include_router(reading_beds_admin_router)
    app.include_router(bookmarks_router)
    app.include_router(resume_router)
    app.include_router(assistant_router)
    app.include_router(exports_router)
    app.include_router(notification_router)
    app.include_router(router, prefix="/api/pipelines", tags=["pipelines"])
    app.include_router(router, prefix="/pipelines", tags=["pipelines"], include_in_schema=False)
    app.include_router(storage_router, prefix="/storage", tags=["storage"])

    static_enabled = _configure_static_assets(app)
    if not static_enabled:
        @app.get("/", tags=["health"])
        def root_healthcheck() -> dict[str, str]:
            return {"status": "ok"}

    return app
