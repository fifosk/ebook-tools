"""Shared filesystem discovery helpers for backend source pickers."""

from __future__ import annotations

import os
import stat as stat_module
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, List, Optional


@dataclass(frozen=True)
class DiscoveredSourceFile:
    """A visible regular file discovered under a picker root."""

    path: Path
    stat: os.stat_result


def safe_stat(path: Path) -> Optional[os.stat_result]:
    """Return ``path.stat()`` while tolerating transient NAS races."""

    try:
        return path.stat()
    except OSError:
        return None


def safe_iterdir(root: Path) -> List[Path]:
    """Return directory children, or an empty list when the root is unavailable."""

    try:
        return list(root.iterdir())
    except OSError:
        return []


def newest_source_file_sort_key(
    entry: DiscoveredSourceFile,
    *,
    secondary_key: Callable[[DiscoveredSourceFile], str] | None = None,
) -> tuple[float, str]:
    """Return a newest-first, stable sort key using the entry's cached stat."""

    label = secondary_key(entry) if secondary_key else entry.path.as_posix()
    return (-entry.stat.st_mtime, label.casefold())


def append_bounded_newest_source_file(
    matches: List[DiscoveredSourceFile],
    entry: DiscoveredSourceFile,
    limit: int,
    *,
    secondary_key: Callable[[DiscoveredSourceFile], str] | None = None,
) -> None:
    """Append ``entry`` while keeping only the newest ``limit`` source files."""

    if limit <= 0:
        return
    entry_key = newest_source_file_sort_key(
        entry,
        secondary_key=secondary_key,
    )
    if len(matches) >= limit:
        last_key = newest_source_file_sort_key(matches[-1], secondary_key=secondary_key)
        if entry_key >= last_key:
            return

    insert_at = _bisect_right_source_files(
        matches,
        entry_key,
        secondary_key=secondary_key,
    )
    matches.insert(insert_at, entry)
    if len(matches) > limit:
        del matches[limit:]


def _bisect_right_source_files(
    matches: List[DiscoveredSourceFile],
    entry_key: tuple[float, str],
    *,
    secondary_key: Callable[[DiscoveredSourceFile], str] | None = None,
) -> int:
    """Return the insertion index without materializing keys for every match."""

    lower = 0
    upper = len(matches)
    while lower < upper:
        middle = (lower + upper) // 2
        middle_key = newest_source_file_sort_key(
            matches[middle],
            secondary_key=secondary_key,
        )
        if entry_key < middle_key:
            upper = middle
        else:
            lower = middle + 1
    return lower


def walk_visible_source_files(
    root: Path,
    *,
    suffixes: Optional[Iterable[str]] = None,
    resolve_paths: bool = False,
    follow_dir_symlinks: bool = True,
) -> List[DiscoveredSourceFile]:
    """Return visible regular files below ``root`` while pruning hidden folders."""

    return list(
        iter_visible_source_files(
            root,
            suffixes=suffixes,
            resolve_paths=resolve_paths,
            follow_dir_symlinks=follow_dir_symlinks,
        )
    )


def iter_visible_source_files(
    root: Path,
    *,
    suffixes: Optional[Iterable[str]] = None,
    resolve_paths: bool = False,
    follow_dir_symlinks: bool = True,
) -> Iterator[DiscoveredSourceFile]:
    """Yield visible regular files below ``root`` while pruning hidden folders."""

    root_stat = safe_stat(root)
    if root_stat is None or not stat_module.S_ISDIR(root_stat.st_mode):
        return

    try:
        root_resolved = root.resolve(strict=True)
    except OSError:
        root_resolved = root

    suffix_filter = _normalized_suffix_filter(suffixes) if suffixes is not None else None
    visited_dirs: set[tuple[int, int]] = set()
    for current_root, dirnames, filenames in os.walk(
        root,
        followlinks=follow_dir_symlinks,
        onerror=lambda _exc: None,
    ):
        current_path = Path(current_root)
        if _has_hidden_relative_part(current_path, root):
            dirnames[:] = []
            continue
        if current_path != root and _has_hidden_symlink_target_part(current_path, root_resolved):
            dirnames[:] = []
            continue
        current_stat = safe_stat(current_path)
        if current_stat is None or not stat_module.S_ISDIR(current_stat.st_mode):
            dirnames[:] = []
            continue

        current_identity = (current_stat.st_dev, current_stat.st_ino)
        if current_identity in visited_dirs:
            dirnames[:] = []
            continue
        visited_dirs.add(current_identity)

        visible_dirs: List[str] = []
        for dirname in sorted(dirnames):
            if dirname.startswith("."):
                continue
            child_path = current_path / dirname
            if _has_hidden_symlink_target_part(child_path, root_resolved):
                continue
            if follow_dir_symlinks:
                child_stat = safe_stat(child_path)
                if child_stat is None or not stat_module.S_ISDIR(child_stat.st_mode):
                    continue
                if (child_stat.st_dev, child_stat.st_ino) in visited_dirs:
                    continue
            visible_dirs.append(dirname)
        dirnames[:] = visible_dirs

        for filename in sorted(filenames):
            if filename.startswith("."):
                continue
            candidate = current_path / filename
            if _has_hidden_relative_part(candidate, root):
                continue
            if _has_hidden_symlink_target_part(candidate, root_resolved):
                continue
            if suffix_filter is not None and candidate.suffix.lower() not in suffix_filter:
                continue
            candidate_stat = safe_stat(candidate)
            if candidate_stat is None or not stat_module.S_ISREG(candidate_stat.st_mode):
                continue
            if resolve_paths:
                try:
                    candidate = candidate.resolve()
                except OSError:
                    continue
            yield DiscoveredSourceFile(path=candidate, stat=candidate_stat)


def _normalized_suffix_filter(suffixes: Iterable[str]) -> set[str]:
    """Normalize suffix filters so callers may pass ``epub`` or ``.epub``."""

    normalized: set[str] = set()
    for suffix in suffixes:
        value = str(suffix).strip().lower()
        if not value:
            continue
        normalized.add(value if value.startswith(".") else f".{value}")
    return normalized


def _has_hidden_relative_part(path: Path, root: Path) -> bool:
    """Return true when ``path`` has hidden components below ``root``."""

    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        relative_parts = path.parts
    return any(part.startswith(".") for part in relative_parts if part not in {"", "."})


def _has_hidden_symlink_target_part(path: Path, root_resolved: Path) -> bool:
    """Return true when a symlink points at a hidden target component."""

    try:
        if not path.is_symlink():
            return False
        resolved_path = path.resolve(strict=True)
    except OSError:
        return True
    return _has_hidden_relative_part(resolved_path, root_resolved)
