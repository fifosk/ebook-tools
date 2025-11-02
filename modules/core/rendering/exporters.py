"""Media export helpers for the rendering pipeline."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence

from PIL import Image
from pydub import AudioSegment

from modules import audio_video_generator as av_gen
from modules import config_manager as cfg
from modules import output_formatter
from modules.audio.tts import get_voice_display_name
from modules.config.loader import get_rendering_config
from modules.core.rendering.constants import LANGUAGE_CODES
from modules.render.context import RenderBatchContext
from modules.render.output_writer import DeferredBatchWriter
from modules.video.api import VideoService
from modules.video.slides import SlideRenderOptions
from modules.audio.highlight import timeline


def _parse_sentence_block(block: str) -> tuple[str, str, str, str]:
    lines = block.split("\n")
    header = lines[0].strip() if lines else ""
    body_lines = [line.strip() for line in lines[1:] if line.strip()]

    original = body_lines[0] if body_lines else ""
    translation = body_lines[1] if len(body_lines) > 1 else ""
    transliteration = body_lines[2] if len(body_lines) > 2 else ""

    return header, original, translation, transliteration


def _split_translation_units(header: str, translation: str) -> List[str]:
    if not translation:
        return []
    if "Chinese" in header or "Japanese" in header:
        return list(translation)
    units = translation.split()
    return units or ([translation] if translation else [])


def _tokenize_words(text: str) -> List[str]:
    if not text:
        return []
    return [token for token in text.split() if token]


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
    selected_voice: str
    voice_name: str
    slide_render_options: Optional[SlideRenderOptions]
    template_name: Optional[str]
    video_backend: str
    video_backend_settings: Mapping[str, Mapping[str, object]]


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
    voice_metadata: Mapping[str, Mapping[str, Sequence[str]]] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class BatchExportResult:
    """Description of artifacts generated for a single batch export."""

    chunk_id: str
    start_sentence: int
    end_sentence: int
    range_fragment: str
    artifacts: Dict[str, str] = field(default_factory=dict)
    sentences: List[Dict[str, object]] = field(default_factory=list)


class BatchExporter:
    """Persist batch outputs for written, audio, and optional video artifacts."""

    def __init__(self, context: BatchExportContext) -> None:
        self._context = context
        self._video_service = VideoService(
            backend=context.video_backend,
            backend_settings=context.video_backend_settings,
        )

    def _build_sentence_metadata(
        self,
        *,
        block: str,
        audio_segment: Optional[AudioSegment],
        sentence_number: int,
    ) -> Dict[str, object]:
        header, original_text, translation_text, transliteration_text = _parse_sentence_block(block)

        timeline_options = timeline.TimelineBuildOptions(
            sync_ratio=self._context.sync_ratio,
            word_highlighting=self._context.word_highlighting,
            highlight_granularity=self._context.highlight_granularity,
        )
        timeline_result = timeline.build(block, audio_segment, timeline_options)

        events_payload: List[Dict[str, object]] = [
            {
                "duration": event.duration,
                "original_index": event.original_index,
                "translation_index": event.translation_index,
                "transliteration_index": event.transliteration_index,
            }
            for event in timeline_result.events
        ]

        original_tokens = _tokenize_words(original_text)
        translation_units = _split_translation_units(header, translation_text)
        transliteration_tokens = _tokenize_words(transliteration_text)

        payload: Dict[str, object] = {
            "sentence_number": sentence_number,
            "original": {
                "text": original_text,
                "tokens": original_tokens,
            },
            "timeline": events_payload,
            "highlight_granularity": timeline_result.effective_granularity,
            "total_duration": sum(event.duration for event in timeline_result.events),
        }

        if translation_text:
            payload["translation"] = {
                "text": translation_text,
                "tokens": translation_units,
            }
        else:
            payload["translation"] = None

        if transliteration_text:
            payload["transliteration"] = {
                "text": transliteration_text,
                "tokens": transliteration_tokens,
            }
        else:
            payload["transliteration"] = None

        payload["counts"] = {
            "original": len(original_tokens),
            "translation": len(translation_units),
            "transliteration": len(transliteration_tokens),
        }

        return payload

    @staticmethod
    def _format_voice_lines(
        metadata: Mapping[str, Mapping[str, Sequence[str]]]
    ) -> list[str]:
        lines: list[str] = []
        role_labels = {
            "source": "Source Voice",
            "translation": "Translation Voice",
        }
        for role, languages in metadata.items():
            if not isinstance(languages, Mapping):
                continue
            label = role_labels.get(role)
            if label is None:
                continue
            for language, voices in languages.items():
                if isinstance(voices, Sequence):
                    ordered = list(dict.fromkeys(str(voice).strip() for voice in voices if voice))
                    if not ordered:
                        continue
                    voice_list = ", ".join(ordered)
                else:
                    voice_list = str(voices).strip()
                    if not voice_list:
                        continue
                suffix = f" ({language})" if language else ""
                lines.append(f"{label}{suffix}: {voice_list}")
        return lines

    def export(self, request: BatchExportRequest) -> BatchExportResult:
        """Write batch outputs and return a description of created files."""

        range_fragment = output_formatter.format_sentence_range(
            request.start_sentence,
            request.end_sentence,
            self._context.total_sentences,
        )

        chunk_id = f"{range_fragment}_{self._context.base_name}"

        voice_lines = self._format_voice_lines(request.voice_metadata)
        voice_display = "\n".join(voice_lines) if voice_lines else self._context.voice_name

        config = get_rendering_config()
        runtime_context = cfg.get_runtime_context(None)
        ramdisk_enabled = config.ramdisk_enabled
        ramdisk_path = config.ramdisk_path
        if runtime_context is not None:
            candidate = Path(ramdisk_path)
            if not candidate.is_absolute():
                candidate = runtime_context.tmp_dir / candidate
            ramdisk_path = str(candidate)
            ramdisk_enabled = ramdisk_enabled and runtime_context.is_tmp_ramdisk
        manifest_context = {
            "batch_id": f"{range_fragment}_{self._context.base_name}",
            "ramdisk_enabled": ramdisk_enabled,
            "ramdisk_path": ramdisk_path,
        }
        media_context = {
            "text": {"range_fragment": range_fragment},
            "audio": {"range_fragment": range_fragment},
            "video": {
                "range_fragment": range_fragment,
                "voice_name": voice_display,
                "voice_lines": voice_lines,
            },
        }
        batch_context = RenderBatchContext(manifest=manifest_context, media=media_context)
        writer = DeferredBatchWriter(Path(self._context.base_dir), batch_context)

        artifacts: Dict[str, str] = {}
        audio_segments: List[AudioSegment] = (
            list(request.audio_segments) if request.generate_audio else []
        )
        video_blocks: List[str] = list(request.video_blocks)
        sentence_payloads: List[Dict[str, object]] = []

        for offset, block in enumerate(video_blocks):
            sentence_number = request.start_sentence + offset
            audio_segment = audio_segments[offset] if offset < len(audio_segments) else None
            metadata = self._build_sentence_metadata(
                block=block,
                audio_segment=audio_segment,
                sentence_number=sentence_number,
            )
            sentence_payloads.append(metadata)

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
            for kind, created_path in document_paths.items():
                staged_path = writer.stage(Path(created_path))
                artifacts[kind] = str(staged_path)

            if request.generate_audio and audio_segments:
                combined = AudioSegment.empty()
                for segment in audio_segments:
                    combined += segment
                audio_filename = writer.work_dir / f"{range_fragment}_{self._context.base_name}.mp3"
                combined.export(str(audio_filename), format="mp3", bitrate="320k")
                staged_audio = writer.stage(audio_filename)
                artifacts["audio"] = str(staged_audio)

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
                    voice_display,
                    slide_render_options=self._context.slide_render_options,
                    template_name=self._context.template_name,
                    video_service=self._video_service,
                    voice_lines=voice_lines,
                )
                video_path = Path(video_output)
                video_path = writer.stage(video_path)
                artifacts["video"] = str(video_path)

            writer.commit()
        except Exception:
            writer.rollback()
            raise

        return BatchExportResult(
            chunk_id=chunk_id,
            start_sentence=request.start_sentence,
            end_sentence=request.end_sentence,
            range_fragment=range_fragment,
            artifacts=artifacts,
            sentences=sentence_payloads,
        )


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
    selected_voice: str,
    primary_target_language: str,
    slide_render_options: Optional[SlideRenderOptions],
    template_name: Optional[str],
    video_backend: str,
    video_backend_settings: Mapping[str, Mapping[str, object]],
) -> BatchExporter:
    """Construct a :class:`BatchExporter` for the provided pipeline context."""

    voice_name = get_voice_display_name(
        selected_voice,
        primary_target_language,
        LANGUAGE_CODES,
    )

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
        selected_voice=selected_voice,
        voice_name=voice_name,
        slide_render_options=slide_render_options,
        template_name=template_name,
        video_backend=video_backend,
        video_backend_settings=video_backend_settings,
    )
    return BatchExporter(context)
