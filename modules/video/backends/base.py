"""Base interfaces and option containers for video rendering backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, Sequence, runtime_checkable

from PIL import Image
from pydub import AudioSegment

from modules.video.slide_renderer import SlideRenderOptions


@dataclass(slots=True)
class VideoRenderOptions:
    """Options describing how a batch of slides should be rendered."""

    batch_start: int
    batch_end: int
    cover_image: Optional[Image.Image] = None
    book_author: str = ""
    book_title: str = ""
    cumulative_word_counts: Sequence[int] | None = None
    total_word_count: int | None = None
    macos_reading_speed: int | None = None
    input_language: str = ""
    total_sentences: int | None = None
    tempo: float | None = None
    sync_ratio: float = 1.0
    word_highlighting: bool = True
    highlight_granularity: str = "word"
    voice_name: str = ""
    voice_lines: Sequence[str] = field(default_factory=list)
    slide_render_options: SlideRenderOptions | None = None
    cleanup: bool = True
    slide_size: Sequence[int] = field(default_factory=lambda: (1280, 720))
    initial_font_size: int = 60
    bg_color: Sequence[int] | None = None
    template_name: str | None = None
    default_font_path: str | None = None


@runtime_checkable
class BaseVideoRenderer(Protocol):
    """Protocol implemented by video rendering backends.

    Implementations should raise :class:`modules.media.exceptions.MediaBackendError`
    (or a subclass) for all operational errors to keep error handling consistent
    across different renderer implementations.
    """

    def render_slides(
        self,
        slides: Sequence[str],
        audio_tracks: Sequence[AudioSegment],
        output_path: str,
        options: VideoRenderOptions,
    ) -> str:
        """Render ``slides`` and ``audio_tracks`` into ``output_path``.

        Should raise :class:`modules.media.exceptions.MediaBackendError` if the
        rendering pipeline fails.
        """

    def concatenate(self, video_paths: Sequence[str], output_path: str) -> str:
        """Concatenate ``video_paths`` into ``output_path``.

        Should raise :class:`modules.media.exceptions.MediaBackendError` if the
        concatenation process fails.
        """


__all__ = ["BaseVideoRenderer", "VideoRenderOptions"]

