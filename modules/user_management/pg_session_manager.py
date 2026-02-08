"""PostgreSQL-backed session manager."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

from sqlalchemy import delete, select

from ..database.engine import get_db_session
from ..database.models.user import SessionModel, UserModel

_log = logging.getLogger(__name__)


class PgSessionManager:
    """Manage session tokens in PostgreSQL."""

    def create_session(self, username: str) -> str:
        token = uuid4().hex
        with get_db_session() as session:
            user = session.execute(
                select(UserModel).where(UserModel.username == username)
            ).scalar_one_or_none()
            if user is None:
                raise KeyError(f"User '{username}' not found")

            model = SessionModel(
                token=token,
                user_id=user.id,
                created_at=datetime.now(timezone.utc),
            )
            session.add(model)
        return token

    def get_session(self, token: str) -> Optional[Dict[str, str]]:
        with get_db_session() as session:
            model = session.execute(
                select(SessionModel).where(SessionModel.token == token)
            ).scalar_one_or_none()
            if model is None:
                return None
            user = session.execute(
                select(UserModel).where(UserModel.id == model.user_id)
            ).scalar_one_or_none()
            username = user.username if user else "unknown"
            return {
                "username": username,
                "created_at": model.created_at.isoformat() if model.created_at else "",
            }

    def get_username(self, token: str) -> Optional[str]:
        data = self.get_session(token)
        if data:
            return data.get("username")
        return None

    def delete_session(self, token: str) -> bool:
        with get_db_session() as session:
            model = session.execute(
                select(SessionModel).where(SessionModel.token == token)
            ).scalar_one_or_none()
            if model is None:
                return False
            session.delete(model)
            return True

    def clear_sessions_for_user(self, username: str) -> int:
        with get_db_session() as session:
            user = session.execute(
                select(UserModel).where(UserModel.username == username)
            ).scalar_one_or_none()
            if user is None:
                return 0
            result = session.execute(
                delete(SessionModel).where(SessionModel.user_id == user.id)
            )
            return result.rowcount
