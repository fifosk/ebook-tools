"""PostgreSQL-backed resume service."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from sqlalchemy import and_, select

from ..database.engine import get_db_session
from ..database.models.resume import ResumePositionModel
from .resume_service import ResumeEntry

logger = logging.getLogger(__name__).getChild("pg_resume_service")


class PgResumeService:
    """Manage playback resume positions in PostgreSQL.

    Implements the same interface as :class:`ResumeService` (filesystem).
    """

    def get(self, job_id: str, user_id: str) -> Optional[ResumeEntry]:
        with get_db_session() as session:
            model = session.execute(
                select(ResumePositionModel).where(
                    and_(
                        ResumePositionModel.user_id == user_id,
                        ResumePositionModel.job_id == job_id,
                    )
                )
            ).scalar_one_or_none()
            if model is None:
                return None
            return self._model_to_entry(model, job_id=job_id)

    def save(self, job_id: str, user_id: str, data: Dict[str, Any]) -> ResumeEntry:
        kind = str(data.get("kind") or "time").strip().lower()
        if kind not in {"time", "sentence"}:
            kind = "time"
        now = data.get("updated_at") or time.time()
        try:
            now = float(now)
        except (TypeError, ValueError):
            now = time.time()

        position = self._coerce_float(data.get("position"))
        sentence = self._coerce_int(data.get("sentence"))
        chunk_id = self._coerce_string(data.get("chunk_id"))
        media_type = self._coerce_string(data.get("media_type"))
        base_id = self._coerce_string(data.get("base_id"))

        with get_db_session() as session:
            model = session.execute(
                select(ResumePositionModel).where(
                    and_(
                        ResumePositionModel.user_id == user_id,
                        ResumePositionModel.job_id == job_id,
                    )
                )
            ).scalar_one_or_none()

            if model is None:
                model = ResumePositionModel(
                    user_id=user_id,
                    job_id=job_id,
                    kind=kind,
                    updated_at=now,
                    position=position,
                    sentence=sentence,
                    chunk_id=chunk_id,
                    media_type=media_type,
                    base_id=base_id,
                )
                session.add(model)
            else:
                model.kind = kind
                model.updated_at = now
                model.position = position
                model.sentence = sentence
                model.chunk_id = chunk_id
                model.media_type = media_type
                model.base_id = base_id

            session.flush()
            return self._model_to_entry(model, job_id=job_id)

    def clear(self, job_id: str, user_id: str) -> bool:
        with get_db_session() as session:
            model = session.execute(
                select(ResumePositionModel).where(
                    and_(
                        ResumePositionModel.user_id == user_id,
                        ResumePositionModel.job_id == job_id,
                    )
                )
            ).scalar_one_or_none()
            if model is None:
                return False
            session.delete(model)
            return True

    @staticmethod
    def _model_to_entry(
        model: ResumePositionModel, *, job_id: str
    ) -> ResumeEntry:
        return ResumeEntry(
            job_id=job_id,
            kind=model.kind,
            updated_at=model.updated_at,
            position=model.position,
            sentence=model.sentence,
            chunk_id=model.chunk_id,
            media_type=model.media_type,
            base_id=model.base_id,
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
