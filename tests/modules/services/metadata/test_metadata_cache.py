from __future__ import annotations

from pathlib import Path

import pytest

from modules.services.metadata.cache import MetadataCache
from modules.services.metadata.types import MediaType, LookupQuery, UnifiedMetadataResult

pytestmark = pytest.mark.services


def test_metadata_cache_get_and_delete_use_safe_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = MetadataCache(tmp_path)
    query = LookupQuery(
        media_type=MediaType.BOOK,
        title="The Test Book",
        author="Ada Reader",
    )
    result = UnifiedMetadataResult(
        title="The Test Book",
        type=MediaType.BOOK,
        author="Ada Reader",
        year=2026,
    )
    cache.set(query, result)
    cache_path = cache._cache_path(cache._cache_key(query))  # noqa: SLF001 - pins cache file behavior.
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path == cache_path:
            raise AssertionError("metadata cache files should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    loaded = cache.get(query)
    deleted = cache.delete(query)

    assert loaded is not None
    assert loaded.title == "The Test Book"
    assert loaded.author == "Ada Reader"
    assert deleted is True
    assert not original_exists(cache_path)
