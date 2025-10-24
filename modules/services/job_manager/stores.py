"""Persistence backends for pipeline job metadata."""

from __future__ import annotations

import threading
from typing import Dict, Protocol

try:  # pragma: no cover - optional dependency
    import redis  # type: ignore
except Exception:  # pragma: no cover - defensive import guard
    redis = None

from ..jobs import persistence as job_persistence
from .metadata import PipelineJobMetadata


class JobStore(Protocol):
    """Persistence backend for job metadata."""

    def save(self, metadata: PipelineJobMetadata) -> None:
        ...

    def update(self, metadata: PipelineJobMetadata) -> None:
        ...

    def get(self, job_id: str) -> PipelineJobMetadata:
        ...

    def list(self) -> Dict[str, PipelineJobMetadata]:
        ...

    def delete(self, job_id: str) -> None:
        ...


class InMemoryJobStore(JobStore):
    """Simple process-local store used as a default fallback."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: Dict[str, PipelineJobMetadata] = {}

    def save(self, metadata: PipelineJobMetadata) -> None:
        with self._lock:
            self._records[metadata.job_id] = metadata

    def update(self, metadata: PipelineJobMetadata) -> None:
        with self._lock:
            self._records[metadata.job_id] = metadata

    def get(self, job_id: str) -> PipelineJobMetadata:
        with self._lock:
            try:
                return self._records[job_id]
            except KeyError as exc:
                raise KeyError(job_id) from exc

    def list(self) -> Dict[str, PipelineJobMetadata]:
        with self._lock:
            return dict(self._records)

    def delete(self, job_id: str) -> None:
        with self._lock:
            try:
                del self._records[job_id]
            except KeyError as exc:
                raise KeyError(job_id) from exc


class FileJobStore(JobStore):
    """Filesystem-backed job store using :mod:`modules.jobs.persistence`."""

    def save(self, metadata: PipelineJobMetadata) -> None:
        job_persistence.save_job(metadata)

    def update(self, metadata: PipelineJobMetadata) -> None:
        job_persistence.save_job(metadata)

    def get(self, job_id: str) -> PipelineJobMetadata:
        try:
            return job_persistence.load_job(job_id)
        except FileNotFoundError as exc:  # pragma: no cover - passthrough
            raise KeyError(job_id) from exc

    def list(self) -> Dict[str, PipelineJobMetadata]:
        return job_persistence.load_all_jobs()

    def delete(self, job_id: str) -> None:
        try:
            job_persistence.delete_job(job_id)
        except FileNotFoundError as exc:  # pragma: no cover - passthrough
            raise KeyError(job_id) from exc


class RedisJobStore(JobStore):
    """Redis-backed implementation of :class:`JobStore`."""

    def __init__(self, url: str, *, namespace: str = "ebook-tools:jobs") -> None:
        if redis is None:  # pragma: no cover - optional dependency
            raise RuntimeError("redis-py is not available; cannot use RedisJobStore")
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._namespace = namespace

    def _key(self, job_id: str) -> str:
        return f"{self._namespace}:{job_id}"

    def save(self, metadata: PipelineJobMetadata) -> None:
        self._client.set(self._key(metadata.job_id), metadata.to_json())

    def update(self, metadata: PipelineJobMetadata) -> None:
        self.save(metadata)

    def get(self, job_id: str) -> PipelineJobMetadata:
        payload = self._client.get(self._key(job_id))
        if payload is None:
            raise KeyError(job_id)
        return PipelineJobMetadata.from_json(payload)

    def list(self) -> Dict[str, PipelineJobMetadata]:
        records: Dict[str, PipelineJobMetadata] = {}
        cursor = 0
        pattern = f"{self._namespace}:*"
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern)
            for key in keys:
                payload = self._client.get(key)
                if payload is None:
                    continue
                job_id = key.split(":", 1)[-1]
                records[job_id] = PipelineJobMetadata.from_json(payload)
            if cursor == 0:
                break
        return records

    def delete(self, job_id: str) -> None:
        removed = self._client.delete(self._key(job_id))
        if not removed:
            raise KeyError(job_id)


__all__ = [
    "JobStore",
    "InMemoryJobStore",
    "FileJobStore",
    "RedisJobStore",
]
