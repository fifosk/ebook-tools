"""Dataclasses and Pydantic schemas for the library domain."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field, validator


def _has_generated_media(payload: Mapping[str, Any]) -> bool:
    files_section = payload.get("files")
    if isinstance(files_section, list):
        for entry in files_section:
            if isinstance(entry, Mapping) and entry:
                return True
    elif isinstance(files_section, Mapping):
        for entry in files_section.values():
            if isinstance(entry, Mapping) and entry:
                return True
            if isinstance(entry, str) and entry.strip():
                return True

    chunks_section = payload.get("chunks")
    if isinstance(chunks_section, list):
        for chunk in chunks_section:
            if not isinstance(chunk, Mapping):
                continue
            if any(chunk.get(key) for key in ("chunk_id", "range_fragment")) or any(
                chunk.get(key) is not None for key in ("start_sentence", "end_sentence")
            ):
                return True
            files = chunk.get("files")
            if isinstance(files, list):
                for entry in files:
                    if isinstance(entry, Mapping) and entry:
                        return True
            elif isinstance(files, Mapping):
                for entry in files.values():
                    if isinstance(entry, Mapping) and entry:
                        return True
                    if isinstance(entry, str) and entry.strip():
                        return True
    return False


class MetadataSnapshot(BaseModel):
    """Wrapper around the JSON metadata persisted alongside each library entry."""

    data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(populate_by_name=True, frozen=True)

    @validator("data", pre=True)
    def _coerce_mapping(cls, value: Any) -> Dict[str, Any]:
        if isinstance(value, MetadataSnapshot):
            return dict(value.data)
        if isinstance(value, Mapping):
            return dict(value)
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return {}
            return decoded if isinstance(decoded, dict) else {}
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def contains_media(self) -> bool:
        generated = self.data.get("generated_files")
        return bool(generated)

    def is_media_completed(self) -> bool:
        metadata_completed = bool(self.data.get("media_completed"))
        if metadata_completed:
            return True
        generated = self.data.get("generated_files")
        if isinstance(generated, Mapping):
            if bool(generated.get("complete")):
                return True
            if _has_generated_media(generated):
                return True
        return False

    def to_json(self) -> str:
        return json.dumps(self.data, ensure_ascii=False)


@dataclass(frozen=True)
class LibraryEntry:
    """Domain representation of a library record."""

    id: str
    author: str
    book_title: str
    genre: Optional[str]
    language: str
    status: str
    created_at: str
    updated_at: str
    library_path: str
    item_type: str = "book"
    cover_path: Optional[str] = None
    isbn: Optional[str] = None
    source_path: Optional[str] = None
    metadata: MetadataSnapshot = field(default_factory=MetadataSnapshot)

    @property
    def absolute_path(self) -> Path:
        return Path(self.library_path)

    def as_payload(self) -> Dict[str, Any]:
        payload = {
            "job_id": self.id,
            "author": self.author or "",
            "book_title": self.book_title or "",
            "item_type": self.item_type or "book",
            "genre": self.genre,
            "language": self.language,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "library_path": self.library_path,
            "cover_path": self.cover_path,
            "isbn": self.isbn,
            "source_path": self.source_path,
            "metadata": dict(self.metadata.data),
        }
        payload["media_completed"] = self.metadata.is_media_completed()
        return payload


class LibraryQuery(BaseModel):
    """Filtering descriptors for listing library entries."""

    query: Optional[str] = None
    author: Optional[str] = None
    book_title: Optional[str] = Field(default=None, alias="book")
    genre: Optional[str] = None
    language: Optional[str] = None
    status: Optional[str] = None
    view: str = "flat"
    page: int = 1
    limit: int = 25
    sort: str = "updated_at_desc"

    model_config = ConfigDict(populate_by_name=True, frozen=True)

    @validator("page", pre=True, always=True)
    def _normalize_page(cls, value: Any) -> int:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return 1
        return 1 if numeric < 1 else numeric

    @validator("limit", pre=True, always=True)
    def _normalize_limit(cls, value: Any) -> int:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return 25
        return max(1, min(numeric, 100))


class UpdateRequest(BaseModel):
    """Change-set for metadata updates."""

    title: Optional[str] = None
    author: Optional[str] = None
    genre: Optional[str] = None
    language: Optional[str] = None
    isbn: Optional[str] = None

    model_config = ConfigDict(frozen=True)

    def to_update_fields(self) -> Dict[str, Optional[str]]:
        return {
            "title": self.title,
            "author": self.author,
            "genre": self.genre,
            "language": self.language,
            "isbn": self.isbn,
        }


__all__ = [
    "LibraryEntry",
    "LibraryQuery",
    "MetadataSnapshot",
    "UpdateRequest",
]
