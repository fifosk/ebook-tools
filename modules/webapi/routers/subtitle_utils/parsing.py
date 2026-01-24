"""Parsing and validation utilities for subtitle route handlers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status


def as_bool(value: Optional[str | bool], default: bool = False) -> bool:
    """Coerce a string or bool value to a boolean."""

    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def coerce_int(value: Optional[str | int]) -> Optional[int]:
    """Coerce a string or int value to an int, raising HTTPException on failure."""

    if isinstance(value, int):
        return value
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(str(value).strip())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid batch_size") from exc


def parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO timestamp string, returning None if invalid."""

    if value is None:
        return None
    trimmed = str(value).strip()
    if not trimmed:
        return None
    try:
        normalized = trimmed.replace("Z", "+00:00") if trimmed.endswith("Z") else trimmed
        return datetime.fromisoformat(normalized)
    except Exception:
        return None


def parse_ass_font_size(value: Optional[str | int]) -> Optional[int]:
    """Parse and validate ASS font size parameter."""

    if value is None:
        return None
    if isinstance(value, int):
        candidate = value
    else:
        trimmed = str(value).strip()
        if not trimmed:
            return None
        try:
            candidate = int(trimmed)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ass_font_size must be an integer",
            ) from exc
    if candidate <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ass_font_size must be greater than zero",
        )
    if candidate > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ass_font_size must be 200 or smaller",
        )
    return candidate


def parse_ass_emphasis_scale(value: Optional[str | float]) -> Optional[float]:
    """Parse and validate ASS emphasis scale parameter."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        candidate = float(value)
    else:
        trimmed = str(value).strip()
        if not trimmed:
            return None
        try:
            candidate = float(trimmed)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ass_emphasis_scale must be a number",
            ) from exc
    if candidate <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ass_emphasis_scale must be greater than zero",
        )
    if candidate > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ass_emphasis_scale must be 3.0 or smaller",
        )
    return candidate


def parse_timecode_to_seconds(value: str, *, allow_minutes_only: bool) -> float:
    """Parse a timecode string (MM:SS or HH:MM:SS) to seconds."""

    trimmed = value.strip()
    if not trimmed:
        raise ValueError("Empty time value")
    segments = trimmed.split(":")
    hours = 0
    minutes_str: Optional[str] = None
    seconds_str: Optional[str] = None
    if len(segments) == 1:
        if not allow_minutes_only:
            raise ValueError("Time value must include ':' separators")
        try:
            minutes = int(segments[0])
        except ValueError as exc:
            raise ValueError("Relative time must be an integer minute value") from exc
        if minutes < 0:
            raise ValueError("Relative minutes must be non-negative")
        return float(minutes * 60)
    if len(segments) == 2:
        minutes_str, seconds_str = segments
    elif len(segments) == 3:
        hours_str, minutes_str, seconds_str = segments
        try:
            hours = int(hours_str)
        except ValueError as exc:
            raise ValueError("Hours component must be an integer") from exc
        if hours < 0:
            raise ValueError("Hours component cannot be negative")
    else:
        raise ValueError("Time value must be MM:SS or HH:MM:SS")

    if minutes_str is None or seconds_str is None:
        raise ValueError("Minutes and seconds components are required")
    try:
        minutes = int(minutes_str)
        seconds = int(seconds_str)
    except ValueError as exc:
        raise ValueError("Minutes and seconds must be integers") from exc
    if minutes < 0 or seconds < 0:
        raise ValueError("Minutes and seconds must be non-negative")
    if len(segments) == 3 and minutes >= 60:
        raise ValueError("Minutes must be between 00 and 59 when hours are provided")
    if seconds >= 60:
        raise ValueError("Seconds must be between 00 and 59")
    return float(hours * 3600 + minutes * 60 + seconds)


def parse_time_offset(value: Optional[str]) -> float:
    """Parse a time offset string, returning 0.0 if empty."""

    if value is None:
        return 0.0
    trimmed = str(value).strip()
    if not trimmed:
        return 0.0
    try:
        return parse_timecode_to_seconds(trimmed, allow_minutes_only=False)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be in MM:SS or HH:MM:SS format.",
        ) from exc


def parse_end_time(value: Optional[str], start_seconds: float) -> Optional[float]:
    """Parse end time, supporting both absolute and relative (+) formats."""

    if value is None:
        return None
    trimmed = str(value).strip()
    if not trimmed:
        return None
    if trimmed.startswith("+"):
        relative_expr = trimmed[1:].strip()
        if not relative_expr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_time offset cannot be empty.",
            )
        try:
            delta = parse_timecode_to_seconds(relative_expr, allow_minutes_only=True)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Relative end_time must be '+MM:SS', '+HH:MM:SS', or '+<minutes>'.",
            ) from exc
        end_seconds = start_seconds + delta
    else:
        try:
            end_seconds = parse_timecode_to_seconds(trimmed, allow_minutes_only=False)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_time must be in MM:SS or HH:MM:SS format.",
            ) from exc
    if end_seconds <= start_seconds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be after start_time.",
        )
    return float(end_seconds)


def parse_tempo_value(value: Optional[float | str]) -> float:
    """Parse and validate tempo value for dubbing."""

    if value is None:
        return 1.0
    try:
        tempo = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tempo must be a number",
        ) from exc
    if tempo <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tempo must be greater than zero",
        )
    if tempo > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tempo must be 5.0 or lower",
        )
    return tempo


def infer_language_from_name(path: Path) -> Optional[str]:
    """Return a language token parsed from the subtitle filename, if any."""

    from modules.services.youtube_dubbing import _find_language_token

    try:
        return _find_language_token(path)
    except Exception:
        return None


__all__ = [
    "as_bool",
    "coerce_int",
    "parse_timestamp",
    "parse_ass_font_size",
    "parse_ass_emphasis_scale",
    "parse_timecode_to_seconds",
    "parse_time_offset",
    "parse_end_time",
    "parse_tempo_value",
    "infer_language_from_name",
]
