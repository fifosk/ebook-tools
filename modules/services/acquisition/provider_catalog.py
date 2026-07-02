"""Discovery provider media-kind catalog shared by registry and routing."""

from __future__ import annotations

from typing import Mapping


DISCOVERY_PROVIDER_MEDIA_KINDS: Mapping[str, tuple[str, ...]] = {
    "gutenberg": ("book",),
    "internet_archive": ("book",),
    "local_epub": ("book",),
    "manual_downloads": ("book", "video"),
    "nas_video": ("video",),
    "newznab_torznab": ("video",),
    "openlibrary": ("book",),
    "youtube_search": ("video",),
    "youtube_url": ("video",),
}

ACQUISITION_PROVIDER_LABELS: Mapping[str, str] = {
    "download_station": "Synology Download Station",
    "gutenberg": "Project Gutenberg/Gutendex",
    "internet_archive": "Internet Archive",
    "local_epub": "Local EPUB library",
    "manual_downloads": "Manual download folders",
    "nas_video": "NAS video library",
    "newznab_torznab": "Newznab/Torznab indexers",
    "openlibrary": "Open Library metadata",
    "youtube_search": "YouTube search",
    "youtube_url": "YouTube URL",
    "zlibrary_attended": "Z-Library attended import",
}


def normalized_provider_id(value: str | None) -> str:
    return str(value or "").strip().casefold()


def discovery_media_kinds_for(provider_id: str) -> tuple[str, ...]:
    """Return media kinds the provider supports through /api/acquisition/discover."""

    return DISCOVERY_PROVIDER_MEDIA_KINDS.get(normalized_provider_id(provider_id), ())


def acquisition_provider_label(provider_id: str) -> str:
    """Return the user-facing label for a known acquisition provider id."""

    normalized = normalized_provider_id(provider_id)
    return ACQUISITION_PROVIDER_LABELS.get(normalized, str(provider_id or "").strip())


def discovery_provider_label(provider_id: str) -> str:
    """Return the user-facing label for a known discovery provider id."""

    return acquisition_provider_label(provider_id)
