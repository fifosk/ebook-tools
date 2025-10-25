"""Utilities for tracking pipeline progress without external dependencies."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import MappingProxyType
import threading
import time
from typing import (
    AsyncIterator,
    Callable,
    Dict,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)


@dataclass(frozen=True)
class ProgressSnapshot:
    """Immutable view of the current pipeline progress statistics."""

    completed: int
    total: Optional[int]
    elapsed: float
    speed: float
    eta: Optional[float]
    generated_files: Mapping[str, Tuple[str, ...]] | None = None


@dataclass(frozen=True)
class ProgressEvent:
    """Structured message emitted by :class:`ProgressTracker`."""

    event_type: str
    snapshot: ProgressSnapshot
    timestamp: float
    metadata: Mapping[str, object]
    error: Optional[BaseException] = None


class ProgressEventStream:
    """Asynchronous iterator that yields :class:`ProgressEvent` objects."""

    _SENTINEL = object()

    def __init__(self, tracker: "ProgressTracker", loop: asyncio.AbstractEventLoop):
        self._tracker = tracker
        self._loop = loop
        self._queue: "asyncio.Queue[object]" = asyncio.Queue()
        self._closed = False
        self._unsubscribe = tracker.register_observer(self._on_event)

    def _on_event(self, event: ProgressEvent) -> None:
        if self._closed:
            return
        try:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, event)
        except RuntimeError:
            pass

    def __aiter__(self) -> AsyncIterator[ProgressEvent]:
        return self

    async def __anext__(self) -> ProgressEvent:
        item = await self._queue.get()
        if item is self._SENTINEL:
            raise StopAsyncIteration
        return item  # type: ignore[return-value]

    async def aclose(self) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._unsubscribe()
        try:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, self._SENTINEL)
        except RuntimeError:
            pass


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
        self._observers: Sequence[Callable[[ProgressEvent], None]] = []
        self._started = False
        self._completion_emitted = False
        self._generated_files: Dict[str, Tuple[str, ...]] = {}

    @property
    def report_interval(self) -> float:
        """Return the preferred monitoring interval in seconds."""

        return self._report_interval

    def set_total(self, total_blocks: int) -> None:
        """Update the expected total number of blocks to process."""

        should_emit_start = False
        new_total = max(0, total_blocks)
        with self._lock:
            self._total = new_total
            if not self._started:
                should_emit_start = True
                self._started = True
            if self._total == 0:
                self._finished_event.set()
        metadata: Dict[str, object] = {"total": new_total}
        if should_emit_start:
            self._emit_event("start", metadata=metadata)
        else:
            self._emit_event("progress", metadata={**metadata, "total_updated": True})
        if new_total == 0:
            self._emit_completion(metadata={**metadata, "forced": False, "reason": "no_work"})

    def record_translation_completion(self, index: int, sentence_number: int) -> None:
        """Record the completion of a translation task."""

        now = time.perf_counter()
        with self._lock:
            self._translation_timestamps[sentence_number] = now
            # No completion counter increment here; consumer completions drive progress.
        self._emit_event(
            "progress",
            metadata={
                "stage": "translation",
                "index": index,
                "sentence_number": sentence_number,
            },
        )

    def record_media_completion(self, index: int, sentence_number: int) -> None:
        """Record the completion of a media generation task."""

        now = time.perf_counter()
        should_emit_completion = False
        with self._lock:
            self._media_timestamps[sentence_number] = now
            self._completed += 1
            if self._total is not None and self._completed >= self._total:
                self._finished_event.set()
                should_emit_completion = True
        metadata = {
            "stage": "media",
            "index": index,
            "sentence_number": sentence_number,
        }
        self._emit_event("progress", metadata=metadata)
        if should_emit_completion:
            self._emit_completion(metadata={**metadata, "forced": False})

    def publish_start(self, metadata: Optional[Dict[str, object]] = None) -> None:
        """Emit an explicit ``start`` event with optional context metadata."""

        payload = dict(metadata or {})
        with self._lock:
            if self._total is not None and "total" not in payload:
                payload["total"] = self._total
            self._started = True
        self._emit_event("start", metadata=payload)

    def publish_progress(self, metadata: Optional[Dict[str, object]] = None) -> None:
        """Emit a ``progress`` event without mutating tracker statistics."""

        self._emit_event("progress", metadata=dict(metadata or {}))

    def record_error(
        self, error: BaseException, metadata: Optional[Dict[str, object]] = None
    ) -> None:
        """Emit an ``error`` event describing ``error``."""

        payload = {"forced": True, **(metadata or {})}
        self._emit_event("error", metadata=payload, error=error)

    def snapshot(self, *, include_generated_files: bool = False) -> ProgressSnapshot:
        """Return a snapshot of the current progress statistics."""

        with self._lock:
            completed = self._completed
            total = self._total
            generated_files: Optional[Dict[str, Tuple[str, ...]]] = None
            if include_generated_files and self._generated_files:
                generated_files = {
                    media_type: tuple(paths)
                    for media_type, paths in self._generated_files.items()
                }
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
            generated_files=generated_files,
        )

    def is_complete(self) -> bool:
        """Return whether all expected blocks have been processed."""

        with self._lock:
            if self._total is None:
                return False
            return self._completed >= self._total

    def mark_finished(
        self,
        *,
        reason: Optional[str] = None,
        forced: Optional[bool] = None,
    ) -> None:
        """Signal that monitoring can stop regardless of completion state."""

        self._finished_event.set()
        with self._lock:
            total = self._total
            completed = self._completed
        if forced is None:
            if total is None:
                forced = True
            elif total == 0:
                forced = False
            else:
                forced = completed < total
        metadata: Dict[str, object] = {"forced": forced}
        if reason:
            metadata["reason"] = reason
        self._emit_completion(metadata=metadata)

    def record_generated_file(
        self,
        media_type: str,
        filename: str,
        *,
        metadata: Optional[Dict[str, object]] = None,
    ) -> None:
        """Register a newly generated media artifact and emit a progress event."""

        normalized_type = media_type.strip().lower() or "unknown"
        normalized_filename = filename
        with self._lock:
            existing = list(self._generated_files.get(normalized_type, ()))
            if normalized_filename not in existing:
                existing.append(normalized_filename)
            self._generated_files[normalized_type] = tuple(existing)
        snapshot = self.snapshot(include_generated_files=True)
        payload: Dict[str, object] = {"media_type": normalized_type, "file": normalized_filename}
        if metadata:
            payload.update(metadata)
        self._emit_event(
            "file_chunk_generated",
            snapshot=snapshot,
            metadata=payload,
        )

    def wait(self, timeout: float) -> bool:
        """Wait for completion or for ``timeout`` seconds."""

        return self._finished_event.wait(timeout)

    def register_observer(
        self, callback: Callable[[ProgressEvent], None]
    ) -> Callable[[], None]:
        """Register ``callback`` to receive :class:`ProgressEvent` notifications."""

        with self._lock:
            observers = list(self._observers)
            observers.append(callback)
            self._observers = observers

        def _unregister() -> None:
            with self._lock:
                observers_inner = list(self._observers)
                try:
                    observers_inner.remove(callback)
                except ValueError:
                    return
                self._observers = observers_inner

        return _unregister

    def events(
        self, *, loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> ProgressEventStream:
        """Return an asynchronous iterator of :class:`ProgressEvent` objects."""

        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
        return ProgressEventStream(self, loop)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit_event(
        self,
        event_type: str,
        *,
        snapshot: Optional[ProgressSnapshot] = None,
        metadata: Optional[Dict[str, object]] = None,
        error: Optional[BaseException] = None,
    ) -> None:
        payload: Dict[str, object] = dict(metadata or {})
        event_snapshot = snapshot or self.snapshot()
        event = ProgressEvent(
            event_type=event_type,
            snapshot=event_snapshot,
            timestamp=time.perf_counter(),
            metadata=MappingProxyType(payload),
            error=error,
        )
        with self._lock:
            observers: Tuple[Callable[[ProgressEvent], None], ...] = tuple(self._observers)
        for observer in observers:
            try:
                observer(event)
            except Exception:
                continue

    def _emit_completion(
        self,
        *,
        snapshot: Optional[ProgressSnapshot] = None,
        metadata: Optional[Dict[str, object]] = None,
    ) -> None:
        with self._lock:
            if self._completion_emitted:
                return
            self._completion_emitted = True
        payload = dict(metadata or {})
        if "forced" not in payload:
            payload["forced"] = False
        self._emit_event("complete", snapshot=snapshot, metadata=payload)


__all__ = [
    "ProgressTracker",
    "ProgressSnapshot",
    "ProgressEvent",
    "ProgressEventStream",
]
