"""Common subtitle processing exceptions."""

from __future__ import annotations


class SubtitleProcessingError(RuntimeError):
    """Raised when subtitle parsing or processing fails."""


class SubtitleJobCancelled(RuntimeError):
    """Raised when a subtitle job is cancelled during processing."""


__all__ = ["SubtitleJobCancelled", "SubtitleProcessingError"]
