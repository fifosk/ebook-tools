"""SQLite-backed indexing helpers for the Library feature."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


@dataclass(frozen=True)
class LibraryItem:
    """In-memory representation of a Library index row."""

    id: str
    author: str
    book_title: str
    genre: Optional[str]
    language: str
    status: str
    created_at: str
    updated_at: str
    library_path: str
    meta_json: str

    @property
    def metadata(self) -> Dict[str, Any]:
        try:
            return json.loads(self.meta_json)
        except (TypeError, json.JSONDecodeError):
            return {}

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "LibraryItem":
        return cls(
            id=row["id"],
            author=row["author"] or "",
            book_title=row["book_title"] or "",
            genre=row["genre"],
            language=row["language"] or "",
            status=row["status"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            library_path=row["library_path"],
            meta_json=row["meta_json"],
        )


class LibraryIndexer:
    """Manage the SQLite index for Library items."""

    def __init__(self, library_root: Path) -> None:
        self._library_root = Path(library_root)
        self._library_root.mkdir(parents=True, exist_ok=True)
        self._state_dir = self._library_root / ".library"
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._state_dir / "library.db"

    @property
    def db_path(self) -> Path:
        return self._db_path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self._db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        connection.row_factory = sqlite3.Row
        self._apply_migrations(connection)
        return connection

    def _apply_migrations(self, connection: sqlite3.Connection) -> None:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("PRAGMA journal_mode = WAL;")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
        )
        applied = {
            row["version"]
            for row in connection.execute("SELECT version FROM schema_migrations")
        }

        for path in _sorted_migrations():
            version = int(path.stem.split("_", 1)[0])
            if version in applied:
                continue
            script = path.read_text(encoding="utf-8")
            connection.executescript(script)
            connection.execute(
                "INSERT OR REPLACE INTO schema_migrations (version) VALUES (?)", (version,)
            )

        connection.commit()

    def upsert(self, item: LibraryItem) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO library_items (
                    id, author, book_title, genre, language, status,
                    created_at, updated_at, library_path, meta_json
                )
                VALUES (
                    :id, :author, :book_title, :genre, :language, :status,
                    :created_at, :updated_at, :library_path, :meta_json
                )
                ON CONFLICT(id) DO UPDATE SET
                    author=excluded.author,
                    book_title=excluded.book_title,
                    genre=excluded.genre,
                    language=excluded.language,
                    status=excluded.status,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    library_path=excluded.library_path,
                    meta_json=excluded.meta_json;
                """,
                item.__dict__,
            )

    def delete(self, job_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM library_items WHERE id = ?", (job_id,))

    def get(self, job_id: str) -> Optional[LibraryItem]:
        with self.connect() as connection:
            cursor = connection.execute("SELECT * FROM library_items WHERE id = ?", (job_id,))
            row = cursor.fetchone()
        return LibraryItem.from_row(row) if row else None

    def iter_all(self) -> Iterator[LibraryItem]:
        with self.connect() as connection:
            cursor = connection.execute("SELECT * FROM library_items ORDER BY updated_at DESC")
            rows = cursor.fetchall()
        for row in rows:
            yield LibraryItem.from_row(row)

    def _compose_filters(
        self,
        query: Optional[str],
        filters: Dict[str, str],
    ) -> tuple[str, str, Dict[str, Any]]:
        joins: List[str] = []
        where_clauses: List[str] = []
        params: Dict[str, Any] = {}

        normalized_query = _build_fts_query(query or "")
        if normalized_query:
            joins.append(
                "JOIN library_items_fts ON library_items.rowid = library_items_fts.rowid"
            )
            params["fts_query"] = normalized_query
            where_clauses.append("library_items_fts MATCH :fts_query")

        for field in ("author", "book_title", "genre", "language", "status"):
            value = filters.get(field)
            if value:
                params[field] = value
                where_clauses.append(f"library_items.{field} = :{field}")

        join_sql = " ".join(joins)
        where_sql = " AND ".join(where_clauses)
        return join_sql, where_sql, params

    def search(
        self,
        *,
        query: Optional[str],
        filters: Dict[str, str],
        limit: int,
        offset: int,
        sort_desc: bool = True,
    ) -> List[LibraryItem]:
        join_sql, where_sql, params = self._compose_filters(query, filters)
        order_clause = (
            "ORDER BY library_items.updated_at DESC"
            if sort_desc
            else "ORDER BY library_items.updated_at ASC"
        )
        where_prefix = f"WHERE {where_sql}" if where_sql else ""

        sql = f"""
            SELECT library_items.*
            FROM library_items
            {join_sql}
            {where_prefix}
            {order_clause}
            LIMIT :limit OFFSET :offset
        """
        query_params = dict(params)
        query_params.update({"limit": limit, "offset": offset})

        with self.connect() as connection:
            cursor = connection.execute(sql, query_params)
            rows = cursor.fetchall()
        return [LibraryItem.from_row(row) for row in rows]

    def count(self, *, query: Optional[str], filters: Dict[str, str]) -> int:
        join_sql, where_sql, params = self._compose_filters(query, filters)
        where_prefix = f"WHERE {where_sql}" if where_sql else ""
        sql = f"""
            SELECT COUNT(*) AS total
            FROM library_items
            {join_sql}
            {where_prefix}
        """
        with self.connect() as connection:
            cursor = connection.execute(sql, params)
            row = cursor.fetchone()
        return int(row["total"]) if row and row["total"] is not None else 0

    def replace_all(self, items: Sequence[LibraryItem]) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM library_items")
            connection.executemany(
                """
                INSERT INTO library_items (
                    id, author, book_title, genre, language, status,
                    created_at, updated_at, library_path, meta_json
                ) VALUES (
                    :id, :author, :book_title, :genre, :language, :status,
                    :created_at, :updated_at, :library_path, :meta_json
                )
                """,
                [item.__dict__ for item in items],
            )


def _sorted_migrations() -> List[Path]:
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(
        (path for path in MIGRATIONS_DIR.iterdir() if path.suffix == ".sql"),
        key=lambda path: path.stem,
    )


def _build_fts_query(raw: str) -> str:
    tokens = [token.strip() for token in raw.split() if token.strip()]
    if not tokens:
        return ""
    normalized = []
    for token in tokens:
        if token.endswith("*"):
            normalized.append(token)
        else:
            normalized.append(f'{token}*')
    return " ".join(normalized)
