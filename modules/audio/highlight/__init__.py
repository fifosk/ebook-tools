"""Audio highlight utilities and timeline helpers."""

from .core import (
    AudioHighlightPart,
    HighlightEvent,
    HighlightSegment,
    HighlightStep,
    SentenceAudioMetadata,
    coalesce_highlight_events,
    _build_events_from_metadata,
    _build_legacy_highlight_events,
    _compute_audio_highlight_metadata,
    _get_audio_metadata,
    _store_audio_metadata,
)
from .timeline import TimelineBuildOptions, TimelineBuildResult
from . import timeline

__all__ = [
    "AudioHighlightPart",
    "HighlightEvent",
    "HighlightSegment",
    "HighlightStep",
    "SentenceAudioMetadata",
    "TimelineBuildOptions",
    "TimelineBuildResult",
    "coalesce_highlight_events",
    "timeline",
    "_build_events_from_metadata",
    "_build_legacy_highlight_events",
    "_compute_audio_highlight_metadata",
    "_get_audio_metadata",
    "_store_audio_metadata",
]
