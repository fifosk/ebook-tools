"""Simple advisory locking primitives backed by on-disk lock files."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


class LockAcquisitionError(RuntimeError):
    """Raised when a lock cannot be acquired within the requested constraints."""


@dataclass
class DirectoryLock:
    """Create and manage a `.lock` file within a directory."""

    target: Path
    filename: str = ".lock"
    poll_interval: float = 0.1
    _locked: bool = False

    def __post_init__(self) -> None:
        self.target = Path(self.target)
        if not self.filename:
            raise ValueError("Lock filename must not be empty")
        self._path = self.target / self.filename

    @property
    def path(self) -> Path:
        """Return the filesystem path of the lock file."""

        return self._path

    def relocate(self, new_target: Path | str) -> None:
        """Point the lock to a new directory without releasing it."""

        new_path = Path(new_target)
        self.target = new_path
        self._path = new_path / self.filename

    def acquire(self, *, blocking: bool = True, timeout: Optional[float] = None) -> None:
        """Attempt to acquire the lock, optionally waiting until it becomes available."""

        if self._locked:
            return

        self.target.mkdir(parents=True, exist_ok=True)
        deadline = None if timeout is None else time.monotonic() + max(timeout, 0.0)

        while True:
            try:
                fd = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if not blocking:
                    raise LockAcquisitionError(f"Lock already held at {self._path}")
                if deadline is not None and time.monotonic() >= deadline:
                    raise LockAcquisitionError(f"Timed out waiting for lock at {self._path}")
                time.sleep(self.poll_interval)
                continue

            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(f"{os.getpid()}:{time.time():.6f}\n")
                handle.flush()
                os.fsync(handle.fileno())

            self._locked = True
            return

    def release(self) -> None:
        """Release the lock if it is currently held."""

        if not self._locked:
            return
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass
        finally:
            self._locked = False

    def __enter__(self) -> "DirectoryLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


@contextmanager
def acquire_lock(path: Path | str, *, filename: str = ".lock", timeout: Optional[float] = None) -> Iterator[DirectoryLock]:
    """Context manager shorthand for acquiring a directory lock."""

    lock = DirectoryLock(Path(path), filename=filename)
    lock.acquire(timeout=timeout)
    try:
        yield lock
    finally:
        lock.release()


def lock_directory(path: Path | str, *, timeout: Optional[float] = None) -> DirectoryLock:
    """Return a lock object for the given directory after acquiring it."""

    lock = DirectoryLock(Path(path))
    lock.acquire(timeout=timeout)
    return lock
