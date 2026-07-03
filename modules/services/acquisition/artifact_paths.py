"""Source-root path resolution for reviewed acquisition artifacts."""

from __future__ import annotations

import stat as stat_module
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from modules.services.source_discovery import safe_stat

from .provider_roots import (
    resolve_books_root,
    resolve_manual_download_roots,
    resolve_video_root,
)


VIDEO_SUFFIXES = {
    ".mp4",
    ".m4v",
    ".mov",
    ".mkv",
    ".webm",
    ".avi",
}


def resolve_book_artifact_path(
    provider: str,
    path_value: str | None,
    config: Mapping[str, Any],
) -> str:
    if not path_value:
        raise ValueError("artifact has not been acquired into a local EPUB source")
    if provider in {"local_epub", "gutenberg", "internet_archive"}:
        books_root = resolve_books_root(config=config, context=None)
        return resolve_epub_under_root(path_value, books_root, allow_relative=True)
    if provider == "manual_downloads":
        return resolve_epub_under_roots(path_value, resolve_manual_download_roots(config))
    raise ValueError(f"provider {provider} does not support prepared book artifacts")


def resolve_video_artifact_path(
    provider: str,
    path_value: str | None,
    config: Mapping[str, Any],
) -> str:
    if not path_value:
        raise ValueError("artifact does not include a local video source")
    if provider == "nas_video":
        return resolve_file_under_roots(
            path_value,
            (resolve_video_root(config),),
            allowed_suffixes=VIDEO_SUFFIXES,
        ).as_posix()
    if provider == "manual_downloads":
        return resolve_file_under_roots(
            path_value,
            resolve_manual_download_roots(config),
            allowed_suffixes=VIDEO_SUFFIXES,
        ).as_posix()
    raise ValueError(f"provider {provider} does not support prepared video artifacts")


def resolve_epub_under_root(
    path_value: str,
    root: Path,
    *,
    allow_relative: bool,
) -> str:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        resolved = resolve_file_under_roots(
            path.as_posix(),
            (root,),
            allowed_suffixes={".epub"},
        )
        return resolved.as_posix()
    if not allow_relative:
        raise ValueError("artifact path must be absolute")
    candidate = (root / path).resolve()
    root_resolved = root.resolve()
    ensure_within_root(candidate, root_resolved)
    ensure_existing_file(candidate, allowed_suffixes={".epub"})
    return relative_path(candidate, root_resolved)


def resolve_epub_under_roots(path_value: str, roots: tuple[Path, ...]) -> str:
    return resolve_file_under_roots(
        path_value,
        roots,
        allowed_suffixes={".epub"},
    ).as_posix()


def resolve_file_under_roots(
    path_value: str,
    roots: tuple[Path, ...],
    *,
    allowed_suffixes: set[str],
) -> Path:
    if not roots:
        raise ValueError("no configured source root can prepare this artifact")
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        raise ValueError("artifact path must be absolute")
    resolved = path.resolve()
    for root in roots:
        try:
            ensure_within_root(resolved, root.resolve())
        except ValueError:
            continue
        ensure_existing_file(resolved, allowed_suffixes=allowed_suffixes)
        return resolved
    raise ValueError("artifact path is outside configured source roots")


def ensure_within_root(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("artifact path is outside configured source roots") from exc


def ensure_existing_file(path: Path, *, allowed_suffixes: set[str]) -> None:
    if path.suffix.casefold() not in allowed_suffixes:
        raise ValueError("artifact path has an unsupported file type")
    path_stat = safe_stat(path)
    if path_stat is None or not stat_module.S_ISREG(path_stat.st_mode):
        raise ValueError("artifact path does not exist")


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
