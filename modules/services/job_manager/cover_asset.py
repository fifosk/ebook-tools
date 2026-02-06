"""Utilities for mirroring and managing cover assets for pipeline jobs."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Mapping, Optional

from ... import config_manager as cfg
from ... import logging_manager
from ..file_locator import FileLocator

_LOGGER = logging_manager.get_logger().getChild("job_manager.cover_asset")


def mirror_cover_asset(
    job_id: str,
    metadata_root: Path,
    media_metadata: Mapping[str, Any],
    file_locator: FileLocator,
) -> Optional[str]:
    """Mirror a cover asset into the metadata directory, returning the relative path."""

    raw_value = media_metadata.get("book_cover_file")
    if not isinstance(raw_value, str) or not raw_value.strip():
        cleanup_cover_assets(metadata_root)
        return None

    source = _resolve_cover_source(job_id, metadata_root, raw_value, file_locator)
    if source is None:
        cleanup_cover_assets(metadata_root)
        return None

    try:
        return _copy_cover_asset(metadata_root, source)
    except Exception:  # pragma: no cover - defensive logging
        _LOGGER.debug("Unable to mirror cover asset for job %s", job_id, exc_info=True)
        return None


def _resolve_cover_source(
    job_id: str,
    metadata_root: Path,
    raw_value: str,
    file_locator: FileLocator,
) -> Optional[Path]:
    candidate = Path(raw_value.strip())
    search_paths: list[Path] = []

    if candidate.is_absolute():
        search_paths.append(candidate)
    else:
        normalised = raw_value.strip().lstrip("/\\")
        relative_candidate = Path(normalised)
        relative_variants = [relative_candidate]

        parts = [part.lower() for part in relative_candidate.parts]
        if parts and parts[0] in {"storage", "metadata"} and len(parts) > 1:
            relative_variants.append(Path(*relative_candidate.parts[1:]))
        if parts and parts[0] == "covers" and len(parts) > 1:
            relative_variants.append(Path(*relative_candidate.parts[1:]))

        for relative in relative_variants:
            search_paths.append(metadata_root / relative)
            try:
                search_paths.append(file_locator.resolve_path(job_id, relative))
            except ValueError:
                pass
            search_paths.append(file_locator.storage_root / relative)

            covers_root = cfg.resolve_directory(None, cfg.DEFAULT_COVERS_RELATIVE)
            search_paths.append(covers_root / relative)

            resolved_script = cfg.resolve_file_path(relative)
            if resolved_script is not None:
                search_paths.append(resolved_script)

    seen: set[Path] = set()
    for path in search_paths:
        try:
            resolved = path.resolve()
        except FileNotFoundError:
            continue
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved
    return None


def _copy_cover_asset(metadata_root: Path, source: Path) -> str:
    metadata_root.mkdir(parents=True, exist_ok=True)
    try:
        resolved_source = source.resolve()
    except OSError:
        resolved_source = source

    suffix = resolved_source.suffix.lower() or ".jpg"
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    destination_name = f"cover{suffix}"
    destination_path = metadata_root / destination_name
    destination_abs = destination_path.parent.resolve() / destination_path.name

    if destination_abs != resolved_source:
        should_copy = True
        if destination_path.exists():
            try:
                src_stat = resolved_source.stat()
                dest_stat = destination_path.stat()
                if (
                    src_stat.st_size == dest_stat.st_size
                    and int(src_stat.st_mtime) == int(dest_stat.st_mtime)
                ):
                    should_copy = False
            except OSError:
                pass
        if should_copy:
            shutil.copy2(resolved_source, destination_path)

    for existing in metadata_root.glob("cover.*"):
        if existing.name == destination_name:
            continue
        try:
            existing.unlink()
        except FileNotFoundError:
            continue
        except OSError:
            _LOGGER.debug("Unable to remove stale cover asset %s", existing, exc_info=True)

    relative_path = Path("metadata") / destination_name
    return relative_path.as_posix()


def cleanup_cover_assets(metadata_root: Path) -> None:
    """Remove all cover assets from the metadata directory."""

    for existing in metadata_root.glob("cover.*"):
        try:
            existing.unlink()
        except FileNotFoundError:
            continue
        except OSError:
            _LOGGER.debug("Unable to remove cover asset %s", existing, exc_info=True)


# Need to import Any for type hints
from typing import Any


__all__ = [
    "mirror_cover_asset",
    "cleanup_cover_assets",
]
