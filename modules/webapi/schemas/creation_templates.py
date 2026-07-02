"""Schemas for reusable cross-surface creation templates."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


CreationTemplateMode = Literal[
    "generated_book",
    "narrate_ebook",
    "subtitle_job",
    "youtube_dub",
]


class CreationTemplatePayload(BaseModel):
    id: str | None = None
    name: str = "Untitled template"
    mode: str = "generated_book"
    payload: dict[str, Any] = Field(default_factory=dict)


class CreationTemplateEntryPayload(BaseModel):
    id: str
    name: str
    mode: CreationTemplateMode
    created_at: float
    updated_at: float
    payload: dict[str, Any]


class CreationTemplateListResponse(BaseModel):
    templates: list[CreationTemplateEntryPayload]


class CreationTemplateDeleteResponse(BaseModel):
    deleted: bool
    template_id: str
