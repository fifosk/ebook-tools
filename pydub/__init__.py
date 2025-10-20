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
    def silent(cls, duration: int = 0) -> "AudioSegment":
        return cls(duration=duration)

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

