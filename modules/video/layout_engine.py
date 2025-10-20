"""Layout utilities powering sentence slide rendering."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from PIL import ImageDraw, ImageFont

from .template_manager import _parse_color


@dataclass(slots=True)
class LineLayout:
    text: str
    x: float
    y: float
    height: float
    width: float
    char_boxes: Sequence[Tuple[int, Tuple[float, float, float, float]]]


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
    ) -> Tuple[float, float, float, float]:
        key = (self._font_key(font), text)
        with self._lock:
            cached = self._bbox_cache.get(key)
        if cached is not None:
            return cached
        bbox = draw_ctx.textbbox((0, 0), text, font=font)
        with self._lock:
            self._bbox_cache[key] = bbox
        return bbox

    def textlength(
        self,
        draw_ctx: ImageDraw.ImageDraw,
        font: ImageFont.FreeTypeFont,
        text: str,
    ) -> float:
        key = (self._font_key(font), text)
        with self._lock:
            cached = self._length_cache.get(key)
        if cached is not None:
            return cached
        length = draw_ctx.textlength(text, font=font)
        with self._lock:
            self._length_cache[key] = length
        return length


class LayoutEngine:
    """High level operations that map textual content to on-screen positions."""

    def __init__(self, cache: Optional[GlyphMetricsCache] = None) -> None:
        self._cache = cache or GlyphMetricsCache()

    def text_size(
        self,
        draw_ctx: ImageDraw.ImageDraw,
        font: ImageFont.ImageFont,
        text: str,
    ) -> Tuple[float, float]:
        bbox = self._cache.textbbox(draw_ctx, font, text)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def prepare_line_layout(
        self,
        *,
        text: str,
        lines: Sequence[str],
        font: ImageFont.ImageFont,
        draw_ctx: ImageDraw.ImageDraw,
        slide_width: int,
        start_y: float,
        line_spacing: float,
    ) -> Tuple[Sequence[LineLayout], Dict[int, Tuple[float, float, float, float]], float]:
        layouts: list[LineLayout] = []
        char_map: Dict[int, Tuple[float, float, float, float]] = {}
        source_index = 0
        y_cursor = start_y

        for line in lines:
            bbox = self._cache.textbbox(draw_ctx, font, line)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]
            x_line = (slide_width - line_width) // 2
            char_boxes: list[Tuple[int, Tuple[float, float, float, float]]] = []

            for pos, ch in enumerate(line):
                if source_index >= len(text):
                    break
                while source_index < len(text) and text[source_index] != ch:
                    source_index += 1
                if source_index >= len(text):
                    break
                prefix = line[:pos]
                next_prefix = line[: pos + 1]
                prev_width = (
                    self._cache.textlength(draw_ctx, font, prefix) if prefix else 0.0
                )
                curr_width = self._cache.textlength(draw_ctx, font, next_prefix)
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
                    char_boxes=tuple(char_boxes),
                )
            )
            y_cursor += line_height + line_spacing

        return layouts, char_map, y_cursor

    def fill_char_range(
        self,
        draw_ctx: ImageDraw.ImageDraw,
        char_map: Mapping[int, Tuple[float, float, float, float]],
        char_range: Optional[Tuple[int, int]],
        color: Sequence[int],
    ) -> None:
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
            draw_ctx.rectangle(bbox, fill=tuple(int(v) for v in color[:3]))

    @staticmethod
    def color_from_template(value: Any, *, default: tuple[int, int, int]) -> tuple[int, int, int]:
        return _parse_color(value, default=default)


__all__ = ["GlyphMetricsCache", "LayoutEngine", "LineLayout"]
