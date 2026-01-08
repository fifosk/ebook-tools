"""Persistence service for per-user playback bookmarks."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .file_locator import FileLocator
from .. import logging_manager


logger = logging_manager.get_logger().getChild("bookmark_service")

_ALLOWED_FRAGMENT_CHARS = {
    *"abcdefghijklmnopqrstuvwxyz",
    *"ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    *"0123456789",
    "-",
    "_",
}


def _sanitize_fragment(value: str, fallback: str) -> str:
    if not value:
        return fallback
    sanitized = [ch if ch in _ALLOWED_FRAGMENT_CHARS else "_" for ch in value]
    result = "".join(sanitized).strip("._")
    return result or fallback


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


@dataclass(frozen=True)
class BookmarkEntry:
    id: str
    job_id: str
    item_type: Optional[str]
    kind: str
    created_at: float
    label: str
    position: Optional[float]
    sentence: Optional[int]
    media_type: Optional[str]
    media_id: Optional[str]
    base_id: Optional[str]
    segment_id: Optional[str]
    chunk_id: Optional[str]


class BookmarkService:
    def __init__(
        self,
        *,
        file_locator: Optional[FileLocator] = None,
        max_entries: int = 300,
    ) -> None:
        self._file_locator = file_locator or FileLocator()
        self._max_entries = max_entries

    def list_bookmarks(self, job_id: str, user_id: str) -> List[BookmarkEntry]:
        payload = self._load_payload(job_id, user_id)
        entries = self._normalize_entries(payload.get("bookmarks"))
        entries.sort(key=lambda entry: entry.created_at, reverse=True)
        return entries

    def add_bookmark(self, job_id: str, user_id: str, entry: Dict[str, Any]) -> BookmarkEntry:
        payload = self._load_payload(job_id, user_id)
        bookmarks = self._normalize_entries(payload.get("bookmarks"))
        normalized = self._normalize_incoming(job_id, entry)

        for index, existing in enumerate(bookmarks):
            if existing.id == normalized.id:
                replacement = normalized
                if normalized.created_at <= 0:
                    replacement = BookmarkEntry(
                        **{**normalized.__dict__, "created_at": existing.created_at}
                    )
                bookmarks[index] = replacement
                self._persist(job_id, user_id, bookmarks)
                return replacement

        for existing in bookmarks:
            if self._is_duplicate(existing, normalized):
                return existing

        bookmarks.append(normalized)
        bookmarks.sort(key=lambda entry: entry.created_at, reverse=True)
        if len(bookmarks) > self._max_entries:
            bookmarks = bookmarks[: self._max_entries]
        self._persist(job_id, user_id, bookmarks)
        return normalized

    def remove_bookmark(self, job_id: str, user_id: str, bookmark_id: str) -> bool:
        payload = self._load_payload(job_id, user_id)
        bookmarks = self._normalize_entries(payload.get("bookmarks"))
        next_entries = [entry for entry in bookmarks if entry.id != bookmark_id]
        if len(next_entries) == len(bookmarks):
            return False
        self._persist(job_id, user_id, next_entries)
        return True

    def _persist(self, job_id: str, user_id: str, entries: Iterable[BookmarkEntry]) -> None:
        payload = {
            "version": 1,
            "job_id": job_id,
            "user_id": user_id,
            "updated_at": time.time(),
            "bookmarks": [self._serialize(entry) for entry in entries],
        }
        _atomic_write_json(self._job_path(job_id, user_id), payload)

    def _serialize(self, entry: BookmarkEntry) -> Dict[str, Any]:
        return {
            "id": entry.id,
            "job_id": entry.job_id,
            "item_type": entry.item_type,
            "kind": entry.kind,
            "created_at": entry.created_at,
            "label": entry.label,
            "position": entry.position,
            "sentence": entry.sentence,
            "media_type": entry.media_type,
            "media_id": entry.media_id,
            "base_id": entry.base_id,
            "segment_id": entry.segment_id,
            "chunk_id": entry.chunk_id,
        }

    def _load_payload(self, job_id: str, user_id: str) -> Dict[str, Any]:
        path = self._job_path(job_id, user_id)
        if not path.exists():
            return {"version": 1, "job_id": job_id, "user_id": user_id, "bookmarks": []}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load bookmarks from %s: %s", path, exc)
            return {"version": 1, "job_id": job_id, "user_id": user_id, "bookmarks": []}
        if not isinstance(payload, dict):
            return {"version": 1, "job_id": job_id, "user_id": user_id, "bookmarks": []}
        return payload

    def _normalize_entries(self, raw_entries: Any) -> List[BookmarkEntry]:
        if not isinstance(raw_entries, list):
            return []
        entries: List[BookmarkEntry] = []
        for entry in raw_entries:
            if not isinstance(entry, dict):
                continue
            normalized = self._normalize_incoming(str(entry.get("job_id") or ""), entry)
            entries.append(normalized)
        return entries

    def _normalize_incoming(self, job_id: str, entry: Dict[str, Any]) -> BookmarkEntry:
        entry_id = str(entry.get("id") or uuid.uuid4())
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
        resolved_job_id = job_id or str(entry.get("job_id") or "")
        return BookmarkEntry(
            id=entry_id,
            job_id=resolved_job_id,
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

    def _job_path(self, job_id: str, user_id: str) -> Path:
        user_fragment = _sanitize_fragment(user_id, "user")
        job_fragment = _sanitize_fragment(job_id, "job")
        root = self._file_locator.storage_root / "bookmarks" / user_fragment
        return root / f"{job_fragment}.json"

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

    @staticmethod
    def _is_duplicate(existing: BookmarkEntry, incoming: BookmarkEntry) -> bool:
        if existing.kind != incoming.kind:
            return False
        if existing.segment_id != incoming.segment_id:
            return False
        if existing.chunk_id != incoming.chunk_id:
            return False
        if existing.kind == "sentence":
            return bool(existing.sentence and existing.sentence == incoming.sentence)
        if existing.position is None or incoming.position is None:
            return False
        return abs(existing.position - incoming.position) < 0.5


__all__ = ["BookmarkService", "BookmarkEntry"]
