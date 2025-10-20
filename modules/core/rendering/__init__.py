"""Rendering pipeline package exposing high-level helpers."""

from __future__ import annotations

from threading import Event
from typing import List, Optional, Sequence, Tuple

from pydub import AudioSegment

from modules.core.config import PipelineConfig
from modules.core.translation import TranslationWorkerPool
from modules.progress_tracker import ProgressTracker

from .constants import LANGUAGE_CODES, NON_LATIN_LANGUAGES
from .pipeline import RenderPipeline


def process_epub(
    input_file: str,
    base_output_file: str,
    input_language: str,
    target_languages: Sequence[str],
    sentences_per_file: int,
    start_sentence: int,
    end_sentence: Optional[int],
    generate_audio: bool,
    audio_mode: str,
    written_mode: str,
    output_html: bool,
    output_pdf: bool,
    *,
    refined_list: Sequence[str],
    generate_video: bool,
    include_transliteration: bool = False,
    book_metadata: Optional[dict] = None,
    pipeline_config: PipelineConfig,
    progress_tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[Event] = None,
    translation_pool: Optional[TranslationWorkerPool] = None,
) -> Tuple[
    List[str],
    Optional[List[AudioSegment]],
    List[str],
    str,
    str,
]:
    """Entry point mirroring the legacy :func:`process_epub` signature."""

    pipeline = RenderPipeline(
        pipeline_config=pipeline_config,
        progress_tracker=progress_tracker,
        stop_event=stop_event,
        translation_pool=translation_pool,
    )
    return pipeline.process_epub(
        input_file=input_file,
        base_output_file=base_output_file,
        input_language=input_language,
        target_languages=target_languages,
        sentences_per_file=sentences_per_file,
        start_sentence=start_sentence,
        end_sentence=end_sentence,
        generate_audio=generate_audio,
        audio_mode=audio_mode,
        written_mode=written_mode,
        output_html=output_html,
        output_pdf=output_pdf,
        refined_list=refined_list,
        generate_video=generate_video,
        include_transliteration=include_transliteration,
        book_metadata=book_metadata,
    )


__all__ = [
    "LANGUAGE_CODES",
    "NON_LATIN_LANGUAGES",
    "RenderPipeline",
    "process_epub",
]
