"""Small utilities for coordinating subtitle jobs."""

from __future__ import annotations

from typing import Optional

from .common import DEFAULT_BATCH_SIZE, DEFAULT_WORKERS


def _resolve_batch_size(candidate: Optional[int], total: int) -> int:
    if isinstance(candidate, int) and candidate > 0:
        return max(1, min(candidate, total))
    return max(1, min(DEFAULT_BATCH_SIZE, total))


def _resolve_worker_count(
    candidate: Optional[int],
    batch_size: int,
    total: int,
) -> int:
    if isinstance(candidate, int) and candidate > 0:
        return max(1, min(candidate, total))
    resolved = min(DEFAULT_WORKERS, batch_size, total)
    return max(1, resolved)


def _is_cancelled(stop_event) -> bool:
    if stop_event is None:
        return False
    checker = getattr(stop_event, "is_set", None)
    if callable(checker):
        try:
            return bool(checker())
        except Exception:  # pragma: no cover - defensive guard
            return False
    return False


__all__ = ["_is_cancelled", "_resolve_batch_size", "_resolve_worker_count"]
