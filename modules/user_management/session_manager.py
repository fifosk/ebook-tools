"""Lightweight session token management."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4


class SessionManager:
    """Persist session tokens in a JSON file."""

    def __init__(self, session_file: Optional[Path] = None) -> None:
        default_path = Path(os.path.expanduser("~/.ebooktools_session.json"))
        self._session_file = session_file or default_path
        self._ensure_storage()

    def create_session(self, username: str) -> str:
        token = uuid4().hex
        sessions = self._load()
        sessions[token] = {
            "username": username,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save(sessions)
        return token

    def get_session(self, token: str) -> Optional[Dict[str, str]]:
        sessions = self._load()
        return sessions.get(token)

    def get_username(self, token: str) -> Optional[str]:
        session = self.get_session(token)
        if session:
            return session.get("username")
        return None

    def delete_session(self, token: str) -> bool:
        sessions = self._load()
        if token not in sessions:
            return False
        del sessions[token]
        self._save(sessions)
        return True

    def clear_sessions_for_user(self, username: str) -> int:
        sessions = self._load()
        to_remove = [token for token, data in sessions.items() if data.get("username") == username]
        for token in to_remove:
            del sessions[token]
        if to_remove:
            self._save(sessions)
        return len(to_remove)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_storage(self) -> None:
        self._session_file.parent.mkdir(parents=True, exist_ok=True)
        if not self._session_file.exists():
            self._session_file.write_text(json.dumps({"sessions": {}}, indent=2), encoding="utf-8")

    def _load(self) -> Dict[str, Dict[str, str]]:
        with self._session_file.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return dict(data.get("sessions", {}))

    def _save(self, sessions: Dict[str, Dict[str, str]]) -> None:
        payload = {"sessions": sessions}
        with self._session_file.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
