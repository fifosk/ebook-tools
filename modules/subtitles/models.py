"""Typed containers for subtitle processing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional


_HEX_COLOR_PATTERN = re.compile(r"^#?(?P<value>[0-9A-Fa-f]{6})$")


def _normalise_hex_color(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a hex colour string in RRGGBB format")
    match = _HEX_COLOR_PATTERN.match(value.strip())
    if not match:
        raise ValueError(f"{name} must be a hex colour string in RRGGBB format")
    return f"#{match.group('value').upper()}"


@dataclass(slots=True)
class SubtitleColorPalette:
    """Colour palette applied during subtitle rendering."""

    original: str = "#FFD60A"
    translation: str = "#21C55D"
    transliteration: str = "#21C55D"
    highlight_current: str = "#FB923C"
    highlight_prior: str = "#FB923C"

    def __post_init__(self) -> None:
        object.__setattr__(self, "original", _normalise_hex_color("original", self.original))
        object.__setattr__(
            self,
            "translation",
            _normalise_hex_color("translation", self.translation),
        )
        object.__setattr__(
            self,
            "transliteration",
            _normalise_hex_color("transliteration", self.transliteration),
        )
        object.__setattr__(
            self,
            "highlight_current",
            _normalise_hex_color("highlight_current", self.highlight_current),
        )
        object.__setattr__(
            self,
            "highlight_prior",
            _normalise_hex_color("highlight_prior", self.highlight_prior),
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "original": self.original,
            "translation": self.translation,
            "transliteration": self.transliteration,
            "highlight_current": self.highlight_current,
            "highlight_prior": self.highlight_prior,
        }

    @classmethod
    def default(cls) -> "SubtitleColorPalette":
        return cls()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object] | None) -> "SubtitleColorPalette":
        if not payload:
            return cls.default()
        data = dict(payload)
        defaults = cls.default()
        return cls(
            original=str(data.get("original", defaults.original)),
            translation=str(data.get("translation", defaults.translation)),
            transliteration=str(data.get("transliteration", defaults.transliteration)),
            highlight_current=str(
                data.get("highlight_current", defaults.highlight_current)
            ),
            highlight_prior=str(data.get("highlight_prior", defaults.highlight_prior)),
        )


@dataclass(slots=True)
class SubtitleCue:
    """Normalized representation of a subtitle cue."""

    index: int
    start: float
    end: float
    lines: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def as_text(self) -> str:
        return "\n".join(self.lines).strip()


@dataclass(slots=True)
class SubtitleJobOptions:
    """Runtime configuration for a subtitle processing task."""

    input_language: str
    target_language: str
    original_language: Optional[str] = None
    show_original: bool = True
    enable_transliteration: bool = False
    highlight: bool = True
    batch_size: Optional[int] = None
    worker_count: Optional[int] = None
    mirror_batches_to_source_dir: bool = True
    start_time_offset: Optional[float] = None
    end_time_offset: Optional[float] = None
    output_format: str = "srt"
    color_palette: SubtitleColorPalette = field(default_factory=SubtitleColorPalette.default)
    llm_model: Optional[str] = None
    ass_font_size: Optional[int] = None
    ass_emphasis_scale: Optional[float] = None

    def __post_init__(self) -> None:
        input_language = (self.input_language or "").strip()
        original_language = (self.original_language or "").strip()
        if not input_language and original_language:
            input_language = original_language
        if not input_language:
            input_language = "English"
        if not original_language:
            original_language = input_language
        object.__setattr__(self, "input_language", input_language)
        object.__setattr__(self, "original_language", original_language)
        object.__setattr__(self, "show_original", bool(self.show_original))
        if self.start_time_offset is not None:
            object.__setattr__(self, "start_time_offset", float(self.start_time_offset))
        if self.end_time_offset is not None:
            object.__setattr__(self, "end_time_offset", float(self.end_time_offset))
        format_value = (self.output_format or "srt").strip().lower()
        if format_value not in {"srt", "ass"}:
            raise ValueError("output_format must be 'srt' or 'ass'")
        object.__setattr__(self, "output_format", format_value)
        palette = self.color_palette
        if isinstance(palette, Mapping):
            palette = SubtitleColorPalette.from_mapping(palette)
        if not isinstance(palette, SubtitleColorPalette):
            raise ValueError("color_palette must be a SubtitleColorPalette instance")
        object.__setattr__(self, "color_palette", palette)
        if self.start_time_offset is not None and self.start_time_offset < 0:
            raise ValueError("start_time_offset must be non-negative")
        if self.end_time_offset is not None:
            if self.end_time_offset < 0:
                raise ValueError("end_time_offset must be non-negative")
            if (
                self.start_time_offset is not None
                and self.end_time_offset <= self.start_time_offset
            ):
                raise ValueError("end_time_offset must be greater than start_time_offset")
        llm_model_value = (self.llm_model or "").strip()
        object.__setattr__(self, "llm_model", llm_model_value or None)
        font_size_value = self.ass_font_size
        resolved_font_size = None
        if font_size_value is not None:
            try:
                resolved_font_size = max(1, int(float(font_size_value)))
            except (ValueError, TypeError):
                resolved_font_size = None
        object.__setattr__(self, "ass_font_size", resolved_font_size)
        emphasis_value = self.ass_emphasis_scale
        resolved_emphasis = None
        if emphasis_value is not None:
            try:
                numeric = float(emphasis_value)
                if numeric > 0:
                    resolved_emphasis = numeric
            except (ValueError, TypeError):
                resolved_emphasis = None
        object.__setattr__(self, "ass_emphasis_scale", resolved_emphasis)

    @classmethod
    def from_mapping(cls, data: Dict[str, object]) -> "SubtitleJobOptions":
        worker_value = data.get("worker_count")
        worker_count = None
        if isinstance(worker_value, int):
            worker_count = worker_value
        elif isinstance(worker_value, str) and worker_value.strip().isdigit():
            worker_count = int(worker_value.strip())
        start_offset_value = data.get("start_time_offset")
        start_time_offset = None
        if isinstance(start_offset_value, (int, float)):
            start_time_offset = float(start_offset_value)
        elif isinstance(start_offset_value, str) and start_offset_value.strip():
            try:
                start_time_offset = float(start_offset_value.strip())
            except ValueError:
                start_time_offset = None
        end_offset_value = data.get("end_time_offset")
        end_time_offset = None
        if isinstance(end_offset_value, (int, float)):
            end_time_offset = float(end_offset_value)
        elif isinstance(end_offset_value, str) and end_offset_value.strip():
            try:
                end_time_offset = float(end_offset_value.strip())
            except ValueError:
                end_time_offset = None
        output_format_raw = str(data.get("output_format") or "srt").strip().lower()
        color_palette_payload = data.get("color_palette")
        palette = (
            SubtitleColorPalette.from_mapping(color_palette_payload)
            if isinstance(color_palette_payload, Mapping)
            else SubtitleColorPalette.default()
        )
        input_language_value = data.get("input_language")
        if isinstance(input_language_value, str):
            stripped_input = input_language_value.strip()
            input_language = stripped_input or "English"
        else:
            input_language = "English"
        target_language_value = data.get("target_language")
        if isinstance(target_language_value, str):
            stripped_target = target_language_value.strip()
            target_language = stripped_target or "English"
        else:
            target_language = "English"
        original_language_value = data.get("original_language")
        original_language = (
            original_language_value.strip()
            if isinstance(original_language_value, str)
            else None
        )
        show_original_value = data.get("show_original")
        show_original = True
        if isinstance(show_original_value, bool):
            show_original = show_original_value
        elif isinstance(show_original_value, str):
            flag = show_original_value.strip().lower()
            if flag in {"false", "0", "no", "off"}:
                show_original = False
            elif flag in {"true", "1", "yes", "on"}:
                show_original = True
        elif isinstance(show_original_value, (int, float)):
            show_original = bool(show_original_value)
        llm_model_raw = data.get("llm_model")
        llm_model = None
        if isinstance(llm_model_raw, str):
            stripped = llm_model_raw.strip()
            if stripped:
                llm_model = stripped
        font_size_raw = data.get("ass_font_size")
        ass_font_size = None
        if isinstance(font_size_raw, (int, float)):
            ass_font_size = int(font_size_raw)
        elif isinstance(font_size_raw, str) and font_size_raw.strip():
            try:
                ass_font_size = int(float(font_size_raw.strip()))
            except ValueError:
                ass_font_size = None
        emphasis_raw = data.get("ass_emphasis_scale")
        ass_emphasis_scale = None
        if isinstance(emphasis_raw, (int, float)):
            candidate_emphasis = float(emphasis_raw)
            if candidate_emphasis > 0:
                ass_emphasis_scale = candidate_emphasis
        elif isinstance(emphasis_raw, str) and emphasis_raw.strip():
            try:
                candidate_emphasis = float(emphasis_raw.strip())
            except ValueError:
                candidate_emphasis = None
            if candidate_emphasis and candidate_emphasis > 0:
                ass_emphasis_scale = candidate_emphasis

        return cls(
            input_language=input_language,
            target_language=target_language,
            original_language=original_language,
            show_original=show_original,
            enable_transliteration=bool(data.get("enable_transliteration")),
            highlight=bool(data.get("highlight", True)),
            batch_size=int(data["batch_size"]) if data.get("batch_size") else None,
            worker_count=worker_count,
            mirror_batches_to_source_dir=bool(
                data.get("mirror_batches_to_source_dir", True)
            ),
            start_time_offset=start_time_offset,
            end_time_offset=end_time_offset,
            output_format=output_format_raw or "srt",
            color_palette=palette,
            llm_model=llm_model,
            ass_font_size=ass_font_size,
            ass_emphasis_scale=ass_emphasis_scale,
        )

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "input_language": self.input_language,
            "target_language": self.target_language,
            "original_language": self.original_language,
            "show_original": self.show_original,
            "enable_transliteration": self.enable_transliteration,
            "highlight": self.highlight,
            "mirror_batches_to_source_dir": self.mirror_batches_to_source_dir,
            "output_format": self.output_format,
            "color_palette": self.color_palette.to_dict(),
        }
        if self.batch_size is not None:
            payload["batch_size"] = self.batch_size
        if self.worker_count is not None:
            payload["worker_count"] = self.worker_count
        if self.start_time_offset is not None:
            payload["start_time_offset"] = self.start_time_offset
        if self.end_time_offset is not None:
            payload["end_time_offset"] = self.end_time_offset
        if self.llm_model:
            payload["llm_model"] = self.llm_model
        if self.ass_font_size is not None:
            payload["ass_font_size"] = self.ass_font_size
        if self.ass_emphasis_scale is not None:
            payload["ass_emphasis_scale"] = self.ass_emphasis_scale
        return payload


@dataclass(slots=True)
class SubtitleProcessingResult:
    """Summary artefacts produced after processing subtitles."""

    output_path: Path
    cue_count: int
    translated_count: int
    metadata: Dict[str, object] = field(default_factory=dict)
