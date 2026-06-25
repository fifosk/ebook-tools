"""Token-safe provider registry for discovery/acquisition surfaces."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from modules import config_manager as cfg
from modules.services.youtube_dubbing import DEFAULT_YOUTUBE_VIDEO_ROOT


@dataclass(frozen=True)
class AcquisitionProvider:
    """Backend provider metadata safe to expose to clients."""

    id: str
    label: str
    media_kinds: tuple[str, ...]
    capabilities: tuple[str, ...]
    status: str
    configured: bool
    available: bool
    rights: tuple[str, ...]
    source_path: str | None = None
    policy_notes: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        """Return a Pydantic-friendly representation."""

        payload: dict[str, object] = {
            "id": self.id,
            "label": self.label,
            "media_kinds": list(self.media_kinds),
            "capabilities": list(self.capabilities),
            "status": self.status,
            "configured": self.configured,
            "available": self.available,
            "rights": list(self.rights),
            "policy_notes": list(self.policy_notes),
            "next_actions": list(self.next_actions),
        }
        if self.source_path:
            payload["source_path"] = self.source_path
        return payload


@dataclass(frozen=True)
class AcquisitionProviderRegistry:
    """Collection of acquisition providers and global policy metadata."""

    providers: tuple[AcquisitionProvider, ...]
    policy_notes: tuple[str, ...] = field(default_factory=tuple)
    paths: Mapping[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        """Return a serializable registry snapshot."""

        return {
            "providers": [provider.as_dict() for provider in self.providers],
            "policy_notes": list(self.policy_notes),
            "paths": dict(self.paths),
        }


def list_acquisition_providers(
    *,
    config: Mapping[str, Any] | None = None,
    context: cfg.RuntimeContext | None = None,
) -> AcquisitionProviderRegistry:
    """Return token-safe provider metadata for Web and Apple Create."""

    config = config or {}
    books_root = resolve_books_root(config=config, context=context)
    video_root = resolve_video_root(config)
    youtube_api_configured = _truthy_env(
        "YOUTUBE_API_KEY",
        "EBOOK_YOUTUBE_API_KEY",
    ) or _truthy_config(config, "youtube_api_key", "youtube_data_api_key")
    download_station_configured = _truthy_env(
        "SYNOLOGY_DOWNLOAD_STATION_URL",
        "SYNOLOGY_DOWNLOAD_STATION_HOST",
        "EBOOK_DOWNLOAD_STATION_URL",
    ) or _truthy_config(
        config,
        "download_station_url",
        "synology_download_station_url",
        "download_station_host",
    )
    indexer_configured = _truthy_env(
        "PROWLARR_URL",
        "TORZNAB_URL",
        "NEWZNAB_URL",
        "EBOOK_PROWLARR_URL",
    ) or _truthy_config(
        config,
        "prowlarr_url",
        "torznab_url",
        "newznab_url",
    )

    providers = (
        AcquisitionProvider(
            id="local_epub",
            label="Local EPUB library",
            media_kinds=("book",),
            capabilities=("import_local", "metadata"),
            status="available" if _is_readable_dir(books_root) else "not_configured",
            configured=True,
            available=_is_readable_dir(books_root),
            rights=("user_provided",),
            source_path=books_root.as_posix(),
            policy_notes=(
                "Uses backend-visible EPUB files under the configured books root.",
            ),
            next_actions=("prepare_epub_source", "create_book_job"),
        ),
        AcquisitionProvider(
            id="nas_video",
            label="NAS video library",
            media_kinds=("video",),
            capabilities=("import_local", "extract_subtitles", "metadata"),
            status="available" if _is_readable_dir(video_root) else "not_configured",
            configured=True,
            available=_is_readable_dir(video_root),
            rights=("user_provided",),
            source_path=video_root.as_posix(),
            policy_notes=(
                "Uses downloaded or user-owned videos visible to the backend NAS scanner.",
            ),
            next_actions=("choose_video", "extract_subtitles", "create_dub_job"),
        ),
        AcquisitionProvider(
            id="youtube_url",
            label="YouTube URL",
            media_kinds=("video",),
            capabilities=("metadata", "acquire", "extract_subtitles"),
            status="available",
            configured=True,
            available=True,
            rights=("unknown", "restricted"),
            policy_notes=(
                "Direct URL inspection reuses the existing yt-dlp workflow and must "
                "respect the user's rights and backend policy.",
            ),
            next_actions=("inspect_url", "choose_subtitle", "download_video"),
        ),
        AcquisitionProvider(
            id="youtube_search",
            label="YouTube search",
            media_kinds=("video",),
            capabilities=("search", "metadata"),
            status="available" if youtube_api_configured else "not_configured",
            configured=youtube_api_configured,
            available=youtube_api_configured,
            rights=("unknown", "restricted"),
            policy_notes=(
                "Search uses the YouTube Data API when configured; acquisition remains "
                "a separate reviewed step.",
            ),
            next_actions=("search", "inspect_url"),
        ),
        AcquisitionProvider(
            id="download_station",
            label="Synology Download Station",
            media_kinds=("video",),
            capabilities=("acquire", "poll"),
            status="available" if download_station_configured else "not_configured",
            configured=download_station_configured,
            available=download_station_configured,
            rights=("unknown", "restricted"),
            policy_notes=(
                "Queue handoff is for lawful reviewed torrents, magnets, NZBs, or URLs only.",
            ),
            next_actions=("confirm_acquisition", "poll_download", "import_local"),
        ),
        AcquisitionProvider(
            id="newznab_torznab",
            label="Newznab/Torznab indexers",
            media_kinds=("video",),
            capabilities=("search", "metadata"),
            status="available" if indexer_configured else "not_configured",
            configured=indexer_configured,
            available=indexer_configured,
            rights=("unknown", "restricted"),
            policy_notes=(
                "Indexer results are review-only until the user confirms a lawful acquisition.",
            ),
            next_actions=("search", "confirm_acquisition"),
        ),
        AcquisitionProvider(
            id="openlibrary",
            label="Open Library metadata",
            media_kinds=("book",),
            capabilities=("search", "metadata"),
            status="planned",
            configured=False,
            available=False,
            rights=("unknown",),
            policy_notes=(
                "Metadata-first book lookup; do not assume a downloadable EPUB is available.",
            ),
            next_actions=("search_metadata", "enrich_book"),
        ),
        AcquisitionProvider(
            id="gutenberg",
            label="Project Gutenberg/Gutendex",
            media_kinds=("book",),
            capabilities=("search", "metadata", "acquire"),
            status="planned",
            configured=False,
            available=False,
            rights=("public_domain", "open_license"),
            policy_notes=(
                "Public-domain/open ebook discovery and download provider planned.",
            ),
            next_actions=("search", "download_epub", "create_book_job"),
        ),
        AcquisitionProvider(
            id="internet_archive",
            label="Internet Archive",
            media_kinds=("book", "video"),
            capabilities=("search", "metadata", "acquire"),
            status="planned",
            configured=False,
            available=False,
            rights=("public_domain", "open_license", "unknown"),
            policy_notes=(
                "Only ordinary downloadable files with suitable access metadata should be offered.",
            ),
            next_actions=("search", "review_files", "import_local"),
        ),
    )

    return AcquisitionProviderRegistry(
        providers=providers,
        policy_notes=(
            "Do not automate Z-Library or other shadow-library download workflows.",
            "Downloader and indexer providers require explicit user review and lawful authorization.",
            "Credentials and raw provider tokens stay server-side and are never returned by this endpoint.",
        ),
        paths={
            "books_root": books_root.as_posix(),
            "video_root": video_root.as_posix(),
        },
    )


def resolve_books_root(
    *,
    config: Mapping[str, Any],
    context: cfg.RuntimeContext | None,
) -> Path:
    """Resolve the backend-visible EPUB source root."""

    if context is not None:
        return context.books_dir.expanduser()
    raw_value = config.get("ebooks_dir")
    if isinstance(raw_value, str) and raw_value.strip():
        return _resolve_display_path(raw_value.strip())
    return _resolve_display_path(cfg.DEFAULT_BOOKS_RELATIVE)


def resolve_video_root(config: Mapping[str, Any]) -> Path:
    """Resolve the backend-visible NAS video source root."""

    for key in ("youtube_video_root", "youtube_library_root", "video_download_root"):
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return _resolve_display_path(value.strip())
    return DEFAULT_YOUTUBE_VIDEO_ROOT


def _resolve_display_path(path_value: object) -> Path:
    path = Path(str(path_value)).expanduser()
    if path.is_absolute():
        return path
    return (cfg.SCRIPT_DIR / path).resolve()


def _is_readable_dir(path: Path) -> bool:
    try:
        return path.exists() and path.is_dir()
    except OSError:
        return False


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
