"""Minimal stub implementation of :mod:`pydub` for test environments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class AudioSegment:
    """Lightweight stand-in for :class:`pydub.AudioSegment`."""

    duration: int = 0
    frame_rate: int = 44100
    raw_data: bytes = b""

    @classmethod
    def empty(cls) -> "AudioSegment":
        """Return an empty audio segment."""

        return cls(duration=0)

    @classmethod
    def silent(cls, duration: int = 0) -> "AudioSegment":
        return cls(duration=duration)

    @classmethod
    def from_file(cls, file: Any, format: Optional[str] = None) -> "AudioSegment":
        """Create an ``AudioSegment`` from a file-like object or filesystem path."""

        if hasattr(file, "read"):
            data = file.read()
        else:
            with open(file, "rb") as fh:
                data = fh.read()
        return cls(duration=len(data), raw_data=data)

    def _spawn(
        self, raw_data: bytes, overrides: Optional[Dict[str, Any]] = None
    ) -> "AudioSegment":
        overrides = overrides or {}
        frame_rate = overrides.get("frame_rate", self.frame_rate)
        return AudioSegment(duration=self.duration, frame_rate=frame_rate, raw_data=raw_data)

    def set_frame_rate(self, frame_rate: int) -> "AudioSegment":
        return AudioSegment(duration=self.duration, frame_rate=frame_rate, raw_data=self.raw_data)

    def __add__(self, other: "AudioSegment") -> "AudioSegment":
        return AudioSegment(duration=self.duration + other.duration)

    def __iadd__(self, other: "AudioSegment") -> "AudioSegment":
        return AudioSegment(duration=self.duration + other.duration)

    def export(
        self,
        out_f: Any,
        format: Optional[str] = None,  # noqa: ARG002 - kept for API compatibility
        bitrate: Optional[str] = None,  # noqa: ARG002 - kept for API compatibility
        **kwargs: Any,  # noqa: ANN401 - match pydub signature flexibility
    ) -> Any:
        """Write the segment's raw data to ``out_f``.

        The real :mod:`pydub` returns the ``out_f`` handle/path, so we mirror that
        behaviour to keep callers working even if they inspect the return value.
        Unknown keyword arguments are accepted for compatibility but ignored.
        """

        if hasattr(out_f, "write"):
            out_f.write(self.raw_data)
            return out_f

        with open(out_f, "wb") as fh:
            fh.write(self.raw_data)
        return out_f

