"""Schemas for managing interactive player reading beds."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReadingBedEntry(BaseModel):
    id: str
    label: str
    url: str
    kind: Literal["bundled", "uploaded"]
    content_type: str | None = None
    is_default: bool = False


class ReadingBedListResponse(BaseModel):
    default_id: str | None = None
    beds: list[ReadingBedEntry] = Field(default_factory=list)


class ReadingBedUpdateRequest(BaseModel):
    label: str | None = None
    set_default: bool | None = None


class ReadingBedDeleteResponse(BaseModel):
    deleted: bool
    default_id: str | None = None

