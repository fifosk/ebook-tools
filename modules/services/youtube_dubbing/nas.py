from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

from modules.subtitles import load_subtitle_cues
from modules.subtitles.models import SubtitleCue
from modules.subtitles.io import write_srt
from modules.subtitles.merge import merge_youtube_subtitle_cues

from .common import (
    DEFAULT_YOUTUBE_VIDEO_ROOT,
    _SUBTITLE_EXTENSIONS,
    _SUBTITLE_MIRROR_DIR,
    _TEMP_DIR,
    _VIDEO_EXTENSIONS,
    YoutubeNasSubtitle,
    YoutubeNasVideo,
    logger,
)
from .dialogues import _ASS_TAG_PATTERN, _HTML_TAG_PATTERN, _WHITESPACE_PATTERN
from .language import _find_language_token, _normalize_language_hint
from .video_utils import _classify_video_source, _subtitle_matches_video


def list_downloaded_videos(base_dir: Path = DEFAULT_YOUTUBE_VIDEO_ROOT) -> List[YoutubeNasVideo]:
    """Return discovered videos under ``base_dir`` with adjacent subtitles."""

    resolved = base_dir.expanduser()
    if not resolved.exists() or not resolved.is_dir():
        raise FileNotFoundError(f"Video directory '{resolved}' is not accessible")

    videos: List[YoutubeNasVideo] = []
    for root, _dirs, files in os.walk(resolved):
        folder = Path(root)
        for filename in files:
            path = folder / filename
            ext = path.suffix.lower().lstrip(".")
            if ".dub" in path.stem.lower():
                continue
            if ext not in _VIDEO_EXTENSIONS:
                continue
            subtitles: List[YoutubeNasSubtitle] = []
            base_stem = path.stem
            for candidate in folder.iterdir():
                if candidate.is_dir():
                    continue
                sub_ext = candidate.suffix.lower().lstrip(".")
                if sub_ext not in _SUBTITLE_EXTENSIONS:
                    continue
                if not _subtitle_matches_video(path, candidate):
                    continue
                language = _find_language_token(candidate)
                subtitles.append(
                    YoutubeNasSubtitle(
                        path=candidate.resolve(),
                        language=language,
                        format=sub_ext,
                    )
                )
            stat = path.stat()
            videos.append(
                YoutubeNasVideo(
                    path=path.resolve(),
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    subtitles=sorted(subtitles, key=lambda s: s.path.name),
                    source=_classify_video_source(path),
                )
            )

    videos.sort(key=lambda entry: entry.modified_at, reverse=True)
    return videos


def _probe_subtitle_streams(video_path: Path) -> List[dict]:
    """Return parsed subtitle streams from ffprobe output."""

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    result = subprocess.run(
        [
            ffprobe_bin,
            "-v",
            "error",
            "-select_streams",
            "s",
            "-show_entries",
            "stream=index,codec_type,codec_name:stream_tags=language,title",
            "-of",
            "json",
            str(video_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="ignore") if result.stderr else ""
        raise RuntimeError(f"ffprobe failed with exit code {result.returncode}: {stderr.strip()}")
    try:
        payload = json.loads(result.stdout.decode() or "{}")
    except Exception as exc:
        raise RuntimeError("Unable to parse ffprobe output") from exc
    streams = payload.get("streams") or []
    subtitle_streams = [stream for stream in streams if stream.get("codec_type") == "subtitle"]
    for position, stream in enumerate(subtitle_streams):
        stream["__position__"] = position
    return subtitle_streams


def _build_subtitle_output_path(video_path: Path, language: Optional[str], stream_index: int) -> Path:
    """Return a unique SRT path next to the video for the given stream."""

    folder = video_path.parent
    stem = video_path.stem
    label_parts = [stem]
    if language:
        label_parts.append(language)
    label_parts.append(f"sub{stream_index}")
    base_name = ".".join(label_parts) + ".srt"
    candidate = folder / base_name
    suffix = 1
    while candidate.exists():
        candidate = folder / f"{stem}.{language or 'sub'}{stream_index}.{suffix}.srt"
        suffix += 1
    return candidate


def _looks_all_caps(text: str) -> bool:
    """Return True when the text contains letters and all are uppercase."""

    if not text:
        return False
    sanitized = _ASS_TAG_PATTERN.sub(" ", text)
    sanitized = _HTML_TAG_PATTERN.sub(" ", sanitized)
    letters = [ch for ch in sanitized if ch.isalpha()]
    if not letters:
        return False
    return all(ch.isupper() for ch in letters)


def _sanitize_subtitle_text(text: str) -> str:
    """Return subtitle text stripped of markup and normalized whitespace."""

    normalized = html.unescape(text or "")
    normalized = _ASS_TAG_PATTERN.sub(" ", normalized)
    normalized = _HTML_TAG_PATTERN.sub(" ", normalized)
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()


def _sanitize_cue_markup(cues: Sequence[SubtitleCue]) -> List[SubtitleCue]:
    """Strip HTML/ASS markup from cue lines."""

    sanitized: List[SubtitleCue] = []
    for cue in cues:
        sanitized_lines = [_sanitize_subtitle_text(line) for line in cue.lines]
        sanitized.append(
            SubtitleCue(
                index=cue.index,
                start=cue.start,
                end=cue.end,
                lines=sanitized_lines,
            )
        )
    return sanitized


def _sentence_case_line(line: str) -> str:
    """Lowercase the line (outside formatting tags) and capitalize the first letter."""

    chars: List[str] = []
    in_angle_tag = False
    brace_depth = 0
    first_done = False
    for ch in line:
        if ch == "<":
            in_angle_tag = True
            chars.append(ch)
            continue
        if in_angle_tag:
            chars.append(ch)
            if ch == ">":
                in_angle_tag = False
            continue
        if ch == "{":
            brace_depth += 1
            chars.append(ch)
            continue
        if brace_depth > 0:
            chars.append(ch)
            if ch == "}":
                brace_depth = max(0, brace_depth - 1)
            continue
        if ch.isalpha():
            if not first_done:
                chars.append(ch.upper())
                first_done = True
            else:
                chars.append(ch.lower())
        else:
            chars.append(ch)
    return "".join(chars)


def _normalize_all_caps_cues(cues: Sequence[SubtitleCue]) -> List[SubtitleCue]:
    """Normalize cues that are fully uppercase into sentence case."""

    normalized: List[SubtitleCue] = []
    for cue in cues:
        if not _looks_all_caps(cue.as_text()):
            normalized.append(cue)
            continue
        normalized_lines = [_sentence_case_line(_sanitize_subtitle_text(line)) for line in cue.lines]
        normalized.append(
            SubtitleCue(
                index=cue.index,
                start=cue.start,
                end=cue.end,
                lines=normalized_lines,
            )
        )
    return normalized


def _mirror_subtitle_to_source_dir(subtitle_path: Path) -> Optional[Path]:
    """Copy ``subtitle_path`` into the NAS subtitle source directory."""

    try:
        target_dir = _SUBTITLE_MIRROR_DIR
        if not target_dir:
            return None
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / subtitle_path.name
        if destination.resolve() == subtitle_path.resolve():
            return destination
        shutil.copy2(subtitle_path, destination)
        return destination
    except Exception:
        logger.warning(
            "Unable to mirror extracted subtitle %s to %s",
            subtitle_path,
            _SUBTITLE_MIRROR_DIR,
            exc_info=True,
        )
        return None


def extract_inline_subtitles(video_path: Path) -> List[YoutubeNasSubtitle]:
    """
    Extract embedded subtitle tracks from ``video_path`` into SRT files.

    Returns the list of extracted subtitles, written alongside the video.
    """

    resolved = video_path.expanduser()
    if not resolved.exists():
        raise FileNotFoundError(f"Video file '{resolved}' does not exist")
    streams = _probe_subtitle_streams(resolved)
    if not streams:
        raise ValueError("No subtitle streams found in the video")
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    extracted: List[YoutubeNasSubtitle] = []
    failed_reasons: List[str] = []
    for stream in streams:
        stream_index = stream.get("index")
        position = int(stream.get("__position__", 0))
        if stream_index is None or position is None:
            continue
        tags = stream.get("tags") or {}
        language = _normalize_language_hint(tags.get("language") or tags.get("LANGUAGE"))
        output_path = _build_subtitle_output_path(resolved, language, stream_index)
        with tempfile.NamedTemporaryFile(
            suffix=".srt",
            delete=False,
            prefix=f"dub-sub-{stream_index}-",
            dir=_TEMP_DIR,
        ) as handle:
            temp_output = Path(handle.name)
        command = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(resolved),
            "-map",
            f"0:s:{position}",
            "-c:s",
            "srt",
            str(temp_output),
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode != 0:
            temp_output.unlink(missing_ok=True)
            stderr = result.stderr.decode(errors="ignore") if result.stderr else ""
            failed_reasons.append(f"stream {stream_index}: {stderr.strip() or 'ffmpeg failed'}")
            logger.warning(
                "Failed to extract subtitle stream %s from %s",
                stream_index,
                resolved.as_posix(),
                extra={
                    "event": "youtube.dub.subtitles.extract.failed",
                    "stream_index": stream_index,
                    "exit_code": result.returncode,
                },
            )
            continue
        try:
            shutil.move(str(temp_output), output_path)
        except Exception:
            logger.debug("Unable to move extracted subtitle to %s", output_path, exc_info=True)
            temp_output.unlink(missing_ok=True)
            continue
        extracted.append(
            YoutubeNasSubtitle(
                path=output_path.resolve(),
                language=language,
                format="srt",
            )
        )
        try:
            cues = load_subtitle_cues(output_path)
            sanitized_cues = _sanitize_cue_markup(cues)
            normalized_cues = _normalize_all_caps_cues(sanitized_cues)
            if normalized_cues != cues:
                write_srt(output_path, normalized_cues)
        except Exception:
            logger.warning(
                "Unable to normalize capitalized subtitles for %s",
                output_path,
                exc_info=True,
            )
        _mirror_subtitle_to_source_dir(output_path)
    if not extracted:
        reason = ""
        if streams:
            reason = f" ({'; '.join(failed_reasons)})" if failed_reasons else " (streams may be image-based or unsupported)"
        raise ValueError(f"No subtitle streams could be extracted from the video{reason}")
    return extracted


__all__ = [
    "DEFAULT_YOUTUBE_VIDEO_ROOT",
    "YoutubeNasSubtitle",
    "YoutubeNasVideo",
    "_build_subtitle_output_path",
    "_mirror_subtitle_to_source_dir",
    "_normalize_all_caps_cues",
    "_probe_subtitle_streams",
    "_sanitize_cue_markup",
    "_sanitize_subtitle_text",
    "_sentence_case_line",
    "_looks_all_caps",
    "extract_inline_subtitles",
    "list_downloaded_videos",
    "logger",
]
