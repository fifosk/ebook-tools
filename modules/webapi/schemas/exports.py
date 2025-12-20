"""Schemas for offline export bundles."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExportRequestPayload(BaseModel):
    """Request payload for building an offline export bundle."""

    source_kind: Literal["job", "library"] = Field(
        ..., description="Where to export from (pipeline job or library entry)."
    )
    source_id: str = Field(..., description="Job ID or library entry ID to export.")
    player_type: Literal["interactive-text"] = Field(
        default="interactive-text",
        description="Offline player bundle to use for the export.",
    )


class ExportResponse(BaseModel):
    """Response payload for a completed offline export bundle."""

    export_id: str = Field(..., description="Server-generated export identifier.")
    download_url: str = Field(..., description="URL for downloading the export bundle.")
    filename: str = Field(..., description="Suggested filename for the download.")
    created_at: str = Field(..., description="Timestamp when the export bundle was created.")

