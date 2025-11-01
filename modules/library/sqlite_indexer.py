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
    cover_path: Optional[str] = None
    isbn: Optional[str] = None
    source_path: Optional[str] = None

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
            cover_path=row["cover_path"] if "cover_path" in row.keys() else None,
            isbn=row["isbn"] if "isbn" in row.keys() else None,
            source_path=row["source_path"] if "source_path" in row.keys() else None,
            meta_json=row["meta_json"],
        )


@dataclass(frozen=True)
class LibraryBookRecord:
    """Structured representation of metadata stored in the ``books`` table."""

    id: str
    title: str
    author: str
    genre: Optional[str]
    language: str
    cover_path: Optional[str]
    created_at: str
    updated_at: str
    isbn: Optional[str] = None
    source_path: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "LibraryBookRecord":
        return cls(
            id=row["id"],
            title=row["title"] or "",
            author=row["author"] or "",
            genre=row["genre"],
            language=row["language"] or "",
            cover_path=row["cover_path"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            isbn=row["isbn"] if "isbn" in row.keys() else None,
            source_path=row["source_path"] if "source_path" in row.keys() else None,
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
        try:
            connection.execute("PRAGMA journal_mode = WAL;")
        except sqlite3.OperationalError:
            connection.execute("PRAGMA journal_mode = DELETE;")
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
            payload = {
                "id": item.id,
                "author": item.author,
                "book_title": item.book_title,
                "genre": item.genre,
                "language": item.language,
                "status": item.status,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "library_path": item.library_path,
                "cover_path": item.cover_path,
                 "isbn": item.isbn,
                 "source_path": item.source_path,
                "meta_json": item.meta_json,
            }
            connection.execute(
                """
                INSERT INTO library_items (
                    id, author, book_title, genre, language, status,
                    created_at, updated_at, library_path, cover_path,
                    isbn, source_path, meta_json
                )
                VALUES (
                    :id, :author, :book_title, :genre, :language, :status,
                    :created_at, :updated_at, :library_path, :cover_path,
                    :isbn, :source_path, :meta_json
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
                    cover_path=excluded.cover_path,
                    isbn=excluded.isbn,
                    source_path=excluded.source_path,
                    meta_json=excluded.meta_json;
                """,
                payload,
            )
            book_payload = {
                "id": item.id,
                "title": item.book_title,
                "author": item.author,
                "genre": item.genre,
                "language": item.language,
                "cover_path": item.cover_path,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "isbn": item.isbn,
                "source_path": item.source_path,
            }
            connection.execute(
                """
                INSERT INTO books (
                    id, title, author, genre, language, cover_path, isbn, source_path, created_at, updated_at
                )
                VALUES (
                    :id, :title, :author, :genre, :language, :cover_path, :isbn, :source_path, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    author=excluded.author,
                    genre=excluded.genre,
                    language=excluded.language,
                    cover_path=excluded.cover_path,
                    isbn=excluded.isbn,
                    source_path=excluded.source_path,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at;
                """,
                book_payload,
            )

    def delete(self, job_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM library_items WHERE id = ?", (job_id,))
            connection.execute("DELETE FROM books WHERE id = ?", (job_id,))

    def get(self, job_id: str) -> Optional[LibraryItem]:
        with self.connect() as connection:
            cursor = connection.execute("SELECT * FROM library_items WHERE id = ?", (job_id,))
            row = cursor.fetchone()
        return LibraryItem.from_row(row) if row else None

    def get_book(self, job_id: str) -> Optional[LibraryBookRecord]:
        with self.connect() as connection:
            cursor = connection.execute("SELECT * FROM books WHERE id = ?", (job_id,))
            row = cursor.fetchone()
        return LibraryBookRecord.from_row(row) if row else None

    def update_book_metadata(
        self,
        job_id: str,
        *,
        title: str,
        author: str,
        genre: Optional[str],
        language: str,
        cover_path: Optional[str],
        created_at: str,
        updated_at: str,
        isbn: Optional[str] = None,
        source_path: Optional[str] = None,
    ) -> None:
        payload = {
            "id": job_id,
            "title": title,
            "author": author,
            "genre": genre,
            "language": language,
            "cover_path": cover_path,
            "created_at": created_at,
            "updated_at": updated_at,
            "isbn": isbn,
            "source_path": source_path,
        }
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE library_items
                SET author=:author,
                    book_title=:title,
                    genre=:genre,
                    language=:language,
                    cover_path=:cover_path,
                    isbn=:isbn,
                    source_path=:source_path,
                    updated_at=:updated_at
                WHERE id=:id
                """,
                payload,
            )
            connection.execute(
                """
                INSERT INTO books (
                    id, title, author, genre, language, cover_path, isbn, source_path, created_at, updated_at
                )
                VALUES (
                    :id, :title, :author, :genre, :language, :cover_path, :isbn, :source_path, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    author=excluded.author,
                    genre=excluded.genre,
                    language=excluded.language,
                    cover_path=excluded.cover_path,
                    isbn=excluded.isbn,
                    source_path=excluded.source_path,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at;
                """,
                payload,
            )

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
            connection.execute("DELETE FROM books")
            library_rows = [
                {
                    "id": item.id,
                    "author": item.author,
                    "book_title": item.book_title,
                    "genre": item.genre,
                    "language": item.language,
                    "status": item.status,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                    "library_path": item.library_path,
                    "cover_path": item.cover_path,
                    "isbn": item.isbn,
                    "source_path": item.source_path,
                    "meta_json": item.meta_json,
                }
                for item in items
            ]
            book_rows = [
                {
                    "id": item.id,
                    "title": item.book_title,
                    "author": item.author,
                    "genre": item.genre,
                    "language": item.language,
                    "cover_path": item.cover_path,
                    "isbn": item.isbn,
                    "source_path": item.source_path,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                }
                for item in items
            ]
            connection.executemany(
                """
                INSERT INTO library_items (
                    id, author, book_title, genre, language, status,
                    created_at, updated_at, library_path, cover_path, isbn, source_path, meta_json
                ) VALUES (
                    :id, :author, :book_title, :genre, :language, :status,
                    :created_at, :updated_at, :library_path, :cover_path, :isbn, :source_path, :meta_json
                )
                """,
                library_rows,
            )
            connection.executemany(
                """
                INSERT INTO books (
                    id, title, author, genre, language, cover_path, isbn, source_path, created_at, updated_at
                )
                VALUES (
                    :id, :title, :author, :genre, :language, :cover_path, :isbn, :source_path, :created_at, :updated_at
                )
                """,
                book_rows,
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
