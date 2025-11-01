#!/usr/bin/env python3
"""Lightweight migration helper for the library SQLite index."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from modules import config_manager as cfg  # noqa: E402
from modules.library.library_repository import LibraryRepository  # noqa: E402


def _column_exists(connection: sqlite3.Connection, table: str, column: str) -> bool:
    cursor = connection.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _add_column_if_missing(connection: sqlite3.Connection, table: str, column: str, definition: str) -> bool:
    if _column_exists(connection, table, column):
        return False
    connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    return True


def _coerce_metadata(meta_json: str | None) -> Dict[str, Any]:
    if not meta_json:
        return {}
    try:
        payload = json.loads(meta_json)
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _extract_isbn(metadata: Dict[str, Any]) -> str | None:
    def _normalize(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = "".join(ch for ch in value if ch.isdigit() or ch.upper() == "X")
        if len(cleaned) in {10, 13}:
            return cleaned.upper()
        return None

    candidates = [metadata.get("isbn")]
    book_metadata = metadata.get("book_metadata")
    if isinstance(book_metadata, dict):
        candidates.extend([
            book_metadata.get("isbn"),
            book_metadata.get("book_isbn"),
        ])
    for candidate in candidates:
        normalized = _normalize(candidate)
        if normalized:
            return normalized
    return None


def _extract_source_path(metadata: Dict[str, Any]) -> str | None:
    candidates = [
        metadata.get("source_path"),
        metadata.get("source_file"),
    ]
    book_metadata = metadata.get("book_metadata")
    if isinstance(book_metadata, dict):
        candidates.extend(
            [
                book_metadata.get("source_path"),
                book_metadata.get("source_file"),
                book_metadata.get("book_source_path"),
            ]
        )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def main() -> None:
    library_root = cfg.get_library_root(create=True)
    repository = LibraryRepository(library_root)

    with repository.connect() as connection:
        connection.row_factory = sqlite3.Row

        added_columns = []
        if _add_column_if_missing(connection, "library_items", "isbn", "TEXT"):
            added_columns.append("library_items.isbn")
        if _add_column_if_missing(connection, "library_items", "source_path", "TEXT"):
            added_columns.append("library_items.source_path")
        if _add_column_if_missing(connection, "books", "isbn", "TEXT"):
            added_columns.append("books.isbn")
        if _add_column_if_missing(connection, "books", "source_path", "TEXT"):
            added_columns.append("books.source_path")

        cursor = connection.execute("SELECT id, meta_json FROM library_items")
        rows = cursor.fetchall()

        for row in rows:
            metadata = _coerce_metadata(row["meta_json"])
            isbn = _extract_isbn(metadata)
            source_path = _extract_source_path(metadata)

            connection.execute(
                "UPDATE library_items SET isbn = COALESCE(?, isbn), source_path = COALESCE(?, source_path) WHERE id = ?",
                (isbn, source_path, row["id"]),
            )
            connection.execute(
                "UPDATE books SET isbn = COALESCE(?, isbn), source_path = COALESCE(?, source_path) WHERE id = ?",
                (isbn, source_path, row["id"]),
            )

        connection.commit()

    if added_columns:
        print("Added columns:", ", ".join(added_columns))
    else:
        print("Schema already up to date. No column changes applied.")


if __name__ == "__main__":
    main()
