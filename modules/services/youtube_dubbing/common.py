from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from modules import logging_manager as log_mgr

logger = log_mgr.get_logger().getChild("services.youtube_dubbing")

DEFAULT_YOUTUBE_VIDEO_ROOT = Path("/Volumes/Data/Video/Youtube").expanduser()

_VIDEO_EXTENSIONS = {"mp4", "mkv", "mov", "webm", "m4v"}
_SUBTITLE_EXTENSIONS = {"ass", "srt", "vtt", "sub"}
_LANGUAGE_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,16}$")
_DEFAULT_ORIGINAL_MIX_PERCENT = 15.0
_DEFAULT_FLUSH_SENTENCES = 10
_TEMP_DIR = Path("/tmp")
_SUBTITLE_MIRROR_DIR = (
    Path(os.environ.get("SUBTITLE_SOURCE_DIR") or "/Volumes/Data/Download/Subtitles").expanduser()
)
_GAP_MIX_SCALAR = 0.25
_GAP_MIX_MAX_PERCENT = 5.0
_TARGET_DUB_HEIGHT = 480
_MIN_DIALOGUE_GAP_SECONDS = 0.0
_MIN_DIALOGUE_DURATION_SECONDS = 0.1
_YOUTUBE_ID_PATTERN = re.compile(r"\[[a-z0-9_-]{8,15}\]", re.IGNORECASE)
_ASS_DIALOGUE_PATTERN = re.compile(
    r"^Dialogue:\s*[^,]*,(?P<start>[^,]+),(?P<end>[^,]+),[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,(?P<text>.*)$",
    re.IGNORECASE,
)
_WHITESPACE_PATTERN = re.compile(r"\s+")
_LLM_WORKER_CAP = 4
_ENCODING_WORKER_CAP = 10


@dataclass(frozen=True)
class YoutubeNasSubtitle:
    """Description of a subtitle file stored alongside a downloaded video."""

    path: Path
    language: Optional[str]
    format: str


@dataclass(frozen=True)
class YoutubeNasVideo:
    """Metadata for a downloaded YouTube video on the NAS."""

    path: Path
    size_bytes: int
    modified_at: datetime
    subtitles: List[YoutubeNasSubtitle]
    source: str = "youtube"


@dataclass(frozen=True)
class _AssDialogue:
    """Parsed ASS dialogue entry with translation text."""

    start: float
    end: float
    translation: str
    original: str
    transliteration: Optional[str] = None
    rtl_normalized: bool = False
    speech_offset: Optional[float] = None
    speech_duration: Optional[float] = None

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class _DubJobCancelled(Exception):
    """Raised when a YouTube dubbing job is interrupted."""


__all__ = [
    "DEFAULT_YOUTUBE_VIDEO_ROOT",
    "_ASS_DIALOGUE_PATTERN",
    "_DEFAULT_FLUSH_SENTENCES",
    "_DEFAULT_ORIGINAL_MIX_PERCENT",
    "_ENCODING_WORKER_CAP",
    "_GAP_MIX_MAX_PERCENT",
    "_GAP_MIX_SCALAR",
    "_LANGUAGE_TOKEN_PATTERN",
    "_LLM_WORKER_CAP",
    "_MIN_DIALOGUE_DURATION_SECONDS",
    "_MIN_DIALOGUE_GAP_SECONDS",
    "_SUBTITLE_EXTENSIONS",
    "_SUBTITLE_MIRROR_DIR",
    "_TARGET_DUB_HEIGHT",
    "_TEMP_DIR",
    "_WHITESPACE_PATTERN",
    "_VIDEO_EXTENSIONS",
    "_YOUTUBE_ID_PATTERN",
    "_AssDialogue",
    "_DubJobCancelled",
    "YoutubeNasSubtitle",
    "YoutubeNasVideo",
    "logger",
]
