"""Schemas for pipeline file browsing endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


class PipelineFileEntry(BaseModel):
    """Describes a selectable file within the dashboard."""

    name: str
    path: str
    type: Literal["file", "directory"]
    size_bytes: Optional[int] = None
    modified_at: Optional[datetime] = None


class PipelineFileBrowserResponse(BaseModel):
    """Response payload listing available ebook and output files."""

    ebooks: List[PipelineFileEntry]
    outputs: List[PipelineFileEntry]
    books_root: str
    output_root: str
