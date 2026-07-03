"""Token-safe Download Station task status/value helpers."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .provider_roots import resolve_manual_download_roots


def task_progress(task: Mapping[str, Any]) -> float | None:
    size = int_value(task.get("size"))
    downloaded = int_value(task.get("size_downloaded"))
    additional = task.get("additional")
    if isinstance(additional, Mapping):
        transfer = additional.get("transfer")
        if isinstance(transfer, Mapping):
            downloaded = downloaded or int_value(transfer.get("size_downloaded"))
        detail = additional.get("detail")
        if isinstance(detail, Mapping):
            size = size or int_value(detail.get("size"))
    if size and downloaded is not None:
        return max(0.0, min(1.0, downloaded / size))
    return None


def normalize_task_status(raw_status: str) -> str:
    normalized = raw_status.casefold()
    if normalized in {"finished", "finish", "completed", "complete", "seeding"}:
        return "completed"
    if normalized in {"downloading", "waiting", "extracting", "hash_checking"}:
        return "running"
    if normalized in {"paused", "error", "broken", "failed"}:
        return "failed" if normalized != "paused" else "paused"
    return "unknown"


def completed_files(
    task: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[str, ...]:
    additional = task.get("additional")
    if not isinstance(additional, Mapping):
        return ()
    files = additional.get("file")
    if not isinstance(files, list):
        return ()
    roots = resolve_manual_download_roots(config)
    paths: list[str] = []
    seen_paths: set[str] = set()
    for item in files:
        if not isinstance(item, Mapping):
            continue
        filename = string_value(item.get("filename")) or string_value(item.get("name"))
        if not filename:
            continue
        safe_path = safe_completed_file_path(filename, roots)
        if safe_path and safe_path not in seen_paths:
            seen_paths.add(safe_path)
            paths.append(safe_path)
    return tuple(paths)


def safe_completed_file_path(
    raw_path: str,
    roots: tuple[Path, ...],
) -> str | None:
    if not roots:
        return None
    if raw_path.startswith("magnet:?"):
        return None
    parsed = urlparse(raw_path)
    if parsed.scheme or parsed.netloc:
        return None
    raw = Path(raw_path).expanduser()
    candidates = [raw] if raw.is_absolute() else [root / raw for root in roots]
    for candidate in candidates:
        resolved_candidate = candidate.resolve()
        for root in roots:
            resolved_root = root.expanduser().resolve()
            try:
                resolved_candidate.relative_to(resolved_root)
            except ValueError:
                continue
            return resolved_candidate.as_posix()
    return None


def download_station_metadata(
    *,
    completed_files: tuple[str, ...] = (),
) -> dict[str, Any]:
    metadata: dict[str, Any] = {"source_kind": "download_station"}
    if completed_files:
        files = list(completed_files)
        metadata["completed_files"] = files
        metadata["files"] = list(files)
        if len(files) == 1:
            metadata["completed_file"] = files[0]
    return metadata


def task_message(task: Mapping[str, Any], raw_status: str) -> str:
    title = string_value(task.get("title"))
    if title:
        return f"Download Station task {title} is {raw_status}."
    return f"Download Station task is {raw_status}."


def int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
