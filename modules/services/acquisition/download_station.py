"""Synology Download Station handoff for reviewed acquisition jobs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests

from .download_station_client import (
    DownloadStationClient as _DownloadStationClient,
    DownloadStationConfig,
    DownloadStationError,
    resolve_download_station_config,
    validate_source_uri as _validate_source_uri,
)
from .download_station_values import (
    completed_files as _completed_files,
    download_station_metadata as _download_station_metadata,
    normalize_task_status as _normalize_task_status,
    string_value as _string_value,
    task_message as _task_message,
    task_progress as _task_progress,
)
from .references import resolve_acquisition_reference
from .tokens import decode_acquisition_token


@dataclass(frozen=True)
class AcquisitionJobStatus:
    """Token-safe downloader job status returned to Web and Apple clients."""

    provider: str
    task_id: str
    status: str
    progress: float | None = None
    message: str | None = None
    external_task_id: str | None = None
    raw_status: str | None = None
    started_at: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_files: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


def enqueue_download_station_task(
    *,
    source_uri: str,
    confirmed: bool,
    destination: str | None = None,
    config: Mapping[str, Any] | None = None,
    session: requests.Session | None = None,
) -> AcquisitionJobStatus:
    """Create a reviewed Download Station task from a URI or magnet link."""

    if not confirmed:
        raise ValueError("confirmation is required before downloader handoff")
    normalized_uri = _validate_source_uri(source_uri)
    settings = resolve_download_station_config(config or {})
    client = _DownloadStationClient(settings, session=session)
    task_id = client.create_task(
        source_uri=normalized_uri,
        destination=destination or settings.destination,
    )
    return AcquisitionJobStatus(
        provider="download_station",
        task_id=task_id or "download_station:submitted",
        status="submitted",
        external_task_id=task_id,
        message=(
            "Download Station accepted the reviewed task."
            if task_id
            else "Download Station accepted the reviewed task; scan manual downloads after it completes."
        ),
        next_actions=("poll_download", "discover_manual_downloads", "import_local"),
        metadata=_download_station_metadata(),
    )


def resolve_download_station_candidate_source_uri(
    *,
    candidate_token: str,
    config: Mapping[str, Any] | None = None,
) -> str:
    """Resolve a reviewed discovery candidate token into a Download Station URI."""

    payload = decode_acquisition_token(candidate_token)
    provider = _string_value(payload.get("provider"))
    media_kind = _string_value(payload.get("media_kind"))
    source_ref = _string_value(payload.get("source_ref"))
    if provider != "newznab_torznab" or media_kind != "video" or not source_ref:
        raise ValueError("candidate_token does not reference a Download Station source")
    reference = resolve_acquisition_reference(
        source_ref,
        provider=provider,
        media_kind=media_kind,
        config=config or {},
    )
    return _validate_source_uri(_string_value(reference.get("source_uri")))


def poll_download_station_task(
    *,
    task_id: str,
    config: Mapping[str, Any] | None = None,
    session: requests.Session | None = None,
) -> AcquisitionJobStatus:
    """Poll a Download Station task by its provider task id."""

    normalized_task_id = (task_id or "").strip()
    if not normalized_task_id:
        raise ValueError("task_id is required")
    if normalized_task_id == "download_station:submitted":
        return AcquisitionJobStatus(
            provider="download_station",
            task_id=normalized_task_id,
            status="submitted",
            message=(
                "Download Station did not return a provider task id; use manual downloads discovery after completion."
            ),
            next_actions=("discover_manual_downloads", "import_local"),
            metadata=_download_station_metadata(),
        )
    settings = resolve_download_station_config(config or {})
    client = _DownloadStationClient(settings, session=session)
    task = client.get_task_info(normalized_task_id)
    raw_status = _string_value(task.get("status")) or "unknown"
    progress = _task_progress(task)
    status = _normalize_task_status(raw_status)
    completed_files = _completed_files(task, config or {}) if status == "completed" else ()
    next_actions = (
        ("discover_manual_downloads", "import_local")
        if status == "completed"
        else ("poll_download",)
    )
    return AcquisitionJobStatus(
        provider="download_station",
        task_id=normalized_task_id,
        status=status,
        progress=progress,
        message=_task_message(task, raw_status),
        external_task_id=normalized_task_id,
        raw_status=raw_status,
        completed_files=completed_files,
        next_actions=next_actions,
        metadata=_download_station_metadata(completed_files=completed_files),
    )
