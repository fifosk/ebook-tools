"""Simplified stub of :mod:`pydub` for unit testing without the dependency."""
from __future__ import annotations


class AudioSegment:
    """Minimal audio segment placeholder."""

    converter: str = ""

    @classmethod
    def empty(cls) -> "AudioSegment":
        return cls()

    def __iadd__(self, other: "AudioSegment") -> "AudioSegment":  # noqa: D401
        return self

    def export(self, *_, **__) -> None:  # pragma: no cover - no-op stub
        return None


__all__ = ["AudioSegment"]
