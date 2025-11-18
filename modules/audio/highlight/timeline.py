"""Shared helpers for constructing slide highlight timelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from pydub import AudioSegment

from modules.text import split_highlight_tokens

from .core import (
    HighlightEvent,
    _build_events_from_metadata,
    _build_legacy_highlight_events,
    _get_audio_metadata,
)


@dataclass(slots=True)
class TimelineBuildOptions:
    """Configuration for highlight timeline construction."""

    sync_ratio: float = 1.0
    word_highlighting: bool = True
    highlight_granularity: str = "word"
    events: Optional[Sequence[HighlightEvent]] = None


@dataclass(slots=True)
class TimelineBuildResult:
    """Result returned by :func:`build` describing highlight events."""

    events: List[HighlightEvent]
    effective_granularity: str
    original_word_count: int
    translation_word_count: int
    transliteration_word_count: int


def _parse_sentence_block(block: str) -> Tuple[str, str, str, str]:
    """Extract header and text segments from a sentence block."""

    raw_lines = block.split("\n")
    header_line = raw_lines[0] if raw_lines else ""
    content = "\n".join(raw_lines[1:]).strip()
    content_lines = [line.strip() for line in content.split("\n") if line.strip()]
    if len(content_lines) >= 3:
        original_seg = content_lines[0]
        translation_seg = content_lines[1]
        transliteration_seg = content_lines[2]
    elif len(content_lines) >= 2:
        original_seg = content_lines[0]
        translation_seg = " ".join(content_lines[1:])
        transliteration_seg = ""
    else:
        original_seg = translation_seg = content
        transliteration_seg = ""
    return header_line, original_seg, translation_seg, transliteration_seg


def _split_translation_units(header_line: str, translation_seg: str) -> Sequence[str]:
    """Return translation units honoring languages without whitespace separators."""

    tokens = split_highlight_tokens(translation_seg)
    if tokens:
        return tokens
    return [translation_seg] if translation_seg else []


def _positive_duration_events(events: Sequence[HighlightEvent]) -> List[HighlightEvent]:
    return [event for event in events if event.duration > 0]


def _has_char_steps(events: Sequence[HighlightEvent]) -> bool:
    return any(
        event.step is not None
        and event.step.char_index_start is not None
        and event.step.char_index_end is not None
        for event in events
    )


def build(
    block: str,
    audio_segment: Optional[AudioSegment],
    options: Optional[TimelineBuildOptions] = None,
) -> TimelineBuildResult:
    """Construct highlight events and determine effective granularity."""

    opts = options or TimelineBuildOptions()

    header_line, original_seg, translation_seg, transliteration_seg = _parse_sentence_block(block)
    original_words = original_seg.split()
    translation_units = _split_translation_units(header_line, translation_seg)
    transliteration_words = transliteration_seg.split()

    num_original_words = len(original_words)
    num_translation_words = len(translation_units)
    num_translit_words = len(transliteration_words)

    audio_duration = float(audio_segment.duration_seconds) if audio_segment else 0.0

    if opts.events is not None:
        candidate_events = list(opts.events)
    elif not opts.word_highlighting:
        candidate_events = [
            HighlightEvent(
                duration=max(audio_duration * opts.sync_ratio, 0.0),
                original_index=num_original_words,
                translation_index=num_translation_words,
                transliteration_index=num_translit_words,
            )
        ]
    else:
        candidate_events: List[HighlightEvent] = []
        metadata = _get_audio_metadata(audio_segment) if audio_segment is not None else None
        if metadata and metadata.parts:
            candidate_events = _build_events_from_metadata(
                metadata,
                opts.sync_ratio,
                num_original_words,
                num_translation_words,
                num_translit_words,
            )
        if not candidate_events:
            candidate_events = _build_legacy_highlight_events(
                audio_duration,
                opts.sync_ratio,
                original_words,
                translation_units,
                transliteration_words,
            )

    timeline_events = _positive_duration_events(candidate_events)
    if not timeline_events:
        timeline_events = [
            HighlightEvent(
                duration=max(audio_duration * opts.sync_ratio, 0.0),
                original_index=num_original_words,
                translation_index=num_translation_words,
                transliteration_index=num_translit_words,
            )
        ]

    has_char_steps = _has_char_steps(timeline_events)
    if (
        opts.word_highlighting
        and opts.highlight_granularity == "char"
        and has_char_steps
    ):
        effective_granularity = "char"
    else:
        effective_granularity = "word"

    return TimelineBuildResult(
        events=list(timeline_events),
        effective_granularity=effective_granularity,
        original_word_count=num_original_words,
        translation_word_count=num_translation_words,
        transliteration_word_count=num_translit_words,
    )


__all__ = ["TimelineBuildOptions", "TimelineBuildResult", "build"]
