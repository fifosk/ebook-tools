"""EPUB acquisition validation and filename helpers."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from modules.services.source_discovery import safe_stat


ALLOWED_GUTENBERG_HOSTS = {
    "gutenberg.org",
    "www.gutenberg.org",
    "gutenberg.pglaf.org",
}
ALLOWED_INTERNET_ARCHIVE_HOSTS = {
    "archive.org",
    "www.archive.org",
}
DEFAULT_DOWNLOAD_LIMIT_BYTES = 100 * 1024 * 1024


def validate_epub_url_for_provider(
    *,
    provider: str | None,
    url: str,
    archive_identifier: str | None = None,
) -> None:
    if provider == "gutenberg":
        validate_gutenberg_epub_url(url)
        return
    if provider == "internet_archive":
        validate_internet_archive_epub_url(url, archive_identifier)
        return
    raise ValueError(f"provider {provider or '<missing>'} does not support acquire")


def validate_gutenberg_epub_url(url: str) -> None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"http", "https"} or hostname not in ALLOWED_GUTENBERG_HOSTS:
        raise ValueError("candidate EPUB URL is not an allowed Gutenberg URL")
    if ".epub" not in unquote(parsed.path).casefold():
        raise ValueError("candidate EPUB URL does not point to an EPUB file")


def validate_internet_archive_epub_url(
    url: str,
    archive_identifier: str | None,
) -> None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("candidate EPUB URL is not an allowed Internet Archive URL")
    if hostname not in ALLOWED_INTERNET_ARCHIVE_HOSTS and not hostname.endswith(".archive.org"):
        raise ValueError("candidate EPUB URL is not an allowed Internet Archive URL")
    path = unquote(parsed.path)
    if ".epub" not in path.casefold():
        raise ValueError("candidate EPUB URL does not point to an EPUB file")
    if archive_identifier and hostname in ALLOWED_INTERNET_ARCHIVE_HOSTS:
        expected_prefix = f"/download/{archive_identifier}/"
        if not path.startswith(expected_prefix):
            raise ValueError("candidate EPUB URL is not an allowed Internet Archive item URL")


def download_limit(config: Mapping[str, Any]) -> int:
    value = config.get("acquisition_download_max_bytes")
    if value is None:
        return DEFAULT_DOWNLOAD_LIMIT_BYTES
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return DEFAULT_DOWNLOAD_LIMIT_BYTES


def normalise_epub_name(filename: str | None) -> str:
    raw_name = Path(filename or "acquired.epub").name or "acquired.epub"
    stem = Path(raw_name).stem
    safe_stem = re.sub(r"[^0-9A-Za-z._ -]", "_", stem).strip(" ._-") or "acquired"
    return f"{safe_stem}.epub"


def filename_from_epub_url(
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


def reserve_epub_destination_path(directory: Path, filename: str) -> Path:
    """Return a collision-safe EPUB destination using tolerant stat checks."""

    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".epub"
    candidate = directory / f"{stem}{suffix}"
    counter = 1
    while safe_stat(candidate) is not None:
        candidate = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate
