"""Persistence layer for the Library feature."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

from .library_models import LibraryEntry, MetadataSnapshot

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class LibraryRepositoryError(RuntimeError):
    """Raised when low-level persistence operations fail."""


class LibraryRepository:
    """Encapsulate SQLite access and metadata persistence for library entries."""

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

    def list_entries(
        self,
        *,
        query: Optional[str] = None,
        filters: Mapping[str, Optional[str]] | None = None,
        limit: int = 25,
        offset: int = 0,
        sort_desc: bool = True,
    ) -> List[LibraryEntry]:
        join_sql, where_sql, params = self._compose_filters(query, filters or {})
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
        return [self._row_to_entry(row) for row in rows]

    def count_entries(
        self,
        *,
        query: Optional[str] = None,
        filters: Mapping[str, Optional[str]] | None = None,
    ) -> int:
        join_sql, where_sql, params = self._compose_filters(query, filters or {})
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

    def get_entry_by_id(self, entry_id: str) -> Optional[LibraryEntry]:
        with self.connect() as connection:
            cursor = connection.execute("SELECT * FROM library_items WHERE id = ?", (entry_id,))
            row = cursor.fetchone()
        return self._row_to_entry(row) if row else None

    def add_entry(self, entry: LibraryEntry) -> None:
        self._upsert(entry)

    def update_entry(self, entry_id: str, fields: Mapping[str, Any]) -> Optional[LibraryEntry]:
        existing = self.get_entry_by_id(entry_id)
        if existing is None:
            return None
        payload = existing.as_payload()

        def apply(field: str, key: str) -> None:
            if field in fields:
                value = fields.get(field)
                payload[key] = value

        apply("author", "author")
        apply("title", "book_title")
        apply("genre", "genre")
        apply("language", "language")
        apply("status", "status")
        payload["updated_at"] = fields.get("updated_at", payload["updated_at"])
        payload["cover_path"] = fields.get("cover_path", payload.get("cover_path"))
        payload["isbn"] = fields.get("isbn", payload.get("isbn"))
        payload["source_path"] = fields.get("source_path", payload.get("source_path"))
        metadata = fields.get("metadata")
        if isinstance(metadata, Mapping):
            payload["metadata"] = dict(metadata)

        updated_entry = LibraryEntry(
            id=payload["job_id"],
            author=payload["author"],
            book_title=payload["book_title"],
            genre=payload.get("genre"),
            language=payload["language"],
            status=payload["status"],
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
            library_path=payload["library_path"],
            cover_path=payload.get("cover_path"),
            isbn=payload.get("isbn"),
            source_path=payload.get("source_path"),
            metadata=MetadataSnapshot(metadata=payload.get("metadata", {})),
        )
        self._upsert(updated_entry)
        return updated_entry

    def delete_entry(self, entry_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM library_items WHERE id = ?", (entry_id,))
            connection.execute("DELETE FROM books WHERE id = ?", (entry_id,))

    def replace_entries(self, entries: Sequence[LibraryEntry]) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM library_items")
            connection.execute("DELETE FROM books")
            library_rows = [
                self._entry_to_db_row(entry)
                for entry in entries
            ]
            book_rows = [
                self._entry_to_book_row(entry)
                for entry in entries
            ]
            connection.executemany(
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

    def sync_from_filesystem(self, library_root: Optional[Path] = None) -> int:
        """Scan metadata files on disk and refresh the SQLite index."""

        root = Path(library_root) if library_root else self._library_root
        entries: List[LibraryEntry] = []
        state_dir = self._state_dir
        for metadata_file in root.rglob("job.json"):
            if metadata_file.parent.name != "metadata":
                continue
            if state_dir in metadata_file.parents:
                continue
            job_root = metadata_file.parent.parent
            try:
                metadata = self.load_metadata(job_root)
            except FileNotFoundError:
                continue
            entry = self._entry_from_metadata(metadata, job_root)
            if entry:
                entries.append(entry)

        self.replace_entries(entries)
        return len(entries)

    def load_metadata(self, job_root: Path) -> Dict[str, Any]:
        metadata_path = Path(job_root) / "metadata" / "job.json"
        text = metadata_path.read_text(encoding="utf-8")
        return json.loads(text)

    def write_metadata(self, job_root: Path, metadata: Mapping[str, Any]) -> None:
        metadata_dir = Path(job_root) / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True)
        (metadata_dir / "job.json").write_text(payload, encoding="utf-8")

    def iter_entries(self) -> Iterator[LibraryEntry]:
        with self.connect() as connection:
            cursor = connection.execute("SELECT * FROM library_items ORDER BY updated_at DESC")
            for row in cursor.fetchall():
                yield self._row_to_entry(row)

    def _entry_from_metadata(self, metadata: Mapping[str, Any], job_root: Path) -> Optional[LibraryEntry]:
        job_id = str(metadata.get("job_id") or "").strip()
        if not job_id:
            return None
        author = str(metadata.get("author") or "").strip()
        book_title = str(metadata.get("book_title") or "").strip()
        genre = metadata.get("genre")
        language = str(metadata.get("language") or "").strip()
        status = str(metadata.get("status") or "finished").strip()
        created_at = str(metadata.get("created_at") or "")
        updated_at = str(metadata.get("updated_at") or created_at)
        cover_path = metadata.get("job_cover_asset")
        isbn = metadata.get("isbn")
        source_path = metadata.get("source_path")

        snapshot = MetadataSnapshot(metadata=metadata)
        return LibraryEntry(
            id=job_id,
            author=author,
            book_title=book_title,
            genre=str(genre) if genre not in {None, ""} else None,
            language=language,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            library_path=str(Path(job_root).resolve()),
            cover_path=str(cover_path) if cover_path else None,
            isbn=str(isbn) if isbn else None,
            source_path=str(source_path) if source_path else None,
            metadata=snapshot,
        )

    def _compose_filters(
        self,
        query: Optional[str],
        filters: Mapping[str, Optional[str]],
    ) -> Tuple[str, str, Dict[str, Any]]:
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

    def _entry_to_db_row(self, entry: LibraryEntry) -> Dict[str, Any]:
        return {
            "id": entry.id,
            "author": entry.author,
            "book_title": entry.book_title,
            "genre": entry.genre,
            "language": entry.language,
            "status": entry.status,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "library_path": entry.library_path,
            "cover_path": entry.cover_path,
            "isbn": entry.isbn,
            "source_path": entry.source_path,
            "meta_json": entry.metadata.to_json(),
        }

    def _entry_to_book_row(self, entry: LibraryEntry) -> Dict[str, Any]:
        return {
            "id": entry.id,
            "title": entry.book_title,
            "author": entry.author,
            "genre": entry.genre,
            "language": entry.language,
            "cover_path": entry.cover_path,
            "isbn": entry.isbn,
            "source_path": entry.source_path,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
        }

    def _row_to_entry(self, row: sqlite3.Row) -> LibraryEntry:
        metadata_payload = row["meta_json"]
        snapshot = MetadataSnapshot(metadata=metadata_payload)
        return LibraryEntry(
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
            metadata=snapshot,
        )

    def _upsert(self, entry: LibraryEntry) -> None:
        payload = self._entry_to_db_row(entry)
        book_payload = self._entry_to_book_row(entry)
        with self.connect() as connection:
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

    def _apply_migrations(self, connection: sqlite3.Connection) -> None:
        connection.execute("PRAGMA foreign_keys = ON;")
        try:
            connection.execute("PRAGMA journal_mode = WAL;")
        except sqlite3.OperationalError:
            try:
                connection.execute("PRAGMA journal_mode = DELETE;")
            except sqlite3.OperationalError:
                pass
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
            normalized.append(f"{token}*")
    return " ".join(normalized)


__all__ = ["LibraryRepository", "LibraryRepositoryError"]
