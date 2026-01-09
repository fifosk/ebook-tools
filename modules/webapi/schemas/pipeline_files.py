"""Schemas for pipeline file browsing endpoints."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class PipelineFileEntry(BaseModel):
    """Describes a selectable file within the dashboard."""

    name: str
    path: str
    type: Literal["file", "directory"]


class PipelineFileBrowserResponse(BaseModel):
    """Response payload listing available ebook and output files."""

    ebooks: List[PipelineFileEntry] = Field(default_factory=list)
    outputs: List[PipelineFileEntry] = Field(default_factory=list)
    books_root: str = ""
    output_root: str = ""
