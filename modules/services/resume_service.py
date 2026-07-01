"""Persistence service for per-user playback resume positions."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from .file_locator import FileLocator
from .source_discovery import safe_iterdir, safe_stat
from .. import logging_manager


logger = logging_manager.get_logger().getChild("resume_service")

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


def _path_exists(path: Path) -> bool:
    return safe_stat(path) is not None


def normalize_resume_job_ids(job_ids: Optional[Sequence[str]]) -> list[str]:
    """Return trimmed, de-duplicated resume job ids in caller order."""
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_job_id in job_ids or []:
        job_id = str(raw_job_id).strip()
        if not job_id or job_id in seen:
            continue
        seen.add(job_id)
        normalized.append(job_id)
    return normalized


@dataclass(frozen=True)
class ResumeEntry:
    job_id: str
    kind: str                    # "time" | "sentence"
    updated_at: float            # unix timestamp (seconds)
    position: Optional[float]    # playback time in seconds
    sentence: Optional[int]      # sentence number
    chunk_id: Optional[str]      # active chunk
    media_type: Optional[str]    # "text" | "audio" | "video"
    base_id: Optional[str]       # media segment identifier
    playback_track: Optional[str] = None  # original | translation when text resume is track-local


class ResumeService:
    def __init__(
        self,
        *,
        file_locator: Optional[FileLocator] = None,
    ) -> None:
        self._file_locator = file_locator or FileLocator()

    def get(self, job_id: str, user_id: str) -> Optional[ResumeEntry]:
        payload = self._load_payload(job_id, user_id)
        raw_entry = payload.get("entry")
        if not isinstance(raw_entry, dict):
            return None
        return self._normalize_entry(job_id, raw_entry)

    def list(
        self,
        user_id: str,
        *,
        job_ids: Optional[Sequence[str]] = None,
        limit: int = 200,
    ) -> list[ResumeEntry]:
        requested_job_ids = normalize_resume_job_ids(job_ids)
        if job_ids is not None and not requested_job_ids:
            return []

        user_fragment = _sanitize_fragment(user_id, "user")
        root = self._file_locator.storage_root / "resume" / user_fragment
        if not _path_exists(root):
            return []

        if requested_job_ids:
            entries = []
            for job_id in requested_job_ids:
                entry = self._load_entry_from_path(job_id, self._job_path(job_id, user_id))
                if entry is not None:
                    entries.append(entry)
            return sorted(entries, key=lambda entry: entry.updated_at, reverse=True)[:limit]

        entries: list[ResumeEntry] = []
        for path in sorted(child for child in safe_iterdir(root) if child.suffix == ".json"):
            entry = self._load_entry_from_path(path.stem, path)
            if entry is None:
                continue
            entries.append(entry)
        return sorted(entries, key=lambda entry: entry.updated_at, reverse=True)[:limit]

    def save(self, job_id: str, user_id: str, data: Dict[str, Any]) -> ResumeEntry:
        entry = self._normalize_entry(job_id, data)
        self._persist(job_id, user_id, entry)
        return entry

    def clear(self, job_id: str, user_id: str) -> bool:
        path = self._job_path(job_id, user_id)
        if not _path_exists(path):
            return False
        try:
            path.unlink()
        except OSError:
            logger.warning("Resume storage could not be removed; leaving state unchanged")
            return False
        return True

    def _persist(self, job_id: str, user_id: str, entry: ResumeEntry) -> None:
        payload = {
            "version": 1,
            "job_id": job_id,
            "user_id": user_id,
            "updated_at": entry.updated_at,
            "entry": self._serialize(entry),
        }
        _atomic_write_json(self._job_path(job_id, user_id), payload)

    def _serialize(self, entry: ResumeEntry) -> Dict[str, Any]:
        return {
            "job_id": entry.job_id,
            "kind": entry.kind,
            "updated_at": entry.updated_at,
            "position": entry.position,
            "sentence": entry.sentence,
            "chunk_id": entry.chunk_id,
            "media_type": entry.media_type,
            "base_id": entry.base_id,
            "playback_track": entry.playback_track,
        }

    def _load_payload(self, job_id: str, user_id: str) -> Dict[str, Any]:
        path = self._job_path(job_id, user_id)
        if not _path_exists(path):
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Resume storage could not be loaded; returning empty state")
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload

    def _load_entry_from_path(
        self, fallback_job_id: str, path: Path
    ) -> Optional[ResumeEntry]:
        if not _path_exists(path):
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Resume storage could not be loaded; returning empty state")
            return None
        if not isinstance(payload, dict):
            return None
        job_id = self._coerce_string(payload.get("job_id")) or fallback_job_id
        raw_entry = payload.get("entry")
        if not isinstance(raw_entry, dict):
            return None
        return self._normalize_entry(job_id, raw_entry)

    def _normalize_entry(self, job_id: str, data: Dict[str, Any]) -> ResumeEntry:
        kind = str(data.get("kind") or "time").strip().lower()
        if kind not in {"time", "sentence"}:
            kind = "time"
        updated_at = self._coerce_float(data.get("updated_at")) or time.time()
        position = self._coerce_float(data.get("position"))
        sentence = self._coerce_int(data.get("sentence"))
        chunk_id = self._coerce_string(data.get("chunk_id"))
        media_type = self._coerce_string(data.get("media_type"))
        base_id = self._coerce_string(data.get("base_id"))
        playback_track = self._coerce_string(data.get("playback_track"))
        return ResumeEntry(
            job_id=job_id,
            kind=kind,
            updated_at=updated_at,
            position=position,
            sentence=sentence,
            chunk_id=chunk_id,
            media_type=media_type,
            base_id=base_id,
            playback_track=playback_track,
        )

    def _job_path(self, job_id: str, user_id: str) -> Path:
        user_fragment = _sanitize_fragment(user_id, "user")
        job_fragment = _sanitize_fragment(job_id, "job")
        root = self._file_locator.storage_root / "resume" / user_fragment
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


__all__ = ["ResumeService", "ResumeEntry", "normalize_resume_job_ids"]
