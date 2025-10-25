"""Service layer for executing the ebook processing pipeline."""

from __future__ import annotations

import copy
import threading
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from .. import config_manager as cfg
from .. import logging_manager as log_mgr
from .. import observability
from ..core import ingestion
from ..core.config import PipelineConfig
from ..progress_tracker import ProgressTracker
from ..translation_engine import ThreadWorkerPool
from .pipeline_phases import config_phase, metadata_phase, render_phase
from .pipeline_types import (
    ConfigPhaseResult,
    IngestionResult,
    MetadataPhaseResult,
    PipelineAttributes,
    PipelineMetadata,
    RenderResult,
    StitchingArtifacts,
)

if TYPE_CHECKING:
    from pydub import AudioSegment
    from .job_manager import PipelineJob, PipelineJobManager

logger = log_mgr.logger


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
    book_metadata: PipelineMetadata

    def __post_init__(self) -> None:
        if not isinstance(self.book_metadata, PipelineMetadata):
            self.book_metadata = PipelineMetadata.from_mapping(self.book_metadata)


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
    translation_pool: Optional[ThreadWorkerPool] = None
    correlation_id: Optional[str] = None
    job_id: Optional[str] = None


@dataclass(slots=True)
class PipelineResponse:
    """Result of running the ebook processing pipeline."""

    success: bool
    pipeline_config: Optional[PipelineConfig] = None
    ingestion: Optional[IngestionResult] = None
    render: Optional[RenderResult] = None
    stitching: StitchingArtifacts = field(default_factory=StitchingArtifacts)
    metadata: PipelineMetadata = field(default_factory=PipelineMetadata)
    generated_files: Dict[str, Any] = field(default_factory=dict)

    @property
    def refined_sentences(self) -> Optional[List[str]]:
        return None if self.ingestion is None else self.ingestion.refined_sentences

    @property
    def refined_updated(self) -> bool:
        return False if self.ingestion is None else self.ingestion.refined_updated

    @property
    def written_blocks(self) -> Optional[List[str]]:
        return None if self.render is None else self.render.written_blocks

    @property
    def audio_segments(self) -> Optional[List["AudioSegment"]]:
        return None if self.render is None else self.render.audio_segments

    @property
    def batch_video_files(self) -> Optional[List[str]]:
        return None if self.render is None else self.render.batch_video_files

    @property
    def base_dir(self) -> Optional[str]:
        return None if self.render is None else self.render.base_dir

    @property
    def base_output_stem(self) -> Optional[str]:
        return None if self.render is None else self.render.base_output_stem

    @property
    def stitched_documents(self) -> Dict[str, str]:
        return self.stitching.documents

    @property
    def stitched_audio_path(self) -> Optional[str]:
        return self.stitching.audio_path

    @property
    def stitched_video_path(self) -> Optional[str]:
        return self.stitching.video_path

    @property
    def book_metadata(self) -> Dict[str, Any]:
        return self.metadata.as_dict()


def run_pipeline(request: PipelineRequest) -> PipelineResponse:
    """Execute the ebook pipeline for the provided :class:`PipelineRequest`."""

    context = request.context or cfg.build_runtime_context(
        request.config, request.environment_overrides
    )
    request.context = context
    cfg.set_runtime_context(context)

    tracker = request.progress_tracker

    correlation_id = request.correlation_id or str(uuid4())
    request.correlation_id = correlation_id
    pipeline_attrs = PipelineAttributes(
        correlation_id=correlation_id,
        job_id=request.job_id,
        input_file=request.inputs.input_file,
    )

    config_result: Optional[ConfigPhaseResult] = None
    metadata_result: Optional[MetadataPhaseResult] = None
    render_result: Optional[RenderResult] = None
    stitching_result = StitchingArtifacts()
    metadata = request.inputs.book_metadata

    try:
        config_result = config_phase.prepare_configuration(request, context)
        metadata = metadata_phase.prepare_metadata(request, context)

        if tracker is not None:
            tracker.publish_start(
                {
                    "stage": "initialization",
                    "input_file": request.inputs.input_file,
                    "target_languages": tuple(request.inputs.target_languages),
                }
            )

        with log_mgr.log_context(
            correlation_id=correlation_id, job_id=request.job_id
        ):
            logger.info(
                "Pipeline execution started",
                extra={
                    "event": "pipeline.run.start",
                    "attributes": {
                        "input_file": request.inputs.input_file,
                        "base_output_file": request.inputs.base_output_file,
                        "target_languages": request.inputs.target_languages,
                        "sentences_per_output_file": request.inputs.sentences_per_output_file,
                        "start_sentence": request.inputs.start_sentence,
                        "end_sentence": request.inputs.end_sentence,
                    },
                    "console_suppress": True,
                },
            )

        with observability.pipeline_operation(
            "pipeline", attributes=pipeline_attrs.as_dict()
        ):
            with observability.pipeline_stage(
                "ingestion",
                {
                    **pipeline_attrs.as_dict(),
                    "target_languages": tuple(request.inputs.target_languages),
                },
            ):
                metadata_result = metadata_phase.run_ingestion(
                    request, config_result, metadata, tracker
                )
                if metadata_result.ingestion.refined_updated:
                    refined_output_path = ingestion.refined_list_output_path(
                        request.inputs.input_file, config_result.pipeline_config
                    )
                    logger.info(
                        "Refined sentence list written",
                        extra={
                            "event": "pipeline.ingestion.refined_output",
                            "attributes": {
                                "path": str(refined_output_path),
                                "total_sentences": metadata_result.ingestion.total_sentences,
                            },
                            "console_suppress": True,
                        },
                    )

            with observability.pipeline_stage(
                "rendering",
                {
                    **pipeline_attrs.as_dict(),
                    "total_sentences": metadata_result.ingestion.total_sentences,
                },
            ):
                render_result = render_phase.execute_render_phase(
                    request, config_result, metadata_result, tracker
                )

            post_process_attrs = {
                **pipeline_attrs.as_dict(),
                "base_dir": render_result.base_dir or "",
            }
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
            elif request.inputs.stitch_full:
                with observability.pipeline_stage("stitching", post_process_attrs):
                    stitching_result = render_phase.build_stitching_artifacts(
                        request, config_result, metadata_result, render_result
                    )

        with log_mgr.log_context(
            correlation_id=correlation_id, job_id=request.job_id
        ):
            logger.info(
                "Pipeline execution completed",
                extra={
                    "event": "pipeline.run.complete",
                    "status": "success",
                    "console_suppress": True,
                },
            )

        generated_files = tracker.get_generated_files() if tracker is not None else {}

        return PipelineResponse(
            success=True,
            pipeline_config=config_result.pipeline_config,
            ingestion=metadata_result.ingestion,
            render=render_result,
            stitching=stitching_result,
            metadata=metadata_result.metadata,
            generated_files=generated_files,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        with log_mgr.log_context(
            correlation_id=correlation_id, job_id=request.job_id
        ):
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
        metadata_payload = metadata_result.metadata if metadata_result else metadata
        generated_files = tracker.get_generated_files() if tracker is not None else {}

        return PipelineResponse(
            success=False,
            pipeline_config=(
                config_result.pipeline_config if config_result else None
            ),
            metadata=metadata_payload,
            generated_files=generated_files,
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
        "llm_source": config.llm_source,
        "local_ollama_url": config.local_ollama_url,
        "cloud_ollama_url": config.cloud_ollama_url,
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
        "highlight_granularity": config.highlight_granularity,
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
        "generated_files": copy.deepcopy(response.generated_files),
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

    payload["inputs"]["book_metadata"] = request.inputs.book_metadata.as_dict()

    if request.correlation_id is not None:
        payload["correlation_id"] = request.correlation_id

    return payload


class PipelineService:
    """High-level orchestration API for the ebook processing pipeline."""

    def __init__(self, job_manager: "PipelineJobManager") -> None:
        self._job_manager = job_manager

    def enqueue(
        self,
        request: PipelineRequest,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> "PipelineJob":
        """Submit ``request`` for background execution and return the job handle."""

        return self._job_manager.submit(request, user_id=user_id, user_role=user_role)

    def get_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> "PipelineJob":
        """Return the job associated with ``job_id``."""

        return self._job_manager.get(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )

    def list_jobs(
        self,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> Dict[str, "PipelineJob"]:
        """Return a mapping of all known job handles."""

        return self._job_manager.list(user_id=user_id, user_role=user_role)

    def pause_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> "PipelineJob":
        """Pause the specified job and return the updated handle."""

        return self._job_manager.pause_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )

    def resume_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> "PipelineJob":
        """Resume the specified job and return the updated handle."""

        return self._job_manager.resume_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )

    def cancel_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> "PipelineJob":
        """Cancel the specified job and return the updated handle."""

        return self._job_manager.cancel_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )

    def delete_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> "PipelineJob":
        """Delete the specified job from persistence and return its final snapshot."""

        return self._job_manager.delete_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )

    def run_sync(self, request: PipelineRequest) -> PipelineResponse:
        """Execute ``request`` synchronously and return the pipeline response."""

        return run_pipeline(request)

    def refresh_metadata(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> "PipelineJob":
        """Force-refresh metadata for the specified job and return the updated handle."""

        return self._job_manager.refresh_metadata(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )
