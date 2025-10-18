"""Utilities for generating audio and video artifacts."""

import io
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Iterable, List, Mapping, Optional, Sequence

from gtts import gTTS
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont

from modules import config_manager as cfg
from modules import logging_manager as log_mgr

logger = log_mgr.logger


_SILENCE_LOCK = Lock()
_SILENCE_FILENAME = "silence.wav"
_SILENCE_DURATION_MS = 100


def _silence_audio_path() -> str:
    """Return the shared silence audio file, creating it if necessary."""

    tmp_dir = cfg.TMP_DIR or tempfile.gettempdir()
    os.makedirs(tmp_dir, exist_ok=True)
    silence_path = os.path.join(tmp_dir, _SILENCE_FILENAME)

    if os.path.exists(silence_path):
        return silence_path

    with _SILENCE_LOCK:
        if not os.path.exists(silence_path):
            silent = AudioSegment.silent(duration=_SILENCE_DURATION_MS)
            silent.export(silence_path, format="wav")
    return silence_path


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def change_audio_tempo(sound: AudioSegment, tempo: float = 1.0) -> AudioSegment:
    """Adjust the tempo of an ``AudioSegment`` by modifying its frame rate."""
    if tempo == 1.0:
        return sound
    new_frame_rate = int(sound.frame_rate * tempo)
    return sound._spawn(sound.raw_data, overrides={"frame_rate": new_frame_rate}).set_frame_rate(sound.frame_rate)


def _synthesize_with_gtts(text: str, lang_code: str) -> AudioSegment:
    tts = gTTS(text=text, lang=lang_code)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return AudioSegment.from_file(fp, format="mp3")


def generate_macos_tts_audio(text: str, voice: str, lang_code: str, macos_reading_speed: int) -> AudioSegment:
    """Generate audio using the macOS ``say`` command, falling back to gTTS on failure."""
    with tempfile.NamedTemporaryFile(suffix=".aiff", dir=cfg.TMP_DIR, delete=False) as tmp:
        tmp_filename = tmp.name
    try:
        cmd = ["say", "-v", voice, "-r", str(macos_reading_speed), "-o", tmp_filename, text]
        subprocess.run(cmd, check=True)
        audio = AudioSegment.from_file(tmp_filename, format="aiff")
    except subprocess.CalledProcessError:
        logger.warning(
            "MacOS TTS command failed for voice '%s'. Falling back to default gTTS voice.",
            voice,
        )
        audio = _synthesize_with_gtts(text, lang_code)
    finally:
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)
    return audio


def generate_audio_segment(
    text: str,
    lang_code: str,
    selected_voice: str,
    macos_reading_speed: int,
) -> AudioSegment:
    """Generate a spoken ``AudioSegment`` for ``text`` using the configured voice."""
    if selected_voice == "gTTS":
        return _synthesize_with_gtts(text, lang_code)

    parts = selected_voice.split(" - ")
    if len(parts) >= 2:
        voice_name = parts[0].strip()
        voice_locale = parts[1].strip()
    else:
        voice_name = selected_voice
        voice_locale = ""

    if voice_locale.lower().startswith(lang_code.lower()):
        return generate_macos_tts_audio(text, voice_name, lang_code, macos_reading_speed)
    return _synthesize_with_gtts(text, lang_code)


def generate_audio_for_sentence(
    sentence_number: int,
    input_sentence: str,
    fluent_translation: str,
    input_language: str,
    target_language: str,
    audio_mode: str,
    total_sentences: int,
    language_codes: Mapping[str, str],
    selected_voice: str,
    tempo: float,
    macos_reading_speed: int,
) -> AudioSegment:
    """Generate the audio segment for a single sentence."""

    def _lang_code(lang: str) -> str:
        return language_codes.get(lang, "en")

    silence = AudioSegment.silent(duration=100)

    tasks = []

    def enqueue(key: str, text: str, lang_code: str) -> None:
        tasks.append((key, text, lang_code))

    target_lang_code = _lang_code(target_language)
    source_lang_code = _lang_code(input_language)

    numbering_str = f"{sentence_number} - {(sentence_number / total_sentences * 100):.2f}%"

    if audio_mode == "1":
        enqueue("translation", fluent_translation, target_lang_code)
        sequence = ["translation"]
    elif audio_mode == "2":
        enqueue("number", numbering_str, "en")
        enqueue("translation", fluent_translation, target_lang_code)
        sequence = ["number", "translation"]
    elif audio_mode == "3":
        enqueue("number", numbering_str, "en")
        enqueue("input", input_sentence, source_lang_code)
        enqueue("translation", fluent_translation, target_lang_code)
        sequence = ["number", "input", "translation"]
    elif audio_mode == "4":
        enqueue("input", input_sentence, source_lang_code)
        enqueue("translation", fluent_translation, target_lang_code)
        sequence = ["input", "translation"]
    elif audio_mode == "5":
        enqueue("input", input_sentence, source_lang_code)
        sequence = ["input"]
    else:
        enqueue("input", input_sentence, source_lang_code)
        enqueue("translation", fluent_translation, target_lang_code)
        sequence = ["input", "translation"]

    if not tasks:
        return change_audio_tempo(AudioSegment.silent(duration=0), tempo)

    worker_count = max(1, min(cfg.get_thread_count(), len(tasks)))
    segments = {}

    if worker_count == 1:
        for key, text, lang_code in tasks:
            segments[key] = generate_audio_segment(text, lang_code, selected_voice, macos_reading_speed)
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(generate_audio_segment, text, lang_code, selected_voice, macos_reading_speed): key
                for key, text, lang_code in tasks
            }
            for future in as_completed(future_map):
                key = future_map[future]
                try:
                    segments[key] = future.result()
                except Exception as exc:  # pragma: no cover - defensive
                    logger.error("Audio synthesis failed for segment '%s': %s", key, exc)
                    segments[key] = AudioSegment.silent(duration=0)

    audio = AudioSegment.silent(duration=0)
    for key in sequence:
        audio += segments.get(key, AudioSegment.silent(duration=0)) + silence

    return change_audio_tempo(audio, tempo)


# ---------------------------------------------------------------------------
# Video helpers
# ---------------------------------------------------------------------------

def get_default_font_path() -> str:
    if sys.platform == "darwin":
        for path in [
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        ]:
            if os.path.exists(path):
                return path
    elif sys.platform == "win32":
        path = r"C:\Windows\Fonts\arialuni.ttf"
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
    """Draw a slide image for a sentence block with optional progressive highlighting."""

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

    def wrap_text_local(text: str, draw_ctx: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, max_width: int) -> str:
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
        chosen_font: ImageFont.FreeTypeFont | None = None
        wrapped_text = text
        while font_size > 10:
            try:
                test_font = ImageFont.truetype(default_font_path, font_size)
            except IOError:
                test_font = ImageFont.load_default()
            candidate_wrapped = wrap_text_local(text, draw, test_font, max_width)
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
    total_text_height_active = sum(segments_heights) + segment_spacing * num_separators + separator_thickness * num_separators

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
                    highlight_font = ImageFont.truetype(default_font_path, int(font_orig.size * scale_factor))
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
                        highlight_font = ImageFont.truetype(default_font_path, int(font_trans.size * scale_factor))
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
                        highlight_font = ImageFont.truetype(default_font_path, int(font_trans.size * scale_factor))
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
                    highlight_font = ImageFont.truetype(default_font_path, int(font_translit.size * scale_factor))
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


def generate_word_synced_sentence_video(
    block: str,
    audio_seg: AudioSegment,
    sentence_index: int,
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

    header_line = raw_lines[0]
    if "Chinese" in header_line or "Japanese" in header_line:
        translation_units: Sequence[str] = list(translation_seg)
    else:
        translation_units = translation_seg.split() or [translation_seg]
    num_translation_words = len(translation_units)

    transliteration_words = transliteration_seg.split()
    num_translit_words = len(transliteration_words)

    audio_duration = audio_seg.duration_seconds
    total_letters = sum(len(w) for w in translation_units)

    word_durations: List[float] = []
    for w in translation_units:
        if total_letters > 0:
            dur = (len(w) / total_letters) * audio_duration * sync_ratio
        else:
            dur = (audio_duration / max(1, len(translation_units))) * sync_ratio
        word_durations.append(dur)

    video_duration = sum(word_durations)
    pad_duration = max(0.0, audio_duration - video_duration)

    word_video_files: List[str] = []
    accumulated_time = 0.0

    for idx, duration in enumerate(word_durations):
        accumulated_time += duration
        if idx == len(word_durations) - 1:
            fraction = 1.0
        else:
            fraction = accumulated_time / audio_duration if audio_duration else 1.0

        original_highlight_index = int(fraction * num_original_words) if num_original_words else 0
        translation_highlight_index = int(fraction * num_translation_words) if num_translation_words else 0
        transliteration_highlight_index = int(fraction * num_translit_words) if num_translit_words else 0

        if not word_highlighting:
            original_highlight_index = num_original_words
            translation_highlight_index = num_translation_words
            transliteration_highlight_index = num_translit_words

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

        img_path = os.path.join(cfg.TMP_DIR, f"word_slide_{sentence_index}_{idx}.png")
        img.save(img_path)

        video_path = os.path.join(cfg.TMP_DIR, f"word_slide_{sentence_index}_{idx}.mp4")
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
            _silence_audio_path(),
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

    concat_list_path = os.path.join(cfg.TMP_DIR, f"concat_word_{sentence_index}.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for video_file in word_video_files:
            f.write(f"file '{video_file}'\n")

    sentence_video_path = os.path.join(cfg.TMP_DIR, f"sentence_slide_{sentence_index}.mp4")
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

    audio_temp_path = os.path.join(cfg.TMP_DIR, f"sentence_audio_{sentence_index}.wav")
    audio_seg.export(audio_temp_path, format="wav")
    merged_video_path = os.path.join(cfg.TMP_DIR, f"sentence_slide_{sentence_index}_merged.mp4")

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

    final_video_path = os.path.join(cfg.TMP_DIR, f"sentence_slide_{sentence_index}_final.mp4")
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


def generate_video_slides_ffmpeg(
    text_blocks: Sequence[str],
    audio_segments: Sequence[AudioSegment],
    output_dir: str,
    batch_start: int,
    batch_end: int,
    base_no_ext: str,
    cover_img: Optional[Image.Image],
    book_author: str,
    book_title: str,
    cumulative_word_counts: Sequence[int],
    total_word_count: int,
    macos_reading_speed: int,
    input_language: str,
    total_sentences: int,
    tempo: float,
    sync_ratio: float,
    word_highlighting: bool,
    cleanup: bool = True,
    slide_size: Sequence[int] = (1280, 720),
    initial_font_size: int = 60,
    bg_color: Sequence[int] = (0, 0, 0),
) -> str:
    """Stitch sentence-level videos together for a batch of slides."""

    logger.info("Generating video slide set for sentences %s to %s...", batch_start, batch_end)
    sentence_video_files: List[str] = []
    silence_audio_path = _silence_audio_path()

    tasks = list(enumerate(zip(text_blocks, audio_segments)))
    worker_count = max(1, min(cfg.get_thread_count(), len(tasks)))
    ordered_results: List[Optional[str]] = [None] * len(tasks)

    def _render_sentence(index: int, block: str, audio_seg: AudioSegment) -> str:
        sentence_number = batch_start + index
        words_processed = cumulative_word_counts[sentence_number - 1]
        remaining_words = total_word_count - words_processed
        if macos_reading_speed > 0:
            est_seconds = int(remaining_words * 60 / macos_reading_speed)
        else:
            est_seconds = 0
        hours = est_seconds // 3600
        minutes = (est_seconds % 3600) // 60
        seconds = est_seconds % 60
        remaining_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        header_tokens = block.split("\n")[0].split(" - ")
        target_lang = header_tokens[0].strip() if header_tokens else ""
        progress_percentage = (sentence_number / total_sentences) * 100 if total_sentences else 0
        header_info = (
            f"Book: {book_title} | Author: {book_author}\n"
            f"Source Language: {input_language} | Target: {target_lang} | Speed: {tempo}\n"
            f"Sentence: {sentence_number}/{total_sentences} | Progress: {progress_percentage:.2f}% | Remaining: {remaining_time_str}"
        )

        local_cover = cover_img.copy() if cover_img else None

        return generate_word_synced_sentence_video(
            block,
            audio_seg,
            sentence_number,
            sync_ratio=sync_ratio,
            word_highlighting=word_highlighting,
            slide_size=slide_size,
            initial_font_size=initial_font_size,
            default_font_path=get_default_font_path(),
            bg_color=bg_color,
            cover_img=local_cover,
            header_info=header_info,
        )

    if worker_count == 1:
        for idx, (block, audio_seg) in tasks:
            try:
                ordered_results[idx] = _render_sentence(idx, block, audio_seg)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Error generating sentence video for sentence %s: %s", batch_start + idx, exc)
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(_render_sentence, idx, block, audio_seg): idx
                for idx, (block, audio_seg) in tasks
            }
            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    ordered_results[idx] = future.result()
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error("Error generating sentence video for sentence %s: %s", batch_start + idx, exc)

    sentence_video_files.extend(path for path in ordered_results if path)

    concat_list_path = os.path.join(output_dir, f"concat_{batch_start}_{batch_end}.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for video_file in sentence_video_files:
            f.write(f"file '{video_file}'\n")

    final_video_path = os.path.join(output_dir, f"{batch_start}-{batch_end}_{base_no_ext}.mp4")
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
        final_video_path,
    ]
    try:
        result = subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            logger.error("FFmpeg final concat error: %s", result.stderr.decode())
            raise subprocess.CalledProcessError(result.returncode, cmd_concat)
    except subprocess.CalledProcessError as exc:
        logger.error("Error concatenating sentence slides: %s", exc)
    finally:
        if os.path.exists(concat_list_path):
            os.remove(concat_list_path)

    logger.info("Final stitched video slide output saved to: %s", final_video_path)

    if cleanup:
        for video_file in sentence_video_files:
            if os.path.exists(video_file):
                os.remove(video_file)
        # The shared silence clip is reused across batches, so we keep it on disk.

    return final_video_path


__all__ = [
    "change_audio_tempo",
    "generate_audio_for_sentence",
    "generate_audio_segment",
    "generate_macos_tts_audio",
    "get_default_font_path",
    "generate_sentence_slide_image",
    "generate_word_synced_sentence_video",
    "generate_video_slides_ffmpeg",
]
