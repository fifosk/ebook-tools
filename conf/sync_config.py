"""Configuration constants for library synchronization."""

from __future__ import annotations

import re

SANITIZE_PATTERN = re.compile(r"[^\w.\- ]+")
UNKNOWN_AUTHOR = "Unknown_Author"
UNTITLED_BOOK = "Untitled_Book"
UNKNOWN_LANGUAGE = "unknown"
UNKNOWN_GENRE = "Unknown Genre"

MEDIA_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".aac",
    ".flac",
    ".ogg",
    ".m4a",
    ".mp4",
    ".mkv",
    ".mov",
    ".webm",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".html",
    ".htm",
    ".md",
    ".pdf",
    ".json",
    ".jsonl",
    ".srt",
    ".vtt",
    ".doc",
    ".docx",
    ".rtf",
}

AUDIO_SUFFIXES = {
    ".mp3",
    ".wav",
    ".aac",
    ".flac",
    ".ogg",
    ".m4a",
}

VIDEO_SUFFIXES = {
    ".mp4",
    ".mkv",
    ".mov",
    ".webm",
}

