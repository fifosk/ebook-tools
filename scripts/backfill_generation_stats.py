#!/usr/bin/env python3
"""One-time backfill script for media_generation_stats.

Scans completed jobs from the filesystem and populates the
``media_generation_stats`` table from their chunk metadata.

Usage:
    python scripts/backfill_generation_stats.py --dry-run
    python scripts/backfill_generation_stats.py
    python scripts/backfill_generation_stats.py --verify
    python scripts/backfill_generation_stats.py --job-id <JOB_ID>

Requires DATABASE_URL to be set (will exit with an error if not).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so modules can be imported.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


def _load_job_metadata(job_dir: Path) -> dict | None:
    """Load metadata/job.json from a job directory."""
    meta_path = job_dir / "metadata" / "job.json"
    if not meta_path.is_file():
        return None
    try:
        with open(meta_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _load_chunk_audio_tracks(job_dir: Path, metadata_path: str) -> dict | None:
    """Load audioTracks from a chunk metadata file on disk."""
    chunk_path = job_dir / metadata_path
    if not chunk_path.is_file():
        return None
    try:
        with open(chunk_path) as f:
            data = json.load(f)
        return data.get("audioTracks") or data.get("audio_tracks")
    except (json.JSONDecodeError, OSError):
        return None


def _enrich_chunks_from_disk(job_dir: Path, chunks: list[dict]) -> list[dict]:
    """For chunks that lack inline audioTracks, load from disk."""
    enriched = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        audio = chunk.get("audioTracks") or chunk.get("audio_tracks")
        if not audio:
            meta_path = chunk.get("metadataPath") or chunk.get("metadata_path")
            if meta_path:
                disk_audio = _load_chunk_audio_tracks(job_dir, meta_path)
                if disk_audio:
                    chunk = dict(chunk)
                    chunk["audioTracks"] = disk_audio
        enriched.append(chunk)
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill media_generation_stats from completed jobs.")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report without writing to DB.")
    parser.add_argument("--verify", action="store_true", help="Compare job count vs stats table count.")
    parser.add_argument("--job-id", help="Backfill a single job by ID.")
    parser.add_argument(
        "--storage-dir",
        default=os.environ.get("JOB_STORAGE_DIR", str(_PROJECT_ROOT / "storage")),
        help="Path to the storage directory (default: $JOB_STORAGE_DIR or ./storage).",
    )
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("ERROR: DATABASE_URL is not set. This script requires PostgreSQL.", file=sys.stderr)
        sys.exit(1)

    # Late imports so the script fails fast on missing DATABASE_URL.
    from modules.services.analytics_service import MediaAnalyticsService

    service = MediaAnalyticsService()

    storage_root = Path(args.storage_dir)

    # Jobs may live under storage/jobs/<uuid>/ or directly under storage/<uuid>/
    jobs_dir = storage_root / "jobs"
    if not jobs_dir.is_dir():
        # Fallback: jobs stored directly under storage root (Docker layout)
        jobs_dir = storage_root

    if not jobs_dir.is_dir():
        print(f"ERROR: Jobs directory not found: {jobs_dir}", file=sys.stderr)
        sys.exit(1)

    # Collect job directories to process.
    if args.job_id:
        job_dirs = [jobs_dir / args.job_id]
        if not job_dirs[0].is_dir():
            print(f"ERROR: Job directory not found: {job_dirs[0]}", file=sys.stderr)
            sys.exit(1)
    else:
        job_dirs = sorted(
            d for d in jobs_dir.iterdir()
            if d.is_dir() and (d / "metadata" / "job.json").is_file()
        )

    if args.verify:
        _verify(jobs_dir, job_dirs)
        return

    # Process jobs.
    processed = 0
    inserted = 0
    skipped = 0
    errors = 0

    for job_dir in job_dirs:
        meta = _load_job_metadata(job_dir)
        if meta is None:
            continue

        status = (meta.get("status") or "").lower()
        if status != "completed":
            skipped += 1
            continue

        job_id = meta.get("job_id") or job_dir.name
        job_type = meta.get("job_type") or "pipeline"
        generated_files = meta.get("generated_files") or {}
        chunks = generated_files.get("chunks")
        if not isinstance(chunks, list) or not chunks:
            skipped += 1
            continue

        # Enrich chunks that lack inline audioTracks.
        chunks = _enrich_chunks_from_disk(job_dir, chunks)

        # Resolve languages.
        request_payload = meta.get("request") or meta.get("request_payload") or {}
        result_payload = meta.get("result_payload") or meta.get("result") or {}

        # Build a simple namespace for _resolve_languages.
        class _FakeJob:
            pass

        fake = _FakeJob()
        fake.job_id = job_id
        fake.job_type = job_type
        fake.request_payload = request_payload
        fake.result_payload = result_payload
        fake.generated_files = {"chunks": chunks}

        input_lang, target_langs = service._resolve_languages(fake)
        entries = service._extract_audio_durations(
            {"chunks": chunks}, job_type, input_lang, target_langs
        )

        if not entries:
            skipped += 1
            continue

        processed += 1

        if args.dry_run:
            total_secs = sum(e.duration_seconds for e in entries)
            langs = ", ".join(sorted({e.language for e in entries}))
            print(f"  [DRY] {job_id} ({job_type}): {len(entries)} entries, "
                  f"{total_secs:.1f}s total, langs={langs}")
            inserted += len(entries)
            continue

        # Write to DB.
        from modules.database.engine import get_db_session
        from modules.database.models.analytics import MediaGenerationStatModel
        from sqlalchemy import and_, select

        with get_db_session() as session:
            for entry in entries:
                existing = session.execute(
                    select(MediaGenerationStatModel).where(
                        and_(
                            MediaGenerationStatModel.job_id == job_id,
                            MediaGenerationStatModel.language == entry.language,
                            MediaGenerationStatModel.track_kind == entry.track_kind,
                        )
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    continue
                session.add(
                    MediaGenerationStatModel(
                        job_id=job_id,
                        job_type=job_type,
                        language=entry.language,
                        track_kind=entry.track_kind,
                        duration_seconds=entry.duration_seconds,
                        sentence_count=entry.sentence_count,
                        chunk_count=entry.chunk_count,
                    )
                )
                inserted += 1

    mode = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{mode}Backfill complete:")
    print(f"  Jobs scanned:  {len(job_dirs)}")
    print(f"  Jobs processed: {processed}")
    print(f"  Rows inserted:  {inserted}")
    print(f"  Jobs skipped:   {skipped}")
    if errors:
        print(f"  Errors:         {errors}")


def _verify(jobs_dir: Path, job_dirs: list[Path]) -> None:
    """Compare completed job count vs media_generation_stats row count."""
    from modules.database.engine import get_db_session
    from modules.database.models.analytics import MediaGenerationStatModel
    from sqlalchemy import func, select

    completed = sum(
        1 for d in job_dirs
        if (meta := _load_job_metadata(d)) is not None
        and (meta.get("status") or "").lower() == "completed"
    )

    with get_db_session() as session:
        total_rows = session.execute(
            select(func.count()).select_from(MediaGenerationStatModel)
        ).scalar() or 0
        unique_jobs = session.execute(
            select(func.count(func.distinct(MediaGenerationStatModel.job_id)))
        ).scalar() or 0

    print(f"Completed jobs on disk:     {completed}")
    print(f"Unique jobs in stats table: {unique_jobs}")
    print(f"Total stats rows:           {total_rows}")

    if unique_jobs >= completed:
        print("\nAll completed jobs are accounted for.")
    else:
        print(f"\n{completed - unique_jobs} jobs still need backfilling.")


if __name__ == "__main__":
    main()
