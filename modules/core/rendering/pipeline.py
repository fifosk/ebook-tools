"""High-level EPUB rendering pipeline built on modular components."""

from __future__ import annotations

import concurrent.futures
import queue
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from PIL import Image
from pydub import AudioSegment

from modules import audio_video_generator as av_gen
from modules.render import MediaBatchOrchestrator
from modules import output_formatter
from modules.book_cover import fetch_book_cover
from modules.config_manager import resolve_file_path
from modules.epub_parser import remove_quotes
from modules.llm_client import create_client
from modules.logging_manager import console_info, console_warning, logger
from modules.progress_tracker import ProgressTracker
from modules.core.config import PipelineConfig
from modules.core.translation import (
    ThreadWorkerPool,
    build_target_sequence,
    create_translation_queue,
    split_translation_and_transliteration,
    start_translation_pipeline,
    translate_batch,
    transliterate_sentence,
)
from modules.transliteration import TransliterationService, get_transliterator

from .blocks import build_written_and_video_blocks
from .constants import LANGUAGE_CODES, NON_LATIN_LANGUAGES
from .exporters import BatchExportRequest, BatchExporter, build_exporter


@dataclass
class PipelineState:
    """Mutable state tracked while processing sentences."""

    written_blocks: List[str] = field(default_factory=list)
    video_blocks: List[str] = field(default_factory=list)
    all_audio_segments: Optional[List[AudioSegment]] = None
    current_audio_segments: Optional[List[AudioSegment]] = None
    batch_video_files: List[str] = field(default_factory=list)
    current_batch_start: int = 0
    last_target_language: str = ""
    processed: int = 0


class RenderPipeline:
    """Coordinator for EPUB rendering and optional media generation."""

    def __init__(
        self,
        *,
        pipeline_config: PipelineConfig,
        progress_tracker: Optional[ProgressTracker] = None,
        stop_event: Optional[threading.Event] = None,
        translation_pool: Optional[ThreadWorkerPool] = None,
        transliterator: Optional[TransliterationService] = None,
    ) -> None:
        self._config = pipeline_config
        self._progress = progress_tracker
        self._stop_event = stop_event
        self._external_translation_pool = translation_pool
        self._transliterator = transliterator or get_transliterator()

    # ------------------------------------------------------------------
    # Public API
    def process_epub(
        self,
        input_file: str,
        base_output_file: str,
        input_language: str,
        target_languages: Sequence[str],
        sentences_per_file: int,
        start_sentence: int,
        end_sentence: Optional[int],
        generate_audio: bool,
        audio_mode: str,
        written_mode: str,
        output_html: bool,
        output_pdf: bool,
        refined_list: Sequence[str],
        generate_video: bool,
        include_transliteration: bool = False,
        book_metadata: Optional[dict] = None,
    ) -> Tuple[
        List[str],
        Optional[List[AudioSegment]],
        List[str],
        str,
        str,
    ]:
        """Process an EPUB file and generate the requested outputs."""

        book_metadata = book_metadata or {}

        console_info(
            "Extracting text from '%s'...",
            input_file,
            logger_obj=logger,
        )
        total_fully = len(refined_list)
        console_info(
            "Total fully split sentences extracted: %s",
            total_fully,
            logger_obj=logger,
        )
        start_idx = max(start_sentence - 1, 0)
        end_idx = (
            end_sentence
            if (end_sentence is not None and end_sentence <= total_fully)
            else total_fully
        )
        selected_sentences = list(refined_list[start_idx:end_idx])
        total_refined = len(selected_sentences)
        console_info(
            "Processing %s sentences starting from refined sentence #%s",
            total_refined,
            start_sentence,
            logger_obj=logger,
        )
        if self._progress is not None:
            self._progress.set_total(total_refined)

        src_code = LANGUAGE_CODES.get(input_language, "XX").upper()
        tgt_code = (
            LANGUAGE_CODES.get(target_languages[0], "XX").upper()
            if target_languages
            else "XX"
        )

        base_dir, base_name, _ = output_formatter.prepare_output_directory(
            input_file,
            book_metadata.get("book_author"),
            book_metadata.get("book_title"),
            src_code,
            tgt_code,
            context=self._config.context,
        )

        book_title = book_metadata.get("book_title", "Unknown Title")
        book_author = book_metadata.get("book_author", "Unknown Author")

        cover_img = self._load_cover_image(
            book_metadata.get("book_cover_file"),
            book_title,
            book_author,
        )

        global_counts, total_book_words = self._build_word_counts(refined_list)
        slide_render_options = self._config.get_slide_render_options()

        exporter = build_exporter(
            base_dir=base_dir,
            base_name=base_name,
            cover_img=cover_img,
            book_author=book_author,
            book_title=book_title,
            global_cumulative_word_counts=global_counts,
            total_book_words=total_book_words,
            macos_reading_speed=self._config.macos_reading_speed,
            input_language=input_language,
            total_sentences=total_fully,
            tempo=self._config.tempo,
            sync_ratio=self._config.sync_ratio,
            word_highlighting=self._config.word_highlighting,
            highlight_granularity=self._config.highlight_granularity,
            slide_render_options=slide_render_options,
            template_name=self._config.slide_template,
        )

        state = self._initial_state(
            generate_audio=generate_audio,
            start_sentence=start_sentence,
            target_languages=target_languages,
        )

        translation_client = self._ensure_translation_client()
        worker_count = max(1, self._config.thread_count)
        active_translation_pool = self._external_translation_pool
        own_pool = False
        if active_translation_pool is None:
            active_translation_pool = ThreadWorkerPool(max_workers=worker_count)
            own_pool = True

        try:
            if not self._config.pipeline_enabled:
                self._process_sequential(
                    state=state,
                    exporter=exporter,
                    sentences=selected_sentences,
                    total_refined=total_refined,
                    start_sentence=start_sentence,
                    input_language=input_language,
                    target_languages=target_languages,
                    generate_audio=generate_audio,
                    generate_video=generate_video,
                    audio_mode=audio_mode,
                    written_mode=written_mode,
                    sentences_per_file=sentences_per_file,
                    include_transliteration=include_transliteration,
                    output_html=output_html,
                    output_pdf=output_pdf,
                    translation_client=translation_client,
                    worker_pool=active_translation_pool,
                    worker_count=worker_count,
                    total_fully=total_fully,
                )
            else:
                self._process_pipeline(
                    state=state,
                    exporter=exporter,
                    sentences=selected_sentences,
                    start_sentence=start_sentence,
                    total_refined=total_refined,
                    input_language=input_language,
                    target_languages=target_languages,
                    generate_audio=generate_audio,
                    generate_video=generate_video,
                    audio_mode=audio_mode,
                    written_mode=written_mode,
                    sentences_per_file=sentences_per_file,
                    include_transliteration=include_transliteration,
                    output_html=output_html,
                    output_pdf=output_pdf,
                    translation_client=translation_client,
                    worker_pool=active_translation_pool,
                    worker_count=worker_count,
                    total_fully=total_fully,
                )
        finally:
            if own_pool and active_translation_pool is not None:
                active_translation_pool.shutdown()

        if state.written_blocks and not self._should_stop():
            request = BatchExportRequest(
                start_sentence=state.current_batch_start,
                end_sentence=state.current_batch_start + len(state.written_blocks) - 1,
                written_blocks=list(state.written_blocks),
                target_language=(
                    state.last_target_language
                    or (target_languages[0] if target_languages else "")
                ),
                output_html=output_html,
                output_pdf=output_pdf,
                generate_audio=generate_audio,
                audio_segments=list(state.current_audio_segments or []),
                generate_video=generate_video,
                video_blocks=list(state.video_blocks),
            )
            video_path = exporter.export(request)
            if video_path:
                state.batch_video_files.append(video_path)
        elif self._should_stop():
            console_info(
                "Skip final batch export due to shutdown request.",
                logger_obj=logger,
            )

        console_info("EPUB processing complete!", logger_obj=logger)
        console_info(
            "Total sentences processed: %s",
            state.processed,
            logger_obj=logger,
        )

        return (
            state.written_blocks,
            state.all_audio_segments,
            state.batch_video_files,
            base_dir,
            base_name,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    def _initial_state(
        self,
        *,
        generate_audio: bool,
        start_sentence: int,
        target_languages: Sequence[str],
    ) -> PipelineState:
        state = PipelineState()
        state.current_batch_start = start_sentence
        state.last_target_language = target_languages[0] if target_languages else ""
        if generate_audio:
            state.all_audio_segments = []
            state.current_audio_segments = []
        return state

    def _ensure_translation_client(self):
        translation_client = getattr(self._config, "translation_client", None)
        if translation_client is None:
            translation_client = create_client(
                model=self._config.ollama_model,
                api_url=self._config.ollama_url,
                debug=self._config.debug,
                api_key=self._config.ollama_api_key,
                llm_source=self._config.llm_source,
                local_api_url=self._config.local_ollama_url,
                cloud_api_url=self._config.cloud_ollama_url,
                cloud_api_key=self._config.ollama_api_key,
            )
        return translation_client

    def _load_cover_image(
        self,
        cover_file: Optional[str],
        book_title: str,
        book_author: str,
    ) -> Optional[Image.Image]:
        cover_file_path = resolve_file_path(cover_file, self._config.books_dir)
        if cover_file_path and cover_file_path.exists():
            try:
                with Image.open(cover_file_path) as img:
                    cover_img = img.convert("RGB")
                    cover_img.load()
                return cover_img
            except Exception as exc:  # pragma: no cover - best effort logging
                logger.debug("Error loading cover image from file: %s", exc)
        remote_cover = fetch_book_cover(f"{book_title} {book_author}")
        if remote_cover:
            try:
                cover_img = remote_cover.convert("RGB")
                cover_img.load()
                return cover_img
            finally:
                try:
                    remote_cover.close()
                except Exception:  # pragma: no cover - ignore cleanup errors
                    pass
        return None

    def _build_word_counts(
        self, sentences: Sequence[str]
    ) -> Tuple[List[int], int]:
        global_counts: List[int] = []
        running = 0
        for sentence in sentences:
            running += len(sentence.split())
            global_counts.append(running)
        return global_counts, running

    def _should_stop(self) -> bool:
        return bool(self._stop_event and self._stop_event.is_set())

    def _maybe_generate_audio(
        self,
        *,
        sentence_number: int,
        sentence: str,
        fluent: str,
        input_language: str,
        target_language: str,
        audio_mode: str,
        total_sentences: int,
    ) -> Optional[AudioSegment]:
        return av_gen.generate_audio_for_sentence(
            sentence_number,
            sentence,
            fluent,
            input_language,
            target_language,
            audio_mode,
            total_sentences,
            LANGUAGE_CODES,
            self._config.selected_voice,
            self._config.tempo,
            self._config.macos_reading_speed,
        )

    def _handle_sentence(
        self,
        *,
        state: PipelineState,
        exporter: BatchExporter,
        sentence_number: int,
        sentence: str,
        fluent: str,
        transliteration_result: str,
        target_language: str,
        sentences_per_file: int,
        written_mode: str,
        total_sentences: int,
        include_transliteration: bool,
        output_html: bool,
        output_pdf: bool,
        generate_audio: bool,
        generate_video: bool,
        audio_segment: Optional[AudioSegment],
    ) -> None:
        written_block, video_block = build_written_and_video_blocks(
            sentence_number=sentence_number,
            sentence=sentence,
            fluent=fluent,
            transliteration=transliteration_result,
            current_target=target_language,
            written_mode=written_mode,
            total_sentences=total_sentences,
            include_transliteration=include_transliteration,
        )
        state.written_blocks.append(written_block)
        if generate_video:
            state.video_blocks.append(video_block)
        if generate_audio and audio_segment is not None:
            if state.current_audio_segments is not None:
                state.current_audio_segments.append(audio_segment)
            if state.all_audio_segments is not None:
                state.all_audio_segments.append(audio_segment)

        should_flush = (
            (sentence_number - state.current_batch_start + 1) % sentences_per_file == 0
        )
        if should_flush:
            request = BatchExportRequest(
                start_sentence=state.current_batch_start,
                end_sentence=sentence_number,
                written_blocks=list(state.written_blocks),
                target_language=target_language or state.last_target_language,
                output_html=output_html,
                output_pdf=output_pdf,
                generate_audio=generate_audio,
                audio_segments=list(state.current_audio_segments or []),
                generate_video=generate_video,
                video_blocks=list(state.video_blocks),
            )
            video_path = exporter.export(request)
            if video_path:
                state.batch_video_files.append(video_path)
            state.written_blocks.clear()
            state.video_blocks.clear()
            if state.current_audio_segments is not None:
                state.current_audio_segments.clear()
            state.current_batch_start = sentence_number + 1
        state.last_target_language = target_language or state.last_target_language
        state.processed += 1
        if self._progress is not None:
            self._progress.record_media_completion(state.processed - 1, sentence_number)

    def _process_sequential(
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
        output_html: bool,
        output_pdf: bool,
        translation_client,
        worker_pool: ThreadWorkerPool,
        worker_count: int,
        total_fully: int,
    ) -> None:
        batch_size = worker_count
        processed = 0
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
                    target_languages[
                        ((number - start_sentence) % len(target_languages))
                    ]
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
                client=translation_client,
                worker_pool=worker_pool,
                max_workers=worker_count,
            )

            for sentence_number, sentence, current_target, translation_result in zip(
                batch_sentence_numbers, batch_sentences, batch_targets, translations
            ):
                if self._should_stop():
                    break
                fluent_candidate = remove_quotes(translation_result or "")
                fluent, inline_transliteration = split_translation_and_transliteration(
                    fluent_candidate
                )
                fluent = fluent.strip()
                inline_transliteration = remove_quotes(inline_transliteration or "").strip()

                should_transliterate = (
                    include_transliteration and current_target in NON_LATIN_LANGUAGES
                )
                transliteration_result = inline_transliteration
                if should_transliterate:
                    candidate = remove_quotes(inline_transliteration or "").strip()
                    if not candidate:
                        candidate = transliterate_sentence(
                            fluent,
                            current_target,
                            client=translation_client,
                            transliterator=self._transliterator,
                        )
                        candidate = remove_quotes(candidate or "").strip()
                    if candidate:
                        transliteration_result = candidate
                audio_segment = None
                if generate_audio:
                    audio_segment = self._maybe_generate_audio(
                        sentence_number=sentence_number,
                        sentence=sentence,
                        fluent=fluent,
                        input_language=input_language,
                        target_language=current_target,
                        audio_mode=audio_mode,
                        total_sentences=total_fully,
                    )
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
                )
                processed += 1

    def _process_pipeline(
        self,
        *,
        state: PipelineState,
        exporter: BatchExporter,
        sentences: Sequence[str],
        start_sentence: int,
        total_refined: int,
        input_language: str,
        target_languages: Sequence[str],
        generate_audio: bool,
        generate_video: bool,
        audio_mode: str,
        written_mode: str,
        sentences_per_file: int,
        include_transliteration: bool,
        output_html: bool,
        output_pdf: bool,
        translation_client,
        worker_pool: ThreadWorkerPool,
        worker_count: int,
        total_fully: int,
    ) -> None:
        pipeline_stop_event = self._stop_event or threading.Event()
        translation_queue = create_translation_queue(self._config.queue_size)
        finalize_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        media_orchestrator = MediaBatchOrchestrator(
            translation_queue,
            worker_count=worker_count,
            total_sentences=total_fully,
            input_language=input_language,
            audio_mode=audio_mode,
            language_codes=LANGUAGE_CODES,
            selected_voice=self._config.selected_voice,
            tempo=self._config.tempo,
            macos_reading_speed=self._config.macos_reading_speed,
            generate_audio=generate_audio,
            queue_size=self._config.queue_size,
            audio_stop_event=pipeline_stop_event,
            progress_tracker=self._progress,
            media_result_factory=av_gen.MediaPipelineResult,
        )
        media_queue, media_threads = media_orchestrator.start()
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
            include_transliteration=include_transliteration,
        )

        buffered_results = {}
        next_index = 0
        export_futures: List[concurrent.futures.Future] = []
        try:
            while state.processed < total_refined:
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
                    fluent_candidate = remove_quotes(item.translation or "")
                    fluent, inline_transliteration = split_translation_and_transliteration(
                        fluent_candidate
                    )
                    fluent = fluent.strip()
                    inline_transliteration = remove_quotes(
                        inline_transliteration or ""
                    ).strip()
                    should_transliterate = (
                        include_transliteration
                        and item.target_language in NON_LATIN_LANGUAGES
                    )
                    transliteration_result = inline_transliteration
                    if should_transliterate:
                        candidate = remove_quotes(
                            (item.transliteration or inline_transliteration or "")
                        ).strip()
                        if not candidate:
                            candidate = transliterate_sentence(
                                fluent,
                                item.target_language,
                                client=translation_client,
                                transliterator=self._transliterator,
                            )
                            candidate = remove_quotes(candidate or "").strip()
                        if candidate:
                            transliteration_result = candidate
                    audio_segment = None
                    if generate_audio:
                        audio_segment = item.audio_segment or AudioSegment.silent(
                            duration=0
                        )
                        if state.current_audio_segments is not None:
                            state.current_audio_segments.append(audio_segment)
                        if state.all_audio_segments is not None:
                            state.all_audio_segments.append(audio_segment)
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
                    if generate_video:
                        state.video_blocks.append(video_block)
                    should_flush = (
                        (item.sentence_number - state.current_batch_start + 1)
                        % sentences_per_file
                        == 0
                    ) and not pipeline_stop_event.is_set()
                    if should_flush:
                        request = BatchExportRequest(
                            start_sentence=state.current_batch_start,
                            end_sentence=item.sentence_number,
                            written_blocks=list(state.written_blocks),
                            target_language=
                            item.target_language or state.last_target_language,
                            output_html=output_html,
                            output_pdf=output_pdf,
                            generate_audio=generate_audio,
                            audio_segments=list(state.current_audio_segments or []),
                            generate_video=generate_video,
                            video_blocks=list(state.video_blocks),
                        )
                        future = finalize_executor.submit(exporter.export, request)
                        export_futures.append(future)
                        state.written_blocks.clear()
                        state.video_blocks.clear()
                        if state.current_audio_segments is not None:
                            state.current_audio_segments.clear()
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
        except KeyboardInterrupt:
            console_warning(
                "Processing interrupted by user; shutting down pipeline...",
                logger_obj=logger,
            )
            pipeline_stop_event.set()
        finally:
            pipeline_stop_event.set()
            for worker in media_threads:
                worker.join(timeout=1.0)
            if translation_thread is not None:
                translation_thread.join(timeout=1.0)
            finalize_executor.shutdown(wait=True)
            for future in export_futures:
                try:
                    video_path = future.result()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error("Failed to finalize batch export: %s", exc)
                else:
                    if video_path:
                        state.batch_video_files.append(video_path)
