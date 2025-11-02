"""Core subtitle parsing and processing logic."""

from __future__ import annotations

import html
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, TextIO

from modules import logging_manager as log_mgr
from modules.progress_tracker import ProgressTracker
from modules.translation_engine import translate_sentence_simple
from modules.transliteration import TransliterationService, get_transliterator

from .models import (
    SubtitleColorPalette,
    SubtitleCue,
    SubtitleJobOptions,
    SubtitleProcessingResult,
)

logger = log_mgr.get_logger().getChild("subtitles.processing")

SRT_TIMESTAMP_PATTERN = re.compile(
    r"^\s*(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})"
)

WEBVTT_HEADER = re.compile(r"^\ufeff?WEBVTT", re.IGNORECASE)

DEFAULT_OUTPUT_SUFFIX = "drt"
SRT_EXTENSION = ".srt"
ASS_EXTENSION = ".ass"
ASS_STYLE_NAME = "DRT"
DEFAULT_BATCH_SIZE = 30
DEFAULT_WORKERS = 30


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

    start_offset = max(0.0, options.start_time_offset or 0.0)
    end_offset = options.end_time_offset
    if end_offset is not None:
        end_offset = max(0.0, float(end_offset))
        if end_offset <= start_offset:
            raise SubtitleProcessingError("End time must be greater than start time")

    if start_offset > 0 or end_offset is not None:
        trimmed: List[SubtitleCue] = []
        for cue in cues:
            if cue.start < start_offset:
                continue
            if end_offset is not None and cue.start >= end_offset:
                continue
            clipped_end = cue.end
            if end_offset is not None and cue.end > end_offset:
                clipped_end = end_offset
            if clipped_end <= cue.start:
                continue
            trimmed.append(
                SubtitleCue(
                    index=cue.index,
                    start=cue.start,
                    end=clipped_end,
                    lines=list(cue.lines),
                )
            )
        cues = trimmed

    total_cues = len(cues)
    if not cues:
        if end_offset is not None:
            start_label = _format_timecode_label(start_offset)
            end_label = _format_timecode_label(end_offset)
            raise SubtitleProcessingError(
                f"No cues found between {start_label} and {end_label}"
            )
        if start_offset > 0:
            label = _format_timecode_label(start_offset)
            raise SubtitleProcessingError(f"No cues found at or after start time {label}")
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
                "start_time_offset": start_offset,
            }
        )

    if transliterator is None and options.enable_transliteration:
        transliterator = get_transliterator()

    temp_output = output_path.with_suffix(output_path.suffix + ".tmp")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    renderer = CueTextRenderer(options.output_format, options.color_palette)
    output_extension = ASS_EXTENSION if options.output_format == "ass" else SRT_EXTENSION

    translated_count = 0
    next_index = 1
    mirror_next_index = 1
    mirror_target: Optional[Path] = None
    if mirror_output_path is not None:
        try:
            mirror_target = mirror_output_path.expanduser()
            if mirror_target.suffix.lower() != output_extension:
                mirror_target = mirror_target.with_suffix(output_extension)
            mirror_target.parent.mkdir(parents=True, exist_ok=True)
            mirror_target.unlink(missing_ok=True)
        except Exception:  # pragma: no cover - best effort mirror
            logger.warning(
                "Unable to prepare subtitle mirror output at %s",
                mirror_output_path,
                exc_info=True,
            )
            mirror_target = None

    try:
        with temp_output.open("w", encoding="utf-8", newline="\n") as handle:
            writer = _SubtitleFileWriter(
                handle,
                renderer,
                options.output_format,
                start_index=next_index,
            )
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
                                renderer,
                            ),
                            batch,
                        )
                    )

                    mirror_handle: Optional[TextIO] = None
                    if mirror_target is not None:
                        try:
                            mirror_handle = mirror_target.open("a", encoding="utf-8", newline="\n")
                        except Exception:  # pragma: no cover - best effort mirror
                            logger.warning(
                                "Unable to append subtitle batch to %s",
                                mirror_target,
                                exc_info=True,
                            )
                            mirror_target = None
                            mirror_handle = None

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
                        next_index = writer.write(cue_output)
                        translated_count += 1
                        if mirror_handle is not None:
                            try:
                                mirror_writer = _SubtitleFileWriter(
                                    mirror_handle,
                                    renderer,
                                    options.output_format,
                                    start_index=mirror_next_index,
                                )
                                mirror_next_index = mirror_writer.write(cue_output)
                            except Exception:  # pragma: no cover - best effort mirror
                                logger.warning(
                                    "Unable to mirror subtitle batch to %s",
                                    mirror_target,
                                    exc_info=True,
                                )
                                if mirror_handle is not None:
                                    try:
                                        mirror_handle.close()
                                    except Exception:
                                        logger.debug(
                                            "Unable to close subtitle mirror handle after failure",
                                            exc_info=True,
                                        )
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
                            mirror_target = None
                            mirror_next_index = next_index
                        finally:
                            try:
                                mirror_handle.close()
                            except Exception:  # pragma: no cover - defensive close
                                logger.debug("Unable to close subtitle mirror handle", exc_info=True)
                            mirror_handle = None
                    elif mirror_target is None:
                        mirror_next_index = next_index
    except SubtitleJobCancelled:
        temp_output.unlink(missing_ok=True)
        raise
    except Exception:
        temp_output.unlink(missing_ok=True)
        raise
    else:
        temp_output.replace(output_path)

    metadata = {
        "input_file": source_path.name,
        "target_language": options.target_language,
        "highlight": options.highlight,
        "transliteration": options.enable_transliteration,
        "batch_size": batch_size,
        "workers": worker_count,
    }
    metadata["start_time_offset_seconds"] = float(start_offset)
    metadata["start_time_offset_label"] = _format_timecode_label(start_offset)
    if end_offset is not None:
        metadata["end_time_offset_seconds"] = float(end_offset)
        metadata["end_time_offset_label"] = _format_timecode_label(end_offset)
    else:
        metadata["end_time_offset_seconds"] = None
        metadata["end_time_offset_label"] = None
    metadata["output_format"] = options.output_format
    metadata["color_palette"] = options.color_palette.to_dict()
    metadata["output_extension"] = output_extension

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


def _seconds_to_ass_timestamp(value: float) -> str:
    total_cs = int(round(value * 100))
    hours, remainder = divmod(total_cs, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

_WHITESPACE_PATTERN = re.compile(r"\s+")
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value or "")
    normalized = html.unescape(normalized)
    normalized = _HTML_TAG_PATTERN.sub(" ", normalized)
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = normalized.replace("‘", "'").replace("’", "'")
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()


class CueTextRenderer:
    """Render cue lines using player-compatible markup."""

    __slots__ = ("format", "palette")

    def __init__(self, output_format: str, palette: SubtitleColorPalette) -> None:
        self.format = output_format
        self.palette = palette

    def render_original(self, text: str) -> str:
        return self._apply_color(self.palette.original, text, bold=False, escape=True)

    def render_translation(self, text: str) -> str:
        return self._apply_color(self.palette.translation, text, bold=False, escape=True)

    def render_transliteration(self, text: str) -> str:
        return self._apply_color(self.palette.transliteration, text, bold=False, escape=True)

    def render_translation_highlight(self, tokens: Sequence[str], index: int) -> str:
        return self._render_highlight_sequence(tokens, index, self.palette.translation)

    def render_transliteration_highlight(self, tokens: Sequence[str], index: int) -> str:
        return self._render_highlight_sequence(tokens, index, self.palette.transliteration)

    def _render_highlight_sequence(
        self,
        tokens: Sequence[str],
        index: int,
        base_color: str,
    ) -> str:
        if not tokens:
            return ""
        safe_index = min(max(index, 0), len(tokens) - 1)
        fragments: List[str] = []
        for position, token in enumerate(tokens):
            if position < safe_index:
                fragments.append(
                    self._apply_color(
                        self.palette.highlight_prior,
                        token,
                        bold=False,
                        escape=True,
                    )
                )
            elif position == safe_index:
                fragments.append(
                    self._apply_color(
                        self.palette.highlight_current,
                        token,
                        bold=True,
                        escape=True,
                    )
                )
            else:
                fragments.append(
                    self._apply_color(
                        base_color,
                        token,
                        bold=False,
                        escape=True,
                    )
                )
        return " ".join(fragments)

    def _apply_color(
        self,
        color: str,
        content: str,
        *,
        bold: bool,
        escape: bool,
    ) -> str:
        if self.format == "ass":
            return self._apply_ass_color(color, content, bold=bold, escape=escape)
        return self._apply_srt_color(color, content, bold=bold, escape=escape)

    def _apply_srt_color(
        self,
        color: str,
        content: str,
        *,
        bold: bool,
        escape: bool,
    ) -> str:
        payload = html.escape(content) if escape else content
        pieces = [f'<font color="{color}">']
        if bold:
            pieces.append("<b>")
        pieces.append(payload)
        if bold:
            pieces.append("</b>")
        pieces.append("</font>")
        return "".join(pieces)

    def _apply_ass_color(
        self,
        color: str,
        content: str,
        *,
        bold: bool,
        escape: bool,
    ) -> str:
        payload = self._escape_ass(content) if escape else content
        components = [f"{{\\c{_ass_color_token(color)}}}"]
        if bold:
            components.append("{\\b1}")
        components.append(payload)
        if bold:
            components.append("{\\b0}")
        return "".join(components)

    @staticmethod
    def _escape_ass(value: str) -> str:
        return value.replace("\\", "\\\\").replace("{", r"\{").replace("}", r"\}")


def _ass_color_token(color: str) -> str:
    hex_value = color.lstrip("#")
    red = hex_value[0:2]
    green = hex_value[2:4]
    blue = hex_value[4:6]
    return f"&H{blue}{green}{red}&"


def _build_output_cues(
    source: SubtitleCue,
    translation: str,
    transliteration: str,
    *,
    highlight: bool,
    renderer: CueTextRenderer,
) -> List[SubtitleCue]:
    translation = translation or ""
    original_text = _normalize_text(source.as_text())
    original_line = renderer.render_original(original_text)
    translation_words = translation.split()
    transliteration_words = transliteration.split() if transliteration else []

    if not highlight or not translation_words:
        lines = [original_line]
        if translation:
            lines.append(renderer.render_translation(translation))
        if transliteration:
            lines.append(renderer.render_transliteration(transliteration))
        return [
            SubtitleCue(
                index=source.index,
                start=source.start,
                end=source.end,
                lines=lines,
            )
        ]

    duration = max(source.duration, 0.2)
    step = duration / max(len(translation_words), 1)
    cues: List[SubtitleCue] = []

    for offset in range(len(translation_words)):
        highlight_translation = renderer.render_translation_highlight(translation_words, offset)
        lines = [
            original_line,
            highlight_translation,
        ]
        if transliteration:
            if transliteration_words:
                highlight_translit = renderer.render_transliteration_highlight(
                    transliteration_words,
                    offset,
                )
                lines.append(highlight_translit)
            else:
                lines.append(renderer.render_transliteration(transliteration))
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


class _SubtitleFileWriter:
    """Serialize subtitle cues using the configured subtitle format."""

    __slots__ = ("handle", "renderer", "format", "_index")

    def __init__(
        self,
        handle: TextIO,
        renderer: CueTextRenderer,
        output_format: str,
        start_index: int = 1,
    ) -> None:
        self.handle = handle
        self.renderer = renderer
        self.format = output_format
        self._index = start_index
        if self.format == "ass" and self._index == 1:
            self._write_ass_header()

    @property
    def index(self) -> int:
        return self._index

    def write(self, cues: Sequence[SubtitleCue]) -> int:
        if not cues:
            return self._index
        if self.format == "ass":
            self._write_ass_block(cues)
        else:
            self._write_srt_block(cues)
        return self._index

    def _write_srt_block(self, cues: Sequence[SubtitleCue]) -> None:
        index = self._index
        for cue in cues:
            start_ts = _seconds_to_timestamp(cue.start)
            end_ts = _seconds_to_timestamp(cue.end)
            self.handle.write(f"{index}\n")
            self.handle.write(f"{start_ts} --> {end_ts}\n")
            for line in cue.lines:
                self.handle.write(f"{line}\n")
            self.handle.write("\n")
            index += 1
        self._index = index

    def _write_ass_block(self, cues: Sequence[SubtitleCue]) -> None:
        for cue in cues:
            start_ts = _seconds_to_ass_timestamp(cue.start)
            end_ts = _seconds_to_ass_timestamp(cue.end)
            text = self._format_ass_lines(cue.lines)
            self.handle.write(
                f"Dialogue: 0,{start_ts},{end_ts},{ASS_STYLE_NAME},,0,0,0,,{text}\n"
            )
        self._index += len(cues)

    def _write_ass_header(self) -> None:
        palette = self.renderer.palette
        translation_color = _ass_color_token(palette.translation)
        highlight_color = _ass_color_token(palette.highlight_current)
        outline_color = "&H64000000"
        back_color = "&H32000000"
        header = (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "Collisions: Normal\n"
            "PlayResX: 1920\n"
            "PlayResY: 1080\n"
            "WrapStyle: 0\n"
            "ScaledBorderAndShadow: yes\n"
            "\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
            "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: {ASS_STYLE_NAME},Arial,48,{translation_color},{highlight_color},"
            f"{outline_color},{back_color},0,0,0,0,100,100,0,0,1,2,0,2,40,40,40,1\n"
            "\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
        self.handle.write(header)

    @staticmethod
    def _format_ass_lines(lines: Sequence[str]) -> str:
        buffer: List[str] = []
        for line in lines:
            candidate = line.replace("\r\n", "\n").replace("\r", "\n")
            buffer.append(candidate.replace("\n", r"\N"))
        return r"\N".join(buffer)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_timecode_label(total_seconds: float) -> str:
    total = max(0, int(round(total_seconds)))
    minutes_total, seconds = divmod(total, 60)
    hours, minutes = divmod(minutes_total, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes_total:02d}:{seconds:02d}"


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
    resolved = min(DEFAULT_WORKERS, batch_size, total)
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
    renderer: CueTextRenderer,
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
        renderer=renderer,
    )
