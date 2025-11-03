"""Metadata extraction and normalization helpers for the library feature."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from modules import metadata_manager

from .library_models import MetadataSnapshot


@dataclass
class MetadataRefreshResult:
    """Structured result returned after a metadata refresh."""

    metadata: Dict[str, Any]
    snapshot: MetadataSnapshot
    cover_path: Optional[str] = None
    isbn: Optional[str] = None


class LibraryMetadataError(RuntimeError):
    """Raised when metadata extraction fails."""


class LibraryMetadataManager:
    """Coordinate metadata inference, ISBN lookups, and cover synchronization."""

    def __init__(self, library_root: Path) -> None:
        self._library_root = Path(library_root)

    def normalize_isbn(self, isbn: str) -> Optional[str]:
        digits = [char for char in str(isbn or "") if char.isdigit() or char.upper() == "X"]
        if not digits:
            return None
        candidate = "".join(digits)
        if len(candidate) == 10 or len(candidate) == 13:
            return candidate.upper()
        return None

    def extract_isbn(self, metadata: Mapping[str, Any]) -> Optional[str]:
        for key in ("isbn", "book_isbn"):
            value = metadata.get(key)
            if isinstance(value, str):
                normalized = self.normalize_isbn(value)
                if normalized:
                    return normalized
        book_metadata = metadata.get("book_metadata")
        if isinstance(book_metadata, Mapping):
            for key in ("isbn", "book_isbn"):
                value = book_metadata.get(key)
                if isinstance(value, str):
                    normalized = self.normalize_isbn(value)
                    if normalized:
                        return normalized
        return None

    def apply_isbn(self, metadata: Dict[str, Any], isbn: Optional[str]) -> None:
        if not isbn:
            return
        metadata["isbn"] = isbn
        book_metadata = metadata.get("book_metadata")
        if isinstance(book_metadata, Mapping):
            nested = dict(book_metadata)
            nested["isbn"] = isbn
            nested["book_isbn"] = isbn
            metadata["book_metadata"] = nested

    def merge_metadata_payloads(self, *payloads: Mapping[str, Any]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        placeholder_checker = getattr(metadata_manager, "_is_placeholder", None)

        def is_placeholder(key: str, value: Any) -> bool:
            if value is None:
                return True
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    return True
                if callable(placeholder_checker):
                    try:
                        return bool(placeholder_checker(key, value))  # type: ignore[misc]
                    except Exception:
                        return False
            return False

        for payload in payloads:
            if not isinstance(payload, Mapping):
                continue
            for key, value in payload.items():
                if value is None:
                    continue
                current = merged.get(key)
                if isinstance(value, str):
                    candidate = value.strip()
                    if not candidate:
                        continue
                    if current is None or is_placeholder(key, current):
                        merged[key] = value
                    elif not is_placeholder(key, value) and candidate != current:
                        merged[key] = value
                else:
                    if current is None:
                        merged[key] = value
        generated = merged.get("generated_files")
        if isinstance(generated, Mapping):
            chunks = generated.get("chunks")
            if isinstance(chunks, list):
                compacted: list[Dict[str, Any]] = []
                changed = False
                for chunk in chunks:
                    if not isinstance(chunk, Mapping):
                        continue
                    entry = dict(chunk)
                    sentences = entry.get("sentences")
                    metadata_path = entry.get("metadata_path")
                    if isinstance(sentences, list) and metadata_path:
                        entry["sentence_count"] = entry.get("sentence_count") or len(sentences)
                        entry.pop("sentences", None)
                        changed = True
                    compacted.append(entry)
                if changed:
                    generated_copy = dict(generated)
                    generated_copy["chunks"] = compacted
                    merged["generated_files"] = generated_copy
        return merged

    def infer_metadata_from_epub(
        self,
        epub_path: Path,
        *,
        existing_metadata: Mapping[str, Optional[str]] | None = None,
        force_refresh: bool = False,
    ) -> Dict[str, Optional[str]]:
        try:
            return metadata_manager.infer_metadata(
                str(epub_path),
                existing_metadata=existing_metadata or {},
                force_refresh=force_refresh,
            )
        except Exception as exc:  # pragma: no cover - delegated failure
            raise LibraryMetadataError(f"Metadata inference failed: {exc}") from exc

    def fetch_metadata_from_isbn(self, isbn: str) -> Dict[str, Optional[str]]:
        normalized = self.normalize_isbn(isbn)
        if not normalized:
            raise LibraryMetadataError("ISBN must contain 10 or 13 digits (optionally including X)")
        return metadata_manager.fetch_metadata_from_isbn(normalized)

    def mirror_cover_asset(self, job_root: Path, cover_source: Optional[str]) -> Optional[str]:
        if not cover_source:
            return None
        source_path = Path(cover_source)
        if not source_path.exists():
            return None
        target_dir = Path(job_root) / "media" / "covers"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / source_path.name
        try:
            shutil.copy2(source_path, target_path)
        except OSError as exc:
            raise LibraryMetadataError(f"Failed to mirror cover asset: {exc}") from exc
        return str(target_path.relative_to(Path(job_root)))

    def build_snapshot(self, metadata: Mapping[str, Any]) -> MetadataSnapshot:
        return MetadataSnapshot(metadata=metadata)


__all__ = [
    "LibraryMetadataError",
    "LibraryMetadataManager",
    "MetadataRefreshResult",
]
