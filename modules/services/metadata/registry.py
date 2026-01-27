"""Source registry and fallback chain configuration for metadata lookup."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Type

from .types import MediaType, MetadataSource
from .clients.base import BaseMetadataClient
from .clients.openlibrary import OpenLibraryClient
from .clients.google_books import GoogleBooksClient
from .clients.tmdb import TMDBClient
from .clients.omdb import OMDbClient
from .clients.tvmaze import TVMazeClient
from .clients.wikipedia import WikipediaClient
from .clients.ytdlp import YtDlpClient


# Default fallback chains by media type
DEFAULT_CHAINS: Dict[MediaType, List[MetadataSource]] = {
    MediaType.BOOK: [
        MetadataSource.OPENLIBRARY,  # Primary: no API key
        MetadataSource.GOOGLE_BOOKS,  # Secondary: API key required
        MetadataSource.WIKIPEDIA,  # Fallback: no API key
    ],
    MediaType.MOVIE: [
        MetadataSource.TMDB,  # Primary: API key required
        MetadataSource.OMDB,  # Secondary: API key required
        MetadataSource.WIKIPEDIA,  # Fallback: no API key
    ],
    MediaType.TV_SERIES: [
        MetadataSource.TMDB,  # Primary: API key required, best metadata
        MetadataSource.OMDB,  # Secondary: API key required
        MetadataSource.TVMAZE,  # Fallback: no API key
        MetadataSource.WIKIPEDIA,  # Fallback: no API key
    ],
    MediaType.TV_EPISODE: [
        MetadataSource.TMDB,  # Primary: API key required, best metadata
        MetadataSource.OMDB,  # Secondary: API key required
        MetadataSource.TVMAZE,  # Fallback: no API key
    ],
    MediaType.YOUTUBE_VIDEO: [
        MetadataSource.YTDLP,  # Only source: no API key
    ],
}


# Mapping from source to client class
CLIENT_CLASSES: Dict[MetadataSource, Type[BaseMetadataClient]] = {
    MetadataSource.OPENLIBRARY: OpenLibraryClient,
    MetadataSource.GOOGLE_BOOKS: GoogleBooksClient,
    MetadataSource.TMDB: TMDBClient,
    MetadataSource.OMDB: OMDbClient,
    MetadataSource.TVMAZE: TVMazeClient,
    MetadataSource.WIKIPEDIA: WikipediaClient,
    MetadataSource.YTDLP: YtDlpClient,
}


# Environment variable names for API keys
API_KEY_ENV_VARS: Dict[MetadataSource, str] = {
    MetadataSource.TMDB: "EBOOK_API_KEY_TMDB",
    MetadataSource.OMDB: "EBOOK_API_KEY_OMDB",
    MetadataSource.GOOGLE_BOOKS: "EBOOK_API_KEY_GOOGLE_BOOKS",
}


class MetadataSourceRegistry:
    """Registry for metadata source clients and fallback chains.

    Manages client instantiation, availability checking, and
    provides the fallback chain for each media type.
    """

    def __init__(
        self,
        api_keys: Optional[Dict[str, str]] = None,
        custom_chains: Optional[Dict[MediaType, List[MetadataSource]]] = None,
    ) -> None:
        """Initialize the registry.

        Args:
            api_keys: Dictionary mapping source names to API keys.
                      Keys should be source enum values (e.g., "tmdb", "omdb").
            custom_chains: Optional custom fallback chains to override defaults.
        """
        self._api_keys = api_keys or {}
        self._clients: Dict[MetadataSource, BaseMetadataClient] = {}
        self._chains = {**DEFAULT_CHAINS}
        if custom_chains:
            self._chains.update(custom_chains)

    def get_client(self, source: MetadataSource) -> Optional[BaseMetadataClient]:
        """Get or create a client for the given source.

        Args:
            source: The metadata source.

        Returns:
            The client if available, None otherwise.
        """
        if source in self._clients:
            return self._clients[source]

        client_class = CLIENT_CLASSES.get(source)
        if client_class is None:
            return None

        # Get API key for this source
        api_key = self._api_keys.get(source.value)

        # Create client
        try:
            client = client_class(api_key=api_key)
        except Exception:
            return None

        # Check if client is available
        if not client.is_available:
            return None

        self._clients[source] = client
        return client

    def get_chain(self, media_type: MediaType) -> Sequence[MetadataSource]:
        """Return the fallback chain for a media type.

        Args:
            media_type: The type of media.

        Returns:
            List of sources to try in order.
        """
        return self._chains.get(media_type, [])

    def get_available_sources(self, media_type: MediaType) -> List[MetadataSource]:
        """Return sources that are both in the chain and available.

        Args:
            media_type: The type of media.

        Returns:
            List of available sources in priority order.
        """
        chain = self.get_chain(media_type)
        available = []
        for source in chain:
            client = self.get_client(source)
            if client is not None and client.supports(media_type):
                available.append(source)
        return available

    def set_chain(self, media_type: MediaType, chain: List[MetadataSource]) -> None:
        """Override the fallback chain for a media type.

        Args:
            media_type: The type of media.
            chain: List of sources to try in order.
        """
        self._chains[media_type] = chain

    def set_api_key(self, source: MetadataSource, api_key: str) -> None:
        """Set or update an API key for a source.

        This will invalidate any existing client for that source.

        Args:
            source: The metadata source.
            api_key: The API key.
        """
        self._api_keys[source.value] = api_key
        # Invalidate existing client
        if source in self._clients:
            self._clients[source].close()
            del self._clients[source]

    def close(self) -> None:
        """Close all clients and release resources."""
        for client in self._clients.values():
            try:
                client.close()
            except Exception:
                pass
        self._clients.clear()

    def __enter__(self) -> "MetadataSourceRegistry":
        return self

    def __exit__(self, *args) -> None:
        self.close()


def create_registry_from_config(config: Optional[Dict] = None) -> MetadataSourceRegistry:
    """Create a registry from configuration.

    Args:
        config: Configuration dictionary. If None, uses default config.

    Returns:
        Configured MetadataSourceRegistry.
    """
    from modules import config_manager as cfg

    if config is None:
        # Load from default config using get_settings()
        settings = cfg.get_settings()
        api_keys_config = getattr(settings, "api_keys", {}) or {}
        metadata_config = getattr(settings, "metadata_lookup", {}) or {}

        # Also check for flat key format (from settings UI)
        tmdb_key = getattr(settings, "tmdb_api_key", None)
        omdb_key = getattr(settings, "omdb_api_key", None)
        google_books_key = getattr(settings, "google_books_api_key", None)
    else:
        api_keys_config = config.get("api_keys", {})
        metadata_config = config.get("metadata_lookup", {})
        tmdb_key = config.get("tmdb_api_key")
        omdb_key = config.get("omdb_api_key")
        google_books_key = config.get("google_books_api_key")

    # Extract relevant API keys (check both nested and flat formats)
    api_keys = {}

    # TMDB key - check flat format first, then nested
    if tmdb_key:
        # Handle SecretStr from settings
        api_keys["tmdb"] = tmdb_key.get_secret_value() if hasattr(tmdb_key, "get_secret_value") else tmdb_key
    elif api_keys_config.get("tmdb"):
        api_keys["tmdb"] = api_keys_config["tmdb"]

    # OMDb key
    if omdb_key:
        api_keys["omdb"] = omdb_key.get_secret_value() if hasattr(omdb_key, "get_secret_value") else omdb_key
    elif api_keys_config.get("omdb"):
        api_keys["omdb"] = api_keys_config["omdb"]

    # Google Books key
    if google_books_key:
        api_keys["google_books"] = google_books_key.get_secret_value() if hasattr(google_books_key, "get_secret_value") else google_books_key
    elif api_keys_config.get("google_books"):
        api_keys["google_books"] = api_keys_config["google_books"]

    # Check for custom chains in config
    custom_chains = None
    if metadata_config.get("fallback_chains"):
        chains_config = metadata_config["fallback_chains"]
        custom_chains = {}
        for media_type_str, sources in chains_config.items():
            try:
                media_type = MediaType(media_type_str)
                source_list = [MetadataSource(s) for s in sources]
                custom_chains[media_type] = source_list
            except (ValueError, KeyError):
                pass

    return MetadataSourceRegistry(api_keys=api_keys, custom_chains=custom_chains)


__all__ = [
    "MetadataSourceRegistry",
    "create_registry_from_config",
    "DEFAULT_CHAINS",
    "CLIENT_CLASSES",
]
