"""Utilities for tracking pipeline progress without external dependencies."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Dict, Optional


@dataclass(frozen=True)
class ProgressSnapshot:
    """Immutable view of the current pipeline progress statistics."""

    completed: int
    total: Optional[int]
    elapsed: float
    speed: float
    eta: Optional[float]


class ProgressTracker:
    """Track progress statistics for the translation/media pipeline."""

    def __init__(self, total_blocks: Optional[int] = None, *, report_interval: float = 5.0) -> None:
        self._lock = threading.Lock()
        self._start_time = time.perf_counter()
        self._completed = 0
        self._total: Optional[int] = total_blocks
        self._report_interval = max(0.1, report_interval)
        self._finished_event = threading.Event()
        self._translation_timestamps: Dict[int, float] = {}
        self._media_timestamps: Dict[int, float] = {}

    @property
    def report_interval(self) -> float:
        """Return the preferred monitoring interval in seconds."""

        return self._report_interval

    def set_total(self, total_blocks: int) -> None:
        """Update the expected total number of blocks to process."""

        with self._lock:
            self._total = max(0, total_blocks)
            if self._total == 0:
                self._finished_event.set()

    def record_translation_completion(self, index: int, sentence_number: int) -> None:
        """Record the completion of a translation task."""

        now = time.perf_counter()
        with self._lock:
            self._translation_timestamps[sentence_number] = now
            # No completion counter increment here; consumer completions drive progress.

    def record_media_completion(self, index: int, sentence_number: int) -> None:
        """Record the completion of a media generation task."""

        now = time.perf_counter()
        with self._lock:
            self._media_timestamps[sentence_number] = now
            self._completed += 1
            if self._total is not None and self._completed >= self._total:
                self._finished_event.set()

    def snapshot(self) -> ProgressSnapshot:
        """Return a snapshot of the current progress statistics."""

        with self._lock:
            completed = self._completed
            total = self._total
        now = time.perf_counter()
        elapsed = max(0.0, now - self._start_time)
        if elapsed > 0 and completed > 0:
            speed = completed / elapsed
        else:
            speed = 0.0
        eta: Optional[float]
        if speed > 0 and total is not None:
            remaining = max(total - completed, 0)
            eta = remaining / speed if remaining > 0 else 0.0
        else:
            eta = None
        return ProgressSnapshot(
            completed=completed,
            total=total,
            elapsed=elapsed,
            speed=speed,
            eta=eta,
        )

    def is_complete(self) -> bool:
        """Return whether all expected blocks have been processed."""

        with self._lock:
            if self._total is None:
                return False
            return self._completed >= self._total

    def mark_finished(self) -> None:
        """Signal that monitoring can stop regardless of completion state."""

        self._finished_event.set()

    def wait(self, timeout: float) -> bool:
        """Wait for completion or for ``timeout`` seconds."""

        return self._finished_event.wait(timeout)


__all__ = ["ProgressTracker", "ProgressSnapshot"]
