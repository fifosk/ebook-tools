"""File-based cache for metadata lookup results."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from modules import logging_manager as log_mgr

from .types import LookupQuery, UnifiedMetadataResult

logger = log_mgr.get_logger().getChild("services.metadata.cache")


class MetadataCache:
    """File-based cache for metadata lookup results.

    Stores results as JSON files with SHA256-based filenames.
    Supports configurable TTL for automatic expiry.
    """

    def __init__(
        self,
        cache_dir: Path,
        ttl_hours: int = 24 * 7,  # 1 week default
    ) -> None:
        """Initialize the cache.

        Args:
            cache_dir: Directory to store cache files.
            ttl_hours: Time-to-live in hours for cache entries.
        """
        self._cache_dir = Path(cache_dir)
        self._ttl = timedelta(hours=ttl_hours)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, query: LookupQuery) -> str:
        """Generate a stable cache key from query parameters.

        Args:
            query: The lookup query.

        Returns:
            A 16-character hex string cache key.
        """
        key_parts = query.cache_key_parts()
        key_string = "|".join(str(p).lower() for p in key_parts)
        return hashlib.sha256(key_string.encode("utf-8")).hexdigest()[:16]

    def _cache_path(self, key: str) -> Path:
        """Get the file path for a cache key.

        Args:
            key: The cache key.

        Returns:
            Path to the cache file.
        """
        return self._cache_dir / f"{key}.json"

    def get(self, query: LookupQuery) -> Optional[UnifiedMetadataResult]:
        """Retrieve cached result if valid.

        Args:
            query: The lookup query.

        Returns:
            Cached result if found and not expired, None otherwise.
        """
        key = self._cache_key(query)
        path = self._cache_path(key)

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("Failed to read cache file %s: %s", path, exc)
            return None

        # Check TTL
        cached_at = data.get("cached_at")
        if cached_at:
            try:
                cached_time = datetime.fromisoformat(cached_at)
                if datetime.now(timezone.utc) - cached_time > self._ttl:
                    logger.debug("Cache entry expired for key %s", key)
                    path.unlink(missing_ok=True)
                    return None
            except ValueError:
                pass

        # Deserialize result
        result_data = data.get("result")
        if not result_data:
            return None

        try:
            result = UnifiedMetadataResult.from_dict(result_data)
            logger.debug("Cache hit for key %s", key)
            return result
        except Exception as exc:
            logger.debug("Failed to deserialize cached result: %s", exc)
            return None

    def set(self, query: LookupQuery, result: UnifiedMetadataResult) -> None:
        """Store result in cache.

        Args:
            query: The lookup query.
            result: The result to cache.
        """
        key = self._cache_key(query)
        path = self._cache_path(key)

        data = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "query": {
                "media_type": query.media_type.value,
                "title": query.title,
                "author": query.author,
                "isbn": query.isbn,
                "series_name": query.series_name,
                "season": query.season,
                "episode": query.episode,
                "youtube_video_id": query.youtube_video_id,
            },
            "result": result.to_dict(include_raw=False),
        }

        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.debug("Cached result for key %s", key)
        except OSError as exc:
            logger.warning("Failed to write cache file %s: %s", path, exc)

    def delete(self, query: LookupQuery) -> bool:
        """Delete a cached result.

        Args:
            query: The lookup query.

        Returns:
            True if entry was deleted, False if not found.
        """
        key = self._cache_key(query)
        path = self._cache_path(key)

        if path.exists():
            try:
                path.unlink()
                logger.debug("Deleted cache entry for key %s", key)
                return True
            except OSError:
                pass
        return False

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries deleted.
        """
        count = 0
        for path in self._cache_dir.glob("*.json"):
            try:
                path.unlink()
                count += 1
            except OSError:
                pass
        logger.info("Cleared %d cache entries", count)
        return count

    def cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of entries removed.
        """
        count = 0
        now = datetime.now(timezone.utc)

        for path in self._cache_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                cached_at = data.get("cached_at")
                if cached_at:
                    cached_time = datetime.fromisoformat(cached_at)
                    if now - cached_time > self._ttl:
                        path.unlink()
                        count += 1
            except (OSError, json.JSONDecodeError, ValueError):
                # Remove invalid entries
                try:
                    path.unlink()
                    count += 1
                except OSError:
                    pass

        if count > 0:
            logger.info("Cleaned up %d expired cache entries", count)
        return count

    @property
    def cache_dir(self) -> Path:
        """Return the cache directory path."""
        return self._cache_dir

    @property
    def ttl_hours(self) -> int:
        """Return the TTL in hours."""
        return int(self._ttl.total_seconds() / 3600)


__all__ = ["MetadataCache"]
