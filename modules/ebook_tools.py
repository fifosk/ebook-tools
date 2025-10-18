#!/usr/bin/env python3
import os
import concurrent.futures
import sys, re, json, subprocess, warnings, statistics, math, base64, time
import shutil
import queue
import threading
from pathlib import Path
from typing import Optional
from . import config_manager as cfg
from . import logging_manager as log_mgr
from . import audio_video_generator as av_gen
from . import translation_engine
from .menu_interface import (
    parse_arguments,
    run_interactive_menu,
    update_book_cover_file_in_config,
    fetch_book_cover,
)
from .epub_parser import (
    DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
    DEFAULT_MAX_WORDS,
    extract_text_from_epub,
    remove_quotes,
    split_text_into_sentences,
    split_text_into_sentences_no_refine,
)

# ReportLab imports for PDF generation
# Arabic/Hebrew processing
import arabic_reshaper
from bidi.algorithm import get_display

# Audio generation (gTTS and pydub)
from pydub import AudioSegment

# Video generation using Pillow and ffmpeg
from PIL import Image

from . import output_formatter
from .progress_tracker import ProgressTracker

SCRIPT_DIR = cfg.SCRIPT_DIR
LOG_DIR = log_mgr.LOG_DIR
LOG_FILE = log_mgr.LOG_FILE
DEFAULT_WORKING_RELATIVE = cfg.DEFAULT_WORKING_RELATIVE
DEFAULT_OUTPUT_RELATIVE = cfg.DEFAULT_OUTPUT_RELATIVE
DEFAULT_TMP_RELATIVE = cfg.DEFAULT_TMP_RELATIVE
DEFAULT_BOOKS_RELATIVE = cfg.DEFAULT_BOOKS_RELATIVE
CONF_DIR = cfg.CONF_DIR
DEFAULT_CONFIG_PATH = cfg.DEFAULT_CONFIG_PATH
DEFAULT_LOCAL_CONFIG_PATH = cfg.DEFAULT_LOCAL_CONFIG_PATH

DERIVED_RUNTIME_DIRNAME = cfg.DERIVED_RUNTIME_DIRNAME
DERIVED_REFINED_FILENAME_TEMPLATE = cfg.DERIVED_REFINED_FILENAME_TEMPLATE
DERIVED_CONFIG_KEYS = cfg.DERIVED_CONFIG_KEYS

DEFAULT_OLLAMA_URL = cfg.DEFAULT_OLLAMA_URL
DEFAULT_FFMPEG_PATH = cfg.DEFAULT_FFMPEG_PATH

logger = log_mgr.logger
configure_logging_level = log_mgr.configure_logging_level
resolve_directory = cfg.resolve_directory
resolve_file_path = cfg.resolve_file_path
initialize_environment = cfg.initialize_environment
load_configuration = cfg.load_configuration
DEFAULT_MODEL = cfg.DEFAULT_MODEL
OLLAMA_MODEL = DEFAULT_MODEL
translation_engine.set_model(OLLAMA_MODEL)

ENTRY_SCRIPT_NAME = "main.py"

# Explicitly set ffmpeg converter for pydub using configurable path
AudioSegment.converter = DEFAULT_FFMPEG_PATH

# Will be updated once configuration is loaded via cfg

# -----------------------
# Path Helpers
# -----------------------
def get_runtime_output_dir():
    """Return the directory used for storing derived runtime artifacts."""
    if cfg.WORKING_DIR:
        base_path = Path(cfg.WORKING_DIR)
    else:
        base_path = Path(resolve_directory(None, DEFAULT_WORKING_RELATIVE))
    runtime_dir = base_path / DERIVED_RUNTIME_DIRNAME
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir


def refined_list_output_path(input_file):
    base_name = Path(input_file).stem if input_file else "refined"
    safe_base = re.sub(r"[^A-Za-z0-9_.-]", "_", base_name)
    runtime_dir = get_runtime_output_dir()
    return runtime_dir / DERIVED_REFINED_FILENAME_TEMPLATE.format(base_name=safe_base)


def save_refined_list(refined_list, input_file, metadata=None):
    """Persist the refined sentence list to the runtime output directory."""
    output_path = refined_list_output_path(input_file)
    payload = {
        "generated_at": time.time(),
        "input_file": input_file,
        "max_words": MAX_WORDS,
        "split_on_comma_semicolon": EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
        "metadata": metadata or {},
        "refined_list": refined_list,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return output_path


def load_refined_list(input_file):
    """Load a previously generated refined list from the runtime directory if available."""
    output_path = refined_list_output_path(input_file)
    if not output_path.exists():
        return None
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, OSError):
        return None


def get_refined_sentences(input_file, force_refresh=False, metadata=None):
    """Return the refined sentence list and whether it was regenerated."""
    if not input_file:
        return [], False

    resolved_input = resolve_file_path(input_file, cfg.BOOKS_DIR)
    if not resolved_input:
        return [], False
    input_file = str(resolved_input)

    expected_settings = {
        "max_words": MAX_WORDS,
        "split_on_comma_semicolon": EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
    }

    cached = None if force_refresh else load_refined_list(input_file)
    if cached and cached.get("refined_list") is not None:
        cached_settings = {
            "max_words": cached.get("max_words"),
            "split_on_comma_semicolon": cached.get("split_on_comma_semicolon"),
        }
        if cached_settings == expected_settings:
            return cached.get("refined_list", []), False

    text = extract_text_from_epub(input_file)
    refined = split_text_into_sentences(
        text,
        max_words=MAX_WORDS,
        extend_split_with_comma_semicolon=EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
    )
    save_refined_list(refined, input_file, metadata=metadata)
    return refined, True


# -----------------------
# Global Variables for Audio/Video Options
# -----------------------
SELECTED_VOICE = "gTTS"
DEBUG = True
translation_engine.set_debug(DEBUG)
MAX_WORDS = DEFAULT_MAX_WORDS
EXTEND_SPLIT_WITH_COMMA_SEMICOLON = DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON
MACOS_READING_SPEED = 100
SYNC_RATIO = 0.9
# New global tempo variable; 1.0 means normal speed.
TEMPO = 1.0

# -----------------------
# Global variable for non-Latin languages (Added Persian)
# -----------------------
NON_LATIN_LANGUAGES = {
    "Arabic", "Armenian", "Chinese (Simplified)", "Chinese (Traditional)",
    "Hebrew", "Japanese", "Korean", "Russian", "Thai", "Greek", "Hindi", "Bengali", "Tamil", "Telugu", "Gujarati", "Persian"
}

# -----------------------
# Global option: Word highlighting for video slides (default enabled)
# -----------------------
WORD_HIGHLIGHTING = True

# -----------------------
# Helper Functions for Text Wrapping & Font Adjustment
# -----------------------


def _build_written_and_video_blocks(
    *,
    sentence_number: int,
    sentence: str,
    fluent: str,
    transliteration: str,
    current_target: str,
    written_mode: str,
    total_sentences: int,
    include_transliteration: bool,
) -> tuple[str, str]:
    """Return formatted written and video blocks mirroring the legacy output."""

    percent = (sentence_number / total_sentences * 100) if total_sentences else 0.0
    header = f"{current_target} - {sentence_number} - {percent:.2f}%\n"

    if written_mode == "1":
        written_block = f"{fluent}\n"
    elif written_mode == "2":
        written_block = f"{sentence_number} - {percent:.2f}%\n{fluent}\n"
    elif written_mode == "3":
        written_block = f"{sentence_number} - {percent:.2f}%\n{sentence}\n\n{fluent}\n"
    else:
        written_block = f"{sentence}\n\n{fluent}\n"

    if include_transliteration and transliteration:
        written_block = written_block.rstrip() + f"\n{transliteration}\n"
        video_block = (
            f"{header}"
            f"{sentence}\n\n{fluent}\n{transliteration}\n"
        )
    else:
        video_block = f"{header}{sentence}\n\n{fluent}\n"

    return written_block, video_block
def wrap_text(text, draw, font, max_width):
    if " " in text:
        words = text.split()
        if not words:
            return ""
        lines = []
        current_line = words[0]
        for word in words[1:]:
            test_line = current_line + " " + word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]
            if width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        return "\n".join(lines)
    else:
        lines = []
        current_line = ""
        for char in text:
            test_line = current_line + char
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]
            if width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
        return "\n".join(lines)

def adjust_font_and_wrap_text(text, draw, slide_size, initial_font_size, font_path="Arial.ttf",
                              max_width_fraction=0.9, max_height_fraction=0.9):
    max_width = slide_size[0] * max_width_fraction
    max_height = slide_size[1] * max_height_fraction
    font_size = int(initial_font_size * 0.85)  # Reduce font size by 15%
    while font_size > 10:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            font = ImageFont.load_default()
        wrapped_text = wrap_text(text, draw, font, max_width)
        total_height = sum((draw.textbbox((0, 0), line, font=font)[3] - 
                            draw.textbbox((0, 0), line, font=font)[1])
                           for line in wrapped_text.split("\n"))
        if total_height <= max_height:
            return wrapped_text, font
        font_size -= 2
    return wrapped_text, font

def adjust_font_for_three_segments(seg1, seg2, seg3, draw, slide_size, initial_font_size, font_path="Arial.ttf",
                                   max_width_fraction=0.9, max_height_fraction=0.9, spacing=10):
    max_width = slide_size[0] * max_width_fraction
    max_height = slide_size[1] * max_height_fraction
    font_size = int(initial_font_size * 0.25)
    while font_size > 10:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            font = ImageFont.load_default()
        wrapped1 = wrap_text(seg1, draw, font, max_width)
        wrapped2 = wrap_text(seg2, draw, font, max_width)
        wrapped3 = wrap_text(seg3, draw, font, max_width)
        total_height = 0
        for wrapped in (wrapped1, wrapped2, wrapped3):
            for line in wrapped.split("\n"):
                total_height += (draw.textbbox((0, 0), line, font=font)[3] - 
                                 draw.textbbox((0, 0), line, font=font)[1])
        total_height += 2 * spacing
        if total_height <= max_height:
            return wrapped1, wrapped2, wrapped3, font
        font_size -= 2
    return wrapped1, wrapped2, wrapped3, font

# -----------------------
# Global Configuration (Consolidated language codes)
# -----------------------
LANGUAGE_CODES = {
    "Afrikaans": "af",
    "Albanian": "sq",
    "Arabic": "ar",
    "Armenian": "hy",
    "Basque": "eu",
    "Bengali": "bn",
    "Bosnian": "bs",
    "Burmese": "my",
    "Catalan": "ca",
    "Chinese (Simplified)": "zh-CN",
    "Chinese (Traditional)": "zh-TW",
    "Czech": "cs",
    "Croatian": "hr",
    "Danish": "da",
    "Dutch": "nl",
    "English": "en",
    "Esperanto": "eo",
    "Estonian": "et",
    "Filipino": "tl",
    "Finnish": "fi",
    "French": "fr",
    "German": "de",
    "Greek": "el",
    "Gujarati": "gu",
    "Hausa": "ha",
    "Hebrew": "he",
    "Hindi": "hi",
    "Hungarian": "hu",
    "Icelandic": "is",
    "Indonesian": "id",
    "Italian": "it",
    "Japanese": "ja",
    "Javanese": "jw",
    "Kannada": "kn",
    "Khmer": "km",
    "Korean": "ko",
    "Latin": "la",
    "Latvian": "lv",
    "Macedonian": "mk",
    "Malay": "ms",
    "Malayalam": "ml",
    "Marathi": "mr",
    "Nepali": "ne",
    "Norwegian": "no",
    "Polish": "pl",
    "Portuguese": "pt",
    "Romanian": "ro",
    "Russian": "ru",
    "Sinhala": "si",
    "Slovak": "sk",
    "Serbian": "sr",
    "Sundanese": "su",
    "Swahili": "sw",
    "Swedish": "sv",
    "Tamil": "ta",
    "Telugu": "te",
    "Thai": "th",
    "Turkish": "tr",
    "Ukrainian": "uk",
    "Urdu": "ur",
    "Vietnamese": "vi",
    "Welsh": "cy",
    "Xhosa": "xh",
    "Yoruba": "yo",
    "Zulu": "zu",
    "Persian": "fa"
}

# -----------------------
# Modified Function: Combined Translation
# -----------------------
def translate_sentence_simple(sentence, input_language, target_language, include_transliteration=False):
    return translation_engine.translate_sentence_simple(
        sentence,
        input_language,
        target_language,
        include_transliteration=include_transliteration,
    )


def transliterate_sentence(translated_sentence, target_language):
    return translation_engine.transliterate_sentence(translated_sentence, target_language)

def _export_pipeline_batch(
    *,
    base_dir,
    base_no_ext,
    batch_start,
    batch_end,
    written_blocks,
    target_language,
    output_html,
    output_pdf,
    generate_audio,
    audio_segments,
    generate_video,
    video_blocks,
    cover_img,
    book_author,
    book_title,
    global_cumulative_word_counts,
    total_book_words,
    macos_reading_speed,
    input_language,
    total_sentences,
    tempo,
    sync_ratio,
    word_highlighting,
):
    """Write batch outputs for a contiguous block of sentences."""

    try:
        output_formatter.export_batch_documents(
            base_dir,
            base_no_ext,
            batch_start,
            batch_end,
            list(written_blocks),
            target_language,
            output_html=output_html,
            output_pdf=output_pdf,
        )

        audio_segments = list(audio_segments) if audio_segments else []
        video_blocks = list(video_blocks) if video_blocks else []
        video_path = None

        if generate_audio and audio_segments:
            combined = AudioSegment.empty()
            for segment in audio_segments:
                combined += segment
            audio_filename = os.path.join(
                base_dir, f"{batch_start}-{batch_end}_{base_no_ext}.mp3"
            )
            combined.export(audio_filename, format="mp3", bitrate="320k")

        if generate_video and audio_segments:
            video_path = av_gen.generate_video_slides_ffmpeg(
                video_blocks,
                audio_segments,
                base_dir,
                batch_start,
                batch_end,
                base_no_ext,
                cover_img,
                book_author,
                book_title,
                global_cumulative_word_counts,
                total_book_words,
                macos_reading_speed,
                input_language,
                total_sentences,
                tempo,
                sync_ratio,
                word_highlighting,
            )
        return video_path
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to export batch %s-%s: %s", batch_start, batch_end, exc)
        return None


# -----------------------
# Main EPUB Processing Function
# -----------------------
def process_epub(
    input_file,
    base_output_file,
    input_language,
    target_languages,
    sentences_per_file,
    start_sentence,
    end_sentence,
    generate_audio,
    audio_mode,
    written_mode,
    output_html,
    output_pdf,
    refined_list,
    generate_video,
    include_transliteration=False,
    book_metadata={},
    *,
    progress_tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
):
    logger.info("Extracting text from '%s'...", input_file)
    total_fully = len(refined_list)
    logger.info("Total fully split sentences extracted: %s", total_fully)
    start_idx = max(start_sentence - 1, 0)
    end_idx = end_sentence if (end_sentence is not None and end_sentence <= total_fully) else total_fully
    selected_sentences = refined_list[start_idx:end_idx]
    total_refined = len(selected_sentences)
    logger.info(
        "Processing %s sentences starting from refined sentence #%s",
        total_refined,
        start_sentence,
    )
    if progress_tracker is not None:
        progress_tracker.set_total(total_refined)
    
        # --- Updated output folder naming convention ---
    # [Author]_[BookTitle]_[SRC_LANGCODE]_[TGT_LANGCODE]

    src_code = LANGUAGE_CODES.get(input_language, "XX").upper()
    tgt_code = LANGUAGE_CODES.get(target_languages[0], "XX").upper()

    base_dir, base_no_ext, base_output_file = output_formatter.prepare_output_directory(
        input_file,
        book_metadata.get("book_author"),
        book_metadata.get("book_title"),
        src_code,
        tgt_code,
    )
    
    book_title = book_metadata.get("book_title", "Unknown Title")
    book_author = book_metadata.get("book_author", "Unknown Author")
    
    cover_img = None
    cover_file_path = resolve_file_path(book_metadata.get("book_cover_file"), cfg.BOOKS_DIR)
    if cover_file_path and cover_file_path.exists():
        try:
            with Image.open(cover_file_path) as img:
                cover_img = img.convert("RGB")
                cover_img.load()
        except Exception as e:
            if DEBUG:
                logger.debug("Error loading cover image from file: %s", e)
            cover_img = None
    else:
        remote_cover = fetch_book_cover(f"{book_title} {book_author}")
        if remote_cover:
            try:
                cover_img = remote_cover.convert("RGB")
                cover_img.load()
            finally:
                try:
                    remote_cover.close()
                except Exception:  # pragma: no cover - best effort cleanup
                    pass
    
    global_cumulative_word_counts = []
    running = 0
    for s in refined_list:
        running += len(s.split())
        global_cumulative_word_counts.append(running)
    total_book_words = running
    
    written_blocks = []
    video_blocks = []
    all_audio_segments = [] if generate_audio else None
    batch_video_files = []
    current_audio = [] if generate_audio else None
    current_batch_start = start_sentence
    processed = 0
    last_target_language = target_languages[0] if target_languages else ""
    pipeline_enabled = cfg.is_pipeline_mode()
    queue_size = cfg.get_queue_size()
    worker_count = max(1, cfg.get_thread_count())
    translation_thread = None
    media_threads = []
    translation_queue = None
    media_queue = None
    finalize_executor = None
    export_futures = []

    if not pipeline_enabled:
        batch_size = worker_count
        while processed < total_refined:
            if stop_event and stop_event.is_set():
                logger.info("Stop requested; halting remaining sequential processing.")
                break
            batch_sentences = selected_sentences[processed : processed + batch_size]
            batch_sentence_numbers = [
                start_sentence + processed + idx for idx in range(len(batch_sentences))
            ]
            batch_targets = [
                target_languages[((number - start_sentence) % len(target_languages))]
                for number in batch_sentence_numbers
            ]
            translations = translation_engine.translate_batch(
                batch_sentences,
                input_language,
                batch_targets,
                include_transliteration=False,
            )

            for (
                sentence_number,
                sentence,
                current_target,
                translation_result,
            ) in zip(batch_sentence_numbers, batch_sentences, batch_targets, translations):
                if stop_event and stop_event.is_set():
                    break
                fluent = remove_quotes(translation_result or "")
                should_transliterate = include_transliteration and current_target in NON_LATIN_LANGUAGES
                transliteration_result = ""
                if should_transliterate:
                    transliteration_result = transliterate_sentence(fluent, current_target)
                    transliteration_result = remove_quotes(transliteration_result)
                written_block, video_block = _build_written_and_video_blocks(
                    sentence_number=sentence_number,
                    sentence=sentence,
                    fluent=fluent,
                    transliteration=transliteration_result,
                    current_target=current_target,
                    written_mode=written_mode,
                    total_sentences=total_fully,
                    include_transliteration=should_transliterate,
                )
                written_blocks.append(written_block)
                if generate_video:
                    video_blocks.append(video_block)
                if generate_audio and current_audio is not None and all_audio_segments is not None:
                    audio_seg = av_gen.generate_audio_for_sentence(
                        sentence_number,
                        sentence,
                        fluent,
                        input_language,
                        current_target,
                        audio_mode,
                        total_fully,
                        LANGUAGE_CODES,
                        SELECTED_VOICE,
                        TEMPO,
                        MACOS_READING_SPEED,
                    )
                    current_audio.append(audio_seg)
                    all_audio_segments.append(audio_seg)

                if (sentence_number - start_sentence + 1) % sentences_per_file == 0:
                    batch_start = current_batch_start
                    batch_end = sentence_number
                    video_path = _export_pipeline_batch(
                        base_dir=base_dir,
                        base_no_ext=base_no_ext,
                        batch_start=batch_start,
                        batch_end=batch_end,
                        written_blocks=written_blocks,
                        target_language=current_target,
                        output_html=output_html,
                        output_pdf=output_pdf,
                        generate_audio=generate_audio,
                        audio_segments=current_audio or [],
                        generate_video=generate_video,
                        video_blocks=video_blocks,
                        cover_img=cover_img,
                        book_author=book_author,
                        book_title=book_title,
                        global_cumulative_word_counts=global_cumulative_word_counts,
                        total_book_words=total_book_words,
                        macos_reading_speed=MACOS_READING_SPEED,
                        input_language=input_language,
                        total_sentences=total_fully,
                        tempo=TEMPO,
                        sync_ratio=SYNC_RATIO,
                        word_highlighting=WORD_HIGHLIGHTING,
                    )
                    if video_path:
                        batch_video_files.append(video_path)
                    written_blocks = []
                    video_blocks = []
                    if generate_audio:
                        current_audio = []
                    current_batch_start = sentence_number + 1
                last_target_language = current_target
                processed += 1
                if progress_tracker is not None:
                    progress_tracker.record_media_completion(
                        processed - 1, sentence_number
                    )

            if stop_event and stop_event.is_set():
                break
    else:
        pipeline_stop_event = stop_event or threading.Event()
        translation_queue = queue.Queue(maxsize=queue_size)
        finalize_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        media_queue, media_threads = av_gen.start_media_pipeline(
            translation_queue,
            worker_count=worker_count,
            total_sentences=total_fully,
            input_language=input_language,
            audio_mode=audio_mode,
            language_codes=LANGUAGE_CODES,
            selected_voice=SELECTED_VOICE,
            tempo=TEMPO,
            macos_reading_speed=MACOS_READING_SPEED,
            generate_audio=generate_audio,
            queue_size=queue_size,
            stop_event=pipeline_stop_event,
            progress_tracker=progress_tracker,
        )
        target_sequence = [
            target_languages[((start_sentence + idx) - start_sentence) % len(target_languages)]
            for idx in range(total_refined)
        ] if target_languages else ["" for _ in range(total_refined)]
        translation_thread = translation_engine.start_translation_pipeline(
            selected_sentences,
            input_language,
            target_sequence,
            start_sentence=start_sentence,
            output_queue=translation_queue,
            consumer_count=len(media_threads) or 1,
            stop_event=pipeline_stop_event,
            max_workers=worker_count,
            progress_tracker=progress_tracker,
        )
        buffered_results = {}
        next_index = 0
        try:
            while processed < total_refined:
                if pipeline_stop_event.is_set() and not buffered_results:
                    break
                try:
                    media_item = media_queue.get(timeout=0.1)
                except queue.Empty:
                    if pipeline_stop_event.is_set():
                        break
                    continue
                if media_item is None:
                    continue
                buffered_results[media_item.index] = media_item
                while next_index in buffered_results:
                    item = buffered_results.pop(next_index)
                    fluent = remove_quotes(item.translation or "")
                    should_transliterate = (
                        include_transliteration and item.target_language in NON_LATIN_LANGUAGES
                    )
                    transliteration_result = ""
                    if should_transliterate:
                        transliteration_result = transliterate_sentence(
                            fluent, item.target_language
                        )
                        transliteration_result = remove_quotes(transliteration_result)
                    written_block, video_block = _build_written_and_video_blocks(
                        sentence_number=item.sentence_number,
                        sentence=item.sentence,
                        fluent=fluent,
                        transliteration=transliteration_result,
                        current_target=item.target_language,
                        written_mode=written_mode,
                        total_sentences=total_fully,
                        include_transliteration=should_transliterate,
                    )
                    written_blocks.append(written_block)
                    if generate_video:
                        video_blocks.append(video_block)
                    if generate_audio and current_audio is not None and all_audio_segments is not None:
                        segment = item.audio_segment or AudioSegment.silent(duration=0)
                        current_audio.append(segment)
                        all_audio_segments.append(segment)
                    if (
                        (item.sentence_number - start_sentence + 1) % sentences_per_file == 0
                        and not pipeline_stop_event.is_set()
                    ):
                        batch_start = current_batch_start
                        batch_end = item.sentence_number
                        future = finalize_executor.submit(
                            _export_pipeline_batch,
                            base_dir=base_dir,
                            base_no_ext=base_no_ext,
                            batch_start=batch_start,
                            batch_end=batch_end,
                            written_blocks=written_blocks,
                            target_language=item.target_language or last_target_language,
                            output_html=output_html,
                            output_pdf=output_pdf,
                            generate_audio=generate_audio,
                            audio_segments=current_audio or [],
                            generate_video=generate_video,
                            video_blocks=video_blocks,
                            cover_img=cover_img,
                            book_author=book_author,
                            book_title=book_title,
                            global_cumulative_word_counts=global_cumulative_word_counts,
                            total_book_words=total_book_words,
                            macos_reading_speed=MACOS_READING_SPEED,
                            input_language=input_language,
                            total_sentences=total_fully,
                            tempo=TEMPO,
                            sync_ratio=SYNC_RATIO,
                            word_highlighting=WORD_HIGHLIGHTING,
                        )
                        export_futures.append(future)
                        written_blocks = []
                        video_blocks = []
                        if generate_audio:
                            current_audio = []
                        current_batch_start = item.sentence_number + 1
                    last_target_language = item.target_language
                    processed += 1
                    next_index += 1
                if pipeline_stop_event.is_set() and not buffered_results:
                    break
        except KeyboardInterrupt:
            logger.warning("Processing interrupted by user; shutting down pipeline...")
            pipeline_stop_event.set()
        finally:
            if not pipeline_stop_event.is_set():
                pipeline_stop_event.set()
            for worker in media_threads:
                worker.join(timeout=1.0)
            if translation_thread is not None:
                translation_thread.join(timeout=1.0)
            if finalize_executor is not None:
                finalize_executor.shutdown(wait=True)
                for future in export_futures:
                    try:
                        video_path = future.result()
                    except Exception as exc:  # pragma: no cover - defensive logging
                        logger.error("Failed to finalize batch export: %s", exc)
                    else:
                        if video_path:
                            batch_video_files.append(video_path)

    if written_blocks and not (stop_event and stop_event.is_set()):
        batch_start = current_batch_start
        batch_end = current_batch_start + len(written_blocks) - 1
        target_for_batch = last_target_language or (
            target_languages[0] if target_languages else ""
        )
        video_path = _export_pipeline_batch(
            base_dir=base_dir,
            base_no_ext=base_no_ext,
            batch_start=batch_start,
            batch_end=batch_end,
            written_blocks=written_blocks,
            target_language=target_for_batch,
            output_html=output_html,
            output_pdf=output_pdf,
            generate_audio=generate_audio,
            audio_segments=current_audio or [],
            generate_video=generate_video,
            video_blocks=video_blocks,
            cover_img=cover_img,
            book_author=book_author,
            book_title=book_title,
            global_cumulative_word_counts=global_cumulative_word_counts,
            total_book_words=total_book_words,
            macos_reading_speed=MACOS_READING_SPEED,
            input_language=input_language,
            total_sentences=total_fully,
            tempo=TEMPO,
            sync_ratio=SYNC_RATIO,
            word_highlighting=WORD_HIGHLIGHTING,
        )
        if video_path:
            batch_video_files.append(video_path)
    elif stop_event and stop_event.is_set():
        logger.info("Skip final batch export due to shutdown request.")
    logger.info("EPUB processing complete!")
    logger.info("Total sentences processed: %s", total_refined)
    return written_blocks, all_audio_segments, batch_video_files, base_dir, base_no_ext

# -----------------------
# Interactive Menu with Grouped Options and Dynamic Summary
# -----------------------
def run_pipeline(
    *,
    progress_tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
):
    """Entry point for executing the ebook processing pipeline."""
    global OLLAMA_MODEL, DEBUG, SELECTED_VOICE, MAX_WORDS, EXTEND_SPLIT_WITH_COMMA_SEMICOLON
    global MACOS_READING_SPEED, SYNC_RATIO, WORD_HIGHLIGHTING, TEMPO

    args = parse_arguments()

    overrides = {
        "ebooks_dir": args.ebooks_dir or os.environ.get("EBOOKS_DIR"),
        "working_dir": args.working_dir or os.environ.get("EBOOK_WORKING_DIR"),
        "output_dir": args.output_dir or os.environ.get("EBOOK_OUTPUT_DIR"),
        "tmp_dir": args.tmp_dir or os.environ.get("EBOOK_TMP_DIR"),
        "ffmpeg_path": args.ffmpeg_path or os.environ.get("FFMPEG_PATH"),
        "ollama_url": args.ollama_url or os.environ.get("OLLAMA_URL"),
        "thread_count": args.thread_count or os.environ.get("EBOOK_THREAD_COUNT"),
    }

    if args.interactive:
        config, interactive_results = run_interactive_menu(
            overrides,
            args.config,
            entry_script_name=ENTRY_SCRIPT_NAME,
        )
        (
            input_file,
            base_output_file,
            input_language,
            target_languages,
            sentences_per_output_file,
            start_sentence,
            end_sentence,
            stitch_full,
            generate_audio,
            audio_mode,
            written_mode,
            selected_voice,
            output_html,
            output_pdf,
            generate_video,
            include_transliteration,
            tempo,
            book_metadata,
        ) = interactive_results
        SELECTED_VOICE = config.get("selected_voice", selected_voice)
        TEMPO = config.get("tempo", tempo)
        OLLAMA_MODEL = config.get("ollama_model", DEFAULT_MODEL)
        DEBUG = config.get("debug", False)
        MAX_WORDS = config.get("max_words", DEFAULT_MAX_WORDS)
        EXTEND_SPLIT_WITH_COMMA_SEMICOLON = config.get(
            "split_on_comma_semicolon",
            DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
        )
        MACOS_READING_SPEED = config.get("macos_reading_speed", 100)
        SYNC_RATIO = config.get("sync_ratio", 0.9)
        WORD_HIGHLIGHTING = config.get("word_highlighting", True)
        cfg.set_thread_count(config.get("thread_count"))
        translation_engine.set_model(OLLAMA_MODEL)
        translation_engine.set_debug(DEBUG)
        configure_logging_level(DEBUG)
    else:
        config = load_configuration(args.config, verbose=False)
        initialize_environment(config, overrides)
        config = update_book_cover_file_in_config(
            config,
            config.get("ebooks_dir"),
            debug_enabled=config.get("debug", False),
        )

        input_file = args.input_file or config.get("input_file")
        if not input_file:
            logger.error("Error: An input EPUB file must be specified either via CLI or configuration.")
            sys.exit(1)

        resolved_input_path = resolve_file_path(input_file, cfg.BOOKS_DIR)
        if not resolved_input_path or not resolved_input_path.exists():
            search_hint = cfg.BOOKS_DIR or config.get("ebooks_dir")
            logger.error(
                "Error: EPUB file '%s' was not found. Check the ebooks directory (%s).",
                input_file,
                search_hint,
            )
            sys.exit(1)
        input_file = str(resolved_input_path)

        input_language = args.input_language or config.get("input_language", "English")
        target_languages = config.get("target_languages", ["Arabic"])
        if args.target_languages:
            target_languages = [x.strip() for x in args.target_languages.split(",") if x.strip()]
        if not target_languages:
            target_languages = ["Arabic"]

        sentences_per_output_file = args.sentences_per_output_file or config.get("sentences_per_output_file", 10)

        base_output_file = args.base_output_file or config.get("base_output_file")
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        target_lang_str = "_".join(target_languages)
        if base_output_file:
            resolved_base = resolve_file_path(base_output_file, cfg.EBOOK_DIR)
            os.makedirs(resolved_base.parent, exist_ok=True)
            base_output_file = str(resolved_base)
        else:
            output_folder = os.path.join(cfg.EBOOK_DIR, f"{target_lang_str}_{base_name}")
            os.makedirs(output_folder, exist_ok=True)
            base_output_file = os.path.join(output_folder, f"{target_lang_str}_{base_name}.html")

        start_sentence = args.start_sentence if args.start_sentence is not None else config.get("start_sentence", 1)
        try:
            start_sentence = int(start_sentence)
        except (TypeError, ValueError):
            start_sentence = 1

        end_sentence = None
        end_arg = args.end_sentence if args.end_sentence is not None else config.get("end_sentence")
        if isinstance(end_arg, str):
            end_arg = end_arg.strip()
            if end_arg.startswith("+") or end_arg.startswith("-"):
                try:
                    end_sentence = start_sentence + int(end_arg)
                except ValueError:
                    end_sentence = None
            elif end_arg.isdigit():
                end_sentence = int(end_arg)
        elif isinstance(end_arg, int):
            end_sentence = end_arg

        stitch_full = config.get("stitch_full", False)
        generate_audio = config.get("generate_audio", True)
        audio_mode = config.get("audio_mode", "1")
        written_mode = config.get("written_mode", "4")
        SELECTED_VOICE = config.get("selected_voice", "gTTS")
        output_html = config.get("output_html", True)
        output_pdf = config.get("output_pdf", False)
        generate_video = config.get("generate_video", False)
        include_transliteration = config.get("include_transliteration", False)
        TEMPO = config.get("tempo", 1.0)
        book_metadata = {
            "book_title": config.get("book_title"),
            "book_author": config.get("book_author"),
            "book_year": config.get("book_year"),
            "book_summary": config.get("book_summary"),
            "book_cover_file": config.get("book_cover_file"),
        }

        if args.debug:
            config["debug"] = True

        OLLAMA_MODEL = config.get("ollama_model", DEFAULT_MODEL)
        translation_engine.set_model(OLLAMA_MODEL)
        DEBUG = config.get("debug", False)
        translation_engine.set_debug(DEBUG)
        configure_logging_level(DEBUG)
        MAX_WORDS = config.get("max_words", 18)
        EXTEND_SPLIT_WITH_COMMA_SEMICOLON = config.get("split_on_comma_semicolon", False)
        MACOS_READING_SPEED = config.get("macos_reading_speed", 100)
        SYNC_RATIO = config.get("sync_ratio", 0.9)
        WORD_HIGHLIGHTING = config.get("word_highlighting", True)

    try:
        logger.info("Starting EPUB processing...")
        logger.info("Input file: %s", input_file)
        logger.info("Base output file: %s", base_output_file)
        logger.info("Input language: %s", input_language)
        logger.info("Target languages: %s", ", ".join(target_languages))
        logger.info("Sentences per output file: %s", sentences_per_output_file)
        logger.info("Starting from sentence: %s", start_sentence)
        if end_sentence is not None:
            logger.info("Ending at sentence: %s", end_sentence)
        else:
            logger.info("Processing until end of file")

        refined_list, refined_updated = get_refined_sentences(
            input_file,
            force_refresh=True,
            metadata={
                "mode": "cli",
                "target_languages": target_languages,
                "max_words": MAX_WORDS,
            },
        )
        if refined_updated:
            refined_output_path = refined_list_output_path(input_file)
            logger.info("Refined sentence list written to: %s", refined_output_path)
        (
            written_blocks,
            all_audio_segments,
            batch_video_files,
            base_dir,
            base_no_ext,
        ) = process_epub(
            input_file,
            base_output_file,
            input_language,
            target_languages,
            sentences_per_output_file,
            start_sentence,
            end_sentence,
            generate_audio,
            audio_mode,
            written_mode,
            output_html,
            output_pdf,
            refined_list=refined_list,
            generate_video=generate_video,
            include_transliteration=include_transliteration,
            book_metadata=book_metadata,
            progress_tracker=progress_tracker,
            stop_event=stop_event,
        )
        if stop_event and stop_event.is_set():
            logger.info("Shutdown request acknowledged; skipping remaining post-processing steps.")
        if stitch_full and not (stop_event and stop_event.is_set()):
            final_sentence = start_sentence + len(written_blocks) - 1 if written_blocks else start_sentence
            stitched_basename = output_formatter.compute_stitched_basename(input_file, target_languages)
            output_formatter.stitch_full_output(
                base_dir,
                start_sentence,
                final_sentence,
                stitched_basename,
                written_blocks,
                target_languages[0],
                output_html=output_html,
                output_pdf=output_pdf,
                epub_title=f"Stitched Translation: {start_sentence}-{final_sentence} {stitched_basename}",
            )
            if generate_audio and all_audio_segments:
                stitched_audio = AudioSegment.empty()
                for seg in all_audio_segments:
                    stitched_audio += seg
                stitched_audio_filename = os.path.join(
                    base_dir,
                    f"{start_sentence}-{final_sentence}_{stitched_basename}.mp3",
                )
                stitched_audio.export(stitched_audio_filename, format="mp3", bitrate="320k")
            if generate_video and batch_video_files:
                logger.info(
                    "Generating stitched video slide output by concatenating batch video files..."
                )
                concat_list_path = os.path.join(
                    base_dir, f"concat_full_{stitched_basename}.txt"
                )
                with open(concat_list_path, "w", encoding="utf-8") as f:
                    for video_file in batch_video_files:
                        f.write(f"file '{video_file}'\n")
                final_video_path = os.path.join(
                    base_dir,
                    f"{start_sentence}-{final_sentence}_{stitched_basename}_stitched.mp4",
                )
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
                subprocess.run(cmd_concat, check=True)
                os.remove(concat_list_path)
                logger.info("Stitched video slide output saved to: %s", final_video_path)
        elif stitch_full and stop_event and stop_event.is_set():
            logger.info("Skipping stitched outputs due to shutdown request.")
        logger.info("Processing complete.")
    except Exception as e:
        logger.error("An error occurred: %s", e)


if __name__ == "__main__":
    run_pipeline()
