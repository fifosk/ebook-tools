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
    LMSTUDIO_MACBOOK,
    LMSTUDIO_MACSTUDIO,
    OLLAMA_CLOUD,
    classify_ollama_provider,
    format_llm_model_identifier,
    split_llm_model_identifier,
)

logger = log_mgr.get_logger().getChild("services.llm_models")


# Translation/lookup quality tiers — lower score = higher placement in the picker.
# Tiers reflect suitability for the app's two LLM use cases: multilingual
# translation (EN→AR/HI/FR/CJK with transliteration) and structured JSON
# dictionary lookup.
#
# ORIGIN: Priors from family reputation + published benchmarks (WMT, FLORES-200,
# LMArena multilingual, vendor evals), then re-ranked using measured results
# from `scripts/probe_llm_models.py` — see `test-results/llm_probe_report.md`
# for the run this is derived from. Spot-check with the probe before reorders.
#
# Tier conventions:
#   10 — pinned default (configured primary, never reordered here)
#   20s — top measured performers (5/5 probe pass, fast latency)
#   30s — strong measured performers (5/5 pass, medium-fast)
#   40s — working but slower (>8s avg) OR partial pass (4/5)
#   50s — small/limited models (<30B — may be echoing, need human QA)
#   60s — slow but usable (20-40s avg)
#   70s — poor (multiple fails AND slow)
#   80  — currently broken server-side
#   90s — avoid (coding-specialised; multilingual knowledge ablated)
#
# Unknown (not in this table): tier 60 (_DEFAULT_MODEL_TIER) — between
# "slow but usable" and "poor", so new releases surface but don't outrank
# vetted choices until they get probed.
_MODEL_QUALITY_TIERS: dict[str, int] = {
    # ── Tier 1: Pinned default — Mistral stays here regardless of measurements
    "mistral-large-3:675b": 10,
    "mistral-large-3:675b-cloud": 11,  # legacy suffix form
    # ── Tier 2: Top measured performers (5/5 pass, <2s)
    # deepseek-v3.1:671b was the measured leader (1.7s, score 0.833)
    "deepseek-v3.1:671b": 20,
    "gemini-3-flash-preview": 21,      # 5/5, 4.6s
    "qwen3-vl:235b-instruct": 22,      # 5/5, 1.9s (235B fast!)
    "gemma4:31b": 23,                  # 5/5, 1.1s — best-value promotion
    "gemma3:27b": 24,                  # 5/5, 0.9s
    "nemotron-3-super": 25,            # 5/5, 1.8s
    # ── Tier 3: Strong measured (5/5 pass, 2-5s)
    "cogito-2.1:671b": 30,             # 5/5, 2.5s
    "minimax-m2.1": 31,                # 5/5, 2.7s
    "minimax-m2": 32,                  # 5/5, 3.5s
    "minimax-m2.5": 33,                # 5/5, 3.6s
    "gpt-oss:120b": 34,                # 5/5, 3.0s
    "ministral-3:14b": 35,             # 5/5, 0.9s (14B but full pass)
    "gemma3:12b": 36,                  # 5/5, 1.2s
    "deepseek-v4-flash": 37,           # 5/5, 3.0s — promoted from tier 55
    # ── Tier 4: Working but slower / partial pass
    "deepseek-v3.2": 40,               # 5/5, 9.1s — reasoning model, slow
    "minimax-m2.7": 41,                # 5/5, 9.6s
    "kimi-k2:1t": 42,                  # 4/5 (missed FR), 2.1s
    # ── Tier 5: Small/limited (5/5 in probe but quality unverified at small size)
    "gpt-oss:20b": 50,                 # 5/5, 1.3s
    "ministral-3:8b": 51,              # 5/5, 0.8s
    "nemotron-3-nano:30b": 52,         # 5/5, 0.8s
    "gemma3:4b": 53,                   # 5/5, 0.8s — 4B, likely truncated output
    "ministral-3:3b": 54,              # 5/5, 0.8s — 3B, lowest quality ceiling
    "rnj-1:8b": 55,                    # 5/5, 0.9s
    # ── Tier 6: Slow (20-40s avg) — usable if you can wait
    "kimi-k2.5": 60,                   # 4/5, 21.5s
    "kimi-k2.6": 61,                   # 4/5, 26.1s
    "qwen3-next:80b": 62,              # 5/5, 29.6s
    "glm-5": 63,                       # 5/5, 30.7s
    "qwen3-vl:235b": 64,               # 4/5, 32.9s
    "glm-5.1": 65,                     # 4/5, 35.5s
    # ── Tier 7: Poor (multiple probe fails AND slow)
    "glm-4.7": 70,                     # 3/5, 44.9s
    "glm-4.6": 71,                     # 2/5, 58.0s
    "qwen3.5:397b": 72,                # 1/5, 51.9s — demoted hard from prior tier 23
    # ── Tier 8: Currently broken server-side
    "kimi-k2-thinking": 80,            # HTTP 500 from Ollama Cloud
    # ── Tier 9: Avoid — coding-specialised lines with ablated multilingual coverage
    "devstral-2:123b": 90,
    "devstral-small-2:24b": 91,
    "qwen3-coder-next": 92,
    "qwen3-coder:480b": 93,
}
# Unknown models sort between "acceptable" and "small/limited" — newly released
# models surface but stay below the vetted top tiers until benchmarked.
_DEFAULT_MODEL_TIER = 60

# Provider group — determines the picker section. LM Studio models are
# appended AFTER all Ollama models (cloud + local) regardless of quality tier,
# because LM Studio is typically a local/personal workstation running smaller
# quantized builds and is 10-40× slower than Ollama Cloud for the same model
# size (measured head-to-head on gemma-4-31b: 214s vs 6.3s for the 5-probe
# suite). Keep them grouped together at the bottom so users see the fast
# cloud+local ollama options first.
_PROVIDER_GROUP: dict[str, int] = {
    "ollama_cloud": 0,        # Ollama cloud (fastest, GPU-backed)
    "ollama_local": 0,        # Ollama local (same catalog as cloud)
    "lmstudio_local": 1,      # LM Studio legacy single-host (= Mac Studio)
    "lmstudio_macstudio": 1,  # LM Studio on the Mac Studio (M-series, faster)
    "lmstudio_macbook": 1,    # LM Studio on the MacBook Pro (laptop, slowest)
}

# Within a provider group, prefer cloud over local Ollama so the configured
# default (cloud Mistral) stays pinned at the very top. Within the LM Studio
# group, Mac Studio is shown before MacBook Pro because the Studio runs the
# stronger M-series GPU and is closer to a workstation than a laptop.
_SUBPROVIDER_ORDER: dict[str, int] = {
    "ollama_cloud": 0,
    "ollama_local": 1,
    "lmstudio_local": 0,        # legacy alias of Mac Studio
    "lmstudio_macstudio": 0,
    "lmstudio_macbook": 1,
}


def _model_quality_tier(model_name: str) -> int:
    """Return the quality tier for a bare model name (no provider prefix)."""
    return _MODEL_QUALITY_TIERS.get(model_name, _DEFAULT_MODEL_TIER)


def _sort_key_for_model(identifier: str) -> tuple[int, int, int, str]:
    """Sort key: (provider_group, quality_tier, subprovider, lowercase_name).

    Primary: provider group — Ollama (0) before LM Studio (1).
    Secondary: quality tier within the group.
    Tertiary: cloud before local within Ollama (so cloud default stays pinned).
    """
    provider, model = split_llm_model_identifier(identifier)
    bare = (model or identifier).strip()
    tier = _model_quality_tier(bare)
    group = _PROVIDER_GROUP.get(provider or "", 2)  # unknown → after LMS
    sub = _SUBPROVIDER_ORDER.get(provider or "", 9)
    return (group, tier, sub, identifier.lower())


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


def _query_lmstudio_models(api_url: str, host_label: str) -> List[str]:
    """Query a single LM Studio host's `/v1/models` endpoint and return ids."""
    models: List[str] = []
    models_url = _resolve_openai_models_url(api_url)
    # LM Studio may be running with "Require API key" enabled. Pull the token
    # from settings or the LMSTUDIO_API_KEY env var so model discovery works
    # in auth-enabled setups. Both hosts share the same auth setting today —
    # split into per-host secrets if that ever stops being true.
    headers: dict[str, str] = {}
    try:
        settings = cfg.get_settings()
        secret = getattr(settings, "lmstudio_api_key", None)
        token = (
            secret.get_secret_value()
            if secret is not None and hasattr(secret, "get_secret_value")
            else (secret if isinstance(secret, str) else None)
        )
    except Exception:
        token = None
    if not token:
        token = os.environ.get("LMSTUDIO_API_KEY")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(models_url, headers=headers or None, timeout=10)
    except requests.RequestException as exc:
        logger.debug("LM Studio (%s) endpoint unavailable: %s", host_label, exc)
        return []
    if response.status_code != 200:
        logger.debug(
            "LM Studio (%s) endpoint returned %s: %s",
            host_label,
            response.status_code,
            response.text[:200],
        )
        return []
    try:
        payload = response.json()
    except ValueError:
        logger.debug("LM Studio (%s) endpoint returned invalid JSON", host_label)
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


def _list_lmstudio_macstudio_models() -> List[str]:
    return _query_lmstudio_models(cfg.get_lmstudio_macstudio_url(), "macstudio")


def _list_lmstudio_macbook_models() -> List[str]:
    return _query_lmstudio_models(cfg.get_lmstudio_macbook_url(), "macbook")


def _list_lmstudio_models() -> List[str]:
    """Legacy single-host accessor — returns Mac Studio's models for back-compat."""
    return _list_lmstudio_macstudio_models()


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

    macstudio_models = _list_lmstudio_macstudio_models()
    for name in macstudio_models:
        labeled = format_llm_model_identifier(LMSTUDIO_MACSTUDIO, name)
        if labeled not in seen:
            seen.add(labeled)
            models.append(labeled)

    macbook_models = _list_lmstudio_macbook_models()
    for name in macbook_models:
        labeled = format_llm_model_identifier(LMSTUDIO_MACBOOK, name)
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

    # Sort by translation/lookup quality (stable). Default model stays at the
    # top because _MODEL_QUALITY_TIERS places mistral-large-3 at tier 10.
    models.sort(key=_sort_key_for_model)
    return models


__all__ = ["list_available_llm_models"]
