"""Local filesystem-backed user store implementation."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional
import bcrypt

from .user_store_base import UserRecord, UserStoreBase

_log = logging.getLogger(__name__)


class LocalUserStore(UserStoreBase):
    """Persist users in a JSON file using bcrypt password hashing."""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self._storage_path = storage_path or Path("config/users/users.json")
        self._ensure_storage()

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def create_user(
        self,
        username: str,
        password: str,
        roles: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, object]] = None,
    ) -> UserRecord:
        users = self._load()
        if username in users:
            raise ValueError(f"User '{username}' already exists")

        record = UserRecord(
            username=username,
            password_hash=self._hash_password(password),
            roles=list(roles or []),
            metadata=dict(metadata or {}),
        )
        users[username] = record
        self._save(users)
        return record

    def get_user(self, username: str) -> Optional[UserRecord]:
        users = self._load()
        return users.get(username)

    def update_user(
        self,
        username: str,
        password: Optional[str] = None,
        roles: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, object]] = None,
    ) -> UserRecord:
        users = self._load()
        if username not in users:
            raise KeyError(f"User '{username}' not found")

        record = users[username]
        if password is not None:
            record.password_hash = self._hash_password(password)
        if roles is not None:
            record.roles = list(roles)
        if metadata is not None:
            record.metadata = dict(metadata)
        users[username] = record
        self._save(users)
        return record

    def delete_user(self, username: str) -> bool:
        users = self._load()
        if username not in users:
            return False
        del users[username]
        self._save(users)
        return True

    def list_users(self) -> List[UserRecord]:
        users = self._load()
        return list(users.values())

    def verify_credentials(self, username: str, password: str) -> bool:
        record = self.get_user(username)
        if record is None:
            return False

        stored = record.password_hash
        pw = password.encode("utf-8")

        # Standard bcrypt hashes start with $2b$ or $2a$
        if stored.startswith(("$2b$", "$2a$")):
            return bcrypt.checkpw(pw, stored.encode("utf-8"))

        # Legacy SHA-256 shim: salt$hex_digest (from local bcrypt/ shim)
        if "$" in stored:
            salt, digest = stored.split("$", 1)
            expected = hashlib.sha256(salt.encode("utf-8") + pw).hexdigest()
            if digest == expected:
                return True
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_storage(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._storage_path.exists():
            self._storage_path.write_text(json.dumps({"users": []}, indent=2), encoding="utf-8")

    def _load(self) -> Dict[str, UserRecord]:
        with self._storage_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        records = {}
        for item in data.get("users", []):
            record = UserRecord.from_dict(item)
            records[record.username] = record
        return records

    def _save(self, users: Dict[str, UserRecord]) -> None:
        payload = {"users": [record.to_dict() for record in users.values()]}
        with self._storage_path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
