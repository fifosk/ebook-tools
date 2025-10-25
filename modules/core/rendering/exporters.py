"""Media export helpers for the rendering pipeline."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Sequence

from PIL import Image
from pydub import AudioSegment

from modules import audio_video_generator as av_gen
from modules import output_formatter
from modules.config.loader import get_rendering_config
from modules.render.context import RenderBatchContext
from modules.render.output_writer import DeferredBatchWriter
from modules.video.slides import SlideRenderOptions


@dataclass(frozen=True)
class BatchExportContext:
    """Static context shared across batch exports."""

    base_dir: str
    base_name: str
    cover_image: Optional[Image.Image]
    book_author: str
    book_title: str
    global_cumulative_word_counts: Sequence[int]
    total_book_words: int
    macos_reading_speed: float
    input_language: str
    total_sentences: int
    tempo: float
    sync_ratio: float
    word_highlighting: bool
    highlight_granularity: str
    slide_render_options: Optional[SlideRenderOptions]
    template_name: Optional[str]


@dataclass(frozen=True)
class BatchExportRequest:
    """User-controlled options and dynamic content for a batch export."""

    start_sentence: int
    end_sentence: int
    written_blocks: Sequence[str]
    target_language: str
    output_html: bool
    output_pdf: bool
    generate_audio: bool
    audio_segments: Sequence[AudioSegment]
    generate_video: bool
    video_blocks: Sequence[str]


class BatchExporter:
    """Persist batch outputs for written, audio, and optional video artifacts."""

    def __init__(self, context: BatchExportContext) -> None:
        self._context = context

    def export(self, request: BatchExportRequest) -> Optional[str]:
        """Write batch outputs and return any generated video path."""

        range_fragment = output_formatter.format_sentence_range(
            request.start_sentence,
            request.end_sentence,
            self._context.total_sentences,
        )

        config = get_rendering_config()
        manifest_context = {
            "batch_id": f"{range_fragment}_{self._context.base_name}",
            "ramdisk_enabled": config.ramdisk_enabled,
            "ramdisk_path": config.ramdisk_path,
        }
        media_context = {
            "text": {"range_fragment": range_fragment},
            "audio": {"range_fragment": range_fragment},
            "video": {"range_fragment": range_fragment},
        }
        batch_context = RenderBatchContext(manifest=manifest_context, media=media_context)
        writer = DeferredBatchWriter(Path(self._context.base_dir), batch_context)

        try:
            document_paths = output_formatter.export_batch_documents(
                str(writer.work_dir),
                self._context.base_name,
                request.start_sentence,
                request.end_sentence,
                list(request.written_blocks),
                request.target_language,
                self._context.total_sentences,
                output_html=request.output_html,
                output_pdf=request.output_pdf,
            )
            for created_path in document_paths.values():
                writer.stage(Path(created_path))

            audio_segments = list(request.audio_segments) if request.generate_audio else []
            video_blocks = list(request.video_blocks) if request.generate_video else []

            video_path: Optional[Path] = None

            if request.generate_audio and audio_segments:
                combined = AudioSegment.empty()
                for segment in audio_segments:
                    combined += segment
                audio_filename = writer.work_dir / f"{range_fragment}_{self._context.base_name}.mp3"
                combined.export(str(audio_filename), format="mp3", bitrate="320k")
                writer.stage(audio_filename)

            if request.generate_video and audio_segments and video_blocks:
                video_output = av_gen.render_video_slides(
                    video_blocks,
                    audio_segments,
                    str(writer.work_dir),
                    request.start_sentence,
                    request.end_sentence,
                    self._context.base_name,
                    self._context.cover_image,
                    self._context.book_author,
                    self._context.book_title,
                    list(self._context.global_cumulative_word_counts),
                    self._context.total_book_words,
                    self._context.macos_reading_speed,
                    self._context.input_language,
                    self._context.total_sentences,
                    self._context.tempo,
                    self._context.sync_ratio,
                    self._context.word_highlighting,
                    self._context.highlight_granularity,
                    slide_render_options=self._context.slide_render_options,
                    template_name=self._context.template_name,
                )
                video_path = Path(video_output)
                video_path = writer.stage(video_path)

            writer.commit()
        except Exception:
            writer.rollback()
            raise

        return str(video_path) if video_path else None


def build_exporter(
    *,
    base_dir: str,
    base_name: str,
    cover_img: Optional[Image.Image],
    book_author: str,
    book_title: str,
    global_cumulative_word_counts: Sequence[int],
    total_book_words: int,
    macos_reading_speed: float,
    input_language: str,
    total_sentences: int,
    tempo: float,
    sync_ratio: float,
    word_highlighting: bool,
    highlight_granularity: str,
    slide_render_options: Optional[SlideRenderOptions],
    template_name: Optional[str],
) -> BatchExporter:
    """Construct a :class:`BatchExporter` for the provided pipeline context."""

    context = BatchExportContext(
        base_dir=base_dir,
        base_name=base_name,
        cover_image=cover_img,
        book_author=book_author,
        book_title=book_title,
        global_cumulative_word_counts=list(global_cumulative_word_counts),
        total_book_words=total_book_words,
        macos_reading_speed=macos_reading_speed,
        input_language=input_language,
        total_sentences=total_sentences,
        tempo=tempo,
        sync_ratio=sync_ratio,
        word_highlighting=word_highlighting,
        highlight_granularity=highlight_granularity,
        slide_render_options=slide_render_options,
        template_name=template_name,
    )
    return BatchExporter(context)
