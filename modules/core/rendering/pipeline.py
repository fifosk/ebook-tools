"""High-level EPUB rendering pipeline built on modular components."""

from __future__ import annotations

import concurrent.futures
import datetime
import json
import queue
import threading
from collections import deque
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from PIL import Image
from pydub import AudioSegment

from modules import audio_video_generator as av_gen
from modules.render import MediaBatchOrchestrator
from modules.render.backends import PollyAudioSynthesizer
from modules import output_formatter
from modules.book_cover import fetch_book_cover
from modules.config_manager import resolve_file_path
from modules.epub_parser import remove_quotes
from modules import text_normalization as text_norm
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
from modules.retry_annotations import is_failure_annotation

from .blocks import build_written_and_video_blocks
from .constants import LANGUAGE_CODES, NON_LATIN_LANGUAGES
from .exporters import BatchExportRequest, BatchExportResult, BatchExporter, build_exporter
from modules.images.drawthings import (
    DrawThingsClientLike,
    DrawThingsError,
    DrawThingsImageRequest,
    DrawThingsImageToImageRequest,
    resolve_drawthings_client,
)
from modules.images.prompting import (
    DiffusionPrompt,
    DiffusionPromptPlan,
    build_sentence_image_negative_prompt,
    build_sentence_image_prompt,
    sentence_to_diffusion_prompt,
    sentence_batches_to_diffusion_prompt_plan,
    sentences_to_diffusion_prompt_map,
    sentences_to_diffusion_prompt_plan,
    stable_diffusion_seed,
)


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


def _job_relative_path(candidate: Path, *, base_dir: Path) -> str:
    """Best-effort conversion of an absolute path to a job-relative storage path."""

    base_dir_path = Path(base_dir)
    path_obj = Path(candidate)
    for parent in base_dir_path.parents:
        if parent.name.lower() == "media" and parent.parent != parent:
            try:
                relative = path_obj.relative_to(parent.parent)
            except ValueError:
                continue
            if relative.as_posix():
                return relative.as_posix()
    job_root_candidates = list(base_dir_path.parents[:4])
    job_root_candidates.append(base_dir_path)
    for root_candidate in job_root_candidates:
        try:
            relative = path_obj.relative_to(root_candidate)
        except ValueError:
            continue
        if relative.as_posix():
            return relative.as_posix()
    return path_obj.name


def _resolve_media_root(base_dir: Path) -> Path:
    """Return the job's media root directory based on ``base_dir``."""

    candidate = Path(base_dir)
    if candidate.name.lower() == "media":
        return candidate
    for parent in candidate.parents:
        if parent.name.lower() == "media":
            return parent
    return candidate


def _resolve_job_root(media_root: Path) -> Optional[Path]:
    candidate = Path(media_root)
    if candidate.name.lower() != "media":
        return None
    if candidate.parent == candidate:
        return None
    return candidate.parent


def _atomic_write_json(path: Path, payload: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


@dataclass(frozen=True, slots=True)
class _SentenceImageResult:
    chunk_id: str
    range_fragment: str
    start_sentence: int
    end_sentence: int
    sentence_number: int
    relative_path: str
    prompt: str
    negative_prompt: str


class _ImageGenerationState:
    """Shared state used to merge async image results into chunk metadata."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._chunks: dict[str, dict[str, Any]] = {}
        self._pending: dict[str, list[_SentenceImageResult]] = {}

    def register_chunk(self, result: BatchExportResult) -> bool:
        """Store ``result`` and apply any pending image updates. Returns True if updated."""

        if result is None:
            return False

        sentence_map: dict[int, dict[str, Any]] = {}
        for entry in result.sentences or []:
            if not isinstance(entry, Mapping):
                continue
            raw_number = entry.get("sentence_number") or entry.get("sentenceNumber")
            try:
                number = int(raw_number)
            except (TypeError, ValueError):
                continue
            sentence_map[number] = entry  # type: ignore[assignment]

        with self._lock:
            self._chunks[result.chunk_id] = {
                "chunk_id": result.chunk_id,
                "range_fragment": result.range_fragment,
                "start_sentence": result.start_sentence,
                "end_sentence": result.end_sentence,
                "files": dict(result.artifacts),
                "sentences": list(result.sentences or []),
                "audio_tracks": dict(result.audio_tracks or {}),
                "timing_tracks": dict(result.timing_tracks or {}),
                "extra_files": [],
                "sentence_map": sentence_map,
            }
            pending = self._pending.pop(result.chunk_id, [])

        updated = False
        for item in pending:
            if self.apply(item):
                updated = True
        return updated

    def apply(self, image: _SentenceImageResult) -> bool:
        """Apply ``image`` into the cached chunk state. Returns True if changed."""

        if image is None:
            return False

        with self._lock:
            chunk = self._chunks.get(image.chunk_id)
            if chunk is None:
                self._pending.setdefault(image.chunk_id, []).append(image)
                return False

            sentence_entry = chunk.get("sentence_map", {}).get(image.sentence_number)
            if isinstance(sentence_entry, dict):
                preserved: dict[str, Any] = {}
                previous = sentence_entry.get("image")
                if isinstance(previous, Mapping):
                    for key, value in previous.items():
                        if key in {"path", "prompt", "negative_prompt", "negativePrompt"}:
                            continue
                        preserved[key] = value

                image_payload: dict[str, Any] = {
                    **preserved,
                    "path": image.relative_path,
                    "prompt": image.prompt,
                }
                if image.negative_prompt:
                    image_payload["negative_prompt"] = image.negative_prompt
                if previous != image_payload:
                    sentence_entry["image"] = image_payload
                    sentence_entry["image_path"] = image.relative_path
                    sentence_entry["imagePath"] = image.relative_path
                    updated = True
                else:
                    updated = False
            else:
                updated = False

            extra_files: list[dict[str, Any]] = chunk.get("extra_files") or []
            signature = ("image", image.relative_path)
            seen = chunk.setdefault("_image_seen", set())
            if signature not in seen:
                seen.add(signature)
                extra_files.append(
                    {
                        "type": "image",
                        "path": image.relative_path,
                        "sentence_number": image.sentence_number,
                        "start_sentence": image.start_sentence,
                        "end_sentence": image.end_sentence,
                        "range_fragment": image.range_fragment,
                        "chunk_id": image.chunk_id,
                    }
                )
                chunk["extra_files"] = extra_files
                updated = True or updated

        return updated

    def snapshot_chunk(self, chunk_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            return dict(chunk) if isinstance(chunk, dict) else None


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
            selected_voice=self._config.selected_voice,
            primary_target_language=target_languages[0] if target_languages else "",
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
                    base_dir=base_dir,
                    base_name=base_name,
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
            self._progress.record_generated_chunk(
                chunk_id=result.chunk_id,
                start_sentence=result.start_sentence,
                end_sentence=result.end_sentence,
                range_fragment=result.range_fragment,
                files=result.artifacts,
                sentences=result.sentences,
                audio_tracks=result.audio_tracks,
                timing_tracks=result.timing_tracks,
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

        should_flush = (
            (sentence_number - state.current_batch_start + 1) % sentences_per_file == 0
        )
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
                )
                processed += 1

    def _process_pipeline(
        self,
        *,
        state: PipelineState,
        exporter: BatchExporter,
        base_dir: str,
        base_name: str,
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
        audio_synthesizer = PollyAudioSynthesizer(
            base_url=self._config.audio_api_base_url,
            timeout=self._config.audio_api_timeout_seconds,
            poll_interval=self._config.audio_api_poll_interval_seconds,
        )
        media_orchestrator = MediaBatchOrchestrator(
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

        image_state: Optional[_ImageGenerationState] = None
        image_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        image_futures: set[concurrent.futures.Future] = set()
        image_client: Optional[DrawThingsClientLike] = None
        image_base_urls = list(self._config.image_api_base_urls or ())
        if not image_base_urls and self._config.image_api_base_url:
            image_base_urls.append(self._config.image_api_base_url)
        image_cluster_nodes: list[dict[str, object]] = []
        image_cluster_available: list[str] = []
        image_cluster_unavailable: list[str] = []
        if generate_images:
            image_state = _ImageGenerationState()
            state.image_state = image_state
            if image_base_urls:
                try:
                    image_client, _available_urls, unavailable_urls = resolve_drawthings_client(
                        base_urls=image_base_urls,
                        timeout_seconds=float(self._config.image_api_timeout_seconds),
                    )
                    image_cluster_available = list(_available_urls or ())
                    image_cluster_unavailable = list(unavailable_urls or ())
                    if unavailable_urls:
                        logger.warning(
                            "DrawThings endpoints unavailable: %s",
                            ", ".join(unavailable_urls),
                            extra={
                                "event": "pipeline.image.unavailable",
                                "attributes": {"unavailable": unavailable_urls},
                                "console_suppress": True,
                            },
                        )
                    if image_client is None:
                        logger.warning(
                            "Image generation enabled but no DrawThings endpoints are reachable.",
                            extra={
                                "event": "pipeline.image.unreachable",
                                "attributes": {"configured": image_base_urls},
                                "console_suppress": True,
                            },
                        )
                except Exception as exc:
                    logger.warning("Unable to configure DrawThings client: %s", exc)
                    image_client = None
            else:
                logger.warning(
                    "Image generation enabled but image_api_base_url(s) are not configured."
                )
                if self._progress is not None:
                    self._progress.record_retry("image", "missing_base_url")

            if image_client is not None:
                max_workers = max(1, int(self._config.image_concurrency or 1))
                image_executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

            if image_base_urls:
                image_cluster_nodes = [
                    {"base_url": url, "active": url in image_cluster_available}
                    for url in image_base_urls
                ]

        def _update_image_cluster_stats() -> None:
            if self._progress is None or not image_cluster_nodes:
                return
            stats_list: list[dict[str, object]] = []
            if image_client is not None and hasattr(image_client, "snapshot_stats"):
                try:
                    stats_list = list(image_client.snapshot_stats())
                except Exception:
                    stats_list = []
            stats_by_url: dict[str, dict[str, object]] = {}
            for entry in stats_list:
                if not isinstance(entry, Mapping):
                    continue
                base_url = entry.get("base_url")
                if isinstance(base_url, str) and base_url:
                    stats_by_url[base_url] = dict(entry)
            nodes_payload: list[dict[str, object]] = []
            for node in image_cluster_nodes:
                base_url = node.get("base_url")
                if not isinstance(base_url, str):
                    continue
                entry = dict(node)
                stats = stats_by_url.get(base_url)
                if stats:
                    entry["processed"] = stats.get("processed", 0)
                    entry["total_seconds"] = stats.get("total_seconds")
                    entry["avg_seconds_per_image"] = stats.get("avg_seconds_per_image")
                else:
                    entry.setdefault("processed", 0)
                    entry.setdefault("avg_seconds_per_image", None)
                nodes_payload.append(entry)
            self._progress.update_generated_files_metadata(
                {"image_cluster": {"nodes": nodes_payload, "unavailable": image_cluster_unavailable}}
            )

        if generate_images and image_cluster_nodes:
            _update_image_cluster_stats()

        target_sentences = [str(entry) for entry in (sentences or ())]
        base_dir_path = Path(base_dir)
        media_root = _resolve_media_root(base_dir_path)
        final_sentence_number = start_sentence + max(total_refined - 1, 0)
        prompt_context_window = max(0, int(getattr(self._config, "image_prompt_context_sentences", 0) or 0))
        recent_prompt_sentences: deque[str] = deque(maxlen=prompt_context_window)
        image_prompt_batching_enabled = bool(
            getattr(self._config, "image_prompt_batching_enabled", True)
        )
        image_prompt_batch_size = max(
            1,
            int(getattr(self._config, "image_prompt_batch_size", 10) or 10),
        )
        image_prompt_batch_size = min(image_prompt_batch_size, 50)
        if not image_prompt_batching_enabled:
            image_prompt_batch_size = 1
        image_prompt_plan_batch_size = max(
            1,
            int(getattr(self._config, "image_prompt_plan_batch_size", 50) or 50),
        )
        image_prompt_plan_batch_size = min(image_prompt_plan_batch_size, 50)
        image_prompt_batches: list[list[str]] = []
        image_prompt_batch_starts: list[int] = []
        if image_prompt_batch_size > 1 and final_sentence_number >= start_sentence:
            for batch_start in range(
                start_sentence,
                final_sentence_number + 1,
                image_prompt_batch_size,
            ):
                offset_start = max(batch_start - start_sentence, 0)
                offset_end = min(
                    offset_start + image_prompt_batch_size, len(target_sentences)
                )
                image_prompt_batches.append(list(target_sentences[offset_start:offset_end]))
                image_prompt_batch_starts.append(int(batch_start))
        image_task_total = 0
        if generate_images and image_executor is not None and image_client is not None:
            image_task_total = (
                len(image_prompt_batch_starts)
                if image_prompt_batch_size > 1
                else len(target_sentences)
            )
            if self._progress is not None and image_task_total > 0:
                self._progress.set_total(total_refined + image_task_total)
        image_prompt_plan: dict[int, DiffusionPrompt] = {}
        if image_prompt_batch_size > 1:
            image_prompt_seed_sources = {
                batch_start: "\n".join(
                    str(sentence).strip()
                    for sentence in batch
                    if str(sentence).strip()
                ).strip()
                for batch_start, batch in zip(
                    image_prompt_batch_starts, image_prompt_batches
                )
            }
        else:
            image_prompt_seed_sources = {
                start_sentence + offset: str(sentence).strip()
                for offset, sentence in enumerate(target_sentences)
            }
        image_prompt_sources: dict[int, str] = {}
        image_prompt_baseline = DiffusionPrompt(prompt="")
        image_prompt_baseline_notes = ""
        image_prompt_baseline_source = "fallback"
        prompt_plan_quality: dict[str, Any] = {}
        image_style_template = getattr(self._config, "image_style_template", None)
        image_seed_with_previous_image = bool(
            getattr(self._config, "image_seed_with_previous_image", False)
        )
        baseline_seed_image_path: Optional[Path] = None
        baseline_seed_relative_path: Optional[str] = None
        baseline_seed_error: Optional[str] = None
        img2img_capability = {"enabled": image_seed_with_previous_image}
        img2img_capability_lock = threading.Lock()
        prompt_plan_lock = threading.Lock()
        prompt_plan_ready = threading.Event()
        prompt_plan_future: Optional[concurrent.futures.Future] = None
        prompt_plan_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        pending_image_keys: set[int] = set()
        prompt_plan_ready_queue: queue.Queue[list[int]] = queue.Queue()
        translation_thread = None

        if image_executor is not None and image_client is not None and generate_images:
            context_window = max(
                0,
                int(getattr(self._config, "image_prompt_context_sentences", 0) or 0),
            )
            window_start_idx = max(start_sentence - 1, 0)
            window_end_idx = min(window_start_idx + total_refined, total_fully)
            prefix_start = max(0, window_start_idx - context_window)
            suffix_end = min(total_fully, window_end_idx + context_window)
            context_prefix = (
                tuple(full_sentences[prefix_start:window_start_idx])
                if prefix_start < window_start_idx
                else ()
            )
            context_suffix = (
                tuple(full_sentences[window_end_idx:suffix_end])
                if window_end_idx < suffix_end
                else ()
            )
            job_root = _resolve_job_root(media_root)
            prompt_plan_path = (
                (job_root / "metadata" / "image_prompt_plan.json")
                if job_root is not None
                else None
            )

            def _build_prompt_plan() -> None:
                nonlocal image_prompt_plan
                nonlocal image_prompt_sources
                nonlocal image_prompt_baseline
                nonlocal image_prompt_baseline_notes
                nonlocal image_prompt_baseline_source
                nonlocal prompt_plan_quality
                nonlocal baseline_seed_image_path
                nonlocal baseline_seed_relative_path
                nonlocal baseline_seed_error
                nonlocal prompt_plan_ready_queue

                def _queue_prompt_keys(keys: list[int]) -> None:
                    if keys:
                        prompt_plan_ready_queue.put(keys)

                def _handle_prompt_chunk(
                    start_idx: int, end_idx: int, plan: DiffusionPromptPlan
                ) -> None:
                    nonlocal image_prompt_baseline
                    nonlocal image_prompt_baseline_notes
                    nonlocal image_prompt_baseline_source
                    if end_idx <= start_idx:
                        return
                    chunk_len = len(plan.prompts)
                    if chunk_len <= 0:
                        return
                    keys: list[int] = []
                    for offset in range(chunk_len):
                        global_index = start_idx + offset
                        if image_prompt_batch_size > 1:
                            if global_index >= len(image_prompt_batch_starts):
                                continue
                            key = int(image_prompt_batch_starts[global_index])
                        else:
                            key = int(start_sentence + global_index)
                        keys.append(key)
                    if not keys:
                        return
                    with prompt_plan_lock:
                        for offset, key in enumerate(keys):
                            image_prompt_plan[key] = plan.prompts[offset]
                            if offset < len(plan.sources):
                                image_prompt_sources[key] = str(plan.sources[offset])
                            else:
                                image_prompt_sources[key] = "fallback"
                        image_prompt_baseline = plan.baseline_prompt
                        image_prompt_baseline_notes = plan.baseline_notes
                        image_prompt_baseline_source = plan.baseline_source
                    _queue_prompt_keys(keys)

                prompt_plan_error: Optional[str] = None
                planned: list[DiffusionPrompt] = []
                planned_sources: list[str] = []
                baseline_prompt = DiffusionPrompt(prompt="")
                baseline_notes = ""
                baseline_source = "fallback"
                quality: dict[str, Any] = {}

                try:
                    if image_prompt_batch_size > 1:
                        planned_plan = sentence_batches_to_diffusion_prompt_plan(
                            image_prompt_batches,
                            context_prefix=context_prefix,
                            context_suffix=context_suffix,
                            chunk_size=image_prompt_plan_batch_size,
                            on_chunk=_handle_prompt_chunk,
                        )
                        expected = len(image_prompt_batch_starts)
                    else:
                        planned_plan = sentences_to_diffusion_prompt_plan(
                            target_sentences,
                            context_prefix=context_prefix,
                            context_suffix=context_suffix,
                            chunk_size=image_prompt_plan_batch_size,
                            on_chunk=_handle_prompt_chunk,
                        )
                        expected = len(target_sentences)
                    planned = planned_plan.prompts
                    planned_sources = planned_plan.sources
                    baseline_prompt = planned_plan.baseline_prompt
                    baseline_notes = planned_plan.baseline_notes
                    baseline_source = planned_plan.baseline_source
                    quality = (
                        dict(planned_plan.quality)
                        if isinstance(planned_plan.quality, dict)
                        else {}
                    )
                    if len(planned) != expected or len(planned_sources) != expected:
                        raise ValueError("Prompt plan length mismatch")
                    if image_prompt_batch_size > 1:
                        quality = dict(quality)
                        quality.setdefault("total_batches", expected)
                        quality.setdefault("total_sentences", len(target_sentences))
                        quality.setdefault("prompt_batch_size", image_prompt_batch_size)
                    if image_prompt_plan_batch_size:
                        quality = dict(quality)
                        quality.setdefault("prompt_plan_batch_size", image_prompt_plan_batch_size)
                except Exception as exc:
                    prompt_plan_error = str(exc)
                    baseline_prompt = DiffusionPrompt(prompt=str(target_sentences[0]).strip() if target_sentences else "")
                    baseline_notes = ""
                    baseline_source = "fallback"
                    if image_prompt_batch_size > 1:
                        planned = [
                            DiffusionPrompt(
                                prompt="\n".join(
                                    str(sentence).strip()
                                    for sentence in batch
                                    if str(sentence).strip()
                                ).strip()
                            )
                            for batch in image_prompt_batches
                        ]
                        planned_sources = ["fallback"] * len(planned)
                    else:
                        planned = [
                            DiffusionPrompt(prompt=str(sentence).strip())
                            for sentence in target_sentences
                        ]
                        planned_sources = ["fallback"] * len(planned)
                    quality = {
                        "version": 1,
                        "total_sentences": len(target_sentences),
                        "llm_requests": 0,
                        "initial_missing": len(planned),
                        "final_fallback": len(planned),
                        "retry_attempts": 0,
                        "retry_requested": 0,
                        "retry_recovered": 0,
                        "retry_recovered_unique": 0,
                        "initial_coverage_rate": 0.0 if planned else 1.0,
                        "llm_coverage_rate": 0.0 if planned else 1.0,
                        "fallback_rate": 1.0 if planned else 0.0,
                        "retry_success_rate": None,
                        "recovery_rate": None,
                        "errors": [prompt_plan_error],
                    }
                    if image_prompt_batch_size > 1:
                        quality["total_batches"] = len(planned)
                        quality["prompt_batch_size"] = image_prompt_batch_size
                    if image_prompt_plan_batch_size:
                        quality["prompt_plan_batch_size"] = image_prompt_plan_batch_size
                    if self._progress is not None:
                        self._progress.record_retry("image", "prompt_plan_error")
                    logger.warning(
                        "Unable to precompute image prompts: %s",
                        exc,
                        extra={
                            "event": "pipeline.image.prompt_plan.error",
                            "attributes": {"error": str(exc)},
                            "console_suppress": True,
                        },
                    )

                if image_prompt_batch_size > 1:
                    plan_map = {
                        int(batch_start): prompt
                        for batch_start, prompt in zip(image_prompt_batch_starts, planned)
                    }
                    source_map = {
                        int(batch_start): str(source)
                        for batch_start, source in zip(image_prompt_batch_starts, planned_sources)
                    }
                else:
                    plan_map = {
                        start_sentence + offset: prompt
                        for offset, prompt in enumerate(planned)
                    }
                    source_map = {
                        start_sentence + offset: str(source)
                        for offset, source in enumerate(planned_sources)
                    }

                with prompt_plan_lock:
                    image_prompt_plan = plan_map
                    image_prompt_sources = source_map
                    image_prompt_baseline = baseline_prompt
                    image_prompt_baseline_notes = baseline_notes
                    image_prompt_baseline_source = baseline_source
                    prompt_plan_quality = quality

                end_sentence_number = start_sentence + max(total_refined - 1, 0)
                baseline_scene = (baseline_prompt.prompt or "").strip()
                baseline_negative = (baseline_prompt.negative_prompt or "").strip()
                baseline_seed_value = stable_diffusion_seed(
                    baseline_scene or f"{start_sentence}-{end_sentence_number}"
                )
                baseline_seed_status = "disabled"
                baseline_seed_image_path_local: Optional[Path] = None
                baseline_seed_relative_path_local: Optional[str] = None
                baseline_seed_error_local: Optional[str] = None

                if image_seed_with_previous_image:
                    baseline_seed_dir = media_root / "images" / "_seed"
                    baseline_seed_image_path_local = baseline_seed_dir / (
                        f"baseline_seed_{start_sentence:05d}_{end_sentence_number:05d}.png"
                    )
                    baseline_seed_relative_path_local = _job_relative_path(
                        baseline_seed_image_path_local, base_dir=base_dir_path
                    )
                    baseline_seed_status = "skipped" if not baseline_scene else "ok"

                    if baseline_scene:
                        try:
                            if not baseline_seed_image_path_local.exists():
                                baseline_prompt_full = build_sentence_image_prompt(
                                    baseline_scene,
                                    style_template=image_style_template,
                                )
                                baseline_negative_full = build_sentence_image_negative_prompt(
                                    baseline_negative,
                                    style_template=image_style_template,
                                )
                                request = DrawThingsImageRequest(
                                    prompt=baseline_prompt_full,
                                    negative_prompt=baseline_negative_full,
                                    width=int(self._config.image_width or 512),
                                    height=int(self._config.image_height or 512),
                                    steps=int(self._config.image_steps or 24),
                                    cfg_scale=float(self._config.image_cfg_scale or 7.0),
                                    sampler_name=self._config.image_sampler_name,
                                    seed=baseline_seed_value,
                                )
                                image_bytes, _ = image_client.txt2img(request)
                                baseline_seed_dir.mkdir(parents=True, exist_ok=True)
                                try:
                                    import io

                                    with Image.open(io.BytesIO(image_bytes)) as loaded:
                                        converted = loaded.convert("RGB")
                                        output = io.BytesIO()
                                        converted.save(output, format="PNG")
                                        baseline_seed_image_path_local.write_bytes(output.getvalue())
                                except Exception:
                                    baseline_seed_image_path_local.write_bytes(image_bytes)
                        except Exception as exc:
                            baseline_seed_error_local = str(exc)
                            baseline_seed_status = "error"
                            logger.warning(
                                "Unable to generate baseline seed image: %s",
                                exc,
                                extra={
                                    "event": "pipeline.image.baseline_seed.error",
                                    "attributes": {"error": str(exc)},
                                    "console_suppress": True,
                                },
                            )

                with prompt_plan_lock:
                    baseline_seed_image_path = baseline_seed_image_path_local
                    baseline_seed_relative_path = baseline_seed_relative_path_local
                    baseline_seed_error = baseline_seed_error_local

                try:
                    if prompt_plan_path is not None:
                        context_prefix_payload = [
                            {
                                "sentence_number": idx + 1,
                                "sentence": str(full_sentences[idx]).strip(),
                            }
                            for idx in range(prefix_start, window_start_idx)
                        ]
                        context_suffix_payload = [
                            {
                                "sentence_number": idx + 1,
                                "sentence": str(full_sentences[idx]).strip(),
                            }
                            for idx in range(window_end_idx, suffix_end)
                        ]
                        prompts_payload = []
                        if image_prompt_batch_size > 1:
                            for batch_index, batch_start in enumerate(image_prompt_batch_starts):
                                offset_start = max(int(batch_start) - start_sentence, 0)
                                offset_end = min(
                                    offset_start + image_prompt_batch_size, len(target_sentences)
                                )
                                batch_sentences = [
                                    str(entry).strip()
                                    for entry in target_sentences[offset_start:offset_end]
                                ]
                                batch_end = int(batch_start) + max(offset_end - offset_start - 1, 0)
                                diffusion = plan_map.get(int(batch_start))
                                scene_prompt = (diffusion.prompt or "").strip() if diffusion else ""
                                scene_negative_prompt = (diffusion.negative_prompt or "").strip() if diffusion else ""
                                source = source_map.get(int(batch_start)) or (
                                    "fallback" if diffusion is None else "llm"
                                )
                                if not scene_prompt:
                                    scene_prompt = batch_sentences[0] if batch_sentences else ""
                                prompts_payload.append(
                                    {
                                        "batch_index": int(batch_index),
                                        "start_sentence": int(batch_start),
                                        "end_sentence": int(batch_end),
                                        "sentences": [
                                            {
                                                "sentence_number": int(batch_start) + idx,
                                                "sentence": sentence,
                                            }
                                            for idx, sentence in enumerate(batch_sentences)
                                        ],
                                        "scene_prompt": scene_prompt,
                                        "scene_negative_prompt": scene_negative_prompt,
                                        "source": source,
                                        "seed": stable_diffusion_seed(
                                            image_prompt_seed_sources.get(int(batch_start))
                                            or scene_prompt
                                        ),
                                    }
                                )
                        else:
                            for offset, sentence_text in enumerate(target_sentences):
                                sentence_number = start_sentence + offset
                                diffusion = plan_map.get(sentence_number)
                                scene_prompt = ""
                                scene_negative_prompt = ""
                                source = source_map.get(sentence_number) or (
                                    "fallback" if diffusion is None else "llm"
                                )
                                if diffusion is not None:
                                    scene_prompt = (diffusion.prompt or "").strip()
                                    scene_negative_prompt = (diffusion.negative_prompt or "").strip()
                                if not scene_prompt:
                                    scene_prompt = str(sentence_text).strip()
                                prompts_payload.append(
                                    {
                                        "sentence_number": sentence_number,
                                        "sentence": str(sentence_text).strip(),
                                        "scene_prompt": scene_prompt,
                                        "scene_negative_prompt": scene_negative_prompt,
                                        "source": source,
                                        "seed": stable_diffusion_seed(
                                            image_prompt_seed_sources.get(sentence_number)
                                            or str(sentence_text).strip()
                                        ),
                                    }
                                )

                        payload = {
                            "version": 1,
                            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "start_sentence": start_sentence,
                            "end_sentence": end_sentence_number,
                            "context_window": context_window,
                            "prompt_batching_enabled": bool(image_prompt_batch_size > 1),
                            "prompt_batch_size": int(image_prompt_batch_size),
                            "prompt_plan_batch_size": int(image_prompt_plan_batch_size),
                            "style_prompt": build_sentence_image_prompt(
                                "",
                                style_template=image_style_template,
                            ),
                            "style_negative_prompt": build_sentence_image_negative_prompt(
                                "",
                                style_template=image_style_template,
                            ),
                            "style_template": image_style_template,
                            "baseline": {
                                "scene_prompt": baseline_scene,
                                "scene_negative_prompt": baseline_negative,
                                "notes": str(baseline_notes or "").strip(),
                                "source": str(baseline_source or "fallback"),
                                "seed": baseline_seed_value,
                                "seed_image_path": baseline_seed_relative_path_local,
                                "seed_image_status": baseline_seed_status,
                            },
                            "context_prefix": context_prefix_payload,
                            "context_suffix": context_suffix_payload,
                            "status": "ok" if plan_map else "error",
                            "quality": quality,
                            "prompts": prompts_payload,
                        }
                        if baseline_seed_error_local:
                            payload["baseline"]["seed_image_error"] = baseline_seed_error_local
                        if prompt_plan_error:
                            payload["error"] = prompt_plan_error
                        prompt_plan_path.parent.mkdir(parents=True, exist_ok=True)
                        _atomic_write_json(prompt_plan_path, payload)
                        summary_path = prompt_plan_path.with_name("image_prompt_plan_summary.json")
                        summary_payload = {
                            "version": payload.get("version", 1),
                            "generated_at": payload.get("generated_at"),
                            "start_sentence": payload.get("start_sentence"),
                            "end_sentence": payload.get("end_sentence"),
                            "context_window": payload.get("context_window"),
                            "prompt_batch_size": payload.get("prompt_batch_size"),
                            "prompt_plan_batch_size": payload.get("prompt_plan_batch_size"),
                            "status": payload.get("status"),
                            "quality": payload.get("quality") or {},
                            "baseline": {
                                "source": payload.get("baseline", {}).get("source"),
                                "seed_image_status": payload.get("baseline", {}).get("seed_image_status"),
                            },
                        }
                        if payload.get("error"):
                            summary_payload["error"] = payload.get("error")
                        _atomic_write_json(summary_path, summary_payload)
                except Exception as exc:
                    logger.warning(
                        "Unable to persist image prompt plan: %s",
                        exc,
                        extra={
                            "event": "pipeline.image.prompt_plan.persist.error",
                            "attributes": {"error": str(exc)},
                            "console_suppress": True,
                        },
                    )
                finally:
                    prompt_plan_ready.set()

            prompt_plan_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            prompt_plan_future = prompt_plan_executor.submit(_build_prompt_plan)

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
        previous_image_future: Optional[concurrent.futures.Future] = None
        previous_image_key_sentence_number: Optional[int] = None
        scheduled_image_keys: set[int] = set()

        def _submit_sentence_image(
            *,
            sentence_number: int,
            sentence_for_prompt: str,
            context_sentences: tuple[str, ...] = (),
        ) -> None:
            nonlocal previous_image_future
            nonlocal previous_image_key_sentence_number

            if (
                image_executor is None
                or image_state is None
                or image_client is None
                or pipeline_stop_event.is_set()
            ):
                return

            image_key_sentence_number = int(sentence_number)
            if image_key_sentence_number in scheduled_image_keys:
                return

            batch_start_sentence_number = image_key_sentence_number
            batch_end_sentence_number = (
                min(
                    batch_start_sentence_number + image_prompt_batch_size - 1,
                    final_sentence_number,
                )
                if image_prompt_batch_size > 1
                else batch_start_sentence_number
            )
            applies_sentence_numbers = tuple(
                range(batch_start_sentence_number, batch_end_sentence_number + 1)
            )

            offset = max(batch_start_sentence_number - start_sentence, 0)
            chunk_start = start_sentence + (offset // max(1, sentences_per_file)) * max(
                1, sentences_per_file
            )
            chunk_end = min(
                chunk_start + max(1, sentences_per_file) - 1,
                final_sentence_number,
            )
            range_fragment = output_formatter.format_sentence_range(chunk_start, chunk_end, total_fully)
            chunk_id = f"{range_fragment}_{base_name}"
            if image_prompt_batch_size > 1:
                images_dir = media_root / "images" / "batches"
                image_path = images_dir / f"batch_{batch_start_sentence_number:05d}.png"
            else:
                images_dir = media_root / "images" / range_fragment
                image_path = images_dir / f"sentence_{batch_start_sentence_number:05d}.png"

            previous_seed_future = None
            previous_key_sentence_number = batch_start_sentence_number - (
                image_prompt_batch_size if image_prompt_batch_size > 1 else 1
            )
            if (
                previous_image_future is not None
                and previous_image_key_sentence_number == previous_key_sentence_number
                and image_prompt_sources.get(previous_key_sentence_number) in {"llm", "llm_retry"}
            ):
                previous_seed_future = previous_image_future

            with prompt_plan_lock:
                baseline_seed_snapshot = baseline_seed_image_path
                baseline_prompt_snapshot = image_prompt_baseline

            def _generate_image(
                *,
                sentence_for_prompt: str = sentence_for_prompt,
                context_sentences: tuple[str, ...] = context_sentences,
                image_key_sentence_number: int = image_key_sentence_number,
                applies_sentence_numbers: tuple[int, ...] = applies_sentence_numbers,
                chunk_id: str = chunk_id,
                range_fragment: str = range_fragment,
                chunk_start: int = chunk_start,
                chunk_end: int = chunk_end,
                images_dir: Path = images_dir,
                image_path: Path = image_path,
                base_dir_path: Path = base_dir_path,
                previous_seed_future: Optional[concurrent.futures.Future] = previous_seed_future,
                previous_key_sentence_number: int = previous_key_sentence_number,
                baseline_seed_image_path: Optional[Path] = baseline_seed_snapshot,
                baseline_prompt: DiffusionPrompt = baseline_prompt_snapshot,
            ) -> list[_SentenceImageResult]:
                success = False
                try:
                    diffusion = image_prompt_plan.get(image_key_sentence_number)
                    if diffusion is None:
                        diffusion = DiffusionPrompt(prompt=str(sentence_for_prompt).strip())
                    scene_description = (diffusion.prompt or "").strip() or (sentence_for_prompt or "").strip()
                    negative = (diffusion.negative_prompt or "").strip()
                    current_source = image_prompt_sources.get(image_key_sentence_number) or ""
                    baseline_scene = (baseline_prompt.prompt or "").strip()
                    baseline_negative = (baseline_prompt.negative_prompt or "").strip()

                    with img2img_capability_lock:
                        allow_img2img = bool(img2img_capability.get("enabled"))

                    use_baseline_fallback = (
                        allow_img2img
                        and current_source == "fallback"
                        and previous_seed_future is None
                        and bool(baseline_scene)
                    )
                    if use_baseline_fallback:
                        scene_description = baseline_scene
                        negative = baseline_negative
                    prompt_full = build_sentence_image_prompt(
                        scene_description,
                        style_template=image_style_template,
                    )
                    negative_full = build_sentence_image_negative_prompt(
                        negative,
                        style_template=image_style_template,
                    )
                    seed_source = image_prompt_seed_sources.get(image_key_sentence_number)
                    if use_baseline_fallback and baseline_scene:
                        seed = stable_diffusion_seed(baseline_scene)
                    else:
                        seed = stable_diffusion_seed(seed_source or sentence_for_prompt)

                    seed_image_path: Optional[Path] = None
                    if allow_img2img and previous_seed_future is not None:
                        try:
                            previous_seed_future.result()
                            if image_prompt_batch_size > 1:
                                candidate = (
                                    media_root
                                    / "images"
                                    / "batches"
                                    / f"batch_{previous_key_sentence_number:05d}.png"
                                )
                            else:
                                prev_offset = max(previous_key_sentence_number - start_sentence, 0)
                                prev_chunk_start = start_sentence + (
                                    prev_offset // max(1, sentences_per_file)
                                ) * max(1, sentences_per_file)
                                prev_chunk_end = min(
                                    prev_chunk_start + max(1, sentences_per_file) - 1,
                                    final_sentence_number,
                                )
                                prev_range_fragment = output_formatter.format_sentence_range(
                                    prev_chunk_start, prev_chunk_end, total_fully
                                )
                                candidate = (
                                    media_root
                                    / "images"
                                    / prev_range_fragment
                                    / f"sentence_{previous_key_sentence_number:05d}.png"
                                )
                            if candidate.exists():
                                seed_image_path = candidate
                        except Exception:
                            seed_image_path = None

                    if (
                        seed_image_path is None
                        and allow_img2img
                        and baseline_seed_image_path is not None
                        and baseline_seed_image_path.exists()
                    ):
                        seed_image_path = baseline_seed_image_path

                    blank_detection_enabled = bool(
                        getattr(self._config, "image_blank_detection_enabled", False)
                    )
                    max_image_retries = 2
                    images_dir.mkdir(parents=True, exist_ok=True)

                    import io

                    def _is_likely_blank(converted: Image.Image) -> bool:
                        try:
                            from PIL import ImageStat

                            stats = ImageStat.Stat(converted.convert("L"))
                            mean = float(stats.mean[0]) if stats.mean else 0.0
                            stddev = float(stats.stddev[0]) if getattr(stats, "stddev", None) else 0.0
                        except Exception:
                            return False

                        if stddev >= 2.0:
                            return False
                        return mean < 8.0 or mean > 247.0

                    last_raw_bytes: Optional[bytes] = None
                    for attempt in range(max_image_retries + 1):
                        seed_value = int(seed + attempt * 9973) if attempt else int(seed)

                        def _txt2img() -> bytes:
                            request = DrawThingsImageRequest(
                                prompt=prompt_full,
                                negative_prompt=negative_full,
                                width=int(self._config.image_width or 512),
                                height=int(self._config.image_height or 512),
                                steps=int(self._config.image_steps or 24),
                                cfg_scale=float(self._config.image_cfg_scale or 7.0),
                                sampler_name=self._config.image_sampler_name,
                                seed=seed_value,
                            )
                            image_bytes, _payload = image_client.txt2img(request)
                            return image_bytes

                        try:
                            use_img2img_attempt = (
                                attempt == 0 and seed_image_path is not None and allow_img2img
                            )
                            if use_img2img_attempt:
                                try:
                                    request = DrawThingsImageToImageRequest(
                                        prompt=prompt_full,
                                        negative_prompt=negative_full,
                                        init_image=seed_image_path.read_bytes(),
                                        denoising_strength=0.5,
                                        width=int(self._config.image_width or 512),
                                        height=int(self._config.image_height or 512),
                                        steps=int(self._config.image_steps or 24),
                                        cfg_scale=float(self._config.image_cfg_scale or 7.0),
                                        sampler_name=self._config.image_sampler_name,
                                        seed=seed_value,
                                    )
                                    image_bytes, _payload = image_client.img2img(request)
                                except DrawThingsError as exc:
                                    message = str(exc)
                                    if (
                                        "(404)" in message
                                        or " 404" in message
                                        or "not found" in message.lower()
                                    ):
                                        with img2img_capability_lock:
                                            img2img_capability["enabled"] = False
                                    image_bytes = _txt2img()
                            else:
                                image_bytes = _txt2img()
                        except DrawThingsError:
                            raise
                        except Exception:
                            raise

                        last_raw_bytes = image_bytes

                        try:
                            with Image.open(io.BytesIO(image_bytes)) as loaded:
                                converted = loaded.convert("RGB")
                                if (
                                    blank_detection_enabled
                                    and attempt < max_image_retries
                                    and _is_likely_blank(converted)
                                ):
                                    if self._progress is not None:
                                        self._progress.record_retry("image", "blank_image")
                                    seed_image_path = None
                                    continue
                                output = io.BytesIO()
                                converted.save(output, format="PNG")
                                image_path.write_bytes(output.getvalue())
                                last_raw_bytes = None
                                break
                        except Exception:
                            if attempt < max_image_retries:
                                if self._progress is not None:
                                    self._progress.record_retry("image", "invalid_image_bytes")
                                seed_image_path = None
                                continue
                            break

                    if last_raw_bytes is not None:
                        image_path.write_bytes(last_raw_bytes)
                    relative_path = _job_relative_path(image_path, base_dir=base_dir_path)
                    results: list[_SentenceImageResult] = []
                    for sentence_number in applies_sentence_numbers:
                        offset = max(sentence_number - start_sentence, 0)
                        sentence_chunk_start = start_sentence + (
                            offset // max(1, sentences_per_file)
                        ) * max(1, sentences_per_file)
                        sentence_chunk_end = min(
                            sentence_chunk_start + max(1, sentences_per_file) - 1,
                            final_sentence_number,
                        )
                        sentence_range_fragment = output_formatter.format_sentence_range(
                            sentence_chunk_start, sentence_chunk_end, total_fully
                        )
                        sentence_chunk_id = f"{sentence_range_fragment}_{base_name}"
                        results.append(
                            _SentenceImageResult(
                                chunk_id=sentence_chunk_id,
                                range_fragment=sentence_range_fragment,
                                start_sentence=sentence_chunk_start,
                                end_sentence=sentence_chunk_end,
                                sentence_number=sentence_number,
                                relative_path=relative_path,
                                prompt=prompt_full,
                                negative_prompt=negative_full,
                            )
                        )
                    success = True
                    _update_image_cluster_stats()
                    return results
                except DrawThingsError as exc:
                    if self._progress is not None:
                        self._progress.record_retry("image", "drawthings_error")
                    logger.warning(
                        "DrawThings image generation failed",
                        extra={
                            "event": "pipeline.image.error",
                            "attributes": {
                                "sentence_number": image_key_sentence_number,
                                "range_fragment": range_fragment,
                                "error": str(exc),
                            },
                            "console_suppress": True,
                        },
                    )
                    raise
                except Exception as exc:  # pragma: no cover - defensive logging
                    if self._progress is not None:
                        self._progress.record_retry("image", "exception")
                    logger.warning(
                        "Image generation failed",
                        extra={
                            "event": "pipeline.image.error",
                            "attributes": {
                                "sentence_number": image_key_sentence_number,
                                "range_fragment": range_fragment,
                                "error": str(exc),
                            },
                            "console_suppress": True,
                        },
                    )
                    raise
                finally:
                    if self._progress is not None and image_task_total > 0:
                        self._progress.record_step_completion(
                            stage="image",
                            index=int(image_key_sentence_number),
                            metadata={
                                "sentence_total": int(total_refined),
                                "image_total": int(image_task_total),
                                "image_batch_size": int(image_prompt_batch_size),
                                "image_key_sentence": int(image_key_sentence_number),
                                "image_success": success,
                            },
                        )

            future = image_executor.submit(_generate_image)
            image_futures.add(future)
            scheduled_image_keys.add(image_key_sentence_number)
            previous_image_future = future
            previous_image_key_sentence_number = image_key_sentence_number

        def _drain_prompt_plan_queue() -> None:
            while True:
                try:
                    keys = prompt_plan_ready_queue.get_nowait()
                except queue.Empty:
                    break
                for key in keys:
                    pending_image_keys.add(int(key))

        def _pop_ready_image_keys() -> list[int]:
            if not pending_image_keys:
                return []
            with prompt_plan_lock:
                ready = [key for key in pending_image_keys if key in image_prompt_plan]
            if not ready:
                return []
            for key in ready:
                pending_image_keys.discard(key)
            return ready

        def _prompt_plan_has_key(sentence_number: int) -> bool:
            with prompt_plan_lock:
                return sentence_number in image_prompt_plan

        cancelled = False
        try:
            while state.processed < total_refined:
                _drain_prompt_plan_queue()
                if image_futures:
                    done = [future for future in list(image_futures) if future.done()]
                    for future in done:
                        image_futures.discard(future)
                        try:
                            image_result = future.result()
                        except Exception:
                            continue
                        if image_state is None:
                            continue
                        results: list[_SentenceImageResult] = []
                        if isinstance(image_result, _SentenceImageResult):
                            results = [image_result]
                        elif isinstance(image_result, Sequence):
                            results = [
                                item
                                for item in image_result
                                if isinstance(item, _SentenceImageResult)
                            ]
                        if not results:
                            continue

                        updated_chunks: dict[str, _SentenceImageResult] = {}
                        for item in results:
                            if image_state.apply(item):
                                updated_chunks[item.chunk_id] = item

                        for chunk_id, item in updated_chunks.items():
                            snapshot = image_state.snapshot_chunk(chunk_id)
                            if snapshot and self._progress is not None:
                                self._progress.record_generated_chunk(
                                    chunk_id=str(snapshot.get("chunk_id") or chunk_id),
                                    start_sentence=int(snapshot.get("start_sentence") or item.start_sentence),
                                    end_sentence=int(snapshot.get("end_sentence") or item.end_sentence),
                                    range_fragment=str(snapshot.get("range_fragment") or item.range_fragment),
                                    files=snapshot.get("files") or {},
                                    extra_files=snapshot.get("extra_files") or [],
                                    sentences=snapshot.get("sentences") or [],
                                    audio_tracks=snapshot.get("audio_tracks") or None,
                                    timing_tracks=snapshot.get("timing_tracks") or None,
                                )
                if pending_image_keys and not pipeline_stop_event.is_set():
                    ready_numbers = sorted(_pop_ready_image_keys())
                    for sentence_number in ready_numbers:
                        offset_start = sentence_number - start_sentence
                        if offset_start < 0 or offset_start >= len(target_sentences):
                            continue
                        fallback_prompt_text = str(target_sentences[offset_start]).strip()
                        if image_prompt_batch_size > 1:
                            offset_end = min(
                                offset_start + image_prompt_batch_size, len(target_sentences)
                            )
                            batch_items = [
                                str(entry).strip()
                                for entry in target_sentences[offset_start:offset_end]
                                if str(entry).strip()
                            ]
                            if batch_items:
                                fallback_prompt_text = "Batch narrative:\n" + "\n".join(
                                    f"- {entry}" for entry in batch_items
                                )
                        _submit_sentence_image(
                            sentence_number=sentence_number,
                            sentence_for_prompt=fallback_prompt_text,
                        )
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
                        if not candidate:
                            candidate = transliterate_sentence(
                                fluent,
                                item.target_language,
                                client=translation_client,
                                transliterator=self._transliterator,
                            )
                            candidate = text_norm.collapse_whitespace(
                                remove_quotes(candidate or "").strip()
                            )
                        if candidate:
                            transliteration_result = candidate
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
                    if generate_images and image_prompt_batch_size > 1:
                        batch_start_sentence_number = start_sentence + (
                            (sentence_number - start_sentence) // image_prompt_batch_size
                        ) * image_prompt_batch_size
                        batch_start_sentence_number = max(start_sentence, int(batch_start_sentence_number))
                        batch_end_sentence_number = min(
                            batch_start_sentence_number + image_prompt_batch_size - 1,
                            final_sentence_number,
                        )
                        relative_path = f"media/images/batches/batch_{batch_start_sentence_number:05d}.png"
                        image_payload = metadata_payload.get("image")
                        if isinstance(image_payload, Mapping):
                            image_payload = dict(image_payload)
                        else:
                            image_payload = {}
                        image_payload.setdefault("path", relative_path)
                        image_payload.setdefault("batch_start_sentence", batch_start_sentence_number)
                        image_payload.setdefault("batch_end_sentence", batch_end_sentence_number)
                        image_payload.setdefault("batch_size", image_prompt_batch_size)
                        metadata_payload["image"] = image_payload
                        metadata_payload["image_path"] = relative_path
                        metadata_payload["imagePath"] = relative_path

                    state.current_sentence_metadata.append(metadata_payload)
                    if state.all_sentence_metadata is not None:
                        state.all_sentence_metadata.append(metadata_payload)

                    sentence_for_prompt = (
                        fluent
                        if (isinstance(fluent, str) and fluent.strip() and not translation_failed)
                        else item.sentence
                    )
                    context_sentences = tuple(recent_prompt_sentences) if prompt_context_window > 0 else ()

                    if (
                        image_executor is not None
                        and image_state is not None
                        and image_client is not None
                        and not pipeline_stop_event.is_set()
                    ):
                        image_key_sentence_number = sentence_number
                        if image_prompt_batch_size > 1:
                            image_key_sentence_number = start_sentence + (
                                (sentence_number - start_sentence) // image_prompt_batch_size
                            ) * image_prompt_batch_size
                            image_key_sentence_number = max(start_sentence, int(image_key_sentence_number))
                        fallback_prompt_text = str(sentence_for_prompt or "").strip()
                        if image_prompt_batch_size > 1:
                            offset_start = max(image_key_sentence_number - start_sentence, 0)
                            offset_end = min(
                                offset_start + image_prompt_batch_size, len(target_sentences)
                            )
                            batch_items = [
                                str(entry).strip()
                                for entry in target_sentences[offset_start:offset_end]
                                if str(entry).strip()
                            ]
                            if batch_items:
                                fallback_prompt_text = "Batch narrative:\n" + "\n".join(
                                    f"- {entry}" for entry in batch_items
                                )
                        if not _prompt_plan_has_key(image_key_sentence_number):
                            pending_image_keys.add(image_key_sentence_number)
                        else:
                            _submit_sentence_image(
                                sentence_number=image_key_sentence_number,
                                sentence_for_prompt=fallback_prompt_text,
                                context_sentences=context_sentences,
                            )

                    recent_prompt_sentences.append(str(sentence_for_prompt or "").strip())

                    should_flush = (
                        (item.sentence_number - state.current_batch_start + 1)
                        % sentences_per_file
                        == 0
                    ) and not pipeline_stop_event.is_set()
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
                            target_language=
                            item.target_language or state.last_target_language,
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

            if (
                pending_image_keys
                and image_executor is not None
                and image_state is not None
                and image_client is not None
                and not pipeline_stop_event.is_set()
            ):
                if prompt_plan_future is not None and not prompt_plan_ready.is_set():
                    try:
                        prompt_plan_future.result()
                    except Exception:
                        pass
                _drain_prompt_plan_queue()
                ready_numbers = sorted(_pop_ready_image_keys())
                if prompt_plan_ready.is_set() and pending_image_keys:
                    ready_numbers.extend(sorted(pending_image_keys))
                    pending_image_keys.clear()
                for sentence_number in ready_numbers:
                    offset_start = sentence_number - start_sentence
                    if offset_start < 0 or offset_start >= len(target_sentences):
                        continue
                    fallback_prompt_text = str(target_sentences[offset_start]).strip()
                    if image_prompt_batch_size > 1:
                        offset_end = min(
                            offset_start + image_prompt_batch_size, len(target_sentences)
                        )
                        batch_items = [
                            str(entry).strip()
                            for entry in target_sentences[offset_start:offset_end]
                            if str(entry).strip()
                        ]
                        if batch_items:
                            fallback_prompt_text = "Batch narrative:\n" + "\n".join(
                                f"- {entry}" for entry in batch_items
                            )
                    _submit_sentence_image(
                        sentence_number=sentence_number,
                        sentence_for_prompt=fallback_prompt_text,
                    )
        except KeyboardInterrupt:
            console_warning(
                "Processing interrupted by user; shutting down pipeline...",
                logger_obj=logger,
            )
            cancelled = True
            pipeline_stop_event.set()
        finally:
            pipeline_stop_event.set()
            for worker in media_threads:
                worker.join(timeout=1.0)
            if translation_thread is not None:
                translation_thread.join(timeout=1.0)
            finalize_executor.shutdown(wait=True)
            if prompt_plan_executor is not None:
                if cancelled and prompt_plan_future is not None:
                    prompt_plan_future.cancel()
                prompt_plan_executor.shutdown(wait=False)
            for future in export_futures:
                try:
                    export_result = future.result()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error("Failed to finalize batch export: %s", exc)
                else:
                    if not getattr(future, "_pipeline_result_recorded", False):
                        self._register_export_result(state, export_result)
            if image_executor is not None:
                if cancelled:
                    for future in list(image_futures):
                        future.cancel()
                if image_futures and image_state is not None and self._progress is not None:
                    for future in concurrent.futures.as_completed(list(image_futures)):
                        try:
                            image_result = future.result()
                        except Exception:
                            continue
                        results: list[_SentenceImageResult] = []
                        if isinstance(image_result, _SentenceImageResult):
                            results = [image_result]
                        elif isinstance(image_result, Sequence):
                            results = [
                                item
                                for item in image_result
                                if isinstance(item, _SentenceImageResult)
                            ]
                        if not results:
                            continue

                        updated_chunks: dict[str, _SentenceImageResult] = {}
                        for item in results:
                            if image_state.apply(item):
                                updated_chunks[item.chunk_id] = item

                        for chunk_id, item in updated_chunks.items():
                            snapshot = image_state.snapshot_chunk(chunk_id)
                            if snapshot:
                                self._progress.record_generated_chunk(
                                    chunk_id=str(snapshot.get("chunk_id") or chunk_id),
                                    start_sentence=int(snapshot.get("start_sentence") or item.start_sentence),
                                    end_sentence=int(snapshot.get("end_sentence") or item.end_sentence),
                                    range_fragment=str(snapshot.get("range_fragment") or item.range_fragment),
                                    files=snapshot.get("files") or {},
                                    extra_files=snapshot.get("extra_files") or [],
                                    sentences=snapshot.get("sentences") or [],
                                    audio_tracks=snapshot.get("audio_tracks") or None,
                                    timing_tracks=snapshot.get("timing_tracks") or None,
                                )
                image_executor.shutdown(wait=True)
