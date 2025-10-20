"""Sentence slide composition and video helpers.

This module centralises the logic for rendering sentence slides and composing
per-sentence videos.  It relies on Pillow (``PIL``) for text rendering with
TrueType fonts and assumes an ``ffmpeg`` executable is available on the system
``PATH`` for video muxing.  Callers should ensure the expected fonts are
installed (see :func:`get_default_font_path`) and that ``ffmpeg`` can be
invoked.
"""

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
    HighlightSegment,
    _build_events_from_metadata,
    _build_legacy_highlight_events,
    _get_audio_metadata,
    coalesce_highlight_events,
)
from modules.audio.tts import active_tmp_dir, silence_audio_path

logger = log_mgr.logger


__all__ = [
    "build_sentence_video",
    "generate_sentence_slide_image",
    "get_default_font_path",
    "SlideRenderOptions",
    "SlideRenderProfiler",
]


@dataclass(slots=True)
class LineLayout:
    text: str
    x: float
    y: float
    height: float
    width: float
    char_boxes: List[Tuple[int, Tuple[float, float, float, float]]]


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


class GlyphMetricsCache:
    """Caches glyph measurement metadata keyed by font and text."""

    def __init__(self) -> None:
        self._bbox_cache: Dict[Tuple[Tuple[object, ...], str], Tuple[float, float, float, float]] = {}
        self._length_cache: Dict[Tuple[Tuple[object, ...], str], float] = {}
        self._lock = threading.Lock()

    def _font_key(self, font: ImageFont.ImageFont) -> Tuple[object, ...]:
        path = getattr(font, "path", None)
        size = getattr(font, "size", None)
        layout = getattr(font, "layout_engine", None)
        index = getattr(font, "index", None)
        if path:
            return (path, size, layout, index)
        name = getattr(font, "getname", None)
        if callable(name):
            family = tuple(name())
        else:
            family = ()
        return (id(font), family, size, layout, index)

    def textbbox(
        self,
        draw_ctx: ImageDraw.ImageDraw,
        font: ImageFont.FreeTypeFont,
        text: str,
        profiler: Optional[SlideRenderProfiler] = None,
    ) -> Tuple[float, float, float, float]:
        key = (self._font_key(font), text)
        with self._lock:
            cached = self._bbox_cache.get(key)
        if cached is not None:
            if profiler:
                profiler.increment("glyph_bbox_cache_hits")
            return cached
        if profiler:
            profiler.increment("glyph_bbox_cache_misses")
        with (profiler.time_block("textbbox") if profiler else nullcontext()):
            bbox = draw_ctx.textbbox((0, 0), text, font=font)
        with self._lock:
            self._bbox_cache[key] = bbox
        return bbox

    def textlength(
        self,
        draw_ctx: ImageDraw.ImageDraw,
        font: ImageFont.FreeTypeFont,
        text: str,
        profiler: Optional[SlideRenderProfiler] = None,
    ) -> float:
        key = (self._font_key(font), text)
        with self._lock:
            cached = self._length_cache.get(key)
        if cached is not None:
            if profiler:
                profiler.increment("glyph_length_cache_hits")
            return cached
        if profiler:
            profiler.increment("glyph_length_cache_misses")
        with (profiler.time_block("textlength") if profiler else nullcontext()):
            length = draw_ctx.textlength(text, font=font)
        with self._lock:
            self._length_cache[key] = length
        return length


@dataclass(slots=True)
class SlideFrameTask:
    """Describes a single frame that needs to be rendered for a sentence."""

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


_GLYPH_CACHE = GlyphMetricsCache()


def _render_slide_frame_local(
    task: SlideFrameTask, profiler: Optional[SlideRenderProfiler]
) -> str:
    cover_image = _deserialize_cover_image(task.cover_image_bytes)
    try:
        image = generate_sentence_slide_image(
            task.block,
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
            profiler=profiler,
        )
        image.save(task.output_path)
        image.close()
    finally:
        if cover_image is not None:
            cover_image.close()
    return task.output_path


def _render_slide_frame(task: SlideFrameTask) -> str:
    return _render_slide_frame_local(task, None)


def _text_bbox(
    draw_ctx: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    text: str,
    profiler: Optional[SlideRenderProfiler] = None,
) -> Tuple[float, float, float, float]:
    return _GLYPH_CACHE.textbbox(draw_ctx, font, text, profiler)


def _text_length(
    draw_ctx: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    text: str,
    profiler: Optional[SlideRenderProfiler] = None,
) -> float:
    return _GLYPH_CACHE.textlength(draw_ctx, font, text, profiler)


def _text_size(
    draw_ctx: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    text: str,
    profiler: Optional[SlideRenderProfiler] = None,
) -> Tuple[float, float]:
    bbox = _text_bbox(draw_ctx, font, text, profiler)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


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


def _prepare_line_layout(
    *,
    text: str,
    lines: Sequence[str],
    font: ImageFont.ImageFont,
    draw_ctx: ImageDraw.ImageDraw,
    slide_width: int,
    start_y: float,
    line_spacing: float,
    profiler: Optional[SlideRenderProfiler] = None,
) -> Tuple[List[LineLayout], Dict[int, Tuple[float, float, float, float]], float]:
    """Compute positioning metadata for rendering ``lines`` of ``text``."""

    layouts: List[LineLayout] = []
    char_map: Dict[int, Tuple[float, float, float, float]] = {}
    source_index = 0
    y_cursor = start_y

    for line in lines:
        bbox = _text_bbox(draw_ctx, font, line, profiler)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        x_line = (slide_width - line_width) // 2
        char_boxes: List[Tuple[int, Tuple[float, float, float, float]]] = []

        for pos, ch in enumerate(line):
            if source_index >= len(text):
                break
            while source_index < len(text) and text[source_index] != ch:
                source_index += 1
            if source_index >= len(text):
                break
            prefix = line[:pos]
            next_prefix = line[: pos + 1]
            prev_width = _text_length(draw_ctx, font, prefix, profiler) if prefix else 0.0
            curr_width = _text_length(draw_ctx, font, next_prefix, profiler)
            bbox_char = (
                x_line + prev_width,
                y_cursor,
                x_line + curr_width,
                y_cursor + line_height,
            )
            char_boxes.append((source_index, bbox_char))
            char_map[source_index] = bbox_char
            source_index += 1

        layouts.append(
            LineLayout(
                text=line,
                x=x_line,
                y=y_cursor,
                height=line_height,
                width=line_width,
                char_boxes=char_boxes,
            )
        )
        y_cursor += line_height + line_spacing

    return layouts, char_map, y_cursor


def _fill_char_range(
    draw_ctx: ImageDraw.ImageDraw,
    char_map: Mapping[int, Tuple[float, float, float, float]],
    char_range: Optional[Tuple[int, int]],
    color: Sequence[int],
) -> None:
    """Render a filled rectangle for each character within ``char_range``."""

    if not char_range:
        return
    start, end = char_range
    if start is None or end is None:
        return
    start_idx = max(int(start), 0)
    end_idx = max(int(end), start_idx)
    for idx in range(start_idx, end_idx):
        bbox = char_map.get(idx)
        if bbox is None:
            continue
        draw_ctx.rectangle(bbox, fill=color)


def get_default_font_path() -> str:
    """Return a platform-appropriate fallback font path for slide rendering."""

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


def generate_sentence_slide_image(
    block: str,
    original_highlight_word_index: Optional[int] = None,
    translation_highlight_word_index: Optional[int] = None,
    transliteration_highlight_word_index: Optional[int] = None,
    *,
    original_highlight_char_range: Optional[Tuple[int, int]] = None,
    translation_highlight_char_range: Optional[Tuple[int, int]] = None,
    transliteration_highlight_char_range: Optional[Tuple[int, int]] = None,
    highlight_granularity: str = "word",
    slide_size: Sequence[int] = (1280, 720),
    initial_font_size: int = 50,
    default_font_path: str = "Arial.ttf",
    bg_color: Sequence[int] = (0, 0, 0),
    cover_img: Optional[Image.Image] = None,
    header_info: str = "",
    profiler: Optional[SlideRenderProfiler] = None,
) -> Image.Image:
    """Draw a slide image for a sentence block with optional highlighting."""

    img = Image.new("RGB", slide_size, bg_color)
    draw = ImageDraw.Draw(img)

    header_height = 150
    left_area_width = header_height

    raw_lines = block.split("\n")
    header_line = raw_lines[0] if raw_lines else ""
    header_text = header_info if header_info else header_line

    with profiler.time_block("draw.rectangle") if profiler else nullcontext():
        draw.rectangle([0, 0, slide_size[0], header_height], fill=bg_color)

    if cover_img:
        cover_thumb = cover_img.copy()
        new_width = left_area_width - 20
        new_height = header_height - 20
        cover_thumb.thumbnail((new_width, new_height))
        img.paste(cover_thumb, (10, (header_height - cover_thumb.height) // 2))

    try:
        header_font = ImageFont.truetype(default_font_path, 24)
    except IOError:
        header_font = ImageFont.load_default()

    header_lines = header_text.split("\n")
    header_line_spacing = 4
    max_header_width = 0
    total_header_height = 0
    for line in header_lines:
        line_width, line_height = _text_size(draw, header_font, line, profiler)
        max_header_width = max(max_header_width, line_width)
        total_header_height += line_height
    total_header_height += header_line_spacing * (len(header_lines) - 1)
    if cover_img:
        available_width = slide_size[0] - left_area_width
        header_x = left_area_width + (available_width - max_header_width) // 2
    else:
        header_x = (slide_size[0] - max_header_width) // 2
    header_y = (header_height - total_header_height) // 2

    with (profiler.time_block("draw.multiline_text") if profiler else nullcontext()):
        draw.multiline_text(
            (header_x, header_y),
            header_text,
            font=header_font,
            fill=(255, 255, 255),
            spacing=header_line_spacing,
            align="center",
        )

    extra_line_spacing = 10
    segment_spacing = 20
    separator_pre_margin = 10

    separator_color = (150, 150, 150)
    separator_thickness = 2
    separator_margin = 40

    content = "\n".join(raw_lines[1:]).strip()
    content_lines = [line.strip() for line in content.split("\n") if line.strip()]
    if len(content_lines) >= 3:
        original_seg = content_lines[0]
        translation_seg = content_lines[1]
        transliteration_seg = content_lines[2]
    elif len(content_lines) >= 2:
        original_seg = content_lines[0]
        translation_seg = " ".join(content_lines[1:])
        transliteration_seg = ""
    else:
        original_seg = translation_seg = content
        transliteration_seg = ""

    def wrap_text_local(
        text: str,
        draw_ctx: ImageDraw.ImageDraw,
        font: ImageFont.ImageFont,
        max_width: int,
        metrics_profiler: Optional[SlideRenderProfiler],
    ) -> str:
        if " " not in text:
            lines_: List[str] = []
            current_line = ""
            for ch in text:
                test_line = current_line + ch
                width, _ = _text_size(draw_ctx, font, test_line, metrics_profiler)
                if width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines_.append(current_line)
                    current_line = ch
            if current_line:
                lines_.append(current_line)
            return "\n".join(lines_)
        words = text.split()
        if not words:
            return ""
        lines_: List[str] = []
        current_line = words[0]
        for word in words[1:]:
            test_line = current_line + " " + word
            width, _ = _text_size(draw_ctx, font, test_line, metrics_profiler)
            if width <= max_width:
                current_line = test_line
            else:
                lines_.append(current_line)
                current_line = word
        lines_.append(current_line)
        return "\n".join(lines_)

    def get_wrapped_text_and_font(text: str) -> tuple[str, ImageFont.ImageFont]:
        max_width = slide_size[0] * 0.9
        max_height = slide_size[1] * 0.9
        font_size = int(initial_font_size * 0.85)
        chosen_font: Optional[ImageFont.ImageFont] = None
        wrapped_text = text
        while font_size > 10:
            try:
                test_font = ImageFont.truetype(default_font_path, font_size)
            except IOError:
                test_font = ImageFont.load_default()
            candidate_wrapped = wrap_text_local(
                text, draw, test_font, int(max_width), profiler
            )
            total_height = 0
            lines = candidate_wrapped.split("\n")
            for i, line in enumerate(lines):
                _, height = _text_size(draw, test_font, line, profiler)
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

    def compute_height(lines: Iterable[str], font: ImageFont.ImageFont) -> int:
        total = 0
        lines_list = list(lines)
        for i, line in enumerate(lines_list):
            _, height = _text_size(draw, font, line, profiler)
            total += height
            if i < len(lines_list) - 1:
                total += extra_line_spacing
        return total

    def get_highlight_font(base_font: ImageFont.ImageFont) -> ImageFont.ImageFont:
        base_size = getattr(base_font, "size", initial_font_size)
        target_size = max(int(base_size * scale_factor), 1)
        try:
            return ImageFont.truetype(default_font_path, target_size)
        except IOError:
            return base_font

    wrapped_orig, font_orig = get_wrapped_text_and_font(original_seg)
    orig_lines = wrapped_orig.split("\n")
    orig_height = compute_height(orig_lines, font_orig)

    wrapped_trans, font_trans = get_wrapped_text_and_font(translation_seg)
    trans_lines = wrapped_trans.split("\n")
    trans_height = compute_height(trans_lines, font_trans)

    translit_lines: List[str] = []
    translit_height = 0
    if transliteration_seg:
        wrapped_translit, font_translit = get_wrapped_text_and_font(transliteration_seg)
        translit_lines = wrapped_translit.split("\n")
        translit_height = compute_height(translit_lines, font_translit)
    else:
        font_translit = font_trans

    segments_heights = [orig_height, trans_height]
    if transliteration_seg:
        segments_heights.append(translit_height)
    num_segments = len(segments_heights)
    num_separators = num_segments - 1
    total_text_height_active = (
        sum(segments_heights)
        + segment_spacing * num_separators
        + separator_thickness * num_separators
    )

    available_area = slide_size[1] - header_height
    y_text = header_height + (available_area - total_text_height_active) // 2

    original_sentence_color = (255, 255, 0)
    translation_color = (153, 255, 153)
    transliteration_color = (255, 255, 0)
    highlight_color = (255, 165, 0)
    scale_factor = 1.05

    def _normalize_char_range(value: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
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

    use_char_highlight = highlight_granularity == "char"
    orig_char_range = _normalize_char_range(original_highlight_char_range) if use_char_highlight else None
    trans_char_range = (
        _normalize_char_range(translation_highlight_char_range)
        if use_char_highlight
        else None
    )
    translit_char_range = (
        _normalize_char_range(transliteration_highlight_char_range)
        if use_char_highlight
        else None
    )

    orig_index_limit = original_highlight_word_index or 0
    if orig_char_range is not None:
        layouts, char_map, y_text = _prepare_line_layout(
            text=original_seg,
            lines=orig_lines,
            font=font_orig,
            draw_ctx=draw,
            slide_width=slide_size[0],
            start_y=y_text,
            line_spacing=extra_line_spacing,
            profiler=profiler,
        )
        _fill_char_range(draw, char_map, orig_char_range, highlight_color)
        for layout in layouts:
            with profiler.time_block("draw.text") if profiler else nullcontext():
                draw.text(
                    (layout.x, layout.y),
                    layout.text,
                    font=font_orig,
                    fill=original_sentence_color,
                )
    else:
        word_counter = 0
        for line in orig_lines:
            words_line = line.split()
            space_width, _ = _text_size(draw, font_orig, " ", profiler)
            word_widths = [_text_size(draw, font_orig, w, profiler)[0] for w in words_line]
            total_width = sum(word_widths) + space_width * (len(words_line) - 1 if words_line else 0)
            x_line = (slide_size[0] - total_width) // 2
            for w in words_line:
                if word_counter < orig_index_limit:
                    highlight_font = get_highlight_font(font_orig)
                    with (
                        profiler.time_block("draw.text.highlight") if profiler else nullcontext()
                    ):
                        draw.text((x_line, y_text), w, font=highlight_font, fill=highlight_color)
                else:
                    with profiler.time_block("draw.text") if profiler else nullcontext():
                        draw.text(
                            (x_line, y_text),
                            w,
                            font=font_orig,
                            fill=original_sentence_color,
                        )
                w_width, _ = _text_size(draw, font_orig, w, profiler)
                x_line += w_width + space_width
                word_counter += 1
            _, line_height = _text_size(draw, font_orig, line, profiler)
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
    header_language = header_text.split(" - ")[0] if header_text else ""

    trans_index_limit = translation_highlight_word_index or 0
    if trans_char_range is not None:
        layouts, char_map, y_text = _prepare_line_layout(
            text=translation_seg,
            lines=trans_lines,
            font=font_trans,
            draw_ctx=draw,
            slide_width=slide_size[0],
            start_y=y_text,
            line_spacing=extra_line_spacing,
            profiler=profiler,
        )
        _fill_char_range(draw, char_map, trans_char_range, highlight_color)
        for layout in layouts:
            with profiler.time_block("draw.text") if profiler else nullcontext():
                draw.text(
                    (layout.x, layout.y),
                    layout.text,
                    font=font_trans,
                    fill=translation_color,
                )
    elif header_language in rtl_languages:
        char_counter = 0
        for line in trans_lines:
            line_width = sum(_text_size(draw, font_trans, ch, profiler)[0] for ch in line)
            x_line = (slide_size[0] - line_width) // 2
            for ch in line:
                ch_width, _ = _text_size(draw, font_trans, ch, profiler)
                if char_counter < trans_index_limit:
                    highlight_font = get_highlight_font(font_trans)
                    with (
                        profiler.time_block("draw.text.highlight") if profiler else nullcontext()
                    ):
                        draw.text((x_line, y_text), ch, font=highlight_font, fill=highlight_color)
                else:
                    with profiler.time_block("draw.text") if profiler else nullcontext():
                        draw.text((x_line, y_text), ch, font=font_trans, fill=translation_color)
                x_line += ch_width
                char_counter += 1
            _, line_height = _text_size(draw, font_trans, line, profiler)
            y_text += line_height + extra_line_spacing
    else:
        word_counter = 0
        for line in trans_lines:
            words_line = line.split()
            space_width, _ = _text_size(draw, font_trans, " ", profiler)
            word_widths = [_text_size(draw, font_trans, w, profiler)[0] for w in words_line]
            total_width = sum(word_widths) + space_width * (len(words_line) - 1 if words_line else 0)
            x_line = (slide_size[0] - total_width) // 2
            for w in words_line:
                if word_counter < trans_index_limit:
                    highlight_font = get_highlight_font(font_trans)
                    with (
                        profiler.time_block("draw.text.highlight") if profiler else nullcontext()
                    ):
                        draw.text((x_line, y_text), w, font=highlight_font, fill=highlight_color)
                else:
                    with profiler.time_block("draw.text") if profiler else nullcontext():
                        draw.text((x_line, y_text), w, font=font_trans, fill=translation_color)
                w_width, _ = _text_size(draw, font_trans, w, profiler)
                x_line += w_width + space_width
                word_counter += 1
            _, line_height = _text_size(draw, font_trans, line, profiler)
            y_text += line_height + extra_line_spacing

    if transliteration_seg:
        y_text += separator_pre_margin
        draw.line(
            [(separator_margin, y_text), (slide_size[0] - separator_margin, y_text)],
            fill=separator_color,
            width=separator_thickness,
        )
        y_text += separator_thickness + segment_spacing

    translit_index_limit = transliteration_highlight_word_index or 0
    if translit_char_range is not None:
        layouts, char_map, y_text = _prepare_line_layout(
            text=transliteration_seg,
            lines=translit_lines,
            font=font_translit,
            draw_ctx=draw,
            slide_width=slide_size[0],
            start_y=y_text,
            line_spacing=extra_line_spacing,
            profiler=profiler,
        )
        _fill_char_range(draw, char_map, translit_char_range, highlight_color)
        for layout in layouts:
            with profiler.time_block("draw.text") if profiler else nullcontext():
                draw.text(
                    (layout.x, layout.y),
                    layout.text,
                    font=font_translit,
                    fill=transliteration_color,
                )
    else:
        word_counter = 0
        for line in translit_lines:
            words_line = line.split()
            space_width, _ = _text_size(draw, font_translit, " ", profiler)
            word_widths = [
                _text_size(draw, font_translit, w, profiler)[0] for w in words_line
            ]
            total_width = sum(word_widths) + space_width * (len(words_line) - 1 if words_line else 0)
            x_line = (slide_size[0] - total_width) // 2
            for w in words_line:
                if word_counter < translit_index_limit:
                    highlight_font = get_highlight_font(font_translit)
                    with (
                        profiler.time_block("draw.text.highlight") if profiler else nullcontext()
                    ):
                        draw.text((x_line, y_text), w, font=highlight_font, fill=highlight_color)
                else:
                    with profiler.time_block("draw.text") if profiler else nullcontext():
                        draw.text(
                            (x_line, y_text),
                            w,
                            font=font_translit,
                            fill=transliteration_color,
                        )
                w_width, _ = _text_size(draw, font_translit, w, profiler)
                x_line += w_width + space_width
                word_counter += 1
            _, line_height = _text_size(draw, font_translit, line, profiler)
            y_text += line_height + extra_line_spacing

    return img


def build_sentence_video(
    block: str,
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
    """Generate a word-synchronised video for a single sentence."""

    if default_font_path is None:
        default_font_path = get_default_font_path()

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
    metadata = _get_audio_metadata(audio_seg)

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
            if metadata and metadata.parts:
                generated = _build_events_from_metadata(
                    metadata,
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

    word_video_files: List[str] = []
    tmp_dir = active_tmp_dir()

    slide_size_tuple = tuple(int(value) for value in slide_size)
    bg_color_tuple = tuple(int(value) for value in bg_color)
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
            )
        )

    render_backend = parallelism
    if len(frame_tasks) <= 1:
        render_backend = "off"
    elif render_backend == "auto":
        worker_hint = options.workers or (os.cpu_count() or 1)
        render_backend = "process" if worker_hint and worker_hint > 1 else "thread"

    if render_backend == "off":
        for task in frame_tasks:
            _render_slide_frame_local(task, profiler)
        if profiler is not None:
            profiler.log_summary(sentence_index)
    else:
        if options.workers is None:
            worker_total = max(1, os.cpu_count() or 1)
        else:
            worker_total = max(1, options.workers)
        executor_cls = ProcessPoolExecutor if render_backend == "process" else ThreadPoolExecutor
        with executor_cls(max_workers=worker_total) as executor:
            futures = {executor.submit(_render_slide_frame, task): task.index for task in frame_tasks}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error(
                        "Slide rendering worker failed for sentence %s frame %s: %s",
                        sentence_index,
                        futures[future],
                        exc,
                    )

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
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for video_file in word_video_files:
            f.write(f"file '{video_file}'\n")

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
            logger.error("FFmpeg error adding pad for sentence %s: %s", sentence_index, exc)
        finally:
            if os.path.exists(merged_video_path):
                os.remove(merged_video_path)
    else:
        os.rename(merged_video_path, final_video_path)

    return final_video_path
