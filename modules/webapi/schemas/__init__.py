"""Pydantic schemas for the FastAPI web backend."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
import copy
from typing import Any, Dict, List, Literal, Optional

from PIL import Image
from pydantic import Base64Bytes, BaseModel, ConfigDict, Field, field_validator, model_validator

from ...core.config import PipelineConfig
from ...progress_tracker import ProgressEvent, ProgressSnapshot
from ...services.file_locator import FileLocator
from ...services.pipeline_service import PipelineInput, PipelineRequest, PipelineResponse
from ...video.backends import VideoRenderOptions
from ...video.jobs import (
    VideoAudioSource,
    VideoJob,
    VideoJobResult,
    VideoJobStatus,
    VideoRenderTask,
)
from ...video.slide_renderer import SlideRenderOptions
from ..jobs import PipelineJob, PipelineJobStatus
from .audio import GTTSLanguage, MacOSVoice, VoiceInventoryResponse, VoiceMatchResponse


class SessionUserPayload(BaseModel):
    """Lightweight description of an authenticated user."""

    username: str
    role: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    last_login: Optional[str] = None


class SessionStatusResponse(BaseModel):
    """Response payload returned for active session lookups."""

    token: str
    user: SessionUserPayload


class LoginRequestPayload(BaseModel):
    """Incoming payload for the login endpoint."""

    username: str
    password: str


class PasswordChangeRequestPayload(BaseModel):
    """Payload for updating the authenticated user's password."""

    current_password: str
    new_password: str


class ManagedUserPayload(BaseModel):
    """Public representation of a stored user account."""

    username: str
    roles: List[str] = Field(default_factory=list)
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: Optional[Literal["active", "suspended", "inactive"]] = None
    is_active: Optional[bool] = None
    is_suspended: Optional[bool] = None
    last_login: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserListResponse(BaseModel):
    """Envelope returned when listing user accounts."""

    users: List[ManagedUserPayload] = Field(default_factory=list)


class UserAccountResponse(BaseModel):
    """Envelope returned when a single account is mutated or retrieved."""

    user: ManagedUserPayload


class UserCreateRequestPayload(BaseModel):
    """Payload for provisioning a new managed user."""

    username: str
    password: str
    roles: List[str] = Field(default_factory=list)
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserUpdateRequestPayload(BaseModel):
    """Payload for updating profile metadata for an existing managed user."""

    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserPasswordResetRequestPayload(BaseModel):
    """Payload for administrators resetting another user's password."""

    password: str


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
    voice_overrides: Dict[str, str] = Field(default_factory=dict)
    book_metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dataclass(self) -> PipelineInput:
        payload = self.model_dump()
        return PipelineInput(**payload)


class PipelineDefaultsResponse(BaseModel):
    """Response payload exposing the resolved baseline configuration."""

    config: Dict[str, Any] = Field(default_factory=dict)


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
    base_dir: Optional[str] = None
    base_output_stem: Optional[str] = None
    stitched_documents: Dict[str, str] = Field(default_factory=dict)
    stitched_audio_path: Optional[str] = None
    stitched_video_path: Optional[str] = None
    book_metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_files: Dict[str, Any] = Field(default_factory=dict)

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
            "audio_api_base_url": config.audio_api_base_url,
            "audio_api_timeout_seconds": config.audio_api_timeout_seconds,
            "audio_api_poll_interval_seconds": config.audio_api_poll_interval_seconds,
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
            generated_files=copy.deepcopy(response.generated_files),
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
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    generated_files: Optional[Dict[str, Any]] = None

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

        generated_files = None
        if job.generated_files is not None:
            generated_files = copy.deepcopy(job.generated_files)

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
            user_id=job.user_id,
            user_role=job.user_role,
            generated_files=generated_files,
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


class PipelineMediaFile(BaseModel):
    """Describes generated media metadata for a job."""

    name: str
    url: Optional[str] = None
    size: Optional[int] = None
    updated_at: Optional[datetime] = None
    source: Literal["completed", "live"]
    relative_path: Optional[str] = None
    path: Optional[str] = None


class PipelineMediaResponse(BaseModel):
    """Response payload grouping generated media by type."""

    media: Dict[str, List[PipelineMediaFile]] = Field(default_factory=dict)


class MediaSearchHit(BaseModel):
    """Single search match across generated ebook media."""

    job_id: str
    job_label: Optional[str] = None
    base_id: Optional[str] = None
    chunk_id: Optional[str] = None
    range_fragment: Optional[str] = None
    start_sentence: Optional[int] = None
    end_sentence: Optional[int] = None
    snippet: str
    occurrence_count: int = Field(default=0, ge=0)
    match_start: Optional[int] = None
    match_end: Optional[int] = None
    text_length: Optional[int] = None
    offset_ratio: Optional[float] = None
    approximate_time_seconds: Optional[float] = None
    media: Dict[str, List[PipelineMediaFile]] = Field(default_factory=dict)


class MediaSearchResponse(BaseModel):
    """Response payload for media search queries."""

    query: str
    limit: int
    count: int
    results: List[MediaSearchHit] = Field(default_factory=list)


class AudioSynthesisRequest(BaseModel):
    """Payload describing a text-to-speech synthesis request."""

    text: str = Field(..., description="Text content that should be spoken aloud.")
    voice: Optional[str] = Field(
        default=None,
        description="Optional voice identifier understood by the configured backend.",
    )
    speed: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Optional speaking rate hint expressed as words per minute.",
    )
    language: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=16,
        description="Optional language code override for synthesis (e.g. 'en' or 'es').",
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Text must not be empty.")
        return value.strip()

    @field_validator("voice")
    @classmethod
    def _validate_voice(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("Voice must not be empty when provided.")
        return value.strip()

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Language must not be empty when provided.")
        return stripped


class AudioSynthesisError(BaseModel):
    """Standard error payload returned by audio synthesis routes."""

    error: str = Field(..., description="Stable error identifier.")
    message: str = Field(..., description="Human readable explanation of the error.")


class VideoImageReference(BaseModel):
    """Reference to a cover image used for video rendering."""

    data: Base64Bytes | None = Field(
        default=None,
        description="Optional base64-encoded image bytes.",
    )
    job_id: str | None = Field(
        default=None,
        description="Identifier of the job providing a stored cover image.",
    )
    relative_path: str | None = Field(
        default=None,
        description="Relative path to the stored cover image.",
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_reference(self) -> "VideoImageReference":
        has_data = self.data is not None
        has_path = self.relative_path is not None
        if has_data == has_path:
            raise ValueError(
                "Image reference must include either inline data or a relative path."
            )
        if has_path and not self.job_id:
            raise ValueError("Image references using a path must include the source job_id.")
        return self

    def resolve(self, locator: FileLocator) -> Image.Image:
        """Return a loaded :class:`PIL.Image.Image` for this reference."""

        if self.data is not None:
            with Image.open(BytesIO(bytes(self.data))) as image:
                loaded = image.convert("RGB")
                loaded.load()
                return loaded

        assert self.job_id is not None  # for type checkers
        assert self.relative_path is not None
        image_path = locator.resolve_path(self.job_id, self.relative_path)
        with Image.open(image_path) as image:
            loaded = image.convert("RGB")
            loaded.load()
            return loaded


class VideoAudioSourcePayload(BaseModel):
    """Description of a single audio track used for video rendering."""

    data: Base64Bytes | None = Field(
        default=None,
        description="Optional base64-encoded audio data.",
    )
    job_id: str | None = Field(
        default=None,
        description="Identifier of the job containing the referenced audio file.",
    )
    relative_path: str | None = Field(
        default=None,
        description="Relative path to a stored audio file.",
    )
    mime_type: str | None = Field(
        default=None,
        description="Optional MIME type hint used to decode the audio.",
    )
    format: str | None = Field(
        default=None,
        description="Explicit audio format hint (e.g. 'mp3' or 'wav').",
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_source(self) -> "VideoAudioSourcePayload":
        has_data = self.data is not None
        has_path = self.relative_path is not None
        if has_data == has_path:
            raise ValueError(
                "Audio source must include either inline data or a relative path."
            )
        if has_path and not self.job_id:
            raise ValueError("Audio sources referencing files must include the source job_id.")
        return self

    def to_source(self, locator: FileLocator) -> VideoAudioSource:
        """Convert this payload into a :class:`VideoAudioSource`."""

        if self.data is not None:
            return VideoAudioSource(
                data=bytes(self.data),
                mime_type=self.mime_type,
                format_hint=self.format,
            )

        assert self.job_id is not None  # for mypy/type checkers
        assert self.relative_path is not None
        audio_path = locator.resolve_path(self.job_id, self.relative_path)
        return VideoAudioSource(
            path=audio_path,
            mime_type=self.mime_type,
            format_hint=self.format,
        )


class VideoRenderOptionsPayload(BaseModel):
    """Public schema mirroring :class:`VideoRenderOptions`."""

    batch_start: int | None = Field(
        default=None,
        description="Sentence number of the first slide in the batch.",
    )
    batch_end: int | None = Field(
        default=None,
        description="Sentence number of the final slide in the batch.",
    )
    cover_image: VideoImageReference | None = Field(
        default=None,
        description="Optional cover image overriding the pipeline default.",
    )
    book_author: str = ""
    book_title: str = ""
    cumulative_word_counts: List[int] | None = None
    total_word_count: int | None = None
    macos_reading_speed: int | None = None
    input_language: str = ""
    total_sentences: int | None = None
    tempo: float | None = None
    sync_ratio: float = 1.0
    word_highlighting: bool = True
    highlight_granularity: str = "word"
    voice_name: str = ""
    voice_lines: List[str] = Field(default_factory=list)
    slide_render_options: Dict[str, Any] | None = None
    cleanup: bool = True
    slide_size: List[int] = Field(default_factory=lambda: [1280, 720])
    initial_font_size: int = 60
    bg_color: List[int] | None = None
    template_name: str | None = None
    default_font_path: str | None = None

    model_config = ConfigDict(extra="forbid")

    def to_render_options(
        self,
        locator: FileLocator,
        *,
        slides_count: int,
    ) -> VideoRenderOptions:
        """Convert the payload into a :class:`VideoRenderOptions` instance."""

        if slides_count <= 0:
            raise ValueError("At least one slide is required to render video output.")

        batch_start = self.batch_start if self.batch_start is not None else 1
        batch_end = (
            self.batch_end
            if self.batch_end is not None
            else batch_start + max(slides_count - 1, 0)
        )

        cover_image = self.cover_image.resolve(locator) if self.cover_image else None

        slide_options = None
        if self.slide_render_options is not None:
            slide_options = SlideRenderOptions(**self.slide_render_options)

        bg_color = tuple(self.bg_color) if self.bg_color is not None else None
        slide_size = tuple(self.slide_size)

        return VideoRenderOptions(
            batch_start=batch_start,
            batch_end=batch_end,
            cover_image=cover_image,
            book_author=self.book_author,
            book_title=self.book_title,
            cumulative_word_counts=list(self.cumulative_word_counts)
            if self.cumulative_word_counts is not None
            else None,
            total_word_count=self.total_word_count,
            macos_reading_speed=self.macos_reading_speed,
            input_language=self.input_language,
            total_sentences=self.total_sentences,
            tempo=self.tempo,
            sync_ratio=self.sync_ratio,
            word_highlighting=self.word_highlighting,
            highlight_granularity=self.highlight_granularity,
            voice_name=self.voice_name,
            voice_lines=list(self.voice_lines),
            slide_render_options=slide_options,
            cleanup=self.cleanup,
            slide_size=slide_size,
            initial_font_size=self.initial_font_size,
            bg_color=bg_color,
            template_name=self.template_name,
            default_font_path=self.default_font_path,
        )


class VideoRenderRequestPayload(BaseModel):
    """Incoming payload describing a standalone video rendering job."""

    slides: List[str] = Field(
        ..., min_length=1, description="Ordered list of slide text blocks."
    )
    audio: List[VideoAudioSourcePayload] = Field(
        ..., min_length=1, description="Audio tracks corresponding to each slide."
    )
    output_filename: str | None = Field(
        default=None,
        description="Desired filename for the rendered video (relative to the job root).",
    )
    options: VideoRenderOptionsPayload | None = Field(
        default=None,
        description="Optional rendering configuration overrides.",
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_lengths(self) -> "VideoRenderRequestPayload":
        if len(self.slides) != len(self.audio):
            raise ValueError("Each slide must include a matching audio track.")
        return self

    def to_task(self, locator: FileLocator) -> VideoRenderTask:
        """Convert this payload into a :class:`VideoRenderTask`."""

        slides = [segment for segment in self.slides]
        audio_sources = [entry.to_source(locator) for entry in self.audio]
        options_payload = self.options or VideoRenderOptionsPayload()
        options = options_payload.to_render_options(locator, slides_count=len(slides))
        output_name = (self.output_filename or "rendered.mp4").strip() or "rendered.mp4"
        return VideoRenderTask(
            slides=slides,
            audio_sources=audio_sources,
            options=options,
            output_filename=output_name,
        )


class VideoJobResultPayload(BaseModel):
    """Serializable representation of :class:`VideoJobResult`."""

    path: str
    relative_path: str
    url: str | None = None

    @classmethod
    def from_result(cls, result: VideoJobResult) -> "VideoJobResultPayload":
        return cls(
            path=str(result.path),
            relative_path=result.relative_path,
            url=result.url,
        )


class VideoJobSubmissionResponse(BaseModel):
    """Response payload returned after submitting a video job."""

    job_id: str
    status: VideoJobStatus
    created_at: datetime

    @classmethod
    def from_job(cls, job: VideoJob) -> "VideoJobSubmissionResponse":
        return cls(job_id=job.job_id, status=job.status, created_at=job.created_at)


class VideoJobStatusResponse(BaseModel):
    """Detailed status payload describing an individual video job."""

    job_id: str
    status: VideoJobStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
    progress: ProgressSnapshotPayload
    latest_event: ProgressEventPayload | None
    result: VideoJobResultPayload | None = None
    generated_files: Dict[str, Any] | None = None

    @classmethod
    def from_job(cls, job: VideoJob) -> "VideoJobStatusResponse":
        result_payload = None
        if job.result is not None:
            result_payload = VideoJobResultPayload.from_result(job.result)

        latest_event = (
            ProgressEventPayload.from_event(job.last_event)
            if job.last_event is not None
            else None
        )

        generated_files = copy.deepcopy(job.generated_files) if job.generated_files else None

        return cls(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error=job.error,
            progress=ProgressSnapshotPayload.from_snapshot(job.tracker.snapshot()),
            latest_event=latest_event,
            result=result_payload,
            generated_files=generated_files,
        )

from .media import (
    AudioGenerationParameters,
    MediaAPISettings,
    MediaErrorResponse,
    MediaGenerationRequestPayload,
    MediaGenerationResponse,
    VideoGenerationParameters,
)
