"""Persistence backends for pipeline job metadata."""

from __future__ import annotations

import atexit
import threading
import time
from typing import Callable, Dict, List, Optional, Protocol

try:  # pragma: no cover - optional dependency
    import redis  # type: ignore
except Exception:  # pragma: no cover - defensive import guard
    redis = None

from ...jobs import persistence as job_persistence
from .metadata import PipelineJobMetadata


class JobStore(Protocol):
    """Persistence backend for job metadata."""

    def save(self, metadata: PipelineJobMetadata) -> None:
        ...

    def update(self, metadata: PipelineJobMetadata) -> None:
        ...

    def get(self, job_id: str) -> PipelineJobMetadata:
        ...

    def list(
        self,
        *,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, PipelineJobMetadata]:
        """Return job metadata, optionally paginated.

        Args:
            offset: Number of jobs to skip (for pagination).
            limit: Maximum number of jobs to return.

        Returns:
            Dict mapping job_id to metadata.
        """
        ...

    def count(self) -> int:
        """Return total number of stored jobs."""
        ...

    def list_ids(self) -> List[str]:
        """Return all job IDs without loading full metadata."""
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

    def list(
        self,
        *,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, PipelineJobMetadata]:
        with self._lock:
            if offset is None and limit is None:
                return dict(self._records)
            # Apply pagination
            items = list(self._records.items())
            start = offset or 0
            end = start + limit if limit is not None else None
            return dict(items[start:end])

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def list_ids(self) -> List[str]:
        with self._lock:
            return list(self._records.keys())

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
        except (FileNotFoundError, PermissionError) as exc:
            raise KeyError(job_id) from exc

    def list(
        self,
        *,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, PipelineJobMetadata]:
        return job_persistence.load_all_jobs(offset=offset, limit=limit)

    def count(self) -> int:
        return job_persistence.count_jobs()

    def list_ids(self) -> List[str]:
        return job_persistence.list_job_ids()

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

    def _scan_keys(self) -> List[str]:
        """Scan all keys matching the namespace pattern."""
        keys: List[str] = []
        cursor = 0
        pattern = f"{self._namespace}:*"
        while True:
            cursor, batch = self._client.scan(cursor=cursor, match=pattern)
            keys.extend(batch)
            if cursor == 0:
                break
        return keys

    def save(self, metadata: PipelineJobMetadata) -> None:
        self._client.set(self._key(metadata.job_id), metadata.to_json())

    def update(self, metadata: PipelineJobMetadata) -> None:
        self.save(metadata)

    def get(self, job_id: str) -> PipelineJobMetadata:
        payload = self._client.get(self._key(job_id))
        if payload is None:
            raise KeyError(job_id)
        return PipelineJobMetadata.from_json(payload)

    def list(
        self,
        *,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, PipelineJobMetadata]:
        keys = self._scan_keys()

        # Apply pagination to keys first (lazy loading)
        if offset is not None or limit is not None:
            start = offset or 0
            end = start + limit if limit is not None else None
            keys = keys[start:end]

        records: Dict[str, PipelineJobMetadata] = {}
        for key in keys:
            payload = self._client.get(key)
            if payload is None:
                continue
            job_id = key.split(":", 1)[-1]
            records[job_id] = PipelineJobMetadata.from_json(payload)
        return records

    def count(self) -> int:
        return len(self._scan_keys())

    def list_ids(self) -> List[str]:
        keys = self._scan_keys()
        return [key.split(":", 1)[-1] for key in keys]

    def delete(self, job_id: str) -> None:
        removed = self._client.delete(self._key(job_id))
        if not removed:
            raise KeyError(job_id)


class CachingJobStore:
    """Read-caching wrapper that caches metadata lookups with TTL.

    Caches individual job metadata to reduce I/O on repeated reads.
    Cache is invalidated on writes to ensure consistency.
    """

    def __init__(
        self,
        store: JobStore,
        *,
        max_cache_size: int = 100,
        ttl_seconds: float = 60.0,
    ) -> None:
        """Initialize the caching store.

        Args:
            store: The underlying store to cache reads from.
            max_cache_size: Maximum number of jobs to cache.
            ttl_seconds: Time-to-live for cached entries.
        """
        self._store = store
        self._max_cache_size = max(1, max_cache_size)
        self._ttl = max(0.0, ttl_seconds)

        self._lock = threading.RLock()
        self._cache: Dict[str, tuple[PipelineJobMetadata, float]] = {}  # job_id -> (metadata, expiry)

    def _is_expired(self, expiry: float) -> bool:
        """Check if a cache entry has expired."""
        return time.monotonic() > expiry

    def _evict_expired(self) -> None:
        """Remove expired entries from cache."""
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._cache.items() if now > exp]
        for k in expired:
            del self._cache[k]

    def _evict_oldest(self) -> None:
        """Remove oldest entries if cache is full."""
        if len(self._cache) >= self._max_cache_size:
            # Sort by expiry time and remove oldest
            sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][1])
            to_remove = len(self._cache) - self._max_cache_size + 1
            for k in sorted_keys[:to_remove]:
                del self._cache[k]

    def _cache_put(self, job_id: str, metadata: PipelineJobMetadata) -> None:
        """Add or update a cache entry."""
        with self._lock:
            self._evict_expired()
            self._evict_oldest()
            expiry = time.monotonic() + self._ttl
            self._cache[job_id] = (metadata, expiry)

    def _cache_get(self, job_id: str) -> Optional[PipelineJobMetadata]:
        """Get from cache if present and not expired."""
        with self._lock:
            entry = self._cache.get(job_id)
            if entry is None:
                return None
            metadata, expiry = entry
            if self._is_expired(expiry):
                del self._cache[job_id]
                return None
            return metadata

    def _cache_invalidate(self, job_id: str) -> None:
        """Remove a specific entry from cache."""
        with self._lock:
            self._cache.pop(job_id, None)

    def _cache_clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()

    def save(self, metadata: PipelineJobMetadata) -> None:
        """Save and update cache."""
        self._store.save(metadata)
        self._cache_put(metadata.job_id, metadata)

    def update(self, metadata: PipelineJobMetadata) -> None:
        """Update and refresh cache."""
        self._store.update(metadata)
        self._cache_put(metadata.job_id, metadata)

    def get(self, job_id: str) -> PipelineJobMetadata:
        """Get from cache or underlying store."""
        cached = self._cache_get(job_id)
        if cached is not None:
            return cached
        metadata = self._store.get(job_id)
        self._cache_put(job_id, metadata)
        return metadata

    def list(
        self,
        *,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, PipelineJobMetadata]:
        """List jobs and populate cache."""
        result = self._store.list(offset=offset, limit=limit)
        # Populate cache with results
        for job_id, metadata in result.items():
            self._cache_put(job_id, metadata)
        return result

    def count(self) -> int:
        """Return total count from underlying store."""
        return self._store.count()

    def list_ids(self) -> List[str]:
        """Return all job IDs from underlying store."""
        return self._store.list_ids()

    def delete(self, job_id: str) -> None:
        """Delete and invalidate cache."""
        self._cache_invalidate(job_id)
        self._store.delete(job_id)

    def clear_cache(self) -> None:
        """Explicitly clear the cache."""
        self._cache_clear()


class BatchingJobStore:
    """Write-buffering wrapper that batches updates to reduce I/O.

    Collects updates in memory and flushes to the underlying store either:
    - When buffer reaches max_buffer_size
    - When flush_interval_seconds has elapsed since last flush
    - When flush() is called explicitly
    - On shutdown (via atexit)

    Reads are served from the buffer first, falling back to underlying store.
    """

    def __init__(
        self,
        store: JobStore,
        *,
        max_buffer_size: int = 10,
        flush_interval_seconds: float = 5.0,
        on_flush_error: Optional[Callable[[str, Exception], None]] = None,
    ) -> None:
        """Initialize the batching store.

        Args:
            store: The underlying store to batch writes to.
            max_buffer_size: Flush when buffer reaches this many pending updates.
            flush_interval_seconds: Flush after this many seconds of inactivity.
            on_flush_error: Optional callback for flush errors (job_id, exception).
        """
        self._store = store
        self._max_buffer_size = max(1, max_buffer_size)
        self._flush_interval = max(0.1, flush_interval_seconds)
        self._on_flush_error = on_flush_error

        self._lock = threading.RLock()
        self._buffer: Dict[str, PipelineJobMetadata] = {}
        self._dirty: set[str] = set()  # job_ids with pending writes
        self._last_flush = time.monotonic()

        # Background flush timer
        self._shutdown = threading.Event()
        self._flush_thread = threading.Thread(
            target=self._flush_loop,
            name="BatchingJobStore-flush",
            daemon=True,
        )
        self._flush_thread.start()

        # Ensure flush on shutdown
        atexit.register(self._shutdown_flush)

    def _flush_loop(self) -> None:
        """Background thread that periodically flushes the buffer."""
        while not self._shutdown.wait(timeout=self._flush_interval / 2):
            elapsed = time.monotonic() - self._last_flush
            if elapsed >= self._flush_interval:
                self.flush()

    def _shutdown_flush(self) -> None:
        """Flush remaining buffer on shutdown."""
        self._shutdown.set()
        self.flush()

    def flush(self) -> None:
        """Flush all pending updates to the underlying store."""
        with self._lock:
            if not self._dirty:
                self._last_flush = time.monotonic()
                return

            to_flush = [(job_id, self._buffer[job_id]) for job_id in list(self._dirty)]
            self._dirty.clear()
            self._last_flush = time.monotonic()

        # Flush outside the lock to avoid blocking reads
        for job_id, metadata in to_flush:
            try:
                self._store.update(metadata)
            except Exception as exc:
                if self._on_flush_error:
                    self._on_flush_error(job_id, exc)

    def save(self, metadata: PipelineJobMetadata) -> None:
        """Buffer a save operation."""
        with self._lock:
            self._buffer[metadata.job_id] = metadata
            self._dirty.add(metadata.job_id)
            if len(self._dirty) >= self._max_buffer_size:
                # Trigger immediate flush
                pass  # Will flush below
            else:
                return
        self.flush()

    def update(self, metadata: PipelineJobMetadata) -> None:
        """Buffer an update operation."""
        self.save(metadata)

    def get(self, job_id: str) -> PipelineJobMetadata:
        """Get from buffer first, then underlying store."""
        with self._lock:
            if job_id in self._buffer:
                return self._buffer[job_id]
        return self._store.get(job_id)

    def list(
        self,
        *,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, PipelineJobMetadata]:
        """List jobs, merging buffer with underlying store."""
        # Get from underlying store
        result = self._store.list(offset=offset, limit=limit)

        # Overlay buffered updates
        with self._lock:
            for job_id, metadata in self._buffer.items():
                if job_id in result or (offset is None and limit is None):
                    result[job_id] = metadata

        return result

    def count(self) -> int:
        """Return total count (may include buffered new jobs)."""
        base_count = self._store.count()
        with self._lock:
            # Count new jobs in buffer not yet in store
            new_in_buffer = sum(
                1 for job_id in self._buffer
                if job_id not in self._store.list_ids()
            )
        return base_count + new_in_buffer

    def list_ids(self) -> List[str]:
        """Return all job IDs including buffered."""
        ids = set(self._store.list_ids())
        with self._lock:
            ids.update(self._buffer.keys())
        return list(ids)

    def delete(self, job_id: str) -> None:
        """Delete from buffer and underlying store."""
        with self._lock:
            self._buffer.pop(job_id, None)
            self._dirty.discard(job_id)
        self._store.delete(job_id)

    def close(self) -> None:
        """Flush and stop the background thread."""
        self._shutdown.set()
        self.flush()
        if self._flush_thread.is_alive():
            self._flush_thread.join(timeout=2.0)


__all__ = [
    "JobStore",
    "InMemoryJobStore",
    "FileJobStore",
    "RedisJobStore",
    "CachingJobStore",
    "BatchingJobStore",
]
