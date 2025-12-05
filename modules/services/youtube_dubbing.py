"""Helpers for discovering downloaded YouTube videos and generating dubbed tracks."""

from __future__ import annotations

import html
import json
import math
import os
import re
import threading
import shutil
import subprocess
import tempfile
import unicodedata
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple, TextIO

from pydub import AudioSegment, effects

from modules import config_manager as cfg, language_policies
from modules import logging_manager as log_mgr
from modules.audio.tts import generate_audio
from modules.audio_video_generator import change_audio_tempo
from modules.core.rendering.constants import LANGUAGE_CODES
from modules.progress_tracker import ProgressTracker
from modules.services.job_manager import PipelineJob, PipelineJobStatus
from modules.subtitles import load_subtitle_cues
from modules.subtitles.models import SubtitleCue, SubtitleColorPalette
from modules.subtitles.processing import (
    merge_youtube_subtitle_cues,
    _translate_text as _translate_subtitle_text,
    _target_uses_non_latin_script,
    _build_output_cues,
    write_srt,
    CueTextRenderer,
    _SubtitleFileWriter,
)
from modules.services.youtube_subtitles import trim_stem_preserving_id
from modules.retry_annotations import is_failure_annotation
from modules.transliteration import get_transliterator, TransliterationService
from modules.services.file_locator import FileLocator

logger = log_mgr.get_logger().getChild("services.youtube_dubbing")

DEFAULT_YOUTUBE_VIDEO_ROOT = Path("/Volumes/Data/Video/Youtube").expanduser()

_VIDEO_EXTENSIONS = {"mp4", "mkv", "mov", "webm", "m4v"}
_SUBTITLE_EXTENSIONS = {"ass", "srt", "vtt", "sub"}
_LANGUAGE_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,16}$")
_DEFAULT_ORIGINAL_MIX_PERCENT = 15.0
_DEFAULT_FLUSH_SENTENCES = 10
_TEMP_DIR = Path("/tmp")
_SUBTITLE_MIRROR_DIR = (
    Path(os.environ.get("SUBTITLE_SOURCE_DIR") or "/Volumes/Data/Download/Subtitles").expanduser()
)
_GAP_MIX_SCALAR = 0.25
_GAP_MIX_MAX_PERCENT = 5.0
_TARGET_DUB_HEIGHT = 480
_YOUTUBE_ID_PATTERN = re.compile(r"\[[a-z0-9_-]{8,15}\]", re.IGNORECASE)
_ASS_DIALOGUE_PATTERN = re.compile(
    r"^Dialogue:\s*[^,]*,(?P<start>[^,]+),(?P<end>[^,]+),[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,(?P<text>.*)$",
    re.IGNORECASE,
)
_ASS_TAG_PATTERN = re.compile(r"\{[^}]*\}")
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_MIN_DIALOGUE_GAP_SECONDS = 0.0
_MIN_DIALOGUE_DURATION_SECONDS = 0.1
_LLM_WORKER_CAP = 4
_ENCODING_WORKER_CAP = 10
_WEBVTT_HEADER = "WEBVTT\n\n"
_WEBVTT_STYLE_BLOCK = """STYLE
::cue(.original) { color: #facc15; }
::cue(.transliteration) { color: #f97316; }
::cue(.translation) { color: #22c55e; }

"""
_RTL_SCRIPT_PATTERN = re.compile(r"[\u0590-\u08FF]")
_RTL_LANGUAGE_HINTS = {
    "arabic",
    "ar",
    "farsi",
    "fa",
    "hebrew",
    "he",
    "iw",
    "persian",
    "ps",
    "pashto",
    "ur",
    "urdu",
}


@dataclass(frozen=True)
class YoutubeNasSubtitle:
    """Description of a subtitle file stored alongside a downloaded video."""

    path: Path
    language: Optional[str]
    format: str


@dataclass(frozen=True)
class YoutubeNasVideo:
    """Metadata for a downloaded YouTube video on the NAS."""

    path: Path
    size_bytes: int
    modified_at: datetime
    subtitles: List[YoutubeNasSubtitle]
    source: str = "youtube"


@dataclass(frozen=True)
class _AssDialogue:
    """Parsed ASS dialogue entry with translation text."""

    start: float
    end: float
    translation: str
    original: str
    transliteration: Optional[str] = None
    rtl_normalized: bool = False
    speech_offset: Optional[float] = None
    speech_duration: Optional[float] = None

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class _DubJobCancelled(Exception):
    """Raised when a YouTube dubbing job is interrupted."""


def _language_uses_non_latin(label: Optional[str]) -> bool:
    """Return True when the language hint expects non-Latin script output."""

    normalized = (label or "").strip()
    if not normalized:
        return False
    if language_policies.is_non_latin_language_hint(normalized):
        return True
    return _target_uses_non_latin_script(normalized)


def _is_rtl_language(label: Optional[str]) -> bool:
    """Return True when the provided language label hints at an RTL script."""

    normalized = (label or "").strip().lower().replace("_", "-")
    if not normalized:
        return False
    if normalized in _RTL_LANGUAGE_HINTS:
        return True
    tokens = [token for token in re.split(r"[^a-z0-9]+", normalized) if token]
    return any(token in _RTL_LANGUAGE_HINTS for token in tokens)


def _normalize_rtl_word_order(text: str, language: Optional[str], *, force: bool = False) -> str:
    """
    Return ``text`` with RTL words ordered left-to-right for display while
    preserving in-word character order.
    """

    if not text or not _is_rtl_language(language):
        return text
    if not force and not _RTL_SCRIPT_PATTERN.search(text):
        return text
    tokens = [segment for segment in text.split() if segment]
    if len(tokens) <= 1:
        return text
    return " ".join(reversed(tokens))


def _transliterate_text(
    transliterator: TransliterationService,
    text: str,
    language: str,
) -> str:
    """Return plain transliteration text from the service result."""

    result = transliterator.transliterate(text, language)
    if hasattr(result, "text"):
        try:
            return str(getattr(result, "text") or "")
        except Exception:
            return ""
    if isinstance(result, str):
        return result
    return ""


def _resolve_worker_count(total_items: int, requested: Optional[int] = None) -> int:
    settings = cfg.get_settings()
    configured = requested if requested is not None else settings.job_max_workers
    if configured is None or configured <= 0:
        configured = 1
    return max(1, min(int(configured), max(1, total_items)))


def _resolve_llm_worker_count(total_items: int) -> int:
    """Return a conservative worker count for LLM-backed steps to avoid flooding APIs."""

    settings = cfg.get_settings()
    configured = settings.job_max_workers
    if configured is None or configured <= 0:
        configured = 1
    capped = min(int(configured), _LLM_WORKER_CAP)
    return max(1, min(capped, max(1, total_items)))


def _resolve_encoding_worker_count(total_items: int, requested: Optional[int] = None) -> int:
    """Return a worker count for encoding tasks capped at a safe ceiling."""

    settings = cfg.get_settings()
    configured = requested if requested is not None else settings.job_max_workers
    if configured is None or configured <= 0:
        configured = _ENCODING_WORKER_CAP
    capped = min(int(configured), _ENCODING_WORKER_CAP)
    return max(1, min(capped, max(1, total_items)))


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
        dialogues.append(
            _AssDialogue(
                start=start,
                end=end,
                translation=translation,
                original=original_line,
                transliteration=None,
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
    # Sum explicit dialogue windows and a minimal gap between them to avoid collisions.
    total_time = 0.0
    for idx, entry in enumerate(dialogues):
        total_time += max(0.05, entry.end - entry.start)
        if idx > 0:
            total_time += _MIN_DIALOGUE_GAP_SECONDS
    duration = max(0.1, total_time)
    words = sum(_count_words(entry.translation) for entry in dialogues)
    wps = words / duration
    required = wps / target_wps if target_wps > 0 else 1.0
    if required <= 1.0:
        return 1.0
    return min(1.4, required)


def _seconds_to_vtt_timestamp(value: float) -> str:
    """Format seconds into a WebVTT timestamp."""

    total_ms = int(round(value * 1000))
    hours, remainder = divmod(total_ms, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def _enforce_dialogue_gaps(dialogues: Sequence[_AssDialogue], *, min_gap: float = _MIN_DIALOGUE_GAP_SECONDS) -> List[_AssDialogue]:
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


def _find_language_token(path: Path) -> Optional[str]:
    stem_parts = path.stem.split(".")
    if len(stem_parts) < 2:
        return None
    candidate = stem_parts[-1].strip()
    if not candidate:
        return None
    if _LANGUAGE_TOKEN_PATTERN.match(candidate):
        return candidate
    return None


def _resolve_language_code(label: Optional[str]) -> str:
    if not label:
        return "en"
    normalized = label.strip()
    if not normalized:
        return "en"
    for name, code in LANGUAGE_CODES.items():
        if normalized.casefold() == name.casefold():
            return code
    return normalized


def _measure_active_window(
    audio: AudioSegment,
    *,
    silence_floor: float = -50.0,
    head_padding_ms: int = 60,
) -> Tuple[float, float]:
    """Return (offset_seconds, duration_seconds) of voiced audio inside ``audio``."""

    if len(audio) == 0:
        return 0.0, 0.0
    threshold = max(silence_floor, (audio.dBFS if math.isfinite(audio.dBFS) else silence_floor) - 18.0)
    step_ms = 20
    first = None
    last = None
    for position in range(0, len(audio), step_ms):
        frame = audio[position : position + step_ms]
        if frame.dBFS > threshold:
            first = position if first is None else first
            last = position + len(frame)
    if first is None or last is None:
        return 0.0, len(audio) / 1000.0
    start_ms = max(0, first - head_padding_ms)
    end_ms = min(len(audio), last + head_padding_ms)
    return start_ms / 1000.0, max(0.0, (end_ms - start_ms) / 1000.0)


def _sanitize_for_tts(text: str) -> str:
    """Clean noisy markers while preserving diacritics for languages like Czech/Hungarian."""

    try:
        cleaned = text.replace(">>", " ").replace("<<", " ").replace("»", " ").replace("«", " ")
        cleaned = _HTML_TAG_PATTERN.sub(" ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or text
    except Exception:
        return text


def _build_atempo_filters(target_ratio: float) -> List[float]:
    """Break a tempo ratio into ffmpeg-safe atempo factors (each 0.5–2.0)."""

    factors: List[float] = []
    ratio = max(0.01, target_ratio)
    while ratio > 2.0:
        factors.append(2.0)
        ratio /= 2.0
    while ratio < 0.5:
        factors.append(0.5)
        ratio *= 2.0
    factors.append(ratio)
    return factors


def _time_stretch_to_duration(segment: AudioSegment, target_ms: int) -> AudioSegment:
    """Time-stretch ``segment`` toward ``target_ms`` with pitch-preserving atempo."""

    if target_ms <= 0:
        return segment
    duration_ms = len(segment)
    if duration_ms <= 0:
        return segment
    ratio = duration_ms / max(target_ms, 1)
    if abs(ratio - 1.0) < 0.01:
        return segment

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, prefix="stretch-in-", dir=_TEMP_DIR) as in_handle:
        temp_in = Path(in_handle.name)
        segment.export(temp_in, format="wav", parameters=["-acodec", "pcm_s16le"])
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, prefix="stretch-out-", dir=_TEMP_DIR) as out_handle:
        temp_out = Path(out_handle.name)

    filters = _build_atempo_filters(ratio)
    filter_arg = ",".join(f"atempo={factor:.5f}" for factor in filters)
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(temp_in),
        "-vn",
        "-ac",
        str(segment.channels or 2),
        "-ar",
        str(segment.frame_rate),
        "-filter:a",
        filter_arg,
        "-f",
        "wav",
        str(temp_out),
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode != 0:
            logger.warning(
                "ffmpeg atempo stretch failed (exit %s); falling back to original segment",
                result.returncode,
                extra={"event": "youtube.dub.atempo.failed"},
            )
            return segment
        stretched = AudioSegment.from_file(temp_out, format="wav")
    finally:
        temp_in.unlink(missing_ok=True)
        temp_out.unlink(missing_ok=True)

    # Final pad/trim within a tiny tolerance to hit the target window.
    final = stretched
    if len(final) > target_ms:
        final = final[:target_ms]
    elif len(final) < target_ms:
        final += AudioSegment.silent(duration=target_ms - len(final), frame_rate=final.frame_rate)
    return _coerce_channels(final.set_frame_rate(segment.frame_rate), segment.channels)


def _fit_segment_to_window(
    segment: AudioSegment,
    target_seconds: float,
    *,
    max_speedup: float = 1.0,
) -> AudioSegment:
    """
    Keep synthesized audio near its intended window without padding/trim.

    We avoid stretching or padding; any gating happens via scheduling downstream.
    """

    target_ms = max(50, int(target_seconds * 1000))
    if len(segment) <= 0:
        return AudioSegment.silent(duration=target_ms, frame_rate=segment.frame_rate)
    return segment


def _subtitle_matches_video(video_path: Path, subtitle_path: Path) -> bool:
    """Return True if ``subtitle_path`` appears to belong to ``video_path``."""

    base_stem = video_path.stem
    subtitle_name = subtitle_path.name
    if subtitle_name.startswith(f"{base_stem}."):
        return True
    if subtitle_name.startswith(f"{base_stem}_"):
        return True
    if subtitle_name.startswith(f"{base_stem}-"):
        return True
    return False


def _classify_video_source(video_path: Path) -> str:
    """Return a source label for NAS videos to distinguish YouTube downloads."""

    stem = video_path.stem.lower()
    normalized = video_path.name.replace("_", "-")
    if stem.endswith("-yt") or stem.endswith("_yt"):
        return "youtube"
    if _YOUTUBE_ID_PATTERN.search(normalized):
        return "youtube"
    return "nas_video"


def _normalize_language_hint(raw: Optional[str]) -> Optional[str]:
    """Return a sanitized language tag suitable for filenames."""

    if not raw:
        return None
    token = raw.strip().replace(" ", "-").lower()
    token = re.sub(r"[^a-z0-9_-]+", "", token)
    if not token:
        return None
    if len(token) > 16:
        token = token[:16]
    return token


def _synthesise_track_from_ass(
    subtitle_path: Path,
    *,
    language: str,
    voice: str,
    tempo: float,
    macos_reading_speed: int,
    llm_model: Optional[str],
    tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
    max_workers: Optional[int] = None,
    start_time_offset: Optional[float] = None,
    end_time_offset: Optional[float] = None,
    progress_milestones: Optional[Sequence[float]] = None,
    progressive_flush: Optional[Callable[[AudioSegment, float], None]] = None,
) -> Tuple[AudioSegment, List[_AssDialogue]]:
    target_rate = 44100
    target_channels = 2
    start_offset, end_offset = _validate_time_window(start_time_offset, end_time_offset)
    all_dialogues = _parse_dialogues(subtitle_path)
    source_language = _find_language_token(subtitle_path) or language
    clipped_dialogues = _clip_dialogues_to_window(
        all_dialogues,
        start_offset=start_offset,
        end_offset=end_offset,
    )
    translated_dialogues: List[_AssDialogue] = []
    needs_translation = source_language and language and source_language.lower() != language.lower()
    total_dialogues = len(clipped_dialogues)
    if tracker is not None:
        tracker.set_total(total_dialogues)
        tracker.publish_progress(
            {"stage": "translation", "total": total_dialogues, "source": source_language, "target": language}
        )
    for idx, entry in enumerate(clipped_dialogues):
        translated_text = entry.translation
        if needs_translation:
            try:
                translated_text = _translate_subtitle_text(
                    entry.translation,
                    source_language=source_language or language,
                    target_language=language,
                    llm_model=llm_model,
                )
                if is_failure_annotation(translated_text):
                    translated_text = entry.translation
            except Exception:
                translated_text = entry.translation
        if tracker is not None and needs_translation:
            tracker.record_step_completion(
                stage="translation",
                index=idx + 1,
                total=total_dialogues,
                metadata={"start": entry.start, "end": entry.end},
            )
        translated_dialogues.append(
            _AssDialogue(
                start=entry.start,
                end=entry.end,
                translation=translated_text,
                original=entry.original,
            )
        )
    translated_dialogues = [entry for entry in translated_dialogues if entry.translation]
    if not translated_dialogues:
        raise ValueError("No dialogue entries found in ASS subtitle.")

    total_segments = len(translated_dialogues)
    workers = _resolve_worker_count(total_segments, requested=max_workers)
    if progressive_flush is not None:
        # Keep ordering predictable for progressive flushes.
        workers = 1
    segments: List[Optional[Tuple[_AssDialogue, AudioSegment]]] = [None] * total_segments

    def _guard() -> None:
        if stop_event is not None and stop_event.is_set():
            raise _DubJobCancelled()

    def _synthesise(index: int, entry: _AssDialogue) -> Tuple[int, _AssDialogue, AudioSegment]:
        _guard()
        sanitized = _sanitize_for_tts(entry.translation)
        segment = generate_audio(sanitized, language, voice, macos_reading_speed)
        fitted = _fit_segment_to_window(segment, entry.duration)
        normalized = _coerce_channels(fitted.set_frame_rate(target_rate), target_channels)
        return index, entry, normalized

    if tracker is not None:
        tracker.publish_progress(
            {
                "stage": "synthesis",
                "segments": total_segments,
                "workers": workers,
            }
        )

    try:
        if workers <= 1:
            for idx, dialogue in enumerate(translated_dialogues):
                _guard()
                _, entry, fitted = _synthesise(idx, dialogue)
                segments[idx] = (entry, fitted)
                if tracker is not None:
                    tracker.record_step_completion(
                        stage="synthesis",
                        index=idx + 1,
                        total=total_segments,
                        metadata={"start": entry.start, "end": entry.end},
                    )
        else:
            futures = []
            with ThreadPoolExecutor(max_workers=workers) as executor:
                for idx, dialogue in enumerate(translated_dialogues):
                    futures.append(executor.submit(_synthesise, idx, dialogue))
                completed = 0
                for future in as_completed(futures):
                    _guard()
                    idx, entry, fitted = future.result()
                    segments[idx] = (entry, fitted)
                    completed += 1
                    if tracker is not None:
                        tracker.record_step_completion(
                            stage="synthesis",
                            index=completed,
                            total=total_segments,
                            metadata={"start": entry.start, "end": entry.end},
                        )
    except _DubJobCancelled:
        for future in locals().get("futures", []):
            future.cancel()
        raise

    resolved_segments: List[Tuple[_AssDialogue, AudioSegment]] = [
        segment for segment in segments if segment is not None
    ]
    if not resolved_segments:
        raise ValueError("No translatable dialogue lines were found in the subtitle.")

    clip_end = end_offset - start_offset if end_offset is not None else None
    max_end = clip_end if clip_end is not None else max(entry.end for entry, _ in resolved_segments)
    base_rate = resolved_segments[0][1].frame_rate
    # Keep a tiny buffer to avoid truncating the last syllable, but stay close to the subtitle window.
    track = AudioSegment.silent(duration=int(max_end * 1000) + 100, frame_rate=base_rate)
    if tracker is not None:
        tracker.publish_progress({"stage": "mixdown", "duration_seconds": max_end})
    milestone_index = 0
    milestones = list(progress_milestones or [])
    for entry, audio in resolved_segments:
        _guard()
        start_ms = int(entry.start * 1000)
        track = track.overlay(audio, position=start_ms)
        while milestone_index < len(milestones) and entry.end >= milestones[milestone_index]:
            if progressive_flush is not None:
                try:
                    progressive_flush(track, milestones[milestone_index])
                except Exception:
                    logger.warning("Progressive mux failed for milestone %.2f", milestones[milestone_index], exc_info=True)
            milestone_index += 1
    return track, [entry for entry, _ in resolved_segments]


def _format_clip_suffix(start_offset: float, end_offset: Optional[float]) -> str:
    # Keep output names compact; we no longer append millisecond offsets for non-zero starts.
    return ""


def _clamp_original_mix(percent: Optional[float]) -> float:
    if percent is None:
        return _DEFAULT_ORIGINAL_MIX_PERCENT
    try:
        value = float(percent)
    except Exception:
        return _DEFAULT_ORIGINAL_MIX_PERCENT
    if math.isnan(value) or math.isinf(value):
        return _DEFAULT_ORIGINAL_MIX_PERCENT
    return max(0.0, min(100.0, value))


def _compute_reference_rms(audios: Sequence[AudioSegment]) -> float:
    """Return a median-ish RMS reference for dubbing segments."""

    values = [audio.rms for audio in audios if audio and audio.rms]
    if not values:
        return 1.0
    values.sort()
    mid = len(values) // 2
    if len(values) % 2 == 1:
        return float(values[mid])
    return float((values[mid - 1] + values[mid]) / 2.0)


def _compute_underlay_gain_db(reference_rms: float, original_rms: float, mix_percent: float) -> float:
    """
    Compute the gain (in dB) that makes the original audio sit at ``mix_percent`` of the dubbed loudness.

    Falls back to a gentle attenuation when RMS values are missing.
    """

    if mix_percent <= 0:
        return -120.0
    target_linear = max(0.0, min(1.0, mix_percent / 100.0))
    dubbed_rms = max(reference_rms or 0.0, 1.0)
    original_rms = max(original_rms or 0.0, 1.0)
    relative_linear = target_linear * (dubbed_rms / original_rms)
    if relative_linear <= 0:
        return -120.0
    return 20 * math.log10(relative_linear)


def _resolve_gap_mix_percent(original_mix_percent: float) -> float:
    """Return a quieter mix percentage for silent gaps to avoid loud jumps."""

    clamped = _clamp_original_mix(original_mix_percent)
    scaled = clamped * _GAP_MIX_SCALAR
    return max(0.0, min(_GAP_MIX_MAX_PERCENT, scaled))


def _coerce_channels(segment: AudioSegment, target_channels: int) -> AudioSegment:
    """Safely convert to ``target_channels`` by downmixing to mono first when needed."""

    if target_channels <= 0 or segment.channels == target_channels:
        return segment
    if target_channels == 1:
        return segment.set_channels(1)
    if segment.channels == 1:
        return segment.set_channels(target_channels)
    mono = segment.set_channels(1)
    if target_channels == 1:
        return mono
    return mono.set_channels(target_channels)


def _apply_audio_gain_to_clip(path: Path, gain_db: float) -> Path:
    """Apply an audio gain to a video clip while copying video streams."""

    if abs(gain_db) < 0.01:
        return path
    if not _has_audio_stream(path):
        return path
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    with tempfile.NamedTemporaryFile(
        suffix=path.suffix or ".mp4",
        delete=False,
        prefix="dub-gain-",
        dir=_TEMP_DIR,
    ) as handle:
        target = Path(handle.name)
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(path),
        "-c:v",
        "copy",
        "-af",
        f"volume={gain_db:.4f}dB",
        "-c:a",
        "aac",
        str(target),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        target.unlink(missing_ok=True)
        return path
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
    return target


def _apply_gap_audio_mix(path: Path, *, mix_percent: float, reference_rms: float) -> Path:
    """Downmix gap clip audio to a quieter underlay level to avoid jumps."""

    gap_mix_percent = _resolve_gap_mix_percent(mix_percent)
    if gap_mix_percent >= 99.0:
        return path
    if gap_mix_percent <= 0.0:
        return _apply_audio_gain_to_clip(path, -120.0)
    clip_rms = 1.0
    try:
        clip_audio = _coerce_channels(AudioSegment.from_file(path).set_frame_rate(44100), 2)
        if clip_audio.rms:
            clip_rms = clip_audio.rms
    except Exception:
        clip_rms = 1.0
    gain_db = _compute_underlay_gain_db(reference_rms, clip_rms, gap_mix_percent)
    return _apply_audio_gain_to_clip(path, gain_db)


def _mix_with_original_audio(
    dubbed_track: AudioSegment,
    source_video: Path,
    *,
    original_mix_percent: float,
    expected_duration_seconds: Optional[float] = None,
    original_audio: Optional[AudioSegment] = None,
) -> AudioSegment:
    """Blend the original audio underneath the dubbed track at the given percentage."""

    mix_percent = _clamp_original_mix(original_mix_percent)
    if mix_percent <= 0:
        return dubbed_track

    if original_audio is None:
        try:
            original = AudioSegment.from_file(source_video)
        except Exception:
            logger.warning(
                "Unable to read original audio for underlay; continuing without mix",
                extra={"event": "youtube.dub.mix.failed", "video": source_video.as_posix()},
                exc_info=True,
            )
            return dubbed_track
    else:
        original = original_audio

    target_rate = dubbed_track.frame_rate
    target_channels = dubbed_track.channels
    original = _coerce_channels(original.set_frame_rate(target_rate), target_channels)

    max_duration_ms = None
    if expected_duration_seconds is not None:
        max_duration_ms = int(expected_duration_seconds * 1000)
    target_ms = len(dubbed_track) if max_duration_ms is None else max(max_duration_ms, len(dubbed_track))
    # Stretch the original slice to match the dubbed duration so both tracks stay aligned.
    if len(original) != target_ms and target_ms > 0:
        original = _time_stretch_to_duration(original, target_ms)
    if len(original) < target_ms:
        original += AudioSegment.silent(duration=target_ms - len(original), frame_rate=target_rate)
    elif len(original) > target_ms:
        original = original[:target_ms]

    # Normalize the underlay relative to the dubbed track so the percentage reflects loudness, not just peak.
    dubbed_rms = dubbed_track.rms or 1
    original_rms = original.rms or 1
    target_linear = mix_percent / 100.0
    relative_linear = target_linear * (dubbed_rms / original_rms)
    if relative_linear <= 0:
        return dubbed_track
    original_gain_db = 20 * math.log10(relative_linear)

    base = dubbed_track - 1.0  # Leave a little headroom before mixing in the underlay.
    return base.overlay(original.apply_gain(original_gain_db))


def _has_audio_stream(path: Path) -> bool:
    """Return True if ffprobe detects an audio stream."""

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            return False
        return b"audio" in result.stdout
    except Exception:
        return False


def _has_video_stream(path: Path) -> bool:
    """Return True if ffprobe detects a valid video stream with a known pixel format."""

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=pix_fmt,width,height",
                "-of",
                "json",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            return False
        try:
            payload = json.loads(result.stdout.decode() or "{}")
        except Exception:
            return False
        streams = payload.get("streams") or []
        if not streams:
            return False
        stream = streams[0] or {}
        pix_fmt = (stream.get("pix_fmt") or "").strip()
        if not pix_fmt:
            return False
        pix_fmt_lower = pix_fmt.lower()
        if pix_fmt_lower in {"unknown", "none"}:
            return False
        # If width/height are present, ensure they are sane (>0).
        width = stream.get("width")
        height = stream.get("height")
        if width is not None and height is not None:
            try:
                if int(width) <= 0 or int(height) <= 0:
                    return False
            except Exception:
                return False
        return True
    except Exception:
        return False


def _probe_duration_seconds(path: Path) -> float:
    """Return media duration in seconds, or 0 on failure."""

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            return 0.0
        return float(result.stdout.decode().strip() or 0.0)
    except Exception:
        return 0.0


def _probe_video_height(path: Path) -> Optional[int]:
    """Return the primary video stream height, or None when unavailable."""

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=height",
                "-of",
                "csv=p=0",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            return None
        payload = result.stdout.decode().strip()
        return int(payload) if payload else None
    except Exception:
        return None


def _resolve_target_width(target_height: int) -> int:
    """Return an even width roughly matching 16:9 for the requested height."""

    if target_height <= 0:
        return 0
    width = int(round(target_height * 16 / 9))
    if width % 2:
        width += 1
    return max(2, width)


def _downscale_video(
    path: Path,
    *,
    target_height: int = _TARGET_DUB_HEIGHT,
    preserve_aspect_ratio: bool = True,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Downscale ``path`` to ``target_height`` using H.264 while copying other streams.
    Returns the final path (same as input when no change was needed). When
    ``output_path`` is provided, the final file is moved there (useful when the
    input lives on a RAM disk and the destination is NAS storage).
    """

    destination = output_path or path
    if target_height <= 0:
        if destination != path and path.exists():
            try:
                shutil.move(str(path), destination)
                return destination
            except Exception:
                logger.debug("Unable to move %s to %s", path, destination, exc_info=True)
        return path
    current_height = _probe_video_height(path)
    if current_height is not None and current_height <= target_height:
        if destination != path and path.exists():
            try:
                shutil.move(str(path), destination)
                return destination
            except Exception:
                logger.debug("Unable to move %s to %s", path, destination, exc_info=True)
        return path
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"

    def _make_temp_output(prefix: str) -> Path:
        candidates = [_TEMP_DIR, Path("/tmp")]
        for candidate in candidates:
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    suffix=path.suffix or ".mp4",
                    delete=False,
                    prefix=prefix,
                    dir=candidate,
                ) as handle:
                    return Path(handle.name)
            except Exception:
                continue
        with tempfile.NamedTemporaryFile(suffix=path.suffix or ".mp4", delete=False, prefix=prefix) as handle:
            return Path(handle.name)

    temp_output = _make_temp_output("dub-resize-")
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(path),
        "-map",
        "0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-vf",
        f"scale={'-2' if preserve_aspect_ratio else _resolve_target_width(target_height)}:{target_height}",
        "-c:a",
        "copy",
        "-c:s",
        "copy",
        "-movflags",
        "+faststart+frag_keyframe+empty_moov+default_base_moof",
        str(temp_output),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        temp_output.unlink(missing_ok=True)
        logger.warning(
            "Unable to downscale dubbed output to %sp (exit %s)",
            target_height,
            result.returncode,
            extra={"event": "youtube.dub.downscale.failed", "path": path.as_posix()},
        )
        if destination != path and path.exists():
            try:
                shutil.move(str(path), destination)
                return destination
            except Exception:
                logger.debug("Unable to move failed downscale source %s to %s", path, destination, exc_info=True)
        return path
    try:
        shutil.move(str(temp_output), destination)
    except Exception:
        logger.debug("Unable to replace %s with downscaled copy", destination, exc_info=True)
        temp_output.unlink(missing_ok=True)
        if destination != path and path.exists():
            try:
                shutil.move(str(path), destination)
            except Exception:
                logger.debug("Unable to move original %s to %s after downscale failure", path, destination, exc_info=True)
        return destination

    # Verify the resulting height; if it is still above target, retry with a stricter transcode.
    try:
        new_height = _probe_video_height(destination)
    except Exception:
        new_height = None
    if new_height is not None and new_height > target_height:
        logger.warning(
            "Downscaled output still above target height (target=%s, actual=%s); retrying fallback transcode",
            target_height,
            new_height,
            extra={"event": "youtube.dub.downscale.retry", "path": destination.as_posix()},
        )
        fallback_output = _make_temp_output("dub-resize-fallback-")
        fallback_command = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(destination),
            "-map",
            "0",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-vf",
            f"scale={'-2' if preserve_aspect_ratio else _resolve_target_width(target_height)}:{target_height}",
            "-c:a",
            "aac",
            "-c:s",
            "copy",
            "-movflags",
            "+faststart+frag_keyframe+empty_moov+default_base_moof",
            str(fallback_output),
        ]
        fallback_result = subprocess.run(
            fallback_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if fallback_result.returncode == 0:
            try:
                shutil.move(str(fallback_output), destination)
            except Exception:
                logger.debug("Unable to replace %s with fallback downscaled copy", destination, exc_info=True)
            else:
                return destination
        fallback_output.unlink(missing_ok=True)
        logger.warning(
            "Fallback downscale failed; keeping existing output",
            extra={"event": "youtube.dub.downscale.retry_failed", "path": destination.as_posix()},
        )
    if destination != path and path.exists():
        try:
            path.unlink(missing_ok=True)
        except Exception:
            logger.debug("Unable to clean up source after downscale", exc_info=True)
    return destination


def _pad_clip_to_duration(path: Path, target_seconds: float) -> Path:
    """
    Ensure ``path`` lasts at least ``target_seconds`` by padding video/audio tails.

    Returns the (possibly new) path to use.
    """

    if target_seconds <= 0:
        return path
    current = _probe_duration_seconds(path)
    delta = target_seconds - current
    # If we're already within 20ms, leave as-is.
    if abs(delta) <= 0.02:
        return path
    # If the clip is longer than expected, trim it to the target duration.
    if delta < -0.02:
        ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
        with tempfile.NamedTemporaryFile(
            suffix=path.suffix or ".mp4",
            delete=False,
            prefix="dub-trim-",
            dir=_TEMP_DIR,
        ) as handle:
            trimmed_path = Path(handle.name)
        command = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(path),
            "-t",
            f"{target_seconds:.6f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            str(trimmed_path),
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode == 0:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return trimmed_path
        else:
            trimmed_path.unlink(missing_ok=True)
            return path

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    with tempfile.NamedTemporaryFile(
        suffix=path.suffix or ".mp4",
        delete=False,
        prefix="dub-pad-",
        dir=_TEMP_DIR,
    ) as handle:
        padded_path = Path(handle.name)

    video_pad = f"tpad=stop_mode=clone:stop_duration={delta:.6f}"
    audio_pad = f"apad=pad_dur={delta:.6f}"
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(path),
        "-vf",
        video_pad,
        "-af",
        audio_pad,
        "-t",
        f"{target_seconds:.6f}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-c:a",
        "aac",
        str(padded_path),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        padded_path.unlink(missing_ok=True)
        return path
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
    return padded_path


def _resolve_output_path(
    video_path: Path,
    language: str,
    output_dir: Optional[Path],
    *,
    start_offset: float = 0.0,
    end_offset: Optional[float] = None,
) -> Path:
    safe_lang = re.sub(r"[^A-Za-z0-9_-]+", "-", language.strip() or "dub")
    target_dir = (output_dir or video_path.parent / f"dubbed-{safe_lang}").expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    clip_suffix = _format_clip_suffix(start_offset, end_offset)
    trimmed_stem = trim_stem_preserving_id(video_path.stem)
    return target_dir / f"{trimmed_stem}.{safe_lang}.dub{clip_suffix}.mp4"


def _format_time_prefix(seconds: float) -> str:
    clamped = max(0, int(seconds))
    hours = clamped // 3600
    minutes = (clamped % 3600) // 60
    secs = clamped % 60
    return f"{hours:02d}-{minutes:02d}-{secs:02d}"


def _resolve_batch_output_path(base_output: Path, start_seconds: float) -> Path:
    stem = base_output.stem
    suffix = base_output.suffix or ".mp4"
    prefix = _format_time_prefix(start_seconds)
    candidate = base_output.with_name(f"{prefix}-{stem}{suffix}")
    counter = 2
    while candidate.exists():
        candidate = base_output.with_name(f"{prefix}-{stem}-{counter}{suffix}")
        counter += 1
    return candidate


def _resolve_temp_batch_path(base_output: Path, start_seconds: float, *, suffix: str = ".mp4") -> Path:
    """Return a temp path on the RAM disk for intermediate batch media."""

    prefix = _format_time_prefix(start_seconds)
    stem = base_output.stem
    counter = 1
    while True:
        name = f"{prefix}-{stem}{'' if counter == 1 else f'-{counter}'}{suffix}"
        candidate = _TEMP_DIR / name
        if not candidate.exists():
            return candidate
        counter += 1


def _resolve_temp_output_path(base_output: Path) -> Path:
    """Return a temp path on the RAM disk mirroring the final output name."""

    stem = base_output.stem
    suffix = base_output.suffix or ".mp4"
    counter = 1
    while True:
        name = f"{stem}{'' if counter == 1 else f'-{counter}'}{suffix}"
        candidate = _TEMP_DIR / name
        if not candidate.exists():
            return candidate
        counter += 1


def _resolve_temp_target(target: Path) -> Path:
    """Return a temp RAM-disk path mirroring the target name."""

    stem = target.stem or "dub"
    suffix = target.suffix or ""
    counter = 1
    while True:
        name = f"{stem}{'' if counter == 1 else f'-{counter}'}{suffix}"
        candidate = _TEMP_DIR / name
        if not candidate.exists():
            return candidate
        counter += 1

def _trim_video_segment(
    video_path: Path,
    *,
    start_offset: float,
    end_offset: Optional[float],
) -> Path:
    """Return a trimmed copy of ``video_path`` based on the provided window."""

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    duration = end_offset - start_offset if end_offset is not None else None
    with tempfile.NamedTemporaryFile(
        suffix=video_path.suffix or ".mp4",
        delete=False,
        prefix="dub-clip-",
        dir=_TEMP_DIR,
    ) as handle:
        trimmed_path = Path(handle.name)

    # Fast path: copy streams, bias seek before input for better keyframe alignment.
    command = [ffmpeg_bin, "-y"]
    if start_offset > 0:
        command.extend(["-ss", f"{start_offset}"])
    command.extend(["-i", str(video_path)])
    if duration is not None:
        command.extend(["-t", f"{duration}"])
    command.extend(
        [
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c",
            "copy",
            "-reset_timestamps",
            "1",
            str(trimmed_path),
        ]
    )

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0:
        return trimmed_path

    # Fallback: re-encode if copy failed (e.g., no keyframe).
    command = [ffmpeg_bin, "-y"]
    if start_offset > 0:
        command.extend(["-ss", f"{start_offset}"])
    command.extend(["-i", str(video_path)])
    if duration is not None:
        command.extend(["-t", f"{duration}"])
    command.extend(
        [
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            str(trimmed_path),
        ]
    )
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        trimmed_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"ffmpeg failed to trim video (exit {result.returncode}): {result.stderr.decode(errors='ignore')}"
        )
    return trimmed_path


def _concat_video_segments(segments: Sequence[Path], output_path: Path) -> None:
    """Concatenate ``segments`` into ``output_path`` using ffmpeg concat demuxer."""

    if not segments:
        raise ValueError("No segments provided for concatenation")
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    inputs: List[str] = []
    filter_inputs: List[str] = []
    input_index = 0

    def _probe_media(path: Path) -> Tuple[bool, float]:
        """Return (has_audio, duration_seconds) for the given media path."""

        has_audio = _has_audio_stream(path)
        duration = 0.0
        ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
        try:
            result = subprocess.run(
                [
                    ffprobe_bin,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            duration = float(result.stdout.decode().strip() or 0.0)
        except Exception:
            duration = 0.0
        return has_audio, max(0.0, duration)

    valid_segments = 0
    for segment in segments:
        has_audio, duration = _probe_media(segment)
        has_video = _has_video_stream(segment)
        if not has_video or duration <= 0.1:
            logger.warning(
                "Skipping invalid concat segment (video=%s, duration=%.3fs)",
                has_video,
                duration,
                extra={"event": "youtube.dub.concat.invalid_segment", "segment": segment.as_posix(), "duration": duration},
            )
            continue
        valid_segments += 1
        if not has_audio:
            logger.warning(
                "Segment lacks audio stream; injecting silence to preserve concat timing",
                extra={"event": "youtube.dub.concat.silence", "segment": segment.as_posix(), "duration": duration},
            )
        inputs.extend(["-i", str(segment)])
        video_label = f"[{input_index}:v:0]"
        audio_label = f"[{input_index}:a:0]"
        input_index += 1
        if not has_audio:
            # Synthesize a silent track so concat never drops audio for this segment.
            silent_duration = max(duration, 0.1)
            inputs.extend(
                [
                    "-f",
                    "lavfi",
                    "-t",
                    f"{silent_duration:.3f}",
                    "-i",
                    "anullsrc=channel_layout=stereo:sample_rate=44100",
                ]
            )
            audio_label = f"[{input_index}:a:0]"
            input_index += 1
        filter_inputs.append(f"{video_label}{audio_label}")
    if valid_segments == 0:
        raise RuntimeError("No valid segments available for concatenation")
    filter_concat = "".join(filter_inputs) + f"concat=n={valid_segments}:v=1:a=1[v][a]"
    command = [
        ffmpeg_bin,
        "-y",
        *inputs,
        "-filter_complex",
        filter_concat,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart+frag_keyframe+empty_moov+default_base_moof",
        str(output_path),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg concat failed (exit {result.returncode}): {result.stderr.decode(errors='ignore')}"
        )


def _mux_audio_track(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    language: str,
    *,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    target_duration_seconds: Optional[float] = None,
    include_source_audio: bool = True,
) -> None:
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    command = [ffmpeg_bin, "-y"]
    if start_time is not None and start_time > 0:
        # Seek the video input while leaving the dubbed audio at t=0 for batch alignment.
        command.extend(["-ss", f"{start_time}"])
    command.extend(["-i", str(video_path)])
    command.extend(["-i", str(audio_path)])
    segment_duration = None
    if end_time is not None and end_time > 0:
        segment_duration = end_time
        if start_time is not None and start_time > 0:
            segment_duration = max(0.0, end_time - start_time)
    stretch_ratio = None
    if target_duration_seconds is not None and target_duration_seconds > 0 and segment_duration:
        if target_duration_seconds > segment_duration + 0.01:
            stretch_ratio = target_duration_seconds / max(segment_duration, 0.001)
    filter_complex: List[str] = []
    if stretch_ratio is not None:
        filter_complex.append(f"[0:v]setpts={stretch_ratio:.6f}*PTS[v0]")
        if include_source_audio:
            atempo_ratio = 1.0 / stretch_ratio
            atempo_chain = ",".join(f"atempo={factor:.5f}" for factor in _build_atempo_filters(atempo_ratio))
            filter_complex.append(f"[0:a]{atempo_chain}[a0]")
    if filter_complex:
        command.extend(["-filter_complex", ";".join(filter_complex)])
    if filter_complex:
        command.extend(["-map", "[v0]"])
    else:
        command.extend(["-map", "0:v:0"])
    command.extend(
        [
            "-map",
            "1:a",
        ]
    )
    if include_source_audio and filter_complex:
        command.extend(["-map", "[a0]"])
    elif include_source_audio:
        command.extend(["-map", "0:a?"])
    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart+frag_keyframe+empty_moov+default_base_moof",
            "-disposition:a:0",
            "default",
            "-metadata:s:a:0",
            f"language={language}",
            "-disposition:a:1",
            "0",
        ]
    )
    duration_arg = None
    if target_duration_seconds is not None and target_duration_seconds > 0:
        duration_arg = max(target_duration_seconds, segment_duration or 0.0)
    elif segment_duration is not None:
        duration_arg = segment_duration
    if duration_arg is not None and duration_arg > 0:
        command.extend(["-t", f"{duration_arg}"])
    command.append(str(output_path))

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed with exit code {result.returncode}: {result.stderr.decode(errors='ignore')}"
        )

    # Ensure the output carries an audio stream; if not, re-mux with dubbed audio only.
    if not _has_audio_stream(output_path):
        logger.warning(
            "Muxed clip missing audio; retrying without source mix",
            extra={"event": "youtube.dub.mux.audio_missing", "clip": output_path.as_posix()},
        )
        recover_command = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            str(output_path),
        ]
        subprocess.run(recover_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

        # If audio is still missing, inject silence to preserve downstream timing.
        if not _has_audio_stream(output_path):
            ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
            inject_command = [
                ffmpeg_bin,
                "-y",
                "-i",
                str(output_path),
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                str(output_path),
            ]
            subprocess.run(inject_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def list_downloaded_videos(base_dir: Path = DEFAULT_YOUTUBE_VIDEO_ROOT) -> List[YoutubeNasVideo]:
    """Return discovered videos under ``base_dir`` with adjacent subtitles."""

    resolved = base_dir.expanduser()
    if not resolved.exists() or not resolved.is_dir():
        raise FileNotFoundError(f"Video directory '{resolved}' is not accessible")

    videos: List[YoutubeNasVideo] = []
    for root, _dirs, files in os.walk(resolved):
        folder = Path(root)
        for filename in files:
            path = folder / filename
            ext = path.suffix.lower().lstrip(".")
            if ".dub" in path.stem.lower():
                continue
            if ext not in _VIDEO_EXTENSIONS:
                continue
            subtitles: List[YoutubeNasSubtitle] = []
            base_stem = path.stem
            for candidate in folder.iterdir():
                if candidate.is_dir():
                    continue
                sub_ext = candidate.suffix.lower().lstrip(".")
                if sub_ext not in _SUBTITLE_EXTENSIONS:
                    continue
                if not _subtitle_matches_video(path, candidate):
                    continue
                language = _find_language_token(candidate)
                subtitles.append(
                    YoutubeNasSubtitle(
                        path=candidate.resolve(),
                        language=language,
                        format=sub_ext,
                    )
                )
            stat = path.stat()
            videos.append(
                YoutubeNasVideo(
                    path=path.resolve(),
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    subtitles=sorted(subtitles, key=lambda s: s.path.name),
                    source=_classify_video_source(path),
                )
            )

    videos.sort(key=lambda entry: entry.modified_at, reverse=True)
    return videos


def _probe_subtitle_streams(video_path: Path) -> List[dict]:
    """Return parsed subtitle streams from ffprobe output."""

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    result = subprocess.run(
        [
            ffprobe_bin,
            "-v",
            "error",
            "-select_streams",
            "s",
            "-show_entries",
            "stream=index,codec_type,codec_name:stream_tags=language,title",
            "-of",
            "json",
            str(video_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="ignore") if result.stderr else ""
        raise RuntimeError(f"ffprobe failed with exit code {result.returncode}: {stderr.strip()}")
    try:
        payload = json.loads(result.stdout.decode() or "{}")
    except Exception as exc:
        raise RuntimeError("Unable to parse ffprobe output") from exc
    streams = payload.get("streams") or []
    subtitle_streams = [stream for stream in streams if stream.get("codec_type") == "subtitle"]
    for position, stream in enumerate(subtitle_streams):
        stream["__position__"] = position
    return subtitle_streams


def _build_subtitle_output_path(video_path: Path, language: Optional[str], stream_index: int) -> Path:
    """Return a unique SRT path next to the video for the given stream."""

    folder = video_path.parent
    stem = video_path.stem
    label_parts = [stem]
    if language:
        label_parts.append(language)
    label_parts.append(f"sub{stream_index}")
    base_name = ".".join(label_parts) + ".srt"
    candidate = folder / base_name
    suffix = 1
    while candidate.exists():
        candidate = folder / f"{stem}.{language or 'sub'}{stream_index}.{suffix}.srt"
        suffix += 1
    return candidate


def _looks_all_caps(text: str) -> bool:
    """Return True when the text contains letters and all are uppercase."""

    if not text:
        return False
    sanitized = _ASS_TAG_PATTERN.sub(" ", text)
    sanitized = _HTML_TAG_PATTERN.sub(" ", sanitized)
    letters = [ch for ch in sanitized if ch.isalpha()]
    if not letters:
        return False
    return all(ch.isupper() for ch in letters)


def _sanitize_subtitle_text(text: str) -> str:
    """Return subtitle text stripped of markup and normalized whitespace."""

    normalized = html.unescape(text or "")
    normalized = _ASS_TAG_PATTERN.sub(" ", normalized)
    normalized = _HTML_TAG_PATTERN.sub(" ", normalized)
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()


def _sanitize_cue_markup(cues: Sequence[SubtitleCue]) -> List[SubtitleCue]:
    """Strip HTML/ASS markup from cue lines."""

    sanitized: List[SubtitleCue] = []
    for cue in cues:
        sanitized_lines = [_sanitize_subtitle_text(line) for line in cue.lines]
        sanitized.append(
            SubtitleCue(
                index=cue.index,
                start=cue.start,
                end=cue.end,
                lines=sanitized_lines,
            )
        )
    return sanitized


def _sentence_case_line(line: str) -> str:
    """Lowercase the line (outside formatting tags) and capitalize the first letter."""

    chars: List[str] = []
    in_angle_tag = False
    brace_depth = 0
    first_done = False
    for ch in line:
        if ch == "<":
            in_angle_tag = True
            chars.append(ch)
            continue
        if in_angle_tag:
            chars.append(ch)
            if ch == ">":
                in_angle_tag = False
            continue
        if ch == "{":
            brace_depth += 1
            chars.append(ch)
            continue
        if brace_depth > 0:
            chars.append(ch)
            if ch == "}":
                brace_depth = max(0, brace_depth - 1)
            continue
        if ch.isalpha():
            if not first_done:
                chars.append(ch.upper())
                first_done = True
            else:
                chars.append(ch.lower())
        else:
            chars.append(ch)
    return "".join(chars)


def _normalize_all_caps_cues(cues: Sequence[SubtitleCue]) -> List[SubtitleCue]:
    """Normalize cues that are fully uppercase into sentence case."""

    normalized: List[SubtitleCue] = []
    for cue in cues:
        if not _looks_all_caps(cue.as_text()):
            normalized.append(cue)
            continue
        normalized_lines = [_sentence_case_line(_sanitize_subtitle_text(line)) for line in cue.lines]
        normalized.append(
            SubtitleCue(
                index=cue.index,
                start=cue.start,
                end=cue.end,
                lines=normalized_lines,
            )
        )
    return normalized


def _mirror_subtitle_to_source_dir(subtitle_path: Path) -> Optional[Path]:
    """Copy ``subtitle_path`` into the NAS subtitle source directory."""

    try:
        target_dir = _SUBTITLE_MIRROR_DIR
        if not target_dir:
            return None
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / subtitle_path.name
        if destination.resolve() == subtitle_path.resolve():
            return destination
        shutil.copy2(subtitle_path, destination)
        return destination
    except Exception:
        logger.warning(
            "Unable to mirror extracted subtitle %s to %s",
            subtitle_path,
            _SUBTITLE_MIRROR_DIR,
            exc_info=True,
        )
        return None


def extract_inline_subtitles(video_path: Path) -> List[YoutubeNasSubtitle]:
    """
    Extract embedded subtitle tracks from ``video_path`` into SRT files.

    Returns the list of extracted subtitles, written alongside the video.
    """

    resolved = video_path.expanduser()
    if not resolved.exists():
        raise FileNotFoundError(f"Video file '{resolved}' does not exist")
    streams = _probe_subtitle_streams(resolved)
    if not streams:
        raise ValueError("No subtitle streams found in the video")
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    extracted: List[YoutubeNasSubtitle] = []
    failed_reasons: List[str] = []
    for stream in streams:
        stream_index = stream.get("index")
        position = int(stream.get("__position__", 0))
        if stream_index is None or position is None:
            continue
        tags = stream.get("tags") or {}
        language = _normalize_language_hint(tags.get("language") or tags.get("LANGUAGE"))
        output_path = _build_subtitle_output_path(resolved, language, stream_index)
        with tempfile.NamedTemporaryFile(
            suffix=".srt",
            delete=False,
            prefix=f"dub-sub-{stream_index}-",
            dir=_TEMP_DIR,
        ) as handle:
            temp_output = Path(handle.name)
        command = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(resolved),
            "-map",
            f"0:s:{position}",
            "-c:s",
            "srt",
            str(temp_output),
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode != 0:
            temp_output.unlink(missing_ok=True)
            stderr = result.stderr.decode(errors="ignore") if result.stderr else ""
            failed_reasons.append(f"stream {stream_index}: {stderr.strip() or 'ffmpeg failed'}")
            logger.warning(
                "Failed to extract subtitle stream %s from %s",
                stream_index,
                resolved.as_posix(),
                extra={
                    "event": "youtube.dub.subtitles.extract.failed",
                    "stream_index": stream_index,
                    "exit_code": result.returncode,
                },
            )
            continue
        try:
            shutil.move(str(temp_output), output_path)
        except Exception:
            logger.debug("Unable to move extracted subtitle to %s", output_path, exc_info=True)
            temp_output.unlink(missing_ok=True)
            continue
        extracted.append(
            YoutubeNasSubtitle(
                path=output_path.resolve(),
                language=language,
                format="srt",
            )
        )
        try:
            cues = load_subtitle_cues(output_path)
            sanitized_cues = _sanitize_cue_markup(cues)
            normalized_cues = _normalize_all_caps_cues(sanitized_cues)
            if normalized_cues != cues:
                write_srt(output_path, normalized_cues)
        except Exception:
            logger.warning(
                "Unable to normalize capitalized subtitles for %s",
                output_path,
                exc_info=True,
            )
        _mirror_subtitle_to_source_dir(output_path)
    if not extracted:
        reason = ""
        if streams:
            reason = f" ({'; '.join(failed_reasons)})" if failed_reasons else " (streams may be image-based or unsupported)"
        raise ValueError(f"No subtitle streams could be extracted from the video{reason}")
    return extracted


def generate_dubbed_video(
    video_path: Path,
    subtitle_path: Path,
    *,
    target_language: Optional[str] = None,
    voice: str = "gTTS",
    tempo: float = 1.0,
    macos_reading_speed: int = 100,
    llm_model: Optional[str] = None,
    output_dir: Optional[Path] = None,
    tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
    max_workers: Optional[int] = None,
    start_time_offset: Optional[float] = None,
    end_time_offset: Optional[float] = None,
    original_mix_percent: Optional[float] = None,
    flush_sentences: Optional[int] = None,
    split_batches: bool = False,
    include_transliteration: Optional[bool] = None,
    on_batch_written: Optional[Callable[[Path], None]] = None,
    target_height: int = _TARGET_DUB_HEIGHT,
    preserve_aspect_ratio: bool = True,
) -> Tuple[Path, List[Path]]:
    """Render an audio dub from ``subtitle_path`` and mux it into ``video_path``."""

    if not video_path.exists():
        raise FileNotFoundError(f"Video file '{video_path}' does not exist")
    if not subtitle_path.exists():
        raise FileNotFoundError(f"Subtitle file '{subtitle_path}' does not exist")
    if subtitle_path.suffix.lower() not in {".ass", ".srt", ".vtt", ".sub"}:
        raise ValueError("Subtitle must be an ASS, SRT, SUB, or VTT file for timing extraction")

    start_offset, end_offset = _validate_time_window(start_time_offset, end_time_offset)
    mix_percent = _clamp_original_mix(original_mix_percent)
    flush_block = flush_sentences if flush_sentences and flush_sentences > 0 else _DEFAULT_FLUSH_SENTENCES
    target_height_resolved = int(target_height) if target_height is not None else _TARGET_DUB_HEIGHT
    if target_height_resolved < 0:
        target_height_resolved = 0
    preserve_aspect_ratio = bool(preserve_aspect_ratio)
    clipped_dialogues = _clip_dialogues_to_window(
        _parse_dialogues(subtitle_path),
        start_offset=start_offset,
        end_offset=end_offset,
    )
    if not clipped_dialogues:
        raise ValueError("No dialogue entries found in subtitle within the selected window.")
    write_batches = bool(split_batches)

    language_code = _resolve_language_code(target_language or _find_language_token(subtitle_path) or "en")
    logger.info(
        "Generating dubbed track for %s using %s (tempo=%s, speed=%s, mix=%s%%, flush_sentences=%s, llm_model=%s)",
        video_path.name,
        language_code,
        tempo,
        macos_reading_speed,
        mix_percent,
        flush_block,
        llm_model or "",
        extra={
            "event": "youtube.dub.start",
            "attributes": {
                "video": video_path.as_posix(),
                "subtitle": subtitle_path.as_posix(),
                "language": language_code,
                "voice": voice,
                "tempo": tempo,
                "speed": macos_reading_speed,
                "start_offset": start_offset,
                "end_offset": end_offset,
                "original_mix_percent": mix_percent,
                "flush_sentences": flush_block,
                "llm_model": llm_model,
                "target_height": target_height_resolved,
                "preserve_aspect_ratio": preserve_aspect_ratio,
            },
        },
    )
    trimmed_video_path: Optional[Path] = None
    source_video: Path = video_path
    written_paths: List[Path] = []
    written_set = set()
    written_batches: List[Tuple[float, Path]] = []
    encoding_futures: List[Tuple[float, Future[Path]]] = []
    encoding_executor: Optional[ThreadPoolExecutor] = None
    encoding_workers = 1
    encoding_lock = threading.Lock()
    output_path = _resolve_output_path(
        video_path,
        language_code,
        output_dir,
        start_offset=start_offset,
        end_offset=end_offset,
    )
    global_ass_handle: Optional[TextIO] = None
    try:
        if start_offset > 0 or end_offset is not None:
            trimmed_video_path = _trim_video_segment(
                video_path,
                start_offset=start_offset,
                end_offset=end_offset,
            )
            source_video = trimmed_video_path
        flushed_until = 0.0
        dubbed_track = AudioSegment.silent(duration=10, frame_rate=44100).set_channels(2)
        source_language = _find_language_token(subtitle_path) or language_code

        try:
            base_original_audio = _coerce_channels(AudioSegment.from_file(source_video).set_frame_rate(44100), 2)
        except Exception:
            base_original_audio = None
            logger.warning("Unable to preload original audio; will retry per flush", exc_info=True)

        requested_transliteration = (
            _language_uses_non_latin(language_code)
            if include_transliteration is None
            else bool(include_transliteration)
        )
        include_transliteration_resolved = bool(
            requested_transliteration and _language_uses_non_latin(language_code)
        )
        if requested_transliteration and not include_transliteration_resolved:
            logger.info(
                "Transliteration disabled for Latin-script language %s",
                language_code,
                extra={"event": "youtube.dub.transliteration.disabled", "language": language_code},
            )
        # Maintain the original name for any nested closures expecting it.
        include_transliteration = include_transliteration_resolved
        transliterator: Optional[TransliterationService] = None
        if include_transliteration_resolved:
            try:
                transliterator = get_transliterator()
            except Exception:
                transliterator = None
                include_transliteration_resolved = False
        palette = SubtitleColorPalette.default()
        uses_non_latin = _language_uses_non_latin(language_code)
        emphasis_scale = 1.3 if uses_non_latin else 1.0
        ass_renderer = CueTextRenderer(
            "ass",
            palette,
            emphasis_scale=emphasis_scale,
        )
        global_ass_writer: Optional[_SubtitleFileWriter] = None
        global_ass_handle = None
        subtitle_index = 1
        all_subtitle_dialogues: List[_AssDialogue] = []
        if not write_batches:
            ass_path = output_path.with_suffix(".ass")
            ass_path.parent.mkdir(parents=True, exist_ok=True)
            global_ass_handle = ass_path.open("w", encoding="utf-8")
            global_ass_writer = _SubtitleFileWriter(
                global_ass_handle,
                ass_renderer,
                "ass",
                start_index=subtitle_index,
            )

        total_dialogues = len(clipped_dialogues)
        if tracker is not None:
            tracker.set_total(total_dialogues)
            tracker.publish_progress(
                {
                    "stage": "translation",
                    "total": total_dialogues,
                    "source": source_language,
                    "target": language_code,
                    "flush_sentences": flush_block,
                }
            )
        if write_batches:
            expected_batches = max(1, math.ceil(total_dialogues / flush_block))
            encoding_workers = _resolve_encoding_worker_count(expected_batches, requested=max_workers)
            if encoding_workers > 1:
                encoding_executor = ThreadPoolExecutor(
                    max_workers=encoding_workers,
                    thread_name_prefix="dub-encode",
                )

        def _translate_dialogues(dialogues: List[_AssDialogue], offset: int) -> List[_AssDialogue]:
            needs_translation = source_language and language_code and source_language.lower() != language_code.lower()
            needs_llm = needs_translation or (include_transliteration_resolved and transliterator is not None)
            if not needs_llm:
                return [
                    _AssDialogue(
                        start=entry.start,
                        end=entry.end,
                        translation=entry.translation,
                        original=entry.original,
                        transliteration=entry.transliteration,
                        rtl_normalized=entry.rtl_normalized,
                        speech_offset=entry.speech_offset,
                        speech_duration=entry.speech_duration,
                    )
                    for entry in dialogues
                ]

            def _process(idx: int, entry: _AssDialogue) -> Tuple[int, _AssDialogue, bool]:
                translated_text = entry.translation
                transliteration_text = entry.transliteration
                rtl_normalized = entry.rtl_normalized
                translated_flag = False
                if needs_translation:
                    try:
                        translated_text = _translate_subtitle_text(
                            entry.translation,
                            source_language=source_language or language_code,
                            target_language=language_code,
                            llm_model=llm_model,
                        )
                        translated_flag = True
                        if is_failure_annotation(translated_text):
                            translated_text = entry.translation
                    except Exception:
                        translated_text = entry.translation
                if include_transliteration_resolved and transliterator is not None and not transliteration_text:
                    try:
                        transliteration_text = _transliterate_text(
                            transliterator,
                            translated_text or entry.translation,
                            language_code,
                        )
                    except Exception:
                        transliteration_text = None
                return idx, _AssDialogue(
                    start=entry.start,
                    end=entry.end,
                    translation=translated_text,
                    original=entry.original,
                    transliteration=transliteration_text,
                    rtl_normalized=rtl_normalized,
                    speech_offset=entry.speech_offset,
                    speech_duration=entry.speech_duration,
                ), translated_flag

            workers = _resolve_llm_worker_count(len(dialogues))
            if workers <= 1:
                results = []
                for local_idx, entry in enumerate(dialogues):
                    idx, dialogue, translated_flag = _process(local_idx, entry)
                    results.append(dialogue)
                    if tracker is not None and translated_flag:
                        tracker.record_step_completion(
                            stage="translation",
                            index=offset + idx + 1,
                            total=total_dialogues,
                            metadata={"start": entry.start, "end": entry.end},
                        )
                return results

            resolved: List[Optional[_AssDialogue]] = [None] * len(dialogues)
            futures = []
            with ThreadPoolExecutor(max_workers=workers) as executor:
                for local_idx, entry in enumerate(dialogues):
                    futures.append(executor.submit(_process, local_idx, entry))
                for future in as_completed(futures):
                    idx, dialogue, translated_flag = future.result()
                    resolved[idx] = dialogue
                    if tracker is not None and translated_flag:
                        tracker.record_step_completion(
                            stage="translation",
                            index=offset + idx + 1,
                            total=total_dialogues,
                            metadata={"start": dialogue.start, "end": dialogue.end},
                        )
            return [entry for entry in resolved if entry is not None]

        def _synthesise_batch(
            dialogues: List[_AssDialogue],
            *,
            batch_pace: float,
            next_starts: Optional[List[Optional[float]]] = None,
        ) -> List[Tuple[_AssDialogue, AudioSegment]]:
            workers = _resolve_worker_count(len(dialogues), requested=max_workers)
            segments: List[Optional[Tuple[_AssDialogue, AudioSegment]]] = [None] * len(dialogues)

            def _guard() -> None:
                if stop_event is not None and stop_event.is_set():
                    raise _DubJobCancelled()

            def _apply_reading_speed_factor(base_speed: int, factor: float) -> int:
                """Return a macOS reading speed tuned by factor, clamped to a sane range."""

                if factor <= 0:
                    return base_speed
                tuned = int(base_speed * factor)
                return max(60, min(tuned, 260))

            def _worker(index: int, entry: _AssDialogue, batch_pace: float) -> Tuple[int, _AssDialogue, AudioSegment]:
                _guard()
                reading_speed = _apply_reading_speed_factor(macos_reading_speed, batch_pace)
                sanitized = _sanitize_for_tts(entry.translation)
                segment = generate_audio(sanitized, language_code, voice, reading_speed)
                normalized = _coerce_channels(segment.set_frame_rate(44100), 2)
                return index, entry, normalized

            if tracker is not None:
                tracker.publish_progress(
                    {"stage": "synthesis", "segments": len(dialogues), "workers": workers}
                )

            if workers <= 1:
                for idx, entry in enumerate(dialogues):
                    _guard()
                    _, resolved_entry, audio = _worker(idx, entry, batch_pace)
                    segments[idx] = (resolved_entry, audio)
            else:
                futures = []
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    for idx, entry in enumerate(dialogues):
                        futures.append(executor.submit(_worker, idx, entry, batch_pace))
                    for future in as_completed(futures):
                        _guard()
                        idx, resolved_entry, audio = future.result()
                        segments[idx] = (resolved_entry, audio)

            resolved = [segment for segment in segments if segment is not None]
            if not resolved:
                raise ValueError("No synthesized segments produced for this batch.")
            return resolved  # type: ignore[return-value]

        def _render_ass_for_block(
            dialogues: Sequence[_AssDialogue],
            writer: _SubtitleFileWriter,
            *,
            start_index: int,
            offset_seconds: float = 0.0,
        ) -> int:
            next_index = start_index
            for entry in dialogues:
                transliteration = entry.transliteration or ""
                if include_transliteration_resolved and transliterator is not None and not transliteration:
                    try:
                        transliteration = _transliterate_text(
                            transliterator,
                            entry.translation,
                            language_code,
                        )
                    except Exception:
                        transliteration = ""
                render_translation = _normalize_rtl_word_order(
                    entry.translation,
                    language_code,
                    force=True,
                )
                render_transliteration = transliteration
                speech_offset = max(0.0, entry.speech_offset or 0.0)
                speech_duration = entry.speech_duration if entry.speech_duration is not None else None
                source_cue = SubtitleCue(
                    index=next_index,
                    start=max(0.0, entry.start - offset_seconds),
                    end=max(0.0, entry.end - offset_seconds),
                    lines=[entry.original],
                )
                rendered_cues = _build_output_cues(
                    source_cue,
                    render_translation,
                    render_transliteration,
                    highlight=True,
                    show_original=True,
                    renderer=ass_renderer,
                    original_text=entry.original,
                    # Drive highlights across the dubbed subtitle span; speech windows
                    # can be noisy for some languages.
                    active_start_offset=0.0,
                    active_duration=None,
                )
                next_index = writer.write(rendered_cues)
            try:
                writer.handle.flush()
            except Exception:
                pass
            return next_index

        def _encode_batch(
            sentence_clip_paths: List[Path],
            sentence_audio_paths: List[Path],
            *,
            block_source_start: float,
            block_start_seconds: float,
            block_end_seconds: float,
            ass_block_dialogues: List[_AssDialogue],
            scheduled_entries: List[_AssDialogue],
            final_batch_path: Path,
            temp_batch_path: Path,
            temp_ass_path: Path,
            temp_vtt_path: Path,
            final_ass_path: Path,
            final_vtt_path: Path,
            batch_start_sentence: int,
            batch_end_sentence: int,
            processed_sentences_snapshot: int,
        ) -> Path:
            batch_path = final_batch_path
            try:
                _concat_video_segments(sentence_clip_paths, temp_batch_path)
                batch_path = _downscale_video(
                    temp_batch_path,
                    target_height=target_height_resolved,
                    preserve_aspect_ratio=preserve_aspect_ratio,
                    output_path=final_batch_path,
                )
                try:
                    merged_dialogues = _merge_overlapping_dialogues(scheduled_entries)
                    _write_webvtt(
                        merged_dialogues,
                        temp_vtt_path,
                        target_language=language_code,
                        include_transliteration=include_transliteration_resolved,
                        transliterator=transliterator if include_transliteration_resolved else None,
                    )
                except Exception:
                    logger.debug("Unable to write batch-aligned VTT for %s", batch_path, exc_info=True)
                try:
                    temp_ass_path.parent.mkdir(parents=True, exist_ok=True)
                    with temp_ass_path.open("w", encoding="utf-8") as handle:
                        writer = _SubtitleFileWriter(
                            handle,
                            ass_renderer,
                            "ass",
                            start_index=1,
                        )
                        _render_ass_for_block(
                            ass_block_dialogues,
                            writer,
                            start_index=1,
                            offset_seconds=block_start_seconds,
                        )
                    final_ass_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(temp_ass_path), final_ass_path)
                except Exception:
                    logger.debug("Unable to write batch ASS for %s", batch_path, exc_info=True)
                    try:
                        temp_ass_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                try:
                    final_vtt_path.parent.mkdir(parents=True, exist_ok=True)
                    if temp_vtt_path.exists():
                        shutil.move(str(temp_vtt_path), final_vtt_path)
                except Exception:
                    logger.debug("Unable to move batch VTT for %s", batch_path, exc_info=True)
                    try:
                        temp_vtt_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                try:
                    rendered_duration = _probe_duration_seconds(batch_path)
                    expected_duration = block_end_seconds - block_start_seconds
                    if abs(rendered_duration - expected_duration) > 0.15:
                        logger.warning(
                            "Batch duration drift detected (expected=%.3fs, actual=%.3fs)",
                            expected_duration,
                            rendered_duration,
                            extra={
                                "event": "youtube.dub.batch.duration_drift",
                                "batch": batch_path.as_posix(),
                                "expected": expected_duration,
                                "actual": rendered_duration,
                            },
                        )
                except Exception:
                    logger.debug("Unable to probe batch duration for %s", batch_path, exc_info=True)
                should_notify = False
                with encoding_lock:
                    if batch_path not in written_set:
                        written_set.add(batch_path)
                        written_paths.append(batch_path)
                        written_batches.append((block_source_start, batch_path))
                        should_notify = True
                if tracker is not None:
                    try:
                        tracker.publish_progress(
                            {
                                "stage": "mux",
                                "seconds_written": block_end_seconds,
                                "output_path": batch_path.as_posix(),
                                "processed_sentences": processed_sentences_snapshot,
                                "block_size": flush_block,
                                "batch_start_sentence": batch_start_sentence,
                                "batch_end_sentence": batch_end_sentence,
                            }
                        )
                    except Exception:
                        logger.debug("Unable to publish mux progress for %s", batch_path, exc_info=True)
                if should_notify and on_batch_written is not None:
                    try:
                        on_batch_written(batch_path)
                    except Exception:
                        logger.warning("Unable to process written batch %s", batch_path, exc_info=True)
                return batch_path
            finally:
                for clip in sentence_clip_paths:
                    clip.unlink(missing_ok=True)
                for audio_path in sentence_audio_paths:
                    audio_path.unlink(missing_ok=True)
                if temp_batch_path.exists() and temp_batch_path != batch_path:
                    temp_batch_path.unlink(missing_ok=True)
                if temp_ass_path.exists():
                    temp_ass_path.unlink(missing_ok=True)
                if temp_vtt_path.exists():
                    temp_vtt_path.unlink(missing_ok=True)

        def _wait_for_encoding_futures() -> None:
            if not encoding_futures:
                if written_batches:
                    ordered = sorted(written_batches, key=lambda item: item[0])
                    written_paths[:] = [path for _, path in ordered]
                return
            for _start, future in encoding_futures:
                future.result()
            encoding_futures.clear()
            if written_batches:
                ordered = sorted(written_batches, key=lambda item: item[0])
                written_paths[:] = [path for _, path in ordered]

        processed_sentences = 0
        global_pace = None
        if flush_block >= total_dialogues:
            global_pace = _compute_pace_factor(clipped_dialogues)
        for block_index in range(0, total_dialogues, flush_block):
            block = clipped_dialogues[block_index : block_index + flush_block]
            translated_block = _translate_dialogues(block, offset=block_index)
            block_pace = global_pace or _compute_pace_factor(translated_block)
            next_starts: List[Optional[float]] = []
            for idx, entry in enumerate(translated_block):
                if block_index + idx + 1 < total_dialogues:
                    next_starts.append(clipped_dialogues[block_index + idx + 1].start)
                else:
                    next_starts.append(None)
            synthesized = _synthesise_batch(translated_block, batch_pace=block_pace, next_starts=next_starts)
            reference_rms = _compute_reference_rms([audio for _entry, audio in synthesized])
            batch_start_sentence = block_index + 1
            batch_end_sentence = block_index + len(synthesized)
            block_start_seconds = 0.0 if write_batches else flushed_until
            block_source_start = min(entry.start for entry, _ in synthesized)
            block_source_end = max(entry.end for entry, _ in synthesized)
            # Build a scheduled timeline that preserves gaps between merged windows and stretches
            # each sentence to the dubbed duration.
            scheduled: List[Tuple[_AssDialogue, AudioSegment, float, float]] = []
            ass_block_dialogues: List[_AssDialogue] = []
            cursor = block_start_seconds
            last_source_end = block_source_start
            for idx, (entry, audio) in enumerate(synthesized):
                if len(audio) < 20:
                    # Guard against empty TTS output to keep timeline and mux stable.
                    audio = AudioSegment.silent(duration=200, frame_rate=44100).set_channels(2)
                speech_offset, speech_duration = _measure_active_window(audio)
                orig_start = translated_block[idx].start
                orig_end = translated_block[idx].end
                transliteration_text = translated_block[idx].transliteration
                render_translation = _normalize_rtl_word_order(
                    entry.translation,
                    language_code,
                    force=True,
                )
                next_gap_source = None
                if idx + 1 < len(translated_block):
                    next_gap_source = max(0.0, translated_block[idx + 1].start - orig_end)
                # Insert untouched gap video/audio for regions without subtitles.
                gap = max(0.0, orig_start - last_source_end)
                if gap > 0:
                    cursor += gap
                    last_source_end = orig_start
                duration_sec = len(audio) / 1000.0
                # Keep subtitles slightly longer than raw audio to avoid highlighting cutting off early,
                # but cap the pad to avoid overlaps in tight sequences (bounded by the upcoming source gap).
                base_pad = min(0.2, duration_sec * 0.15)
                if next_gap_source is not None:
                    base_pad = min(base_pad, max(0.0, next_gap_source - 0.05))
                subtitle_duration = duration_sec + base_pad
                scheduled_entry = _AssDialogue(
                    start=cursor,
                    end=cursor + subtitle_duration,
                    translation=render_translation,
                    original=entry.original,
                    transliteration=transliteration_text,
                    rtl_normalized=True,
                    speech_offset=speech_offset,
                    speech_duration=speech_duration,
                )
                scheduled.append((scheduled_entry, audio, orig_start, orig_end))
                ass_block_dialogues.append(scheduled_entry)
                cursor = scheduled_entry.end
                last_source_end = orig_end
            # Preserve trailing gap to the end of the merged window.
            if last_source_end < block_source_end:
                cursor += (block_source_end - last_source_end)
            block_end_seconds = cursor
            block_duration = max(0.0, block_end_seconds - block_start_seconds)
            scheduled_entries = [entry for entry, _audio, _start, _end in scheduled]

            all_subtitle_dialogues.extend(ass_block_dialogues if write_batches else scheduled_entries)

            # Defer batch subtitle writes until the batch media is finalized on RAM disk.
            if not write_batches and global_ass_writer is not None:
                # Keep ASS cues on the absolute dubbed timeline so highlights follow stretched audio.
                subtitle_index = _render_ass_for_block(
                    ass_block_dialogues if write_batches else scheduled_entries,
                    global_ass_writer,
                    start_index=subtitle_index,
                    offset_seconds=0.0,
                )
            sentence_clip_paths: List[Path] = []
            sentence_audio_paths: List[Path] = []
            gap_start = block_source_start
            timeline_cursor = block_start_seconds
            for idx, (entry, audio, orig_start, orig_end) in enumerate(scheduled):
                # Insert gap clip (original A/V only) for regions without dialogue, sized to the scheduled gap.
                gap_duration = max(0.0, entry.start - timeline_cursor)
                if write_batches and gap_duration > 0.001:
                    try:
                        gap_clip = _trim_video_segment(
                            source_video,
                            start_offset=gap_start,
                            end_offset=orig_start,
                        )
                        gap_clip = _pad_clip_to_duration(gap_clip, gap_duration)
                        gap_clip = _apply_gap_audio_mix(
                            gap_clip,
                            mix_percent=mix_percent,
                            reference_rms=reference_rms,
                        )
                        sentence_clip_paths.append(gap_clip)
                        timeline_cursor += gap_duration
                    except Exception:
                        logger.warning(
                            "Failed to extract gap clip (start=%.3f end=%.3f); continuing without gap",
                            gap_start,
                            orig_start,
                            extra={"event": "youtube.dub.gap.clip.failed"},
                            exc_info=True,
                        )
                audio_len_seconds = len(audio) / 1000.0
                audio_end_seconds = entry.start + audio_len_seconds
                if not write_batches:
                    end_ms = int(audio_end_seconds * 1000) + 50
                    if len(dubbed_track) < end_ms:
                        dubbed_track += AudioSegment.silent(duration=end_ms - len(dubbed_track), frame_rate=44100)
                    dubbed_track = dubbed_track.overlay(audio, position=int(entry.start * 1000))
                else:
                    # Per-sentence video slice cut and stretch to the dubbed duration.
                    original_slice = None
                    if base_original_audio is not None:
                        original_slice = base_original_audio[
                            int(orig_start * 1000) : int(math.ceil(orig_end * 1000))
                        ]
                    mixed_sentence = _mix_with_original_audio(
                        audio,
                        source_video,
                        original_mix_percent=mix_percent,
                        expected_duration_seconds=audio_len_seconds,
                        original_audio=original_slice,
                    )
                    with tempfile.NamedTemporaryFile(
                        suffix=".wav",
                        delete=False,
                        prefix=f"dubbed-sentence-{batch_start_sentence + idx}-",
                        dir=_TEMP_DIR,
                    ) as sentence_audio_handle:
                        sentence_audio_path = Path(sentence_audio_handle.name)
                    mixed_sentence.export(
                        sentence_audio_path,
                        format="wav",
                        parameters=["-acodec", "pcm_s16le"],
                    )
                    sentence_audio_paths.append(sentence_audio_path)
                    local_start = orig_start
                    # Drive video length from dubbed audio; stretch/pad as needed.
                    local_end = audio_len_seconds
                    sentence_video = source_video
                    trimmed = False
                    try:
                        sentence_video = _trim_video_segment(
                            source_video,
                            start_offset=orig_start,
                            end_offset=orig_end,
                        )
                        trimmed = True
                        # Trimmed clip is reset to start at 0 via -reset_timestamps.
                        local_start = 0.0
                    except Exception:
                        sentence_video = source_video
                    sentence_output = _resolve_temp_batch_path(
                        output_path,
                        orig_start,
                        suffix=".tmp.mp4",
                    )
                    _mux_audio_track(
                        sentence_video,
                        sentence_audio_paths[-1],
                        sentence_output,
                        language_code,
                        start_time=local_start,
                        end_time=local_start + local_end if local_end > 0 else None,
                        target_duration_seconds=audio_len_seconds,
                        include_source_audio=False,
                    )
                    if not _has_audio_stream(sentence_output):
                        logger.warning(
                            "Sentence clip missing audio; re-muxing to force dubbed track",
                            extra={
                                "event": "youtube.dub.sentence.audio_missing",
                                "clip": sentence_output.as_posix(),
                                "audio": sentence_audio_paths[-1].as_posix(),
                            },
                        )
                        ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
                        recover_cmd = [
                            ffmpeg_bin,
                            "-y",
                            "-i",
                            str(sentence_video),
                            "-i",
                            str(sentence_audio_paths[-1]),
                            "-map",
                            "0:v:0",
                            "-map",
                            "1:a:0",
                            "-c:v",
                            "copy",
                            "-c:a",
                            "aac",
                            str(sentence_output),
                        ]
                        subprocess.run(recover_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                        if not _has_audio_stream(sentence_output):
                            # Last resort: attach dubbed audio with a silent video of the right duration.
                            subprocess.run(
                                [
                                    ffmpeg_bin,
                                    "-y",
                                    "-f",
                                    "lavfi",
                                    "-i",
                                    f"color=c=black:s=16x16:d={audio_len_seconds:.6f}",
                                    "-i",
                                    str(sentence_audio_paths[-1]),
                                    "-map",
                                    "0:v:0",
                                    "-map",
                                    "1:a:0",
                                    "-c:v",
                                    "libx264",
                                    "-preset",
                                    "ultrafast",
                                    "-c:a",
                                    "aac",
                                    str(sentence_output),
                                ],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                check=False,
                            )
                    sentence_output = _pad_clip_to_duration(sentence_output, audio_len_seconds)
                    final_duration = _probe_duration_seconds(sentence_output)
                    if abs(final_duration - audio_len_seconds) > 0.05:
                        logger.warning(
                            "Sentence clip duration drift (expected=%.3fs, actual=%.3fs); padding to fix",
                            audio_len_seconds,
                            final_duration,
                            extra={
                                "event": "youtube.dub.sentence.duration_drift",
                                "clip": sentence_output.as_posix(),
                                "expected": audio_len_seconds,
                                "actual": final_duration,
                            },
                        )
                        sentence_output = _pad_clip_to_duration(sentence_output, audio_len_seconds)
                    sentence_clip_paths.append(sentence_output)
                    if trimmed and sentence_video != source_video:
                        sentence_video.unlink(missing_ok=True)
                    timeline_cursor = entry.start + audio_len_seconds
                gap_start = orig_end
            # Add trailing gap within the batch window so video length matches scheduled timeline.
            trailing_gap = max(0.0, block_end_seconds - timeline_cursor)
            if write_batches and trailing_gap > 0.001 and block_source_end > gap_start:
                try:
                    gap_clip = _trim_video_segment(
                        source_video,
                        start_offset=gap_start,
                        end_offset=block_source_end,
                    )
                    gap_clip = _pad_clip_to_duration(gap_clip, trailing_gap)
                    gap_clip = _apply_gap_audio_mix(
                        gap_clip,
                        mix_percent=mix_percent,
                        reference_rms=reference_rms,
                    )
                    sentence_clip_paths.append(gap_clip)
                except Exception:
                    logger.warning(
                        "Failed to extract trailing gap clip (start=%.3f end=%.3f)",
                        gap_start,
                        block_source_end,
                        extra={"event": "youtube.dub.gap.trailing.failed"},
                        exc_info=True,
                    )
            processed_sentences += len(synthesized)
            if write_batches and sentence_clip_paths:
                final_batch_path = _resolve_batch_output_path(output_path, block_source_start)
                final_batch_path.parent.mkdir(parents=True, exist_ok=True)
                temp_batch_path = _resolve_temp_batch_path(output_path, block_source_start)
                temp_batch_path.parent.mkdir(parents=True, exist_ok=True)
                final_ass_path = final_batch_path.with_suffix(".ass")
                final_vtt_path = final_ass_path.with_suffix(".vtt")
                temp_ass_path = _resolve_temp_target(final_ass_path)
                temp_vtt_path = _resolve_temp_target(final_vtt_path)
                processed_snapshot = processed_sentences
                if encoding_executor is not None:
                    encoding_futures.append(
                        (
                            block_source_start,
                            encoding_executor.submit(
                                _encode_batch,
                                sentence_clip_paths,
                                sentence_audio_paths,
                                block_source_start=block_source_start,
                                block_start_seconds=block_start_seconds,
                                block_end_seconds=block_end_seconds,
                                ass_block_dialogues=list(ass_block_dialogues),
                                scheduled_entries=list(scheduled_entries),
                                final_batch_path=final_batch_path,
                                temp_batch_path=temp_batch_path,
                                temp_ass_path=temp_ass_path,
                                temp_vtt_path=temp_vtt_path,
                                final_ass_path=final_ass_path,
                                final_vtt_path=final_vtt_path,
                                batch_start_sentence=batch_start_sentence,
                                batch_end_sentence=batch_end_sentence,
                                processed_sentences_snapshot=processed_snapshot,
                            ),
                        )
                    )
                else:
                    _encode_batch(
                        sentence_clip_paths,
                        sentence_audio_paths,
                        block_source_start=block_source_start,
                        block_start_seconds=block_start_seconds,
                        block_end_seconds=block_end_seconds,
                        ass_block_dialogues=list(ass_block_dialogues),
                        scheduled_entries=list(scheduled_entries),
                        final_batch_path=final_batch_path,
                        temp_batch_path=temp_batch_path,
                        temp_ass_path=temp_ass_path,
                        temp_vtt_path=temp_vtt_path,
                        final_ass_path=final_ass_path,
                        final_vtt_path=final_vtt_path,
                        batch_start_sentence=batch_start_sentence,
                        batch_end_sentence=batch_end_sentence,
                        processed_sentences_snapshot=processed_snapshot,
                    )
                flushed_until = block_end_seconds
            if write_batches:
                continue
            else:
                # For single-output mode, accumulate onto the main dubbed_track and mux once after loop.
                flushed_until = block_end_seconds

        if not write_batches and all_subtitle_dialogues:
            try:
                merged_dialogues = _merge_overlapping_dialogues(all_subtitle_dialogues)
                vtt_path = output_path.with_suffix(".vtt")
                _write_webvtt(
                    merged_dialogues,
                    vtt_path,
                    target_language=language_code,
                    include_transliteration=include_transliteration_resolved,
                    transliterator=transliterator if include_transliteration_resolved else None,
                )
            except Exception:
                logger.debug("Unable to create WebVTT subtitles for %s", output_path, exc_info=True)

        if write_batches:
            _wait_for_encoding_futures()

        total_seconds = flushed_until
        final_output = written_paths[0] if write_batches and written_paths else output_path

        if not write_batches:
            # Mux the full accumulated track once to avoid batch sync gaps.
            final_audio_slice = dubbed_track[: int(math.ceil(total_seconds * 1000))] if total_seconds > 0 else dubbed_track
            # Reapply the original underlay for the full track to honour mix_percent in single-output mode.
            original_audio_slice = None
            if base_original_audio is not None:
                original_audio_slice = base_original_audio[: len(final_audio_slice)]
            final_audio_slice = _mix_with_original_audio(
                final_audio_slice,
                source_video,
                original_mix_percent=mix_percent,
                expected_duration_seconds=total_seconds if total_seconds > 0 else None,
                original_audio=original_audio_slice,
            )
            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
                prefix="dubbed-track-final-",
                dir=_TEMP_DIR,
            ) as chunk_handle:
                chunk_path = Path(chunk_handle.name)
            final_output_path = output_path
            temp_output_path = _resolve_temp_output_path(output_path)
            temp_output_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                final_audio_slice.export(
                    chunk_path,
                    format="wav",
                    parameters=["-acodec", "pcm_s16le"],
                )
                _mux_audio_track(
                    source_video,
                    chunk_path,
                    temp_output_path,
                    language_code,
                    start_time=start_offset if start_offset > 0 else None,
                    end_time=end_offset,
                )
            finally:
                chunk_path.unlink(missing_ok=True)
            output_path = _downscale_video(
                temp_output_path,
                target_height=target_height_resolved,
                preserve_aspect_ratio=preserve_aspect_ratio,
                output_path=final_output_path,
            )
            if temp_output_path.exists() and temp_output_path != output_path:
                temp_output_path.unlink(missing_ok=True)
            written_paths.append(output_path)
            if on_batch_written is not None:
                try:
                    on_batch_written(output_path)
                except Exception:
                    logger.warning("Unable to process final dubbed output %s", output_path, exc_info=True)

        logger.info(
            "Dubbed video created at %s",
            final_output,
            extra={
                "event": "youtube.dub.complete",
                "attributes": {"output": final_output.as_posix(), "written_paths": [p.as_posix() for p in written_paths]},
            },
        )
        if not write_batches and not written_paths:
            written_paths.append(output_path)
        return final_output, written_paths
    finally:
        try:
            if write_batches:
                _wait_for_encoding_futures()
        except Exception:
            logger.debug("Unable to flush encoding futures during cleanup", exc_info=True)
        if encoding_executor is not None:
            try:
                encoding_executor.shutdown(wait=True)
            except Exception:
                logger.debug("Unable to shut down encoding executor", exc_info=True)
        try:
            if global_ass_handle is not None:
                global_ass_handle.close()
        except Exception:
            logger.debug("Unable to close ASS writer handle", exc_info=True)
        if trimmed_video_path is not None:
            try:
                trimmed_video_path.unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:
                logger.debug("Unable to clean up temporary trimmed video %s", trimmed_video_path, exc_info=True)


def _write_webvtt(
    dialogues: Sequence[_AssDialogue],
    destination: Path,
    *,
    target_language: Optional[str] = None,
    include_transliteration: bool = False,
    transliterator: Optional[TransliterationService] = None,
) -> Path:
    """Serialize dialogues into a WebVTT file."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    resolved_language = target_language or _find_language_token(destination)

    def _clean_line(value: str) -> str:
        if not value:
            return ""
        unescaped = html.unescape(value)
        stripped = _HTML_TAG_PATTERN.sub("", unescaped)
        return _WHITESPACE_PATTERN.sub(" ", stripped).strip()

    def _resolve_transliteration(entry: _AssDialogue) -> str:
        if not include_transliteration:
            return entry.transliteration or ""
        if entry.transliteration:
            return entry.transliteration
        if transliterator is None or resolved_language is None:
            return ""
        try:
            return _transliterate_text(
                transliterator,
                entry.translation,
                resolved_language,
            )
        except Exception:
            return ""

    def _format_lines(entry: _AssDialogue) -> str:
        original = _clean_line(entry.original)
        transliteration = _normalize_rtl_word_order(
            _clean_line(_resolve_transliteration(entry)),
            resolved_language,
            force=False,
        )
        translation = _normalize_rtl_word_order(
            _clean_line(entry.translation),
            resolved_language,
            force=True,
        )

        # Deduplicate content: skip lines that are identical (case-insensitive, trimmed).
        seen: set[str] = set()
        payload_lines: list[str] = []

        def _add_line(label: str | None, css_class: str) -> None:
            if not label:
                return
            normalised = label.strip().lower()
            if not normalised or normalised in seen:
                return
            seen.add(normalised)
            payload_lines.append(f"<c.{css_class}>{html.escape(label)}</c>")

        _add_line(original, "original")
        _add_line(transliteration, "transliteration")
        _add_line(translation, "translation")

        if payload_lines:
            return "\n".join(payload_lines)
        return translation or original or transliteration or ""

    with destination.open("w", encoding="utf-8") as handle:
        handle.write(_WEBVTT_HEADER)
        handle.write(_WEBVTT_STYLE_BLOCK)
        for index, entry in enumerate(dialogues, 1):
            start_ts = _seconds_to_vtt_timestamp(entry.start)
            end_ts = _seconds_to_vtt_timestamp(entry.end)
            if entry.end <= entry.start:
                continue
            payload = _format_lines(entry)
            if not payload.strip():
                continue
            handle.write(f"{index}\n{start_ts} --> {end_ts}\n{payload}\n\n")
    return destination


def _ensure_webvtt_variant(
    source: Path,
    storage_root: Optional[Path],
    *,
    target_language: Optional[str] = None,
    include_transliteration: bool = False,
    transliterator: Optional[TransliterationService] = None,
) -> Optional[Path]:
    """Create (or refresh) a WebVTT sibling for ``source`` inside ``storage_root`` if possible."""

    if storage_root is None:
        return None
    try:
        if source.suffix.lower() == ".vtt":
            return source
        dialogues = _parse_dialogues(source)
        dialogues = _merge_overlapping_dialogues(dialogues)
        if not dialogues:
            return None
        target = storage_root / f"{source.stem}.vtt"
        # Always rewrite so latest RTL/transliteration rules apply.
        return _write_webvtt(
            dialogues,
            target,
            target_language=target_language or _find_language_token(source),
            include_transliteration=include_transliteration,
            transliterator=transliterator if include_transliteration else None,
        )
    except Exception:
        logger.debug("Unable to create WebVTT variant for %s", source, exc_info=True)
        return None


def _ensure_webvtt_for_video(
    subtitle_source: Path,
    video_path: Path,
    storage_root: Optional[Path],
    *,
    target_language: Optional[str] = None,
    include_transliteration: bool = False,
    transliterator: Optional[TransliterationService] = None,
) -> Optional[Path]:
    """Create (or refresh) a VTT aligned to the rendered video (including batch offsets)."""

    if storage_root is None:
        return None
    try:
        window_start = _parse_batch_start_seconds(video_path) or 0.0
        duration = _probe_duration_seconds(video_path)
        window_end = window_start + duration if duration > 0 else None
        dialogues = _parse_dialogues(subtitle_source)
        dialogues = _merge_overlapping_dialogues(dialogues)
        clipped = _clip_dialogues_to_window(dialogues, start_offset=window_start, end_offset=window_end)
        if not clipped:
            return None
        source_span = max((entry.end for entry in clipped), default=0.0)
        scale = None
        if source_span and source_span > 0 and duration and duration > 0:
            scale = max(duration / source_span, 0.0001)
        # Shift to the video timeline (batch starts at 0) and scale to the rendered duration.
        shifted = []
        for entry in clipped:
            local_start = entry.start
            local_end = entry.end
            if scale is not None:
                local_start *= scale
                local_end *= scale
            shifted.append(
                _AssDialogue(
                    start=local_start,
                    end=local_end,
                    translation=entry.translation,
                    original=entry.original,
                    transliteration=entry.transliteration,
                    rtl_normalized=entry.rtl_normalized,
                )
            )
        shifted = _merge_overlapping_dialogues(shifted)
        if not shifted:
            return None
        target = storage_root / f"{video_path.stem}.vtt"
        # Always rewrite so latest RTL/transliteration rules apply.
        return _write_webvtt(
            shifted,
            target,
            target_language=target_language or _find_language_token(subtitle_source),
            include_transliteration=include_transliteration,
            transliterator=transliterator if include_transliteration else None,
        )
    except Exception:
        logger.debug("Unable to create aligned WebVTT for %s", video_path, exc_info=True)
        return None


def _serialize_generated_files(output_path: Path, *, relative_prefix: Optional[Path] = None) -> dict:
    return _serialize_generated_files_batch([output_path], relative_prefix=relative_prefix)


def _serialize_generated_files_batch(
    paths: Sequence[Path],
    *,
    relative_prefix: Optional[Path] = None,
    subtitle_paths: Optional[Sequence[Path]] = None,
    subtitle_relative_prefix: Optional[Path] = None,
) -> dict:
    files = []
    for path in paths:
        files.append(
            {
                "type": "video",
                "path": path.as_posix(),
                "name": path.name,
                **(
                    {"relative_path": (relative_prefix / path.name).as_posix()}
                    if relative_prefix is not None
                    else {}
                ),
            }
        )
    subtitle_prefix = subtitle_relative_prefix if subtitle_relative_prefix is not None else relative_prefix
    if subtitle_paths:
        for subtitle_path in subtitle_paths:
            files.append(
                {
                    "type": "text",
                    "path": subtitle_path.as_posix(),
                    "name": subtitle_path.name,
                    **(
                        {"relative_path": (subtitle_prefix / subtitle_path.name).as_posix()}
                        if subtitle_prefix is not None
                        else {}
                    ),
                }
            )
    return {
        "complete": True,
        "chunks": [
            {
                "chunk_id": "youtube_dub",
                "range_fragment": "dub",
                "files": files,
            }
        ],
    }


def _build_job_result(
    *,
    output_path: Path,
    written_paths: List[Path],
    video_path: Path,
    subtitle_path: Path,
    source_subtitle_path: Optional[Path],
    source_kind: str,
    language: str,
    voice: str,
    tempo: float,
    macos_reading_speed: int,
    dialogues: int,
    start_offset: float,
    end_offset: Optional[float],
    original_mix_percent: float,
    flush_sentences: int,
    llm_model: Optional[str],
    target_height: int,
    preserve_aspect_ratio: bool,
) -> dict:
    return {
        "youtube_dub": {
            "output_path": output_path.as_posix(),
            "video_path": video_path.as_posix(),
            "subtitle_path": subtitle_path.as_posix(),
            "source_subtitle_path": source_subtitle_path.as_posix() if source_subtitle_path else subtitle_path.as_posix(),
            "source_kind": source_kind,
            "language": language,
            "voice": voice,
            "tempo": tempo,
            "reading_speed": macos_reading_speed,
            "dialogues": dialogues,
            "start_time_offset_seconds": start_offset,
            "end_time_offset_seconds": end_offset,
            "original_mix_percent": original_mix_percent,
            "flush_sentences": flush_sentences,
            "llm_model": llm_model,
            "written_paths": [path.as_posix() for path in written_paths],
            "split_batches": len(written_paths) > 1,
            "target_height": target_height,
            "preserve_aspect_ratio": preserve_aspect_ratio,
        }
    }


def _run_dub_job(
    job: PipelineJob,
    *,
    video_path: Path,
    subtitle_path: Path,
    language_code: str,
    voice: str,
    tempo: float,
    macos_reading_speed: int,
    output_dir: Optional[Path],
    max_workers: Optional[int] = None,
    start_time_offset: Optional[float] = None,
    end_time_offset: Optional[float] = None,
    original_mix_percent: Optional[float] = None,
    flush_sentences: Optional[int] = None,
    llm_model: Optional[str] = None,
    split_batches: bool = False,
    include_transliteration: Optional[bool] = None,
    target_height: int = _TARGET_DUB_HEIGHT,
    preserve_aspect_ratio: bool = True,
    file_locator: Optional[FileLocator] = None,
    source_subtitle_path: Optional[Path] = None,
    source_kind: str = "youtube",
    ) -> None:
    tracker = job.tracker or ProgressTracker()
    stop_event = job.stop_event or threading.Event()
    source_subtitle = source_subtitle_path or subtitle_path
    target_height_resolved = int(target_height)
    tracker.publish_progress(
        {
            "stage": "validation",
            "video": video_path.as_posix(),
            "subtitle": subtitle_path.as_posix(),
            "language": language_code,
            "start_offset": start_time_offset or 0.0,
            "end_offset": end_time_offset,
            "split_batches": split_batches,
        }
    )
    try:
        media_root: Optional[Path] = None
        relative_prefix: Optional[Path] = None
        subtitle_storage_path: Path = subtitle_path
        subtitle_artifacts: List[Path] = []
        requested_transliteration = (
            _language_uses_non_latin(language_code)
            if include_transliteration is None
            else bool(include_transliteration)
        )
        include_transliteration_resolved = bool(
            requested_transliteration and _language_uses_non_latin(language_code)
        )
        if requested_transliteration and not include_transliteration_resolved:
            logger.info(
                "Transliteration disabled for Latin-script language %s",
                language_code,
                extra={"event": "youtube.dub.transliteration.disabled", "language": language_code},
            )
        # Preserve the original name for nested closures that may still reference it.
        include_transliteration = include_transliteration_resolved
        transliterator: Optional[TransliterationService] = None
        if include_transliteration_resolved:
            try:
                transliterator = get_transliterator()
            except Exception:
                transliterator = None
                include_transliteration_resolved = False

        def _ensure_media_root() -> Optional[Path]:
            nonlocal media_root
            if file_locator is None:
                return None
            if media_root is None:
                media_root = file_locator.media_root(job.job_id)
                media_root.mkdir(parents=True, exist_ok=True)
            return media_root

        def _copy_into_storage(path: Path) -> Path:
            root = _ensure_media_root()
            if root is None:
                return path
            target = root / path.name
            try:
                if path.resolve() == target.resolve():
                    return target
            except Exception:
                pass
            try:
                shutil.copy2(path, target)
                return target
            except Exception:
                logger.warning(
                    "Unable to copy dubbed artifact %s into storage for job %s",
                    path,
                    job.job_id,
                    exc_info=True,
                )
                return path

        try:
            subtitle_storage_path = _copy_into_storage(subtitle_storage_path)
            subtitle_artifacts.append(subtitle_storage_path)
            if media_root and subtitle_storage_path.is_relative_to(media_root):
                relative_prefix = Path("media")
            vtt_variant = _ensure_webvtt_variant(
                subtitle_storage_path,
                media_root,
                target_language=language_code,
                # Skip transliteration when copying the source subtitles into storage;
                # the translated/batch subtitles later in the pipeline will carry the
                # transliteration track to avoid front-loading a long LLM pass here.
                include_transliteration=False,
                transliterator=None,
            )
            if vtt_variant:
                subtitle_artifacts.append(vtt_variant)
        except Exception:
            logger.debug("Unable to prepare subtitle copy for storage", exc_info=True)

        storage_written_paths: List[Path] = []

        def _serialize_files() -> dict:
            return _serialize_generated_files_batch(
                storage_written_paths,
                relative_prefix=relative_prefix,
                subtitle_paths=subtitle_artifacts,
                subtitle_relative_prefix=relative_prefix,
            )

        def _register_written_path(path: Path) -> None:
            nonlocal relative_prefix
            batch_subtitles: list[Path] = []

            def _relative_str(candidate: Path) -> str:
                try:
                    if media_root and candidate.is_relative_to(media_root):
                        return (Path("media") / candidate.relative_to(media_root)).as_posix()
                except Exception:
                    pass
                return candidate.as_posix()

            def _subtitles_map(paths: Sequence[Path]) -> dict[str, str]:
                mapping: dict[str, str] = {}
                for candidate in paths:
                    suffix = candidate.suffix.lower().lstrip(".") or "text"
                    if suffix in mapping:
                        continue
                    if suffix not in {"vtt", "ass", "srt", "text"}:
                        suffix = "text"
                    mapping[suffix] = _relative_str(candidate)
                return mapping

            stored = _copy_into_storage(path)
            root = media_root
            if root and stored.is_relative_to(root):
                relative_prefix = Path("media")
            if stored not in storage_written_paths:
                storage_written_paths.append(stored)
            subtitle_bases = {stored, path}
            for base in subtitle_bases:
                subtitle_candidate = base.with_suffix(".ass")
                alt_subtitle = base.with_suffix(".srt")
                vtt_subtitle = base.with_suffix(".vtt")
                candidates = (vtt_subtitle, subtitle_candidate, alt_subtitle)
                for candidate in candidates:
                    try:
                        if candidate.exists():
                            copied_subtitle = _copy_into_storage(candidate)
                            if copied_subtitle not in subtitle_artifacts:
                                subtitle_artifacts.append(copied_subtitle)
                            if copied_subtitle not in batch_subtitles:
                                batch_subtitles.append(copied_subtitle)
                            # Avoid re-rendering VTT files when they already exist; keep the
                            # authored transliteration/RTL ordering and skip LLM work here.
                            if copied_subtitle.suffix.lower() == ".vtt":
                                continue
                            vtt_variant = _ensure_webvtt_variant(
                                copied_subtitle,
                                media_root,
                                target_language=language_code,
                                include_transliteration=include_transliteration_resolved,
                                transliterator=transliterator if include_transliteration_resolved else None,
                            )
                            if vtt_variant:
                                if vtt_variant not in subtitle_artifacts:
                                    subtitle_artifacts.append(vtt_variant)
                                if vtt_variant not in batch_subtitles:
                                    batch_subtitles.append(vtt_variant)
                            aligned_variant = _ensure_webvtt_for_video(
                                copied_subtitle,
                                stored,
                                media_root,
                                target_language=language_code,
                                include_transliteration=include_transliteration_resolved,
                                transliterator=transliterator if include_transliteration_resolved else None,
                            )
                            if aligned_variant:
                                if aligned_variant not in subtitle_artifacts:
                                    subtitle_artifacts.append(aligned_variant)
                                if aligned_variant not in batch_subtitles:
                                    batch_subtitles.append(aligned_variant)
                    except Exception:
                        logger.debug("Unable to register subtitle artifact %s", candidate, exc_info=True)
            job.generated_files = _serialize_files()
            try:
                subtitle_map = _subtitles_map(batch_subtitles or subtitle_artifacts)
                chunk_files: dict[str, str] = {"video": _relative_str(stored)}
                chunk_files.update(subtitle_map)
                chunk_identifier = stored.stem or "youtube_dub"
                tracker.record_generated_chunk(
                    chunk_id=chunk_identifier,
                    start_sentence=0,
                    end_sentence=0,
                    range_fragment=stored.stem,
                    files=chunk_files,
                )
                job.generated_files = tracker.get_generated_files()
            except Exception:
                logger.debug("Unable to publish generated chunk for %s", stored, exc_info=True)
            try:
                tracker.publish_progress(
                    {"stage": "media.update", "generated_files": job.generated_files, "output_path": stored.as_posix()}
                )
            except Exception:
                logger.debug("Unable to publish generated media update for %s", stored, exc_info=True)

        # Persist subtitle reference immediately so active jobs can expose tracks even before videos finish.
        job.generated_files = _serialize_files()
        try:
            subtitle_map = {
                (
                    sub.suffix.lower().lstrip(".") if sub.suffix.lower().lstrip(".") in {"vtt", "ass", "srt"} else "text"
                ): (
                    (Path("media") / sub.relative_to(media_root)).as_posix()
                    if media_root and sub.is_relative_to(media_root)
                    else sub.as_posix()
                )
                for sub in subtitle_artifacts
            }
            chunk_identifier = f"{subtitle_storage_path.stem or 'youtube_dub'}_init"
            tracker.record_generated_chunk(
                chunk_id=chunk_identifier,
                start_sentence=0,
                end_sentence=0,
                range_fragment="dub",
                files=subtitle_map,
            )
            job.generated_files = tracker.get_generated_files()
        except Exception:
            logger.debug("Unable to publish initial generated subtitles snapshot", exc_info=True)
        try:
            tracker.publish_progress({"stage": "media.init", "generated_files": job.generated_files})
        except Exception:
            logger.debug("Unable to publish initial generated media snapshot", exc_info=True)

        final_output, written_paths = generate_dubbed_video(
            video_path,
            subtitle_path,
            target_language=language_code,
            voice=voice,
            tempo=tempo,
            macos_reading_speed=macos_reading_speed,
            output_dir=output_dir,
            tracker=tracker,
            stop_event=stop_event,
            max_workers=max_workers,
            start_time_offset=start_time_offset,
            end_time_offset=end_time_offset,
            original_mix_percent=original_mix_percent,
            flush_sentences=flush_sentences,
            llm_model=llm_model,
            split_batches=split_batches,
            include_transliteration=include_transliteration_resolved,
            on_batch_written=_register_written_path,
            target_height=target_height,
            preserve_aspect_ratio=preserve_aspect_ratio,
        )
    except _DubJobCancelled:
        job.status = PipelineJobStatus.CANCELLED
        job.error_message = None
        return
    if stop_event.is_set():
        job.status = PipelineJobStatus.CANCELLED
        job.error_message = None
        return
    job.status = PipelineJobStatus.COMPLETED
    job.error_message = None
    if not storage_written_paths:
        for path in written_paths:
            _register_written_path(path)
    try:
        job.generated_files = tracker.get_generated_files()
    except Exception:
        logger.debug("Unable to snapshot generated files after completion", exc_info=True)
    job.media_completed = True
    dialogues = _clip_dialogues_to_window(
        _parse_dialogues(subtitle_path),
        start_offset=start_time_offset or 0.0,
        end_offset=end_time_offset,
    )
    job.result_payload = _build_job_result(
        output_path=(storage_written_paths[0] if storage_written_paths else final_output),
        written_paths=written_paths,
        video_path=video_path,
        subtitle_path=subtitle_storage_path,
        source_subtitle_path=source_subtitle,
        source_kind=source_kind,
        language=language_code,
        voice=voice,
        tempo=tempo,
        macos_reading_speed=macos_reading_speed,
        dialogues=len([entry for entry in dialogues if entry.translation]),
        start_offset=start_time_offset or 0.0,
        end_offset=end_time_offset,
        original_mix_percent=_clamp_original_mix(original_mix_percent),
        flush_sentences=flush_sentences if flush_sentences is not None else _DEFAULT_FLUSH_SENTENCES,
        llm_model=llm_model,
        target_height=target_height_resolved,
        preserve_aspect_ratio=preserve_aspect_ratio,
    )
    try:
        job.generated_files = tracker.get_generated_files()
    except Exception:
        logger.debug("Unable to snapshot generated files from tracker on completion; falling back to serialized batch", exc_info=True)
        job.generated_files = _serialize_generated_files_batch(
            storage_written_paths,
            relative_prefix=relative_prefix,
            subtitle_paths=subtitle_artifacts,
            subtitle_relative_prefix=relative_prefix,
        )
    tracker.publish_progress({"stage": "complete", "output_path": final_output.as_posix()})


class YoutubeDubbingService:
    """Coordinate YouTube dubbing jobs with progress tracking."""

    def __init__(
        self,
        job_manager: "PipelineJobManager",
        *,
        max_workers: Optional[int] = None,
    ) -> None:
        self._job_manager = job_manager
        self._max_workers = max_workers

    def enqueue(
        self,
        video_path: Path,
        subtitle_path: Path,
        *,
        target_language: Optional[str],
        voice: str,
        tempo: float,
        macos_reading_speed: int,
        output_dir: Optional[Path],
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        start_time_offset: Optional[float] = None,
        end_time_offset: Optional[float] = None,
        original_mix_percent: Optional[float] = None,
        flush_sentences: Optional[int] = None,
        llm_model: Optional[str] = None,
        split_batches: Optional[bool] = None,
        include_transliteration: Optional[bool] = None,
        target_height: Optional[int] = None,
        preserve_aspect_ratio: Optional[bool] = None,
    ) -> PipelineJob:
        resolved_video = video_path.expanduser()
        resolved_subtitle = subtitle_path.expanduser()
        if not resolved_video.exists():
            raise FileNotFoundError(f"Video file '{resolved_video}' does not exist")
        if not resolved_subtitle.exists():
            raise FileNotFoundError(f"Subtitle file '{resolved_subtitle}' does not exist")
        if resolved_video.parent != resolved_subtitle.parent:
            raise ValueError("subtitle_path must be in the same directory as the video file")
        if resolved_subtitle.suffix.lower() not in {".ass", ".srt", ".vtt", ".sub"}:
            raise ValueError("subtitle_path must reference an ASS, SRT, SUB, or VTT subtitle file.")

        start_offset, end_offset = _validate_time_window(start_time_offset, end_time_offset)
        resolved_target_height = int(target_height) if target_height is not None else _TARGET_DUB_HEIGHT
        if resolved_target_height < 0:
            resolved_target_height = 0
        allowed_heights = {320, 480, 720}
        if resolved_target_height not in allowed_heights:
            raise ValueError("target_height must be one of 320, 480, or 720")
        preserve_aspect_ratio_resolved = True if preserve_aspect_ratio is None else bool(preserve_aspect_ratio)

        tracker = ProgressTracker()
        stop_event = threading.Event()
        source_kind = _classify_video_source(resolved_video)
        language_code = _resolve_language_code(
            target_language or _find_language_token(resolved_subtitle) or "en"
        )
        payload = {
            "video_path": resolved_video.as_posix(),
            "subtitle_path": resolved_subtitle.as_posix(),
            "source_subtitle_path": resolved_subtitle.as_posix(),
            "source_kind": source_kind,
            "target_language": language_code,
            "voice": voice,
            "tempo": tempo,
            "macos_reading_speed": macos_reading_speed,
            "output_dir": output_dir.as_posix() if output_dir else None,
            "start_time_offset": start_offset,
            "end_time_offset": end_offset,
            "original_mix_percent": _clamp_original_mix(original_mix_percent),
            "flush_sentences": flush_sentences if flush_sentences is not None else _DEFAULT_FLUSH_SENTENCES,
            "llm_model": llm_model,
            "split_batches": bool(split_batches) if split_batches is not None else False,
            "include_transliteration": include_transliteration,
            "target_height": resolved_target_height,
            "preserve_aspect_ratio": preserve_aspect_ratio_resolved,
        }

        def _worker(job: PipelineJob) -> None:
            _run_dub_job(
                job,
                video_path=resolved_video,
                subtitle_path=resolved_subtitle,
                language_code=language_code,
                voice=voice,
                tempo=tempo,
                macos_reading_speed=macos_reading_speed,
                output_dir=output_dir,
                max_workers=self._max_workers,
                start_time_offset=start_offset,
                end_time_offset=end_offset,
                original_mix_percent=original_mix_percent,
                flush_sentences=flush_sentences,
                llm_model=llm_model,
                split_batches=bool(split_batches) if split_batches is not None else False,
                include_transliteration=include_transliteration,
                target_height=resolved_target_height,
                preserve_aspect_ratio=preserve_aspect_ratio_resolved,
                file_locator=self._job_manager.file_locator,
                source_subtitle_path=resolved_subtitle,
                source_kind=source_kind,
            )

        return self._job_manager.submit_background_job(
            job_type="youtube_dub",
            worker=_worker,
            tracker=tracker,
            stop_event=stop_event,
            request_payload=payload,
            user_id=user_id,
            user_role=user_role,
        )


__all__ = [
    "DEFAULT_YOUTUBE_VIDEO_ROOT",
    "YoutubeNasSubtitle",
    "YoutubeNasVideo",
    "generate_dubbed_video",
    "list_downloaded_videos",
    "extract_inline_subtitles",
    "YoutubeDubbingService",
]
