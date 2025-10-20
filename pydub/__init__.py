"""Minimal stub implementation of :mod:`pydub` for test environments."""

from __future__ import annotations

from dataclasses import dataclass
import io
import os
import wave
from typing import Any, Dict, Optional


@dataclass
class AudioSegment:
    """Lightweight stand-in for :class:`pydub.AudioSegment`."""

    duration: int = 0
    frame_rate: int = 44100
    raw_data: bytes = b""

    @property
    def duration_seconds(self) -> float:
        """Return the segment duration expressed in seconds."""

        return self.duration / 1000 if self.duration else 0.0

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

        payload: bytes
        target_is_path = isinstance(out_f, (str, bytes, os.PathLike))

        def _write_bytes(data: bytes) -> None:
            if hasattr(out_f, "write"):
                out_f.write(data)
            else:
                with open(out_f, "wb") as fh:
                    fh.write(data)

        fmt = format
        if fmt is None and target_is_path and isinstance(out_f, (str, bytes, os.PathLike)):
            fmt = os.fspath(out_f).split(".")[-1].lower() if "." in os.fspath(out_f) else None

        if fmt == "wav":
            frame_rate = self.frame_rate or 44100
            sample_width = 2
            raw = self.raw_data or (b"\x00" * sample_width)
            # Ensure we write at least one frame so downstream tools like FFmpeg accept it.
            if len(raw) % sample_width != 0:
                raw += b"\x00" * (sample_width - (len(raw) % sample_width))
            if len(raw) == 0:
                raw = b"\x00" * sample_width

            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wav_out:
                wav_out.setnchannels(1)
                wav_out.setsampwidth(sample_width)
                wav_out.setframerate(frame_rate)
                wav_out.writeframes(raw)
            payload = buffer.getvalue()
            _write_bytes(payload)
            return out_f

        payload = self.raw_data
        _write_bytes(payload)
        return out_f

