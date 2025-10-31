"""Filesystem utility helpers for ebook-tools."""

from __future__ import annotations

from .atomic_move import atomic_move, AtomicMoveError, ChecksumMismatchError
from .locks import (
    DirectoryLock,
    LockAcquisitionError,
    acquire_lock,
    lock_directory,
)

__all__ = [
    "atomic_move",
    "AtomicMoveError",
    "ChecksumMismatchError",
    "DirectoryLock",
    "LockAcquisitionError",
    "acquire_lock",
    "lock_directory",
]
