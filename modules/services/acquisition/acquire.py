"""Reviewed acquisition helpers for discovery candidates."""

from __future__ import annotations

import stat as stat_module
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from modules.services.source_discovery import safe_stat
from modules.services.youtube_dubbing import list_downloaded_videos

from .artifact_epubs import (
    download_limit as _download_limit,
    filename_from_epub_url as _filename_from_epub_url,
    normalise_epub_name as _normalise_epub_name,
    reserve_epub_destination_path as _reserve_epub_destination_path,
    validate_epub_url_for_provider as _validate_epub_url_for_provider,
)
from .artifact_metadata import (
    normalized_token_id as _normalized_token_id,
    prepare_artifact_metadata,
    source_kind,
)
from .artifact_paths import (
    relative_path as _relative_path,
    resolve_book_artifact_path as _resolve_book_artifact_path,
    resolve_video_artifact_path as _resolve_video_artifact_path,
)
from .discovery_values import int_value as _int_value, string_value as _string_value
from .provider_roots import (
    resolve_books_root,
    resolve_manual_download_roots,
    resolve_video_root,
)
from .tokens import decode_acquisition_token, encode_acquisition_token


@dataclass(frozen=True)
class AcquisitionArtifact:
    """Completed artifact created from a reviewed acquisition candidate."""

    provider: str
    media_kind: str
    status: str
    artifact_path: str
    local_path: str
    filename: str
    size_bytes: int
    modified_at: datetime
    next_actions: tuple[str, ...]
    metadata: Mapping[str, Any]
    artifact_id: str = ""


@dataclass(frozen=True)
class AcquisitionPreparedArtifact:
    """Existing Create-flow source fields resolved from a discovery artifact."""

    provider: str
    media_kind: str
    source_kind: str
    local_path: str
    input_file: str | None = None
    video_path: str | None = None
    subtitle_path: str | None = None
    subtitles: tuple[Mapping[str, Any], ...] = ()
    next_actions: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


def acquire_acquisition_candidate(
    *,
    candidate_token: str,
    confirmed: bool,
    filename: str | None = None,
    config: Mapping[str, Any] | None = None,
    session: requests.Session | None = None,
) -> AcquisitionArtifact:
    """Acquire a reviewed candidate into a backend-visible source root."""

    if not confirmed:
        raise ValueError("confirmation is required before acquisition")

    payload = _decode_candidate_token(candidate_token)
    provider = _normalized_token_id(payload.get("provider"))
    media_kind = _normalized_token_id(payload.get("media_kind"))
    if provider not in {"gutenberg", "internet_archive"} or media_kind != "book":
        raise ValueError(f"provider {provider or '<missing>'} does not support acquire")

    epub_url = _string_value(payload.get("epub_url"))
    gutenberg_id = _int_value(payload.get("gutenberg_id"))
    archive_identifier = _string_value(payload.get("identifier"))
    if not epub_url:
        raise ValueError("candidate token does not include an EPUB URL")
    _validate_epub_url_for_provider(
        provider=provider,
        url=epub_url,
        archive_identifier=archive_identifier,
    )

    books_root = resolve_books_root(config=config or {}, context=None)
    books_root.mkdir(parents=True, exist_ok=True)
    target_name = _normalise_epub_name(
        filename or _filename_from_epub_url(epub_url, provider, gutenberg_id, archive_identifier)
    )
    destination = _reserve_epub_destination_path(books_root, target_name)
    _download_to_path(
        epub_url,
        destination,
        provider=provider,
        archive_identifier=archive_identifier,
        session=session,
        max_bytes=_download_limit(config or {}),
    )
    stat = safe_stat(destination)
    if stat is None or not stat_module.S_ISREG(stat.st_mode):
        raise ValueError("downloaded EPUB could not be verified")
    local_path = _relative_path(destination, books_root)
    artifact_token_payload: dict[str, Any] = {
        "provider": provider,
        "media_kind": "book",
        "path": local_path,
        "source_kind": provider,
        "source_url": epub_url,
    }
    if gutenberg_id is not None:
        artifact_token_payload["gutenberg_id"] = gutenberg_id
    if archive_identifier:
        artifact_token_payload["identifier"] = archive_identifier
    artifact_id = _artifact_token(artifact_token_payload)
    return AcquisitionArtifact(
        provider=provider,
        media_kind="book",
        status="completed",
        artifact_path=local_path,
        local_path=local_path,
        filename=destination.name,
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime),
        next_actions=("create_book_job", "load_content_index"),
        metadata={
            "source_kind": provider,
            "gutenberg_id": gutenberg_id,
            "identifier": archive_identifier,
            "source_url": epub_url,
        },
        artifact_id=artifact_id,
    )


def prepare_acquisition_artifact(
    *,
    artifact_id: str,
    config: Mapping[str, Any] | None = None,
) -> AcquisitionPreparedArtifact:
    """Resolve a reviewed artifact token into fields existing Create forms use."""

    payload = _decode_candidate_token(artifact_id)
    provider = _normalized_token_id(payload.get("provider"))
    media_kind = _normalized_token_id(payload.get("media_kind"))
    if not provider or media_kind not in {"book", "video"}:
        raise ValueError("artifact_id is invalid")

    config = config or {}
    path_value = _string_value(payload.get("path"))
    if media_kind == "book":
        local_path = _resolve_book_artifact_path(provider, path_value, config)
        return AcquisitionPreparedArtifact(
            provider=provider,
            media_kind="book",
            source_kind=source_kind(provider, payload),
            local_path=local_path,
            input_file=local_path,
            next_actions=("create_book_job", "load_content_index"),
            metadata=prepare_artifact_metadata(provider, "book", payload, local_path),
        )
    local_path = _resolve_video_artifact_path(provider, path_value, config)
    subtitles = _video_subtitle_hints(local_path, provider, config)
    preferred_subtitle = _string_value(subtitles[0].get("path")) if subtitles else None
    return AcquisitionPreparedArtifact(
        provider=provider,
        media_kind="video",
        source_kind=source_kind(provider, payload),
        local_path=local_path,
        video_path=local_path,
        subtitle_path=preferred_subtitle,
        subtitles=subtitles,
        next_actions=("extract_subtitles", "create_dub_job"),
        metadata=prepare_artifact_metadata(provider, "video", payload, local_path),
    )


def _decode_candidate_token(candidate_token: str) -> Mapping[str, Any]:
    return decode_acquisition_token(candidate_token)


def _artifact_token(payload: Mapping[str, Any]) -> str:
    return encode_acquisition_token(payload)


def _video_subtitle_hints(
    local_path: str,
    provider: str,
    config: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    roots = (
        (resolve_video_root(config),)
        if provider == "nas_video"
        else resolve_manual_download_roots(config)
    )
    target = Path(local_path).expanduser().resolve()
    for root in roots:
        try:
            videos = list_downloaded_videos(root)
        except FileNotFoundError:
            continue
        for video in videos:
            if video.path.resolve() != target:
                continue
            return tuple(
                {
                    "path": subtitle.path.as_posix(),
                    "filename": subtitle.path.name,
                    "language": subtitle.language,
                    "format": subtitle.format,
                }
                for subtitle in video.subtitles
            )
    return ()


def _download_to_path(
    url: str,
    destination: Path,
    *,
    provider: str | None,
    archive_identifier: str | None,
    session: requests.Session | None,
    max_bytes: int,
) -> None:
    client = session or requests.Session()
    tmp_path = destination.with_name(f".{destination.name}.part")
    bytes_written = 0
    response = None
    try:
        current_url = url
        for _ in range(4):
            response = client.get(
                current_url,
                stream=True,
                timeout=30,
                allow_redirects=False,
            )
            if not 300 <= getattr(response, "status_code", 200) < 400:
                break
            location = _string_value(getattr(response, "headers", {}).get("Location"))
            response.close()
            response = None
            if not location:
                raise ValueError("EPUB redirect did not include a Location")
            current_url = urljoin(current_url, location)
            _validate_epub_url_for_provider(
                provider=provider,
                url=current_url,
                archive_identifier=archive_identifier,
            )
        else:
            raise ValueError("EPUB redirected too many times")

        response.raise_for_status()
        with tmp_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise ValueError("downloaded EPUB exceeds configured size limit")
                handle.write(chunk)
        tmp_path.replace(destination)
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise
    finally:
        if response is not None:
            response.close()
