"""Dependency wiring for the FastAPI application."""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Dict, Iterator, Optional

from .. import config_manager as cfg
from ..services.pipeline_service import PipelineService
from .jobs import PipelineJobManager


class RuntimeContextProvider:
    """Factory responsible for building runtime contexts for requests."""

    def create(
        self,
        config: Dict[str, object],
        overrides: Optional[Dict[str, object]] = None,
    ) -> cfg.RuntimeContext:
        """Construct a :class:`RuntimeContext` for the supplied settings."""

        return cfg.build_runtime_context(config, overrides or {})

    @contextmanager
    def activation(
        self,
        config: Dict[str, object],
        overrides: Optional[Dict[str, object]] = None,
    ) -> Iterator[cfg.RuntimeContext]:
        """Context manager that activates and cleans up the runtime context."""

        context = self.create(config, overrides)
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
