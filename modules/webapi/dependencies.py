"""Dependency wiring for the FastAPI application."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from functools import lru_cache
import threading
from typing import Any, Dict, Iterator, Mapping, Optional, cast
from .. import config_manager as cfg
from .. import logging_manager as log_mgr
from ..services.pipeline_service import PipelineService
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
        self._lock = threading.RLock()
        self._base_context: Optional[cfg.RuntimeContext] = None

    def ensure_base_context(self) -> cfg.RuntimeContext:
        """Return the base runtime context, creating it if necessary."""

        with self._lock:
            if self._base_context is None:
                self._base_context = cfg.build_runtime_context(
                    dict(self._base_config), {}
                )
            return self._base_context

    def startup(self) -> None:
        """Prepare the base context during application startup."""

        try:
            self.ensure_base_context()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to initialize runtime context: %s",
                exc,
                extra={"event": "context.initialize.failed", "console_suppress": True},
            )

    def shutdown(self) -> None:
        """Release managed resources when the application stops."""

        with self._lock:
            context = self._base_context
            self._base_context = None
        if context is not None:
            try:
                cfg.cleanup_environment(context)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.debug(
                    "Failed to clean up runtime context during shutdown: %s",
                    exc,
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

        normalized_config = dict(config)
        override_mapping = dict(overrides or {})
        if not override_mapping and normalized_config == self._base_config:
            return self.ensure_base_context()
        return cfg.build_runtime_context(normalized_config, override_mapping)

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
        cleanup_required = self.should_cleanup(context)
        cfg.set_runtime_context(context)
        try:
            yield context
        finally:
            try:
                if cleanup_required:
                    cfg.cleanup_environment(context)
            finally:
                cfg.clear_runtime_context()

    def should_cleanup(self, context: Optional[cfg.RuntimeContext]) -> bool:
        """Return ``True`` when ``context`` should be cleaned up after use."""

        if context is None:
            return True
        with self._lock:
            return context is not self._base_context


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
