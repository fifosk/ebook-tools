"""Helpers for querying available LLM models."""

from __future__ import annotations

from typing import List, Mapping, Optional

from modules import logging_manager as log_mgr
from modules.llm_client import create_client

logger = log_mgr.get_logger().getChild("services.llm_models")


def list_available_llm_models() -> List[str]:
    """Return the list of available Ollama model names."""

    models: List[str] = []
    try:
        with create_client() as client:
            payload = client.list_available_tags()
    except Exception:
        logger.error("Unable to query Ollama model tags", exc_info=True)
        raise

    if isinstance(payload, Mapping):
        entries: Optional[object] = payload.get("models")
        seen: set[str] = set()
        if isinstance(entries, list):
            for entry in entries:
                name: Optional[str] = None
                if isinstance(entry, Mapping):
                    raw_name = entry.get("name")
                    if isinstance(raw_name, str):
                        name = raw_name.strip()
                elif isinstance(entry, str):
                    name = entry.strip()
                if name and name not in seen:
                    models.append(name)
                    seen.add(name)
    return models


__all__ = ["list_available_llm_models"]
