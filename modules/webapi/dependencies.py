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
from ..library.sqlite_indexer import LibraryIndexer
from ..library.library_service import LibraryService
from ..services.file_locator import FileLocator
from ..services.pipeline_service import PipelineService
from ..user_management import AuthService, LocalUserStore, SessionManager
from ..video.api import VideoService
from ..video.jobs import VideoJobManager
from .jobs import PipelineJobManager


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
    get_video_service.cache_clear()


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


def _env_video_backend_override() -> str | None:
    for key in ("EBOOK_VIDEO_BACKEND", "VIDEO_BACKEND"):
        value = os.environ.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _env_video_executable_override() -> str | None:
    for key in ("EBOOK_VIDEO_EXECUTABLE", "EBOOK_FFMPEG_PATH", "FFMPEG_PATH"):
        value = os.environ.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _coerce_backend_settings(payload: Any) -> Dict[str, Dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return {}
    result: Dict[str, Dict[str, Any]] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, Mapping):
            result[key] = dict(value)
    return result


def _resolve_video_configuration(
    config: Mapping[str, Any]
) -> tuple[str | None, Dict[str, Dict[str, Any]]]:
    backend_name = None
    config_backend = config.get("video_backend")
    if isinstance(config_backend, str) and config_backend.strip():
        backend_name = config_backend.strip()

    backend_settings = _coerce_backend_settings(config.get("video_backend_settings"))

    ffmpeg_path = config.get("ffmpeg_path")
    if isinstance(ffmpeg_path, str) and ffmpeg_path.strip():
        ffmpeg_cfg = dict(backend_settings.get("ffmpeg", {}))
        ffmpeg_cfg.setdefault("executable", ffmpeg_path.strip())
        backend_settings["ffmpeg"] = ffmpeg_cfg

    backend_override = _env_video_backend_override()
    executable_override = _env_video_executable_override()

    active_backend = (backend_override or backend_name or "ffmpeg").strip()
    if executable_override:
        backend_cfg = dict(backend_settings.get(active_backend, {}))
        backend_cfg["executable"] = executable_override
        backend_settings[active_backend] = backend_cfg

    if backend_override:
        backend_name = backend_override

    return backend_name, backend_settings


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
        try:
            self._base_config = cfg.load_configuration(verbose=False)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to load base configuration; falling back to defaults.",
                exc_info=exc,
                extra={"event": "config.load.failed", "console_suppress": True},
            )
            self._base_config: Dict[str, Any] = {}

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
def get_library_indexer() -> LibraryIndexer:
    """Return the process-wide :class:`LibraryIndexer`."""

    return LibraryIndexer(cfg.get_library_root(create=True))


@lru_cache
def get_library_service() -> LibraryService:
    """Return the shared :class:`LibraryService` instance."""

    library_root = cfg.get_library_root(create=True)
    locator = get_file_locator()
    indexer = get_library_indexer()
    job_manager = get_pipeline_job_manager()
    return LibraryService(
        library_root=library_root,
        file_locator=locator,
        indexer=indexer,
        job_manager=job_manager,
    )


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
def get_video_service() -> VideoService:
    """Return a configured :class:`VideoService` instance."""

    config = _get_bootstrapped_media_config()
    backend_name, backend_settings = _resolve_video_configuration(config)
    return VideoService(backend=backend_name, backend_settings=backend_settings)


@lru_cache
def get_video_job_manager() -> VideoJobManager:
    """Return the process-wide :class:`VideoJobManager` instance."""

    return VideoJobManager()


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


@lru_cache
def get_auth_service() -> AuthService:
    """Return a configured :class:`AuthService` instance."""

    user_store_path, session_file = _resolve_auth_configuration()
    user_store = LocalUserStore(storage_path=user_store_path)
    session_manager = SessionManager(session_file=session_file)
    return AuthService(user_store, session_manager)


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
        user_role = role_value.lower() if role_value else None
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
            normalized = primary.strip()
            if normalized:
                role = normalized.lower()
    return RequestUserContext(user_id=record.username, user_role=role)
