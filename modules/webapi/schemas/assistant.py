"""Schemas for assistant and lookup endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class LLMModelListResponse(BaseModel):
    """Response payload describing available LLM models."""

    models: List[str] = Field(default_factory=list)


class AssistantChatMessage(BaseModel):
    """A single assistant chat message (used for optional history/context)."""

    role: Literal["user", "assistant"]
    content: str


class AssistantRequestContext(BaseModel):
    """Optional context for assistant requests (future UI action wiring)."""

    source: Optional[str] = None
    page: Optional[str] = None
    job_id: Optional[str] = None
    selection_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssistantLookupRequest(BaseModel):
    """Request payload for a dictionary-style lookup."""

    query: str
    input_language: str
    lookup_language: str = "English"
    llm_model: Optional[str] = None
    system_prompt: Optional[str] = None
    history: List[AssistantChatMessage] = Field(default_factory=list)
    context: Optional[AssistantRequestContext] = None


class AssistantLookupResponse(BaseModel):
    """Response payload for assistant lookups."""

    answer: str
    model: str
    token_usage: Dict[str, int] = Field(default_factory=dict)
    source: Optional[str] = None
