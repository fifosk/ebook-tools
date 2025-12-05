"""Subtitle file parsing and serialization helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Sequence

from .common import (
    ASS_EXTENSION,
    SRT_EXTENSION,
    SRT_TIMESTAMP_PATTERN,
    WEBVTT_HEADER,
)
from .errors import SubtitleProcessingError
from .models import SubtitleCue


def load_subtitle_cues(path: Path) -> List[SubtitleCue]:
    """Parse ``path`` as an SRT/VTT file and return normalized cues."""

    payload = _read_subtitle_text(path)

    if WEBVTT_HEADER.match(payload.splitlines()[0] if payload else ""):
        return _parse_webvtt(payload)
    if path.suffix.lower() == ".vtt":
        return _parse_webvtt(payload)
    return _parse_srt(payload)


def _read_subtitle_text(path: Path) -> str:
    """Return subtitle text with defensive decoding and binary detection."""

    raw = path.read_bytes()
    suffix = path.suffix.lower()

    # Detect common VobSub (.sub) MPEG stream headers that are binary and unsupported.
    if suffix == ".sub":
        header = raw[:16]
        if header.startswith(b"\x00\x00\x01\xba") or header.startswith(b"\x00\x00\x01\xb3"):
            raise ValueError(
                "Binary .sub (VobSub) subtitles are not supported. Please convert to SRT, VTT, or ASS."
            )

    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise ValueError(
        f"Unable to decode subtitle file '{path}'. Please provide a UTF-8/Latin-1 encoded SRT, VTT, or ASS file."
    )


def _parse_srt(payload: str) -> List[SubtitleCue]:
    blocks = _split_blocks(payload)
    cues: List[SubtitleCue] = []
    for raw_block in blocks:
        lines = [line.strip("\ufeff") for line in raw_block.splitlines() if line.strip() != ""]
        if len(lines) < 2:
            continue
        index_line = lines[0]
        try:
            index = int(index_line)
            time_line_index = 1
        except ValueError:
            index = len(cues) + 1
            time_line_index = 0
        if time_line_index >= len(lines):
            continue
        time_line = lines[time_line_index]
        match = SRT_TIMESTAMP_PATTERN.match(time_line)
        if not match:
            continue
        start_seconds = _timestamp_to_seconds(match.group("start"))
        end_seconds = _timestamp_to_seconds(match.group("end"))
        text_lines = lines[time_line_index + 1 :]
        cues.append(
            SubtitleCue(
                index=index,
                start=start_seconds,
                end=end_seconds,
                lines=text_lines,
            )
        )
    return cues


def _parse_webvtt(payload: str) -> List[SubtitleCue]:
    lines = payload.replace("\r\n", "\n").splitlines()
    cues: List[SubtitleCue] = []
    index = 1
    buffer: List[str] = []
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None

    iterator = iter(lines)
    for line in iterator:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("webvtt"):
            continue
        if "-->" in stripped:
            start_value, end_value = [token.strip() for token in stripped.split("-->")]
            start_seconds = _timestamp_to_seconds(start_value)
            end_seconds = _timestamp_to_seconds(end_value)
            buffer = []
            for next_line in iterator:
                if not next_line.strip():
                    break
                buffer.append(next_line.strip())
            cues.append(
                SubtitleCue(
                    index=index,
                    start=start_seconds or 0.0,
                    end=end_seconds or (start_seconds or 0.0),
                    lines=list(buffer),
                )
            )
            index += 1
    return cues


def write_srt(path: Path, cues: Sequence[SubtitleCue]) -> None:
    """Serialize ``cues`` to ``path`` using SRT formatting."""

    fragments: List[str] = []
    for index, cue in enumerate(cues, start=1):
        start_ts = _seconds_to_timestamp(cue.start)
        end_ts = _seconds_to_timestamp(cue.end)
        fragments.append(f"{index}")
        fragments.append(f"{start_ts} --> {end_ts}")
        fragments.extend(cue.lines)
        fragments.append("")
    payload = "\n".join(fragments).strip() + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _timestamp_to_seconds(value: str) -> float:
    sanitized = value.replace(",", ".")
    parts = sanitized.split(":")
    if len(parts) != 3:
        raise SubtitleProcessingError(f"Invalid timestamp: {value!r}")
    hours, minutes, seconds = parts
    seconds_part = float(seconds)
    return int(hours) * 3600 + int(minutes) * 60 + seconds_part


def _seconds_to_timestamp(value: float) -> str:
    total_ms = int(round(value * 1000))
    hours, remainder = divmod(total_ms, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _seconds_to_ass_timestamp(value: float) -> str:
    total_cs = int(round(value * 100))
    hours, remainder = divmod(total_cs, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def _split_blocks(payload: str) -> List[str]:
    sanitized = payload.strip()
    if not sanitized:
        return []
    return re.split(r"\n{2,}", sanitized)


__all__ = [
    "ASS_EXTENSION",
    "SRT_EXTENSION",
    "_parse_srt",
    "_parse_webvtt",
    "_read_subtitle_text",
    "_seconds_to_ass_timestamp",
    "_seconds_to_timestamp",
    "_split_blocks",
    "_timestamp_to_seconds",
    "load_subtitle_cues",
    "write_srt",
]
