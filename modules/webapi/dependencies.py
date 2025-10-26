"""Dependency wiring for the FastAPI application."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Optional, cast

from .. import config_manager as cfg
from .. import logging_manager as log_mgr
from ..audio.api import AudioService
from ..services.file_locator import FileLocator
from ..services.pipeline_service import PipelineService
from ..user_management import AuthService, LocalUserStore, SessionManager
from .jobs import PipelineJobManager


logger = log_mgr.logger


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
def get_audio_service() -> AudioService:
    """Return a configured :class:`AudioService` instance."""

    config = cfg.load_configuration(verbose=False)
    return AudioService(config=config)


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
