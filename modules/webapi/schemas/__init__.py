"""Pydantic schemas for the FastAPI web backend."""

from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from ...core.config import PipelineConfig
from ...progress_tracker import ProgressEvent, ProgressSnapshot
from ...services.pipeline_service import PipelineInput, PipelineRequest, PipelineResponse
from ...video.jobs import (
    VideoJob,
    VideoJobResult,
    VideoJobStatus,
)
from ...services.video_payloads import (
    VideoAudioSourcePayload,
    VideoImageReference,
    VideoRenderOptionsPayload,
    VideoRenderRequestPayload,
)
from ..jobs import PipelineJob, PipelineJobStatus
from .audio import GTTSLanguage, MacOSVoice, VoiceInventoryResponse, VoiceMatchResponse
from .library import (
    LibraryItemPayload,
    LibraryIsbnLookupResponse,
    LibraryIsbnUpdateRequest,
    LibraryMediaRemovalResponse,
    LibraryMetadataUpdateRequest,
    LibraryMoveRequest,
    LibraryMoveResponse,
    LibraryReindexResponse,
    LibrarySearchResponse,
)


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
    sentences_per_output_file: int = 1
    start_sentence: int = 1
    end_sentence: Optional[int] = None
    stitch_full: bool = False
    generate_audio: bool = True
    audio_mode: str = "1"
    written_mode: str = "4"
    selected_voice: str = "gTTS"
    output_html: bool = False
    output_pdf: bool = False
    generate_video: bool = False
    add_images: bool = False
    include_transliteration: bool = True
    tempo: float = 1.0
    voice_overrides: Dict[str, str] = Field(default_factory=dict)
    book_metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dataclass(self) -> PipelineInput:
        payload = self.model_dump()
        return PipelineInput(**payload)


class PipelineDefaultsResponse(BaseModel):
    """Response payload exposing the resolved baseline configuration."""

    config: Dict[str, Any] = Field(default_factory=dict)


class PipelineFileDeleteRequest(BaseModel):
    """Request payload for deleting a stored pipeline input file."""

    path: str

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Path cannot be empty")
        return trimmed


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
    job_type: str = "pipeline"


class SubtitleSourceEntry(BaseModel):
    """Metadata describing a discoverable subtitle file."""

    name: str
    path: str
    format: str
    language: Optional[str] = None
    modified_at: Optional[datetime] = None


class SubtitleDeleteRequest(BaseModel):
    """Request payload used to delete a subtitle source file."""

    subtitle_path: str
    base_dir: Optional[str] = None


class SubtitleDeleteResponse(BaseModel):
    """Outcome of deleting a subtitle source file."""

    subtitle_path: str
    base_dir: Optional[str] = None
    removed: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)


class SubtitleSubmissionPayload(BaseModel):
    """Payload used when submitting a subtitle job via JSON."""

    input_language: str
    target_language: str
    enable_transliteration: bool = False
    highlight: bool = True
    batch_size: Optional[int] = None
    source_path: Optional[str] = None
    cleanup_source: bool = False
    mirror_batches_to_source_dir: bool = True
    llm_model: Optional[str] = None


class SubtitleSourceListResponse(BaseModel):
    """Collection of available subtitle sources."""

    sources: List[SubtitleSourceEntry] = Field(default_factory=list)


class SubtitleTvMetadataParse(BaseModel):
    """Parsed TV episode identifier inferred from a subtitle filename."""

    series: str
    season: int
    episode: int
    pattern: str


class SubtitleTvMetadataResponse(BaseModel):
    """Response payload describing subtitle TV metadata enrichment state."""

    job_id: str
    source_name: Optional[str] = None
    parsed: Optional[SubtitleTvMetadataParse] = None
    media_metadata: Optional[Dict[str, Any]] = None


class SubtitleTvMetadataLookupRequest(BaseModel):
    """Request payload to trigger a TV metadata lookup for a subtitle job."""

    force: bool = False


class SubtitleTvMetadataPreviewResponse(BaseModel):
    """Response payload describing TV metadata lookup results for a filename."""

    source_name: Optional[str] = None
    parsed: Optional[SubtitleTvMetadataParse] = None
    media_metadata: Optional[Dict[str, Any]] = None


class SubtitleTvMetadataPreviewLookupRequest(BaseModel):
    """Request payload to trigger a TV metadata lookup for a subtitle filename."""

    source_name: str
    force: bool = False


class YoutubeVideoMetadataParse(BaseModel):
    """Parsed YouTube video identifier inferred from a filename/URL."""

    video_id: str
    pattern: str


class YoutubeVideoMetadataResponse(BaseModel):
    """Response payload describing YouTube metadata enrichment state for a job."""

    job_id: str
    source_name: Optional[str] = None
    parsed: Optional[YoutubeVideoMetadataParse] = None
    youtube_metadata: Optional[Dict[str, Any]] = None


class YoutubeVideoMetadataLookupRequest(BaseModel):
    """Request payload to trigger a YouTube metadata lookup for a job."""

    force: bool = False


class YoutubeVideoMetadataPreviewResponse(BaseModel):
    """Response payload describing YouTube metadata lookup results for a filename/URL."""

    source_name: Optional[str] = None
    parsed: Optional[YoutubeVideoMetadataParse] = None
    youtube_metadata: Optional[Dict[str, Any]] = None


class YoutubeVideoMetadataPreviewLookupRequest(BaseModel):
    """Request payload to trigger a YouTube metadata lookup for a filename/URL."""

    source_name: str
    force: bool = False


class BookOpenLibraryQuery(BaseModel):
    """Parsed Open Library query inferred from a filename/title/ISBN."""

    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None


class BookOpenLibraryMetadataResponse(BaseModel):
    """Response payload describing Open Library enrichment for a book-like job."""

    job_id: str
    source_name: Optional[str] = None
    query: Optional[BookOpenLibraryQuery] = None
    book_metadata_lookup: Optional[Dict[str, Any]] = None


class BookOpenLibraryMetadataLookupRequest(BaseModel):
    """Request payload to trigger an Open Library lookup for a book-like job."""

    force: bool = False


class BookOpenLibraryMetadataPreviewResponse(BaseModel):
    """Response payload describing Open Library lookup results for a filename/title/ISBN."""

    source_name: Optional[str] = None
    query: Optional[BookOpenLibraryQuery] = None
    book_metadata_lookup: Optional[Dict[str, Any]] = None


class BookOpenLibraryMetadataPreviewLookupRequest(BaseModel):
    """Request payload to trigger an Open Library lookup for a filename/title/ISBN."""

    query: str
    force: bool = False


class YoutubeSubtitleTrackPayload(BaseModel):
    """Description of an available YouTube subtitle track."""

    language: str
    kind: Literal["auto", "manual"]
    name: Optional[str] = None
    formats: List[str] = Field(default_factory=list)


class YoutubeSubtitleListResponse(BaseModel):
    """Available subtitle tracks for a YouTube video."""

    video_id: str
    title: Optional[str] = None
    tracks: List[YoutubeSubtitleTrackPayload] = Field(default_factory=list)
    video_formats: List["YoutubeVideoFormatPayload"] = Field(default_factory=list)


class YoutubeVideoFormatPayload(BaseModel):
    """Description of an available YouTube mp4 format option."""

    format_id: str
    ext: str
    resolution: Optional[str] = None
    fps: Optional[int] = None
    note: Optional[str] = None
    bitrate_kbps: Optional[float] = None
    filesize: Optional[str] = None


class YoutubeSubtitleDownloadRequest(BaseModel):
    """Request payload to download a YouTube subtitle track."""

    url: str
    language: str
    kind: Literal["auto", "manual"] = "manual"
    video_output_dir: Optional[str] = None
    timestamp: Optional[str] = None


class YoutubeSubtitleDownloadResponse(BaseModel):
    """Response after downloading a YouTube subtitle track."""

    output_path: str
    filename: str


class YoutubeVideoDownloadRequest(BaseModel):
    """Request payload to download a YouTube video."""

    url: str
    output_dir: Optional[str] = None
    format_id: Optional[str] = None
    timestamp: Optional[str] = None


class YoutubeVideoDownloadResponse(BaseModel):
    """Response after downloading a YouTube video."""

    output_path: str
    filename: str
    folder: str


class YoutubeNasSubtitlePayload(BaseModel):
    """Subtitle file stored next to a downloaded YouTube video."""

    path: str
    filename: str
    language: Optional[str] = None
    format: str


class YoutubeNasVideoPayload(BaseModel):
    """Downloaded YouTube video and its discovered subtitle companions."""

    path: str
    filename: str
    folder: str
    size_bytes: int
    modified_at: datetime
    source: Optional[str] = Field(default="youtube")
    linked_job_ids: List[str] = Field(default_factory=list)
    subtitles: List[YoutubeNasSubtitlePayload] = Field(default_factory=list)


class YoutubeNasLibraryResponse(BaseModel):
    """Response describing the NAS directory of downloaded YouTube videos."""

    base_dir: str
    videos: List[YoutubeNasVideoPayload] = Field(default_factory=list)


class YoutubeSubtitleExtractionRequest(BaseModel):
    """Request payload for extracting embedded subtitle tracks from a video."""

    video_path: str
    languages: Optional[List[str]] = None


class YoutubeInlineSubtitleStream(BaseModel):
    """Single subtitle stream embedded in a video file."""

    index: int
    position: int
    language: Optional[str] = None
    codec: Optional[str] = None
    title: Optional[str] = None
    can_extract: bool = True


class YoutubeSubtitleExtractionResponse(BaseModel):
    """Response describing extracted subtitle tracks."""

    video_path: str
    extracted: List[YoutubeNasSubtitlePayload] = Field(default_factory=list)


class YoutubeInlineSubtitleListResponse(BaseModel):
    """Response describing subtitle streams embedded in a video."""

    video_path: str
    streams: List[YoutubeInlineSubtitleStream] = Field(default_factory=list)


class YoutubeSubtitleDeleteRequest(BaseModel):
    """Request payload for deleting a subtitle next to a NAS video."""

    video_path: str
    subtitle_path: str


class YoutubeSubtitleDeleteResponse(BaseModel):
    """Response payload after deleting a NAS subtitle and companions."""

    video_path: str
    subtitle_path: str
    removed: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)


class YoutubeVideoDeleteRequest(BaseModel):
    """Request payload to delete a downloaded YouTube video."""

    video_path: str


class YoutubeVideoDeleteResponse(BaseModel):
    """Response payload after deleting a YouTube video and companions."""

    video_path: str
    removed: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)


class YoutubeDubRequest(BaseModel):
    """Request payload for generating a dubbed audio track from an ASS file."""

    video_path: str
    subtitle_path: str
    media_metadata: Optional[Dict[str, Any]] = None
    target_language: Optional[str] = None
    voice: Optional[str] = None
    tempo: Optional[float] = None
    macos_reading_speed: Optional[int] = None
    output_dir: Optional[str] = None
    start_time_offset: Optional[str] = None
    end_time_offset: Optional[str] = None
    original_mix_percent: Optional[float] = None
    flush_sentences: Optional[int] = None
    llm_model: Optional[str] = None
    split_batches: Optional[bool] = None
    stitch_batches: Optional[bool] = True
    include_transliteration: Optional[bool] = None
    target_height: Optional[int] = None
    preserve_aspect_ratio: Optional[bool] = None


class YoutubeDubResponse(BaseModel):
    """Job handle for generating a dubbed YouTube video."""

    job_id: str
    status: PipelineJobStatus
    created_at: datetime
    job_type: str = "youtube_dub"
    output_path: Optional[str] = None


class LLMModelListResponse(BaseModel):
    """Response payload describing available LLM models."""

    models: List[str] = Field(default_factory=list)


class AssistantChatMessage(BaseModel):
    """A single assistant chat message (used for optional history/context)."""

    role: Literal["user", "assistant"]
    content: str


class AssistantRequestContext(BaseModel):
    """Optional context for assistant requests (future UI action wiring)."""

    source: Optional[str] = None
    page: Optional[str] = None
    job_id: Optional[str] = None
    selection_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssistantLookupRequest(BaseModel):
    """Request payload for a dictionary-style lookup."""

    query: str
    input_language: str
    lookup_language: str = "English"
    llm_model: Optional[str] = None
    system_prompt: Optional[str] = None
    history: List[AssistantChatMessage] = Field(default_factory=list)
    context: Optional[AssistantRequestContext] = None


class AssistantLookupResponse(BaseModel):
    """Response payload for assistant lookups."""

    answer: str
    model: str
    token_usage: Dict[str, int] = Field(default_factory=dict)
    source: Optional[str] = None


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
            "voice_overrides": dict(config.voice_overrides),
            "image_api_base_url": config.image_api_base_url,
            "image_api_timeout_seconds": config.image_api_timeout_seconds,
            "image_concurrency": config.image_concurrency,
            "image_width": config.image_width,
            "image_height": config.image_height,
            "image_steps": config.image_steps,
            "image_cfg_scale": config.image_cfg_scale,
            "image_sampler_name": config.image_sampler_name,
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


class JobParameterSnapshot(BaseModel):
    """Captured subset of the inputs/configuration used to execute a job."""

    input_file: Optional[str] = None
    base_output_file: Optional[str] = None
    input_language: Optional[str] = None
    target_languages: List[str] = Field(default_factory=list)
    start_sentence: Optional[int] = None
    end_sentence: Optional[int] = None
    sentences_per_output_file: Optional[int] = None
    llm_model: Optional[str] = None
    audio_mode: Optional[str] = None
    selected_voice: Optional[str] = None
    voice_overrides: Dict[str, str] = Field(default_factory=dict)
    worker_count: Optional[int] = None
    batch_size: Optional[int] = None
    show_original: Optional[bool] = None
    enable_transliteration: Optional[bool] = None
    start_time_offset_seconds: Optional[float] = None
    end_time_offset_seconds: Optional[float] = None
    video_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    tempo: Optional[float] = None
    macos_reading_speed: Optional[int] = None
    output_dir: Optional[str] = None
    original_mix_percent: Optional[float] = None
    flush_sentences: Optional[int] = None
    split_batches: Optional[bool] = None
    include_transliteration: Optional[bool] = None
    add_images: Optional[bool] = None


def _coerce_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed:
            return trimmed
    return None


def _coerce_int(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(float(stripped))
        except ValueError:
            return None
    return None


def _coerce_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return None


def _normalize_language_list(value: Any) -> List[str]:
    languages: List[str] = []
    if isinstance(value, (list, tuple, set)):
        for entry in value:
            text = _coerce_str(entry)
            if text:
                languages.append(text)
    else:
        text = _coerce_str(value)
        if text:
            languages.append(text)
    return languages


def _normalize_voice_overrides(value: Any) -> Dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    overrides: Dict[str, str] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str):
            continue
        key = raw_key.strip()
        if not key:
            continue
        normalized_value = _coerce_str(raw_value)
        if normalized_value:
            overrides[key] = normalized_value
    return overrides


def _build_pipeline_parameters(payload: Mapping[str, Any]) -> Optional[JobParameterSnapshot]:
    inputs = payload.get("inputs")
    if not isinstance(inputs, Mapping):
        return None

    target_languages = _normalize_language_list(inputs.get("target_languages"))
    input_language = _coerce_str(inputs.get("input_language"))
    start_sentence = _coerce_int(inputs.get("start_sentence"))
    end_sentence = _coerce_int(inputs.get("end_sentence"))
    sentences_per_file = _coerce_int(inputs.get("sentences_per_output_file"))
    audio_mode = _coerce_str(inputs.get("audio_mode"))
    selected_voice = _coerce_str(inputs.get("selected_voice"))
    voice_overrides = _normalize_voice_overrides(inputs.get("voice_overrides"))
    include_transliteration = _coerce_bool(inputs.get("include_transliteration"))
    add_images = _coerce_bool(inputs.get("add_images"))

    input_file = _coerce_str(inputs.get("input_file"))
    base_output_file = _coerce_str(inputs.get("base_output_file"))

    llm_model = None
    config_payload = payload.get("config")
    if isinstance(config_payload, Mapping):
        llm_model = _coerce_str(config_payload.get("ollama_model"))

    pipeline_overrides = payload.get("pipeline_overrides")
    if isinstance(pipeline_overrides, Mapping):
        override_model = _coerce_str(pipeline_overrides.get("ollama_model"))
        if override_model:
            llm_model = override_model
        override_audio_mode = _coerce_str(pipeline_overrides.get("audio_mode"))
        if override_audio_mode:
            audio_mode = override_audio_mode
        override_voice_overrides = _normalize_voice_overrides(
            pipeline_overrides.get("voice_overrides")
        )
        if override_voice_overrides:
            voice_overrides = override_voice_overrides

    return JobParameterSnapshot(
        input_file=input_file,
        base_output_file=base_output_file,
        input_language=input_language,
        target_languages=target_languages,
        start_sentence=start_sentence,
        end_sentence=end_sentence,
        sentences_per_output_file=sentences_per_file,
        llm_model=llm_model,
        audio_mode=audio_mode,
        selected_voice=selected_voice,
        voice_overrides=voice_overrides,
        include_transliteration=include_transliteration,
        add_images=add_images,
    )


def _build_subtitle_parameters(payload: Mapping[str, Any]) -> Optional[JobParameterSnapshot]:
    options = payload.get("options")
    if not isinstance(options, Mapping):
        return None

    subtitle_path = (
        _coerce_str(payload.get("original_name"))
        or _coerce_str(payload.get("source_path"))
        or _coerce_str(payload.get("source_file"))
        or _coerce_str(payload.get("submitted_source"))
    )

    target_language = _coerce_str(options.get("target_language"))
    target_languages = [target_language] if target_language else []
    input_language = _coerce_str(options.get("input_language")) or _coerce_str(
        options.get("original_language")
    )

    return JobParameterSnapshot(
        input_language=input_language,
        target_languages=target_languages,
        subtitle_path=subtitle_path,
        llm_model=_coerce_str(options.get("llm_model")),
        worker_count=_coerce_int(options.get("worker_count")),
        batch_size=_coerce_int(options.get("batch_size")),
        show_original=_coerce_bool(options.get("show_original")),
        enable_transliteration=_coerce_bool(options.get("enable_transliteration")),
        start_time_offset_seconds=_coerce_float(options.get("start_time_offset")),
        end_time_offset_seconds=_coerce_float(options.get("end_time_offset")),
    )


def _build_youtube_dub_parameters(payload: Mapping[str, Any]) -> Optional[JobParameterSnapshot]:
    video_path = _coerce_str(payload.get("video_path"))
    subtitle_path = _coerce_str(payload.get("subtitle_path"))
    target_language = _coerce_str(payload.get("target_language"))
    voice = _coerce_str(payload.get("voice"))
    tempo = _coerce_float(payload.get("tempo"))
    reading_speed = _coerce_int(payload.get("macos_reading_speed"))
    output_dir = _coerce_str(payload.get("output_dir"))
    start_offset = _coerce_float(payload.get("start_time_offset"))
    end_offset = _coerce_float(payload.get("end_time_offset"))
    original_mix_percent = _coerce_float(payload.get("original_mix_percent"))
    flush_sentences = _coerce_int(payload.get("flush_sentences"))
    llm_model = _coerce_str(payload.get("llm_model"))
    split_batches = _coerce_bool(payload.get("split_batches"))

    target_languages = [target_language] if target_language else []

    return JobParameterSnapshot(
        input_file=video_path,
        video_path=video_path,
        subtitle_path=subtitle_path,
        target_languages=target_languages,
        selected_voice=voice,
        tempo=tempo,
        macos_reading_speed=reading_speed,
        output_dir=output_dir,
        start_time_offset_seconds=start_offset,
        end_time_offset_seconds=end_offset,
        original_mix_percent=original_mix_percent,
        flush_sentences=flush_sentences,
        llm_model=llm_model,
        split_batches=split_batches,
    )


def _build_job_parameters(job: PipelineJob) -> Optional[JobParameterSnapshot]:
    payload: Optional[Mapping[str, Any]] = None
    if isinstance(job.request_payload, Mapping):
        payload = job.request_payload
    elif isinstance(job.resume_context, Mapping):
        payload = job.resume_context

    if payload is None:
        return None

    if job.job_type == "subtitle":
        return _build_subtitle_parameters(payload)
    if job.job_type == "youtube_dub":
        return _build_youtube_dub_parameters(payload)
    return _build_pipeline_parameters(payload)


def _filename_stem(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    basename = trimmed.split("/")[-1].split("\\")[-1]
    try:
        stem = Path(basename).stem
    except Exception:
        return basename
    return stem or basename


def _resolve_job_label(job: PipelineJob) -> Optional[str]:
    """Return a human-friendly label for ``job`` when possible."""

    request_payload: Optional[Mapping[str, Any]] = None
    if isinstance(job.request_payload, Mapping):
        request_payload = job.request_payload
    elif isinstance(job.resume_context, Mapping):
        request_payload = job.resume_context

    if job.job_type == "subtitle":
        if request_payload is not None:
            media_metadata = request_payload.get("media_metadata")
            if isinstance(media_metadata, Mapping):
                label = media_metadata.get("job_label")
                if isinstance(label, str) and label.strip():
                    return label.strip()
            for key in ("original_name", "source_file", "source_path", "submitted_source"):
                stem = _filename_stem(request_payload.get(key))
                if stem:
                    return stem

        if isinstance(job.result_payload, Mapping):
            subtitle_section = job.result_payload.get("subtitle")
            if isinstance(subtitle_section, Mapping):
                metadata = subtitle_section.get("metadata")
                if isinstance(metadata, Mapping):
                    label = metadata.get("job_label")
                    if isinstance(label, str) and label.strip():
                        return label.strip()
                    for key in ("input_file", "source", "subtitle_name"):
                        stem = _filename_stem(metadata.get(key))
                        if stem:
                            return stem

        return None

    if job.job_type == "youtube_dub":
        if request_payload is not None:
            media_metadata = request_payload.get("media_metadata")
            if isinstance(media_metadata, Mapping):
                label = media_metadata.get("job_label")
                if isinstance(label, str) and label.strip():
                    return label.strip()
            for key in ("video_path", "subtitle_path"):
                stem = _filename_stem(request_payload.get(key))
                if stem:
                    return stem

        if isinstance(job.result_payload, Mapping):
            dub_section = job.result_payload.get("youtube_dub")
            if isinstance(dub_section, Mapping):
                for key in ("video_path", "output_path", "subtitle_path"):
                    stem = _filename_stem(dub_section.get(key))
                    if stem:
                        return stem

        return None

    if request_payload is not None and job.job_type in {"pipeline", "book"}:
        inputs = request_payload.get("inputs")
        if isinstance(inputs, Mapping):
            for key in ("job_label", "title", "name", "topic"):
                candidate = inputs.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
            book_metadata = inputs.get("book_metadata")
            if isinstance(book_metadata, Mapping):
                for key in ("job_label", "title", "book_title", "book_name", "name", "topic"):
                    candidate = book_metadata.get(key)
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate.strip()
            stem = _filename_stem(inputs.get("input_file")) or _filename_stem(
                inputs.get("base_output_file")
            )
            if stem:
                return stem

    return None


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
    job_type: str
    status: PipelineJobStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Dict[str, Any] | PipelineResponsePayload]
    error: Optional[str]
    latest_event: Optional[ProgressEventPayload]
    tuning: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    generated_files: Optional[Dict[str, Any]] = None
    parameters: Optional[JobParameterSnapshot] = None
    media_completed: Optional[bool] = None
    retry_summary: Optional[Dict[str, Dict[str, int]]] = None
    job_label: Optional[str] = None

    @classmethod
    def from_job(cls, job: PipelineJob) -> "PipelineStatusResponse":
        result_payload: Optional[PipelineResponsePayload | Dict[str, Any]] = None
        if job.job_type in {"pipeline", "book"}:
            if job.result is not None:
                result_payload = PipelineResponsePayload.from_response(job.result)
            elif job.result_payload is not None:
                result_payload = PipelineResponsePayload(**job.result_payload)
        elif job.result_payload is not None:
            result_payload = copy.deepcopy(job.result_payload)

        latest_event = None
        if job.last_event is not None:
            latest_event = ProgressEventPayload.from_event(job.last_event)

        generated_files = None
        if job.generated_files is not None:
            generated_files = copy.deepcopy(job.generated_files)

        return cls(
            job_id=job.job_id,
            job_type=job.job_type,
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
            parameters=_build_job_parameters(job),
            media_completed=job.media_completed,
            retry_summary=job.tracker.get_retry_counts() if job.tracker else job.retry_summary,
            job_label=_resolve_job_label(job),
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
    chunk_id: Optional[str] = None
    range_fragment: Optional[str] = None
    start_sentence: Optional[int] = None
    end_sentence: Optional[int] = None
    type: Optional[str] = None

    @field_serializer("updated_at")
    def _serialize_updated_at(self, value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        return value.isoformat()


class ChunkSentenceTimelineEvent(BaseModel):
    duration: float
    original_index: int
    translation_index: int
    transliteration_index: int


class ChunkSentenceVariant(BaseModel):
    text: str = ""
    tokens: List[str] = Field(default_factory=list)


class ChunkSentenceMetadata(BaseModel):
    sentence_number: Optional[int] = None
    original: ChunkSentenceVariant
    translation: Optional[ChunkSentenceVariant] = None
    transliteration: Optional[ChunkSentenceVariant] = None
    timeline: List[ChunkSentenceTimelineEvent] = Field(default_factory=list)
    total_duration: Optional[float] = None
    highlight_granularity: Optional[str] = None
    counts: Dict[str, int] = Field(default_factory=dict)
    phase_durations: Dict[str, float] = Field(default_factory=dict)

class AudioTrackMetadata(BaseModel):
    """Metadata about an audio artifact referenced by a chunk."""

    path: Optional[str] = None
    url: Optional[str] = None
    duration: Optional[float] = None
    sampleRate: Optional[int] = None


class PipelineMediaChunk(BaseModel):
    """Groups media files produced for a specific chunk."""

    chunk_id: Optional[str] = None
    range_fragment: Optional[str] = None
    start_sentence: Optional[int] = None
    end_sentence: Optional[int] = None
    files: List[PipelineMediaFile] = Field(default_factory=list)
    sentences: List[ChunkSentenceMetadata] = Field(default_factory=list)
    metadata_path: Optional[str] = None
    metadata_url: Optional[str] = None
    sentence_count: Optional[int] = None
    audio_tracks: Dict[str, AudioTrackMetadata] = Field(default_factory=dict)


class PipelineMediaResponse(BaseModel):
    """Response payload grouping generated media by type."""

    media: Dict[str, List[PipelineMediaFile]] = Field(default_factory=dict)
    chunks: List[PipelineMediaChunk] = Field(default_factory=list)
    complete: bool = False


class MediaSearchHit(BaseModel):
    """Single search match across generated ebook media."""

    job_id: str
    job_label: Optional[str] = None
    base_id: Optional[str] = None
    chunk_id: Optional[str] = None
    chunk_index: Optional[int] = None
    chunk_total: Optional[int] = None
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
    source: Literal["pipeline", "library"] = Field(default="pipeline")
    library_author: Optional[str] = Field(default=None, alias="libraryAuthor")
    library_genre: Optional[str] = Field(default=None, alias="libraryGenre")
    library_language: Optional[str] = Field(default=None, alias="libraryLanguage")
    cover_path: Optional[str] = Field(default=None, alias="coverPath")
    library_path: Optional[str] = Field(default=None, alias="libraryPath")


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
from .video import VideoGenerationRequest, VideoGenerationResponse
