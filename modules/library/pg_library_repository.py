"""PostgreSQL-backed library repository."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..database.engine import get_db_session
from ..database.models.library import (
    BookModel,
    LibraryItemGrantModel,
    LibraryItemModel,
)
from ..permissions import resolve_access_policy
from .library_models import LibraryEntry, MetadataSnapshot
from .library_repository import LibraryRepositoryError
from .sync import metadata as metadata_utils

logger = logging.getLogger(__name__).getChild("pg_library_repository")

UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}$"
)
FTS_TOKEN_PATTERN = re.compile(r"[\w]+(?:\*)?", flags=re.UNICODE)


class PgLibraryRepository:
    """Manage library entries in PostgreSQL with tsvector FTS."""

    def __init__(self, library_root: Path) -> None:
        self._library_root = Path(library_root)
        self._library_root.mkdir(parents=True, exist_ok=True)

    @property
    def db_path(self) -> Path:
        """Compatibility shim — returns library root (no SQLite file)."""
        return self._library_root

    def connect(self):
        """Compatibility shim — returns a DB session context manager."""
        return get_db_session()

    def list_entries(
        self,
        *,
        query: Optional[str] = None,
        filters: Mapping[str, Optional[str]] | None = None,
        limit: int = 25,
        offset: int = 0,
        sort_desc: bool = True,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> List[LibraryEntry]:
        stmt = select(LibraryItemModel)
        stmt = self._apply_search_filter(stmt, query)
        stmt = self._apply_field_filters(stmt, filters or {})
        stmt = self._apply_access_filter(stmt, user_id, user_role)

        if sort_desc:
            stmt = stmt.order_by(LibraryItemModel.updated_at.desc())
        else:
            stmt = stmt.order_by(LibraryItemModel.updated_at.asc())

        stmt = stmt.limit(limit).offset(offset)

        with get_db_session() as session:
            models = session.execute(stmt).scalars().all()
            return [self._model_to_entry(m) for m in models]

    def count_entries(
        self,
        *,
        query: Optional[str] = None,
        filters: Mapping[str, Optional[str]] | None = None,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(LibraryItemModel)
        stmt = self._apply_search_filter(stmt, query)
        stmt = self._apply_field_filters(stmt, filters or {})
        stmt = self._apply_access_filter(stmt, user_id, user_role)

        with get_db_session() as session:
            return session.execute(stmt).scalar_one()

    def get_entry_by_id(self, entry_id: str) -> Optional[LibraryEntry]:
        with get_db_session() as session:
            model = session.execute(
                select(LibraryItemModel).where(LibraryItemModel.id == entry_id)
            ).scalar_one_or_none()
            if model is None:
                return None
            return self._model_to_entry(model)

    def add_entry(self, entry: LibraryEntry) -> None:
        self._upsert(entry)

    def update_entry(
        self, entry_id: str, fields: Mapping[str, Any]
    ) -> Optional[LibraryEntry]:
        existing = self.get_entry_by_id(entry_id)
        if existing is None:
            return None
        payload = existing.as_payload()

        def apply(field: str, key: str) -> None:
            if field in fields:
                payload[key] = fields.get(field)

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
            item_type=payload.get("item_type") or "book",
            genre=payload.get("genre"),
            language=payload["language"],
            status=payload["status"],
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
            library_path=payload["library_path"],
            cover_path=payload.get("cover_path"),
            isbn=payload.get("isbn"),
            source_path=payload.get("source_path"),
            owner_id=payload.get("owner_id"),
            visibility=payload.get("visibility") or "public",
            metadata=MetadataSnapshot(metadata=payload.get("metadata", {})),
        )
        self._upsert(updated_entry)
        return updated_entry

    def delete_entry(self, entry_id: str) -> None:
        with get_db_session() as session:
            # CASCADE handles books and grants
            session.execute(
                delete(LibraryItemModel).where(LibraryItemModel.id == entry_id)
            )

    def replace_entries(self, entries: Sequence[LibraryEntry]) -> None:
        with get_db_session() as session:
            session.execute(delete(LibraryItemGrantModel))
            session.execute(delete(BookModel))
            session.execute(delete(LibraryItemModel))

            for entry in entries:
                item_model = self._entry_to_item_model(entry)
                session.add(item_model)

                book_model = self._entry_to_book_model(entry)
                session.add(book_model)

            session.flush()

            for entry in entries:
                policy = self._extract_access_policy(entry)
                self._write_grants(session, entry.id, policy)

    def sync_from_filesystem(self, library_root: Optional[Path] = None) -> int:
        """Scan metadata files on disk and refresh the PostgreSQL index."""
        root = Path(library_root) if library_root else self._library_root
        entries: List[LibraryEntry] = []
        for metadata_file in root.rglob("job.json"):
            if metadata_file.parent.name != "metadata":
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
        text_content = metadata_path.read_text(encoding="utf-8")
        return json.loads(text_content)

    def write_metadata(
        self, job_root: Path, metadata: Mapping[str, Any]
    ) -> None:
        metadata_dir = Path(job_root) / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True)
        (metadata_dir / "job.json").write_text(payload, encoding="utf-8")

    def iter_entries(self) -> Iterator[LibraryEntry]:
        with get_db_session() as session:
            models = (
                session.execute(
                    select(LibraryItemModel).order_by(
                        LibraryItemModel.updated_at.desc()
                    )
                )
                .scalars()
                .all()
            )
            for model in models:
                yield self._model_to_entry(model)

    # ------------------------------------------------------------------
    # Search & filtering
    # ------------------------------------------------------------------

    def _apply_search_filter(self, stmt, query: Optional[str]):
        """Apply FTS or exact-ID filter to a SQLAlchemy statement."""
        trimmed = (query or "").strip()
        if not trimmed:
            return stmt
        if UUID_PATTERN.match(trimmed):
            return stmt.where(LibraryItemModel.id == trimmed)
        tsquery = _build_pg_fts_query(trimmed)
        if tsquery:
            return stmt.where(
                LibraryItemModel.search_vector.op("@@")(
                    func.to_tsquery("simple", tsquery)
                )
            )
        return stmt

    @staticmethod
    def _apply_field_filters(stmt, filters: Mapping[str, Optional[str]]):
        """Apply exact-match column filters."""
        for field_name in (
            "author",
            "book_title",
            "genre",
            "language",
            "status",
            "item_type",
        ):
            value = filters.get(field_name)
            if value:
                stmt = stmt.where(
                    getattr(LibraryItemModel, field_name) == value
                )
        return stmt

    @staticmethod
    def _apply_access_filter(stmt, user_id: Optional[str], user_role: Optional[str]):
        """Apply visibility / ownership / grant-based access filter."""
        normalized_role = (user_role or "").strip().lower()
        normalized_user = (user_id or "").strip()

        if normalized_role == "admin":
            return stmt

        if not normalized_user and not normalized_role:
            return stmt.where(LibraryItemModel.visibility == "public")

        clauses = [LibraryItemModel.visibility == "public"]

        if normalized_user:
            clauses.append(LibraryItemModel.owner_id == normalized_user)
            clauses.append(
                LibraryItemModel.id.in_(
                    select(LibraryItemGrantModel.entry_id).where(
                        and_(
                            LibraryItemGrantModel.subject_type == "user",
                            LibraryItemGrantModel.subject_id == normalized_user,
                            LibraryItemGrantModel.permission.in_(["view", "edit"]),
                        )
                    )
                )
            )

        if normalized_role:
            clauses.append(
                LibraryItemModel.id.in_(
                    select(LibraryItemGrantModel.entry_id).where(
                        and_(
                            LibraryItemGrantModel.subject_type == "role",
                            LibraryItemGrantModel.subject_id == normalized_role,
                            LibraryItemGrantModel.permission.in_(["view", "edit"]),
                        )
                    )
                )
            )

        return stmt.where(or_(*clauses))

    # ------------------------------------------------------------------
    # Model ↔ entry conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _model_to_entry(model: LibraryItemModel) -> LibraryEntry:
        meta_json = model.meta_json if model.meta_json else {}
        snapshot = MetadataSnapshot(metadata=meta_json)
        return LibraryEntry(
            id=model.id,
            author=model.author or "",
            book_title=model.book_title or "",
            item_type=model.item_type or "book",
            genre=model.genre,
            language=model.language or "",
            status=model.status or "",
            created_at=str(model.created_at) if model.created_at else "",
            updated_at=str(model.updated_at) if model.updated_at else "",
            library_path=model.library_path,
            cover_path=model.cover_path,
            isbn=model.isbn,
            source_path=model.source_path,
            owner_id=model.owner_id,
            visibility=model.visibility or "public",
            metadata=snapshot,
        )

    @staticmethod
    def _entry_to_item_model(entry: LibraryEntry) -> LibraryItemModel:
        meta_json = (
            entry.metadata.data
            if isinstance(entry.metadata, MetadataSnapshot)
            else {}
        )
        return LibraryItemModel(
            id=entry.id,
            author=entry.author,
            book_title=entry.book_title,
            item_type=entry.item_type or "book",
            genre=entry.genre,
            language=entry.language,
            status=entry.status,
            created_at=entry.created_at or None,
            updated_at=entry.updated_at or None,
            library_path=entry.library_path,
            cover_path=entry.cover_path,
            isbn=entry.isbn,
            source_path=entry.source_path,
            owner_id=entry.owner_id,
            visibility=entry.visibility or "public",
            meta_json=meta_json,
        )

    @staticmethod
    def _entry_to_book_model(entry: LibraryEntry) -> BookModel:
        return BookModel(
            id=entry.id,
            title=entry.book_title,
            author=entry.author,
            genre=entry.genre,
            language=entry.language,
            cover_path=entry.cover_path,
            isbn=entry.isbn,
            source_path=entry.source_path,
            created_at=entry.created_at or None,
            updated_at=entry.updated_at or None,
        )

    def _upsert(self, entry: LibraryEntry) -> None:
        meta_json = (
            entry.metadata.data
            if isinstance(entry.metadata, MetadataSnapshot)
            else {}
        )

        with get_db_session() as session:
            # Upsert library_items
            item_values = {
                "id": entry.id,
                "author": entry.author,
                "book_title": entry.book_title,
                "item_type": entry.item_type or "book",
                "genre": entry.genre,
                "language": entry.language,
                "status": entry.status,
                "created_at": entry.created_at or None,
                "updated_at": entry.updated_at or None,
                "library_path": entry.library_path,
                "cover_path": entry.cover_path,
                "isbn": entry.isbn,
                "source_path": entry.source_path,
                "owner_id": entry.owner_id,
                "visibility": entry.visibility or "public",
                "meta_json": meta_json,
            }
            item_stmt = pg_insert(LibraryItemModel).values(**item_values)
            item_stmt = item_stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    k: item_stmt.excluded[k]
                    for k in item_values
                    if k != "id"
                },
            )
            session.execute(item_stmt)

            # Upsert books
            book_values = {
                "id": entry.id,
                "title": entry.book_title,
                "author": entry.author,
                "genre": entry.genre,
                "language": entry.language,
                "cover_path": entry.cover_path,
                "isbn": entry.isbn,
                "source_path": entry.source_path,
                "created_at": entry.created_at or None,
                "updated_at": entry.updated_at or None,
            }
            book_stmt = pg_insert(BookModel).values(**book_values)
            book_stmt = book_stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    k: book_stmt.excluded[k]
                    for k in book_values
                    if k != "id"
                },
            )
            session.execute(book_stmt)

            # Write grants
            policy = self._extract_access_policy(entry)
            self._write_grants(session, entry.id, policy)

    @staticmethod
    def _extract_access_policy(entry: LibraryEntry):
        metadata_payload = (
            dict(entry.metadata.data)
            if isinstance(entry.metadata, MetadataSnapshot)
            else dict(entry.metadata or {})
        )
        default_visibility = entry.visibility or "public"
        return resolve_access_policy(
            metadata_payload.get("access"), default_visibility=default_visibility
        )

    @staticmethod
    def _write_grants(session, entry_id: str, policy) -> None:
        session.execute(
            delete(LibraryItemGrantModel).where(
                LibraryItemGrantModel.entry_id == entry_id
            )
        )
        for grant in policy.grants:
            for permission in grant.permissions:
                session.add(
                    LibraryItemGrantModel(
                        entry_id=entry_id,
                        subject_type=grant.subject_type,
                        subject_id=grant.subject_id,
                        permission=permission,
                        granted_by=grant.granted_by,
                        granted_at=grant.granted_at,
                    )
                )

    def _entry_from_metadata(
        self, metadata: Mapping[str, Any], job_root: Path
    ) -> Optional[LibraryEntry]:
        job_id = str(metadata.get("job_id") or "").strip()
        if not job_id:
            return None
        owner_id = metadata.get("user_id") or metadata.get("owner_id")
        if isinstance(owner_id, str):
            owner_id = owner_id.strip() or None
        else:
            owner_id = None
        access_policy = resolve_access_policy(
            metadata.get("access"), default_visibility="public"
        )
        author = str(metadata.get("author") or "").strip()
        book_title = str(metadata.get("book_title") or "").strip()
        genre = metadata.get("genre")
        language = str(metadata.get("language") or "").strip()
        status = str(metadata.get("status") or "finished").strip()
        created_at = str(metadata.get("created_at") or "")
        updated_at = str(metadata.get("updated_at") or created_at)
        cover_path = metadata.get("job_cover_asset")
        item_type = metadata_utils.infer_item_type(metadata)
        isbn = metadata.get("isbn")
        source_path = metadata.get("source_path")

        snapshot = MetadataSnapshot(metadata=metadata)
        return LibraryEntry(
            id=job_id,
            author=author,
            book_title=book_title,
            item_type=item_type,
            genre=str(genre) if genre not in {None, ""} else None,
            language=language,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            library_path=str(Path(job_root).resolve()),
            cover_path=str(cover_path) if cover_path else None,
            isbn=str(isbn) if isbn else None,
            source_path=str(source_path) if source_path else None,
            owner_id=owner_id,
            visibility=access_policy.visibility,
            metadata=snapshot,
        )


def _build_pg_fts_query(raw: str) -> str:
    """Convert a raw search string to PostgreSQL tsquery syntax.

    SQLite FTS5 uses ``term*`` for prefix matching.
    PostgreSQL uses ``term:*`` with ``to_tsquery('simple', ...)``.
    Multiple tokens are AND-ed with ``&``.
    """
    tokens = [token.strip() for token in raw.split() if token.strip()]
    if not tokens:
        return ""
    normalized: list[str] = []
    for token in tokens:
        candidates = FTS_TOKEN_PATTERN.findall(token)
        for candidate in candidates:
            if not candidate:
                continue
            if candidate.endswith("*"):
                # Already has wildcard — convert to PG prefix syntax
                normalized.append(f"{candidate[:-1]}:*")
            else:
                normalized.append(f"{candidate}:*")
    return " & ".join(normalized).strip()


__all__ = ["PgLibraryRepository", "LibraryRepositoryError"]
