"""Schemas for managing interactive player reading beds."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ReadingBedEntry(BaseModel):
    id: str
    label: str
    url: str
    kind: Literal["bundled", "uploaded"]
    content_type: str | None = None
    is_default: bool


class ReadingBedListResponse(BaseModel):
    default_id: str | None
    beds: list[ReadingBedEntry]


class ReadingBedUpdateRequest(BaseModel):
    label: str | None = None
    set_default: bool | None = None


class ReadingBedDeleteResponse(BaseModel):
    deleted: bool
    default_id: str | None
