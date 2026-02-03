"""Processing helpers for the rendering pipeline."""

from __future__ import annotations

import concurrent.futures
import math
import queue
import threading
import time
from functools import partial
from typing import Any, Dict, Mapping, Optional, Sequence, List, TYPE_CHECKING

from pydub import AudioSegment

from modules import audio_video_generator as av_gen
from modules.render.backends import PollyAudioSynthesizer
from modules.epub_parser import remove_quotes
from modules import text_normalization as text_norm
from modules.logging_manager import console_info, console_warning, logger
from modules.core.translation import (
    ThreadWorkerPool,
    build_target_sequence,
    create_translation_queue,
    split_translation_and_transliteration,
    start_translation_pipeline,
    translate_batch,
    transliterate_sentence,
)
from modules.transliteration import TransliterationService
from modules.retry_annotations import is_failure_annotation
from modules.text import align_token_counts

from .blocks import build_written_and_video_blocks
from .constants import LANGUAGE_CODES, NON_LATIN_LANGUAGES
from .exporters import BatchExportRequest, BatchExportResult, BatchExporter
from .pipeline_image_state import _ImageGenerationState
from .pipeline_images import ImagePipelineCoordinator

if TYPE_CHECKING:  # pragma: no cover - typing only
    from modules.progress_tracker import ProgressTracker

    from .pipeline import PipelineState, RenderPipeline


def _resolve_first_flush_size(
    sentences_per_file: int, translation_batch_size: Optional[int]
) -> Optional[int]:
    if sentences_per_file <= 1 or translation_batch_size is None:
        return None
    try:
        batch_size = int(translation_batch_size)
    except (TypeError, ValueError):
        return None
    if batch_size <= 1 or batch_size >= sentences_per_file:
        return None
    return batch_size


def _resolve_media_batch_total(
    total_sentences: int,
    sentences_per_file: int,
    first_flush_size: Optional[int],
) -> int:
    total = max(0, int(total_sentences))
    if total == 0:
        return 0
    safe_sentences_per_file = max(1, int(sentences_per_file))
    if safe_sentences_per_file <= 1:
        return total
    if first_flush_size and 0 < first_flush_size < safe_sentences_per_file:
        if total <= first_flush_size:
            return 1
        remaining = total - first_flush_size
        return 1 + math.ceil(remaining / safe_sentences_per_file)
    return math.ceil(total / safe_sentences_per_file)


def _initialize_media_batch_progress(
    *,
    state: "PipelineState",
    total_refined: int,
    sentences_per_file: int,
    first_flush_size: Optional[int],
    progress_tracker: Optional["ProgressTracker"],
) -> None:
    batch_total = _resolve_media_batch_total(
        total_refined,
        sentences_per_file,
        first_flush_size,
    )
    state.media_batch_total = batch_total
    state.media_batch_completed = 0
    state.media_batch_items_total = max(0, int(total_refined))
    state.media_batch_items_completed = 0
    state.media_batch_size = max(1, int(sentences_per_file))
    state.media_batch_ids = set()
    if first_flush_size:
        state.media_batch_first_size = int(first_flush_size)
    if progress_tracker is None:
        return
    payload: Dict[str, object] = {
        "batch_size": state.media_batch_size,
        "batches_total": batch_total,
        "batches_completed": 0,
        "items_total": state.media_batch_items_total,
        "items_completed": 0,
        "last_updated": round(time.time(), 3),
    }
    if state.media_batch_first_size:
        payload["first_batch_size"] = state.media_batch_first_size
    progress_tracker.update_generated_files_metadata(
        {"media_batch_stats": payload}
    )



def process_sequential(
    self,
    *,
    state: PipelineState,
    exporter: BatchExporter,
    sentences: Sequence[str],
    total_refined: int,
    start_sentence: int,
    input_language: str,
    target_languages: Sequence[str],
    generate_audio: bool,
    generate_video: bool,
    audio_mode: str,
    written_mode: str,
    sentences_per_file: int,
    include_transliteration: bool,
    translation_provider: Optional[str],
    translation_batch_size: Optional[int],
    transliteration_mode: str,
    transliteration_client,
    output_html: bool,
    output_pdf: bool,
    translation_client,
    worker_pool: ThreadWorkerPool,
    worker_count: int,
    total_fully: int,
) -> None:
    batch_size = worker_count
    processed = 0
    first_flush_size = _resolve_first_flush_size(
        sentences_per_file, translation_batch_size
    )
    _initialize_media_batch_progress(
        state=state,
        total_refined=total_refined,
        sentences_per_file=sentences_per_file,
        first_flush_size=first_flush_size,
        progress_tracker=self._progress,
    )
    while processed < total_refined:
        if self._should_stop():
            console_info(
                "Stop requested; halting remaining sequential processing.",
                logger_obj=logger,
            )
            break
        batch_sentences = sentences[processed : processed + batch_size]
        batch_sentence_numbers = [
            start_sentence + processed + idx for idx in range(len(batch_sentences))
        ]
        batch_targets = (
            [
                target_languages[((number - start_sentence) % len(target_languages))]
                for number in batch_sentence_numbers
            ]
            if target_languages
            else ["" for _ in batch_sentence_numbers]
        )
        translations = translate_batch(
            batch_sentences,
            input_language,
            batch_targets,
            include_transliteration=include_transliteration,
            transliteration_mode=transliteration_mode,
            transliteration_client=transliteration_client,
            transliterator=self._transliterator,
            translation_provider=translation_provider,
            llm_batch_size=translation_batch_size,
            client=translation_client,
            worker_pool=worker_pool,
            max_workers=worker_count,
            progress_tracker=self._progress,
            sentence_numbers=batch_sentence_numbers,
        )

        for sentence_number, sentence, current_target, translation_result in zip(
            batch_sentence_numbers, batch_sentences, batch_targets, translations
        ):
            if self._should_stop():
                break
            fluent_candidate = text_norm.collapse_whitespace(
                remove_quotes(translation_result or "")
            )
            translation_failed = is_failure_annotation(fluent_candidate)
            fluent, inline_transliteration = split_translation_and_transliteration(
                fluent_candidate
            )
            fluent = text_norm.collapse_whitespace(fluent.strip())
            inline_transliteration = text_norm.collapse_whitespace(
                remove_quotes(inline_transliteration or "").strip()
            )
            if inline_transliteration and not text_norm.is_latin_heavy(inline_transliteration):
                inline_transliteration = ""

            should_transliterate = (
                include_transliteration
                and current_target in NON_LATIN_LANGUAGES
                and not translation_failed
            )
            transliteration_result = inline_transliteration
            if should_transliterate:
                candidate = text_norm.collapse_whitespace(
                    remove_quotes(inline_transliteration or "").strip()
                )
                if candidate and not text_norm.is_latin_heavy(candidate):
                    candidate = ""
                if not candidate:
                    candidate = transliterate_sentence(
                        fluent,
                        current_target,
                        client=transliteration_client,
                        transliterator=self._transliterator,
                        transliteration_mode=transliteration_mode,
                    )
                    candidate = remove_quotes(candidate or "").strip()
                if candidate:
                    transliteration_result = candidate
            # Apply token alignment for CJK languages
            if fluent and transliteration_result:
                _, aligned_translit, _ = align_token_counts(
                    fluent, transliteration_result, current_target
                )
                transliteration_result = aligned_translit
            audio_segment: Optional[AudioSegment] = None
            original_audio_segment: Optional[AudioSegment] = None
            voice_metadata: Optional[Mapping[str, Mapping[str, str]]] = None
            if generate_audio:
                audio_result = self._maybe_generate_audio(
                    sentence_number=sentence_number,
                    sentence=sentence,
                    fluent=fluent,
                    input_language=input_language,
                    target_language=current_target,
                    audio_mode=audio_mode,
                    total_sentences=total_fully,
                )
                if audio_result is not None:
                    raw_tracks = getattr(audio_result, "audio_tracks", None)
                    has_tracks = isinstance(raw_tracks, Mapping)
                    if has_tracks:
                        translation_track = raw_tracks.get("translation") or raw_tracks.get("trans")
                        original_track = raw_tracks.get("orig") or raw_tracks.get("original")
                        if isinstance(translation_track, AudioSegment):
                            audio_segment = translation_track
                        if isinstance(original_track, AudioSegment):
                            original_audio_segment = original_track
                    if audio_segment is None and not has_tracks:
                        audio_segment = audio_result.audio
                    voice_metadata = audio_result.voice_metadata
            self._handle_sentence(
                state=state,
                exporter=exporter,
                sentence_number=sentence_number,
                sentence=sentence,
                fluent=fluent,
                transliteration_result=transliteration_result,
                target_language=current_target,
                sentences_per_file=sentences_per_file,
                written_mode=written_mode,
                total_sentences=total_fully,
                include_transliteration=(
                    should_transliterate and bool(transliteration_result)
                ),
                output_html=output_html,
                output_pdf=output_pdf,
                generate_audio=generate_audio,
                generate_video=generate_video,
                audio_segment=audio_segment,
                original_audio_segment=original_audio_segment,
                voice_metadata=voice_metadata,
                first_flush_size=first_flush_size,
                first_batch_start=start_sentence,
            )
            processed += 1


def process_pipeline(
    self,
    *,
    state: PipelineState,
    exporter: BatchExporter,
    base_dir: str,
    base_name: str,
    book_metadata: Mapping[str, Any],
    full_sentences: Sequence[str],
    sentences: Sequence[str],
    start_sentence: int,
    total_refined: int,
    input_language: str,
    target_languages: Sequence[str],
    generate_audio: bool,
    generate_video: bool,
    generate_images: bool,
    audio_mode: str,
    written_mode: str,
    sentences_per_file: int,
    include_transliteration: bool,
    translation_provider: Optional[str],
    translation_batch_size: Optional[int],
    transliteration_mode: str,
    transliteration_client,
    output_html: bool,
    output_pdf: bool,
    translation_client,
    worker_pool: ThreadWorkerPool,
    worker_count: int,
    total_fully: int,
    media_orchestrator_cls,
) -> None:
    pipeline_stop_event = self._stop_event or threading.Event()
    translation_queue = create_translation_queue(self._config.queue_size)
    finalize_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    audio_synthesizer = PollyAudioSynthesizer(
        base_url=self._config.audio_api_base_url,
        timeout=self._config.audio_api_timeout_seconds,
        poll_interval=self._config.audio_api_poll_interval_seconds,
    )
    media_orchestrator = media_orchestrator_cls(
        translation_queue,
        worker_count=worker_count,
        total_sentences=total_fully,
        input_language=input_language,
        audio_mode=audio_mode,
        language_codes=LANGUAGE_CODES,
        selected_voice=self._config.selected_voice,
        voice_overrides=self._config.voice_overrides,
        tempo=self._config.tempo,
        macos_reading_speed=self._config.macos_reading_speed,
        generate_audio=generate_audio,
        tts_backend=self._config.tts_backend,
        tts_executable_path=(
            self._config.tts_executable_path or self._config.say_path
        ),
        queue_size=self._config.queue_size,
        audio_stop_event=pipeline_stop_event,
        progress_tracker=self._progress,
        audio_synthesizer=audio_synthesizer,
        media_result_factory=av_gen.MediaPipelineResult,
    )
    media_queue, media_threads = media_orchestrator.start()

    image_pipeline = ImagePipelineCoordinator(
        config=self._config,
        progress=self._progress,
        state=state,
        base_dir=base_dir,
        base_name=base_name,
        book_metadata=book_metadata,
        full_sentences=full_sentences,
        sentences=sentences,
        start_sentence=start_sentence,
        total_refined=total_refined,
        total_fully=total_fully,
        sentences_per_file=sentences_per_file,
        generate_images=generate_images,
        stop_event=pipeline_stop_event,
    )

    first_flush_size = _resolve_first_flush_size(
        sentences_per_file, translation_batch_size
    )
    _initialize_media_batch_progress(
        state=state,
        total_refined=total_refined,
        sentences_per_file=sentences_per_file,
        first_flush_size=first_flush_size,
        progress_tracker=self._progress,
    )

    target_sequence = build_target_sequence(
        target_languages,
        total_refined,
        start_sentence=start_sentence,
    )
    translation_thread = start_translation_pipeline(
        sentences,
        input_language,
        target_sequence,
        start_sentence=start_sentence,
        output_queue=translation_queue,
        consumer_count=len(media_threads) or 1,
        stop_event=pipeline_stop_event,
        worker_count=worker_count,
        progress_tracker=self._progress,
        client=translation_client,
        worker_pool=worker_pool,
        transliterator=self._transliterator,
        translation_provider=translation_provider,
        transliteration_mode=transliteration_mode,
        transliteration_client=transliteration_client,
        include_transliteration=include_transliteration,
        llm_batch_size=translation_batch_size,
    )

    buffered_results = {}
    next_index = 0
    export_futures: List[concurrent.futures.Future] = []
    cancelled = False
    try:
        while state.processed < total_refined:
            image_pipeline.tick()
            if pipeline_stop_event.is_set() and not buffered_results:
                cancelled = state.processed < total_refined
                break
            try:
                media_item = media_queue.get(timeout=0.1)
            except queue.Empty:
                if pipeline_stop_event.is_set():
                    cancelled = state.processed < total_refined
                    break
                continue
            if media_item is None:
                continue
            buffered_results[media_item.index] = media_item
            while next_index in buffered_results:
                item = buffered_results.pop(next_index)
                fluent_candidate = text_norm.collapse_whitespace(
                    remove_quotes(item.translation or "")
                )
                translation_failed = is_failure_annotation(fluent_candidate)
                fluent, inline_transliteration = split_translation_and_transliteration(
                    fluent_candidate
                )
                fluent = text_norm.collapse_whitespace(fluent.strip())
                inline_transliteration = text_norm.collapse_whitespace(
                    remove_quotes(inline_transliteration or "").strip()
                )
                if inline_transliteration and not text_norm.is_latin_heavy(inline_transliteration):
                    inline_transliteration = ""
                should_transliterate = (
                    include_transliteration
                    and item.target_language in NON_LATIN_LANGUAGES
                    and not translation_failed
                )
                transliteration_result = inline_transliteration
                if should_transliterate:
                    candidate = text_norm.collapse_whitespace(
                        remove_quotes(
                            (item.transliteration or inline_transliteration or "")
                        ).strip()
                    )
                    if candidate and not text_norm.is_latin_heavy(candidate):
                        candidate = ""
                    if not candidate:
                        candidate = transliterate_sentence(
                            fluent,
                            item.target_language,
                            client=transliteration_client,
                            transliterator=self._transliterator,
                            transliteration_mode=transliteration_mode,
                        )
                        candidate = text_norm.collapse_whitespace(
                            remove_quotes(candidate or "").strip()
                        )
                    if candidate:
                        transliteration_result = candidate
                # Apply token alignment for CJK languages
                if fluent and transliteration_result:
                    _, aligned_translit, _ = align_token_counts(
                        fluent, transliteration_result, item.target_language
                    )
                    transliteration_result = aligned_translit
                audio_segment = None
                original_audio_segment: Optional[AudioSegment] = None
                if generate_audio:
                    raw_tracks = getattr(item, "audio_tracks", None)
                    if isinstance(raw_tracks, Mapping):
                        translation_track = raw_tracks.get("translation") or raw_tracks.get("trans")
                        original_track = raw_tracks.get("orig") or raw_tracks.get("original")
                        if isinstance(translation_track, AudioSegment):
                            audio_segment = translation_track
                        if isinstance(original_track, AudioSegment):
                            original_audio_segment = original_track
                    else:
                        audio_segment = item.audio_segment
                    if audio_segment is not None:
                        if state.current_audio_segments is not None:
                            state.current_audio_segments.append(audio_segment)
                        if state.all_audio_segments is not None:
                            state.all_audio_segments.append(audio_segment)
                    if original_audio_segment is not None:
                        if state.current_original_segments is not None:
                            state.current_original_segments.append(original_audio_segment)
                        if state.all_original_segments is not None:
                            state.all_original_segments.append(original_audio_segment)
                self._update_voice_metadata(state, getattr(item, "voice_metadata", None))
                written_block, video_block = build_written_and_video_blocks(
                    sentence_number=item.sentence_number,
                    sentence=item.sentence,
                    fluent=fluent,
                    transliteration=transliteration_result,
                    current_target=item.target_language,
                    written_mode=written_mode,
                    total_sentences=total_fully,
                    include_transliteration=(
                        should_transliterate and bool(transliteration_result)
                    ),
                )
                state.written_blocks.append(written_block)
                state.video_blocks.append(video_block)

                raw_metadata = getattr(item, "metadata", None)
                metadata_payload: Dict[str, Any]
                if isinstance(raw_metadata, Mapping):
                    metadata_payload = dict(raw_metadata)
                else:
                    metadata_payload = {}
                metadata_payload.setdefault("sentence_number", item.sentence_number)
                metadata_payload.setdefault("id", str(item.sentence_number))
                metadata_payload.setdefault(
                    "text",
                    metadata_payload.get("text")
                    or fluent
                    or transliteration_result
                    or item.sentence,
                )
                metadata_payload.setdefault("t0", 0.0)

                duration_val = None
                if "t1" in metadata_payload:
                    try:
                        duration_val = float(metadata_payload["t1"])
                    except (TypeError, ValueError):
                        duration_val = None
                if duration_val is None and audio_segment is not None:
                    try:
                        duration_val = float(audio_segment.duration_seconds)
                    except Exception:
                        duration_val = None
                if duration_val is None:
                    tokens = metadata_payload.get("word_tokens")
                    if isinstance(tokens, Sequence) and tokens:
                        last_token = tokens[-1]
                        try:
                            duration_val = float(last_token.get("end", 0.0))
                        except (TypeError, ValueError, AttributeError):
                            duration_val = None
                metadata_payload["t1"] = round(max(duration_val or 0.0, 0.0), 6)

                if audio_segment is not None and metadata_payload.get("word_tokens"):
                    try:
                        setattr(audio_segment, "word_tokens", metadata_payload["word_tokens"])
                    except Exception:
                        pass

                sentence_number = int(item.sentence_number)
                image_pipeline.decorate_metadata(
                    metadata_payload,
                    sentence_number=sentence_number,
                )

                state.current_sentence_metadata.append(metadata_payload)
                if state.all_sentence_metadata is not None:
                    state.all_sentence_metadata.append(metadata_payload)

                sentence_for_prompt = (
                    fluent
                    if (isinstance(fluent, str) and fluent.strip() and not translation_failed)
                    else item.sentence
                )

                image_pipeline.handle_sentence(
                    sentence_number=sentence_number,
                    sentence_for_prompt=str(sentence_for_prompt or "").strip(),
                    sentence_text=str(item.sentence or "").strip(),
                )

                sentences_in_chunk = item.sentence_number - state.current_batch_start + 1
                should_flush = (
                    sentences_in_chunk % sentences_per_file == 0
                ) and not pipeline_stop_event.is_set()
                if (
                    not should_flush
                    and first_flush_size
                    and state.current_batch_start == start_sentence
                    and sentences_in_chunk >= first_flush_size
                    and not pipeline_stop_event.is_set()
                ):
                    should_flush = True
                if should_flush:
                    audio_tracks: Dict[str, List[AudioSegment]] = {}
                    if state.current_original_segments:
                        audio_tracks["orig"] = list(state.current_original_segments)
                    if state.current_audio_segments:
                        audio_tracks["translation"] = list(state.current_audio_segments)
                    request = BatchExportRequest(
                        start_sentence=state.current_batch_start,
                        end_sentence=item.sentence_number,
                        written_blocks=list(state.written_blocks),
                        target_language=item.target_language or state.last_target_language,
                        output_html=output_html,
                        output_pdf=output_pdf,
                        generate_audio=generate_audio,
                        audio_segments=list(state.current_audio_segments or []),
                        audio_tracks=audio_tracks,
                        generate_video=generate_video,
                        video_blocks=list(state.video_blocks),
                        voice_metadata=self._drain_current_voice_metadata(state),
                        sentence_metadata=list(state.current_sentence_metadata),
                    )
                    future = finalize_executor.submit(exporter.export, request)
                    export_futures.append(future)
                    future.add_done_callback(
                        partial(self._handle_export_future_completion, state)
                    )
                    state.written_blocks.clear()
                    state.video_blocks.clear()
                    if state.current_audio_segments is not None:
                        state.current_audio_segments.clear()
                    if state.current_original_segments is not None:
                        state.current_original_segments.clear()
                    state.current_sentence_metadata.clear()
                    state.current_batch_start = item.sentence_number + 1
                state.last_target_language = item.target_language or state.last_target_language
                state.processed += 1
                if self._progress is not None:
                    self._progress.record_media_completion(
                        state.processed - 1, item.sentence_number
                    )
                next_index += 1
            if pipeline_stop_event.is_set() and not buffered_results:
                break

        image_pipeline.finalize_pending()
    except KeyboardInterrupt:
        console_warning(
            "Processing interrupted by user; shutting down pipeline...",
            logger_obj=logger,
        )
        cancelled = True
        pipeline_stop_event.set()
    finally:
        # Only set stop_event if we were actually cancelled, not on normal completion
        # This allows post-processing phases (like lookup_cache) to run
        if cancelled:
            pipeline_stop_event.set()
        for worker in media_threads:
            worker.join(timeout=1.0)
        if translation_thread is not None:
            translation_thread.join(timeout=1.0)
        finalize_executor.shutdown(wait=True)
        for future in export_futures:
            try:
                export_result = future.result()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Failed to finalize batch export: %s", exc)
            else:
                if not getattr(future, "_pipeline_result_recorded", False):
                    self._register_export_result(state, export_result)
        image_pipeline.shutdown(cancelled=cancelled)
