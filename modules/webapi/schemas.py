"""Pydantic schemas for the FastAPI web backend."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from ..core.config import PipelineConfig
from ..progress_tracker import ProgressEvent, ProgressSnapshot
from ..services.pipeline_service import PipelineInput, PipelineRequest, PipelineResponse
from .jobs import PipelineJob, PipelineJobStatus


class PipelineInputPayload(BaseModel):
    """Public schema representing :class:`PipelineInput`."""

    input_file: str
    base_output_file: str
    input_language: str
    target_languages: List[str]
    sentences_per_output_file: int = 10
    start_sentence: int = 1
    end_sentence: Optional[int] = None
    stitch_full: bool = False
    generate_audio: bool = True
    audio_mode: str = "1"
    written_mode: str = "4"
    selected_voice: str = "gTTS"
    output_html: bool = True
    output_pdf: bool = False
    generate_video: bool = False
    include_transliteration: bool = False
    tempo: float = 1.0
    book_metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dataclass(self) -> PipelineInput:
        payload = self.model_dump()
        return PipelineInput(**payload)


class PipelineDefaultsResponse(BaseModel):
    """Response payload exposing the resolved baseline configuration."""

    config: Dict[str, Any] = Field(default_factory=dict)


class PipelineMetadataRequest(BaseModel):
    """Request payload for inferring metadata for an input file."""

    input_file: str
    force_refresh: bool = False
    existing_metadata: Dict[str, Any] = Field(default_factory=dict)


class PipelineMetadataResponse(BaseModel):
    """Response payload containing inferred metadata for an input file."""

    metadata: Dict[str, Any] = Field(default_factory=dict)


class PipelineRequestPayload(BaseModel):
    """Schema mirroring :class:`PipelineRequest` for incoming submissions."""

    config: Dict[str, Any] = Field(default_factory=dict)
    environment_overrides: Dict[str, Any] = Field(default_factory=dict)
    pipeline_overrides: Dict[str, Any] = Field(default_factory=dict)
    inputs: PipelineInputPayload
    correlation_id: Optional[str] = None

    def to_pipeline_request(
        self,
        *,
        context=None,
        resolved_config: Optional[Dict[str, Any]] = None,
    ) -> PipelineRequest:
        return PipelineRequest(
            config=dict(resolved_config) if resolved_config is not None else dict(self.config),
            context=context,
            environment_overrides=dict(self.environment_overrides),
            pipeline_overrides=dict(self.pipeline_overrides),
            inputs=self.inputs.to_dataclass(),
            correlation_id=self.correlation_id,
        )


class PipelineSubmissionResponse(BaseModel):
    """Response payload after submitting a pipeline job."""

    job_id: str
    status: PipelineJobStatus
    created_at: datetime


class PipelineResponsePayload(BaseModel):
    """Serializable representation of :class:`PipelineResponse`."""

    success: Optional[bool] = None
    pipeline_config: Optional[Dict[str, Any]] = None
    refined_sentences: Optional[List[str]] = None
    refined_updated: bool = False
    written_blocks: Optional[List[str]] = None
    audio_segments: Optional[List[float]] = None
    batch_video_files: Optional[List[str]] = None
    batch_previews: Optional[List[str]] = None
    base_dir: Optional[str] = None
    base_output_stem: Optional[str] = None
    stitched_documents: Dict[str, str] = Field(default_factory=dict)
    stitched_audio_path: Optional[str] = None
    stitched_video_path: Optional[str] = None
    book_metadata: Dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def _serialize_pipeline_config(config: PipelineConfig) -> Dict[str, Any]:
        data = {
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
        return data

    @classmethod
    def from_response(cls, response: PipelineResponse) -> "PipelineResponsePayload":
        audio_segments: Optional[List[float]] = None
        if response.audio_segments:
            audio_segments = [segment.duration_seconds for segment in response.audio_segments]

        pipeline_config_data: Optional[Dict[str, Any]] = None
        if response.pipeline_config is not None:
            pipeline_config_data = cls._serialize_pipeline_config(response.pipeline_config)

        return cls(
            success=response.success,
            pipeline_config=pipeline_config_data,
            refined_sentences=response.refined_sentences,
            refined_updated=response.refined_updated,
            written_blocks=response.written_blocks,
            audio_segments=audio_segments,
            batch_video_files=response.batch_video_files,
            base_dir=str(response.base_dir) if response.base_dir else None,
            base_output_stem=response.base_output_stem,
            stitched_documents=dict(response.stitched_documents),
            stitched_audio_path=response.stitched_audio_path,
            stitched_video_path=response.stitched_video_path,
            book_metadata=dict(response.book_metadata),
        )


class ProgressSnapshotPayload(BaseModel):
    """Serializable payload for :class:`ProgressSnapshot`."""

    completed: int
    total: Optional[int]
    elapsed: float
    speed: float
    eta: Optional[float]

    @classmethod
    def from_snapshot(cls, snapshot: ProgressSnapshot) -> "ProgressSnapshotPayload":
        return cls(
            completed=snapshot.completed,
            total=snapshot.total,
            elapsed=snapshot.elapsed,
            speed=snapshot.speed,
            eta=snapshot.eta,
        )


class ProgressEventPayload(BaseModel):
    """Serializable payload for :class:`ProgressEvent`."""

    event_type: str
    timestamp: float
    metadata: Dict[str, Any]
    snapshot: ProgressSnapshotPayload
    error: Optional[str] = None

    @classmethod
    def from_event(cls, event: ProgressEvent) -> "ProgressEventPayload":
        metadata = dict(event.metadata)
        error_message = None
        if event.error is not None:
            error_message = str(event.error)
        return cls(
            event_type=event.event_type,
            timestamp=event.timestamp,
            metadata=metadata,
            snapshot=ProgressSnapshotPayload.from_snapshot(event.snapshot),
            error=error_message,
        )


class PipelineStatusResponse(BaseModel):
    """Full status payload for a pipeline job."""

    job_id: str
    status: PipelineJobStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[PipelineResponsePayload]
    error: Optional[str]
    latest_event: Optional[ProgressEventPayload]
    tuning: Optional[Dict[str, Any]] = None

    @classmethod
    def from_job(cls, job: PipelineJob) -> "PipelineStatusResponse":
        result_payload: Optional[PipelineResponsePayload] = None
        if job.result is not None:
            result_payload = PipelineResponsePayload.from_response(job.result)
        elif job.result_payload is not None:
            result_payload = PipelineResponsePayload(**job.result_payload)

        latest_event = None
        if job.last_event is not None:
            latest_event = ProgressEventPayload.from_event(job.last_event)

        return cls(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            result=result_payload,
            error=job.error_message,
            latest_event=latest_event,
            tuning=dict(job.tuning_summary) if job.tuning_summary else None,
        )


class PipelineJobListResponse(BaseModel):
    """Response payload describing a collection of pipeline jobs."""

    jobs: List[PipelineStatusResponse] = Field(default_factory=list)


class PipelineJobActionResponse(BaseModel):
    """Response payload for job lifecycle mutations."""

    job: PipelineStatusResponse
    error: Optional[str] = None


class PipelineFileEntry(BaseModel):
    """Describes a selectable file within the dashboard."""

    name: str
    path: str
    type: Literal["file", "directory"]


class PipelineFileBrowserResponse(BaseModel):
    """Response payload listing available ebook and output files."""

    ebooks: List[PipelineFileEntry] = Field(default_factory=list)
    outputs: List[PipelineFileEntry] = Field(default_factory=list)
    books_root: str = ""
    output_root: str = ""
