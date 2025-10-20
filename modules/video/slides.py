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
from typing import Iterable, List, Optional, Sequence

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

    orig_index_limit = original_highlight_word_index or 0
    word_counter = 0
    for line in orig_lines:
        words_line = line.split()
        space_bbox = draw.textbbox((0, 0), " ", font=font_orig)
        space_width = space_bbox[2] - space_bbox[0]
        total_width = sum(
            (draw.textbbox((0, 0), w, font=font_orig)[2] - draw.textbbox((0, 0), w, font=font_orig)[0])
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
        line_height = draw.textbbox((0, 0), line, font=font_orig)[3] - draw.textbbox((0, 0), line, font=font_orig)[1]
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
    if header_language in rtl_languages:
        char_counter = 0
        for line in trans_lines:
            line_width = sum(
                draw.textbbox((0, 0), ch, font=font_trans)[2] - draw.textbbox((0, 0), ch, font=font_trans)[0]
                for ch in line
            )
            x_line = (slide_size[0] - line_width) // 2
            for ch in line:
                ch_width = draw.textbbox((0, 0), ch, font=font_trans)[2] - draw.textbbox((0, 0), ch, font=font_trans)[0]
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
            line_height = draw.textbbox((0, 0), line, font=font_trans)[3] - draw.textbbox((0, 0), line, font=font_trans)[1]
            y_text += line_height + extra_line_spacing
    else:
        word_counter = 0
        for line in trans_lines:
            words_line = line.split()
            space_bbox = draw.textbbox((0, 0), " ", font=font_trans)
            space_width = space_bbox[2] - space_bbox[0]
            total_width = sum(
                (draw.textbbox((0, 0), w, font=font_trans)[2] - draw.textbbox((0, 0), w, font=font_trans)[0])
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
                w_width = draw.textbbox((0, 0), w, font=font_trans)[2] - draw.textbbox((0, 0), w, font=font_trans)[0]
                x_line += w_width + space_width
                word_counter += 1
            line_height = draw.textbbox((0, 0), line, font=font_trans)[3] - draw.textbbox((0, 0), line, font=font_trans)[1]
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
    word_counter = 0
    for line in translit_lines:
        words_line = line.split()
        space_bbox = draw.textbbox((0, 0), " ", font=font_translit)
        space_width = space_bbox[2] - space_bbox[0]
        total_width = sum(
            (draw.textbbox((0, 0), w, font=font_translit)[2] - draw.textbbox((0, 0), w, font=font_translit)[0])
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
        line_height = draw.textbbox((0, 0), line, font=font_translit)[3] - draw.textbbox((0, 0), line, font=font_translit)[1]
        y_text += line_height + extra_line_spacing

    return img


def build_sentence_video(
    block: str,
    audio_seg: AudioSegment,
    sentence_index: int,
    *,
    sync_ratio: float,
    word_highlighting: bool,
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

    if not word_highlighting:
        highlight_events = [
            HighlightEvent(
                duration=max(audio_duration * sync_ratio, 0.0),
                original_index=num_original_words,
                translation_index=num_translation_words,
                transliteration_index=num_translit_words,
            )
        ]
    else:
        highlight_events = []
        if metadata and metadata.parts:
            highlight_events = _build_events_from_metadata(
                metadata,
                sync_ratio,
                num_original_words,
                num_translation_words,
                num_translit_words,
            )
        if not highlight_events:
            highlight_events = _build_legacy_highlight_events(
                audio_duration,
                sync_ratio,
                original_words,
                translation_units,
                transliteration_words,
            )

    highlight_events = [event for event in highlight_events if event.duration > 0]
    if not highlight_events:
        highlight_events = [
            HighlightEvent(
                duration=max(audio_duration * sync_ratio, 0.0),
                original_index=num_original_words,
                translation_index=num_translation_words,
                transliteration_index=num_translit_words,
            )
        ]

    video_duration = sum(event.duration for event in highlight_events)
    pad_duration = max(0.0, audio_duration - video_duration)

    word_video_files: List[str] = []
    tmp_dir = active_tmp_dir()

    for idx, event in enumerate(highlight_events):
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

        img = generate_sentence_slide_image(
            block,
            original_highlight_word_index=original_highlight_index,
            translation_highlight_word_index=translation_highlight_index,
            transliteration_highlight_word_index=transliteration_highlight_index,
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
