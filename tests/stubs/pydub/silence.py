"""Stub for :mod:`pydub.silence`."""
from __future__ import annotations

from typing import Any, List, Tuple


def detect_silence(*_args: Any, **_kwargs: Any) -> List[Tuple[int, int]]:
    """Return an empty list of silent ranges."""
    return []


__all__ = ["detect_silence"]
