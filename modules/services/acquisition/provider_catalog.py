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


def normalized_provider_id(value: str | None) -> str:
    return str(value or "").strip().casefold()


def discovery_media_kinds_for(provider_id: str) -> tuple[str, ...]:
    """Return media kinds the provider supports through /api/acquisition/discover."""

    return DISCOVERY_PROVIDER_MEDIA_KINDS.get(normalized_provider_id(provider_id), ())
