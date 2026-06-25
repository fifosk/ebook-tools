"""Shared filesystem discovery helpers for backend source pickers."""

from __future__ import annotations

import os
import stat as stat_module
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


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
) -> List[DiscoveredSourceFile]:
    """Return visible regular files below ``root`` while pruning hidden folders."""

    if not root.exists():
        return []

    suffix_filter = {suffix.lower() for suffix in suffixes} if suffixes is not None else None
    discovered: List[DiscoveredSourceFile] = []
    for current_root, dirnames, filenames in os.walk(root, onerror=lambda _exc: None):
        dirnames[:] = sorted(name for name in dirnames if not name.startswith("."))
        current_path = Path(current_root)
        for filename in sorted(filenames):
            if filename.startswith("."):
                continue
            candidate = current_path / filename
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
            discovered.append(DiscoveredSourceFile(path=candidate, stat=candidate_stat))
    return discovered
