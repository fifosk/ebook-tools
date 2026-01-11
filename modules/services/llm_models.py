"""Helpers for querying available LLM models."""

from __future__ import annotations

from typing import List, Mapping, Optional
from urllib.parse import urlparse, urlunparse

import requests

from modules import logging_manager as log_mgr
from modules import config_manager as cfg
from modules.llm_client import create_client
from modules.llm_providers import (
    LMSTUDIO_LOCAL,
    classify_ollama_provider,
    format_llm_model_identifier,
)

logger = log_mgr.get_logger().getChild("services.llm_models")


def _list_ollama_models() -> List[str]:
    models: List[str] = []
    try:
        with create_client(llm_source="local") as client:
            payload = client.list_available_tags()
    except Exception:
        logger.error("Unable to query Ollama model tags", exc_info=True)
        raise

    if isinstance(payload, Mapping):
        entries: Optional[object] = payload.get("models")
        if isinstance(entries, list):
            for entry in entries:
                name: Optional[str] = None
                if isinstance(entry, Mapping):
                    raw_name = entry.get("name")
                    if isinstance(raw_name, str):
                        name = raw_name.strip()
                elif isinstance(entry, str):
                    name = entry.strip()
                if name:
                    models.append(name)
    return models


def _resolve_lmstudio_models_url(api_url: str) -> str:
    parsed = urlparse(api_url)
    path = parsed.path or ""
    if "/v1" in path:
        prefix = path.split("/v1", 1)[0]
        base_path = f"{prefix}/v1"
    else:
        base_path = path.rstrip("/")
    if not base_path:
        base_path = "/v1"
    models_path = f"{base_path.rstrip('/')}/models"
    return urlunparse(parsed._replace(path=models_path, params="", query="", fragment=""))


def _list_lmstudio_models() -> List[str]:
    models: List[str] = []
    api_url = cfg.get_lmstudio_url()
    models_url = _resolve_lmstudio_models_url(api_url)
    try:
        response = requests.get(models_url, timeout=10)
    except requests.RequestException as exc:
        logger.debug("LM Studio models endpoint unavailable: %s", exc)
        return []
    if response.status_code != 200:
        logger.debug(
            "LM Studio models endpoint returned %s: %s",
            response.status_code,
            response.text[:200],
        )
        return []
    try:
        payload = response.json()
    except ValueError:
        logger.debug("LM Studio models endpoint returned invalid JSON")
        return []
    if isinstance(payload, Mapping):
        entries: Optional[object] = payload.get("data")
        if isinstance(entries, list):
            for entry in entries:
                name: Optional[str] = None
                if isinstance(entry, Mapping):
                    raw_name = entry.get("id") or entry.get("name")
                    if isinstance(raw_name, str):
                        name = raw_name.strip()
                elif isinstance(entry, str):
                    name = entry.strip()
                if name:
                    models.append(name)
    return models


def list_available_llm_models() -> List[str]:
    """Return the list of available LLM model identifiers."""

    models: List[str] = []
    seen: set[str] = set()
    ollama_error: Optional[Exception] = None

    try:
        ollama_models = _list_ollama_models()
    except Exception as exc:
        ollama_models = []
        ollama_error = exc
        logger.warning("Ollama model list unavailable; continuing with other providers.")

    for name in ollama_models:
        provider = classify_ollama_provider(name)
        labeled = format_llm_model_identifier(provider, name)
        if labeled not in seen:
            seen.add(labeled)
            models.append(labeled)

    lmstudio_models = _list_lmstudio_models()
    for name in lmstudio_models:
        labeled = format_llm_model_identifier(LMSTUDIO_LOCAL, name)
        if labeled not in seen:
            seen.add(labeled)
            models.append(labeled)

    if not models and ollama_error is not None:
        raise RuntimeError("No LLM providers responded") from ollama_error

    return models


__all__ = ["list_available_llm_models"]
