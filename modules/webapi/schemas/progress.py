"""Schemas for job progress payloads."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel

from ...progress_tracker import ProgressEvent, ProgressSnapshot


class ProgressSnapshotPayload(BaseModel):
    """Serializable payload for :class:`ProgressSnapshot`."""

    completed: int
    total: Optional[int]
    elapsed: float
    speed: float
    eta: Optional[float]

    @classmethod
    def from_snapshot(cls, snapshot: ProgressSnapshot) -> "ProgressSnapshotPayload":
        return cls(
            completed=snapshot.completed,
            total=snapshot.total,
            elapsed=snapshot.elapsed,
            speed=snapshot.speed,
            eta=snapshot.eta,
        )


class ProgressEventPayload(BaseModel):
    """Serializable payload for :class:`ProgressEvent`."""

    event_type: str
    timestamp: float
    metadata: Dict[str, Any]
    snapshot: ProgressSnapshotPayload
    error: Optional[str] = None

    @classmethod
    def from_event(cls, event: ProgressEvent) -> "ProgressEventPayload":
        metadata = dict(event.metadata)
        error_message = None
        if event.error is not None:
            error_message = str(event.error)
        return cls(
            event_type=event.event_type,
            timestamp=event.timestamp,
            metadata=metadata,
            snapshot=ProgressSnapshotPayload.from_snapshot(event.snapshot),
            error=error_message,
        )
