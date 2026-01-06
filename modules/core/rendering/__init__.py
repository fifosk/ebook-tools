"""Rendering pipeline package exposing high-level helpers."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Event
from typing import List, Optional, Sequence, Tuple

from pydub import AudioSegment

from modules.core.config import PipelineConfig
from modules.core.translation import ThreadWorkerPool
from modules.transliteration import TransliterationService
from modules.progress_tracker import ProgressTracker

from .constants import LANGUAGE_CODES, NON_LATIN_LANGUAGES
from .pipeline import RenderPipeline


@dataclass(slots=True)
class RenderPhaseRequest:
    """Structured payload for :func:`process_epub`."""

    pipeline_config: PipelineConfig
    input_file: str
    base_output_file: str
    input_language: str
    target_languages: Sequence[str]
    sentences_per_file: int
    start_sentence: int
    end_sentence: Optional[int]
    generate_audio: bool
    audio_mode: str
    written_mode: str
    output_html: bool
    output_pdf: bool
    refined_sentences: Sequence[str]
    generate_video: bool
    generate_images: bool = False
    include_transliteration: bool = False
    translation_provider: Optional[str] = None
    transliteration_mode: Optional[str] = None
    transliteration_model: Optional[str] = None
    book_metadata: Optional[dict] = None


def process_epub(
    request: RenderPhaseRequest,
    *,
    progress_tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[Event] = None,
    translation_pool: Optional[ThreadWorkerPool] = None,
    transliterator: Optional[TransliterationService] = None,
) -> Tuple[
    List[str],
    Optional[List[AudioSegment]],
    List[str],
    str,
    str,
]:
    """Entry point mirroring the legacy :func:`process_epub` signature."""

    pipeline = RenderPipeline(
        pipeline_config=request.pipeline_config,
        progress_tracker=progress_tracker,
        stop_event=stop_event,
        translation_pool=translation_pool,
        transliterator=transliterator,
    )
    return pipeline.process_epub(
        input_file=request.input_file,
        base_output_file=request.base_output_file,
        input_language=request.input_language,
        target_languages=request.target_languages,
        sentences_per_file=request.sentences_per_file,
        start_sentence=request.start_sentence,
        end_sentence=request.end_sentence,
        generate_audio=request.generate_audio,
        audio_mode=request.audio_mode,
        written_mode=request.written_mode,
        output_html=request.output_html,
        output_pdf=request.output_pdf,
        refined_list=request.refined_sentences,
        generate_video=request.generate_video,
        generate_images=request.generate_images,
        include_transliteration=request.include_transliteration,
        translation_provider=request.translation_provider,
        transliteration_mode=request.transliteration_mode,
        transliteration_model=request.transliteration_model,
        book_metadata=request.book_metadata,
    )


__all__ = [
    "LANGUAGE_CODES",
    "NON_LATIN_LANGUAGES",
    "RenderPhaseRequest",
    "RenderPipeline",
    "process_epub",
]
