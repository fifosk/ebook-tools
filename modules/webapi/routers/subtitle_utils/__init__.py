"""Subtitle route modules."""

from .parsing import (
    as_bool,
    coerce_int,
    parse_timestamp,
    parse_ass_font_size,
    parse_ass_emphasis_scale,
    parse_timecode_to_seconds,
    parse_time_offset,
    parse_end_time,
    parse_tempo_value,
    infer_language_from_name,
)

from .youtube_routes import (
    router as youtube_router,
    _looks_like_youtube_subtitle,
)

from .metadata_routes import router as metadata_router

__all__ = [
    # Parsing utilities
    "as_bool",
    "coerce_int",
    "parse_timestamp",
    "parse_ass_font_size",
    "parse_ass_emphasis_scale",
    "parse_timecode_to_seconds",
    "parse_time_offset",
    "parse_end_time",
    "parse_tempo_value",
    "infer_language_from_name",
    # Routers
    "youtube_router",
    "metadata_router",
    # Helpers
    "_looks_like_youtube_subtitle",
]
