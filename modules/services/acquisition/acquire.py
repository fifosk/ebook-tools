"""Reviewed acquisition helpers for discovery candidates."""

from __future__ import annotations

import re
import stat as stat_module
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

import requests

from modules.services.source_discovery import safe_stat
from modules.services.youtube_dubbing import list_downloaded_videos

from .provider_registry import (
    resolve_books_root,
    resolve_manual_download_roots,
    resolve_video_root,
)
from .tokens import decode_acquisition_token, encode_acquisition_token


_ALLOWED_GUTENBERG_HOSTS = {
    "gutenberg.org",
    "www.gutenberg.org",
    "gutenberg.pglaf.org",
}
_ALLOWED_INTERNET_ARCHIVE_HOSTS = {
    "archive.org",
    "www.archive.org",
}
_DEFAULT_DOWNLOAD_LIMIT_BYTES = 100 * 1024 * 1024
_VIDEO_SUFFIXES = {
    ".mp4",
    ".m4v",
    ".mov",
    ".mkv",
    ".webm",
    ".avi",
}


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
    destination = _reserve_destination_path(books_root, target_name)
    _download_to_path(
        epub_url,
        destination,
        provider=provider,
        archive_identifier=archive_identifier,
        session=session,
        max_bytes=_download_limit(config or {}),
    )
    stat = destination.stat()
    local_path = _relative_path(destination, books_root)
    artifact_id = _artifact_token(
        {
            "provider": provider,
            "media_kind": "book",
            "path": local_path,
            "source_kind": provider,
        }
    )
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
            source_kind=_source_kind(provider, payload),
            local_path=local_path,
            input_file=local_path,
            next_actions=("create_book_job", "load_content_index"),
            metadata=_prepare_metadata(provider, "book", payload, local_path),
        )
    local_path = _resolve_video_artifact_path(provider, path_value, config)
    subtitles = _video_subtitle_hints(local_path, provider, config)
    preferred_subtitle = _string_value(subtitles[0].get("path")) if subtitles else None
    return AcquisitionPreparedArtifact(
        provider=provider,
        media_kind="video",
        source_kind=_source_kind(provider, payload),
        local_path=local_path,
        video_path=local_path,
        subtitle_path=preferred_subtitle,
        subtitles=subtitles,
        next_actions=("extract_subtitles", "create_dub_job"),
        metadata=_prepare_metadata(provider, "video", payload, local_path),
    )


def _decode_candidate_token(candidate_token: str) -> Mapping[str, Any]:
    return decode_acquisition_token(candidate_token)


def _artifact_token(payload: Mapping[str, Any]) -> str:
    return encode_acquisition_token(payload)


def _resolve_book_artifact_path(
    provider: str,
    path_value: str | None,
    config: Mapping[str, Any],
) -> str:
    if not path_value:
        raise ValueError("artifact has not been acquired into a local EPUB source")
    if provider in {"local_epub", "gutenberg", "internet_archive"}:
        books_root = resolve_books_root(config=config, context=None)
        return _resolve_epub_under_root(path_value, books_root, allow_relative=True)
    if provider == "manual_downloads":
        return _resolve_epub_under_roots(path_value, resolve_manual_download_roots(config))
    raise ValueError(f"provider {provider} does not support prepared book artifacts")


def _resolve_video_artifact_path(
    provider: str,
    path_value: str | None,
    config: Mapping[str, Any],
) -> str:
    if not path_value:
        raise ValueError("artifact does not include a local video source")
    if provider == "nas_video":
        return _resolve_file_under_roots(
            path_value,
            (resolve_video_root(config),),
            allowed_suffixes=_VIDEO_SUFFIXES,
        ).as_posix()
    if provider == "manual_downloads":
        return _resolve_file_under_roots(
            path_value,
            resolve_manual_download_roots(config),
            allowed_suffixes=_VIDEO_SUFFIXES,
        ).as_posix()
    raise ValueError(f"provider {provider} does not support prepared video artifacts")


def _resolve_epub_under_root(
    path_value: str,
    root: Path,
    *,
    allow_relative: bool,
) -> str:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        resolved = _resolve_file_under_roots(
            path.as_posix(),
            (root,),
            allowed_suffixes={".epub"},
        )
        return resolved.as_posix()
    if not allow_relative:
        raise ValueError("artifact path must be absolute")
    candidate = (root / path).resolve()
    root_resolved = root.resolve()
    _ensure_within_root(candidate, root_resolved)
    _ensure_existing_file(candidate, allowed_suffixes={".epub"})
    return _relative_path(candidate, root_resolved)


def _resolve_epub_under_roots(path_value: str, roots: tuple[Path, ...]) -> str:
    return _resolve_file_under_roots(
        path_value,
        roots,
        allowed_suffixes={".epub"},
    ).as_posix()


def _resolve_file_under_roots(
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
            _ensure_within_root(resolved, root.resolve())
        except ValueError:
            continue
        _ensure_existing_file(resolved, allowed_suffixes=allowed_suffixes)
        return resolved
    raise ValueError("artifact path is outside configured source roots")


def _ensure_within_root(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("artifact path is outside configured source roots") from exc


def _ensure_existing_file(path: Path, *, allowed_suffixes: set[str]) -> None:
    if path.suffix.casefold() not in allowed_suffixes:
        raise ValueError("artifact path has an unsupported file type")
    path_stat = safe_stat(path)
    if path_stat is None or not stat_module.S_ISREG(path_stat.st_mode):
        raise ValueError("artifact path does not exist")


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


def _source_kind(provider: str, payload: Mapping[str, Any]) -> str:
    return _normalized_token_id(payload.get("source_kind")) or provider


def _prepare_metadata(
    provider: str,
    media_kind: str,
    payload: Mapping[str, Any],
    local_path: str,
) -> Mapping[str, Any]:
    metadata: dict[str, Any] = {
        "source_kind": _source_kind(provider, payload),
        "source_path": local_path,
        "source_provider": provider,
        "acquisition_provider": provider,
    }
    candidate_id = _prepared_candidate_id(provider, media_kind, payload)
    if candidate_id:
        metadata["acquisition_candidate_id"] = candidate_id
    for key in (
        "gutenberg_id",
        "identifier",
        "source_url",
        "openlibrary_work_key",
        "openlibrary_book_key",
    ):
        value = payload.get(key)
        if value not in (None, ""):
            metadata[key] = value
    return metadata


def _prepared_candidate_id(
    provider: str,
    media_kind: str,
    payload: Mapping[str, Any],
) -> str | None:
    explicit = _string_value(payload.get("candidate_id"))
    if explicit:
        return explicit
    path = _string_value(payload.get("path"))
    if provider == "local_epub" and path:
        return f"local_epub:{path}"
    if provider == "nas_video" and path:
        return f"nas_video:{path}"
    if provider == "manual_downloads" and path:
        return f"manual_downloads:{media_kind}:{path}"
    gutenberg_id = _int_value(payload.get("gutenberg_id"))
    if provider == "gutenberg" and gutenberg_id is not None:
        return f"gutenberg:{gutenberg_id}"
    identifier = _string_value(payload.get("identifier"))
    if provider == "internet_archive" and identifier:
        return f"internet_archive:{identifier}"
    video_id = _string_value(payload.get("video_id"))
    if provider in {"youtube_search", "youtube_url"} and video_id:
        return f"{provider}:{video_id}"
    guid = _string_value(payload.get("guid"))
    if provider == "newznab_torznab" and guid:
        return f"newznab_torznab:{guid}"
    return None


def _validate_gutenberg_epub_url(url: str) -> None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"http", "https"} or hostname not in _ALLOWED_GUTENBERG_HOSTS:
        raise ValueError("candidate EPUB URL is not an allowed Gutenberg URL")
    if ".epub" not in unquote(parsed.path).casefold():
        raise ValueError("candidate EPUB URL does not point to an EPUB file")


def _validate_internet_archive_epub_url(
    url: str,
    archive_identifier: str | None,
) -> None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("candidate EPUB URL is not an allowed Internet Archive URL")
    if hostname not in _ALLOWED_INTERNET_ARCHIVE_HOSTS and not hostname.endswith(".archive.org"):
        raise ValueError("candidate EPUB URL is not an allowed Internet Archive URL")
    path = unquote(parsed.path)
    if ".epub" not in path.casefold():
        raise ValueError("candidate EPUB URL does not point to an EPUB file")
    if archive_identifier and hostname in _ALLOWED_INTERNET_ARCHIVE_HOSTS:
        expected_prefix = f"/download/{archive_identifier}/"
        if not path.startswith(expected_prefix):
            raise ValueError("candidate EPUB URL is not an allowed Internet Archive item URL")


def _validate_epub_url_for_provider(
    *,
    provider: str | None,
    url: str,
    archive_identifier: str | None = None,
) -> None:
    if provider == "gutenberg":
        _validate_gutenberg_epub_url(url)
        return
    if provider == "internet_archive":
        _validate_internet_archive_epub_url(url, archive_identifier)
        return
    raise ValueError(f"provider {provider or '<missing>'} does not support acquire")


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


def _download_limit(config: Mapping[str, Any]) -> int:
    value = config.get("acquisition_download_max_bytes")
    if value is None:
        return _DEFAULT_DOWNLOAD_LIMIT_BYTES
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return _DEFAULT_DOWNLOAD_LIMIT_BYTES


def _normalise_epub_name(filename: str | None) -> str:
    raw_name = Path(filename or "acquired.epub").name or "acquired.epub"
    stem = Path(raw_name).stem
    safe_stem = re.sub(r"[^0-9A-Za-z._ -]", "_", stem).strip(" ._-") or "acquired"
    if raw_name.casefold().endswith(".epub"):
        return f"{safe_stem}.epub"
    return f"{safe_stem}.epub"


def _filename_from_epub_url(
    url: str,
    provider: str | None,
    gutenberg_id: int | None,
    archive_identifier: str | None,
) -> str:
    parsed = urlparse(url)
    name = Path(unquote(parsed.path)).name
    if name and ".epub" in name.casefold():
        stem = name[: name.casefold().find(".epub")]
        return f"{stem}.epub"
    if provider == "gutenberg" and gutenberg_id is not None:
        return f"gutenberg-{gutenberg_id}.epub"
    if provider == "internet_archive" and archive_identifier:
        return f"{archive_identifier}.epub"
    return "acquired.epub"


def _reserve_destination_path(directory: Path, filename: str) -> Path:
    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".epub"
    candidate = directory / f"{stem}{suffix}"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _int_value(value: Any) -> int | None:
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


def _string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _normalized_token_id(value: Any) -> str | None:
    raw = _string_value(value)
    return raw.casefold() if raw else None
