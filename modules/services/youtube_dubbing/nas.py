from __future__ import annotations

import html
import json
import os
import shutil
import stat as stat_module
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set

from modules.subtitles import load_subtitle_cues
from modules.subtitles.models import SubtitleCue
from modules.subtitles.io import write_srt
from modules.subtitles.merge import merge_youtube_subtitle_cues
from modules.services import source_discovery
from modules.services.source_discovery import safe_stat

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


@dataclass(frozen=True)
class SubtitleDeletionResult:
    """Outcome from deleting a subtitle and its mirrored artifacts."""

    removed: List[Path]
    missing: List[Path]


def _safe_path_exists(path: Path) -> bool:
    return safe_stat(path) is not None


def _safe_is_regular_file(path: Path) -> bool:
    stat_result = safe_stat(path)
    return stat_result is not None and stat_module.S_ISREG(stat_result.st_mode)


def list_downloaded_videos(
    base_dir: Path = DEFAULT_YOUTUBE_VIDEO_ROOT,
    *,
    recover_partials: bool = True,
    max_results: int | None = None,
) -> List[YoutubeNasVideo]:
    """Return discovered videos under ``base_dir`` with adjacent subtitles."""

    resolved = base_dir.expanduser()
    root_stat = safe_stat(resolved)
    if root_stat is None or not stat_module.S_ISDIR(root_stat.st_mode):
        raise FileNotFoundError(f"Video directory '{resolved}' is not accessible")
    if max_results is not None and max_results <= 0:
        return []

    videos: List[YoutubeNasVideo] = []

    def _finalize_partial_video(path: Path) -> Optional[Path]:
        """Attempt to recover a completed download by dropping a trailing .part suffix."""

        if path.suffix.lower() != ".part":
            return None
        target = path.with_suffix("")
        if _safe_path_exists(target):
            return None
        try:
            path.rename(target)
            logger.info("Recovered partial YouTube download as %s", target)
            return target
        except OSError:
            logger.debug("Unable to rename partial download %s", path, exc_info=True)
            return None

    suffixes = {f".{extension}" for extension in _VIDEO_EXTENSIONS | _SUBTITLE_EXTENSIONS}
    if recover_partials:
        suffixes.add(".part")
    discovered_by_folder: dict[Path, List[source_discovery.DiscoveredSourceFile]] = {}
    for discovered in source_discovery.iter_visible_source_files(resolved, suffixes=suffixes):
        discovered_by_folder.setdefault(discovered.path.parent, []).append(discovered)

    for folder in sorted(discovered_by_folder, key=lambda path: path.as_posix().casefold()):
        video_candidates: List[tuple[Path, os.stat_result]] = []
        subtitle_candidates: List[tuple[Path, str, os.stat_result]] = []
        for discovered in sorted(discovered_by_folder[folder], key=lambda entry: entry.path.name.casefold()):
            path = discovered.path
            entry_stat = discovered.stat
            if path.suffix.lower() == ".part":
                recovered = _finalize_partial_video(path)
                if recovered is None:
                    continue
                path = recovered
                recovered_stat = safe_stat(path)
                if recovered_stat is None or not stat_module.S_ISREG(recovered_stat.st_mode):
                    logger.debug("Skipping stale recovered NAS video candidate %s", path)
                    continue
                entry_stat = recovered_stat
                ext = path.suffix.lower().lstrip(".")
            else:
                ext = path.suffix.lower().lstrip(".")
            if ext not in _VIDEO_EXTENSIONS:
                if ext in _SUBTITLE_EXTENSIONS:
                    subtitle_candidates.append((path, ext, entry_stat))
                continue
            if ".dub" in path.stem.lower():
                continue

            video_candidates.append((path, entry_stat))

        for path, video_stat in video_candidates:
            subtitles: List[YoutubeNasSubtitle] = []
            for candidate, sub_ext, candidate_stat in subtitle_candidates:
                if not _subtitle_matches_video(path, candidate):
                    continue
                try:
                    resolved_subtitle = candidate.resolve()
                except OSError:
                    logger.debug("Unable to resolve NAS subtitle candidate %s", candidate, exc_info=True)
                    continue
                language = _find_language_token(candidate)
                subtitles.append(
                    YoutubeNasSubtitle(
                        path=resolved_subtitle,
                        language=language,
                        format=sub_ext,
                    )
                )
            folder_stat = safe_stat(folder)
            effective_mtime = (
                max(video_stat.st_mtime, folder_stat.st_mtime)
                if folder_stat is not None and stat_module.S_ISDIR(folder_stat.st_mode)
                else video_stat.st_mtime
            )
            try:
                resolved_video = path.resolve()
            except OSError:
                logger.debug("Unable to resolve NAS video candidate %s", path, exc_info=True)
                continue
            _append_bounded_newest_video(
                videos,
                YoutubeNasVideo(
                    path=resolved_video,
                    size_bytes=video_stat.st_size,
                    # Prefer the folder mtime when available because NAS downloads can preserve the
                    # original file timestamp, which makes "recently added" videos appear old.
                    modified_at=datetime.fromtimestamp(effective_mtime),
                    subtitles=sorted(subtitles, key=lambda s: s.path.name),
                    source=_classify_video_source(path),
                ),
                max_results,
            )

    videos.sort(key=lambda entry: (-entry.modified_at.timestamp(), entry.path.as_posix().casefold()))
    return videos


def _append_bounded_newest_video(
    videos: List[YoutubeNasVideo],
    video: YoutubeNasVideo,
    max_results: int | None,
) -> None:
    videos.append(video)
    if max_results is None:
        return
    videos.sort(key=lambda entry: (-entry.modified_at.timestamp(), entry.path.as_posix().casefold()))
    if len(videos) > max_results:
        del videos[max_results:]


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


def _subtitle_codec_is_image_based(codec_name: Optional[str]) -> bool:
    """Return True when the subtitle codec represents images (no text to extract)."""

    if not codec_name:
        return False
    lowered = codec_name.lower()
    # Common bitmap codecs that cannot be converted to text-based SRT without OCR.
    return lowered in {
        "hdmv_pgs_subtitle",
        "pgssub",
        "dvb_subtitle",
        "dvd_subtitle",
        "xsub",
        "dvb_teletext",
    }


def _summarize_ffmpeg_error(stderr: str) -> str:
    """Return a compact error string instead of the full ffmpeg banner."""

    if not stderr:
        return "ffmpeg failed"
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    # Drop leading banner/configuration noise.
    while lines and lines[0].lower().startswith("ffmpeg version"):
        lines.pop(0)
    # Prefer the last line that looks like an error message.
    for line in reversed(lines):
        lower = line.lower()
        if "error" in lower or "invalid" in lower or "unsupported" in lower:
            return line
    # Fall back to the final line to keep the response concise.
    return lines[-1] if lines else "ffmpeg failed"


def _normalize_language_filters(languages: Optional[Iterable[str]]) -> Set[str]:
    """Return a normalized set of language filters (lowercase tokens)."""

    filters: Set[str] = set()
    if not languages:
        return filters
    for value in languages:
        if not value:
            continue
        normalized = _normalize_language_hint(value) or value.strip().lower()
        if normalized:
            filters.add(normalized)
    return filters


def _language_matches_filters(language: Optional[str], filters: Set[str]) -> bool:
    """Return True when the given language matches one of the filters."""

    if not filters:
        return True
    if not language:
        return False
    normalized = _normalize_language_hint(language) or language.strip().lower()
    if not normalized:
        return False
    if normalized in filters:
        return True
    return any(normalized.startswith(f"{token}-") for token in filters)


def list_inline_subtitle_streams(video_path: Path) -> List[dict]:
    """Return metadata about embedded subtitle streams without extracting them."""

    resolved = video_path.expanduser()
    if not _safe_is_regular_file(resolved):
        raise FileNotFoundError(f"Video file '{resolved}' does not exist")
    streams = _probe_subtitle_streams(resolved)
    results: List[dict] = []
    for stream in streams:
        stream_index = stream.get("index")
        position = int(stream.get("__position__", 0))
        tags = stream.get("tags") or {}
        language = _normalize_language_hint(tags.get("language") or tags.get("LANGUAGE"))
        codec = stream.get("codec_name") or stream.get("codec")
        title = tags.get("title") or tags.get("TITLE")
        results.append(
            {
                "index": stream_index,
                "position": position,
                "language": language,
                "codec": codec,
                "title": title,
                "can_extract": not _subtitle_codec_is_image_based(codec),
            }
        )
    return results


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
    while _safe_path_exists(candidate):
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


def delete_nas_subtitle(subtitle_path: Path) -> SubtitleDeletionResult:
    """
    Delete a subtitle from the NAS along with any mirrored HTML transcript.

    Removes the subtitle beside the video, the mirrored copy inside
    ``_SUBTITLE_MIRROR_DIR`` (when configured), and an ``html/<name>.html``
    companion if present in either location.
    """

    resolved = subtitle_path.expanduser()
    suffix = resolved.suffix.lower().lstrip(".")
    if suffix not in _SUBTITLE_EXTENSIONS:
        raise ValueError("subtitle_path must reference an ASS, SRT, VTT, or SUB subtitle file")
    if not _safe_path_exists(resolved):
        return SubtitleDeletionResult(removed=[], missing=[resolved])

    removed: List[Path] = []
    missing: List[Path] = []

    def _delete(path: Path) -> None:
        try:
            if _safe_is_regular_file(path):
                path.unlink()
                removed.append(path.resolve())
            else:
                missing.append(path.resolve())
        except FileNotFoundError:
            missing.append(path.resolve())
        except Exception:
            logger.warning("Unable to delete subtitle artifact %s", path, exc_info=True)

    _delete(resolved)

    companions: Set[Path] = {
        resolved.parent / "html" / f"{resolved.stem}.html",
    }
    if _SUBTITLE_MIRROR_DIR:
        companions.add(_SUBTITLE_MIRROR_DIR / resolved.name)
        companions.add(_SUBTITLE_MIRROR_DIR / "html" / f"{resolved.stem}.html")

    for companion in companions:
        _delete(companion)

    return SubtitleDeletionResult(removed=removed, missing=missing)


def delete_downloaded_video(video_path: Path) -> SubtitleDeletionResult:
    """
    Delete a downloaded video folder and any adjacent subtitles or mirrored artifacts.

    This removes the parent directory of the video (covering the video file,
    dubbed output folders, and matching subtitle files in the same directory)
    plus any mirrored HTML companions when present.
    """

    resolved = video_path.expanduser()
    try:
        resolved = resolved.resolve(strict=False)
    except OSError:
        raise FileNotFoundError(f"Video file '{resolved}' does not exist")

    suffix = resolved.suffix.lower().lstrip(".")
    if suffix not in _VIDEO_EXTENSIONS:
        raise ValueError("video_path must reference a supported video file")

    if not _safe_path_exists(resolved):
        return SubtitleDeletionResult(removed=[], missing=[resolved])
    if not _safe_is_regular_file(resolved):
        raise ValueError("video_path must reference a file")

    video_dir = resolved.parent

    removed: List[Path] = []
    missing: List[Path] = []

    subtitles: List[Path] = []
    try:
        for candidate in video_dir.iterdir():
            try:
                if not _safe_is_regular_file(candidate):
                    continue
                suffix = candidate.suffix.lower().lstrip(".")
                if suffix not in _SUBTITLE_EXTENSIONS:
                    continue
                if not _subtitle_matches_video(resolved, candidate):
                    continue
            except OSError:
                logger.debug("Skipping stale subtitle candidate %s during video deletion", candidate, exc_info=True)
                continue
            subtitles.append(candidate)
    except OSError:
        logger.warning("Unable to scan subtitles for %s during deletion", resolved, exc_info=True)

    for subtitle in subtitles:
        try:
            result = delete_nas_subtitle(subtitle)
            removed.extend(result.removed)
            missing.extend(result.missing)
        except FileNotFoundError:
            missing.append(subtitle.resolve())
        except Exception:
            logger.warning("Unable to delete subtitle %s while removing %s", subtitle, resolved, exc_info=True)

    try:
        shutil.rmtree(video_dir)
        removed.append(video_dir.resolve())
        removed.append(resolved)
    except FileNotFoundError:
        missing.append(video_dir.resolve())
    except Exception:
        logger.warning("Unable to delete folder %s for %s; falling back to file removal", video_dir, resolved, exc_info=True)
        try:
            resolved.unlink()
            removed.append(resolved)
        except FileNotFoundError:
            missing.append(resolved)
        except Exception:
            logger.warning("Unable to delete video %s after folder removal failed", resolved, exc_info=True)

    return SubtitleDeletionResult(removed=removed, missing=missing)


def extract_inline_subtitles(
    video_path: Path, languages: Optional[Sequence[str]] = None
) -> List[YoutubeNasSubtitle]:
    """
    Extract embedded subtitle tracks from ``video_path`` into SRT files.

    Returns the list of extracted subtitles, written alongside the video.
    """

    resolved = video_path.expanduser()
    if not _safe_is_regular_file(resolved):
        raise FileNotFoundError(f"Video file '{resolved}' does not exist")
    language_filters = _normalize_language_filters(languages)
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
        codec = stream.get("codec_name") or stream.get("codec")
        if language_filters and not _language_matches_filters(language, language_filters):
            logger.info(
                "Skipping subtitle stream %s (language=%s) not in selection %s",
                stream_index,
                language,
                sorted(language_filters),
                extra={
                    "event": "youtube.dub.subtitles.extract.skipped",
                    "reason": "language-filter",
                    "language": language,
                    "filters": sorted(language_filters),
                },
            )
            continue
        if _subtitle_codec_is_image_based(codec):
            failed_reasons.append(
                f"stream {stream_index}: image-based subtitle codec '{codec}' cannot be converted to SRT;"
                " provide a text subtitle instead"
            )
            logger.info(
                "Skipping image-based subtitle stream %s (%s) in %s",
                stream_index,
                codec,
                resolved.as_posix(),
                extra={
                    "event": "youtube.dub.subtitles.extract.skipped",
                    "reason": "image-based",
                    "codec": codec,
                },
            )
            continue
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
            failed_reasons.append(f"stream {stream_index}: {_summarize_ffmpeg_error(stderr)}")
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
        reason_parts: List[str] = []
        if language_filters and streams:
            reason_parts.append(f"no subtitle streams matched languages: {', '.join(sorted(language_filters))}")
        if failed_reasons:
            reason_parts.extend(failed_reasons)
        elif streams:
            reason_parts.append("streams may be image-based or unsupported")
        reason = f" ({'; '.join(reason_parts)})" if reason_parts else ""
        raise ValueError(f"No subtitle streams could be extracted from the video{reason}")
    return extracted


__all__ = [
    "DEFAULT_YOUTUBE_VIDEO_ROOT",
    "YoutubeNasSubtitle",
    "YoutubeNasVideo",
    "SubtitleDeletionResult",
    "_build_subtitle_output_path",
    "_mirror_subtitle_to_source_dir",
    "delete_nas_subtitle",
    "_normalize_all_caps_cues",
    "_normalize_language_filters",
    "_language_matches_filters",
    "_probe_subtitle_streams",
    "list_inline_subtitle_streams",
    "_subtitle_codec_is_image_based",
    "_summarize_ffmpeg_error",
    "_sanitize_cue_markup",
    "_sanitize_subtitle_text",
    "_sentence_case_line",
    "_looks_all_caps",
    "extract_inline_subtitles",
    "list_downloaded_videos",
    "logger",
]
