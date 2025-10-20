"""Service layer for executing the ebook processing pipeline."""

from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from pydub import AudioSegment

from .. import config_manager as cfg
from .. import logging_manager as log_mgr
from .. import metadata_manager
from .. import output_formatter
from .. import observability
from ..core import ingestion
from ..core.config import PipelineConfig, build_pipeline_config
from ..core.rendering import process_epub
from ..progress_tracker import ProgressTracker
from ..translation_engine import TranslationWorkerPool

if TYPE_CHECKING:
    from .job_manager import PipelineJob, PipelineJobManager

logger = log_mgr.logger
configure_logging_level = log_mgr.configure_logging_level


@dataclass(slots=True)
class PipelineInput:
    """User-supplied parameters describing a pipeline execution request."""

    input_file: str
    base_output_file: str
    input_language: str
    target_languages: List[str]
    sentences_per_output_file: int
    start_sentence: int
    end_sentence: Optional[int]
    stitch_full: bool
    generate_audio: bool
    audio_mode: str
    written_mode: str
    selected_voice: str
    output_html: bool
    output_pdf: bool
    generate_video: bool
    include_transliteration: bool
    tempo: float
    book_metadata: Dict[str, Any]


@dataclass(slots=True)
class PipelineRequest:
    """Complete description of a pipeline execution request."""

    config: Dict[str, Any]
    context: Optional[cfg.RuntimeContext]
    environment_overrides: Dict[str, Any]
    pipeline_overrides: Dict[str, Any]
    inputs: PipelineInput
    progress_tracker: Optional[ProgressTracker] = None
    stop_event: Optional[threading.Event] = None
    translation_pool: Optional[TranslationWorkerPool] = None
    correlation_id: Optional[str] = None
    job_id: Optional[str] = None


@dataclass(slots=True)
class PipelineResponse:
    """Result of running the ebook processing pipeline."""

    success: bool
    pipeline_config: Optional[PipelineConfig] = None
    refined_sentences: Optional[List[str]] = None
    refined_updated: bool = False
    written_blocks: Optional[List[str]] = None
    audio_segments: Optional[List[AudioSegment]] = None
    batch_video_files: Optional[List[str]] = None
    base_dir: Optional[str] = None
    base_output_stem: Optional[str] = None
    stitched_documents: Dict[str, str] = field(default_factory=dict)
    stitched_audio_path: Optional[str] = None
    stitched_video_path: Optional[str] = None
    book_metadata: Dict[str, Any] = field(default_factory=dict)


def run_pipeline(request: PipelineRequest) -> PipelineResponse:
    """Execute the ebook pipeline for the provided :class:`PipelineRequest`."""

    context = request.context or cfg.build_runtime_context(
        request.config, request.environment_overrides
    )
    cfg.set_runtime_context(context)

    pipeline_config: Optional[PipelineConfig] = None
    stitched_audio_path: Optional[str] = None
    stitched_video_path: Optional[str] = None
    stitched_documents: Dict[str, str] = {}
    refined_list: List[str] = []
    total_fully = 0
    tracker = request.progress_tracker

    correlation_id = request.correlation_id or str(uuid4())
    request.correlation_id = correlation_id
    job_id = request.job_id

    pipeline_attrs = {
        "correlation_id": correlation_id,
        "job_id": job_id,
        "input_file": request.inputs.input_file,
    }

    try:
        overrides = {**request.environment_overrides, **request.pipeline_overrides}
        selected_voice = request.inputs.selected_voice
        if selected_voice and "selected_voice" not in overrides:
            overrides["selected_voice"] = selected_voice
        pipeline_config = build_pipeline_config(context, request.config, overrides=overrides)
        pipeline_config.apply_runtime_settings()
        configure_logging_level(pipeline_config.debug)

        inputs = request.inputs
        metadata: Dict[str, Any] = dict(inputs.book_metadata)
        if request.config.get("auto_metadata", True):
            try:
                input_path = cfg.resolve_file_path(inputs.input_file, context.books_dir)
                if input_path:
                    inferred = metadata_manager.infer_metadata(
                        str(input_path),
                        existing_metadata=metadata,
                        force_refresh=bool(
                            request.pipeline_overrides.get("force_metadata_refresh")
                            or request.pipeline_overrides.get("refresh_metadata")
                        ),
                    )
                    metadata.update({k: v for k, v in inferred.items() if v is not None})
            except Exception as metadata_error:  # pragma: no cover - defensive logging
                logger.debug(
                    "Metadata inference failed for %s: %s",
                    inputs.input_file,
                    metadata_error,
                )
        inputs.book_metadata = metadata
        generate_audio = pipeline_config.generate_audio
        audio_mode = pipeline_config.audio_mode

        if tracker is not None:
            tracker.publish_start(
                {
                    "stage": "initialization",
                    "input_file": inputs.input_file,
                    "target_languages": tuple(inputs.target_languages),
                }
            )

        with log_mgr.log_context(correlation_id=correlation_id, job_id=job_id):
            logger.info(
                "Pipeline execution started",
                extra={
                    "event": "pipeline.run.start",
                    "attributes": {
                        "input_file": inputs.input_file,
                        "base_output_file": inputs.base_output_file,
                        "target_languages": inputs.target_languages,
                        "sentences_per_output_file": inputs.sentences_per_output_file,
                        "start_sentence": inputs.start_sentence,
                        "end_sentence": inputs.end_sentence,
                    },
                    "console_suppress": True,
                },
            )

        with observability.pipeline_operation("pipeline", attributes=pipeline_attrs):
            with observability.pipeline_stage(
                "ingestion",
                {
                    **pipeline_attrs,
                    "target_languages": tuple(inputs.target_languages),
                },
            ):
                refined_list, refined_updated = ingestion.get_refined_sentences(
                    inputs.input_file,
                    pipeline_config,
                    force_refresh=True,
                    metadata={
                        "mode": "cli",
                        "target_languages": inputs.target_languages,
                        "max_words": pipeline_config.max_words,
                    },
                )
                total_fully = len(refined_list)
                if tracker is not None:
                    tracker.publish_progress(
                        {
                            "stage": "ingestion",
                            "message": "Sentence ingestion complete.",
                            "total_sentences": total_fully,
                        }
                    )
                if refined_updated:
                    refined_output_path = ingestion.refined_list_output_path(
                        inputs.input_file, pipeline_config
                    )
                    logger.info(
                        "Refined sentence list written",
                        extra={
                            "event": "pipeline.ingestion.refined_output",
                            "attributes": {
                                "path": str(refined_output_path),
                                "total_sentences": total_fully,
                            },
                            "console_suppress": True,
                        },
                    )

            with observability.pipeline_stage(
                "rendering",
                {**pipeline_attrs, "total_sentences": total_fully},
            ):
                (
                    written_blocks,
                    all_audio_segments,
                    batch_video_files,
                    base_dir,
                    base_no_ext,
                ) = process_epub(
                    inputs.input_file,
                    inputs.base_output_file,
                    inputs.input_language,
                    inputs.target_languages,
                    inputs.sentences_per_output_file,
                    inputs.start_sentence,
                    inputs.end_sentence,
                    generate_audio,
                    audio_mode,
                    inputs.written_mode,
                    inputs.output_html,
                    inputs.output_pdf,
                    refined_list=refined_list,
                    generate_video=inputs.generate_video,
                    include_transliteration=inputs.include_transliteration,
                    book_metadata=metadata,
                    pipeline_config=pipeline_config,
                    progress_tracker=request.progress_tracker,
                    stop_event=request.stop_event,
                    translation_pool=request.translation_pool,
                )

                if tracker is not None:
                    tracker.publish_progress(
                        {
                            "stage": "rendering",
                            "message": "Rendering phase completed.",
                        }
                    )

            post_process_attrs = {**pipeline_attrs, "base_dir": base_dir or ""}
            if request.stop_event and request.stop_event.is_set():
                with observability.pipeline_stage("shutdown", post_process_attrs):
                    logger.info(
                        "Shutdown request acknowledged; skipping remaining post-processing steps.",
                        extra={
                            "event": "pipeline.shutdown.requested",
                            "console_suppress": True,
                        },
                    )
                    if tracker is not None:
                        tracker.publish_progress(
                            {
                                "stage": "shutdown",
                                "message": "Stop event acknowledged in pipeline.",
                            }
                        )
            elif inputs.stitch_full:
                with observability.pipeline_stage("stitching", post_process_attrs):
                    final_sentence = (
                        inputs.start_sentence + len(written_blocks) - 1
                        if written_blocks
                        else inputs.start_sentence
                    )
                    stitched_basename = output_formatter.compute_stitched_basename(
                        inputs.input_file, inputs.target_languages
                    )
                    range_fragment = output_formatter.format_sentence_range(
                        inputs.start_sentence, final_sentence, total_fully
                    )
                    stitched_documents = output_formatter.stitch_full_output(
                        base_dir,
                        inputs.start_sentence,
                        final_sentence,
                        stitched_basename,
                        written_blocks,
                        inputs.target_languages[0],
                        total_fully,
                        output_html=inputs.output_html,
                        output_pdf=inputs.output_pdf,
                        epub_title=f"Stitched Translation: {range_fragment} {stitched_basename}",
                    )
                    if pipeline_config.generate_audio and all_audio_segments:
                        stitched_audio = AudioSegment.empty()
                        for seg in all_audio_segments:
                            stitched_audio += seg
                        stitched_audio_path = os.path.join(
                            base_dir,
                            f"{range_fragment}_{stitched_basename}.mp3",
                        )
                        stitched_audio.export(
                            stitched_audio_path, format="mp3", bitrate="320k"
                        )
                    if inputs.generate_video and batch_video_files:
                        logger.info(
                            "Generating stitched video slide output by concatenating batch video files...",
                            extra={
                                "event": "pipeline.stitching.video.start",
                                "console_suppress": True,
                            },
                        )
                        concat_list_path = os.path.join(
                            base_dir, f"concat_full_{stitched_basename}.txt"
                        )
                        with open(concat_list_path, "w", encoding="utf-8") as file_obj:
                            for video_file in batch_video_files:
                                file_obj.write(f"file '{video_file}'\n")
                        stitched_video_path = os.path.join(
                            base_dir,
                            f"{range_fragment}_{stitched_basename}_stitched.mp4",
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
                            stitched_video_path,
                        ]
                        subprocess.run(cmd_concat, check=True)
                        os.remove(concat_list_path)
                        logger.info(
                            "Stitched video slide output saved",
                            extra={
                                "event": "pipeline.stitching.video.complete",
                                "attributes": {"path": stitched_video_path},
                                "console_suppress": True,
                            },
                        )
            else:
                stitched_documents = {}

        with log_mgr.log_context(correlation_id=correlation_id, job_id=job_id):
            logger.info(
                "Pipeline execution completed",
                extra={
                    "event": "pipeline.run.complete",
                    "status": "success",
                    "console_suppress": True,
                },
            )

        return PipelineResponse(
            success=True,
            pipeline_config=pipeline_config,
            refined_sentences=refined_list,
            refined_updated=refined_updated,
            written_blocks=written_blocks,
            audio_segments=all_audio_segments,
            batch_video_files=batch_video_files,
            base_dir=base_dir,
            base_output_stem=base_no_ext,
            stitched_documents=stitched_documents,
            stitched_audio_path=stitched_audio_path,
            stitched_video_path=stitched_video_path,
            book_metadata=metadata,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        with log_mgr.log_context(correlation_id=correlation_id, job_id=job_id):
            logger.error(
                "Pipeline execution failed",
                extra={
                    "event": "pipeline.run.error",
                    "status": "failed",
                    "attributes": {"error": str(exc)},
                },
            )
        if tracker is not None:
            tracker.record_error(exc, {"stage": "pipeline"})
            tracker.mark_finished(reason="pipeline error", forced=True)
        return PipelineResponse(
            success=False,
            pipeline_config=pipeline_config,
            book_metadata=inputs.book_metadata,
        )
    finally:
        if context is not None:
            try:
                cfg.cleanup_environment(context)
            except Exception as cleanup_exc:  # pragma: no cover - defensive logging
                logger.debug(
                    "Failed to clean up temporary workspace: %s", cleanup_exc
                )
        cfg.clear_runtime_context()


def _serialize_pipeline_config(config: PipelineConfig) -> Dict[str, Any]:
    return {
        "working_dir": str(config.working_dir),
        "output_dir": str(config.output_dir) if config.output_dir else None,
        "tmp_dir": str(config.tmp_dir),
        "books_dir": str(config.books_dir),
        "ollama_model": config.ollama_model,
        "ollama_url": config.ollama_url,
        "ffmpeg_path": config.ffmpeg_path,
        "thread_count": config.thread_count,
        "queue_size": config.queue_size,
        "pipeline_enabled": config.pipeline_enabled,
        "max_words": config.max_words,
        "split_on_comma_semicolon": config.split_on_comma_semicolon,
        "debug": config.debug,
        "generate_audio": config.generate_audio,
        "audio_mode": config.audio_mode,
        "selected_voice": config.selected_voice,
        "tempo": config.tempo,
        "macos_reading_speed": config.macos_reading_speed,
        "sync_ratio": config.sync_ratio,
        "word_highlighting": config.word_highlighting,
    }


def serialize_pipeline_response(response: PipelineResponse) -> Dict[str, Any]:
    """Convert ``response`` into a JSON-serializable mapping."""

    audio_segments: Optional[List[float]] = None
    if response.audio_segments:
        audio_segments = [segment.duration_seconds for segment in response.audio_segments]

    payload: Dict[str, Any] = {
        "success": response.success,
        "refined_sentences": response.refined_sentences,
        "refined_updated": response.refined_updated,
        "written_blocks": response.written_blocks,
        "audio_segments": audio_segments,
        "batch_video_files": response.batch_video_files,
        "base_dir": str(response.base_dir) if response.base_dir else None,
        "base_output_stem": response.base_output_stem,
        "stitched_documents": dict(response.stitched_documents),
        "stitched_audio_path": response.stitched_audio_path,
        "stitched_video_path": response.stitched_video_path,
        "book_metadata": dict(response.book_metadata),
    }

    if response.pipeline_config is not None:
        payload["pipeline_config"] = _serialize_pipeline_config(response.pipeline_config)

    return payload


def serialize_pipeline_request(request: PipelineRequest) -> Dict[str, Any]:
    """Convert ``request`` into a JSON-serializable mapping."""

    payload: Dict[str, Any] = {
        "config": dict(request.config),
        "environment_overrides": dict(request.environment_overrides),
        "pipeline_overrides": dict(request.pipeline_overrides),
        "inputs": asdict(request.inputs),
    }

    if request.correlation_id is not None:
        payload["correlation_id"] = request.correlation_id

    return payload


class PipelineService:
    """High-level orchestration API for the ebook processing pipeline."""

    def __init__(self, job_manager: "PipelineJobManager") -> None:
        self._job_manager = job_manager

    def enqueue(self, request: PipelineRequest) -> "PipelineJob":
        """Submit ``request`` for background execution and return the job handle."""

        return self._job_manager.submit(request)

    def get_job(self, job_id: str) -> "PipelineJob":
        """Return the job associated with ``job_id``."""

        return self._job_manager.get(job_id)

    def list_jobs(self) -> Dict[str, "PipelineJob"]:
        """Return a mapping of all known job handles."""

        return self._job_manager.list()

    def run_sync(self, request: PipelineRequest) -> PipelineResponse:
        """Execute ``request`` synchronously and return the pipeline response."""

        return run_pipeline(request)

    def refresh_metadata(self, job_id: str) -> "PipelineJob":
        """Force-refresh metadata for the specified job and return the updated handle."""

        return self._job_manager.refresh_metadata(job_id)

    def pause_job(self, job_id: str) -> "PipelineJob":
        """Request that the specified job pause execution."""

        return self._job_manager.request_pause(job_id)

    def cancel_job(self, job_id: str) -> "PipelineJob":
        """Request that the specified job cancel execution."""

        return self._job_manager.request_cancel(job_id)
