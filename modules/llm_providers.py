"""Utilities for handling prefixed LLM model identifiers."""

from __future__ import annotations

from typing import Optional, Tuple

OLLAMA_LOCAL = "ollama_local"
OLLAMA_CLOUD = "ollama_cloud"
LMSTUDIO_LOCAL = "lmstudio_local"

_PROVIDER_ALIASES = {
    "ollama_local": OLLAMA_LOCAL,
    "ollama-local": OLLAMA_LOCAL,
    "ollama_cloud": OLLAMA_CLOUD,
    "ollama-cloud": OLLAMA_CLOUD,
    "lmstudio": LMSTUDIO_LOCAL,
    "lmstudio_local": LMSTUDIO_LOCAL,
    "lmstudio-local": LMSTUDIO_LOCAL,
}


def normalize_llm_provider(raw: Optional[str]) -> Optional[str]:
    """Return the canonical provider tag when recognized."""

    if not isinstance(raw, str):
        return None
    normalized = raw.strip().lower()
    if not normalized:
        return None
    normalized = normalized.replace(" ", "_")
    normalized = normalized.replace("-", "_")
    return _PROVIDER_ALIASES.get(normalized)


def split_llm_model_identifier(
    raw: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """Split ``provider:model`` identifiers into provider + model name."""

    if not isinstance(raw, str):
        return None, None
    text = raw.strip()
    if not text:
        return None, None
    if ":" not in text:
        return None, text
    prefix, remainder = text.split(":", 1)
    provider = normalize_llm_provider(prefix)
    if provider is None:
        return None, text
    model = remainder.strip()
    return provider, model or None


def format_llm_model_identifier(provider: str, model: str) -> str:
    """Return the ``provider:model`` identifier string."""

    return f"{provider}:{model}"


def classify_ollama_provider(model: str) -> str:
    """Return the provider tag for an Ollama model name."""

    if "cloud" in model.lower():
        return OLLAMA_CLOUD
    return OLLAMA_LOCAL


def is_local_llm_provider(provider: Optional[str]) -> Optional[bool]:
    """Return whether ``provider`` should be treated as local (GPU/CPU bound)."""

    if provider is None:
        return None
    if provider == OLLAMA_CLOUD:
        return False
    if provider in {OLLAMA_LOCAL, LMSTUDIO_LOCAL}:
        return True
    return None


__all__ = [
    "OLLAMA_LOCAL",
    "OLLAMA_CLOUD",
    "LMSTUDIO_LOCAL",
    "classify_ollama_provider",
    "format_llm_model_identifier",
    "is_local_llm_provider",
    "normalize_llm_provider",
    "split_llm_model_identifier",
]
