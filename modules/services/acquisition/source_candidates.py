"""Helpers for backend-visible acquisition source candidates."""

from __future__ import annotations

import re
from pathlib import Path

from modules.services.source_discovery import (
    DiscoveredSourceFile,
    newest_source_file_sort_key,
)


ManualSourceMatch = tuple[DiscoveredSourceFile, Path, str]


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
    matches.append((entry, root, absolute_path))
    matches.sort(
        key=lambda item: newest_source_file_sort_key(
            item[0],
            secondary_key=lambda source: title_from_filename(source.path),
        )
    )
    if len(matches) > limit:
        del matches[limit:]
