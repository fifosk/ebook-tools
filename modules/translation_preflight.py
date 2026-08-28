"""Bounded, endpoint-specific model checks before managed translation work."""

from __future__ import annotations

import hashlib
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit, urlunsplit

import requests

from modules import config_manager as cfg
from modules.llm_client import LLMClient
from modules.llm_endpoints import LLMSource, resolve_endpoints

_lock = threading.Lock()
_cache: dict[str, tuple[float, str, str]] = {}


class TranslationPreflightError(RuntimeError):
    """A confirmed unavailable model must not fall back to per-item calls."""


def check_model(client: LLMClient) -> tuple[str, str]:
    """Return available/unavailable/unknown. Discovery failure is not absence.

    A catalog check cannot promise inference capacity or translation quality.
    Never change the selected model or expose provider responses/credentials.
    """
    endpoints = resolve_endpoints(client.settings)
    if not endpoints:
        return "unavailable", "No translation endpoint is configured for the selected model."
    if len(endpoints) > 1:
        return "unknown", "Multiple provider endpoints configured; inference will use the configured fallback order."
    endpoint = endpoints[0]
    parts = urlsplit(endpoint.url)
    local = endpoint.source == LLMSource.LOCAL
    path = "/api/tags" if local else parts.path.removesuffix("/chat/completions").removesuffix("/completions") + "/models"
    url = urlunsplit((parts.scheme, parts.netloc, path, "", ""))
    digest = hashlib.sha256(repr((url, client.model, sorted(endpoint.headers.items()))).encode()).hexdigest()
    with _lock:
        cached = _cache.get(digest)
        if cached and cached[0] > time.monotonic():
            return cached[1], cached[2]
    status, message = "unknown", "Model availability could not be confirmed; inference will use the selected model."
    try:
        response = requests.get(url, headers=endpoint.headers, timeout=(2, 3))
        if response.status_code in (401, 403):
            status, message = "unavailable", "Translation model authorization failed. Check the cloud pool/account connection."
        elif response.status_code == 200:
            payload = response.json()
            entries = payload.get("models" if local else "data") if isinstance(payload, dict) else None
            if isinstance(entries, list):
                names = set()
                for entry in entries:
                    if isinstance(entry, dict):
                        name = entry.get("name") or entry.get("model") or entry.get("id")
                        if isinstance(name, str) and name.strip():
                            names.add(name.strip())
                selected = client.model
                if selected in names or (local and selected + ":latest" in names):
                    status, message = "available", "Selected translation model is listed by its provider."
                elif names or not entries:
                    status, message = "unavailable", "Selected translation model is not available. Choose an available translation model."
    except (requests.RequestException, ValueError):
        pass
    with _lock:
        now = time.monotonic()
        for key in list(_cache):
            if _cache[key][0] <= now:
                del _cache[key]
        if len(_cache) >= 128:
            _cache.pop(next(iter(_cache)))
        _cache[digest] = (now + 30, status, message)
    return status, message


def preflight_translation(client, provider, tracker=None) -> None:
    """Check in the job worker/caller, never in the API event loop or per item."""
    context = cfg.get_runtime_context(None)
    output = getattr(context, "output_dir", None)
    if (provider != "llm" or not isinstance(client, LLMClient) or not output
            or Path(output).name != "media" or not (Path(output).parent / "data").is_dir()):
        return
    status, message = check_model(client)
    if tracker is not None:
        tracker.update_generated_files_metadata({"translation_preflight": {
            "status": status, "message": message, "model": client.model,
        }})
    if status == "unavailable":
        raise TranslationPreflightError(message)
