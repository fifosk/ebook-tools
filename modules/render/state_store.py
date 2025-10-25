"""Serialization helpers for persisting render batch context."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from .context import RenderBatchContext


def serialize_batch_context(context: Optional[RenderBatchContext]) -> Optional[Dict[str, Any]]:
    """Convert ``context`` into a JSON-serializable representation."""

    if context is None:
        return None
    return context.to_dict()


def deserialize_batch_context(payload: Optional[Mapping[str, Any]]) -> Optional[RenderBatchContext]:
    """Reconstruct a :class:`RenderBatchContext` from serialized data."""

    if not payload:
        return None
    return RenderBatchContext.from_mapping(payload)


__all__ = ["serialize_batch_context", "deserialize_batch_context"]
