"""Helpers for querying available LLM models."""

from __future__ import annotations

from typing import List, Mapping, Optional
from urllib.parse import urlparse, urlunparse

import os
import shutil
import subprocess
import requests

from modules import logging_manager as log_mgr
from modules import config_manager as cfg
from modules.llm_client import create_client
from modules.llm_providers import (
    LMSTUDIO_LOCAL,
    OLLAMA_CLOUD,
    classify_ollama_provider,
    format_llm_model_identifier,
    split_llm_model_identifier,
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


def _build_ollama_cli_env() -> Mapping[str, str]:
    env = os.environ.copy()
    if env.get("OLLAMA_HOST"):
        return env
    local_url = cfg.get_local_ollama_url()
    parsed = urlparse(local_url)
    host = None
    if parsed.scheme and parsed.netloc:
        host = parsed.netloc
    elif local_url and "://" not in local_url:
        host = local_url.strip()
    if host:
        env["OLLAMA_HOST"] = host
    return env


def _list_ollama_cli_models() -> List[str]:
    if not shutil.which("ollama"):
        return []
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            env=_build_ollama_cli_env(),
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("Ollama CLI model list unavailable: %s", exc)
        return []
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        logger.debug("Ollama CLI model list returned %s: %s", result.returncode, stderr[:200])
        return []
    models: List[str] = []
    for line in result.stdout.splitlines():
        text = line.strip()
        if not text:
            continue
        if text.lower().startswith("name "):
            continue
        name = text.split()[0]
        if name:
            models.append(name)
    return models


def _resolve_openai_models_url(api_url: str) -> str:
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
    models_url = _resolve_openai_models_url(api_url)
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


def _list_cloud_models() -> List[str]:
    settings = cfg.get_settings()
    api_key = getattr(settings, "ollama_api_key", None)
    if api_key is not None:
        api_key = api_key.get_secret_value()
    if not api_key:
        return []
    api_url = cfg.get_cloud_ollama_url()
    models_url = _resolve_openai_models_url(api_url)
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(models_url, headers=headers, timeout=10)
    except requests.RequestException as exc:
        logger.debug("Ollama Cloud models endpoint unavailable: %s", exc)
        return []
    if response.status_code != 200:
        logger.debug(
            "Ollama Cloud models endpoint returned %s: %s",
            response.status_code,
            response.text[:200],
        )
        return []
    try:
        payload = response.json()
    except ValueError:
        logger.debug("Ollama Cloud models endpoint returned invalid JSON")
        return []
    models: List[str] = []
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


def _normalize_model_identifier(
    raw: Optional[str],
    provider_hint: Optional[str] = None,
) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    provider, model = split_llm_model_identifier(text)
    if provider and model:
        return format_llm_model_identifier(provider, model)
    if provider_hint:
        return format_llm_model_identifier(provider_hint, text)
    provider = classify_ollama_provider(text)
    return format_llm_model_identifier(provider, text)


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
        labeled = _normalize_model_identifier(name)
        if labeled not in seen:
            seen.add(labeled)
            models.append(labeled)

    cli_models = _list_ollama_cli_models()
    for name in cli_models:
        labeled = _normalize_model_identifier(name)
        if labeled and labeled not in seen:
            seen.add(labeled)
            models.append(labeled)

    cloud_models = _list_cloud_models()
    for name in cloud_models:
        labeled = _normalize_model_identifier(name, provider_hint=OLLAMA_CLOUD)
        if labeled and labeled not in seen:
            seen.add(labeled)
            models.append(labeled)

    lmstudio_models = _list_lmstudio_models()
    for name in lmstudio_models:
        labeled = format_llm_model_identifier(LMSTUDIO_LOCAL, name)
        if labeled not in seen:
            seen.add(labeled)
            models.append(labeled)

    settings = cfg.get_settings()
    extra_candidates: List[Optional[str]] = [
        getattr(settings, "ollama_model", None),
        cfg.DEFAULT_MODEL,
        cfg.get_translation_fallback_model(),
    ]
    extra_list = getattr(settings, "llm_model_options", None)
    if isinstance(extra_list, list):
        extra_candidates.extend([entry for entry in extra_list if isinstance(entry, str)])
    for candidate in extra_candidates:
        labeled = _normalize_model_identifier(candidate)
        if labeled and labeled not in seen:
            seen.add(labeled)
            models.append(labeled)

    if not models and ollama_error is not None:
        raise RuntimeError("No LLM providers responded") from ollama_error

    return models


__all__ = ["list_available_llm_models"]
