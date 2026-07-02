"""Source-root resolution helpers for acquisition providers."""

from __future__ import annotations

import os
import stat as stat_module
from pathlib import Path
from typing import Any, Mapping

from modules import config_manager as cfg
from modules.services.source_discovery import safe_stat
from modules.services.youtube_dubbing import DEFAULT_YOUTUBE_VIDEO_ROOT


_EXPLICIT_MANUAL_DOWNLOAD_ROOT_KEYS = (
    "acquisition_manual_download_roots",
    "manual_download_roots",
    "acquisition_manual_download_root",
    "manual_download_root",
    "download_station_completed_root",
    "downloads_root",
)

_VIDEO_DOWNLOAD_ROOT_KEYS = (
    "youtube_video_root",
    "youtube_library_root",
    "video_download_root",
)

_MANUAL_DOWNLOAD_ROOT_ENV_KEYS = (
    "EBOOK_ACQUISITION_MANUAL_ROOTS",
    "EBOOK_MANUAL_DOWNLOAD_ROOTS",
    "EBOOK_ACQUISITION_MANUAL_ROOT",
    "EBOOK_MANUAL_DOWNLOAD_ROOT",
    "DOWNLOAD_STATION_COMPLETED_ROOT",
)


def resolve_books_root(
    *,
    config: Mapping[str, Any],
    context: cfg.RuntimeContext | None,
) -> Path:
    """Resolve the backend-visible EPUB source root."""

    if context is not None:
        return context.books_dir.expanduser()
    raw_value = config.get("ebooks_dir")
    if isinstance(raw_value, str) and raw_value.strip():
        return resolve_display_path(raw_value.strip())
    return resolve_display_path(cfg.DEFAULT_BOOKS_RELATIVE)


def resolve_video_root(config: Mapping[str, Any]) -> Path:
    """Resolve the backend-visible NAS video source root."""

    for key in _VIDEO_DOWNLOAD_ROOT_KEYS:
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return resolve_display_path(value.strip())
    return DEFAULT_YOUTUBE_VIDEO_ROOT


def resolve_manual_download_roots(config: Mapping[str, Any]) -> tuple[Path, ...]:
    """Resolve user-authorized manual download folders visible to the backend."""

    return _resolve_manual_download_roots(
        config,
        include_video_roots=True,
        readable_only=False,
    )


def readable_explicit_manual_download_roots(config: Mapping[str, Any]) -> tuple[Path, ...]:
    """Return readable manual roots explicitly configured as download inboxes."""

    return _resolve_manual_download_roots(
        config,
        include_video_roots=False,
        readable_only=True,
    )


def manual_download_source_label(roots: tuple[Path, ...]) -> str:
    return "Manual download folder" if len(roots) == 1 else "Manual download folders"


def resolve_display_path(path_value: object) -> Path:
    path = Path(str(path_value)).expanduser()
    if path.is_absolute():
        return path
    return (cfg.SCRIPT_DIR / path).resolve()


def is_readable_dir(path: Path) -> bool:
    path_stat = safe_stat(path)
    return path_stat is not None and stat_module.S_ISDIR(path_stat.st_mode)


def _resolve_manual_download_roots(
    config: Mapping[str, Any],
    *,
    include_video_roots: bool,
    readable_only: bool,
) -> tuple[Path, ...]:
    roots: list[Path] = []
    seen: set[str] = set()
    for value in _manual_download_root_values(
        config,
        include_video_roots=include_video_roots,
    ):
        for part in split_path_values(value):
            root = resolve_display_path(part)
            key = root.as_posix()
            if key in seen:
                continue
            if readable_only and not is_readable_dir(root):
                continue
            seen.add(key)
            roots.append(root)
    return tuple(roots)


def _manual_download_root_values(
    config: Mapping[str, Any],
    *,
    include_video_roots: bool,
) -> tuple[object, ...]:
    raw_values: list[object] = []
    config_keys = _EXPLICIT_MANUAL_DOWNLOAD_ROOT_KEYS
    if include_video_roots:
        config_keys += _VIDEO_DOWNLOAD_ROOT_KEYS
    for key in config_keys:
        value = config.get(key)
        if value not in (None, ""):
            raw_values.append(value)
    for key in _MANUAL_DOWNLOAD_ROOT_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if value:
            raw_values.append(value)
    return tuple(raw_values)


def split_path_values(value: object) -> tuple[str, ...]:
    if isinstance(value, (list, tuple, set)):
        parts = [str(item).strip() for item in value]
    else:
        text = str(value)
        normalized = text.replace("\n", os.pathsep).replace(",", os.pathsep)
        parts = [part.strip() for part in normalized.split(os.pathsep)]
    return tuple(part for part in parts if part)
