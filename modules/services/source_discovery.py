"""Shared filesystem discovery helpers for backend source pickers."""

from __future__ import annotations

import os
import stat as stat_module
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional


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
            if follow_dir_symlinks:
                child_stat = safe_stat(current_path / dirname)
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
