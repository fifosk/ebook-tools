"""Storage coordination utilities for pipeline job persistence."""

from __future__ import annotations

import os
from typing import Dict, Iterable, Optional

from ... import config_manager as cfg
from ... import logging_manager as log_mgr
from .metadata import PipelineJobMetadata
from .stores import FileJobStore, InMemoryJobStore, JobStore, RedisJobStore

logger = log_mgr.logger


class JobStorageCoordinator:
    """Encapsulate job store selection and recovery helpers."""

    def __init__(self, store: Optional[JobStore] = None) -> None:
        self._store = store or self._default_store()

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
