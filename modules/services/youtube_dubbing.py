"""Helpers for discovering downloaded YouTube videos and generating dubbed tracks."""

from __future__ import annotations

import html
import math
import os
import re
import threading
import subprocess
import tempfile
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple, TextIO

from pydub import AudioSegment, effects

from modules import config_manager as cfg
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
    CueTextRenderer,
    _SubtitleFileWriter,
)
from modules.retry_annotations import is_failure_annotation
from modules.transliteration import get_transliterator, TransliterationService

logger = log_mgr.get_logger().getChild("services.youtube_dubbing")

DEFAULT_YOUTUBE_VIDEO_ROOT = Path("/Volumes/Data/Video/Youtube").expanduser()

_VIDEO_EXTENSIONS = {"mp4", "mkv", "mov", "webm", "m4v"}
_SUBTITLE_EXTENSIONS = {"ass", "srt", "vtt"}
_LANGUAGE_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,16}$")
_DEFAULT_ORIGINAL_MIX_PERCENT = 15.0
_DEFAULT_FLUSH_SENTENCES = 10
_TEMP_DIR = Path("/tmp")
_ASS_DIALOGUE_PATTERN = re.compile(
    r"^Dialogue:\s*[^,]*,(?P<start>[^,]+),(?P<end>[^,]+),[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,(?P<text>.*)$",
    re.IGNORECASE,
)
_ASS_TAG_PATTERN = re.compile(r"\{[^}]*\}")
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_MIN_DIALOGUE_GAP_SECONDS = 0.0
_MIN_DIALOGUE_DURATION_SECONDS = 0.1


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


@dataclass(frozen=True)
class _AssDialogue:
    """Parsed ASS dialogue entry with translation text."""

    start: float
    end: float
    translation: str
    original: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class _DubJobCancelled(Exception):
    """Raised when a YouTube dubbing job is interrupted."""


def _resolve_worker_count(total_items: int, requested: Optional[int] = None) -> int:
    settings = cfg.get_settings()
    configured = requested if requested is not None else settings.job_max_workers
    if configured is None or configured <= 0:
        configured = 1
    return max(1, min(int(configured), max(1, total_items)))


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
            )
        )
    return clipped


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
    return final.set_frame_rate(segment.frame_rate).set_channels(segment.channels)


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
        normalized = fitted.set_frame_rate(target_rate).set_channels(target_channels)
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
    if start_offset <= 0 and end_offset is None:
        return ""
    tokens = []
    if start_offset > 0:
        tokens.append(f"from{int(start_offset * 1000)}ms")
    return "." + "-".join(tokens) if tokens else ""


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
    original = original.set_frame_rate(target_rate).set_channels(target_channels)

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
    return target_dir / f"{video_path.stem}.{safe_lang}.dub{clip_suffix}.mp4"


def _resolve_batch_output_path(base_output: Path, start_sentence: int, end_sentence: int) -> Path:
    stem = base_output.stem
    suffix = base_output.suffix or ".mp4"
    return base_output.with_name(f"{stem}.s{start_sentence}-s{end_sentence}{suffix}")


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

    for segment in segments:
        has_audio, duration = _probe_media(segment)
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
    filter_concat = "".join(filter_inputs) + f"concat=n={len(segments)}:v=1:a=1[v][a]"
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
                )
            )

    videos.sort(key=lambda entry: entry.modified_at, reverse=True)
    return videos


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
) -> Tuple[Path, List[Path]]:
    """Render an audio dub from ``subtitle_path`` and mux it into ``video_path``."""

    if not video_path.exists():
        raise FileNotFoundError(f"Video file '{video_path}' does not exist")
    if not subtitle_path.exists():
        raise FileNotFoundError(f"Subtitle file '{subtitle_path}' does not exist")
    if subtitle_path.suffix.lower() not in {".ass", ".srt", ".vtt"}:
        raise ValueError("Subtitle must be an ASS, SRT, or VTT file for timing extraction")

    start_offset, end_offset = _validate_time_window(start_time_offset, end_time_offset)
    mix_percent = _clamp_original_mix(original_mix_percent)
    flush_block = flush_sentences if flush_sentences and flush_sentences > 0 else _DEFAULT_FLUSH_SENTENCES
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
            },
        },
    )
    trimmed_video_path: Optional[Path] = None
    source_video: Path = video_path
    written_paths: List[Path] = []
    written_set = set()
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
            base_original_audio = AudioSegment.from_file(source_video).set_frame_rate(44100).set_channels(2)
        except Exception:
            base_original_audio = None
            logger.warning("Unable to preload original audio; will retry per flush", exc_info=True)

        include_transliteration = _target_uses_non_latin_script(language_code)
        transliterator: Optional[TransliterationService] = None
        if include_transliteration:
            try:
                transliterator = get_transliterator()
            except Exception:
                transliterator = None
                include_transliteration = False
        palette = SubtitleColorPalette.default()
        uses_non_latin = _target_uses_non_latin_script(language_code)
        emphasis_scale = 1.3 if uses_non_latin else 1.0
        ass_renderer = CueTextRenderer(
            "ass",
            palette,
            emphasis_scale=emphasis_scale,
        )
        global_ass_writer: Optional[_SubtitleFileWriter] = None
        global_ass_handle = None
        subtitle_index = 1
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

        def _translate_dialogues(dialogues: List[_AssDialogue], offset: int) -> List[_AssDialogue]:
            translated: List[_AssDialogue] = []
            needs_translation = source_language and language_code and source_language.lower() != language_code.lower()
            for local_idx, entry in enumerate(dialogues):
                translated_text = entry.translation
                if needs_translation:
                    try:
                        translated_text = _translate_subtitle_text(
                            entry.translation,
                            source_language=source_language or language_code,
                            target_language=language_code,
                            llm_model=llm_model,
                        )
                        if is_failure_annotation(translated_text):
                            translated_text = entry.translation
                    except Exception:
                        translated_text = entry.translation
                    if tracker is not None:
                        tracker.record_step_completion(
                            stage="translation",
                            index=offset + local_idx + 1,
                            total=total_dialogues,
                            metadata={"start": entry.start, "end": entry.end},
                        )
                translated.append(
                    _AssDialogue(
                        start=entry.start,
                        end=entry.end,
                        translation=translated_text,
                        original=entry.original,
                    )
                )
            return translated

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
                normalized = segment.set_frame_rate(44100).set_channels(2)
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
                transliteration = ""
                if include_transliteration and transliterator is not None:
                    try:
                        transliteration = transliterator.transliterate(entry.translation, language_code)
                    except Exception:
                        transliteration = ""
                source_cue = SubtitleCue(
                    index=next_index,
                    start=max(0.0, entry.start - offset_seconds),
                    end=max(0.0, entry.end - offset_seconds),
                    lines=[entry.original],
                )
                rendered_cues = _build_output_cues(
                    source_cue,
                    entry.translation,
                    transliteration,
                    highlight=True,
                    show_original=True,
                    renderer=ass_renderer,
                    original_text=entry.original,
                )
                next_index = writer.write(rendered_cues)
            try:
                writer.handle.flush()
            except Exception:
                pass
            return next_index

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
                orig_start = translated_block[idx].start
                orig_end = translated_block[idx].end
                # Insert untouched gap video/audio for regions without subtitles.
                gap = max(0.0, orig_start - last_source_end)
                if gap > 0:
                    cursor += gap
                    last_source_end = orig_start
                duration_sec = len(audio) / 1000.0
                scheduled_entry = _AssDialogue(
                    start=cursor,
                    end=cursor + duration_sec,
                    translation=entry.translation,
                    original=entry.original,
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

            # Render batch ASS subtitles aligned to this batch.
            if write_batches:
                batch_ass_path = _resolve_batch_output_path(
                    output_path, batch_start_sentence, batch_end_sentence
                ).with_suffix(".ass")
                batch_ass_path.parent.mkdir(parents=True, exist_ok=True)
                with batch_ass_path.open("w", encoding="utf-8") as handle:
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
            elif global_ass_writer is not None:
                subtitle_index = _render_ass_for_block(
                    ass_block_dialogues if write_batches else scheduled_entries,
                    global_ass_writer,
                    start_index=subtitle_index,
                    offset_seconds=block_start_seconds,
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
                    sentence_output = _resolve_batch_output_path(
                        output_path,
                        batch_start_sentence + idx,
                        batch_start_sentence + idx,
                    ).with_suffix(".tmp.mp4")
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
                batch_path = _resolve_batch_output_path(output_path, batch_start_sentence, batch_end_sentence)
                batch_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    _concat_video_segments(sentence_clip_paths, batch_path)
                    # Verify batch duration equals scheduled sum (sentences + gaps); warn if not.
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
                finally:
                    for clip in sentence_clip_paths:
                        clip.unlink(missing_ok=True)
                    for audio_path in sentence_audio_paths:
                        audio_path.unlink(missing_ok=True)
                flushed_until = block_end_seconds
                if batch_path not in written_set:
                    written_paths.append(batch_path)
                    written_set.add(batch_path)
                if tracker is not None:
                    tracker.publish_progress(
                        {
                            "stage": "mux",
                            "seconds_written": block_end_seconds,
                            "output_path": batch_path.as_posix(),
                            "processed_sentences": processed_sentences,
                            "block_size": flush_block,
                            "batch_start_sentence": batch_start_sentence,
                            "batch_end_sentence": batch_end_sentence,
                        }
                    )
            if write_batches:
                continue
            else:
                # For single-output mode, accumulate onto the main dubbed_track and mux once after loop.
                flushed_until = block_end_seconds

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
            try:
                final_audio_slice.export(
                    chunk_path,
                    format="wav",
                    parameters=["-acodec", "pcm_s16le"],
                )
                _mux_audio_track(
                    source_video,
                    chunk_path,
                    output_path,
                    language_code,
                    start_time=start_offset if start_offset > 0 else None,
                    end_time=end_offset,
                )
            finally:
                chunk_path.unlink(missing_ok=True)
            written_paths.append(output_path)

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
            if global_ass_handle is not None:
                global_ass_handle.close()
        except Exception:
            logger.debug("Unable to close ASS writer handle", exc_info=True)
        if trimmed_video_path is not None:
            try:
                trimmed_video_path.unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:
                logger.debug("Unable to clean up temporary trimmed video %s", trimmed_video_path, exc_info=True)


def _serialize_generated_files(output_path: Path) -> dict:
    return _serialize_generated_files_batch([output_path])


def _serialize_generated_files_batch(paths: Sequence[Path]) -> dict:
    files = []
    for path in paths:
        files.append(
            {
                "type": "video",
                "path": path.as_posix(),
                "relative_path": path.name,
                "name": path.name,
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
) -> dict:
    return {
        "youtube_dub": {
            "output_path": output_path.as_posix(),
            "video_path": video_path.as_posix(),
            "subtitle_path": subtitle_path.as_posix(),
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
) -> None:
    tracker = job.tracker or ProgressTracker()
    stop_event = job.stop_event or threading.Event()
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
    job.media_completed = True
    dialogues = _clip_dialogues_to_window(
        _parse_dialogues(subtitle_path),
        start_offset=start_time_offset or 0.0,
        end_offset=end_time_offset,
    )
    job.result_payload = _build_job_result(
        output_path=final_output,
        written_paths=written_paths,
        video_path=video_path,
        subtitle_path=subtitle_path,
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
    )
    job.generated_files = _serialize_generated_files_batch(written_paths)
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
    ) -> PipelineJob:
        resolved_video = video_path.expanduser()
        resolved_subtitle = subtitle_path.expanduser()
        if not resolved_video.exists():
            raise FileNotFoundError(f"Video file '{resolved_video}' does not exist")
        if not resolved_subtitle.exists():
            raise FileNotFoundError(f"Subtitle file '{resolved_subtitle}' does not exist")
        if resolved_video.parent != resolved_subtitle.parent:
            raise ValueError("subtitle_path must be in the same directory as the video file")
        if resolved_subtitle.suffix.lower() not in {".ass", ".srt", ".vtt"}:
            raise ValueError("subtitle_path must reference an ASS, SRT, or VTT subtitle file.")

        start_offset, end_offset = _validate_time_window(start_time_offset, end_time_offset)

        tracker = ProgressTracker()
        stop_event = threading.Event()
        language_code = _resolve_language_code(
            target_language or _find_language_token(resolved_subtitle) or "en"
        )
        payload = {
            "video_path": resolved_video.as_posix(),
            "subtitle_path": resolved_subtitle.as_posix(),
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
    "YoutubeDubbingService",
]
