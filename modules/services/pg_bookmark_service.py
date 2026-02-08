"""PostgreSQL-backed bookmark service."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, delete, func, select

from ..database.engine import get_db_session
from ..database.models.bookmark import BookmarkModel
from .bookmark_service import BookmarkEntry

logger = logging.getLogger(__name__).getChild("pg_bookmark_service")

MAX_BOOKMARKS_PER_JOB = 300


class PgBookmarkService:
    """Manage playback bookmarks in PostgreSQL.

    Implements the same interface as :class:`BookmarkService` (filesystem).
    """

    def __init__(self, *, max_bookmarks: int = MAX_BOOKMARKS_PER_JOB) -> None:
        self._max_bookmarks = max_bookmarks

    def list_bookmarks(self, job_id: str, user_id: str) -> List[BookmarkEntry]:
        with get_db_session() as session:
            models = (
                session.execute(
                    select(BookmarkModel)
                    .where(
                        and_(
                            BookmarkModel.user_id == user_id,
                            BookmarkModel.job_id == job_id,
                        )
                    )
                    .order_by(BookmarkModel.created_at.desc())
                )
                .scalars()
                .all()
            )
            return [self._model_to_entry(m) for m in models]

    def add_bookmark(self, job_id: str, user_id: str, entry: Dict[str, Any]) -> BookmarkEntry:
        entry_id = str(entry.get("id") or uuid.uuid4().hex)
        label = str(entry.get("label") or "").strip() or "Bookmark"
        kind = str(entry.get("kind") or "time").strip().lower()
        if kind not in {"time", "sentence"}:
            kind = "time"
        created_at = self._coerce_float(entry.get("created_at")) or time.time()
        position = self._coerce_float(entry.get("position"))
        sentence = self._coerce_int(entry.get("sentence"))
        media_type = self._coerce_string(entry.get("media_type"))
        media_id = self._coerce_string(entry.get("media_id"))
        base_id = self._coerce_string(entry.get("base_id"))
        segment_id = self._coerce_string(entry.get("segment_id"))
        chunk_id = self._coerce_string(entry.get("chunk_id"))
        item_type = self._coerce_string(entry.get("item_type"))

        with get_db_session() as session:
            # Check for existing bookmark with same id
            existing = session.execute(
                select(BookmarkModel).where(
                    and_(
                        BookmarkModel.id == entry_id,
                        BookmarkModel.user_id == user_id,
                        BookmarkModel.job_id == job_id,
                    )
                )
            ).scalar_one_or_none()

            if existing:
                # Update in place
                existing.item_type = item_type
                existing.kind = kind
                existing.label = label
                existing.position = position
                existing.sentence = sentence
                existing.media_type = media_type
                existing.media_id = media_id
                existing.base_id = base_id
                existing.segment_id = segment_id
                existing.chunk_id = chunk_id
                session.flush()
                return self._model_to_entry(existing)

            # Enforce max bookmarks per user/job
            count = session.execute(
                select(func.count())
                .select_from(BookmarkModel)
                .where(
                    and_(
                        BookmarkModel.user_id == user_id,
                        BookmarkModel.job_id == job_id,
                    )
                )
            ).scalar_one()

            if count >= self._max_bookmarks:
                oldest = (
                    session.execute(
                        select(BookmarkModel)
                        .where(
                            and_(
                                BookmarkModel.user_id == user_id,
                                BookmarkModel.job_id == job_id,
                            )
                        )
                        .order_by(BookmarkModel.created_at.asc())
                        .limit(1)
                    )
                    .scalar_one_or_none()
                )
                if oldest:
                    session.delete(oldest)

            model = BookmarkModel(
                id=entry_id,
                user_id=user_id,
                job_id=job_id,
                item_type=item_type,
                kind=kind,
                created_at=created_at,
                label=label,
                position=position,
                sentence=sentence,
                media_type=media_type,
                media_id=media_id,
                base_id=base_id,
                segment_id=segment_id,
                chunk_id=chunk_id,
            )
            session.add(model)
            session.flush()
            return self._model_to_entry(model)

    def remove_bookmark(self, job_id: str, user_id: str, bookmark_id: str) -> bool:
        with get_db_session() as session:
            result = session.execute(
                delete(BookmarkModel).where(
                    and_(
                        BookmarkModel.id == bookmark_id,
                        BookmarkModel.user_id == user_id,
                        BookmarkModel.job_id == job_id,
                    )
                )
            )
            return result.rowcount > 0

    @staticmethod
    def _model_to_entry(model: BookmarkModel) -> BookmarkEntry:
        return BookmarkEntry(
            id=model.id,
            job_id=model.job_id,
            item_type=model.item_type,
            kind=model.kind,
            created_at=model.created_at,
            label=model.label,
            position=model.position,
            sentence=model.sentence,
            media_type=model.media_type,
            media_id=model.media_id,
            base_id=model.base_id,
            segment_id=model.segment_id,
            chunk_id=model.chunk_id,
        )

    @staticmethod
    def _coerce_float(value: Any) -> Optional[float]:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return numeric if numeric >= 0 else 0.0

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return None
        return numeric if numeric > 0 else None

    @staticmethod
    def _coerce_string(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        trimmed = value.strip()
        return trimmed or None
