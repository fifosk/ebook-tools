"""Persistence service for reusable cross-surface creation templates."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .file_locator import FileLocator
from .pipeline_payload_normalization import normalize_discovery_identifiers
from .. import logging_manager


logger = logging_manager.get_logger().getChild("creation_template_service")

_ALLOWED_FRAGMENT_CHARS = {
    *"abcdefghijklmnopqrstuvwxyz",
    *"ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    *"0123456789",
    "-",
    "_",
}
_DEFAULT_MODE = "generated_book"
_MODE_ALIASES = {
    "book": "generated_book",
    "book_job": "generated_book",
    "generated": "generated_book",
    "generatedbook": "generated_book",
    "generated_book": "generated_book",
    "generated-book": "generated_book",
    "narrate": "narrate_ebook",
    "narrateebook": "narrate_ebook",
    "narrate_ebook": "narrate_ebook",
    "narrate-ebook": "narrate_ebook",
    "pipeline": "narrate_ebook",
    "subtitle": "subtitle_job",
    "subtitlejob": "subtitle_job",
    "subtitle_job": "subtitle_job",
    "subtitle-job": "subtitle_job",
    "youtube": "youtube_dub",
    "youtubedub": "youtube_dub",
    "youtube_dub": "youtube_dub",
    "youtube-dub": "youtube_dub",
}
_SENSITIVE_KEY_MARKERS = (
    "password",
    "secret",
    "token",
    "authorization",
    "authheader",
    "apikey",
    "api_key",
    "bearer",
    "cookie",
    "credential",
    "csrf",
    "jwt",
    "privatekey",
    "private_key",
    "sessioncookie",
)


def _sanitize_fragment(value: str, fallback: str) -> str:
    if not value:
        return fallback
    sanitized = [ch if ch in _ALLOWED_FRAGMENT_CHARS else "_" for ch in value]
    result = "".join(sanitized).strip("._")
    return result or fallback


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    tmp_path.replace(path)


def normalize_creation_template_filter_mode(value: str | None) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().replace(" ", "_")
    if not normalized:
        return None
    key = normalized.replace("_", "").replace("-", "").lower()
    if key in _MODE_ALIASES:
        return _MODE_ALIASES[key]
    return _MODE_ALIASES.get(normalized.lower())


@dataclass(frozen=True)
class CreationTemplateEntry:
    id: str
    name: str
    mode: str
    created_at: float
    updated_at: float
    payload: Dict[str, Any]


class CreationTemplateService:
    """Store reusable create-job settings without device-local secrets."""

    def __init__(
        self,
        *,
        file_locator: Optional[FileLocator] = None,
        max_entries: int = 100,
    ) -> None:
        self._file_locator = file_locator or FileLocator()
        self._max_entries = max_entries

    def list_templates(
        self,
        user_id: str,
        *,
        mode: Optional[str] = None,
    ) -> List[CreationTemplateEntry]:
        if mode and mode.strip():
            normalized_mode = self._normalize_filter_mode(mode)
            if normalized_mode is None:
                return []
        else:
            normalized_mode = None

        entries = self._load_entries(user_id)
        if normalized_mode:
            entries = [entry for entry in entries if entry.mode == normalized_mode]
        entries.sort(key=lambda entry: entry.updated_at, reverse=True)
        return entries

    def get_template(
        self,
        user_id: str,
        template_id: str,
    ) -> Optional[CreationTemplateEntry]:
        safe_id = self.canonical_template_id(template_id)
        if not safe_id:
            return None
        for entry in self._load_entries(user_id):
            if entry.id == safe_id:
                return entry
        return None

    def save_template(self, user_id: str, entry: Dict[str, Any]) -> CreationTemplateEntry:
        entries = self._load_entries(user_id)
        normalized = self._normalize_incoming(entry)
        replaced = False
        next_entries: List[CreationTemplateEntry] = []
        for existing in entries:
            if existing.id == normalized.id:
                normalized = CreationTemplateEntry(
                    id=normalized.id,
                    name=normalized.name,
                    mode=normalized.mode,
                    created_at=existing.created_at,
                    updated_at=normalized.updated_at,
                    payload=normalized.payload,
                )
                next_entries.append(normalized)
                replaced = True
            else:
                next_entries.append(existing)

        if not replaced:
            next_entries.append(normalized)

        next_entries.sort(key=lambda item: item.updated_at, reverse=True)
        if len(next_entries) > self._max_entries:
            next_entries = next_entries[: self._max_entries]
        self._persist(user_id, next_entries)
        return normalized

    def delete_template(self, user_id: str, template_id: str) -> bool:
        safe_id = self.canonical_template_id(template_id)
        if not safe_id:
            return False
        entries = self._load_entries(user_id)
        next_entries = [entry for entry in entries if entry.id != safe_id]
        if len(next_entries) == len(entries):
            return False
        self._persist(user_id, next_entries)
        return True

    @staticmethod
    def canonical_template_id(template_id: str) -> str:
        return _sanitize_fragment(template_id, "")

    def _persist(self, user_id: str, entries: Iterable[CreationTemplateEntry]) -> None:
        payload = {
            "version": 1,
            "user_id": user_id,
            "updated_at": time.time(),
            "templates": [self._serialize(entry) for entry in entries],
        }
        _atomic_write_json(self._user_path(user_id), payload)

    def _load_entries(self, user_id: str) -> List[CreationTemplateEntry]:
        payload = self._load_payload(user_id)
        raw_entries = payload.get("templates")
        if not isinstance(raw_entries, list):
            logger.warning("Creation templates storage could not be loaded; returning empty list")
            return []
        entries: List[CreationTemplateEntry] = []
        for entry in raw_entries:
            if isinstance(entry, dict):
                entries.append(self._normalize_incoming(entry))
        return entries

    def _load_payload(self, user_id: str) -> Dict[str, Any]:
        path = self._user_path(user_id)
        if not path.exists():
            return {"version": 1, "user_id": user_id, "templates": []}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Creation templates storage could not be loaded; returning empty list")
            return {"version": 1, "user_id": user_id, "templates": []}
        if not isinstance(payload, dict):
            logger.warning("Creation templates storage could not be loaded; returning empty list")
            return {"version": 1, "user_id": user_id, "templates": []}
        return payload

    def _normalize_incoming(self, entry: Dict[str, Any]) -> CreationTemplateEntry:
        now = time.time()
        entry_id = _sanitize_fragment(str(entry.get("id") or uuid.uuid4()), "template")
        name = str(entry.get("name") or "").strip() or "Untitled template"
        mode = self._normalize_mode(str(entry.get("mode") or ""))
        created_at = self._coerce_float(entry.get("created_at")) or now
        updated_at = self._coerce_float(entry.get("updated_at")) or now
        payload = self._sanitize_payload(entry.get("payload"))
        return CreationTemplateEntry(
            id=entry_id,
            name=name,
            mode=mode,
            created_at=created_at,
            updated_at=updated_at,
            payload=payload,
        )

    def _user_path(self, user_id: str) -> Path:
        user_fragment = _sanitize_fragment(user_id, "user")
        return (
            self._file_locator.storage_root
            / "creation_templates"
            / f"{user_fragment}.json"
        )

    @staticmethod
    def _serialize(entry: CreationTemplateEntry) -> Dict[str, Any]:
        return {
            "id": entry.id,
            "name": entry.name,
            "mode": entry.mode,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "payload": entry.payload,
        }

    @staticmethod
    def _normalize_mode(value: str) -> str:
        normalized = value.strip().replace(" ", "_")
        key = normalized.replace("_", "").replace("-", "").lower()
        if key in _MODE_ALIASES:
            return _MODE_ALIASES[key]
        return _MODE_ALIASES.get(normalized.lower(), _DEFAULT_MODE)

    @staticmethod
    def _normalize_filter_mode(value: str) -> Optional[str]:
        return normalize_creation_template_filter_mode(value)

    @classmethod
    def _sanitize_payload(cls, value: Any) -> Dict[str, Any]:
        sanitized = cls._sanitize_value(value)
        if not isinstance(sanitized, dict):
            return {}
        return normalize_discovery_identifiers(sanitized)

    @classmethod
    def _sanitize_value(cls, value: Any) -> Any:
        if isinstance(value, dict):
            result: Dict[str, Any] = {}
            for key, child in value.items():
                key_text = str(key)
                if cls._is_sensitive_key(key_text):
                    continue
                result[key_text] = cls._sanitize_value(child)
            return result
        if isinstance(value, list):
            return [cls._sanitize_value(child) for child in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    @staticmethod
    def _is_sensitive_key(key: str) -> bool:
        normalized = key.replace("-", "").replace("_", "").lower()
        return any(
            marker.replace("_", "") in normalized
            for marker in _SENSITIVE_KEY_MARKERS
        )

    @staticmethod
    def _coerce_float(value: Any) -> Optional[float]:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return numeric if numeric >= 0 else None
