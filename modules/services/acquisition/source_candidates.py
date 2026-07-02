"""Helpers for backend-visible acquisition source candidates."""

from __future__ import annotations

import re
from bisect import bisect_right
from datetime import datetime
from pathlib import Path
from typing import Protocol, TypeVar

from modules.services.source_discovery import (
    DiscoveredSourceFile,
    newest_source_file_sort_key,
)


ManualSourceMatch = tuple[DiscoveredSourceFile, Path, str]
CandidateT = TypeVar("CandidateT", bound="NewestCandidate")


class NewestCandidate(Protocol):
    """Candidate fields required for newest-first bounded discovery lists."""

    title: str
    modified_at: datetime | None


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def title_from_filename(path: Path) -> str:
    title = re.sub(r"[_\s]+", " ", path.stem).strip()
    return title or path.name


def is_usable_epub_entry(entry: DiscoveredSourceFile) -> bool:
    return entry.stat.st_size > 0


def append_bounded_newest_manual_entry(
    matches: list[ManualSourceMatch],
    entry: DiscoveredSourceFile,
    root: Path,
    absolute_path: str,
    limit: int,
) -> None:
    if limit <= 0:
        return
    match = (entry, root, absolute_path)
    match_key = _manual_source_match_sort_key(match)
    if len(matches) >= limit and match_key >= _manual_source_match_sort_key(matches[-1]):
        return
    insert_at = bisect_right(
        [_manual_source_match_sort_key(item) for item in matches],
        match_key,
    )
    matches.insert(insert_at, match)
    if len(matches) > limit:
        del matches[limit:]


def append_bounded_newest_candidate(
    matches: list[CandidateT],
    candidate: CandidateT,
    limit: int,
) -> None:
    """Append and keep the newest visible source candidates up to ``limit``."""

    if limit <= 0:
        return
    candidate_key = _newest_candidate_sort_key(candidate)
    if len(matches) >= limit and candidate_key >= _newest_candidate_sort_key(matches[-1]):
        return
    insert_at = bisect_right(
        [_newest_candidate_sort_key(item) for item in matches],
        candidate_key,
    )
    matches.insert(insert_at, candidate)
    if len(matches) > limit:
        del matches[limit:]


def _manual_source_match_sort_key(
    item: ManualSourceMatch,
) -> tuple[float, str]:
    return newest_source_file_sort_key(
        item[0],
        secondary_key=lambda source: title_from_filename(source.path),
    )


def _newest_candidate_sort_key(candidate: NewestCandidate) -> tuple[float, str]:
    return (
        -candidate.modified_at.timestamp() if candidate.modified_at else 0,
        candidate.title.casefold(),
    )
