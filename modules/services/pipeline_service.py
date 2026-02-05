"""Service layer for executing the ebook processing pipeline."""

from __future__ import annotations

import copy
import json
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Mapping, Optional, Tuple
from uuid import uuid4

from .. import config_manager as cfg
from .. import logging_manager as log_mgr
from .. import metadata_manager
from .. import observability
from ..permissions import merge_access_policy, resolve_access_policy
from ..core import ingestion
from ..core.config import PipelineConfig
from ..progress_tracker import ProgressTracker
from ..translation_engine import ThreadWorkerPool
from .pipeline_phases import config_phase, lookup_cache_phase, metadata_phase, render_phase
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
    add_images: bool
    include_transliteration: bool
    tempo: float
    translation_provider: str = "llm"
    translation_batch_size: int = 10
    transliteration_mode: str = "default"
    transliteration_model: Optional[str] = None
    enable_lookup_cache: bool = True
    lookup_cache_batch_size: int = 10
    book_metadata: PipelineMetadata = field(default_factory=PipelineMetadata)
    voice_overrides: Dict[str, str] = field(default_factory=dict)
    audio_bitrate_kbps: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.book_metadata, PipelineMetadata):
            self.book_metadata = PipelineMetadata.from_mapping(self.book_metadata)
        if not isinstance(self.voice_overrides, dict):
            self.voice_overrides = {}
        else:
            sanitized: Dict[str, str] = {}
            for key, value in self.voice_overrides.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    continue
                normalized_key = key.strip()
                normalized_value = value.strip()
                if not normalized_key or not normalized_value:
                    continue
                sanitized[normalized_key] = normalized_value
            self.voice_overrides = sanitized
        try:
            batch_size = int(self.translation_batch_size)
        except (TypeError, ValueError):
            batch_size = 1
        self.translation_batch_size = max(1, batch_size)


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

            # Signal that media is ready for playback (before lookup cache builds)
            if tracker is not None:
                tracker.publish_progress(
                    {
                        "stage": "media_ready",
                        "message": "Media generation complete. Content is ready for playback.",
                        "media_ready": True,
                    }
                )

            # Build lookup cache in background if enabled (non-blocking)
            if not (request.stop_event and request.stop_event.is_set()):
                enable_cache = getattr(request.inputs, "enable_lookup_cache", True)
                if enable_cache:
                    # Run lookup cache in background thread so playback can start immediately
                    def _build_lookup_cache_background():
                        try:
                            if tracker is not None:
                                tracker.publish_progress(
                                    {
                                        "stage": "lookup_cache",
                                        "message": "Building word lookup cache in background...",
                                        "lookup_cache_status": "building",
                                    }
                                )
                            with observability.pipeline_stage("lookup_cache", post_process_attrs):
                                lookup_cache_phase.build_lookup_cache_phase(
                                    request, config_result, render_result, tracker
                                )
                            if tracker is not None:
                                tracker.publish_progress(
                                    {
                                        "stage": "lookup_cache",
                                        "message": "Word lookup cache complete.",
                                        "lookup_cache_status": "complete",
                                    }
                                )
                        except Exception as cache_exc:
                            logger.warning(
                                f"Lookup cache build failed (non-fatal): {cache_exc}",
                                extra={"event": "pipeline.lookup_cache.error"},
                            )
                            if tracker is not None:
                                tracker.publish_progress(
                                    {
                                        "stage": "lookup_cache",
                                        "message": f"Lookup cache failed: {cache_exc}",
                                        "lookup_cache_status": "error",
                                    }
                                )

                    cache_thread = threading.Thread(
                        target=_build_lookup_cache_background,
                        name=f"lookup-cache-{request.job_id}",
                        daemon=True,
                    )
                    cache_thread.start()
                    # Don't wait for the thread - let it run in background

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
        "audio_bitrate_kbps": getattr(config, "audio_bitrate_kbps", None),
        "selected_voice": config.selected_voice,
        "audio_api_base_url": config.audio_api_base_url,
        "audio_api_timeout_seconds": config.audio_api_timeout_seconds,
        "audio_api_poll_interval_seconds": config.audio_api_poll_interval_seconds,
        "tts_backend": config.tts_backend,
        "tts_executable_path": config.tts_executable_path,
        "say_path": config.say_path,
        "tempo": config.tempo,
        "macos_reading_speed": config.macos_reading_speed,
        "sync_ratio": config.sync_ratio,
        "word_highlighting": config.word_highlighting,
        "highlight_granularity": config.highlight_granularity,
        "image_api_base_url": config.image_api_base_url,
        "image_api_base_urls": list(config.image_api_base_urls),
        "image_api_timeout_seconds": config.image_api_timeout_seconds,
        "image_concurrency": config.image_concurrency,
        "image_width": config.image_width,
        "image_height": config.image_height,
        "image_steps": config.image_steps,
        "image_cfg_scale": config.image_cfg_scale,
        "image_sampler_name": config.image_sampler_name,
        "image_style_template": getattr(config, "image_style_template", None),
        "image_prompt_pipeline": getattr(config, "image_prompt_pipeline", None),
        "image_prompt_batching_enabled": getattr(config, "image_prompt_batching_enabled", None),
        "image_prompt_batch_size": getattr(config, "image_prompt_batch_size", None),
        "image_prompt_plan_batch_size": getattr(config, "image_prompt_plan_batch_size", None),
        "image_blank_detection_enabled": getattr(config, "image_blank_detection_enabled", None),
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


@dataclass(slots=True)
class InitialMetadataSnapshot:
    """Captured artefacts created when a job is submitted."""

    book_metadata: Dict[str, Any]
    refined_sentences: List[str]


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

        metadata_snapshot = self._prepare_submission_metadata(request)
        config = request.config

        job = self._job_manager.submit(request, user_id=user_id, user_role=user_role)

        if metadata_snapshot is not None:
            try:
                self._job_manager.apply_initial_metadata(job.job_id, metadata_snapshot.book_metadata)
            except Exception:  # pragma: no cover - best-effort update
                logger.debug("Unable to register initial job metadata", exc_info=True)
            try:
                self._persist_initial_metadata(job.job_id, metadata_snapshot, request)
            except Exception:  # pragma: no cover - filesystem/log noise
                logger.debug("Unable to persist initial metadata snapshot", exc_info=True)

        try:
            use_ramdisk = bool(config.get("use_ramdisk"))
        except Exception:
            use_ramdisk = False

        try:
            auto_metadata = bool(config.get("auto_metadata", True))
        except Exception:
            auto_metadata = True

        if use_ramdisk and not auto_metadata:
            logger.info(
                "Releasing RAM disk for job with auto_metadata disabled",
                extra={
                    "event": "pipeline.enqueue.release_ramdisk",
                    "job_id": job.job_id,
                    "console_suppress": True,
                },
            )
            cfg.cleanup_environment(request.context)

        return job

    def get_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        permission: str = "view",
    ) -> "PipelineJob":
        """Return the job associated with ``job_id``."""

        return self._job_manager.get(
            job_id,
            user_id=user_id,
            user_role=user_role,
            permission=permission,
        )

    def update_job_access(
        self,
        job_id: str,
        *,
        visibility: Optional[str] = None,
        grants: Optional[Iterable[Mapping[str, Any]]] = None,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> "PipelineJob":
        """Update the access policy for ``job_id`` and return the updated job."""

        def _mutate(job: "PipelineJob") -> None:
            default_visibility = "private" if job.user_id else "public"
            existing = resolve_access_policy(job.access, default_visibility=default_visibility)
            merged = merge_access_policy(
                existing,
                visibility=visibility,
                grants=grants,
                actor_id=user_id,
            )
            job.access = merged.to_dict()

        return self._job_manager.mutate_job(
            job_id,
            _mutate,
            user_id=user_id,
            user_role=user_role,
        )

    def list_jobs(
        self,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, "PipelineJob"]:
        """Return a mapping of all known job handles.

        Args:
            user_id: User ID for access filtering.
            user_role: User role for access filtering.
            offset: Number of jobs to skip (pagination).
            limit: Maximum number of jobs to return.
        """

        return self._job_manager.list(
            user_id=user_id,
            user_role=user_role,
            offset=offset,
            limit=limit,
        )

    def count_jobs(
        self,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> int:
        """Return total number of jobs visible to the user."""

        return self._job_manager.count(user_id=user_id, user_role=user_role)

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

    def restart_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> "PipelineJob":
        """Restart a completed/failed job with the same settings, wiping generated outputs."""

        return self._job_manager.restart_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )

    def _prepare_submission_metadata(self, request: PipelineRequest) -> Optional[InitialMetadataSnapshot]:
        context = request.context
        if context is None:
            return None

        input_file = request.inputs.input_file
        placeholder_checker = getattr(metadata_manager, "_is_placeholder", None)

        def is_placeholder(key: str, value: object) -> bool:
            if callable(placeholder_checker):
                try:
                    return bool(placeholder_checker(key, value))  # type: ignore[misc]
                except Exception:  # pragma: no cover - defensive guard
                    pass
            if value is None:
                return True
            if isinstance(value, str):
                cleaned = value.strip()
                if not cleaned:
                    return True
                return cleaned.casefold() in {"unknown", "unknown title", "book"}
            return False

        base_metadata = request.inputs.book_metadata.as_dict()

        config_metadata: Dict[str, Any] = {}
        config = request.config or {}
        config_book_metadata = config.get("book_metadata")
        if isinstance(config_book_metadata, Mapping):
            config_metadata.update(
                {
                    key: value
                    for key, value in config_book_metadata.items()
                    if value not in (None, "")
                }
            )

        for key in (
            "book_title",
            "book_author",
            "book_year",
            "book_summary",
            "book_cover_file",
            "book_cover_title",
        ):
            value = config.get(key)
            if value not in (None, ""):
                config_metadata.setdefault(key, value)

        merged_metadata = dict(base_metadata)
        for key, value in config_metadata.items():
            if is_placeholder(key, merged_metadata.get(key)) and not is_placeholder(key, value):
                merged_metadata[key] = value

        request.inputs.book_metadata = PipelineMetadata.from_mapping(merged_metadata)

        try:
            inferred_metadata = metadata_manager.infer_metadata(
                input_file,
                existing_metadata=request.inputs.book_metadata.as_dict(),
                force_refresh=False,
            )
        except Exception:
            logger.debug("Unable to infer book metadata during submission", exc_info=True)
            inferred_metadata = request.inputs.book_metadata.as_dict()

        request.inputs.book_metadata = PipelineMetadata.from_mapping(inferred_metadata)

        refined_sentences: List[str] = []
        try:
            config_result = config_phase.prepare_configuration(request, context)
            pipeline_config = config_result.pipeline_config
            refined, _ = ingestion.get_refined_sentences(
                input_file,
                pipeline_config,
                force_refresh=False,
                metadata={
                    "mode": "api",
                    "target_languages": request.inputs.target_languages,
                    "max_words": pipeline_config.max_words,
                },
            )
            refined_sentences = list(refined)
        except Exception:
            logger.debug("Unable to generate refined sentences during submission", exc_info=True)

        if not inferred_metadata and not refined_sentences:
            return None

        return InitialMetadataSnapshot(
            book_metadata=inferred_metadata,
            refined_sentences=refined_sentences,
        )

    def _persist_initial_metadata(
        self,
        job_id: str,
        snapshot: InitialMetadataSnapshot,
        request: PipelineRequest,
    ) -> None:
        locator = self._job_manager.file_locator
        root = locator.resolve_metadata_path(job_id)
        root.mkdir(parents=True, exist_ok=True)

        metadata_path = locator.resolve_metadata_path(job_id, "book.json")
        sentences_path = locator.resolve_metadata_path(job_id, "sentences.json")
        request_path = locator.resolve_metadata_path(job_id, "request.json")
        config_path = locator.resolve_metadata_path(job_id, "config.json")

        metadata_path.write_text(
            json.dumps(snapshot.book_metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        sentences_path.write_text(
            json.dumps(snapshot.refined_sentences, indent=2),
            encoding="utf-8",
        )

        serialized_request = serialize_pipeline_request(request)
        request_path.write_text(
            json.dumps(serialized_request, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        config_snapshot = {
            "config": request.config,
            "environment_overrides": request.environment_overrides,
            "pipeline_overrides": request.pipeline_overrides,
        }
        config_path.write_text(
            json.dumps(config_snapshot, indent=2, sort_keys=True),
            encoding="utf-8",
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

    def enrich_metadata(
        self,
        job_id: str,
        *,
        force: bool = False,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> Tuple["PipelineJob", Dict[str, Any]]:
        """Enrich job metadata from external sources without re-extracting from EPUB.

        Returns:
            Tuple of (updated job, enrichment info dict).
        """
        return self._job_manager.enrich_metadata(
            job_id,
            force=force,
            user_id=user_id,
            user_role=user_role,
        )
