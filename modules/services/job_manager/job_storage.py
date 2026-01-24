"""Storage coordination utilities for pipeline job persistence."""

from __future__ import annotations

import os
from typing import Dict, Iterable, Optional

from ... import config_manager as cfg
from ... import logging_manager as log_mgr
from .metadata import PipelineJobMetadata
from .stores import BatchingJobStore, CachingJobStore, FileJobStore, InMemoryJobStore, JobStore, RedisJobStore

logger = log_mgr.logger


class JobStorageCoordinator:
    """Encapsulate job store selection and recovery helpers."""

    def __init__(
        self,
        store: Optional[JobStore] = None,
        *,
        enable_batching: Optional[bool] = None,
        batch_size: int = 10,
        batch_flush_interval: float = 5.0,
        enable_caching: Optional[bool] = None,
        cache_size: int = 100,
        cache_ttl: float = 60.0,
    ) -> None:
        """Initialize the storage coordinator.

        Args:
            store: Optional explicit store instance.
            enable_batching: Whether to wrap the store with BatchingJobStore.
                If None, reads from settings (defaults to True for FileJobStore).
            batch_size: Number of updates to buffer before flushing.
            batch_flush_interval: Seconds between automatic flushes.
            enable_caching: Whether to wrap the store with CachingJobStore.
                If None, reads from settings (defaults to True for FileJobStore).
            cache_size: Maximum number of jobs to cache.
            cache_ttl: Time-to-live for cached entries in seconds.
        """
        base_store = store or self._default_store()
        settings = cfg.get_settings()

        # Determine if caching should be enabled
        if enable_caching is None:
            enable_caching = getattr(settings, "job_store_caching", None)
            if enable_caching is None:
                # Default: enable caching for file-based stores (most I/O benefit)
                enable_caching = isinstance(base_store, FileJobStore)

        # Determine if batching should be enabled
        if enable_batching is None:
            enable_batching = getattr(settings, "job_store_batching", None)
            if enable_batching is None:
                # Default: enable batching for file-based stores (most I/O benefit)
                enable_batching = isinstance(base_store, FileJobStore)

        # Apply wrappers: caching first (for reads), then batching (for writes)
        wrapped_store = base_store

        if enable_caching:
            wrapped_store = CachingJobStore(
                wrapped_store,
                max_cache_size=cache_size,
                ttl_seconds=cache_ttl,
            )
            self._caching_enabled = True
        else:
            self._caching_enabled = False

        if enable_batching:
            wrapped_store = BatchingJobStore(
                wrapped_store,
                max_buffer_size=batch_size,
                flush_interval_seconds=batch_flush_interval,
                on_flush_error=self._on_batch_flush_error,
            )
            self._batching_enabled = True
        else:
            self._batching_enabled = False

        self._store = wrapped_store

    def _on_batch_flush_error(self, job_id: str, exc: Exception) -> None:
        """Handle errors during batch flush."""
        logger.warning(
            "Failed to flush batched job update",
            exc_info=exc,
            extra={
                "event": "pipeline.job.batch_flush.failed",
                "job_id": job_id,
                "console_suppress": True,
            },
        )

    @property
    def store(self) -> JobStore:
        """Return the active job store instance."""

        return self._store

    def load_all(self) -> Dict[str, PipelineJobMetadata]:
        """Return all persisted job metadata records."""

        try:
            return self._store.list()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to load persisted pipeline jobs",  # pragma: no cover - log only
                exc_info=exc,
                extra={"event": "pipeline.job.restore.failed", "console_suppress": True},
            )
            return {}

    def persist_reconciliation(self, updates: Iterable[PipelineJobMetadata]) -> None:
        """Persist metadata updates produced during recovery."""

        for payload in updates:
            try:
                self._store.update(payload)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "Failed to persist reconciled job state",  # pragma: no cover - log only
                    exc_info=exc,
                    extra={
                        "event": "pipeline.job.restore.persist_failed",
                        "job_id": payload.job_id,
                        "console_suppress": True,
                    },
                )

    def flush(self) -> None:
        """Flush any pending batched updates to the underlying store."""
        if self._batching_enabled and isinstance(self._store, BatchingJobStore):
            self._store.flush()

    def close(self) -> None:
        """Flush pending updates and release resources."""
        if self._batching_enabled and isinstance(self._store, BatchingJobStore):
            self._store.close()

    @property
    def batching_enabled(self) -> bool:
        """Return whether batching is enabled."""
        return self._batching_enabled

    @property
    def caching_enabled(self) -> bool:
        """Return whether caching is enabled."""
        return self._caching_enabled

    def _default_store(self) -> JobStore:
        settings = cfg.get_settings()
        secret = settings.job_store_url
        url = secret.get_secret_value() if secret is not None else None
        if not url:
            url = os.environ.get("JOB_STORE_URL")
        if url:
            try:
                logger.debug("Using RedisJobStore for pipeline job metadata at %s", url)
                return RedisJobStore(url)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to initialize RedisJobStore: %s", exc)
        try:
            return FileJobStore()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to initialize FileJobStore: %s", exc)
        return InMemoryJobStore()
