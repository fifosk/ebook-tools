"""Rendering helpers for subtitle output and transcripts."""

from __future__ import annotations

import html
import math
from pathlib import Path
from typing import List, Optional, Sequence, TextIO

from modules.text import split_highlight_tokens

from .common import (
    ASS_BACKGROUND_COLOR,
    ASS_BOX_OUTLINE,
    ASS_EXTENSION,
    ASS_STYLE_NAME,
    DEFAULT_ASS_EMPHASIS,
    DEFAULT_ASS_FONT_SIZE,
    MAX_ASS_EMPHASIS,
    MAX_ASS_FONT_SIZE,
    MIN_ASS_EMPHASIS,
    MIN_ASS_FONT_SIZE,
    logger,
)
from .models import SubtitleColorPalette, SubtitleCue
from .text import _ASS_TAG_PATTERN, _normalize_rendered_lines, _normalize_text


def _ass_color_token(color: str) -> str:
    hex_value = color.lstrip("#")
    red = hex_value[0:2]
    green = hex_value[2:4]
    blue = hex_value[4:6]
    return f"&H{blue}{green}{red}&"


def _resolve_ass_emphasis_scale(value: Optional[float]) -> float:
    try:
        numeric = float(value) if value is not None else DEFAULT_ASS_EMPHASIS
    except (TypeError, ValueError):
        numeric = DEFAULT_ASS_EMPHASIS
    return max(MIN_ASS_EMPHASIS, min(MAX_ASS_EMPHASIS, numeric))


def _resolve_ass_font_size(value: Optional[int]) -> int:
    try:
        numeric = int(value) if value is not None else DEFAULT_ASS_FONT_SIZE
    except (TypeError, ValueError):
        numeric = DEFAULT_ASS_FONT_SIZE
    return max(MIN_ASS_FONT_SIZE, min(MAX_ASS_FONT_SIZE, numeric))


def _token_weight(token: str) -> float:
    stripped = token.strip()
    if not stripped:
        return 1.0
    weight = 0.0
    for char in stripped:
        if char.isspace():
            continue
        category = unicodedata.category(char)
        weight += 0.5 if category.startswith("P") else 1.0
    return max(weight, 0.5)


class CueTextRenderer:
    """Render cue lines using player-compatible markup."""

    __slots__ = ("format", "palette", "emphasis_scale")

    def __init__(
        self,
        output_format: str,
        palette: SubtitleColorPalette,
        *,
        emphasis_scale: Optional[float] = None,
    ) -> None:
        self.format = output_format
        self.palette = palette
        self.emphasis_scale = _resolve_ass_emphasis_scale(emphasis_scale)

    def render_original(self, text: str) -> str:
        return self._apply_color(self.palette.original, text, bold=False, escape=True)

    def render_translation(self, text: str) -> str:
        return self._apply_color(
            self.palette.translation,
            text,
            bold=False,
            escape=True,
            scale=self.emphasis_scale,
        )

    def render_transliteration(self, text: str) -> str:
        return self._apply_color(self.palette.transliteration, text, bold=False, escape=True)

    def render_translation_highlight(self, tokens: Sequence[str], index: int) -> str:
        return self._render_highlight_sequence(
            tokens,
            index,
            self.palette.translation,
            scale=self.emphasis_scale,
        )

    def render_transliteration_highlight(self, tokens: Sequence[str], index: int) -> str:
        return self._render_highlight_sequence(tokens, index, self.palette.transliteration)

    def _render_highlight_sequence(
        self,
        tokens: Sequence[str],
        index: int,
        base_color: str,
        *,
        scale: float = 1.0,
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
                        scale=scale,
                    )
                )
            elif position == safe_index:
                fragments.append(
                    self._apply_color(
                        self.palette.highlight_current,
                        token,
                        bold=True,
                        escape=True,
                        scale=scale,
                    )
                )
            else:
                fragments.append(
                    self._apply_color(
                        base_color,
                        token,
                        bold=False,
                        escape=True,
                        scale=scale,
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
        scale: float = 1.0,
    ) -> str:
        if self.format == "ass":
            return self._apply_ass_color(color, content, bold=bold, escape=escape, scale=scale)
        return self._apply_srt_color(color, content, bold=bold, escape=escape, scale=scale)

    def _apply_srt_color(
        self,
        color: str,
        content: str,
        *,
        bold: bool,
        escape: bool,
        scale: float,
    ) -> str:
        payload = html.escape(content) if escape else content
        size_attr = ""
        if not math.isclose(scale, 1.0):
            base_size = 3
            scaled = max(1, min(7, int(math.ceil(base_size * scale))))
            size_attr = f' size="{scaled}"'
        pieces = [f'<font color="{color}"{size_attr}>']
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
        scale: float,
    ) -> str:
        payload = self._escape_ass(content) if escape else content
        components = []
        if not math.isclose(scale, 1.0):
            percent = max(10, min(1000, int(round(scale * 100))))
            components.append(f"{{\\fscx{percent}\\fscy{percent}}}")
        components.append(f"{{\\c{_ass_color_token(color)}}}")
        if bold:
            components.append("{\\b1}")
        components.append(payload)
        if bold:
            components.append("{\\b0}")
        if not math.isclose(scale, 1.0):
            components.append("{\\fscx100\\fscy100}")
        return "".join(components)

    @staticmethod
    def _escape_ass(value: str) -> str:
        return value.replace("\\", "\\\\").replace("{", r"\{").replace("}", r"\}")


def _build_output_cues(
    source: SubtitleCue,
    translation: str,
    transliteration: str,
    *,
    highlight: bool,
    show_original: bool,
    renderer: CueTextRenderer,
    original_text: Optional[str] = None,
    active_start_offset: float = 0.0,
    active_duration: Optional[float] = None,
) -> List[SubtitleCue]:
    translation = translation or ""
    normalized_original = (
        original_text if original_text is not None else _normalize_text(source.as_text())
    )
    include_original = show_original and bool(normalized_original)
    original_line = renderer.render_original(normalized_original) if include_original else ""
    translation_words = split_highlight_tokens(translation)
    if highlight and translation and not translation_words:
        translation_words = [token for token in translation.split() if token]
    transliteration_words = transliteration.split() if transliteration else []
    use_highlight = highlight and bool(translation_words)
    base_line: Optional[str] = original_line if include_original and original_line else None

    if not use_highlight:
        lines: List[str] = []
        if base_line:
            lines.append(base_line)
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

    total_duration = max(source.duration, 0.2)
    speech_offset = max(0.0, min(active_start_offset, total_duration))
    window_duration = max(0.05, total_duration - speech_offset)
    measured_duration = None
    if active_duration is not None:
        measured_duration = max(0.05, min(window_duration, active_duration))

    highlight_duration = window_duration
    if measured_duration is not None:
        tail_slack = min(0.25, max(0.08, window_duration * 0.12))
        measured_span = min(window_duration, measured_duration + tail_slack)
        # Avoid over-trusting silence detection; if detected speech is very short,
        # bias highlights toward the full dubbed window.
        min_confidence = 0.7
        if measured_span >= window_duration * min_confidence:
            highlight_duration = measured_span
    highlight_duration = max(0.05, highlight_duration)

    highlight_start = min(source.end, source.start + speech_offset)
    token_weights = [_token_weight(token) for token in translation_words]
    total_weight = sum(token_weights)
    if total_weight <= 0:
        token_weights = [1.0 for _ in translation_words]
        total_weight = float(len(token_weights))

    # Blend character-weighted pacing with a small uniform component so highlights keep
    # moving even when punctuation-only tokens are present.
    uniform_share = 1.0 / max(1, len(token_weights))
    blended_weights = []
    for weight in token_weights:
        normalized = weight / total_weight if total_weight > 0 else uniform_share
        blended = normalized * 0.85 + uniform_share * 0.15
        blended_weights.append(blended)
    weight_sum = sum(blended_weights) or 1.0
    normalized_weights = [weight / weight_sum for weight in blended_weights]

    state_durations: List[float] = [
        highlight_duration * weight for weight in normalized_weights
    ]
    total_allocated = sum(state_durations)
    if total_allocated <= 0:
        state_durations = [highlight_duration]
    else:
        correction = highlight_duration - total_allocated
        state_durations[-1] = max(0.0, state_durations[-1] + correction)

    def _build_lines(highlight_index: int) -> List[str]:
        highlight_translation = renderer.render_translation_highlight(
            translation_words,
            highlight_index,
        )
        lines = [base_line] if base_line else []
        lines.append(highlight_translation)
        if transliteration:
            if transliteration_words:
                highlight_translit = renderer.render_transliteration_highlight(
                    transliteration_words,
                    highlight_index,
                )
                lines.append(highlight_translit)
            else:
                lines.append(renderer.render_transliteration(transliteration))
        return lines

    cues: List[SubtitleCue] = []
    max_preroll = 0.35
    preroll_end = min(source.end, source.start + min(highlight_start - source.start, max_preroll))
    if preroll_end - source.start >= 0.05:
        cues.append(
            SubtitleCue(
                index=source.index,
                start=source.start,
                end=preroll_end,
                lines=_build_lines(0),
            )
        )

    cursor = highlight_start
    for highlight_index, state_duration in enumerate(state_durations):
        end_time = cursor + state_duration
        cues.append(
            SubtitleCue(
                index=source.index,
                start=cursor,
                end=end_time,
                lines=_build_lines(highlight_index),
            )
        )
        cursor = end_time

    if not cues:
        fallback_lines = _build_lines(0)
        cues.append(
            SubtitleCue(
                index=source.index,
                start=source.start,
                end=source.end,
                lines=fallback_lines if fallback_lines else list(source.lines),
            )
        )

    # Keep the final cue aligned to the subtitle window to avoid overlaps.
    cues[-1] = SubtitleCue(
        index=cues[-1].index,
        start=cues[-1].start,
        end=source.end,
        lines=cues[-1].lines,
    )

    return cues


class _SubtitleFileWriter:
    """Serialize subtitle cues using the configured subtitle format."""

    __slots__ = ("handle", "renderer", "format", "_index", "_ass_font_size")

    def __init__(
        self,
        handle: TextIO,
        renderer: CueTextRenderer,
        output_format: str,
        start_index: int = 1,
        ass_font_size: Optional[int] = None,
    ) -> None:
        self.handle = handle
        self.renderer = renderer
        self.format = output_format
        self._index = start_index
        self._ass_font_size = _resolve_ass_font_size(ass_font_size)
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
        back_color = ASS_BACKGROUND_COLOR
        font_size = self._ass_font_size
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
            f"Style: {ASS_STYLE_NAME},Arial,{font_size},{translation_color},{highlight_color},"
            f"{outline_color},{back_color},0,0,0,0,100,100,0,0,3,{ASS_BOX_OUTLINE},0,2,40,40,40,1\n"
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


class _HtmlTranscriptWriter:
    """Best-effort helper that appends batches to a companion HTML file."""

    __slots__ = ("_path", "_available", "_header_written", "_finalized")

    def __init__(self, subtitle_path: Optional[Path]) -> None:
        self._path: Optional[Path] = None
        self._available = False
        self._header_written = False
        self._finalized = False
        if subtitle_path is None:
            return
        resolved = Path(subtitle_path)
        html_dir = resolved.parent / "html"
        html_path = html_dir / f"{resolved.stem}.html"
        try:
            html_dir.mkdir(parents=True, exist_ok=True)
            html_path.unlink(missing_ok=True)
        except Exception:  # pragma: no cover - best effort preparation
            logger.warning(
                "Unable to prepare HTML transcript destination %s",
                html_path,
                exc_info=True,
            )
            return
        self._path = html_path
        self._available = True

    @property
    def path(self) -> Optional[Path]:
        return self._path

    def append(self, entries: Sequence["SubtitleHtmlEntry"]) -> None:
        if (
            not self._available
            or not entries
            or self._path is None
            or self._finalized
        ):
            return
        try:
            with self._path.open("a", encoding="utf-8") as handle:
                if not self._header_written:
                    self._write_header(handle)
                    self._header_written = True
                for entry in entries:
                    _write_html_entry(handle, entry)
        except Exception:  # pragma: no cover - best effort append
            logger.warning(
                "Unable to append HTML transcript to %s",
                self._path,
                exc_info=True,
            )
            self._available = False

    def finalize(self) -> None:
        if (
            not self._available
            or self._path is None
            or self._finalized
        ):
            return
        try:
            with self._path.open("a", encoding="utf-8") as handle:
                if not self._header_written:
                    self._write_header(handle)
                    self._header_written = True
                handle.write("</body>\n</html>\n")
            self._finalized = True
        except Exception:  # pragma: no cover - best effort footer
            logger.warning(
                "Unable to finalize HTML transcript %s",
                self._path,
                exc_info=True,
            )
            self._available = False

    def discard(self) -> None:
        if self._path is None:
            return
        try:
            self._path.unlink(missing_ok=True)
        finally:
            self._available = False

    @staticmethod
    def _write_header(handle: TextIO) -> None:
        handle.write(
            "<!DOCTYPE html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            "<meta charset=\"utf-8\">\n"
            "<title>Subtitle transcript</title>\n"
            "</head>\n"
            "<body>\n"
        )


_HTML_TIME_SEPARATOR = "\u2013"  # En dash requested for start–end headers.


def _write_html_entry(handle: TextIO, entry: "SubtitleHtmlEntry") -> None:
    start = _format_html_timestamp(entry.start)
    end = _format_html_timestamp(entry.end)
    original = html.escape(entry.original_text or "")
    transliteration = html.escape(entry.transliteration_text or "")
    translation = html.escape(entry.translation_text or "")
    handle.write(f"<h3>{start}{_HTML_TIME_SEPARATOR}{end}</h3>\n")
    handle.write(f"<p>{original}</p>\n")
    if transliteration:
        handle.write(f"<p>{transliteration}</p>\n")
    handle.write('<p style="font-size:150%; font-weight:600;">')
    handle.write(translation)
    handle.write("</p>\n\n")


def _format_html_timestamp(value: float) -> str:
    clamped = max(0, int(round(value or 0.0)))
    hours, remainder = divmod(clamped, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# Late imports to avoid circular references for type checking.
from typing import TYPE_CHECKING  # noqa: E402
import unicodedata  # noqa: E402

from .io import _seconds_to_ass_timestamp, _seconds_to_timestamp  # noqa: E402

if TYPE_CHECKING:  # pragma: no cover
    from .models import SubtitleHtmlEntry  # noqa: F401


__all__ = [
    "CueTextRenderer",
    "_HtmlTranscriptWriter",
    "_SubtitleFileWriter",
    "_ass_color_token",
    "_build_output_cues",
    "_format_html_timestamp",
    "_resolve_ass_emphasis_scale",
    "_resolve_ass_font_size",
]
