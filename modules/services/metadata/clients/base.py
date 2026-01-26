"""Base class for metadata API clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence, TYPE_CHECKING

import requests

from ..types import LookupOptions, LookupQuery, MediaType, MetadataSource, UnifiedMetadataResult

if TYPE_CHECKING:
    pass


class BaseMetadataClient(ABC):
    """Abstract base class for metadata API clients.

    All metadata source clients inherit from this class and implement
    the `lookup` method to query their respective APIs.
    """

    # Subclasses must set these class attributes
    name: MetadataSource
    supported_types: Sequence[MediaType]
    requires_api_key: bool = False

    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        """Initialize the client.

        Args:
            session: Optional requests session for connection pooling.
            api_key: API key for services that require authentication.
            timeout_seconds: Default timeout for API requests.
        """
        self._session = session or requests.Session()
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._owns_session = session is None

    @property
    def is_available(self) -> bool:
        """Return True if this client can be used.

        A client is available if it doesn't require an API key,
        or if an API key has been provided.
        """
        if self.requires_api_key and not self._api_key:
            return False
        return True

    @abstractmethod
    def lookup(
        self,
        query: LookupQuery,
        options: LookupOptions,
    ) -> Optional[UnifiedMetadataResult]:
        """Execute a metadata lookup and return normalized result.

        Args:
            query: The lookup query with search parameters.
            options: Options controlling lookup behavior.

        Returns:
            A UnifiedMetadataResult if a match is found, None otherwise.
            Should not raise exceptions - return None on errors.
        """
        ...

    def supports(self, media_type: MediaType) -> bool:
        """Return True if this client supports the given media type.

        Args:
            media_type: The type of media to check.

        Returns:
            True if the client can look up this media type.
        """
        return media_type in self.supported_types

    def close(self) -> None:
        """Release resources."""
        if self._owns_session:
            self._session.close()

    def __enter__(self) -> "BaseMetadataClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _get(
        self,
        url: str,
        *,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> Optional[dict]:
        """Make a GET request and return JSON response.

        Args:
            url: The URL to request.
            params: Optional query parameters.
            headers: Optional additional headers.
            timeout: Optional timeout override.

        Returns:
            Parsed JSON response as dict, or None on error.
        """
        try:
            response = self._session.get(
                url,
                params=params,
                headers={"Accept": "application/json", **(headers or {})},
                timeout=timeout or self._timeout,
            )
            if response.status_code != 200:
                return None
            return response.json()
        except Exception:
            return None


__all__ = ["BaseMetadataClient"]
