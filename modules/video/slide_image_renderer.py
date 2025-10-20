"""Rendering utilities for generating slide images."""

from __future__ import annotations

from contextlib import nullcontext
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from .layout_engine import GlyphMetricsCache, LayoutEngine
from .slide_core import HighlightSpec, Slide
from .template_manager import TemplateDefinition, TemplateManager, _parse_color


_GLYPH_CACHE = GlyphMetricsCache()


class SlideImageRenderer:
    """Create slide images using the configured template and layout engine."""

    def __init__(
        self,
        *,
        template_manager: Optional[TemplateManager] = None,
        layout_engine: Optional[LayoutEngine] = None,
    ) -> None:
        self._template_manager = template_manager or TemplateManager()
        self._layout_engine = layout_engine or LayoutEngine(_GLYPH_CACHE)

    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
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
        profiler: Optional["SlideRenderProfiler"] = None,
    ) -> Image.Image:
        _, resolved = self._resolve_template(slide, template_name)
        layout_cfg = resolved.get("layout") if isinstance(resolved.get("layout"), Mapping) else {}
        blocks_cfg = layout_cfg.get("blocks") if isinstance(layout_cfg, Mapping) else {}
        header_cfg = blocks_cfg.get("header") if isinstance(blocks_cfg, Mapping) else {}
        body_cfg = blocks_cfg.get("body") if isinstance(blocks_cfg, Mapping) else {}

        header_height = (
            int(header_cfg.get("height", 150)) if isinstance(header_cfg, Mapping) else 150
        )
        left_area_width = (
            int(header_cfg.get("left_width", header_height)) if isinstance(header_cfg, Mapping) else header_height
        )
        extra_line_spacing = (
            float(body_cfg.get("line_spacing", 10)) if isinstance(body_cfg, Mapping) else 10.0
        )
        segment_spacing = (
            float(body_cfg.get("segment_spacing", 20)) if isinstance(body_cfg, Mapping) else 20.0
        )
        separator_pre_margin = (
            float(body_cfg.get("separator_margin_pre", 10)) if isinstance(body_cfg, Mapping) else 10.0
        )
        separator_color = _parse_color(
            body_cfg.get("separator_color") if isinstance(body_cfg, Mapping) else None,
            default=(150, 150, 150),
        )
        separator_thickness = (
            int(body_cfg.get("separator_thickness", 2)) if isinstance(body_cfg, Mapping) else 2
        )
        separator_margin = (
            int(body_cfg.get("separator_margin", 40)) if isinstance(body_cfg, Mapping) else 40
        )
        highlight_scale = (
            float(body_cfg.get("highlight_scale", 1.05)) if isinstance(body_cfg, Mapping) else 1.05
        )

        font_cfg = resolved.get("font") if isinstance(resolved.get("font"), Mapping) else {}
        header_font_size = (
            int(font_cfg.get("size_title", 24)) if isinstance(font_cfg, Mapping) else 24
        )
        body_font_size = (
            int(font_cfg.get("size_body", initial_font_size)) if isinstance(font_cfg, Mapping) else initial_font_size
        )
        header_color = _parse_color(
            font_cfg.get("color_title") if isinstance(font_cfg, Mapping) else None,
            default=(255, 255, 255),
        )

        colors_cfg = resolved.get("colors") if isinstance(resolved.get("colors"), Mapping) else {}
        if bg_color is not None:
            background_color = _parse_color(bg_color, default=(0, 0, 0))
        else:
            background_color = _parse_color(
                colors_cfg.get("background") if isinstance(colors_cfg, Mapping) else None,
                default=(0, 0, 0),
            )
        accent_color = _parse_color(
            colors_cfg.get("accent") if isinstance(colors_cfg, Mapping) else None,
            default=(255, 165, 0),
        )
        segment_colors = (
            resolved.get("segment_colors") if isinstance(resolved.get("segment_colors"), Mapping) else {}
        )
        original_color = _parse_color(
            segment_colors.get("original") if isinstance(segment_colors, Mapping) else None,
            default=(255, 255, 0),
        )
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
            cover_thumb.close()

        header_font = self._ensure_font(default_font_path, header_font_size)
        header_lines = raw_header.split("\n")
        header_line_spacing = (
            float(header_cfg.get("line_spacing", 4)) if isinstance(header_cfg, Mapping) else 4.0
        )
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

        original_seg, translation_seg, transliteration_seg = self._extract_sentence_segments(slide)

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
                            draw.text((x_line, y_text), w, font=font_orig, fill=original_color)
                    word_counter += 1
                    x_line += self._layout_engine.text_size(draw, font_orig, w)[0] + space_width
                y_text += self._layout_engine.text_size(draw, font_orig, line)[1] + extra_line_spacing

        if transliteration_seg:
            with profiler.time_block("draw.line") if profiler else nullcontext():
                draw.line(
                    [
                        (slide_size[0] * 0.1, y_text + separator_pre_margin),
                        (slide_size[0] * 0.9, y_text + separator_pre_margin),
                    ],
                    fill=separator_color,
                    width=separator_thickness,
                )
            y_text += separator_pre_margin + separator_thickness + separator_margin

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
                    word_counter += 1
                    x_line += self._layout_engine.text_size(draw, font_trans, w)[0] + space_width
                y_text += self._layout_engine.text_size(draw, font_trans, line)[1] + extra_line_spacing

        if transliteration_seg:
            with profiler.time_block("draw.line") if profiler else nullcontext():
                draw.line(
                    [
                        (slide_size[0] * 0.1, y_text + separator_pre_margin),
                        (slide_size[0] * 0.9, y_text + separator_pre_margin),
                    ],
                    fill=separator_color,
                    width=separator_thickness,
                )
            y_text += separator_pre_margin + separator_thickness + separator_margin

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
                    word_widths = [
                        self._layout_engine.text_size(draw, font_translit, w)[0] for w in words_line
                    ]
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
                                draw.text((x_line, y_text), w, font=font_translit, fill=transliteration_color)
                        word_counter += 1
                        x_line += (
                            self._layout_engine.text_size(draw, font_translit, w)[0] + space_width
                        )
                    y_text += self._layout_engine.text_size(draw, font_translit, line)[1] + extra_line_spacing

        return img


__all__ = ["SlideImageRenderer"]
