"""Slide rendering orchestration built on modular layout and templates."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment

from modules import logging_manager as log_mgr
from modules.audio.highlight import (
    HighlightEvent,
    _build_events_from_metadata,
    _build_legacy_highlight_events,
    _get_audio_metadata,
    coalesce_highlight_events,
)
from modules.audio.tts import active_tmp_dir, silence_audio_path

from .layout_engine import GlyphMetricsCache, LayoutEngine
from .slide_core import HighlightSpec, Slide, SlideType
from .template_manager import TemplateDefinition, TemplateManager, _parse_color

logger = log_mgr.logger


@dataclass(slots=True)
class SlideRenderOptions:
    """Options controlling how slide frames are rendered."""

    parallelism: str = "off"
    workers: Optional[int] = None
    prefer_pillow_simd: bool = False
    benchmark_rendering: bool = False


class SlideRenderProfiler:
    """Collects timing/counter statistics for slide rendering operations."""

    def __init__(self) -> None:
        self._timers: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))
        self._counters: Dict[str, int] = defaultdict(int)

    @contextmanager
    def time_block(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            count, total = self._timers[name]
            self._timers[name] = (count + 1, total + elapsed)

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] += value

    def merge(self, other: "SlideRenderProfiler") -> None:
        for key, (count, total) in other._timers.items():
            cur_count, cur_total = self._timers[key]
            self._timers[key] = (cur_count + count, cur_total + total)
        for key, value in other._counters.items():
            self._counters[key] += value

    def log_summary(self, sentence_index: int) -> None:
        if not self._timers and not self._counters:
            return
        logger.debug(
            "Slide rendering benchmark for sentence %s:",
            sentence_index,
            extra={"event": "video.slide.benchmark", "console_suppress": True},
        )
        for name, (count, total) in sorted(
            self._timers.items(), key=lambda item: item[1][1], reverse=True
        ):
            avg = total / count if count else 0.0
            logger.debug(
                "  %s -> total %.4fs across %s calls (avg %.6fs)",
                name,
                total,
                count,
                avg,
                extra={"event": f"video.slide.benchmark.{name}", "console_suppress": True},
            )
        for name, value in self._counters.items():
            logger.debug(
                "  %s -> %s",
                name,
                value,
                extra={
                    "event": f"video.slide.benchmark.counter.{name}",
                    "console_suppress": True,
                },
            )


@dataclass(slots=True)
class SlideFrameTask:
    index: int
    block: str
    duration: float
    original_highlight_index: int
    translation_highlight_index: int
    transliteration_highlight_index: int
    original_char_range: Optional[Tuple[int, int]]
    translation_char_range: Optional[Tuple[int, int]]
    transliteration_char_range: Optional[Tuple[int, int]]
    slide_size: Sequence[int]
    initial_font_size: int
    default_font_path: str
    bg_color: Sequence[int]
    cover_image_bytes: Optional[bytes]
    header_info: str
    highlight_granularity: str
    output_path: str
    template_name: Optional[str]


_GLYPH_CACHE = GlyphMetricsCache()


def _serialize_cover_image(image: Optional[Image.Image]) -> Optional[bytes]:
    if image is None:
        return None
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _deserialize_cover_image(payload: Optional[bytes]) -> Optional[Image.Image]:
    if payload is None:
        return None
    stream = io.BytesIO(payload)
    img = Image.open(stream)
    converted = img.convert("RGB")
    converted.load()
    img.close()
    return converted


def _has_simd_support() -> bool:
    core = getattr(Image, "core", None)
    return bool(getattr(core, "have_simd", False))


_SIMD_STATUS_LOGGED = False


def _log_simd_preference(prefer_simd: bool) -> None:
    global _SIMD_STATUS_LOGGED
    if not prefer_simd or _SIMD_STATUS_LOGGED:
        return
    _SIMD_STATUS_LOGGED = True
    if _has_simd_support():
        logger.debug(
            "Pillow SIMD acceleration detected for slide rendering.",
            extra={"event": "video.slide.simd", "console_suppress": True},
        )
    else:
        logger.warning(
            "Pillow-SIMD acceleration requested but not available on this installation.",
            extra={"event": "video.slide.simd.missing"},
        )


class SlideRenderer:
    """Render :class:`Slide` instances using JSON-defined templates."""

    def __init__(
        self,
        *,
        template_manager: Optional[TemplateManager] = None,
        layout_engine: Optional[LayoutEngine] = None,
    ) -> None:
        self._template_manager = template_manager or TemplateManager()
        self._layout_engine = layout_engine or LayoutEngine(_GLYPH_CACHE)

    # Rendering helpers -------------------------------------------------
    def _resolve_template(
        self, slide: Slide, template_name: Optional[str]
    ) -> Tuple[TemplateDefinition, Mapping[str, object]]:
        template = self._template_manager.get_template(template_name or slide.template_name)
        resolved = template.resolve(slide.slide_type.value)
        return template, resolved

    def _ensure_font(
        self, path: str, size: int, *, fallback: Optional[ImageFont.ImageFont] = None
    ) -> ImageFont.ImageFont:
        try:
            return ImageFont.truetype(path, size)
        except IOError:
            return fallback or ImageFont.load_default()

    def _extract_sentence_segments(self, slide: Slide) -> Tuple[str, str, str]:
        original = slide.content[0] if slide.content else ""
        translation = slide.content[1] if len(slide.content) >= 2 else ""
        transliteration = slide.content[2] if len(slide.content) >= 3 else ""
        return original, translation, transliteration

    def _build_highlight_specs(
        self,
        slide: Slide,
        original_word_index: Optional[int],
        translation_word_index: Optional[int],
        transliteration_word_index: Optional[int],
        original_char_range: Optional[Tuple[int, int]],
        translation_char_range: Optional[Tuple[int, int]],
        transliteration_char_range: Optional[Tuple[int, int]],
    ) -> Tuple[HighlightSpec, HighlightSpec, HighlightSpec]:
        original_spec = slide.highlight_original
        translation_spec = slide.highlight_translation
        transliteration_spec = slide.highlight_transliteration
        if original_word_index is not None or original_char_range is not None:
            original_spec = HighlightSpec(
                word_index=original_word_index,
                char_range=original_char_range,
            )
        if translation_word_index is not None or translation_char_range is not None:
            translation_spec = HighlightSpec(
                word_index=translation_word_index,
                char_range=translation_char_range,
            )
        if transliteration_word_index is not None or transliteration_char_range is not None:
            transliteration_spec = HighlightSpec(
                word_index=transliteration_word_index,
                char_range=transliteration_char_range,
            )
        return original_spec, translation_spec, transliteration_spec

    def _normalize_char_range(
        self, value: Optional[Tuple[int, int]]
    ) -> Optional[Tuple[int, int]]:
        if not value:
            return None
        start, end = value
        if start is None or end is None:
            return None
        start_idx = int(start)
        end_idx = int(end)
        if end_idx <= start_idx:
            return None
        return (start_idx, end_idx)

    def render_sentence_slide_image(
        self,
        slide: Slide,
        *,
        original_highlight_word_index: Optional[int] = None,
        translation_highlight_word_index: Optional[int] = None,
        transliteration_highlight_word_index: Optional[int] = None,
        original_highlight_char_range: Optional[Tuple[int, int]] = None,
        translation_highlight_char_range: Optional[Tuple[int, int]] = None,
        transliteration_highlight_char_range: Optional[Tuple[int, int]] = None,
        highlight_granularity: str = "word",
        slide_size: Sequence[int] = (1280, 720),
        initial_font_size: int = 50,
        default_font_path: str = "Arial.ttf",
        bg_color: Optional[Sequence[int]] = None,
        cover_img: Optional[Image.Image] = None,
        header_info: str = "",
        template_name: Optional[str] = None,
        profiler: Optional[SlideRenderProfiler] = None,
    ) -> Image.Image:
        template, resolved = self._resolve_template(slide, template_name)
        layout_cfg = resolved.get("layout") if isinstance(resolved.get("layout"), Mapping) else {}
        blocks_cfg = layout_cfg.get("blocks") if isinstance(layout_cfg, Mapping) else {}
        header_cfg = blocks_cfg.get("header") if isinstance(blocks_cfg, Mapping) else {}
        body_cfg = blocks_cfg.get("body") if isinstance(blocks_cfg, Mapping) else {}

        header_height = int(header_cfg.get("height", 150)) if isinstance(header_cfg, Mapping) else 150
        left_area_width = int(header_cfg.get("left_width", header_height)) if isinstance(header_cfg, Mapping) else header_height

        extra_line_spacing = float(body_cfg.get("line_spacing", 10)) if isinstance(body_cfg, Mapping) else 10.0
        segment_spacing = float(body_cfg.get("segment_spacing", 20)) if isinstance(body_cfg, Mapping) else 20.0
        separator_pre_margin = float(body_cfg.get("separator_margin_pre", 10)) if isinstance(body_cfg, Mapping) else 10.0
        separator_color = _parse_color(
            body_cfg.get("separator_color") if isinstance(body_cfg, Mapping) else None,
            default=(150, 150, 150),
        )
        separator_thickness = int(body_cfg.get("separator_thickness", 2)) if isinstance(body_cfg, Mapping) else 2
        separator_margin = int(body_cfg.get("separator_margin", 40)) if isinstance(body_cfg, Mapping) else 40
        highlight_scale = float(body_cfg.get("highlight_scale", 1.05)) if isinstance(body_cfg, Mapping) else 1.05

        font_cfg = resolved.get("font") if isinstance(resolved.get("font"), Mapping) else {}
        header_font_size = int(font_cfg.get("size_title", 24)) if isinstance(font_cfg, Mapping) else 24
        body_font_size = int(font_cfg.get("size_body", initial_font_size)) if isinstance(font_cfg, Mapping) else initial_font_size
        header_color = _parse_color(
            font_cfg.get("color_title") if isinstance(font_cfg, Mapping) else None,
            default=(255, 255, 255),
        )

        colors_cfg = resolved.get("colors") if isinstance(resolved.get("colors"), Mapping) else {}
        background_color = tuple(int(v) for v in (bg_color or colors_cfg.get("background", (0, 0, 0))))
        accent_color = _parse_color(colors_cfg.get("accent") if isinstance(colors_cfg, Mapping) else None, default=(255, 165, 0))
        segment_colors = resolved.get("segment_colors") if isinstance(resolved.get("segment_colors"), Mapping) else {}
        original_color = _parse_color(segment_colors.get("original") if isinstance(segment_colors, Mapping) else None, default=(255, 255, 0))
        translation_color = _parse_color(
            segment_colors.get("translation") if isinstance(segment_colors, Mapping) else None,
            default=(153, 255, 153),
        )
        transliteration_color = _parse_color(
            segment_colors.get("transliteration") if isinstance(segment_colors, Mapping) else None,
            default=(255, 255, 0),
        )

        img = Image.new("RGB", tuple(int(v) for v in slide_size), background_color)
        draw = ImageDraw.Draw(img)

        raw_header = header_info or slide.title
        with profiler.time_block("draw.rectangle") if profiler else nullcontext():
            draw.rectangle([0, 0, slide_size[0], header_height], fill=background_color)

        if cover_img:
            cover_thumb = cover_img.copy()
            new_width = max(left_area_width - 20, 1)
            new_height = max(header_height - 20, 1)
            cover_thumb.thumbnail((new_width, new_height))
            img.paste(cover_thumb, (10, max((header_height - cover_thumb.height) // 2, 0)))

        header_font = self._ensure_font(default_font_path, header_font_size)
        header_lines = raw_header.split("\n")
        header_line_spacing = float(header_cfg.get("line_spacing", 4)) if isinstance(header_cfg, Mapping) else 4.0
        max_header_width = 0.0
        total_header_height = 0.0
        for line in header_lines:
            line_width, line_height = self._layout_engine.text_size(draw, header_font, line)
            max_header_width = max(max_header_width, line_width)
            total_header_height += line_height
        total_header_height += header_line_spacing * (len(header_lines) - 1)
        if cover_img:
            available_width = slide_size[0] - left_area_width
            header_x = left_area_width + (available_width - max_header_width) // 2
        else:
            header_x = (slide_size[0] - max_header_width) // 2
        header_y = (header_height - total_header_height) // 2

        with profiler.time_block("draw.multiline_text") if profiler else nullcontext():
            draw.multiline_text(
                (header_x, header_y),
                raw_header,
                font=header_font,
                fill=header_color,
                spacing=header_line_spacing,
                align="center",
            )

        slide_for_segments = self._extract_sentence_segments(slide)
        original_seg, translation_seg, transliteration_seg = slide_for_segments

        original_spec, translation_spec, transliteration_spec = self._build_highlight_specs(
            slide,
            original_highlight_word_index,
            translation_highlight_word_index,
            transliteration_highlight_word_index,
            self._normalize_char_range(original_highlight_char_range),
            self._normalize_char_range(translation_highlight_char_range),
            self._normalize_char_range(transliteration_highlight_char_range),
        )

        scale_factor = highlight_scale

        def wrap_text_local(
            text: str, draw_ctx: ImageDraw.ImageDraw, font_obj: ImageFont.ImageFont, max_width: int
        ) -> str:
            words = text.split()
            if not words:
                return ""
            lines_: List[str] = []
            current_line = words[0]
            for word in words[1:]:
                test_line = f"{current_line} {word}".strip()
                line_width, _ = self._layout_engine.text_size(draw_ctx, font_obj, test_line)
                if line_width <= max_width:
                    current_line = test_line
                else:
                    lines_.append(current_line)
                    current_line = word
            lines_.append(current_line)
            return "\n".join(lines_)

        def get_wrapped_text_and_font(text: str) -> Tuple[str, ImageFont.ImageFont]:
            max_width = int(slide_size[0] * float(body_cfg.get("max_width_ratio", 0.9)))
            max_height = int(slide_size[1] * float(body_cfg.get("max_height_ratio", 0.9)))
            font_size = int(body_font_size * float(body_cfg.get("scale", 0.85)))
            chosen_font: Optional[ImageFont.ImageFont] = None
            wrapped_text = text
            while font_size > 10:
                test_font = self._ensure_font(default_font_path, font_size)
                candidate_wrapped = wrap_text_local(text, draw, test_font, max_width)
                total_height = 0
                lines = candidate_wrapped.split("\n")
                for i, line in enumerate(lines):
                    _, height = self._layout_engine.text_size(draw, test_font, line)
                    total_height += height
                    if i < len(lines) - 1:
                        total_height += extra_line_spacing
                if total_height <= max_height:
                    wrapped_text = candidate_wrapped
                    chosen_font = test_font
                    break
                font_size -= 2
            if chosen_font is None:
                chosen_font = ImageFont.load_default()
            return wrapped_text, chosen_font

        def compute_height(lines: Iterable[str], font_obj: ImageFont.ImageFont) -> int:
            total = 0
            line_list = list(lines)
            for i, line in enumerate(line_list):
                _, height = self._layout_engine.text_size(draw, font_obj, line)
                total += height
                if i < len(line_list) - 1:
                    total += extra_line_spacing
            return total

        def get_highlight_font(base_font: ImageFont.ImageFont) -> ImageFont.ImageFont:
            base_size = getattr(base_font, "size", body_font_size)
            target_size = max(int(base_size * scale_factor), 1)
            return self._ensure_font(default_font_path, target_size, fallback=base_font)

        wrapped_orig, font_orig = get_wrapped_text_and_font(original_seg)
        orig_lines = wrapped_orig.split("\n") if wrapped_orig else [""]
        orig_height = compute_height(orig_lines, font_orig)

        wrapped_trans, font_trans = get_wrapped_text_and_font(translation_seg)
        trans_lines = wrapped_trans.split("\n") if wrapped_trans else [""]
        trans_height = compute_height(trans_lines, font_trans)

        translit_lines: List[str] = []
        translit_height = 0
        if transliteration_seg:
            wrapped_translit, font_translit = get_wrapped_text_and_font(transliteration_seg)
            translit_lines = wrapped_translit.split("\n") if wrapped_translit else [""]
            translit_height = compute_height(translit_lines, font_translit)
        else:
            font_translit = font_trans

        segments_heights = [orig_height, trans_height]
        if transliteration_seg:
            segments_heights.append(translit_height)
        num_segments = len(segments_heights)
        num_separators = max(num_segments - 1, 0)
        total_text_height_active = (
            sum(segments_heights)
            + segment_spacing * num_separators
            + separator_thickness * num_separators
        )

        available_area = slide_size[1] - header_height
        y_text = header_height + (available_area - total_text_height_active) // 2

        def render_char_range(
            *,
            text_value: str,
            lines_list: Sequence[str],
            font_obj: ImageFont.ImageFont,
            char_range: Optional[Tuple[int, int]],
            color_value: Sequence[int],
            start_y: float,
        ) -> float:
            layouts, char_map, end_y = self._layout_engine.prepare_line_layout(
                text=text_value,
                lines=lines_list,
                font=font_obj,
                draw_ctx=draw,
                slide_width=slide_size[0],
                start_y=start_y,
                line_spacing=extra_line_spacing,
            )
            self._layout_engine.fill_char_range(draw, char_map, char_range, color_value)
            for layout in layouts:
                with profiler.time_block("draw.text") if profiler else nullcontext():
                    draw.text(
                        (layout.x, layout.y),
                        layout.text,
                        font=font_obj,
                        fill=color_value,
                    )
            return end_y

        orig_char_range = original_spec.char_range if highlight_granularity == "char" else None
        if orig_char_range is not None:
            y_text = render_char_range(
                text_value=original_seg,
                lines_list=orig_lines,
                font_obj=font_orig,
                char_range=orig_char_range,
                color_value=original_color,
                start_y=y_text,
            )
        else:
            word_counter = 0
            for line in orig_lines:
                words_line = line.split()
                space_width, _ = self._layout_engine.text_size(draw, font_orig, " ")
                word_widths = [self._layout_engine.text_size(draw, font_orig, w)[0] for w in words_line]
                total_width = sum(word_widths) + space_width * (len(words_line) - 1 if words_line else 0)
                x_line = (slide_size[0] - total_width) // 2
                for w in words_line:
                    if word_counter < (original_spec.word_index or 0):
                        highlight_font = get_highlight_font(font_orig)
                        with (
                            profiler.time_block("draw.text.highlight") if profiler else nullcontext()
                        ):
                            draw.text((x_line, y_text), w, font=highlight_font, fill=accent_color)
                    else:
                        with profiler.time_block("draw.text") if profiler else nullcontext():
                            draw.text(
                                (x_line, y_text),
                                w,
                                font=font_orig,
                                fill=original_color,
                            )
                    w_width, _ = self._layout_engine.text_size(draw, font_orig, w)
                    x_line += w_width + space_width
                    word_counter += 1
                _, line_height = self._layout_engine.text_size(draw, font_orig, line)
                y_text += line_height + extra_line_spacing

        if translation_seg:
            y_text += separator_pre_margin
            with profiler.time_block("draw.line") if profiler else nullcontext():
                draw.line(
                    [(separator_margin, y_text), (slide_size[0] - separator_margin, y_text)],
                    fill=separator_color,
                    width=separator_thickness,
                )
            y_text += separator_thickness + segment_spacing

        rtl_languages = {"Arabic", "Hebrew", "Urdu", "Persian"}
        header_language = raw_header.split(" - ")[0] if raw_header else ""

        trans_char_range = translation_spec.char_range if highlight_granularity == "char" else None
        if trans_char_range is not None:
            y_text = render_char_range(
                text_value=translation_seg,
                lines_list=trans_lines,
                font_obj=font_trans,
                char_range=trans_char_range,
                color_value=translation_color,
                start_y=y_text,
            )
        elif header_language in rtl_languages:
            char_counter = 0
            for line in trans_lines:
                line_width = sum(self._layout_engine.text_size(draw, font_trans, ch)[0] for ch in line)
                x_line = (slide_size[0] - line_width) // 2
                for ch in line:
                    ch_width, _ = self._layout_engine.text_size(draw, font_trans, ch)
                    if char_counter < (translation_spec.word_index or 0):
                        highlight_font = get_highlight_font(font_trans)
                        with (
                            profiler.time_block("draw.text.highlight") if profiler else nullcontext()
                        ):
                            draw.text((x_line, y_text), ch, font=highlight_font, fill=accent_color)
                    else:
                        with profiler.time_block("draw.text") if profiler else nullcontext():
                            draw.text((x_line, y_text), ch, font=font_trans, fill=translation_color)
                    x_line += ch_width
                    char_counter += 1
                _, line_height = self._layout_engine.text_size(draw, font_trans, line)
                y_text += line_height + extra_line_spacing
        else:
            word_counter = 0
            for line in trans_lines:
                words_line = line.split()
                space_width, _ = self._layout_engine.text_size(draw, font_trans, " ")
                word_widths = [self._layout_engine.text_size(draw, font_trans, w)[0] for w in words_line]
                total_width = sum(word_widths) + space_width * (len(words_line) - 1 if words_line else 0)
                x_line = (slide_size[0] - total_width) // 2
                for w in words_line:
                    if word_counter < (translation_spec.word_index or 0):
                        highlight_font = get_highlight_font(font_trans)
                        with (
                            profiler.time_block("draw.text.highlight") if profiler else nullcontext()
                        ):
                            draw.text((x_line, y_text), w, font=highlight_font, fill=accent_color)
                    else:
                        with profiler.time_block("draw.text") if profiler else nullcontext():
                            draw.text((x_line, y_text), w, font=font_trans, fill=translation_color)
                    w_width, _ = self._layout_engine.text_size(draw, font_trans, w)
                    x_line += w_width + space_width
                    word_counter += 1
                _, line_height = self._layout_engine.text_size(draw, font_trans, line)
                y_text += line_height + extra_line_spacing

        if transliteration_seg:
            y_text += separator_pre_margin
            with profiler.time_block("draw.line") if profiler else nullcontext():
                draw.line(
                    [(separator_margin, y_text), (slide_size[0] - separator_margin, y_text)],
                    fill=separator_color,
                    width=separator_thickness,
                )
            y_text += separator_thickness + segment_spacing

        translit_char_range = (
            transliteration_spec.char_range if highlight_granularity == "char" else None
        )
        if translit_char_range is not None:
            y_text = render_char_range(
                text_value=transliteration_seg,
                lines_list=translit_lines,
                font_obj=font_translit,
                char_range=translit_char_range,
                color_value=transliteration_color,
                start_y=y_text,
            )
        else:
            word_counter = 0
            for line in translit_lines:
                words_line = line.split()
                space_width, _ = self._layout_engine.text_size(draw, font_translit, " ")
                word_widths = [self._layout_engine.text_size(draw, font_translit, w)[0] for w in words_line]
                total_width = sum(word_widths) + space_width * (len(words_line) - 1 if words_line else 0)
                x_line = (slide_size[0] - total_width) // 2
                for w in words_line:
                    if word_counter < (transliteration_spec.word_index or 0):
                        highlight_font = get_highlight_font(font_translit)
                        with (
                            profiler.time_block("draw.text.highlight") if profiler else nullcontext()
                        ):
                            draw.text((x_line, y_text), w, font=highlight_font, fill=accent_color)
                    else:
                        with profiler.time_block("draw.text") if profiler else nullcontext():
                            draw.text(
                                (x_line, y_text),
                                w,
                                font=font_translit,
                                fill=transliteration_color,
                            )
                    w_width, _ = self._layout_engine.text_size(draw, font_translit, w)
                    x_line += w_width + space_width
                    word_counter += 1
                _, line_height = self._layout_engine.text_size(draw, font_translit, line)
                y_text += line_height + extra_line_spacing

        return img

    # Video composition -------------------------------------------------
    def _render_slide_frame_local(
        self, task: SlideFrameTask, profiler: Optional[SlideRenderProfiler]
    ) -> str:
        cover_image = _deserialize_cover_image(task.cover_image_bytes)
        try:
            slide = Slide.from_sentence_block(
                task.block,
                template_name=task.template_name,
            )
            image = self.render_sentence_slide_image(
                slide,
                original_highlight_word_index=task.original_highlight_index,
                translation_highlight_word_index=task.translation_highlight_index,
                transliteration_highlight_word_index=task.transliteration_highlight_index,
                original_highlight_char_range=task.original_char_range,
                translation_highlight_char_range=task.translation_char_range,
                transliteration_highlight_char_range=task.transliteration_char_range,
                highlight_granularity=task.highlight_granularity,
                slide_size=task.slide_size,
                initial_font_size=task.initial_font_size,
                default_font_path=task.default_font_path,
                bg_color=task.bg_color,
                cover_img=cover_image,
                header_info=task.header_info,
                template_name=task.template_name,
                profiler=profiler,
            )
            image.save(task.output_path)
            image.close()
        finally:
            if cover_image is not None:
                cover_image.close()
        return task.output_path

    def _render_slide_frame(self, task: SlideFrameTask) -> str:
        return self._render_slide_frame_local(task, None)

    def build_sentence_video(
        self,
        slide: Slide,
        audio_seg: AudioSegment,
        sentence_index: int,
        *,
        sync_ratio: float,
        word_highlighting: bool,
        highlight_events: Optional[Sequence[HighlightEvent]] = None,
        highlight_granularity: str = "word",
        slide_size: Sequence[int] = (1280, 720),
        initial_font_size: int = 50,
        default_font_path: Optional[str] = None,
        bg_color: Sequence[int] = (0, 0, 0),
        cover_img: Optional[Image.Image] = None,
        header_info: str = "",
        render_options: Optional[SlideRenderOptions] = None,
    ) -> str:
        if default_font_path is None:
            default_font_path = self.get_default_font_path()

        options = render_options or SlideRenderOptions()
        parallelism = (options.parallelism or "off").lower()
        if parallelism not in {"off", "auto", "thread", "process", "none"}:
            parallelism = "off"
        if parallelism == "none":
            parallelism = "off"
        _log_simd_preference(options.prefer_pillow_simd)

        profiler: Optional[SlideRenderProfiler] = None
        if options.benchmark_rendering:
            if parallelism == "off":
                profiler = SlideRenderProfiler()
            else:
                logger.warning(
                    "Slide rendering benchmark requested but parallel backend '%s' is active; timing data will not be collected.",
                    parallelism,
                    extra={"event": "video.slide.benchmark.skipped"},
                )

        block = slide.metadata.get("raw_block", slide.title)
        raw_lines = block.split("\n")
        content = "\n".join(raw_lines[1:]).strip()
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        if len(lines) >= 3:
            original_seg = lines[0]
            translation_seg = lines[1]
            transliteration_seg = lines[2]
        elif len(lines) >= 2:
            original_seg = lines[0]
            translation_seg = " ".join(lines[1:])
            transliteration_seg = ""
        else:
            original_seg = translation_seg = content
            transliteration_seg = ""

        original_words = original_seg.split()
        num_original_words = len(original_words)

        header_line = raw_lines[0] if raw_lines else ""
        if "Chinese" in header_line or "Japanese" in header_line:
            translation_units: Sequence[str] = list(translation_seg)
        else:
            translation_units = translation_seg.split() or [translation_seg]
        num_translation_words = len(translation_units)

        transliteration_words = transliteration_seg.split()
        num_translit_words = len(transliteration_words)

        audio_duration = audio_seg.duration_seconds
        audio_metadata = _get_audio_metadata(audio_seg)

        if highlight_events is None:
            if not word_highlighting:
                events: Sequence[HighlightEvent] = [
                    HighlightEvent(
                        duration=max(audio_duration * sync_ratio, 0.0),
                        original_index=num_original_words,
                        translation_index=num_translation_words,
                        transliteration_index=num_translit_words,
                    )
                ]
            else:
                generated: List[HighlightEvent] = []
                if audio_metadata and audio_metadata.parts:
                    generated = _build_events_from_metadata(
                        audio_metadata,
                        sync_ratio,
                        num_original_words,
                        num_translation_words,
                        num_translit_words,
                    )
                if not generated:
                    generated = _build_legacy_highlight_events(
                        audio_duration,
                        sync_ratio,
                        original_words,
                        translation_units,
                        transliteration_words,
                    )
                events = generated
        else:
            events = list(highlight_events)

        timeline_events = [event for event in events if event.duration > 0]
        if not timeline_events:
            timeline_events = [
                HighlightEvent(
                    duration=max(audio_duration * sync_ratio, 0.0),
                    original_index=num_original_words,
                    translation_index=num_translation_words,
                    transliteration_index=num_translit_words,
                )
            ]

        has_char_steps = any(
            event.step is not None
            and event.step.char_index_start is not None
            and event.step.char_index_end is not None
            for event in timeline_events
        )
        effective_granularity = (
            "char"
            if word_highlighting and highlight_granularity == "char" and has_char_steps
            else "word"
        )

        segments = coalesce_highlight_events(timeline_events)
        video_duration = sum(segment.duration for segment in segments)
        pad_duration = max(0.0, audio_duration - video_duration)

        tmp_dir = active_tmp_dir()
        os.makedirs(tmp_dir, exist_ok=True)
        slide_size_tuple = tuple(int(value) for value in slide_size)
        if bg_color is None:
            bg_color_tuple: Tuple[int, ...] = ()
        else:
            bg_values = [int(value) for value in bg_color]
            if len(bg_values) < 3:
                bg_values.extend([0] * (3 - len(bg_values)))
            bg_color_tuple = tuple(bg_values[:3])
        cover_bytes = _serialize_cover_image(cover_img)

        frame_tasks: List[SlideFrameTask] = []
        for idx, segment in enumerate(segments):
            original_highlight_index = (
                min(segment.original_index, num_original_words)
                if word_highlighting
                else num_original_words
            )
            translation_highlight_index = (
                min(segment.translation_index, num_translation_words)
                if word_highlighting
                else num_translation_words
            )
            transliteration_highlight_index = (
                min(segment.transliteration_index, num_translit_words)
                if word_highlighting
                else num_translit_words
            )
            original_char_range = (
                segment.original_char_range if effective_granularity == "char" else None
            )
            translation_char_range = (
                segment.translation_char_range if effective_granularity == "char" else None
            )
            transliteration_char_range = (
                segment.transliteration_char_range if effective_granularity == "char" else None
            )
            img_path = os.path.join(tmp_dir, f"word_slide_{sentence_index}_{idx}.png")
            frame_tasks.append(
                SlideFrameTask(
                    index=idx,
                    block=block,
                    duration=segment.duration,
                    original_highlight_index=original_highlight_index,
                    translation_highlight_index=translation_highlight_index,
                    transliteration_highlight_index=transliteration_highlight_index,
                    original_char_range=original_char_range,
                    translation_char_range=translation_char_range,
                    transliteration_char_range=transliteration_char_range,
                    slide_size=slide_size_tuple,
                    initial_font_size=initial_font_size,
                    default_font_path=default_font_path,
                    bg_color=bg_color_tuple,
                    cover_image_bytes=cover_bytes,
                    header_info=header_info,
                    highlight_granularity=effective_granularity,
                    output_path=img_path,
                    template_name=slide.template_name,
                )
            )

        render_backend = parallelism
        if len(frame_tasks) <= 1:
            render_backend = "off"
        elif render_backend == "auto":
            worker_hint = options.workers or (os.cpu_count() or 1)
            render_backend = "process" if worker_hint and worker_hint > 1 else "thread"

        self._render_frames(
            frame_tasks,
            parallelism=render_backend,
            options=options,
            profiler=profiler,
        )

        word_video_files: List[str] = []
        for task in frame_tasks:
            video_path = os.path.join(tmp_dir, f"word_slide_{sentence_index}_{task.index}.mp4")
            cmd = [
                "ffmpeg",
                "-loglevel",
                "quiet",
                "-y",
                "-loop",
                "1",
                "-i",
                task.output_path,
                "-i",
                silence_audio_path(),
                "-c:v",
                "libx264",
                "-t",
                f"{task.duration:.2f}",
                "-pix_fmt",
                "yuv420p",
                "-vf",
                "format=yuv420p",
                "-an",
                video_path,
            ]
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as exc:
                logger.error("FFmpeg error on word slide %s_%s: %s", sentence_index, task.index, exc)
            finally:
                if os.path.exists(task.output_path):
                    os.remove(task.output_path)
            word_video_files.append(video_path)

        concat_list_path = os.path.join(tmp_dir, f"concat_word_{sentence_index}.txt")
        with open(concat_list_path, "w", encoding="utf-8") as handle:
            for video_file in word_video_files:
                handle.write(f"file '{video_file}'\n")

        sentence_video_path = os.path.join(tmp_dir, f"sentence_slide_{sentence_index}.mp4")
        cmd_concat = [
            "ffmpeg",
            "-loglevel",
            "quiet",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_path,
            "-c",
            "copy",
            sentence_video_path,
        ]
        try:
            result = subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logger.error("FFmpeg concat error: %s", result.stderr.decode())
                raise subprocess.CalledProcessError(result.returncode, cmd_concat)
        except subprocess.CalledProcessError as exc:
            logger.error("Error concatenating word slides for sentence %s: %s", sentence_index, exc)
        finally:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)

        for vf in word_video_files:
            if os.path.exists(vf):
                os.remove(vf)

        audio_temp_path = os.path.join(tmp_dir, f"sentence_audio_{sentence_index}.wav")
        audio_seg.export(audio_temp_path, format="wav")
        merged_video_path = os.path.join(tmp_dir, f"sentence_slide_{sentence_index}_merged.mp4")

        cmd_merge = [
            "ffmpeg",
            "-loglevel",
            "quiet",
            "-y",
            "-i",
            sentence_video_path,
            "-i",
            audio_temp_path,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            merged_video_path,
        ]
        try:
            subprocess.run(cmd_merge, check=True)
        except subprocess.CalledProcessError as exc:
            logger.error("FFmpeg error merging audio for sentence %s: %s", sentence_index, exc)
        finally:
            if os.path.exists(audio_temp_path):
                os.remove(audio_temp_path)
            if os.path.exists(sentence_video_path):
                os.remove(sentence_video_path)

        final_video_path = os.path.join(tmp_dir, f"sentence_slide_{sentence_index}_final.mp4")
        if pad_duration > 0:
            cmd_tpad = [
                "ffmpeg",
                "-loglevel",
                "quiet",
                "-y",
                "-i",
                merged_video_path,
                "-vf",
                f"tpad=stop_mode=clone:stop_duration={pad_duration:.2f}",
                "-af",
                f"apad=pad_dur={pad_duration:.2f}",
                final_video_path,
            ]
            try:
                subprocess.run(cmd_tpad, check=True)
            except subprocess.CalledProcessError as exc:
                logger.error("FFmpeg error applying padding for sentence %s: %s", sentence_index, exc)
            finally:
                if os.path.exists(merged_video_path):
                    os.remove(merged_video_path)
        else:
            final_video_path = merged_video_path

        if profiler is not None:
            profiler.log_summary(sentence_index)

        return final_video_path

    # Support utilities -------------------------------------------------
    def _render_frames(
        self,
        frame_tasks: Sequence[SlideFrameTask],
        *,
        parallelism: str,
        options: SlideRenderOptions,
        profiler: Optional[SlideRenderProfiler],
    ) -> None:
        if not frame_tasks:
            return

        if parallelism == "off" or len(frame_tasks) == 1:
            for task in frame_tasks:
                self._render_slide_frame_local(task, profiler)
            return

        workers = options.workers
        if workers is None or workers < 1:
            workers = os.cpu_count() or 1

        executor_cls = ThreadPoolExecutor if parallelism == "thread" else ProcessPoolExecutor
        init_kwargs = {"max_workers": workers}

        with executor_cls(**init_kwargs) as executor:
            futures = {
                executor.submit(self._render_slide_frame, task): task.index
                for task in frame_tasks
            }
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error(
                        "Slide rendering worker failed for sentence frame %s: %s",
                        futures[future],
                        exc,
                    )

    def get_default_font_path(self) -> str:
        if sys.platform == "darwin":
            for path in [
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            ]:
                if os.path.exists(path):
                    return path
        elif sys.platform == "win32":
            path = r"C:\\Windows\\Fonts\\arialuni.ttf"
            if os.path.exists(path):
                return path
        else:
            for path in [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            ]:
                if os.path.exists(path):
                    return path
        return "Arial.ttf"

    def _build_highlight_events(
        self,
        slide: Slide,
        audio_seg: AudioSegment,
        *,
        sync_ratio: float,
        word_highlighting: bool,
    ) -> Sequence[HighlightSegment]:
        block = slide.metadata.get("raw_block", slide.title)
        metadata = _get_audio_metadata(audio_seg)
        if metadata:
            events = _build_events_from_metadata(
                metadata,
                sync_ratio=sync_ratio,
                word_highlighting=word_highlighting,
            )
        else:
            events = _build_legacy_highlight_events(
                block,
                audio_seg.duration_seconds,
                sync_ratio=sync_ratio,
                word_highlighting=word_highlighting,
            )
        return coalesce_highlight_events(events)


__all__ = [
    "SlideRenderer",
    "SlideRenderOptions",
    "SlideRenderProfiler",
]
