"""Compatibility layer exposing the historical slide rendering API."""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

from PIL import Image
from pydub import AudioSegment

from modules.audio.highlight import HighlightEvent

from .slide_core import HighlightSpec, Slide
from .slide_renderer import (
    SentenceFrameBatch,
    SlideRenderOptions,
    SlideRenderProfiler,
    SlideRenderer,
)

__all__ = [
    "generate_sentence_slide_image",
    "get_default_font_path",
    "prepare_sentence_frames",
    "SlideRenderOptions",
    "SlideRenderProfiler",
]


_DEFAULT_RENDERER = SlideRenderer()


def get_default_font_path() -> str:
    """Return a platform-appropriate fallback font path for slide rendering."""

    return _DEFAULT_RENDERER.get_default_font_path()


def _build_slide(block: str, template_name: Optional[str]) -> Slide:
    slide = Slide.from_sentence_block(block, template_name=template_name)
    return slide


def generate_sentence_slide_image(
    block: str,
    original_highlight_word_index: Optional[int] = None,
    translation_highlight_word_index: Optional[int] = None,
    transliteration_highlight_word_index: Optional[int] = None,
    *,
    original_highlight_char_range: Optional[Tuple[int, int]] = None,
    translation_highlight_char_range: Optional[Tuple[int, int]] = None,
    transliteration_highlight_char_range: Optional[Tuple[int, int]] = None,
    highlight_granularity: str = "word",
    slide_size: Sequence[int] = (1280, 720),
    initial_font_size: int = 50,
    default_font_path: str = "Arial.ttf",
    bg_color: Optional[Sequence[int]] = None,
    cover_img: Optional[Image.Image] = None,
    header_info: str = "",
    profiler: Optional[SlideRenderProfiler] = None,
    template_name: Optional[str] = None,
) -> Image.Image:
    """Draw a slide image for a sentence block with optional highlighting."""

    slide = _build_slide(block, template_name)
    slide = slide.with_highlights(
        original=HighlightSpec(
            word_index=original_highlight_word_index,
            char_range=original_highlight_char_range,
        ),
        translation=HighlightSpec(
            word_index=translation_highlight_word_index,
            char_range=translation_highlight_char_range,
        ),
        transliteration=HighlightSpec(
            word_index=transliteration_highlight_word_index,
            char_range=transliteration_highlight_char_range,
        ),
    )
    return _DEFAULT_RENDERER.render_sentence_slide_image(
        slide,
        original_highlight_word_index=original_highlight_word_index,
        translation_highlight_word_index=translation_highlight_word_index,
        transliteration_highlight_word_index=transliteration_highlight_word_index,
        original_highlight_char_range=original_highlight_char_range,
        translation_highlight_char_range=translation_highlight_char_range,
        transliteration_highlight_char_range=transliteration_highlight_char_range,
        highlight_granularity=highlight_granularity,
        slide_size=slide_size,
        initial_font_size=initial_font_size,
        default_font_path=default_font_path,
        bg_color=bg_color,
        cover_img=cover_img,
        header_info=header_info,
        template_name=template_name,
        profiler=profiler,
    )


def prepare_sentence_frames(
    block: str,
    audio_seg: AudioSegment,
    sentence_index: int,
    *,
    sync_ratio: float,
    word_highlighting: bool,
    highlight_events: Optional[Sequence[HighlightEvent]] = None,
    highlight_granularity: str = "word",
    slide_size: Sequence[int] = (1280, 720),
    initial_font_size: int = 50,
    default_font_path: Optional[str] = None,
    bg_color: Optional[Sequence[int]] = None,
    cover_img: Optional[Image.Image] = None,
    header_info: str = "",
    render_options: Optional[SlideRenderOptions] = None,
    template_name: Optional[str] = None,
) -> SentenceFrameBatch:
    """Prepare rendered slide frames for a single sentence."""

    slide = _build_slide(block, template_name)
    return _DEFAULT_RENDERER.prepare_sentence_frames(
        slide,
        audio_seg,
        sentence_index,
        sync_ratio=sync_ratio,
        word_highlighting=word_highlighting,
        highlight_events=highlight_events,
        highlight_granularity=highlight_granularity,
        slide_size=slide_size,
        initial_font_size=initial_font_size,
        default_font_path=default_font_path,
        bg_color=bg_color,
        cover_img=cover_img,
        header_info=header_info,
        render_options=render_options,
    )
