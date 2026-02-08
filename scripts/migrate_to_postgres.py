#!/usr/bin/env python3
"""One-time data migration from JSON/SQLite to PostgreSQL.

Usage:
    # Dry run (read-only, shows what would be migrated):
    python scripts/migrate_to_postgres.py --dry-run

    # Perform migration:
    python scripts/migrate_to_postgres.py

    # Verify migration counts:
    python scripts/migrate_to_postgres.py --verify

Requires DATABASE_URL environment variable to be set.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure the project root is on sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

os.environ.setdefault("DATABASE_URL", "")


def _require_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("ERROR: DATABASE_URL environment variable is required.")
        print("Example: DATABASE_URL=postgresql+psycopg2://ebook_tools:pw@localhost:5432/ebook_tools")
        sys.exit(1)
    return url


# ---------------------------------------------------------------------------
# Domain migration functions
# ---------------------------------------------------------------------------

def migrate_users(dry_run: bool) -> int:
    """Migrate users from JSON file to PostgreSQL."""
    from modules.user_management.local_user_store import LocalUserStore
    from modules.database.engine import get_db_session
    from modules.database.models.user import UserModel

    store = LocalUserStore()
    users = store.list_users()
    count = len(users)

    print(f"  Users found: {count}")
    if dry_run or count == 0:
        return count

    with get_db_session() as session:
        for user in users:
            from sqlalchemy import select
            existing = session.execute(
                select(UserModel).where(UserModel.username == user.username)
            ).scalar_one_or_none()
            if existing:
                print(f"    SKIP (exists): {user.username}")
                continue

            model = UserModel(
                username=user.username,
                password_hash=user.password_hash,
                roles=user.roles or [],
                metadata_=user.metadata or {},
            )
            session.add(model)
            print(f"    ADD: {user.username} (roles: {user.roles})")

    print(f"  Users migrated: {count}")
    return count


def migrate_sessions(dry_run: bool) -> int:
    """Migrate sessions from JSON file to PostgreSQL."""
    from modules.user_management.session_manager import SessionManager
    from modules.database.engine import get_db_session
    from modules.database.models.user import SessionModel, UserModel
    from sqlalchemy import select

    sm = SessionManager()
    sessions = sm._load()
    count = len(sessions)

    print(f"  Sessions found: {count}")
    if dry_run or count == 0:
        return count

    with get_db_session() as session:
        # Build a username → user_id map
        user_map = {}
        for model in session.execute(select(UserModel)).scalars().all():
            user_map[model.username] = model.id

        migrated = 0
        for token, data in sessions.items():
            username = data.get("username", "")
            user_id = user_map.get(username)
            if user_id is None:
                print(f"    SKIP (user not found): token for {username}")
                continue

            existing = session.execute(
                select(SessionModel).where(SessionModel.token == token)
            ).scalar_one_or_none()
            if existing:
                print(f"    SKIP (exists): token for {username}")
                continue

            created_at_str = data.get("created_at", "")
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except (ValueError, TypeError):
                created_at = datetime.now(timezone.utc)

            model = SessionModel(
                token=token,
                user_id=user_id,
                created_at=created_at,
            )
            session.add(model)
            migrated += 1
            print(f"    ADD: token for {username}")

    print(f"  Sessions migrated: {migrated}")
    return migrated


def migrate_library(dry_run: bool) -> int:
    """Migrate library from SQLite to PostgreSQL."""
    from modules.library.library_repository import LibraryRepository
    from modules.library.pg_library_repository import PgLibraryRepository
    from modules.config_manager.constants import DEFAULT_LIBRARY_ROOT

    library_root = Path(os.environ.get("EBOOK_LIBRARY_ROOT", str(DEFAULT_LIBRARY_ROOT)))
    if not library_root.exists():
        print(f"  Library root not found: {library_root}")
        return 0

    sqlite_repo = LibraryRepository(library_root)
    entries = list(sqlite_repo.iter_entries())
    count = len(entries)

    print(f"  Library entries found: {count}")
    if dry_run or count == 0:
        return count

    pg_repo = PgLibraryRepository(library_root)
    pg_repo.replace_entries(entries)

    print(f"  Library entries migrated: {count}")
    return count


def migrate_config(dry_run: bool) -> int:
    """Migrate config from SQLite to PostgreSQL."""
    from modules.config_manager.config_repository import ConfigRepository
    from modules.config_manager.pg_config_repository import PgConfigRepository

    try:
        sqlite_repo = ConfigRepository()
        sqlite_repo.connect().__enter__()
    except Exception as e:
        print(f"  Config DB not found or not accessible: {e}")
        return 0

    # Migrate snapshots
    try:
        snapshots, total = sqlite_repo.list_snapshots(limit=10000)
    except Exception:
        snapshots, total = [], 0

    print(f"  Config snapshots found: {total}")
    if dry_run:
        return total

    pg_repo = PgConfigRepository()

    for snap_meta in snapshots:
        result = sqlite_repo.get_snapshot(snap_meta.snapshot_id)
        if not result:
            continue
        meta, config = result
        try:
            pg_repo.save_snapshot(
                config,
                label=meta.label,
                description=meta.description,
                created_by=meta.created_by,
                source=meta.source,
                activate=meta.is_active,
            )
            print(f"    ADD snapshot: {meta.snapshot_id} ({meta.label or 'no label'})")
        except Exception as e:
            print(f"    ERROR snapshot {meta.snapshot_id}: {e}")

    # Migrate secrets (key paths only — values stay encrypted with same key)
    secret_keys = sqlite_repo.list_secrets()
    for key_path in secret_keys:
        secret_value = sqlite_repo.get_secret(key_path)
        if secret_value:
            try:
                pg_repo.store_secret(key_path, secret_value)
                print(f"    ADD secret: {key_path}")
            except Exception as e:
                print(f"    ERROR secret {key_path}: {e}")

    print(f"  Config snapshots migrated: {total}")
    return total


def migrate_bookmarks(dry_run: bool) -> int:
    """Migrate bookmarks from JSON files to PostgreSQL."""
    from modules.database.engine import get_db_session
    from modules.database.models.bookmark import BookmarkModel
    from modules.services.file_locator import FileLocator
    from sqlalchemy import select

    locator = FileLocator()
    storage_dir = locator.storage_root
    bookmarks_dir = storage_dir / "bookmarks"

    if not bookmarks_dir.exists():
        print("  Bookmarks directory not found")
        return 0

    total = 0
    for user_dir in bookmarks_dir.iterdir():
        if not user_dir.is_dir():
            continue
        user_id = user_dir.name
        for bookmark_file in user_dir.glob("*.json"):
            job_id = bookmark_file.stem
            try:
                data = json.loads(bookmark_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            entries = data.get("bookmarks", [])
            total += len(entries)

            if dry_run:
                continue

            with get_db_session() as session:
                for entry in entries:
                    bm_id = entry.get("id", "")
                    existing = session.execute(
                        select(BookmarkModel).where(
                            BookmarkModel.id == bm_id,
                            BookmarkModel.user_id == user_id,
                            BookmarkModel.job_id == job_id,
                        )
                    ).scalar_one_or_none()
                    if existing:
                        continue

                    model = BookmarkModel(
                        id=bm_id,
                        user_id=user_id,
                        job_id=job_id,
                        item_type=entry.get("item_type"),
                        kind=entry.get("kind", "time"),
                        created_at=entry.get("created_at", time.time()),
                        label=entry.get("label", "Bookmark"),
                        position=entry.get("position"),
                        sentence=entry.get("sentence"),
                        media_type=entry.get("media_type"),
                        media_id=entry.get("media_id"),
                        base_id=entry.get("base_id"),
                        segment_id=entry.get("segment_id"),
                        chunk_id=entry.get("chunk_id"),
                    )
                    session.add(model)

    print(f"  Bookmarks found: {total}")
    if not dry_run:
        print(f"  Bookmarks migrated: {total}")
    return total


def migrate_resume(dry_run: bool) -> int:
    """Migrate resume positions from JSON files to PostgreSQL."""
    from modules.database.engine import get_db_session
    from modules.database.models.resume import ResumePositionModel
    from modules.services.file_locator import FileLocator
    from sqlalchemy import select

    locator = FileLocator()
    storage_dir = locator.storage_root
    resume_dir = storage_dir / "resume"

    if not resume_dir.exists():
        print("  Resume directory not found")
        return 0

    total = 0
    for user_dir in resume_dir.iterdir():
        if not user_dir.is_dir():
            continue
        user_id = user_dir.name
        for resume_file in user_dir.glob("*.json"):
            job_id = resume_file.stem
            try:
                data = json.loads(resume_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            total += 1

            if dry_run:
                continue

            with get_db_session() as session:
                existing = session.execute(
                    select(ResumePositionModel).where(
                        ResumePositionModel.user_id == user_id,
                        ResumePositionModel.job_id == job_id,
                    )
                ).scalar_one_or_none()
                if existing:
                    continue

                model = ResumePositionModel(
                    user_id=user_id,
                    job_id=job_id,
                    kind=data.get("kind", "time"),
                    updated_at=data.get("updated_at", time.time()),
                    position=data.get("position"),
                    sentence=data.get("sentence"),
                    chunk_id=data.get("chunk_id"),
                    media_type=data.get("media_type"),
                    base_id=data.get("base_id"),
                )
                session.add(model)

    print(f"  Resume positions found: {total}")
    if not dry_run:
        print(f"  Resume positions migrated: {total}")
    return total


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

def verify_migration() -> None:
    """Compare source counts against PostgreSQL row counts."""
    from modules.database.engine import get_db_session
    from modules.database.models.user import UserModel, SessionModel
    from modules.database.models.library import LibraryItemModel
    from modules.database.models.config import ConfigSnapshotModel
    from modules.database.models.bookmark import BookmarkModel
    from modules.database.models.resume import ResumePositionModel
    from sqlalchemy import func, select

    print("\n--- Verification ---\n")

    with get_db_session() as session:
        users = session.execute(select(func.count()).select_from(UserModel)).scalar_one()
        sessions = session.execute(select(func.count()).select_from(SessionModel)).scalar_one()
        library = session.execute(select(func.count()).select_from(LibraryItemModel)).scalar_one()
        snapshots = session.execute(select(func.count()).select_from(ConfigSnapshotModel)).scalar_one()
        bookmarks = session.execute(select(func.count()).select_from(BookmarkModel)).scalar_one()
        resume = session.execute(select(func.count()).select_from(ResumePositionModel)).scalar_one()

    print(f"  Users:            {users}")
    print(f"  Sessions:         {sessions}")
    print(f"  Library items:    {library}")
    print(f"  Config snapshots: {snapshots}")
    print(f"  Bookmarks:        {bookmarks}")
    print(f"  Resume positions: {resume}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate ebook-tools data from JSON/SQLite to PostgreSQL"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration by comparing row counts",
    )
    args = parser.parse_args()

    _require_database_url()

    # Initialize the DB engine
    from modules.database.engine import get_engine
    get_engine()

    if args.verify:
        verify_migration()
        return

    mode = "DRY RUN" if args.dry_run else "MIGRATION"
    print(f"\n=== PostgreSQL Data Migration ({mode}) ===\n")

    start = time.time()

    print("[1/6] Migrating users...")
    migrate_users(args.dry_run)
    print()

    print("[2/6] Migrating sessions...")
    migrate_sessions(args.dry_run)
    print()

    print("[3/6] Migrating library...")
    migrate_library(args.dry_run)
    print()

    print("[4/6] Migrating config...")
    migrate_config(args.dry_run)
    print()

    print("[5/6] Migrating bookmarks...")
    migrate_bookmarks(args.dry_run)
    print()

    print("[6/6] Migrating resume positions...")
    migrate_resume(args.dry_run)
    print()

    elapsed = time.time() - start
    print(f"=== {mode} completed in {elapsed:.1f}s ===\n")

    if not args.dry_run:
        verify_migration()


if __name__ == "__main__":
    main()
