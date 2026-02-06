"""High-level EPUB rendering pipeline built on modular components."""

from __future__ import annotations

from dataclasses import dataclass, field
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from PIL import Image
from pydub import AudioSegment

from modules import audio_video_generator as av_gen
from modules.render import MediaBatchOrchestrator
from modules import output_formatter
from modules.book_cover import fetch_book_cover
from modules.config_manager import resolve_file_path
from modules.llm_client import create_client
from modules.logging_manager import console_info, logger
from modules.progress_tracker import ProgressTracker
from modules.core.config import PipelineConfig
from modules.core.translation import ThreadWorkerPool
from modules.transliteration import TransliterationService, get_transliterator

from .blocks import build_written_and_video_blocks
from .constants import LANGUAGE_CODES
from .exporters import BatchExportRequest, BatchExportResult, BatchExporter, build_exporter
from .pipeline_processing import _ImageGenerationState, process_pipeline, process_sequential


@dataclass
class PipelineState:
    """Mutable state tracked while processing sentences."""

    written_blocks: List[str] = field(default_factory=list)
    video_blocks: List[str] = field(default_factory=list)
    all_audio_segments: Optional[List[AudioSegment]] = None
    current_audio_segments: Optional[List[AudioSegment]] = None
    all_original_segments: Optional[List[AudioSegment]] = None
    current_original_segments: Optional[List[AudioSegment]] = None
    all_sentence_metadata: Optional[List[Dict[str, Any]]] = None
    current_sentence_metadata: List[Dict[str, Any]] = field(default_factory=list)
    batch_video_files: List[str] = field(default_factory=list)
    current_batch_start: int = 0
    last_target_language: str = ""
    processed: int = 0
    voice_metadata: Dict[str, Dict[str, Set[str]]] = field(default_factory=dict)
    current_voice_metadata: Dict[str, Dict[str, Set[str]]] = field(
        default_factory=dict
    )
    image_state: Any = None
    media_batch_total: int = 0
    media_batch_completed: int = 0
    media_batch_items_total: int = 0
    media_batch_items_completed: int = 0
    media_batch_size: int = 0
    media_batch_first_size: Optional[int] = None
    media_batch_ids: Set[str] = field(default_factory=set)


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
        generate_images: bool = False,
        include_transliteration: bool = False,
        translation_provider: Optional[str] = None,
        translation_batch_size: Optional[int] = None,
        transliteration_mode: Optional[str] = None,
        transliteration_model: Optional[str] = None,
        media_metadata: Optional[dict] = None,
        enable_lookup_cache: bool = True,
        lookup_cache_batch_size: int = 10,
    ) -> Tuple[
        List[str],
        Optional[List[AudioSegment]],
        List[str],
        str,
        str,
    ]:
        """Process an EPUB file and generate the requested outputs."""

        media_metadata = media_metadata or {}

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
            self._progress.set_playable_total(total_refined)

        src_code = LANGUAGE_CODES.get(input_language, "XX").upper()
        tgt_code = (
            LANGUAGE_CODES.get(target_languages[0], "XX").upper()
            if target_languages
            else "XX"
        )

        base_dir, base_name, _ = output_formatter.prepare_output_directory(
            input_file,
            media_metadata.get("book_author"),
            media_metadata.get("book_title"),
            src_code,
            tgt_code,
            context=self._config.context,
        )

        book_title = media_metadata.get("book_title", "Unknown Title")
        book_author = media_metadata.get("book_author", "Unknown Author")

        cover_img = self._load_cover_image(
            media_metadata.get("book_cover_file"),
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
            selected_voice=self._config.selected_voice,
            primary_target_language=target_languages[0] if target_languages else "",
            audio_bitrate_kbps=getattr(self._config, "audio_bitrate_kbps", None),
            slide_render_options=slide_render_options,
            template_name=self._config.slide_template,
            video_backend=self._config.video_backend,
            video_backend_settings=self._config.video_backend_settings,
        )

        state = self._initial_state(
            generate_audio=generate_audio,
            start_sentence=start_sentence,
            target_languages=target_languages,
        )

        translation_client = self._ensure_translation_client()
        normalized_transliteration_mode = self._normalize_transliteration_mode(
            transliteration_mode
        )
        transliteration_client, owns_transliteration_client = (
            self._resolve_transliteration_client(
                normalized_transliteration_mode,
                translation_client,
                transliteration_model,
            )
        )
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
                    translation_provider=translation_provider,
                    translation_batch_size=translation_batch_size,
                    transliteration_mode=normalized_transliteration_mode,
                    transliteration_client=transliteration_client,
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
                    base_dir=base_dir,
                    base_name=base_name,
                    media_metadata=media_metadata,
                    full_sentences=refined_list,
                    sentences=selected_sentences,
                    start_sentence=start_sentence,
                    total_refined=total_refined,
                    input_language=input_language,
                    target_languages=target_languages,
                    generate_audio=generate_audio,
                    generate_video=generate_video,
                    generate_images=generate_images,
                    audio_mode=audio_mode,
                    written_mode=written_mode,
                    sentences_per_file=sentences_per_file,
                    include_transliteration=include_transliteration,
                    translation_provider=translation_provider,
                    translation_batch_size=translation_batch_size,
                    transliteration_mode=normalized_transliteration_mode,
                    transliteration_client=transliteration_client,
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
            if owns_transliteration_client and transliteration_client is not None:
                transliteration_client.close()

        if state.written_blocks and not self._should_stop():
            audio_tracks: Dict[str, List[AudioSegment]] = {}
            if state.current_original_segments:
                audio_tracks["orig"] = list(state.current_original_segments)
            if state.current_audio_segments:
                audio_tracks["translation"] = list(state.current_audio_segments)
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
                audio_tracks=audio_tracks,
                generate_video=generate_video,
                video_blocks=list(state.video_blocks),
                voice_metadata=self._drain_current_voice_metadata(state),
                sentence_metadata=list(state.current_sentence_metadata),
            )
            export_result = exporter.export(request)
            self._register_export_result(state, export_result)
            state.current_sentence_metadata.clear()
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
    def _register_export_result(
        self, state: PipelineState, result: Optional[BatchExportResult]
    ) -> None:
        if result is None:
            return
        video_path = result.artifacts.get("video")
        if video_path:
            state.batch_video_files.append(video_path)
        if self._progress is not None:
            self._record_media_batch_progress(state, result)
            self._progress.record_generated_chunk(
                chunk_id=result.chunk_id,
                start_sentence=result.start_sentence,
                end_sentence=result.end_sentence,
                range_fragment=result.range_fragment,
                files=result.artifacts,
                sentences=result.sentences,
                audio_tracks=result.audio_tracks,
                timing_tracks=result.timing_tracks,
                timing_version=result.timing_version,
                highlighting_policy=result.highlighting_policy,
            )
            image_state = getattr(state, "image_state", None)
            if isinstance(image_state, _ImageGenerationState):
                updated = image_state.register_chunk(result)
                if updated:
                    snapshot = image_state.snapshot_chunk(result.chunk_id)
                    if snapshot:
                        self._progress.record_generated_chunk(
                            chunk_id=str(snapshot.get("chunk_id") or result.chunk_id),
                            start_sentence=int(snapshot.get("start_sentence") or result.start_sentence),
                            end_sentence=int(snapshot.get("end_sentence") or result.end_sentence),
                            range_fragment=str(snapshot.get("range_fragment") or result.range_fragment),
                            files=snapshot.get("files") or dict(result.artifacts),
                            extra_files=snapshot.get("extra_files") or [],
                            sentences=snapshot.get("sentences") or list(result.sentences or []),
                            audio_tracks=snapshot.get("audio_tracks") or result.audio_tracks,
                            timing_tracks=snapshot.get("timing_tracks") or result.timing_tracks,
                            timing_version=result.timing_version,
                            highlighting_policy=result.highlighting_policy,
                        )

    def _record_media_batch_progress(
        self,
        state: PipelineState,
        result: BatchExportResult,
    ) -> None:
        if self._progress is None:
            return
        if state.media_batch_total <= 0:
            return
        chunk_id = str(result.chunk_id or "")
        if not chunk_id:
            return
        if chunk_id in state.media_batch_ids:
            return
        state.media_batch_ids.add(chunk_id)
        if result.sentences:
            item_count = len(result.sentences)
        else:
            try:
                item_count = int(result.end_sentence) - int(result.start_sentence) + 1
            except (TypeError, ValueError):
                item_count = 0
        state.media_batch_completed += 1
        state.media_batch_items_completed += max(0, item_count)
        payload: Dict[str, object] = {
            "batch_size": state.media_batch_size,
            "batches_total": state.media_batch_total,
            "batches_completed": state.media_batch_completed,
            "items_total": state.media_batch_items_total,
            "items_completed": state.media_batch_items_completed,
            "last_updated": round(time.time(), 3),
        }
        if state.media_batch_first_size:
            payload["first_batch_size"] = state.media_batch_first_size
        self._progress.update_generated_files_metadata({"media_batch_stats": payload})
        # Emit per-sentence playable progress events (throttled to prevent flooding)
        self._progress.record_playable_batch(
            start_sentence=result.start_sentence,
            end_sentence=result.end_sentence,
            chunk_id=chunk_id,
        )


    def _handle_export_future_completion(
        self,
        state: PipelineState,
        future: concurrent.futures.Future[Optional[BatchExportResult]],
    ) -> None:
        """Register export results as soon as the background task finishes."""

        exception = future.exception()
        if exception is not None:
            return

        result = future.result()
        try:
            self._register_export_result(state, result)
        except Exception:  # pragma: no cover - defensive logging
            chunk_label = getattr(result, "chunk_id", "unknown") if result else "unknown"
            logger.error("Failed to record generated chunk %s", chunk_label, exc_info=True)
        finally:
            setattr(future, "_pipeline_result_recorded", True)

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
        state.current_sentence_metadata = []
        state.all_sentence_metadata = []
        if generate_audio:
            state.all_audio_segments = []
            state.current_audio_segments = []
            state.all_original_segments = []
            state.current_original_segments = []
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
                lmstudio_api_url=self._config.lmstudio_url,
                cloud_api_key=self._config.ollama_api_key,
            )
        return translation_client

    def _normalize_transliteration_mode(self, mode: Optional[str]) -> str:
        if not mode:
            return "default"
        normalized = mode.strip().lower().replace("_", "-")
        if normalized in {"python", "python-module", "module", "local-module"}:
            return "python"
        if normalized in {"default", "llm", "ollama"}:
            return "default"
        return "default"

    def _resolve_transliteration_client(
        self,
        mode: str,
        translation_client,
        transliteration_model: Optional[str],
    ):
        if mode == "python":
            return None, False
        resolved_model = (transliteration_model or "").strip()
        if not resolved_model:
            return translation_client, False
        if resolved_model == translation_client.model:
            return translation_client, False
        client = create_client(
            model=resolved_model,
            api_url=self._config.ollama_url,
            debug=self._config.debug,
            api_key=self._config.ollama_api_key,
            llm_source=self._config.llm_source,
            local_api_url=self._config.local_ollama_url,
            cloud_api_url=self._config.cloud_ollama_url,
            lmstudio_api_url=self._config.lmstudio_url,
            cloud_api_key=self._config.ollama_api_key,
        )
        return client, True

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

    def _update_voice_metadata(
        self,
        state: PipelineState,
        metadata: Optional[Mapping[str, Mapping[str, str]]],
    ) -> None:
        if not metadata:
            return
        role_labels = {
            "source": "Source voice",
            "translation": "Translation voice",
        }
        for role, languages in metadata.items():
            if not isinstance(languages, Mapping):
                continue
            aggregate = state.voice_metadata.setdefault(role, {})
            current = state.current_voice_metadata.setdefault(role, {})
            for language, voice in languages.items():
                normalized_voice = (voice or "").strip()
                if not normalized_voice:
                    continue
                normalized_language = (language or "Unknown").strip() or "Unknown"
                aggregate_set = aggregate.setdefault(normalized_language, set())
                is_new_voice = normalized_voice not in aggregate_set
                aggregate_set.add(normalized_voice)
                current.setdefault(normalized_language, set()).add(normalized_voice)
                label = role_labels.get(role)
                if is_new_voice and label:
                    console_info(
                        "%s (%s): %s",
                        label,
                        normalized_language,
                        normalized_voice,
                        logger_obj=logger,
                        extra={
                            "event": "render.voice.detected",
                            "attributes": {
                                "role": role,
                                "language": normalized_language,
                                "voice": normalized_voice,
                            },
                        },
                    )

    def _drain_current_voice_metadata(
        self, state: PipelineState
    ) -> Dict[str, Dict[str, List[str]]]:
        payload: Dict[str, Dict[str, List[str]]] = {}
        for role, languages in state.current_voice_metadata.items():
            role_payload: Dict[str, List[str]] = {}
            for language, voices in languages.items():
                if voices:
                    role_payload[language] = sorted(voices)
            if role_payload:
                payload[role] = role_payload
        state.current_voice_metadata = {}
        return payload

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
    ) -> Optional[SynthesisResult]:
        return av_gen.generate_audio_for_sentence(
            sentence_number=sentence_number,
            input_sentence=sentence,
            fluent_translation=fluent,
            input_language=input_language,
            target_language=target_language,
            audio_mode=audio_mode,
            total_sentences=total_sentences,
            language_codes=LANGUAGE_CODES,
            selected_voice=self._config.selected_voice,
            tempo=self._config.tempo,
            macos_reading_speed=self._config.macos_reading_speed,
            voice_overrides=self._config.voice_overrides,
            tts_backend=self._config.tts_backend,
            tts_executable_path=self._config.tts_executable_path or self._config.say_path,
            progress_tracker=self._progress,
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
        original_audio_segment: Optional[AudioSegment] = None,
        voice_metadata: Optional[Mapping[str, Mapping[str, str]]] = None,
        first_flush_size: Optional[int] = None,
        first_batch_start: Optional[int] = None,
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
        self._update_voice_metadata(state, voice_metadata)
        state.written_blocks.append(written_block)
        state.video_blocks.append(video_block)
        if generate_audio:
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

        metadata_payload: Dict[str, Any] = {
            "sentence_number": sentence_number,
            "id": str(sentence_number),
            "text": fluent or transliteration_result or sentence,
            "t0": 0.0,
        }
        duration_val = 0.0
        if audio_segment is not None:
            try:
                duration_val = float(audio_segment.duration_seconds)
            except Exception:
                duration_val = 0.0
        metadata_payload["t1"] = round(max(duration_val, 0.0), 6)

        if generate_audio and audio_segment is not None:
            tokens: List[Dict[str, float | str]] = []
            words = [word for word in (fluent or "").split() if word]
            token_count = len(words)
            slice_duration = (duration_val / token_count) if token_count > 0 else 0.0
            cursor = 0.0
            for index, word in enumerate(words):
                start = cursor
                end = duration_val if index == token_count - 1 else cursor + slice_duration
                start = round(max(start, 0.0), 6)
                end = round(max(min(end, duration_val), 0.0), 6)
                tokens.append({"text": word, "start": start, "end": end})
                cursor = end
            if tokens:
                metadata_payload["word_tokens"] = tokens
                try:
                    setattr(audio_segment, "word_tokens", tokens)
                except Exception:
                    pass

        state.current_sentence_metadata.append(metadata_payload)
        if state.all_sentence_metadata is not None:
            state.all_sentence_metadata.append(metadata_payload)

        sentences_in_chunk = sentence_number - state.current_batch_start + 1
        should_flush = sentences_in_chunk % sentences_per_file == 0
        if (
            not should_flush
            and first_flush_size
            and first_batch_start is not None
            and state.current_batch_start == first_batch_start
            and sentences_in_chunk >= first_flush_size
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
                end_sentence=sentence_number,
                written_blocks=list(state.written_blocks),
                target_language=target_language or state.last_target_language,
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
            export_result = exporter.export(request)
            self._register_export_result(state, export_result)
            state.written_blocks.clear()
            state.video_blocks.clear()
            if state.current_audio_segments is not None:
                state.current_audio_segments.clear()
            if state.current_original_segments is not None:
                state.current_original_segments.clear()
            state.current_sentence_metadata.clear()
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
        return process_sequential(
            self,
            state=state,
            exporter=exporter,
            sentences=sentences,
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
            translation_provider=translation_provider,
            translation_batch_size=translation_batch_size,
            transliteration_mode=transliteration_mode,
            transliteration_client=transliteration_client,
            output_html=output_html,
            output_pdf=output_pdf,
            translation_client=translation_client,
            worker_pool=worker_pool,
            worker_count=worker_count,
            total_fully=total_fully,
        )

    def _process_pipeline(
        self,
        *,
        state: PipelineState,
        exporter: BatchExporter,
        base_dir: str,
        base_name: str,
        media_metadata: Mapping[str, Any],
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
    ) -> None:
        return process_pipeline(
            self,
            state=state,
            exporter=exporter,
            base_dir=base_dir,
            base_name=base_name,
            media_metadata=media_metadata,
            full_sentences=full_sentences,
            sentences=sentences,
            start_sentence=start_sentence,
            total_refined=total_refined,
            input_language=input_language,
            target_languages=target_languages,
            generate_audio=generate_audio,
            generate_video=generate_video,
            generate_images=generate_images,
            audio_mode=audio_mode,
            written_mode=written_mode,
            sentences_per_file=sentences_per_file,
            include_transliteration=include_transliteration,
            translation_provider=translation_provider,
            translation_batch_size=translation_batch_size,
            transliteration_mode=transliteration_mode,
            transliteration_client=transliteration_client,
            output_html=output_html,
            output_pdf=output_pdf,
            translation_client=translation_client,
            worker_pool=worker_pool,
            worker_count=worker_count,
            total_fully=total_fully,
            media_orchestrator_cls=MediaBatchOrchestrator,
        )
