"""File-backed acquisition discovery providers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from modules.services.source_discovery import (
    DiscoveredSourceFile,
    append_bounded_newest_source_file,
    iter_visible_source_files,
)
from modules.services.youtube_dubbing import list_downloaded_videos

from .models import AcquisitionCandidate, AcquisitionSubtitleHint
from .provider_roots import (
    resolve_books_root,
    resolve_manual_download_roots,
    resolve_video_root,
)
from .source_candidates import (
    append_bounded_newest_candidate,
    append_bounded_newest_manual_entry,
    is_usable_epub_entry,
    relative_path,
    title_from_filename,
)
from .tokens import encode_acquisition_token


def discover_local_epubs(
    config: Mapping[str, Any],
    query: str,
    limit: int,
) -> list[AcquisitionCandidate]:
    if limit <= 0:
        return []
    root = resolve_books_root(config=config, context=None)
    matches: list[DiscoveredSourceFile] = []

    def secondary_key(entry: DiscoveredSourceFile) -> str:
        return title_from_filename(entry.path)

    for entry in iter_visible_source_files(root, suffixes={".epub"}):
        if not is_usable_epub_entry(entry):
            continue
        source_relative_path = relative_path(entry.path, root)
        if query and query not in _search_blob(entry.path.name, source_relative_path):
            continue
        append_bounded_newest_source_file(
            matches,
            entry,
            limit,
            secondary_key=secondary_key,
        )
    return [local_epub_candidate(entry, root) for entry in matches]


def local_epub_candidate(entry: DiscoveredSourceFile, root: Path) -> AcquisitionCandidate:
    source_relative_path = relative_path(entry.path, root)
    token = _candidate_token(
        {
            "provider": "local_epub",
            "media_kind": "book",
            "path": source_relative_path,
        }
    )
    return AcquisitionCandidate(
        candidate_id=f"local_epub:{source_relative_path}",
        provider="local_epub",
        media_kind="book",
        title=title_from_filename(entry.path),
        rights="user_provided",
        capabilities=("import_local", "metadata"),
        candidate_token=token,
        local_path=source_relative_path,
        size_bytes=entry.stat.st_size,
        modified_at=datetime.fromtimestamp(entry.stat.st_mtime),
        requires_confirmation=False,
        policy_notes=(
            "Backend-visible EPUB under the configured books root.",
        ),
        metadata={
            "source_kind": "local_epub",
            "source_path": source_relative_path,
        },
    )


def manual_download_epub_candidate(
    entry: DiscoveredSourceFile,
    root: Path,
    absolute_path: str,
) -> AcquisitionCandidate:
    token = _candidate_token(
        {
            "provider": "manual_downloads",
            "media_kind": "book",
            "path": absolute_path,
        }
    )
    return AcquisitionCandidate(
        candidate_id=f"manual_downloads:book:{absolute_path}",
        provider="manual_downloads",
        media_kind="book",
        title=title_from_filename(entry.path),
        rights="user_provided",
        capabilities=("import_local", "metadata"),
        candidate_token=token,
        local_path=absolute_path,
        size_bytes=entry.stat.st_size,
        modified_at=datetime.fromtimestamp(entry.stat.st_mtime),
        requires_confirmation=False,
        policy_notes=(
            "Backend-visible EPUB found in a configured manual download folder.",
        ),
        metadata={
            "source_kind": "manual_download",
            "source_path": absolute_path,
            "source_root": root.as_posix(),
        },
    )


def discover_nas_videos(
    config: Mapping[str, Any],
    query: str,
    limit: int,
) -> list[AcquisitionCandidate]:
    if limit <= 0:
        return []
    root = resolve_video_root(config)
    try:
        videos = list_downloaded_videos(
            root,
            recover_partials=False,
            max_results=limit if not query else None,
        )
    except FileNotFoundError:
        return []

    matches: list[AcquisitionCandidate] = []
    for video in videos:
        source_relative_path = relative_path(video.path, root)
        if query and query not in _search_blob(video.path.name, source_relative_path):
            continue
        append_bounded_newest_candidate(
            matches,
            nas_video_candidate(video),
            limit,
        )
    return matches


def nas_video_candidate(video: Any) -> AcquisitionCandidate:
    subtitles = tuple(
        AcquisitionSubtitleHint(
            path=subtitle.path.as_posix(),
            filename=subtitle.path.name,
            language=subtitle.language,
            format=subtitle.format,
        )
        for subtitle in video.subtitles
    )
    token = _candidate_token(
        {
            "provider": "nas_video",
            "media_kind": "video",
            "path": video.path.as_posix(),
        }
    )
    return AcquisitionCandidate(
        candidate_id=f"nas_video:{video.path.as_posix()}",
        provider="nas_video",
        media_kind="video",
        title=title_from_filename(video.path),
        rights="user_provided",
        capabilities=("import_local", "extract_subtitles", "metadata"),
        candidate_token=token,
        local_path=video.path.as_posix(),
        size_bytes=video.size_bytes,
        modified_at=video.modified_at,
        subtitles=subtitles,
        requires_confirmation=False,
        policy_notes=(
            "Backend-visible NAS video under the configured video root.",
        ),
        metadata={
            "source_kind": getattr(video, "source", "nas_video") or "nas_video",
            "source_path": video.path.as_posix(),
        },
    )


def discover_manual_downloads(
    config: Mapping[str, Any],
    media_kind: str,
    query: str,
    limit: int,
) -> list[AcquisitionCandidate]:
    roots = resolve_manual_download_roots(config)
    if not roots:
        return []
    if media_kind == "book":
        return discover_manual_download_epubs(roots, query, limit)
    if media_kind == "video":
        return discover_manual_download_videos(roots, query, limit)
    return []


def discover_manual_download_epubs(
    roots: Sequence[Path],
    query: str,
    limit: int,
) -> list[AcquisitionCandidate]:
    if limit <= 0:
        return []
    matches: list[tuple[DiscoveredSourceFile, Path, str]] = []
    seen_paths: set[str] = set()
    for root in roots:
        for entry in iter_visible_source_files(root, suffixes={".epub"}, resolve_paths=True):
            if not is_usable_epub_entry(entry):
                continue
            absolute_path = entry.path.as_posix()
            source_relative_path = relative_path(entry.path, root)
            if query and query not in _search_blob(
                entry.path.name,
                source_relative_path,
                absolute_path,
            ):
                continue
            if absolute_path in seen_paths:
                continue
            seen_paths.add(absolute_path)
            append_bounded_newest_manual_entry(
                matches,
                entry,
                root,
                absolute_path,
                limit,
            )
    return [
        manual_download_epub_candidate(entry, root, absolute_path)
        for entry, root, absolute_path in matches
    ]


def discover_manual_download_videos(
    roots: Sequence[Path],
    query: str,
    limit: int,
) -> list[AcquisitionCandidate]:
    if limit <= 0:
        return []
    matches: list[AcquisitionCandidate] = []
    seen_paths: set[str] = set()
    for root in roots:
        try:
            videos = list_downloaded_videos(
                root,
                recover_partials=False,
                max_results=limit if not query else None,
            )
        except FileNotFoundError:
            continue
        for video in videos:
            absolute_path = video.path.as_posix()
            if absolute_path in seen_paths:
                continue
            seen_paths.add(absolute_path)
            source_relative_path = relative_path(video.path, root)
            if query and query not in _search_blob(
                video.path.name,
                source_relative_path,
                absolute_path,
            ):
                continue
            append_bounded_newest_candidate(
                matches,
                manual_download_video_candidate(video, root, absolute_path),
                limit,
            )
    return matches


def manual_download_video_candidate(
    video: Any,
    root: Path,
    absolute_path: str,
) -> AcquisitionCandidate:
    subtitles = tuple(
        AcquisitionSubtitleHint(
            path=subtitle.path.as_posix(),
            filename=subtitle.path.name,
            language=subtitle.language,
            format=subtitle.format,
        )
        for subtitle in video.subtitles
    )
    token = _candidate_token(
        {
            "provider": "manual_downloads",
            "media_kind": "video",
            "path": absolute_path,
        }
    )
    return AcquisitionCandidate(
        candidate_id=f"manual_downloads:video:{absolute_path}",
        provider="manual_downloads",
        media_kind="video",
        title=title_from_filename(video.path),
        rights="user_provided",
        capabilities=("import_local", "extract_subtitles", "metadata"),
        candidate_token=token,
        local_path=absolute_path,
        size_bytes=video.size_bytes,
        modified_at=video.modified_at,
        subtitles=subtitles,
        requires_confirmation=False,
        policy_notes=(
            "Backend-visible video found in a configured manual download folder.",
        ),
        metadata={
            "source_kind": "manual_download",
            "source_path": absolute_path,
            "source_root": root.as_posix(),
        },
    )


def _search_blob(*values: str) -> str:
    return " ".join(values).casefold()


def _candidate_token(payload: Mapping[str, Any]) -> str:
    return encode_acquisition_token(payload)
