"""Fine-grained locking utilities for pipeline job management."""

from __future__ import annotations

import threading
import weakref
from contextlib import contextmanager
from typing import Dict, Iterator, Optional


class JobLockManager:
    """Provide per-job locks to reduce contention on shared resources.

    This manager maintains a global lock for the job registry and separate
    per-job locks for individual job operations. This allows multiple jobs
    to be processed concurrently without blocking each other.

    Usage:
        lock_manager = JobLockManager()

        # For operations on the jobs registry (list, add, remove)
        with lock_manager.registry_lock():
            jobs[job_id] = job

        # For operations on a specific job
        with lock_manager.job_lock(job_id):
            job.update_status(...)

        # For atomic operations that need both
        with lock_manager.job_lock(job_id, include_registry=True):
            job = jobs.get(job_id)
            job.update_status(...)
    """

    def __init__(self, *, max_locks: int = 1000) -> None:
        """Initialize the lock manager.

        Args:
            max_locks: Maximum number of per-job locks to cache.
                       Old locks are cleaned up when limit is reached.
        """
        self._registry_lock = threading.RLock()
        self._job_locks: Dict[str, threading.RLock] = {}
        self._job_locks_lock = threading.Lock()  # Protects _job_locks dict
        self._max_locks = max(10, max_locks)

    @contextmanager
    def registry_lock(self) -> Iterator[None]:
        """Acquire the global registry lock for job dictionary operations."""
        with self._registry_lock:
            yield

    def _get_or_create_job_lock(self, job_id: str) -> threading.RLock:
        """Get or create a lock for a specific job."""
        with self._job_locks_lock:
            lock = self._job_locks.get(job_id)
            if lock is None:
                # Cleanup old locks if we're at capacity
                if len(self._job_locks) >= self._max_locks:
                    self._cleanup_unused_locks()
                lock = threading.RLock()
                self._job_locks[job_id] = lock
            return lock

    def _cleanup_unused_locks(self) -> None:
        """Remove locks that are not currently held.

        Called when lock cache reaches capacity. Removes approximately
        half of the unlocked entries to avoid frequent cleanups.
        """
        to_remove = []
        target = len(self._job_locks) // 2

        for job_id, lock in list(self._job_locks.items()):
            # Try to acquire lock without blocking
            acquired = lock.acquire(blocking=False)
            if acquired:
                # Lock was free, safe to remove
                lock.release()
                to_remove.append(job_id)
                if len(to_remove) >= target:
                    break

        for job_id in to_remove:
            self._job_locks.pop(job_id, None)

    @contextmanager
    def job_lock(
        self, job_id: str, *, include_registry: bool = False
    ) -> Iterator[None]:
        """Acquire a lock for operations on a specific job.

        Args:
            job_id: The job to lock.
            include_registry: If True, also acquire the registry lock first.
                             Use this for operations that modify both the
                             job and the jobs dictionary.
        """
        job_lock = self._get_or_create_job_lock(job_id)

        if include_registry:
            with self._registry_lock:
                with job_lock:
                    yield
        else:
            with job_lock:
                yield

    def remove_job_lock(self, job_id: str) -> None:
        """Remove the lock for a job (call after job is deleted)."""
        with self._job_locks_lock:
            self._job_locks.pop(job_id, None)

    @property
    def active_lock_count(self) -> int:
        """Return the number of cached job locks."""
        with self._job_locks_lock:
            return len(self._job_locks)


# For backwards compatibility, provide a shim that wraps the old single-lock pattern
class CompatibilityLockManager:
    """Drop-in replacement that uses fine-grained locking internally.

    This class provides the same interface as a single RLock but uses
    the JobLockManager internally. Use this during migration to avoid
    changing all call sites at once.
    """

    def __init__(self, job_lock_manager: Optional[JobLockManager] = None) -> None:
        self._manager = job_lock_manager or JobLockManager()
        self._current_job_id: Optional[str] = None

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        """Acquire the registry lock (for compatibility)."""
        return self._manager._registry_lock.acquire(blocking=blocking, timeout=timeout)

    def release(self) -> None:
        """Release the registry lock (for compatibility)."""
        self._manager._registry_lock.release()

    def __enter__(self) -> "CompatibilityLockManager":
        self._manager._registry_lock.acquire()
        return self

    def __exit__(self, *args) -> None:
        self._manager._registry_lock.release()

    @contextmanager
    def for_job(self, job_id: str) -> Iterator[None]:
        """Context manager for job-specific operations."""
        with self._manager.job_lock(job_id):
            yield

    @property
    def job_lock_manager(self) -> JobLockManager:
        """Access the underlying JobLockManager."""
        return self._manager


__all__ = ["JobLockManager", "CompatibilityLockManager"]
