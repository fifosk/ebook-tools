"""Default discovery provider readiness helpers."""

from __future__ import annotations

import os
from typing import Any, Mapping


def is_youtube_search_configured(config: Mapping[str, Any]) -> bool:
    """Return whether YouTube search can be included in default video discovery."""

    return _truthy_env(
        "YOUTUBE_API_KEY",
        "EBOOK_YOUTUBE_API_KEY",
    ) or _truthy_config(config, "youtube_api_key", "youtube_data_api_key")


def is_indexer_search_configured(config: Mapping[str, Any]) -> bool:
    """Return whether review-only Newznab/Torznab search can join video discovery."""

    return _truthy_env(
        "PROWLARR_URL",
        "TORZNAB_URL",
        "NEWZNAB_URL",
        "EBOOK_PROWLARR_URL",
    ) or _truthy_config(
        config,
        "prowlarr_url",
        "torznab_url",
        "newznab_url",
        "indexer_url",
    )


def default_discovery_provider_ids_from_readiness(
    media_kind: str,
    *,
    books_root_readable: bool,
    video_root_readable: bool,
    has_readable_manual_roots: bool,
    youtube_search_configured: bool,
    indexer_search_configured: bool = False,
) -> tuple[str, ...]:
    """Return default providers from precomputed root/config readiness."""

    if media_kind == "book":
        providers: list[str] = []
        if books_root_readable:
            providers.append("local_epub")
        if has_readable_manual_roots:
            providers.append("manual_downloads")
        return tuple(providers or ("local_epub",))
    if media_kind == "video":
        providers = []
        if video_root_readable or not has_readable_manual_roots:
            providers.append("nas_video")
        if has_readable_manual_roots:
            providers.append("manual_downloads")
        if youtube_search_configured:
            providers.append("youtube_search")
        if indexer_search_configured:
            providers.append("newznab_torznab")
        return tuple(providers or ("nas_video",))
    return ()


def _truthy_env(*keys: str) -> bool:
    return any(bool(os.environ.get(key, "").strip()) for key in keys)


def _truthy_config(config: Mapping[str, Any], *keys: str) -> bool:
    for key in keys:
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return True
        if value is not None and not isinstance(value, str):
            return True
    return False
