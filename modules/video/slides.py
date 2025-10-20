"""Sentence slide composition and video helpers.

This module centralises the logic for rendering sentence slides and composing
per-sentence videos.  It relies on Pillow (``PIL``) for text rendering with
TrueType fonts and assumes an ``ffmpeg`` executable is available on the system
``PATH`` for video muxing.  Callers should ensure the expected fonts are
installed (see :func:`get_default_font_path`) and that ``ffmpeg`` can be
invoked.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment

from modules import logging_manager as log_mgr
from modules.audio.highlight import (
    HighlightEvent,
    _build_events_from_metadata,
    _build_legacy_highlight_events,
    _get_audio_metadata,
)
from modules.audio.tts import active_tmp_dir, silence_audio_path

logger = log_mgr.logger


__all__ = [
    "build_sentence_video",
    "generate_sentence_slide_image",
    "get_default_font_path",
]


@dataclass(slots=True)
class LineLayout:
    text: str
    x: float
    y: float
    height: float
    width: float
    char_boxes: List[Tuple[int, Tuple[float, float, float, float]]]


def _prepare_line_layout(
    *,
    text: str,
    lines: Sequence[str],
    font: ImageFont.FreeTypeFont,
    draw_ctx: ImageDraw.ImageDraw,
    slide_width: int,
    start_y: float,
    line_spacing: float,
) -> Tuple[List[LineLayout], Dict[int, Tuple[float, float, float, float]], float]:
    """Compute positioning metadata for rendering ``lines`` of ``text``."""

    layouts: List[LineLayout] = []
    char_map: Dict[int, Tuple[float, float, float, float]] = {}
    source_index = 0
    y_cursor = start_y

    for line in lines:
        bbox = draw_ctx.textbbox((0, 0), line, font=font)
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
            prev_width = draw_ctx.textlength(prefix, font=font) if prefix else 0.0
            curr_width = draw_ctx.textlength(next_prefix, font=font)
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
) -> Image.Image:
    """Draw a slide image for a sentence block with optional highlighting."""

    img = Image.new("RGB", slide_size, bg_color)
    draw = ImageDraw.Draw(img)

    header_height = 150
    left_area_width = header_height

    raw_lines = block.split("\n")
    header_line = raw_lines[0] if raw_lines else ""
    header_text = header_info if header_info else header_line

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
        bbox = draw.textbbox((0, 0), line, font=header_font)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        max_header_width = max(max_header_width, line_width)
        total_header_height += line_height
    total_header_height += header_line_spacing * (len(header_lines) - 1)
    if cover_img:
        available_width = slide_size[0] - left_area_width
        header_x = left_area_width + (available_width - max_header_width) // 2
    else:
        header_x = (slide_size[0] - max_header_width) // 2
    header_y = (header_height - total_header_height) // 2

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
        text: str, draw_ctx: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, max_width: int
    ) -> str:
        if " " not in text:
            lines_: List[str] = []
            current_line = ""
            for ch in text:
                test_line = current_line + ch
                bbox = draw_ctx.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] <= max_width:
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
            bbox = draw_ctx.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                lines_.append(current_line)
                current_line = word
        lines_.append(current_line)
        return "\n".join(lines_)

    def get_wrapped_text_and_font(text: str) -> tuple[str, ImageFont.FreeTypeFont]:
        max_width = slide_size[0] * 0.9
        max_height = slide_size[1] * 0.9
        font_size = int(initial_font_size * 0.85)
        chosen_font: Optional[ImageFont.FreeTypeFont] = None
        wrapped_text = text
        while font_size > 10:
            try:
                test_font = ImageFont.truetype(default_font_path, font_size)
            except IOError:
                test_font = ImageFont.load_default()
            candidate_wrapped = wrap_text_local(text, draw, test_font, int(max_width))
            total_height = 0
            lines = candidate_wrapped.split("\n")
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=test_font)
                total_height += bbox[3] - bbox[1]
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

    def compute_height(lines: Iterable[str], font: ImageFont.FreeTypeFont) -> int:
        total = 0
        lines_list = list(lines)
        for i, line in enumerate(lines_list):
            bbox = draw.textbbox((0, 0), line, font=font)
            total += bbox[3] - bbox[1]
            if i < len(lines_list) - 1:
                total += extra_line_spacing
        return total

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
        )
        _fill_char_range(draw, char_map, orig_char_range, highlight_color)
        for layout in layouts:
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
            space_bbox = draw.textbbox((0, 0), " ", font=font_orig)
            space_width = space_bbox[2] - space_bbox[0]
            total_width = sum(
                (
                    draw.textbbox((0, 0), w, font=font_orig)[2]
                    - draw.textbbox((0, 0), w, font=font_orig)[0]
                )
                for w in words_line
            ) + space_width * (len(words_line) - 1)
            x_line = (slide_size[0] - total_width) // 2
            for w in words_line:
                if word_counter < orig_index_limit:
                    try:
                        highlight_font = ImageFont.truetype(
                            default_font_path, int(font_orig.size * scale_factor)
                        )
                    except IOError:
                        highlight_font = font_orig
                    draw.text((x_line, y_text), w, font=highlight_font, fill=highlight_color)
                else:
                    draw.text((x_line, y_text), w, font=font_orig, fill=original_sentence_color)
                w_bbox = draw.textbbox((0, 0), w, font=font_orig)
                w_width = w_bbox[2] - w_bbox[0]
                x_line += w_width + space_width
                word_counter += 1
            line_height = (
                draw.textbbox((0, 0), line, font=font_orig)[3]
                - draw.textbbox((0, 0), line, font=font_orig)[1]
            )
            y_text += line_height + extra_line_spacing

    if translation_seg:
        y_text += separator_pre_margin
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
        )
        _fill_char_range(draw, char_map, trans_char_range, highlight_color)
        for layout in layouts:
            draw.text(
                (layout.x, layout.y),
                layout.text,
                font=font_trans,
                fill=translation_color,
            )
    elif header_language in rtl_languages:
        char_counter = 0
        for line in trans_lines:
            line_width = sum(
                draw.textbbox((0, 0), ch, font=font_trans)[2]
                - draw.textbbox((0, 0), ch, font=font_trans)[0]
                for ch in line
            )
            x_line = (slide_size[0] - line_width) // 2
            for ch in line:
                ch_width = (
                    draw.textbbox((0, 0), ch, font=font_trans)[2]
                    - draw.textbbox((0, 0), ch, font=font_trans)[0]
                )
                if char_counter < trans_index_limit:
                    try:
                        highlight_font = ImageFont.truetype(
                            default_font_path, int(font_trans.size * scale_factor)
                        )
                    except IOError:
                        highlight_font = font_trans
                    draw.text((x_line, y_text), ch, font=highlight_font, fill=highlight_color)
                else:
                    draw.text((x_line, y_text), ch, font=font_trans, fill=translation_color)
                x_line += ch_width
                char_counter += 1
            line_height = (
                draw.textbbox((0, 0), line, font=font_trans)[3]
                - draw.textbbox((0, 0), line, font=font_trans)[1]
            )
            y_text += line_height + extra_line_spacing
    else:
        word_counter = 0
        for line in trans_lines:
            words_line = line.split()
            space_bbox = draw.textbbox((0, 0), " ", font=font_trans)
            space_width = space_bbox[2] - space_bbox[0]
            total_width = sum(
                (
                    draw.textbbox((0, 0), w, font=font_trans)[2]
                    - draw.textbbox((0, 0), w, font=font_trans)[0]
                )
                for w in words_line
            ) + space_width * (len(words_line) - 1)
            x_line = (slide_size[0] - total_width) // 2
            for w in words_line:
                if word_counter < trans_index_limit:
                    try:
                        highlight_font = ImageFont.truetype(
                            default_font_path, int(font_trans.size * scale_factor)
                        )
                    except IOError:
                        highlight_font = font_trans
                    draw.text((x_line, y_text), w, font=highlight_font, fill=highlight_color)
                else:
                    draw.text((x_line, y_text), w, font=font_trans, fill=translation_color)
                w_width = (
                    draw.textbbox((0, 0), w, font=font_trans)[2]
                    - draw.textbbox((0, 0), w, font=font_trans)[0]
                )
                x_line += w_width + space_width
                word_counter += 1
            line_height = (
                draw.textbbox((0, 0), line, font=font_trans)[3]
                - draw.textbbox((0, 0), line, font=font_trans)[1]
            )
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
        )
        _fill_char_range(draw, char_map, translit_char_range, highlight_color)
        for layout in layouts:
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
            space_bbox = draw.textbbox((0, 0), " ", font=font_translit)
            space_width = space_bbox[2] - space_bbox[0]
            total_width = sum(
                (
                    draw.textbbox((0, 0), w, font=font_translit)[2]
                    - draw.textbbox((0, 0), w, font=font_translit)[0]
                )
                for w in words_line
            ) + space_width * (len(words_line) - 1)
            x_line = (slide_size[0] - total_width) // 2
            for w in words_line:
                if word_counter < translit_index_limit:
                    try:
                        highlight_font = ImageFont.truetype(
                            default_font_path, int(font_translit.size * scale_factor)
                        )
                    except IOError:
                        highlight_font = font_translit
                    draw.text((x_line, y_text), w, font=highlight_font, fill=highlight_color)
                else:
                    draw.text((x_line, y_text), w, font=font_translit, fill=transliteration_color)
                w_bbox = draw.textbbox((0, 0), w, font=font_translit)
                w_width = w_bbox[2] - w_bbox[0]
                x_line += w_width + space_width
                word_counter += 1
            line_height = (
                draw.textbbox((0, 0), line, font=font_translit)[3]
                - draw.textbbox((0, 0), line, font=font_translit)[1]
            )
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
) -> str:
    """Generate a word-synchronised video for a single sentence."""

    if default_font_path is None:
        default_font_path = get_default_font_path()

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

    video_duration = sum(event.duration for event in timeline_events)
    pad_duration = max(0.0, audio_duration - video_duration)

    word_video_files: List[str] = []
    tmp_dir = active_tmp_dir()

    for idx, event in enumerate(timeline_events):
        duration = event.duration
        original_highlight_index = (
            min(event.original_index, num_original_words) if word_highlighting else num_original_words
        )
        translation_highlight_index = (
            min(event.translation_index, num_translation_words)
            if word_highlighting
            else num_translation_words
        )
        transliteration_highlight_index = (
            min(event.transliteration_index, num_translit_words)
            if word_highlighting
            else num_translit_words
        )

        def _event_char_range(
            evt: HighlightEvent, target_kind: str
        ) -> Optional[Tuple[int, int]]:
            step = evt.step
            if step is None or step.kind != target_kind:
                return None
            start = step.char_index_start
            end = step.char_index_end
            if start is None or end is None:
                return None
            start_idx = int(start)
            end_idx = int(end)
            if end_idx <= start_idx:
                return None
            return (start_idx, end_idx)

        original_char_range = (
            _event_char_range(event, "original")
            if effective_granularity == "char"
            else None
        )
        translation_char_range = (
            _event_char_range(event, "translation")
            if effective_granularity == "char"
            else None
        )
        transliteration_char_range = (
            _event_char_range(event, "other")
            if effective_granularity == "char"
            else None
        )

        img = generate_sentence_slide_image(
            block,
            original_highlight_word_index=original_highlight_index,
            translation_highlight_word_index=translation_highlight_index,
            transliteration_highlight_word_index=transliteration_highlight_index,
            original_highlight_char_range=original_char_range,
            translation_highlight_char_range=translation_char_range,
            transliteration_highlight_char_range=transliteration_char_range,
            highlight_granularity=effective_granularity,
            slide_size=slide_size,
            initial_font_size=initial_font_size,
            default_font_path=default_font_path,
            bg_color=bg_color,
            cover_img=cover_img,
            header_info=header_info,
        )

        img_path = os.path.join(tmp_dir, f"word_slide_{sentence_index}_{idx}.png")
        img.save(img_path)

        video_path = os.path.join(tmp_dir, f"word_slide_{sentence_index}_{idx}.mp4")
        cmd = [
            "ffmpeg",
            "-loglevel",
            "quiet",
            "-y",
            "-loop",
            "1",
            "-i",
            img_path,
            "-i",
            silence_audio_path(),
            "-c:v",
            "libx264",
            "-t",
            f"{duration:.2f}",
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
            logger.error("FFmpeg error on word slide %s_%s: %s", sentence_index, idx, exc)
        finally:
            if os.path.exists(img_path):
                os.remove(img_path)
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
