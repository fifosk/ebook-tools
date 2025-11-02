"""Core subtitle parsing and processing logic."""

from __future__ import annotations

import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
import os
from typing import Iterable, List, Optional, Sequence

from modules import logging_manager as log_mgr
from modules.progress_tracker import ProgressTracker
from modules.translation_engine import translate_sentence_simple
from modules.transliteration import TransliterationService, get_transliterator

from .models import SubtitleCue, SubtitleJobOptions, SubtitleProcessingResult

logger = log_mgr.get_logger().getChild("subtitles.processing")

SRT_TIMESTAMP_PATTERN = re.compile(
    r"^\s*(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})"
)

WEBVTT_HEADER = re.compile(r"^\ufeff?WEBVTT", re.IGNORECASE)

DEFAULT_OUTPUT_SUFFIX = "drt.srt"
DEFAULT_BATCH_SIZE = 24
DEFAULT_WORKERS = 4


class SubtitleProcessingError(RuntimeError):
    """Raised when subtitle parsing or processing fails."""


class SubtitleJobCancelled(RuntimeError):
    """Raised when a subtitle job is cancelled during processing."""


def load_subtitle_cues(path: Path) -> List[SubtitleCue]:
    """Parse ``path`` as an SRT/VTT file and return normalized cues."""

    try:
        payload = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        payload = path.read_text(encoding="utf-8-sig")

    if WEBVTT_HEADER.match(payload.splitlines()[0] if payload else ""):
        return _parse_webvtt(payload)
    if path.suffix.lower() == ".vtt":
        return _parse_webvtt(payload)
    return _parse_srt(payload)


def process_subtitle_file(
    source_path: Path,
    output_path: Path,
    options: SubtitleJobOptions,
    *,
    mirror_output_path: Optional[Path] = None,
    tracker: Optional[ProgressTracker] = None,
    stop_event=None,
    transliterator: Optional[TransliterationService] = None,
) -> SubtitleProcessingResult:
    """Process ``source_path`` and persist the translated subtitles."""

    cues = load_subtitle_cues(source_path)
    total_cues = len(cues)
    if not cues:
        raise SubtitleProcessingError("No cues processed from source subtitle")

    batch_size = _resolve_batch_size(options.batch_size, total_cues)
    worker_count = _resolve_worker_count(options.worker_count, batch_size, total_cues)

    if tracker is not None:
        tracker.set_total(total_cues)
        tracker.publish_start(
            {
                "stage": "subtitle",
                "input_file": source_path.name,
                "target_language": options.target_language,
                "batch_size": batch_size,
                "workers": worker_count,
            }
        )

    if transliterator is None and options.enable_transliteration:
        transliterator = get_transliterator()

    temp_output = output_path.with_suffix(output_path.suffix + ".tmp")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    translated_count = 0
    next_index = 1
    mirror_next_index = 1
    mirror_handle = None
    mirror_target: Optional[Path] = None
    if mirror_output_path is not None:
        try:
            mirror_target = mirror_output_path.expanduser()
            mirror_target.parent.mkdir(parents=True, exist_ok=True)
            mirror_handle = mirror_target.open("w", encoding="utf-8", newline="\n")
        except Exception:  # pragma: no cover - best effort mirror
            logger.warning(
                "Unable to open subtitle mirror output at %s",
                mirror_output_path,
                exc_info=True,
            )
            mirror_handle = None
            mirror_target = None

    try:
        with temp_output.open("w", encoding="utf-8", newline="\n") as handle:
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                for batch_number, batch_start in enumerate(range(0, total_cues, batch_size), start=1):
                    if _is_cancelled(stop_event):
                        raise SubtitleJobCancelled("Subtitle job interrupted by cancellation request")

                    batch = cues[batch_start : batch_start + batch_size]
                    processed_batch = list(
                        executor.map(
                            lambda cue: _process_cue(
                                cue,
                                options,
                                transliterator,
                                stop_event,
                            ),
                            batch,
                        )
                    )

                    for offset, cue_output in enumerate(processed_batch, start=1):
                        cue_index = batch_start + offset
                        if tracker is not None:
                            tracker.record_step_completion(
                                stage="subtitle",
                                index=cue_index,
                                total=total_cues,
                                metadata={
                                    "batch": batch_number,
                                    "batch_size": batch_size,
                                },
                            )
                        next_index = _write_srt_block(handle, cue_output, next_index)
                        translated_count += 1
                        if mirror_handle is not None:
                            try:
                                mirror_next_index = _write_srt_block(
                                    mirror_handle,
                                    cue_output,
                                    mirror_next_index,
                                )
                            except Exception:  # pragma: no cover - best effort mirror
                                logger.warning(
                                    "Unable to mirror subtitle batch to %s",
                                    mirror_target,
                                    exc_info=True,
                                )
                                try:
                                    mirror_handle.close()
                                except Exception:
                                    pass
                                mirror_handle = None
                                mirror_target = None
                                mirror_next_index = next_index
                    handle.flush()
                    if mirror_handle is not None:
                        try:
                            mirror_handle.flush()
                        except Exception:  # pragma: no cover - best effort mirror
                            logger.warning(
                                "Unable to flush mirrored subtitle output %s",
                                mirror_target,
                                exc_info=True,
                            )
                            try:
                                mirror_handle.close()
                            except Exception:
                                pass
                            mirror_handle = None
                            mirror_target = None
                            mirror_next_index = next_index
    except SubtitleJobCancelled:
        temp_output.unlink(missing_ok=True)
        raise
    except Exception:
        temp_output.unlink(missing_ok=True)
        raise
    else:
        temp_output.replace(output_path)
    finally:
        if mirror_handle is not None:
            try:
                mirror_handle.close()
            except Exception:  # pragma: no cover - defensive close
                logger.debug("Unable to close subtitle mirror handle", exc_info=True)

    metadata = {
        "input_file": source_path.name,
        "target_language": options.target_language,
        "highlight": options.highlight,
        "transliteration": options.enable_transliteration,
        "batch_size": batch_size,
        "workers": worker_count,
    }

    return SubtitleProcessingResult(
        output_path=output_path,
        cue_count=total_cues,
        translated_count=translated_count,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Parsing utilities
# ---------------------------------------------------------------------------

def _parse_srt(payload: str) -> List[SubtitleCue]:
    blocks = re.split(r"\n{2,}", payload.strip())
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


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

_WHITESPACE_PATTERN = re.compile(r"\s+")


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value or "")
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = normalized.replace("‘", "'").replace("’", "'")
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()


def _build_output_cues(
    source: SubtitleCue,
    translation: str,
    transliteration: str,
    *,
    highlight: bool,
) -> List[SubtitleCue]:
    if not translation:
        translation = ""

    base_lines = [source.as_text(), translation]
    if transliteration:
        base_lines.append(transliteration)

    if not highlight or not translation:
        return [
            SubtitleCue(
                index=source.index,
                start=source.start,
                end=source.end,
                lines=base_lines,
            )
        ]

    words = translation.split()
    if not words:
        return [
            SubtitleCue(
                index=source.index,
                start=source.start,
                end=source.end,
                lines=base_lines,
            )
        ]

    duration = max(source.duration, 0.2)
    step = duration / max(len(words), 1)
    cues: List[SubtitleCue] = []

    for offset, count in enumerate(range(1, len(words) + 1)):
        highlight_translation = _highlight_words(words, count)
        lines = [source.as_text(), highlight_translation]
        if transliteration:
            transliteration_words = transliteration.split()
            highlight_translit = _highlight_words(transliteration_words, count)
            lines.append(highlight_translit)
        cues.append(
            SubtitleCue(
                index=source.index,
                start=source.start + offset * step,
                end=source.start + (offset + 1) * step,
                lines=lines,
            )
        )

    last_end = cues[-1].end if cues else source.end
    if last_end < source.end - 0.01:
        cues[-1].end = source.end
    elif last_end > source.end + 0.5:
        delta = last_end - source.end
        cues[-1].end -= delta

    return cues


def _highlight_words(words: Sequence[str], count: int) -> str:
    fragments: List[str] = []
    for index, word in enumerate(words):
        token = word
        if index < count - 1:
            token = f"<span class=\"drt-prior\">{word}</span>"
        elif index == count - 1:
            token = f"<span class=\"drt-current\">{word}</span>"
        fragments.append(token)
    return " ".join(fragments)


# ---------------------------------------------------------------------------
# Utility dataclasses for persistence
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SubtitleOutputSummary:
    """Lightweight summary describing the generated subtitle file."""

    relative_path: str
    format: str
    word_count: int


def _resolve_batch_size(candidate: Optional[int], total: int) -> int:
    if isinstance(candidate, int) and candidate > 0:
        return max(1, min(candidate, total))
    return max(1, min(DEFAULT_BATCH_SIZE, total))


def _resolve_worker_count(
    candidate: Optional[int],
    batch_size: int,
    total: int,
) -> int:
    if isinstance(candidate, int) and candidate > 0:
        return max(1, min(candidate, total))
    cpu_default = os.cpu_count() or DEFAULT_WORKERS
    resolved = min(DEFAULT_WORKERS, cpu_default)
    resolved = min(resolved, batch_size, total)
    return max(1, resolved)


def _is_cancelled(stop_event) -> bool:
    if stop_event is None:
        return False
    checker = getattr(stop_event, "is_set", None)
    if callable(checker):
        try:
            return bool(checker())
        except Exception:  # pragma: no cover - defensive guard
            return False
    return False


def _process_cue(
    cue: SubtitleCue,
    options: SubtitleJobOptions,
    transliterator: Optional[TransliterationService],
    stop_event,
) -> List[SubtitleCue]:
    if _is_cancelled(stop_event):
        raise SubtitleJobCancelled("Subtitle job interrupted by cancellation request")

    normalized_source = cue.as_text()
    translation = _normalize_text(
        translate_sentence_simple(
            normalized_source,
            options.input_language,
            options.target_language,
            include_transliteration=False,
        )
    )

    transliteration_text = ""
    if options.enable_transliteration and transliterator is not None and translation:
        try:
            transliteration_result = transliterator.transliterate(
                translation,
                options.target_language,
            )
        except Exception as exc:  # pragma: no cover - defensive fallbacks
            logger.debug(
                "Transliteration failed for cue %s: %s", cue.index, exc, exc_info=True
            )
        else:
            transliteration_text = _normalize_text(transliteration_result.text)

    return _build_output_cues(
        cue,
        translation,
        transliteration_text,
        highlight=options.highlight,
    )


def _write_srt_block(handle, cues: Sequence[SubtitleCue], start_index: int) -> int:
    index = start_index
    for cue in cues:
        start_ts = _seconds_to_timestamp(cue.start)
        end_ts = _seconds_to_timestamp(cue.end)
        handle.write(f"{index}\n")
        handle.write(f"{start_ts} --> {end_ts}\n")
        for line in cue.lines:
            handle.write(f"{line}\n")
        handle.write("\n")
        index += 1
    return index
