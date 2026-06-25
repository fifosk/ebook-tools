"""Reviewed acquisition helpers for discovery candidates."""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

import requests

from .provider_registry import resolve_books_root


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
    provider = _string_value(payload.get("provider"))
    media_kind = _string_value(payload.get("media_kind"))
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
    )


def _decode_candidate_token(candidate_token: str) -> Mapping[str, Any]:
    token = (candidate_token or "").strip()
    if not token:
        raise ValueError("candidate_token is required")
    padded = token + "=" * (-len(token) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
    except (UnicodeEncodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("candidate_token is invalid") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("candidate_token is invalid")
    return payload


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
