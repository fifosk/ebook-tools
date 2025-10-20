from __future__ import annotations

import concurrent.futures
import os
import queue
import threading
from typing import List, Optional, Tuple

from PIL import Image, ImageFont
from pydub import AudioSegment

from .. import audio_video_generator as av_gen
from .. import output_formatter
from ..config_manager import resolve_file_path
from ..llm_client import create_client
from ..epub_parser import remove_quotes
from ..logging_manager import console_info, console_warning, logger
from ..book_cover import fetch_book_cover
from ..progress_tracker import ProgressTracker
from .config import PipelineConfig
from .translation import (
    build_target_sequence,
    create_translation_queue,
    start_translation_pipeline,
    translate_batch,
    transliterate_sentence,
    TranslationWorkerPool,
)


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
    "Persian": "fa",
}

NON_LATIN_LANGUAGES = {
    "Arabic",
    "Armenian",
    "Chinese (Simplified)",
    "Chinese (Traditional)",
    "Hebrew",
    "Japanese",
    "Korean",
    "Russian",
    "Thai",
    "Greek",
    "Hindi",
    "Bengali",
    "Tamil",
    "Telugu",
    "Gujarati",
    "Persian",
}


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
) -> Tuple[str, str]:
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
        video_block = f"{header}{sentence}\n\n{fluent}\n{transliteration}\n"
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


def adjust_font_and_wrap_text(
    text,
    draw,
    slide_size,
    initial_font_size,
    font_path="Arial.ttf",
    max_width_fraction=0.9,
    max_height_fraction=0.9,
):
    max_width = slide_size[0] * max_width_fraction
    max_height = slide_size[1] * max_height_fraction
    font_size = int(initial_font_size * 0.85)  # Reduce font size by 15%
    while font_size > 10:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            font = ImageFont.load_default()
        wrapped_text = wrap_text(text, draw, font, max_width)
        total_height = sum(
            (
                draw.textbbox((0, 0), line, font=font)[3]
                - draw.textbbox((0, 0), line, font=font)[1]
            )
            for line in wrapped_text.split("\n")
        )
        if total_height <= max_height:
            return wrapped_text, font
        font_size -= 2
    return wrapped_text, font


def adjust_font_for_three_segments(
    seg1,
    seg2,
    seg3,
    draw,
    slide_size,
    initial_font_size,
    font_path="Arial.ttf",
    max_width_fraction=0.9,
    max_height_fraction=0.9,
    spacing=10,
):
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
                total_height += (
                    draw.textbbox((0, 0), line, font=font)[3]
                    - draw.textbbox((0, 0), line, font=font)[1]
                )
        total_height += 2 * spacing
        if total_height <= max_height:
            return wrapped1, wrapped2, wrapped3, font
        font_size -= 2
    return wrapped1, wrapped2, wrapped3, font


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
        range_fragment = output_formatter.format_sentence_range(
            batch_start, batch_end, total_sentences
        )

        output_formatter.export_batch_documents(
            base_dir,
            base_no_ext,
            batch_start,
            batch_end,
            list(written_blocks),
            target_language,
            total_sentences,
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
                base_dir, f"{range_fragment}_{base_no_ext}.mp3"
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
                pipeline_config.highlight_granularity,
            )
        return video_path
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to export batch %s-%s: %s", batch_start, batch_end, exc)
        raise


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
    book_metadata=None,
    *,
    pipeline_config: PipelineConfig,
    progress_tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
    translation_pool: Optional[TranslationWorkerPool] = None,
):
    """Process an EPUB file and generate the requested outputs."""

    if book_metadata is None:
        book_metadata = {}

    console_info("Extracting text from '%s'...", input_file, logger_obj=logger)
    total_fully = len(refined_list)
    console_info("Total fully split sentences extracted: %s", total_fully, logger_obj=logger)
    start_idx = max(start_sentence - 1, 0)
    end_idx = end_sentence if (end_sentence is not None and end_sentence <= total_fully) else total_fully
    selected_sentences = refined_list[start_idx:end_idx]
    total_refined = len(selected_sentences)
    console_info(
        "Processing %s sentences starting from refined sentence #%s",
        total_refined,
        start_sentence,
        logger_obj=logger,
    )
    if progress_tracker is not None:
        progress_tracker.set_total(total_refined)

    src_code = LANGUAGE_CODES.get(input_language, "XX").upper()
    tgt_code = LANGUAGE_CODES.get(target_languages[0], "XX").upper() if target_languages else "XX"

    base_dir, base_no_ext, base_output_file = output_formatter.prepare_output_directory(
        input_file,
        book_metadata.get("book_author"),
        book_metadata.get("book_title"),
        src_code,
        tgt_code,
        context=pipeline_config.context,
    )

    book_title = book_metadata.get("book_title", "Unknown Title")
    book_author = book_metadata.get("book_author", "Unknown Author")

    cover_img = None
    cover_file_path = resolve_file_path(
        book_metadata.get("book_cover_file"), pipeline_config.books_dir
    )
    if cover_file_path and cover_file_path.exists():
        try:
            with Image.open(cover_file_path) as img:
                cover_img = img.convert("RGB")
                cover_img.load()
        except Exception as exc:
            logger.debug("Error loading cover image from file: %s", exc)
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
                except Exception:
                    pass

    global_cumulative_word_counts: List[int] = []
    running = 0
    for sentence in refined_list:
        running += len(sentence.split())
        global_cumulative_word_counts.append(running)
    total_book_words = running

    written_blocks: List[str] = []
    video_blocks: List[str] = []
    all_audio_segments: Optional[List[AudioSegment]] = [] if generate_audio else None
    batch_video_files: List[str] = []
    current_audio: Optional[List[AudioSegment]] = [] if generate_audio else None
    current_batch_start = start_sentence
    processed = 0
    last_target_language = target_languages[0] if target_languages else ""
    pipeline_enabled = pipeline_config.pipeline_enabled
    queue_size = pipeline_config.queue_size
    worker_count = max(1, pipeline_config.thread_count)
    translation_client = getattr(pipeline_config, "translation_client", None)
    if translation_client is None:
        translation_client = create_client(
            model=pipeline_config.ollama_model,
            api_url=pipeline_config.ollama_url,
            debug=pipeline_config.debug,
            api_key=pipeline_config.ollama_api_key,
        )
    translation_thread = None
    media_threads: List[threading.Thread] = []
    translation_queue = None
    media_queue = None
    finalize_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
    export_futures: List[concurrent.futures.Future] = []

    active_translation_pool: Optional[TranslationWorkerPool] = translation_pool
    own_translation_pool = active_translation_pool is None
    try:
        if active_translation_pool is None:
            active_translation_pool = TranslationWorkerPool(max_workers=worker_count)

        if not pipeline_enabled:
            batch_size = worker_count
            while processed < total_refined:
                if stop_event and stop_event.is_set():
                    console_info(
                        "Stop requested; halting remaining sequential processing.",
                        logger_obj=logger,
                    )
                    break
                batch_sentences = selected_sentences[processed : processed + batch_size]
                batch_sentence_numbers = [
                    start_sentence + processed + idx for idx in range(len(batch_sentences))
                ]
                batch_targets = [
                    target_languages[((number - start_sentence) % len(target_languages))]
                    for number in batch_sentence_numbers
                ] if target_languages else ["" for _ in range(len(batch_sentence_numbers))]
                translations = translate_batch(
                    batch_sentences,
                    input_language,
                    batch_targets,
                    include_transliteration=include_transliteration,
                    client=translation_client,
                    worker_pool=active_translation_pool,
                    max_workers=worker_count,
                )

                for (
                    sentence_number,
                    sentence,
                    current_target,
                    translation_result,
                ) in zip(
                    batch_sentence_numbers, batch_sentences, batch_targets, translations
                ):
                    if stop_event and stop_event.is_set():
                        break
                    fluent = remove_quotes(translation_result or "")
                    should_transliterate = (
                        include_transliteration and current_target in NON_LATIN_LANGUAGES
                    )
                    transliteration_result = ""
                    if should_transliterate:
                        transliteration_result = transliterate_sentence(
                            fluent, current_target, client=translation_client
                        )
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
                    if (
                        generate_audio
                        and current_audio is not None
                        and all_audio_segments is not None
                    ):
                        audio_seg = av_gen.generate_audio_for_sentence(
                            sentence_number,
                            sentence,
                            fluent,
                            input_language,
                            current_target,
                            audio_mode,
                            total_fully,
                            LANGUAGE_CODES,
                            pipeline_config.selected_voice,
                            pipeline_config.tempo,
                            pipeline_config.macos_reading_speed,
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
                            macos_reading_speed=pipeline_config.macos_reading_speed,
                            input_language=input_language,
                            total_sentences=total_fully,
                            tempo=pipeline_config.tempo,
                            sync_ratio=pipeline_config.sync_ratio,
                            word_highlighting=pipeline_config.word_highlighting,
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
                console_info(
                    "Stop requested; exiting pipeline early before media generation.",
                    logger_obj=logger,
                )
        else:
            pipeline_stop_event = stop_event or threading.Event()
            translation_queue = create_translation_queue(queue_size)
            finalize_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            media_queue, media_threads = av_gen.start_media_pipeline(
                translation_queue,
                worker_count=worker_count,
                total_sentences=total_fully,
                input_language=input_language,
                audio_mode=audio_mode,
                language_codes=LANGUAGE_CODES,
                selected_voice=pipeline_config.selected_voice,
                tempo=pipeline_config.tempo,
                macos_reading_speed=pipeline_config.macos_reading_speed,
                generate_audio=generate_audio,
                queue_size=queue_size,
                stop_event=pipeline_stop_event,
                progress_tracker=progress_tracker,
            )
            target_sequence = build_target_sequence(
                target_languages,
                total_refined,
                start_sentence=start_sentence,
            )
            translation_thread = start_translation_pipeline(
                selected_sentences,
                input_language,
                target_sequence,
                start_sentence=start_sentence,
                output_queue=translation_queue,
                consumer_count=len(media_threads) or 1,
                stop_event=pipeline_stop_event,
                worker_count=worker_count,
                progress_tracker=progress_tracker,
                client=translation_client,
                worker_pool=active_translation_pool,
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
                            include_transliteration
                            and item.target_language in NON_LATIN_LANGUAGES
                        )
                        transliteration_result = ""
                        if should_transliterate:
                            transliteration_result = transliterate_sentence(
                                fluent, item.target_language, client=translation_client
                            )
                            transliteration_result = remove_quotes(
                                transliteration_result
                            )
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
                        if (
                            generate_audio
                            and current_audio is not None
                            and all_audio_segments is not None
                        ):
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
                                macos_reading_speed=pipeline_config.macos_reading_speed,
                                input_language=input_language,
                                total_sentences=total_fully,
                                tempo=pipeline_config.tempo,
                                sync_ratio=pipeline_config.sync_ratio,
                                word_highlighting=pipeline_config.word_highlighting,
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
                console_warning(
                    "Processing interrupted by user; shutting down pipeline...",
                    logger_obj=logger,
                )
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
    finally:
        if active_translation_pool is not None and own_translation_pool:
            active_translation_pool.shutdown()
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
            macos_reading_speed=pipeline_config.macos_reading_speed,
            input_language=input_language,
            total_sentences=total_fully,
            tempo=pipeline_config.tempo,
            sync_ratio=pipeline_config.sync_ratio,
            word_highlighting=pipeline_config.word_highlighting,
        )
        if video_path:
            batch_video_files.append(video_path)
    elif stop_event and stop_event.is_set():
        console_info(
            "Skip final batch export due to shutdown request.",
            logger_obj=logger,
        )
    console_info("EPUB processing complete!", logger_obj=logger)
    console_info(
        "Total sentences processed: %s", total_refined, logger_obj=logger
    )
    return written_blocks, all_audio_segments, batch_video_files, base_dir, base_no_ext
