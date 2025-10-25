"""Utilities for serializing progress events."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from ...progress_tracker import ProgressEvent, ProgressSnapshot


def serialize_progress_event(event: ProgressEvent) -> Dict[str, Any]:
    """Convert ``event`` into a JSON-serializable mapping."""

    snapshot = event.snapshot
    return {
        "event_type": event.event_type,
        "timestamp": event.timestamp,
        "metadata": dict(event.metadata),
        "error": str(event.error) if event.error else None,
        "snapshot": {
            "completed": snapshot.completed,
            "total": snapshot.total,
            "elapsed": snapshot.elapsed,
            "speed": snapshot.speed,
            "eta": snapshot.eta,
            "generated_files": {
                media_type: list(paths)
                for media_type, paths in (snapshot.generated_files or {}).items()
            }
            if snapshot.generated_files
            else None,
        },
    }


def deserialize_progress_event(payload: Mapping[str, Any]) -> ProgressEvent:
    """Reconstruct a :class:`ProgressEvent` from serialized ``payload``."""

    snapshot_data = payload.get("snapshot", {})
    snapshot = ProgressSnapshot(
        completed=int(snapshot_data.get("completed", 0)),
        total=snapshot_data.get("total"),
        elapsed=float(snapshot_data.get("elapsed", 0.0)),
        speed=float(snapshot_data.get("speed", 0.0)),
        eta=snapshot_data.get("eta"),
        generated_files=(
            {
                str(media_type): tuple(str(path) for path in paths)
                for media_type, paths in snapshot_data.get("generated_files", {}).items()
            }
            if snapshot_data.get("generated_files")
            else None
        ),
    )
    error_message = payload.get("error")
    error: Optional[BaseException] = None
    if error_message:
        error = RuntimeError(str(error_message))
    metadata = dict(payload.get("metadata", {}))
    return ProgressEvent(
        event_type=str(payload.get("event_type", "progress")),
        snapshot=snapshot,
        timestamp=float(payload.get("timestamp", 0.0)),
        metadata=metadata,
        error=error,
    )


__all__ = ["serialize_progress_event", "deserialize_progress_event"]
