"""Schemas for audio-related API responses."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MacOSVoice(BaseModel):
    """Description of a cached macOS ``say`` voice."""

    name: str = Field(description="Display name reported by macOS")
    lang: str = Field(description="Language or locale identifier")
    quality: Optional[str] = Field(
        default=None,
        description="Quality tier reported by macOS, when available",
    )


class GTTSLanguage(BaseModel):
    """Description of an available gTTS language."""

    code: str = Field(description="gTTS language code")
    name: str = Field(description="Human readable language name")


class VoiceInventoryResponse(BaseModel):
    """Payload returned by the ``GET /api/audio/voices`` endpoint."""

    macos: list[MacOSVoice] = Field(
        default_factory=list,
        description="Cached inventory of macOS voices",
    )
    gtts: list[GTTSLanguage] = Field(
        default_factory=list,
        description="Supported gTTS language entries",
    )


class VoiceMatchResponse(BaseModel):
    """Response describing the matched voice identifier."""

    voice: str = Field(description="Identifier returned by the voice selection logic")
