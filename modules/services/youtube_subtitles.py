"""Helpers for listing and downloading YouTube subtitles with yt-dlp."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
import random
import re
import shutil
import time
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
    video_formats: List["YoutubeVideoFormat"]


@dataclass(frozen=True)
class YoutubeVideoFormat:
    """Description of an available YouTube mp4 video format."""

    format_id: str
    ext: str
    resolution: Optional[str]
    fps: Optional[int]
    note: Optional[str]
    bitrate_kbps: Optional[float]
    filesize: Optional[str]


_COMMON_YT_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "extract_flat": False,
    "noprogress": True,
    # Keep built-in retries modest; we handle 429s with our own backoff loop.
    "retries": 3,
    "compat_opts": ["no-youtube-unavailable-videos"],
    "extractor_args": {"youtube": {"player_client": ["android"]}},
}
_TITLE_SEGMENT_LIMIT = 50
_ID_SUFFIX_PATTERN = re.compile(r"^(?P<title>.+?)(?P<suffix>\s*\[[^\]]+\].*)$")


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


def _is_rate_limited_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    return "429" in message or "too many requests" in message or "rate limit" in message


def _extract_with_backoff(ydl: YoutubeDL, url: str, *, download: bool) -> dict:
    """Call yt-dlp with explicit backoff for 429s."""

    delays = [0.0, 1.0, 2.0, 4.0, 8.0]
    last_error: Optional[Exception] = None
    for delay in delays:
        if delay:
            time.sleep(delay + random.uniform(0, 0.5))
        try:
            return ydl.extract_info(url, download=download)
        except (DownloadError, ExtractorError) as exc:
            last_error = exc
            if not _is_rate_limited_error(exc):
                raise
            continue
    if last_error:
        raise last_error
    raise RuntimeError("Extraction failed without error")


def _format_size(value: float) -> str:
    size = float(value)
    for unit in ("bytes", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.0f} TiB"


def _parse_resolution(entry: dict) -> Optional[str]:
    height = entry.get("height")
    width = entry.get("width")
    if isinstance(height, int) and isinstance(width, int) and height > 0 and width > 0:
        return f"{width}x{height}"
    resolution = entry.get("resolution")
    if isinstance(resolution, str) and resolution.strip():
        return resolution.strip()
    return None


def _build_video_formats(info_dict: dict) -> List[YoutubeVideoFormat]:
    formats: List[YoutubeVideoFormat] = []
    for entry in info_dict.get("formats") or []:
        if not isinstance(entry, dict):
            continue
        ext = entry.get("ext")
        format_id = entry.get("format_id")
        vcodec = entry.get("vcodec")
        if ext != "mp4" or not isinstance(format_id, str) or vcodec in (None, "none"):
            continue
        resolution = _parse_resolution(entry)
        fps = entry.get("fps") if isinstance(entry.get("fps"), int) else None
        note = entry.get("format_note")
        bitrate = entry.get("tbr") if isinstance(entry.get("tbr"), (int, float)) else None
        filesize_value = entry.get("filesize") or entry.get("filesize_approx")
        filesize = (
            _format_size(float(filesize_value))
            if isinstance(filesize_value, (int, float)) and filesize_value > 0
            else None
        )
        formats.append(
            YoutubeVideoFormat(
                format_id=format_id,
                ext=ext,
                resolution=resolution,
                fps=fps,
                note=str(note).strip() if isinstance(note, str) and note.strip() else None,
                bitrate_kbps=float(bitrate) if bitrate is not None else None,
                filesize=filesize,
            )
        )

    # Highest resolution first, then bitrate/fps as tie-breakers.
    formats.sort(
        key=lambda fmt: (
            -(int(fmt.resolution.split("x")[1]) if fmt.resolution and "x" in fmt.resolution else -1),
            -(fmt.bitrate_kbps or -1),
            -(fmt.fps or -1),
        )
    )
    return formats


def list_available_subtitles(url: str) -> YoutubeSubtitleListing:
    """Return available subtitle tracks for ``url`` without downloading files."""

    options = dict(_COMMON_YT_OPTS)
    with YoutubeDL(options) as ydl:
        try:
            info = _extract_with_backoff(ydl, url, download=False)
        except (DownloadError, ExtractorError) as exc:
            logger.warning("Unable to list subtitles for %s", url, exc_info=True)
            raise

    video_id = str(info.get("id") or "").strip() or "video"
    title = info.get("title")
    if isinstance(title, str):
        title = title.strip() or None
    else:
        title = None
    payload = info if isinstance(info, dict) else {}
    tracks = _build_tracks(payload)
    video_formats = _build_video_formats(payload)
    return YoutubeSubtitleListing(
        video_id=video_id,
        title=title,
        tracks=tracks,
        video_formats=video_formats,
    )


def download_subtitle(
    url: str,
    *,
    language: str,
    kind: SubtitleKind,
    output_dir: Path,
    video_output_dir: Optional[Path] = None,
    timestamp: Optional[datetime] = None,
    video_id: Optional[str] = None,
    video_title: Optional[str] = None,
) -> Path:
    """Download a single subtitle track to ``output_dir`` and return the SRT path."""

    normalized_lang = _normalise_language(language)
    resolved_dir = output_dir.expanduser()
    resolved_dir.mkdir(parents=True, exist_ok=True)
    folder_timestamp = timestamp or datetime.now()
    video_dir = video_output_dir.expanduser() if video_output_dir is not None else None
    initial_media_base = build_youtube_basename(video_title or "YouTube video", video_id or "video")

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
            "outtmpl": str(resolved_dir / f"{initial_media_base}.%(ext)s"),
            "postprocessors": [{"key": "FFmpegSubtitlesConvertor", "format": "srt"}],
            "convertsubtitles": "srt",
            "overwrites": True,
        }
    )

    downloaded_path: Optional[Path] = None
    resolved_video_id = video_id or "video"
    resolved_title = video_title or "YouTube video"
    with YoutubeDL(options) as ydl:
        try:
            info = _extract_with_backoff(ydl, url, download=True)
        except (DownloadError, ExtractorError) as exc:
            logger.warning(
                "Subtitle download failed for %s (%s)", url, normalized_lang, exc_info=True
            )
            raise

        resolved_video_id = str(info.get("id") or "").strip() or resolved_video_id
        title_value = info.get("title")
        if isinstance(title_value, str) and title_value.strip():
            resolved_title = title_value.strip()
        base_file = Path(ydl.prepare_filename(info))
        base_without_ext = base_file.with_suffix("")
        expected_path = base_without_ext.with_name(f"{base_without_ext.name}.{normalized_lang}.srt")
        if expected_path.exists():
            downloaded_path = expected_path
        if downloaded_path is None:
            candidates = sorted(
                resolved_dir.glob(f"*{resolved_video_id}*.{normalized_lang}.srt"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                downloaded_path = candidates[0]

        if downloaded_path is None:
            fallback_candidates = sorted(
                resolved_dir.glob(f"*{normalized_lang}.srt"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if fallback_candidates:
                downloaded_path = fallback_candidates[0]

    if downloaded_path is None:
        raise FileNotFoundError("Unable to locate downloaded subtitle file")

    media_base = build_youtube_basename(resolved_title, resolved_video_id)
    target_name = f"{media_base}_yt.{normalized_lang}.srt"
    target_path = downloaded_path.with_name(target_name)
    if target_path != downloaded_path:
        try:
            downloaded_path.rename(target_path)
            downloaded_path = target_path
        except OSError:
            downloaded_path = _tag_youtube_filename(downloaded_path)
    else:
        downloaded_path = _tag_youtube_filename(downloaded_path)

    if video_dir is not None:
        try:
            mirror_folder = _ensure_directory(video_dir / build_video_folder_name(resolved_title, folder_timestamp))
            mirror_path = mirror_folder / downloaded_path.name
            shutil.copy2(downloaded_path, mirror_path)
        except Exception:
            logger.warning(
                "Failed to mirror subtitle into video directory %s",
                video_dir,
                exc_info=True,
            )

    return downloaded_path


def _tag_youtube_filename(path: Path) -> Path:
    """Ensure filename includes `_yt` before the final extension (and language, if present)."""

    name = path.name
    if "_yt" in Path(name).stem:
        return path

    parts = name.split(".")
    tagged_name: str
    if len(parts) >= 3 and parts[-1].lower() == "srt":
        base = ".".join(parts[:-2]) or path.stem
        language = parts[-2]
        tagged_name = f"{base}_yt.{language}.srt"
    else:
        tagged_name = f"{path.stem}_yt{path.suffix}"

    tagged_path = path.with_name(tagged_name)
    try:
        path.rename(tagged_path)
    except OSError:
        return path
    return tagged_path


def _trim_title_segment(value: str, *, max_length: int = _TITLE_SEGMENT_LIMIT) -> str:
    """Return ``value`` shortened to ``max_length`` characters, without trailing punctuation."""

    normalized = value.strip()
    if len(normalized) <= max_length:
        return normalized or "video"
    trimmed = normalized[:max_length].rstrip("-_. ")
    return trimmed or normalized[:max_length]


def build_youtube_title_slug(title: str, *, max_length: int = _TITLE_SEGMENT_LIMIT) -> str:
    """Slugify and trim a YouTube title for filesystem use."""

    return _trim_title_segment(_slugify(title), max_length=max_length)


def build_youtube_basename(
    title: str, video_id: str, *, max_length: int = _TITLE_SEGMENT_LIMIT
) -> str:
    """Return a trimmed base name including the YouTube video ID."""

    safe_title = build_youtube_title_slug(title, max_length=max_length)
    safe_id = video_id.strip() or "video"
    return f"{safe_title} [{safe_id}]"


def build_video_folder_name(title: str, timestamp: datetime) -> str:
    """Return the folder name for a downloaded video based on title and timestamp."""

    return f"{build_youtube_title_slug(title)} - {timestamp:%Y-%m-%d %H-%M-%S}"


def trim_stem_preserving_id(stem: str, *, max_length: int = _TITLE_SEGMENT_LIMIT) -> str:
    """Trim the leading title portion of ``stem`` while keeping any trailing [id] suffix."""

    match = _ID_SUFFIX_PATTERN.match(stem)
    if match:
        base = match.group("title") or ""
        suffix = match.group("suffix") or ""
    else:
        base, suffix = stem, ""
    trimmed_base = _trim_title_segment(base, max_length=max_length)
    return f"{trimmed_base}{suffix}"


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
    format_id: Optional[str] = None,
) -> Path:
    """Download the YouTube video to ``output_root`` and return the file path."""

    timestamp = timestamp or datetime.now()
    listing = list_available_subtitles(url)
    title = listing.title or "YouTube video"
    video_id = listing.video_id or "video"
    folder_name = build_video_folder_name(title, timestamp)
    base_dir = _ensure_directory(output_root / folder_name)
    media_base = build_youtube_basename(title, video_id)
    video_extensions = {"mkv", "mp4", "webm", "m4v", "mov"}

    format_selector = (
        f"{format_id}+bestaudio[ext=m4a]/bestaudio/best"
        if format_id
        else "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    )

    options = dict(_COMMON_YT_OPTS)
    options.update(
        {
            "skip_download": False,
            "paths": {"home": str(base_dir)},
            "outtmpl": str(base_dir / f"{media_base}.%(ext)s"),
            # Prefer mp4 video variants (optionally respecting a chosen itag) and
            # mux with the best available audio.
            "format": format_selector,
            "merge_output_format": "mp4",
            "writesubtitles": False,
            "writeautomaticsub": False,
            "noplaylist": True,
            "overwrites": True,
        }
    )

    with YoutubeDL(options) as ydl:
        try:
            info = _extract_with_backoff(ydl, url, download=True)
        except (DownloadError, ExtractorError) as exc:
            logger.warning("Unable to download YouTube video for %s", url, exc_info=True)
            raise
        # Prefer any muxed output file in the download directory, falling back to
        # yt-dlp's prepared filename if needed.
        candidates = sorted(
            (
                path
                for path in base_dir.iterdir()
                if path.is_file() and path.suffix.lower().lstrip(".") in video_extensions
            ),
            key=lambda path: (path.suffix.lower() != ".mp4", -path.stat().st_mtime),
        )
        if candidates:
            candidate = _tag_youtube_filename(candidates[0])
            target_name = f"{media_base}_yt{candidate.suffix}"
            target_path = candidate.with_name(target_name)
            if target_path != candidate:
                try:
                    candidate.rename(target_path)
                    return target_path
                except OSError:
                    return candidate
            return candidate

        output_path = Path(ydl.prepare_filename(info))
        if output_path.exists():
            candidate = _tag_youtube_filename(output_path)
            target_name = f"{media_base}_yt{candidate.suffix}"
            target_path = candidate.with_name(target_name)
            if target_path != candidate:
                try:
                    candidate.rename(target_path)
                    return target_path
                except OSError:
                    return candidate
            return candidate
    raise FileNotFoundError("Video download failed; output file not found")


__all__ = [
    "YoutubeSubtitleListing",
    "YoutubeSubtitleTrack",
    "YoutubeVideoFormat",
    "SubtitleKind",
    "download_subtitle",
    "download_video",
    "list_available_subtitles",
    "build_video_folder_name",
    "build_youtube_basename",
    "build_youtube_title_slug",
    "trim_stem_preserving_id",
]
