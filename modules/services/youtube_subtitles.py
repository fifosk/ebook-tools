"""Helpers for listing and downloading YouTube subtitles with yt-dlp."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
from typing import Iterable, List, Literal, Optional

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

from modules import logging_manager as log_mgr

logger = log_mgr.get_logger().getChild("services.youtube_subtitles")

SubtitleKind = Literal["auto", "manual"]


@dataclass(frozen=True)
class YoutubeSubtitleTrack:
    """Description of an available YouTube subtitle track."""

    language: str
    kind: SubtitleKind
    name: Optional[str]
    formats: List[str]


@dataclass(frozen=True)
class YoutubeSubtitleListing:
    """Subtitle inventory for a specific YouTube video."""

    video_id: str
    title: Optional[str]
    tracks: List[YoutubeSubtitleTrack]


_COMMON_YT_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "extract_flat": False,
    "noprogress": True,
    "retries": 2,
    "compat_opts": ["no-youtube-unavailable-videos"],
    "extractor_args": {"youtube": {"player_client": ["android"]}},
}


def _normalise_language(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("Subtitle language cannot be empty")
    return trimmed


def _format_list(value: Iterable[str | None]) -> List[str]:
    seen = []
    for entry in value:
        if not entry:
            continue
        candidate = str(entry).strip()
        if candidate and candidate not in seen:
            seen.append(candidate)
    return seen


def _parse_track_entries(entries: object) -> tuple[List[str], Optional[str]]:
    if not isinstance(entries, list):
        return [], None
    formats: List[str] = []
    label: Optional[str] = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        ext = entry.get("ext")
        if isinstance(ext, str):
            normalized = ext.strip()
            if normalized and normalized not in formats:
                formats.append(normalized)
        if label is None:
            candidate = entry.get("name") or entry.get("format_note")
            if isinstance(candidate, str):
                candidate = candidate.strip()
                if candidate:
                    label = candidate
    return formats, label


def _build_tracks(info_dict: dict) -> List[YoutubeSubtitleTrack]:
    tracks: List[YoutubeSubtitleTrack] = []
    subtitles = info_dict.get("subtitles") or {}
    auto_subs = info_dict.get("automatic_captions") or {}

    for language, entries in subtitles.items():
        try:
            normalized_lang = _normalise_language(str(language))
        except ValueError:
            continue
        formats, label = _parse_track_entries(entries)
        tracks.append(
            YoutubeSubtitleTrack(
                language=normalized_lang,
                kind="manual",
                name=label,
                formats=_format_list(formats),
            )
        )

    for language, entries in auto_subs.items():
        try:
            normalized_lang = _normalise_language(str(language))
        except ValueError:
            continue
        formats, label = _parse_track_entries(entries)
        tracks.append(
            YoutubeSubtitleTrack(
                language=normalized_lang,
                kind="auto",
                name=label,
                formats=_format_list(formats),
            )
        )

    # Prefer manual entries first, then alphabetical.
    tracks.sort(key=lambda track: (track.kind != "manual", track.language.lower()))
    return tracks


def list_available_subtitles(url: str) -> YoutubeSubtitleListing:
    """Return available subtitle tracks for ``url`` without downloading files."""

    options = dict(_COMMON_YT_OPTS)
    with YoutubeDL(options) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except (DownloadError, ExtractorError) as exc:
            logger.warning("Unable to list subtitles for %s", url, exc_info=True)
            raise

    video_id = str(info.get("id") or "").strip() or "video"
    title = info.get("title")
    if isinstance(title, str):
        title = title.strip() or None
    else:
        title = None
    tracks = _build_tracks(info if isinstance(info, dict) else {})
    return YoutubeSubtitleListing(video_id=video_id, title=title, tracks=tracks)


def download_subtitle(
    url: str,
    *,
    language: str,
    kind: SubtitleKind,
    output_dir: Path,
) -> Path:
    """Download a single subtitle track to ``output_dir`` and return the SRT path."""

    normalized_lang = _normalise_language(language)
    resolved_dir = output_dir.expanduser()
    resolved_dir.mkdir(parents=True, exist_ok=True)

    options = dict(_COMMON_YT_OPTS)
    options.update(
        {
            "skip_download": True,
            "writesubtitles": kind == "manual",
            "writeautomaticsub": kind == "auto",
            "subtitleslangs": [normalized_lang],
            # Ask for SRT if present; otherwise rely on postprocessing.
            "subtitlesformat": "srt/best",
            "paths": {"home": str(resolved_dir)},
            "outtmpl": str(resolved_dir / "%(title)s [%(id)s].%(ext)s"),
            "postprocessors": [{"key": "FFmpegSubtitlesConvertor", "format": "srt"}],
            "convertsubtitles": "srt",
            "overwrites": True,
        }
    )

    with YoutubeDL(options) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except (DownloadError, ExtractorError) as exc:
            logger.warning(
                "Subtitle download failed for %s (%s)", url, normalized_lang, exc_info=True
            )
            raise

        base_file = Path(ydl.prepare_filename(info))
        base_without_ext = base_file.with_suffix("")
        expected_path = base_without_ext.with_name(f"{base_without_ext.name}.{normalized_lang}.srt")
        if expected_path.exists():
            return _maybe_tag_youtube_suffix(expected_path)

        video_id = str(info.get("id") or "").strip()
        candidates = sorted(
            resolved_dir.glob(f"*{video_id}*.{normalized_lang}.srt"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return _maybe_tag_youtube_suffix(candidates[0])

        fallback_candidates = sorted(
            resolved_dir.glob(f"*{normalized_lang}.srt"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if fallback_candidates:
            return _maybe_tag_youtube_suffix(fallback_candidates[0])

    raise FileNotFoundError("Unable to locate downloaded subtitle file")


def _maybe_tag_youtube_suffix(path: Path) -> Path:
    """Ensure the filename is tagged as a YouTube download."""

    suffix = "_yt"
    if path.stem.endswith(suffix):
        return path
    tagged = path.with_name(f"{path.stem}{suffix}{path.suffix}")
    try:
        path.rename(tagged)
    except OSError:
        # Best effort rename; return original if rename fails.
        return path
    return tagged


def _slugify(value: str) -> str:
    sanitized = []
    for ch in value.strip():
        if ch.isalnum():
            sanitized.append(ch)
        elif ch in {"-", "_", " "}:
            sanitized.append("-")
        elif ch in {"(", ")", "[", "]"}:
            sanitized.append(ch)
    slug = "".join(sanitized).strip("-") or "video"
    return slug


def _ensure_directory(path: Path) -> Path:
    resolved = path.expanduser()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def download_video(
    url: str,
    *,
    output_root: Path,
    timestamp: Optional[datetime] = None,
) -> Path:
    """Download the YouTube video to ``output_root`` and return the file path."""

    timestamp = timestamp or datetime.now()
    listing = list_available_subtitles(url)
    title = listing.title or "YouTube video"
    folder_name = f"{_slugify(title)} - {timestamp:%Y-%m-%d %H-%M-%S}"
    base_dir = _ensure_directory(output_root / folder_name)

    options = dict(_COMMON_YT_OPTS)
    options.update(
        {
            "skip_download": False,
            "paths": {"home": str(base_dir)},
            "outtmpl": str(base_dir / "%(title)s [%(id)s].%(ext)s"),
            "merge_output_format": "mp4",
            "format": "bestvideo*+bestaudio/best",
            "writesubtitles": False,
            "writeautomaticsub": False,
            "noplaylist": True,
            "overwrites": True,
        }
    )

    with YoutubeDL(options) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except (DownloadError, ExtractorError) as exc:
            logger.warning("Unable to download YouTube video for %s", url, exc_info=True)
            raise
        output_path = Path(ydl.prepare_filename(info))
        merged_path = output_path.with_suffix(".mp4")
        if merged_path.exists():
            return merged_path
        if output_path.exists():
            return output_path
    raise FileNotFoundError("Video download failed; output file not found")


__all__ = [
    "YoutubeSubtitleListing",
    "YoutubeSubtitleTrack",
    "SubtitleKind",
    "download_subtitle",
    "download_video",
    "list_available_subtitles",
]
