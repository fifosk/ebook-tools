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

EXPLICIT_ONLY_DISCOVERY_PROVIDER_IDS: tuple[str, ...] = (
    "youtube_url",
    "zlibrary_attended",
)

ACQUISITION_PROVIDER_ORDER: tuple[str, ...] = (
    "local_epub",
    "nas_video",
    "manual_downloads",
    "youtube_url",
    "youtube_search",
    "download_station",
    "newznab_torznab",
    "openlibrary",
    "zlibrary_attended",
    "gutenberg",
    "internet_archive",
)

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

_ACQUISITION_PROVIDER_ORDER_INDEX = {
    provider_id: index for index, provider_id in enumerate(ACQUISITION_PROVIDER_ORDER)
}


def normalized_provider_id(value: str | None) -> str:
    return str(value or "").strip().casefold()


def acquisition_provider_sort_key(provider_id: str | None) -> tuple[int, str]:
    """Return a stable cross-surface ordering key for acquisition providers."""

    normalized = normalized_provider_id(provider_id)
    return (
        _ACQUISITION_PROVIDER_ORDER_INDEX.get(
            normalized,
            len(_ACQUISITION_PROVIDER_ORDER_INDEX),
        ),
        normalized,
    )


def discovery_media_kinds_for(provider_id: str) -> tuple[str, ...]:
    """Return media kinds the provider supports through /api/acquisition/discover."""

    return DISCOVERY_PROVIDER_MEDIA_KINDS.get(normalized_provider_id(provider_id), ())


def can_join_default_discovery(provider_id: str, media_kind: str) -> bool:
    """Return whether provider may participate in backend-owned Default sources."""

    normalized = normalized_provider_id(provider_id)
    if normalized in EXPLICIT_ONLY_DISCOVERY_PROVIDER_IDS:
        return False
    return normalized_provider_id(media_kind) in discovery_media_kinds_for(normalized)


def acquisition_provider_label(provider_id: str) -> str:
    """Return the user-facing label for a known acquisition provider id."""

    normalized = normalized_provider_id(provider_id)
    return ACQUISITION_PROVIDER_LABELS.get(normalized, str(provider_id or "").strip())


def discovery_provider_label(provider_id: str) -> str:
    """Return the user-facing label for a known discovery provider id."""

    return acquisition_provider_label(provider_id)
