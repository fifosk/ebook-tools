"""Dependency wiring for the FastAPI application."""

from __future__ import annotations

import os
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Optional, cast

from fastapi import Depends, Header, Query

from .. import config_manager as cfg
from .. import logging_manager as log_mgr
from ..audio.api import AudioService
from ..library import (
    LibraryRepository,
    LibraryService,
    LibrarySync,
    PgLibraryRepository,
    get_library_service as build_library_service,
)
from ..services.file_locator import FileLocator
from ..services.pipeline_service import PipelineService
from ..services.media_metadata_service import MediaMetadataService
from ..services.subtitle_service import SubtitleService
from ..services.subtitle_metadata_service import SubtitleMetadataService
from ..services.youtube_video_metadata_service import YoutubeVideoMetadataService
from ..services.youtube_dubbing import YoutubeDubbingService
from ..services.export_service import ExportService
from ..services.bookmark_service import BookmarkService
from ..services.resume_service import ResumeService
from ..user_management import AuthService, LocalUserStore, SessionManager
from ..user_management import PgUserStore, PgSessionManager
from modules.permissions import normalize_role
from ..services.job_manager import PipelineJobManager
from ..notifications import APNsConfig, APNsService, NotificationService


logger = log_mgr.logger


_BOOTSTRAPPED_MEDIA_CONFIG: Dict[str, Any] | None = None


@dataclass(frozen=True)
class RequestUserContext:
    """Identity extracted from headers or the current session token."""

    user_id: str | None
    user_role: str | None


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token.strip() or None
    return authorization.strip() or None


def _apply_audio_api_configuration(config: Mapping[str, Any]) -> None:
    base_url = config.get("audio_api_base_url")
    if isinstance(base_url, str):
        base_url = base_url.strip()
    if base_url:
        os.environ["EBOOK_AUDIO_API_BASE_URL"] = base_url
    else:
        os.environ.pop("EBOOK_AUDIO_API_BASE_URL", None)

    def _apply_numeric(key: str, env_key: str) -> None:
        value = config.get(key)
        if value is None:
            os.environ.pop(env_key, None)
            return
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            os.environ.pop(env_key, None)
            return
        os.environ[env_key] = str(numeric)

    _apply_numeric("audio_api_timeout_seconds", "EBOOK_AUDIO_API_TIMEOUT_SECONDS")
    _apply_numeric(
        "audio_api_poll_interval_seconds", "EBOOK_AUDIO_API_POLL_INTERVAL_SECONDS"
    )


def configure_media_services(*, config: Mapping[str, Any] | None = None) -> None:
    """Cache the bootstrap configuration used by media service dependencies."""

    global _BOOTSTRAPPED_MEDIA_CONFIG
    _BOOTSTRAPPED_MEDIA_CONFIG = dict(config or {})
    _apply_audio_api_configuration(_BOOTSTRAPPED_MEDIA_CONFIG)
    get_audio_service.cache_clear()


def _get_bootstrapped_media_config() -> Dict[str, Any]:
    if _BOOTSTRAPPED_MEDIA_CONFIG is not None:
        return dict(_BOOTSTRAPPED_MEDIA_CONFIG)
    try:
        config = cfg.load_configuration(verbose=False)
        _apply_audio_api_configuration(config)
        return config
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(
            "Falling back to empty configuration after load failure.",
            exc_info=exc,
            extra={"event": "config.media.load_failed", "console_suppress": True},
        )
        return {}


def _env_audio_backend_override() -> str | None:
    for key in ("EBOOK_AUDIO_BACKEND", "EBOOK_TTS_BACKEND"):
        value = os.environ.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _env_audio_executable_override() -> str | None:
    for key in (
        "EBOOK_AUDIO_EXECUTABLE",
        "EBOOK_TTS_EXECUTABLE",
        "EBOOK_SAY_PATH",
        "SAY_PATH",
    ):
        value = os.environ.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _deep_merge(base: Mapping[str, Any], overrides: Mapping[str, Any]) -> Dict[str, Any]:
    """Recursively merge ``overrides`` into ``base`` and return a copy."""

    merged: Dict[str, Any] = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(
                cast(Mapping[str, Any], merged[key]),
                value,
            )
        else:
            merged[key] = value
    return merged


class RuntimeContextProvider:
    """Factory responsible for building runtime contexts for requests."""

    def __init__(self) -> None:
        self._base_config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load or reload configuration from all sources."""
        try:
            self._base_config = cfg.load_configuration(verbose=False)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to load base configuration; falling back to defaults.",
                exc_info=exc,
                extra={"event": "config.load.failed", "console_suppress": True},
            )
            self._base_config = {}

    def refresh_config(self) -> None:
        """Reload configuration from all sources including database."""
        self._load_config()
        logger.info(
            "Configuration refreshed",
            extra={"event": "config.refreshed", "console_important": True},
        )

    def resolve_config(self, updates: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """Return the default configuration merged with ``updates``."""

        if not updates:
            return deepcopy(self._base_config)
        return _deep_merge(self._base_config, dict(updates))

    def build_context(
        self,
        config: Mapping[str, Any],
        overrides: Optional[Dict[str, Any]] = None,
    ) -> cfg.RuntimeContext:
        """Construct a :class:`RuntimeContext` from a resolved configuration."""

        return cfg.build_runtime_context(dict(config), overrides or {})

    def create(
        self,
        config: Dict[str, object],
        overrides: Optional[Dict[str, object]] = None,
    ) -> cfg.RuntimeContext:
        """Construct a :class:`RuntimeContext` for the supplied settings."""

        resolved = self.resolve_config(config)
        return self.build_context(resolved, overrides)

    @contextmanager
    def activation(
        self,
        config: Dict[str, object],
        overrides: Optional[Dict[str, object]] = None,
    ) -> Iterator[cfg.RuntimeContext]:
        """Context manager that activates and cleans up the runtime context."""

        resolved = self.resolve_config(config)
        context = self.build_context(resolved, overrides)
        cfg.set_runtime_context(context)
        try:
            yield context
        finally:
            try:
                cfg.cleanup_environment(context)
            finally:
                cfg.clear_runtime_context()


@lru_cache
def get_runtime_context_provider() -> RuntimeContextProvider:
    """Return a singleton :class:`RuntimeContextProvider`."""

    return RuntimeContextProvider()


def refresh_runtime_config() -> None:
    """Refresh configuration in the RuntimeContextProvider singleton.

    Call this after configuration has been updated (e.g., via admin UI)
    to ensure subsequent requests use the updated configuration.
    """
    provider = get_runtime_context_provider()
    provider.refresh_config()


@lru_cache
def get_pipeline_job_manager() -> PipelineJobManager:
    """Return the process-wide :class:`PipelineJobManager` instance."""

    return PipelineJobManager()


@lru_cache
def get_pipeline_service() -> PipelineService:
    """Return a lazily constructed :class:`PipelineService`."""

    return PipelineService(get_pipeline_job_manager())


@lru_cache
def get_file_locator() -> FileLocator:
    """Return a cached :class:`FileLocator` instance for route handlers."""

    return FileLocator()


@lru_cache
def get_library_service() -> LibraryService:
    """Return the shared :class:`LibraryService` instance.

    Uses PostgreSQL-backed repository when DATABASE_URL is set,
    otherwise falls back to the legacy SQLite repository.
    """
    library_root = cfg.get_library_root(create=True)
    locator = get_file_locator()
    job_manager = get_pipeline_job_manager()
    if _use_postgres():
        repo = PgLibraryRepository(library_root)
        return LibraryService(
            library_root=library_root,
            file_locator=locator,
            repository=repo,
            job_manager=job_manager,
        )
    return build_library_service(
        library_root=library_root,
        file_locator=locator,
        job_manager=job_manager,
    )


@lru_cache
def get_library_sync() -> LibrarySync:
    """Convenience accessor for the shared :class:`LibrarySync`."""

    return get_library_service().sync


@lru_cache
def get_library_repository() -> LibraryRepository:
    """Convenience accessor for the shared :class:`LibraryRepository`."""

    return get_library_service().repository


@lru_cache
def get_export_service() -> ExportService:
    """Return the shared :class:`ExportService` instance."""

    return ExportService(
        pipeline_service=get_pipeline_service(),
        library_service=get_library_service(),
        file_locator=get_file_locator(),
    )


@lru_cache
def get_bookmark_service():
    """Return the shared bookmark service (PG or filesystem)."""
    if _use_postgres():
        from ..services.pg_bookmark_service import PgBookmarkService
        return PgBookmarkService()
    return BookmarkService(file_locator=get_file_locator())


@lru_cache
def get_resume_service():
    """Return the shared resume service (PG or filesystem)."""
    if _use_postgres():
        from ..services.pg_resume_service import PgResumeService
        return PgResumeService()
    return ResumeService(file_locator=get_file_locator())


@lru_cache
def get_analytics_service():
    """Return the shared analytics service (PG only, None if no DB)."""
    if _use_postgres():
        from ..services.analytics_service import MediaAnalyticsService

        return MediaAnalyticsService()
    return None


@lru_cache
def get_audio_service() -> AudioService:
    """Return a configured :class:`AudioService` instance."""

    config = _get_bootstrapped_media_config()
    backend_override = _env_audio_backend_override()
    executable_override = _env_audio_executable_override()
    return AudioService(
        config=config,
        backend_name=backend_override,
        executable_path=executable_override,
    )


@lru_cache
def get_subtitle_service() -> SubtitleService:
    """Return the shared :class:`SubtitleService` instance."""

    job_manager = get_pipeline_job_manager()
    locator = get_file_locator()
    return SubtitleService(job_manager=job_manager, locator=locator)


@lru_cache
def get_subtitle_metadata_service() -> SubtitleMetadataService:
    """Return the shared :class:`SubtitleMetadataService` instance."""

    job_manager = get_pipeline_job_manager()
    return SubtitleMetadataService(job_manager=job_manager)


@lru_cache
def get_media_metadata_service() -> MediaMetadataService:
    """Return the shared :class:`MediaMetadataService` instance."""

    job_manager = get_pipeline_job_manager()
    return MediaMetadataService(job_manager=job_manager)


@lru_cache
def get_youtube_video_metadata_service() -> YoutubeVideoMetadataService:
    """Return the shared :class:`YoutubeVideoMetadataService` instance."""

    job_manager = get_pipeline_job_manager()
    return YoutubeVideoMetadataService(job_manager=job_manager)


@lru_cache
def get_youtube_dubbing_service() -> YoutubeDubbingService:
    """Return the shared :class:`YoutubeDubbingService` instance."""

    job_manager = get_pipeline_job_manager()
    return YoutubeDubbingService(job_manager=job_manager, max_workers=cfg.get_settings().job_max_workers)


def _expand_path(path_value: Optional[str]) -> Optional[Path]:
    if not path_value:
        return None
    return Path(path_value).expanduser()


def _resolve_auth_configuration() -> tuple[Optional[Path], Optional[Path]]:
    config = cfg.load_configuration(verbose=False)
    auth_config = config.get("authentication") or {}

    user_store_config = auth_config.get("user_store") or {}
    sessions_config = auth_config.get("sessions") or {}

    user_store_path = _expand_path(user_store_config.get("storage_path"))
    session_file = _expand_path(sessions_config.get("session_file"))

    return user_store_path, session_file


def _use_postgres() -> bool:
    """Return True if DATABASE_URL is set (PostgreSQL mode)."""
    return bool(os.environ.get("DATABASE_URL", "").strip())


@lru_cache
def get_auth_service() -> AuthService:
    """Return a configured :class:`AuthService` instance.

    Uses PostgreSQL backends when DATABASE_URL is set, otherwise falls
    back to the legacy JSON-file backends.
    """
    if _use_postgres():
        return AuthService(PgUserStore(), PgSessionManager())

    user_store_path, session_file = _resolve_auth_configuration()
    user_store = LocalUserStore(storage_path=user_store_path)
    session_manager = SessionManager(session_file=session_file)
    return AuthService(user_store, session_manager)


def _resolve_apns_configuration() -> APNsConfig | None:
    """Load APNs configuration from config files."""
    config = cfg.load_configuration(verbose=False)
    apns_config = config.get("apns") or {}

    if not apns_config.get("enabled", False):
        return None

    key_path_str = apns_config.get("key_path", "")
    if not key_path_str:
        return None

    key_path = Path(key_path_str).expanduser()
    if not key_path.is_absolute():
        # SCRIPT_DIR is already the project root
        key_path = cfg.SCRIPT_DIR / key_path

    return APNsConfig(
        key_id=apns_config.get("key_id", ""),
        team_id=apns_config.get("team_id", ""),
        bundle_id=apns_config.get("bundle_id", ""),
        key_path=key_path,
        environment=apns_config.get("environment", "development"),
    )


@lru_cache
def get_apns_service() -> APNsService | None:
    """Return a configured APNs service, or None if not configured."""
    apns_config = _resolve_apns_configuration()
    if not apns_config or not apns_config.is_valid():
        logger.debug("APNs not configured or invalid; push notifications disabled")
        return None
    return APNsService(apns_config)


def _get_apns_api_base_url() -> str | None:
    """Get the API base URL for notification payloads."""
    config = cfg.load_configuration(verbose=False)
    apns_config = config.get("apns") or {}
    return apns_config.get("api_base_url")


@lru_cache
def get_notification_service() -> NotificationService:
    """Return the shared NotificationService instance."""
    apns_service = get_apns_service()
    auth_service = get_auth_service()
    api_base_url = _get_apns_api_base_url()
    return NotificationService(
        apns_service=apns_service,
        user_store=auth_service.user_store,
        api_base_url=api_base_url,
    )


def get_request_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    header_user_id: str | None = Header(default=None, alias="X-User-Id"),
    header_user_role: str | None = Header(default=None, alias="X-User-Role"),
    access_token: str | None = Query(default=None, alias="access_token"),
    auth_service: AuthService = Depends(get_auth_service),
) -> RequestUserContext:
    """Resolve the request user identity from forwarded headers or session token."""

    if header_user_id:
        user_id = header_user_id.strip() or None
        role_value = (header_user_role or "").strip()
        user_role = normalize_role(role_value) if role_value else None
        return RequestUserContext(user_id=user_id, user_role=user_role)

    token = _extract_bearer_token(authorization)
    if not token:
        token = (access_token or "").strip() or None
    if not token:
        return RequestUserContext(user_id=None, user_role=None)

    record = auth_service.authenticate(token)
    if record is None:
        return RequestUserContext(user_id=None, user_role=None)

    role = None
    if record.roles:
        primary = record.roles[0]
        if isinstance(primary, str):
            role = normalize_role(primary)
    return RequestUserContext(user_id=record.username, user_role=role)
