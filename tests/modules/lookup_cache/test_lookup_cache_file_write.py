"""Test that lookup cache file is actually written to disk."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from modules.lookup_cache import (
    LookupCache,
    LookupCacheEntry,
    LookupCacheManager,
    LookupCacheStats,
    load_lookup_cache,
    normalize_word,
)


def test_direct_file_write():
    """Test that LookupCacheManager.save() actually writes a file."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Create manager
        manager = LookupCacheManager(
            job_id="test-job",
            job_dir=tmp_path,
            input_language="Arabic",
            definition_language="English",
        )

        # Add entries directly
        for i, word in enumerate(["كتاب", "قلم", "باب"]):
            entry = LookupCacheEntry(
                word=word,
                word_normalized=normalize_word(word),
                input_language="Arabic",
                definition_language="English",
                lookup_result={
                    "type": "word",
                    "definition": f"Definition {i}",
                    "part_of_speech": "noun",
                },
                audio_references=[],
            )
            manager.add_entry(entry)

        # Save
        print(f"Saving to: {manager.cache_path}")
        manager.save()

        # Check file exists
        cache_path = tmp_path / "metadata" / "lookup_cache.json"
        print(f"Cache path exists: {cache_path.exists()}")
        assert cache_path.exists(), f"Cache file not created at {cache_path}"

        # Read and verify
        with open(cache_path, "r") as f:
            data = json.load(f)

        print(f"Entries count: {len(data.get('entries', {}))}")
        assert len(data.get("entries", {})) == 3

        # Load via load_lookup_cache
        loaded = load_lookup_cache(tmp_path)
        assert loaded is not None
        assert loaded.stats.total_words == 3

        print("SUCCESS: File was written correctly!")


def test_lookup_cache_model_save():
    """Test the LookupCache model's save method directly."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir(parents=True)

        cache = LookupCache(
            job_id="test-job",
            input_language="Arabic",
            definition_language="English",
        )

        # Add entry
        entry = LookupCacheEntry(
            word="كتاب",
            word_normalized="كتاب",
            input_language="Arabic",
            definition_language="English",
            lookup_result={"type": "word", "definition": "book"},
            audio_references=[],
        )
        cache.add(entry)
        cache.update_stats()

        # Save
        cache_path = metadata_dir / "lookup_cache.json"
        print(f"Saving LookupCache to: {cache_path}")
        cache.save(cache_path)

        # Check
        assert cache_path.exists(), f"File not created: {cache_path}"

        with open(cache_path) as f:
            data = json.load(f)
        print(f"File content: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
        assert "entries" in data
        assert len(data["entries"]) == 1

        print("SUCCESS: LookupCache.save() works!")


if __name__ == "__main__":
    print("=" * 60)
    print("Test 1: Direct file write via LookupCacheManager")
    print("=" * 60)
    test_direct_file_write()

    print()
    print("=" * 60)
    print("Test 2: LookupCache model save")
    print("=" * 60)
    test_lookup_cache_model_save()
