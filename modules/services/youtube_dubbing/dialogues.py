from __future__ import annotations

import html
import math
import re
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from modules.subtitles import load_subtitle_cues
from modules.subtitles.models import SubtitleCue
from modules.subtitles.merge import merge_youtube_subtitle_cues

from .common import (
    _ASS_DIALOGUE_PATTERN,
    _MIN_DIALOGUE_DURATION_SECONDS,
    _MIN_DIALOGUE_GAP_SECONDS,
    _WHITESPACE_PATTERN,
    _AssDialogue,
)
from .language import _normalize_rtl_word_order

_ASS_TAG_PATTERN = re.compile(r"\{[^}]*\}")
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def _parse_ass_timestamp(value: str) -> float:
    """Convert an ASS timestamp (H:MM:SS.cc) to seconds."""

    trimmed = value.strip()
    if not trimmed:
        raise ValueError("Empty timestamp")
    if "." in trimmed:
        main, fractional = trimmed.split(".", 1)
    else:
        main, fractional = trimmed, "0"
    hours_str, minutes_str, seconds_str = main.split(":")
    hours = int(hours_str)
    minutes = int(minutes_str)
    seconds = int(seconds_str)
    centiseconds = int(fractional.ljust(2, "0")[:2])
    total_seconds = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
    return float(total_seconds)


def _normalize_ass_line(line: str) -> str:
    without_tags = _ASS_TAG_PATTERN.sub(" ", line)
    without_html = _HTML_TAG_PATTERN.sub(" ", without_tags)
    unescaped = html.unescape(without_html)
    normalized = _WHITESPACE_PATTERN.sub(" ", unescaped)
    return normalized.strip()


def _extract_translation(lines: Sequence[str]) -> str:
    """Heuristic to choose the translated line from rendered ASS text."""

    filtered = [line for line in lines if line]
    if not filtered:
        return ""
    if len(filtered) == 1:
        return filtered[0]
    # Most ASS exports place the original first and the translation next.
    if len(filtered) >= 2:
        return filtered[1] or filtered[-1]
    return filtered[-1]


def _parse_ass_dialogues(path: Path) -> List[_AssDialogue]:
    """Return parsed dialogue windows and translations from an ASS file."""

    payload = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    dialogues: List[_AssDialogue] = []
    for line in payload:
        match = _ASS_DIALOGUE_PATTERN.match(line)
        if not match:
            continue
        try:
            start = _parse_ass_timestamp(match.group("start"))
            end = _parse_ass_timestamp(match.group("end"))
        except Exception:
            continue
        text = match.group("text")
        cleaned_lines = [
            _normalize_ass_line(part) for part in text.replace("\\N", "\n").replace("\\n", "\n").splitlines()
        ]
        cleaned_lines = [entry for entry in cleaned_lines if entry]
        translation = _extract_translation(cleaned_lines)
        original_line = cleaned_lines[0] if cleaned_lines else translation
        transliteration_line: Optional[str] = None
        # Our ASS renderer emits: original, translation, transliteration (when enabled).
        # Preserve the transliteration so stitched subtitle generation does not
        # re-run expensive per-cue LLM transliteration.
        if len(cleaned_lines) >= 3:
            transliteration_line = cleaned_lines[2]
        dialogues.append(
            _AssDialogue(
                start=start,
                end=end,
                translation=translation,
                original=original_line,
                transliteration=transliteration_line,
                rtl_normalized=False,
            )
        )
    return [entry for entry in dialogues if entry.end > entry.start]


def _cues_to_dialogues(cues: Sequence[SubtitleCue]) -> List[_AssDialogue]:
    """Convert merged subtitle cues to dialogue windows."""

    dialogues: List[_AssDialogue] = []
    for cue in cues:
        text = _WHITESPACE_PATTERN.sub(" ", cue.as_text()).strip()
        if not text:
            continue
        dialogues.append(
            _AssDialogue(
                start=float(cue.start),
                end=float(cue.end),
                translation=text,
                original=text,
                transliteration=None,
                rtl_normalized=False,
            )
        )
    return dialogues


def _count_words(text: str) -> int:
    """Rough word counter used for pace estimation."""

    return len([token for token in text.strip().split() if token])


def _compute_pace_factor(dialogues: Sequence[_AssDialogue], *, target_wps: float = 2.8) -> float:
    """Estimate a multiplier for reading speed to fit the batch window without overlaps."""

    if not dialogues:
        return 1.0
    total_words = sum(_count_words(entry.translation) for entry in dialogues)
    if total_words <= 0:
        return 1.0
    window_seconds = max((entry.end for entry in dialogues), default=0.0)
    if window_seconds <= 0:
        return 1.0
    words_per_second = total_words / window_seconds
    if words_per_second <= 0:
        return 1.0
    return max(0.5, min(target_wps / words_per_second, 2.0))


def _seconds_to_vtt_timestamp(value: float) -> str:
    """Format seconds into a WebVTT timestamp."""

    total_ms = int(round(value * 1000))
    hours, remainder = divmod(total_ms, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def _enforce_dialogue_gaps(
    dialogues: Sequence[_AssDialogue],
    *,
    min_gap: float = _MIN_DIALOGUE_GAP_SECONDS,
) -> List[_AssDialogue]:
    """Shift dialogue windows to guarantee a small gap, preventing overlaps."""

    adjusted: List[_AssDialogue] = []
    last_end = None
    for entry in dialogues:
        start = entry.start
        end = entry.end
        if last_end is not None:
            desired_start = last_end + min_gap
            if start < desired_start:
                shift = desired_start - start
                start += shift
                end += shift
        if end <= start:
            end = start + _MIN_DIALOGUE_DURATION_SECONDS
        adjusted.append(
            _AssDialogue(
                start=start,
                end=end,
                translation=entry.translation,
                original=entry.original,
                transliteration=entry.transliteration,
                rtl_normalized=entry.rtl_normalized,
                speech_offset=entry.speech_offset,
                speech_duration=entry.speech_duration,
            )
        )
        last_end = end
    return adjusted


def _normalize_dialogue_windows(dialogues: Sequence[_AssDialogue]) -> List[_AssDialogue]:
    """Ensure dialogue windows are ordered, non-overlapping, and minimally long."""

    ordered = sorted(dialogues, key=lambda d: (d.start, d.end))
    enforced = _enforce_dialogue_gaps(ordered)
    normalized: List[_AssDialogue] = []
    for idx, entry in enumerate(enforced):
        start = entry.start
        end = entry.end
        if idx + 1 < len(enforced):
            next_start = enforced[idx + 1].start
            max_end = max(start + _MIN_DIALOGUE_DURATION_SECONDS, next_start - _MIN_DIALOGUE_GAP_SECONDS)
            if end > max_end:
                end = max_end
        if end <= start:
            end = start + _MIN_DIALOGUE_DURATION_SECONDS
        normalized.append(
            _AssDialogue(
                start=start,
                end=end,
                translation=entry.translation,
                original=entry.original,
                transliteration=entry.transliteration,
                rtl_normalized=entry.rtl_normalized,
                speech_offset=entry.speech_offset,
                speech_duration=entry.speech_duration,
            )
        )
    return normalized


def _parse_dialogues(path: Path) -> List[_AssDialogue]:
    """Parse either ASS or SRT/VTT subtitles into dialogue windows."""

    suffix = path.suffix.lower()
    if suffix == ".ass":
        return _normalize_dialogue_windows(_parse_ass_dialogues(path))

    cues = merge_youtube_subtitle_cues(load_subtitle_cues(path))
    return _normalize_dialogue_windows(_cues_to_dialogues(cues))


def _validate_time_window(
    start_time_offset: Optional[float],
    end_time_offset: Optional[float],
) -> Tuple[float, Optional[float]]:
    start_offset = max(0.0, float(start_time_offset or 0.0))
    end_offset = end_time_offset
    if end_offset is not None:
        end_offset = max(0.0, float(end_offset))
        if end_offset <= start_offset:
            raise ValueError("end_time_offset must be greater than start_time_offset")
    return start_offset, end_offset


def _clip_dialogues_to_window(
    dialogues: Sequence[_AssDialogue],
    *,
    start_offset: float,
    end_offset: Optional[float],
) -> List[_AssDialogue]:
    """Return dialogues shifted to start at ``start_offset`` and bounded by ``end_offset``."""

    clipped: List[_AssDialogue] = []
    for entry in dialogues:
        if entry.end <= start_offset:
            continue
        if end_offset is not None and entry.start >= end_offset:
            continue
        new_start = max(0.0, entry.start - start_offset)
        new_end = entry.end
        if end_offset is not None and new_end > end_offset:
            new_end = end_offset
        new_end -= start_offset
        if new_end <= new_start:
            continue
        clipped.append(
            _AssDialogue(
                start=new_start,
                end=new_end,
                translation=entry.translation,
                original=entry.original,
                transliteration=entry.transliteration,
                rtl_normalized=entry.rtl_normalized,
                speech_offset=entry.speech_offset,
                speech_duration=entry.speech_duration,
            )
        )
    return clipped


def _merge_overlapping_dialogues(dialogues: Sequence[_AssDialogue]) -> List[_AssDialogue]:
    """Coalesce overlapping/duplicate dialogue windows with the same text."""

    merged: List[_AssDialogue] = []
    for entry in sorted(dialogues, key=lambda d: (d.start, d.end)):
        text = entry.translation.strip()
        if not text:
            continue
        if merged and merged[-1].translation == text and entry.start <= merged[-1].end + 0.05:
            last = merged[-1]
            merged[-1] = _AssDialogue(
                start=last.start,
                end=max(last.end, entry.end),
                translation=text,
                original=entry.original,
                transliteration=last.transliteration or entry.transliteration,
                rtl_normalized=last.rtl_normalized or entry.rtl_normalized,
                speech_offset=last.speech_offset or entry.speech_offset,
                speech_duration=last.speech_duration or entry.speech_duration,
            )
        else:
            merged.append(
                _AssDialogue(
                    start=entry.start,
                    end=entry.end,
                    translation=text,
                    original=entry.original,
                    transliteration=entry.transliteration,
                    rtl_normalized=entry.rtl_normalized,
                    speech_offset=entry.speech_offset,
                    speech_duration=entry.speech_duration,
                )
            )
    return merged


def _parse_batch_start_seconds(path: Path) -> Optional[float]:
    """Return the start seconds encoded in a batch filename prefix (hh-mm-ss-...)."""

    parts = path.stem.split("-", 3)
    if len(parts) < 3:
        return None
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        return float(hours * 3600 + minutes * 60 + seconds)
    except Exception:
        return None


__all__ = [
    "_ASS_TAG_PATTERN",
    "_HTML_TAG_PATTERN",
    "_clip_dialogues_to_window",
    "_compute_pace_factor",
    "_cues_to_dialogues",
    "_enforce_dialogue_gaps",
    "_extract_translation",
    "_merge_overlapping_dialogues",
    "_normalize_ass_line",
    "_normalize_dialogue_windows",
    "_parse_ass_dialogues",
    "_parse_ass_timestamp",
    "_parse_batch_start_seconds",
    "_parse_dialogues",
    "_seconds_to_vtt_timestamp",
    "_validate_time_window",
]
