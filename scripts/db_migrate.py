"""Utility for triggering database migrations used by ebook-tools services."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules import config_manager as cfg
from modules.library.sqlite_indexer import LibraryIndexer


def migrate_library_index(library_root: Path) -> Path:
    """Ensure the library SQLite index is migrated to the latest schema."""

    indexer = LibraryIndexer(library_root)
    # Connecting once runs migrations thanks to the indexer bootstrap logic.
    with indexer.connect():
        pass
    return indexer.db_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply ebook-tools database migrations (currently library index only).",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--library-root",
        type=Path,
        help="Override the library root directory (defaults to configured library_root).",
    )
    args = parser.parse_args()

    try:
        library_root = args.library_root or cfg.get_library_root(create=True)
        library_root = Path(library_root).expanduser().resolve()
        db_path = migrate_library_index(library_root)
    except Exception as exc:  # pragma: no cover - command line usage
        print(f"[ERROR] Migration failed: {exc}", file=sys.stderr)
        return 1

    print(f"[OK] Library index migrations applied at {db_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
