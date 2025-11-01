"""Shared video payload models used by service and API layers."""

from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List

from PIL import Image
from pydantic import Base64Bytes, BaseModel, ConfigDict, Field, model_validator

from .file_locator import FileLocator
from ..video.backends import VideoRenderOptions
from ..video.jobs import VideoAudioSource, VideoRenderTask
from ..video.slide_renderer import SlideRenderOptions


class VideoImageReference(BaseModel):
    """Reference to an image supplied either inline or via job storage."""

    data: Base64Bytes | None = Field(
        default=None,
        description="Optional base64-encoded representation of the image.",
    )
    job_id: str | None = Field(
        default=None,
        description="Identifier of the job containing the referenced image.",
    )
    relative_path: str | None = Field(
        default=None,
        description="Relative path to an image stored alongside job artifacts.",
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

        assert self.job_id is not None  # for static type checkers
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

        assert self.job_id is not None  # for type checkers
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


__all__ = [
    "VideoAudioSourcePayload",
    "VideoImageReference",
    "VideoRenderOptionsPayload",
    "VideoRenderRequestPayload",
]
