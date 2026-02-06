#!/usr/bin/env python3
"""Rebuild the lookup cache for an existing job.

Usage:
    python scripts/rebuild_lookup_cache.py <job_id_or_path> [--dry-run]

This script:
1. Loads all chunk metadata for the job
2. Extracts translation text from sentences
3. Deletes the old lookup cache
4. Rebuilds it using the LLM with the corrected tokenizer

Examples:
    python scripts/rebuild_lookup_cache.py d3493926-805c-46c3-a095-2d5198e2ef90
    python scripts/rebuild_lookup_cache.py storage/d3493926-... --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def find_job_dir(job_id_or_path: str) -> Path:
    """Resolve job directory from ID or path."""
    candidate = Path(job_id_or_path)
    if candidate.is_dir() and (candidate / "metadata").is_dir():
        return candidate.resolve()

    # Try storage/<job_id>
    storage_path = PROJECT_ROOT / "storage" / job_id_or_path
    if storage_path.is_dir():
        return storage_path.resolve()

    # Try storage/jobs/<job_id>
    jobs_path = PROJECT_ROOT / "storage" / "jobs" / job_id_or_path
    if jobs_path.is_dir():
        return jobs_path.resolve()

    raise FileNotFoundError(f"Cannot find job directory for: {job_id_or_path}")


def load_sentences_from_chunks(job_dir: Path) -> list[str]:
    """Load all translation sentences from chunk metadata files."""
    metadata_dir = job_dir / "metadata"
    sentences: list[str] = []

    # Find all chunk files
    chunk_files = sorted(metadata_dir.glob("chunk_*.json"))
    if not chunk_files:
        raise FileNotFoundError(f"No chunk files found in {metadata_dir}")

    for chunk_file in chunk_files:
        with open(chunk_file, "r", encoding="utf-8") as f:
            chunk_data = json.load(f)

        chunk_sentences = chunk_data.get("sentences", [])
        for entry in chunk_sentences:
            if not isinstance(entry, dict):
                continue

            # Extract translation text (same logic as lookup_cache_phase._extract_lookup_text)
            text = None

            # Prefer translation variant
            translation_raw = entry.get("translation")
            if isinstance(translation_raw, dict):
                t = translation_raw.get("text", "")
                if isinstance(t, str) and t.strip():
                    text = t.strip()
            elif isinstance(translation_raw, str) and translation_raw.strip():
                text = translation_raw.strip()

            # Fall back to original variant
            if not text:
                original_raw = entry.get("original")
                if isinstance(original_raw, dict):
                    t = original_raw.get("text", "")
                    if isinstance(t, str) and t.strip():
                        text = t.strip()

            # Fall back to top-level text
            if not text:
                text_value = entry.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    text = text_value.strip()

            if text:
                sentences.append(text)

    return sentences


def main():
    parser = argparse.ArgumentParser(description="Rebuild lookup cache for an existing job")
    parser.add_argument("job", help="Job ID or path to job directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without rebuilding")
    parser.add_argument("--batch-size", type=int, default=10, help="Words per LLM batch call (default: 10)")
    args = parser.parse_args()

    # Find job directory
    job_dir = find_job_dir(args.job)
    job_id = job_dir.name
    print(f"Job directory: {job_dir}")
    print(f"Job ID: {job_id}")

    # Check existing cache
    cache_path = job_dir / "metadata" / "lookup_cache.json"
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            old_cache = json.load(f)
        old_count = len(old_cache.get("entries", {}))
        old_lang = old_cache.get("input_language", "?")
        old_def_lang = old_cache.get("definition_language", "?")
        print(f"Existing cache: {old_count} entries, {old_lang} → {old_def_lang}")
        # Show a few broken keys for comparison
        old_keys = list(old_cache.get("entries", {}).keys())[:5]
        print(f"  Sample old keys: {old_keys}")
    else:
        old_lang = None
        old_def_lang = None
        print("No existing cache found")

    # Load sentences
    sentences = load_sentences_from_chunks(job_dir)
    print(f"Loaded {len(sentences)} sentences from chunk files")

    if not sentences:
        print("No sentences found — nothing to do")
        return

    # Show sample extraction with new tokenizer
    from modules.lookup_cache.tokenizer import extract_words, normalize_word
    sample_text = sentences[0]
    sample_words = extract_words(sample_text)
    print(f"\nSample sentence: {sample_text[:80]}...")
    print(f"Extracted words: {sample_words[:10]}")

    # Determine languages
    input_language = old_lang or "Hindi"
    definition_language = old_def_lang or "English"

    # Count unique new words
    from modules.lookup_cache.tokenizer import extract_unique_words
    unique_words = extract_unique_words(
        sentences,
        existing_cache=None,  # Ignore existing cache — full rebuild
        language=input_language,
        skip_stopwords=True,
        min_word_length=2,
    )
    print(f"\nUnique words to look up: {len(unique_words)}")
    print(f"  Sample: {unique_words[:15]}")

    if args.dry_run:
        print("\n[DRY RUN] Would rebuild cache with the above words. Exiting.")
        return

    # Backup old cache
    if cache_path.exists():
        backup_path = cache_path.with_suffix(".json.bak")
        import shutil
        shutil.copy2(cache_path, backup_path)
        print(f"\nBacked up old cache to: {backup_path.name}")
        # Delete old cache so we start fresh
        cache_path.unlink()

    # Rebuild
    from modules.lookup_cache import LookupCacheManager
    from modules.llm_client_manager import client_scope

    print(f"\nRebuilding cache: {input_language} → {definition_language}")
    print(f"Batch size: {args.batch_size}")

    start_time = time.perf_counter()

    cache_manager = LookupCacheManager(
        job_id=job_id,
        job_dir=job_dir,
        input_language=input_language,
        definition_language=definition_language,
    )

    with client_scope(None) as llm_client:
        new_count = cache_manager.build_from_sentences(
            sentences=sentences,
            llm_client=llm_client,
            batch_size=args.batch_size,
            skip_stopwords=True,
        )

    cache_manager.save()

    elapsed = time.perf_counter() - start_time
    print(f"\nDone! Built {new_count} entries in {elapsed:.1f}s")
    print(f"Cache saved to: {cache_path}")

    # Verify
    with open(cache_path, "r", encoding="utf-8") as f:
        new_cache = json.load(f)
    new_keys = list(new_cache.get("entries", {}).keys())[:10]
    print(f"New cache entries: {len(new_cache.get('entries', {}))}")
    print(f"  Sample new keys: {new_keys}")


if __name__ == "__main__":
    main()
