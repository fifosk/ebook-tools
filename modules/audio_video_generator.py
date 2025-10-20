"""Utilities for generating audio and video artifacts."""

import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from queue import Empty, Full, Queue
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, TYPE_CHECKING

from pydub import AudioSegment
from PIL import Image

from modules.audio.highlight import (
    HighlightEvent,
    _build_events_from_metadata,
    _build_legacy_highlight_events,
    _compute_audio_highlight_metadata,
    _get_audio_metadata,
    _store_audio_metadata,
)
from modules.audio.tts import synthesize_segment
from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules import output_formatter
from modules.translation_engine import TranslationTask
from modules.video.slides import build_sentence_video

if TYPE_CHECKING:
    from modules.progress_tracker import ProgressTracker
logger = log_mgr.logger

@dataclass(slots=True)
class MediaPipelineResult:
    """Result produced by the media generation workers."""

    index: int
    sentence_number: int
    sentence: str
    target_language: str
    translation: str
    audio_segment: Optional[AudioSegment]


def _parse_sentence_block(block: str) -> Tuple[str, str, str, str]:
    """Extract header and text segments from a sentence block."""

    raw_lines = block.split("\n")
    header_line = raw_lines[0] if raw_lines else ""
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
    return header_line, original_seg, translation_seg, transliteration_seg


def _assemble_highlight_timeline(
    block: str,
    audio_seg: AudioSegment,
    *,
    sync_ratio: float,
    word_highlighting: bool,
    highlight_granularity: str,
) -> Tuple[List[HighlightEvent], str]:
    """Generate slide highlight events and determine effective granularity."""

    header_line, original_seg, translation_seg, transliteration_seg = _parse_sentence_block(
        block
    )
    original_words = original_seg.split()
    if "Chinese" in header_line or "Japanese" in header_line:
        translation_units: Sequence[str] = list(translation_seg)
    else:
        translation_units = translation_seg.split() or [translation_seg]
    transliteration_words = transliteration_seg.split()

    num_original_words = len(original_words)
    num_translation_words = len(translation_units)
    num_translit_words = len(transliteration_words)

    audio_duration = audio_seg.duration_seconds
    metadata = _get_audio_metadata(audio_seg)

    events: List[HighlightEvent]
    metadata_has_char = False

    if not word_highlighting:
        events = [
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
            metadata_has_char = any(
                event.step is not None
                and event.step.char_index_start is not None
                and event.step.char_index_end is not None
                for event in generated
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

    events = [event for event in events if event.duration > 0]
    if not events:
        events = [
            HighlightEvent(
                duration=max(audio_duration * sync_ratio, 0.0),
                original_index=num_original_words,
                translation_index=num_translation_words,
                transliteration_index=num_translit_words,
            )
        ]

    effective_granularity = (
        "char" if highlight_granularity == "char" and metadata_has_char else "word"
    )
    if not word_highlighting:
        effective_granularity = "word"

    return events, effective_granularity


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def change_audio_tempo(sound: AudioSegment, tempo: float = 1.0) -> AudioSegment:
    """Adjust the tempo of an ``AudioSegment`` by modifying its frame rate."""
    if tempo == 1.0:
        return sound
    new_frame_rate = int(sound.frame_rate * tempo)
    return sound._spawn(sound.raw_data, overrides={"frame_rate": new_frame_rate}).set_frame_rate(sound.frame_rate)


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
    segment_texts: Dict[str, str] = {}

    def enqueue(key: str, text: str, lang_code: str) -> None:
        tasks.append((key, text, lang_code))
        segment_texts[key] = text

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
            segments[key] = synthesize_segment(text, lang_code, selected_voice, macos_reading_speed)
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(synthesize_segment, text, lang_code, selected_voice, macos_reading_speed): key
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

    tempo_adjusted = change_audio_tempo(audio, tempo)
    try:
        metadata = _compute_audio_highlight_metadata(
            tempo_adjusted, sequence, segments, tempo, segment_texts
        )
        _store_audio_metadata(tempo_adjusted, metadata)
    except Exception:  # pragma: no cover - metadata attachment best effort
        logger.debug("Failed to compute audio metadata for sentence %s", sentence_number)

    return tempo_adjusted


def _media_worker(
    name: str,
    task_queue: Queue[Optional[TranslationTask]],
    result_queue: Queue[Optional[MediaPipelineResult]],
    *,
    total_sentences: int,
    input_language: str,
    audio_mode: str,
    language_codes: Mapping[str, str],
    selected_voice: str,
    tempo: float,
    macos_reading_speed: int,
    generate_audio: bool,
    stop_event: Optional[threading.Event] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
) -> None:
    """Consume translation results and emit completed media payloads."""

    while True:
        if stop_event and stop_event.is_set():
            break
        try:
            task = task_queue.get(timeout=0.1)
        except Empty:
            continue
        if task is None:
            task_queue.task_done()
            break
        start_time = time.perf_counter()
        audio_segment: Optional[AudioSegment] = None
        try:
            if generate_audio:
                audio_segment = generate_audio_for_sentence(
                    task.sentence_number,
                    task.sentence,
                    task.translation,
                    input_language,
                    task.target_language,
                    audio_mode,
                    total_sentences,
                    language_codes,
                    selected_voice,
                    tempo,
                    macos_reading_speed,
                )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Consumer %s failed for sentence %s: %s", name, task.sentence_number, exc
            )
            if generate_audio:
                audio_segment = AudioSegment.silent(duration=0)
        finally:
            task_queue.task_done()
        elapsed = time.perf_counter() - start_time
        logger.debug(
            "Consumer %s processed sentence %s in %.3fs",
            name,
            task.sentence_number,
            elapsed,
        )
        payload = MediaPipelineResult(
            index=task.index,
            sentence_number=task.sentence_number,
            sentence=task.sentence,
            target_language=task.target_language,
            translation=task.translation,
            audio_segment=audio_segment,
        )
        while True:
            if stop_event and stop_event.is_set():
                break
            try:
                result_queue.put(payload, timeout=0.1)
                if progress_tracker:
                    progress_tracker.record_media_completion(
                        payload.index, payload.sentence_number
                    )
                break
            except Full:
                continue


def start_media_pipeline(
    task_queue: Queue[Optional[TranslationTask]],
    *,
    worker_count: Optional[int] = None,
    total_sentences: int,
    input_language: str,
    audio_mode: str,
    language_codes: Mapping[str, str],
    selected_voice: str,
    tempo: float,
    macos_reading_speed: int,
    generate_audio: bool,
    queue_size: Optional[int] = None,
    stop_event: Optional[threading.Event] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
) -> Tuple[Queue[Optional[MediaPipelineResult]], List[threading.Thread]]:
    """Start consumer threads that transform translations into media artifacts."""

    worker_total = worker_count or cfg.get_thread_count()
    worker_total = max(1, worker_total)
    result_queue: Queue[Optional[MediaPipelineResult]] = Queue(maxsize=queue_size or 0)
    stop_event = stop_event or threading.Event()
    workers: List[threading.Thread] = []
    active_context = cfg.get_runtime_context(None)

    def _thread_target(*args, **kwargs) -> None:
        if active_context is not None:
            cfg.set_runtime_context(active_context)
        try:
            _media_worker(*args, **kwargs)
        finally:
            if active_context is not None:
                cfg.clear_runtime_context()

    for idx in range(worker_total):
        thread_name = f"Consumer-{idx + 1}"
        thread = threading.Thread(
            target=_thread_target,
            name=thread_name,
            args=(
                thread_name,
                task_queue,
                result_queue,
            ),
            kwargs={
                "total_sentences": total_sentences,
                "input_language": input_language,
                "audio_mode": audio_mode,
                "language_codes": language_codes,
                "selected_voice": selected_voice,
                "tempo": tempo,
                "macos_reading_speed": macos_reading_speed,
                "generate_audio": generate_audio,
                "stop_event": stop_event,
                "progress_tracker": progress_tracker,
            },
            daemon=True,
        )
        thread.start()
        workers.append(thread)
    return result_queue, workers


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
    highlight_granularity: str,
    cleanup: bool = True,
    slide_size: Sequence[int] = (1280, 720),
    initial_font_size: int = 60,
    bg_color: Sequence[int] = (0, 0, 0),
) -> str:
    """Stitch sentence-level videos together for a batch of slides."""

    logger.info("Generating video slide set for sentences %s to %s...", batch_start, batch_end)
    sentence_video_files: List[str] = []
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

        highlight_events, effective_granularity = _assemble_highlight_timeline(
            block,
            audio_seg,
            sync_ratio=sync_ratio,
            word_highlighting=word_highlighting,
            highlight_granularity=highlight_granularity,
        )

        return build_sentence_video(
            block,
            audio_seg,
            sentence_number,
            sync_ratio=sync_ratio,
            word_highlighting=word_highlighting,
            highlight_events=highlight_events,
            highlight_granularity=effective_granularity,
            slide_size=slide_size,
            initial_font_size=initial_font_size,
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

    range_fragment = output_formatter.format_sentence_range(
        batch_start, batch_end, total_sentences
    )
    concat_list_path = os.path.join(output_dir, f"concat_{range_fragment}.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for video_file in sentence_video_files:
            f.write(f"file '{video_file}'\n")

    final_video_path = os.path.join(output_dir, f"{range_fragment}_{base_no_ext}.mp4")
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
    "generate_video_slides_ffmpeg",
]
