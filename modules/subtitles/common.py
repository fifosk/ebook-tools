"""Shared constants and logger used across subtitle processing modules."""

from __future__ import annotations

import re

from modules import logging_manager as log_mgr

logger = log_mgr.get_logger().getChild("subtitles.processing")

SRT_TIMESTAMP_PATTERN = re.compile(
    r"^\s*(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})"
)

WEBVTT_HEADER = re.compile(r"^\ufeff?WEBVTT", re.IGNORECASE)

DEFAULT_OUTPUT_SUFFIX = "drt"
SRT_EXTENSION = ".srt"
ASS_EXTENSION = ".ass"
ASS_STYLE_NAME = "DRT"

DEFAULT_BATCH_SIZE = 30
DEFAULT_WORKERS = 15
DEFAULT_TRANSLATION_BATCH_SIZE = 10

DEFAULT_ASS_FONT_SIZE = 56
MIN_ASS_FONT_SIZE = 12
MAX_ASS_FONT_SIZE = 120

DEFAULT_ASS_EMPHASIS = 1.6
MIN_ASS_EMPHASIS = 1.0
MAX_ASS_EMPHASIS = 2.5

ASS_BACKGROUND_COLOR = "&HA0000000"
ASS_BOX_OUTLINE = 6

__all__ = [
    "ASS_BACKGROUND_COLOR",
    "ASS_BOX_OUTLINE",
    "ASS_EXTENSION",
    "ASS_STYLE_NAME",
    "DEFAULT_ASS_EMPHASIS",
    "DEFAULT_ASS_FONT_SIZE",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_OUTPUT_SUFFIX",
    "DEFAULT_TRANSLATION_BATCH_SIZE",
    "DEFAULT_WORKERS",
    "MAX_ASS_EMPHASIS",
    "MAX_ASS_FONT_SIZE",
    "MIN_ASS_EMPHASIS",
    "MIN_ASS_FONT_SIZE",
    "SRT_EXTENSION",
    "SRT_TIMESTAMP_PATTERN",
    "WEBVTT_HEADER",
    "logger",
]
