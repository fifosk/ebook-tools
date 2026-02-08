"""PostgreSQL-backed user store implementation."""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Iterable, List, Optional

import bcrypt
from sqlalchemy import select

from ..database.engine import get_db_session
from ..database.models.user import UserModel
from .user_store_base import UserRecord, UserStoreBase

_log = logging.getLogger(__name__)


class PgUserStore(UserStoreBase):
    """Persist users in PostgreSQL using bcrypt password hashing."""

    def create_user(
        self,
        username: str,
        password: str,
        roles: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserRecord:
        with get_db_session() as session:
            existing = session.execute(
                select(UserModel).where(UserModel.username == username)
            ).scalar_one_or_none()
            if existing is not None:
                raise ValueError(f"User '{username}' already exists")

            model = UserModel(
                username=username,
                password_hash=self._hash_password(password),
                roles=list(roles or []),
                metadata_=dict(metadata or {}),
            )
            session.add(model)
            session.flush()
            return self._model_to_record(model)

    def get_user(self, username: str) -> Optional[UserRecord]:
        with get_db_session() as session:
            model = session.execute(
                select(UserModel).where(UserModel.username == username)
            ).scalar_one_or_none()
            if model is None:
                return None
            return self._model_to_record(model)

    def update_user(
        self,
        username: str,
        password: Optional[str] = None,
        roles: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserRecord:
        with get_db_session() as session:
            model = session.execute(
                select(UserModel).where(UserModel.username == username)
            ).scalar_one_or_none()
            if model is None:
                raise KeyError(f"User '{username}' not found")

            if password is not None:
                model.password_hash = self._hash_password(password)
            if roles is not None:
                model.roles = list(roles)
            if metadata is not None:
                model.metadata_ = dict(metadata)
            session.flush()
            return self._model_to_record(model)

    def delete_user(self, username: str) -> bool:
        with get_db_session() as session:
            model = session.execute(
                select(UserModel).where(UserModel.username == username)
            ).scalar_one_or_none()
            if model is None:
                return False
            session.delete(model)
            return True

    def list_users(self) -> List[UserRecord]:
        with get_db_session() as session:
            models = session.execute(select(UserModel)).scalars().all()
            return [self._model_to_record(m) for m in models]

    def verify_credentials(self, username: str, password: str) -> bool:
        record = self.get_user(username)
        if record is None:
            return False

        stored = record.password_hash
        pw = password.encode("utf-8")

        # Standard bcrypt hashes start with $2b$ or $2a$
        if stored.startswith(("$2b$", "$2a$")):
            return bcrypt.checkpw(pw, stored.encode("utf-8"))

        # Legacy SHA-256 shim: salt$hex_digest
        if "$" in stored:
            salt, digest = stored.split("$", 1)
            expected = hashlib.sha256(salt.encode("utf-8") + pw).hexdigest()
            if digest == expected:
                return True
        return False

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    @staticmethod
    def _model_to_record(model: UserModel) -> UserRecord:
        return UserRecord(
            username=model.username,
            password_hash=model.password_hash,
            roles=list(model.roles) if model.roles else [],
            metadata=dict(model.metadata_) if model.metadata_ else {},
        )
