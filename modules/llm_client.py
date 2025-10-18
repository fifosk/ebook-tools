"""Utility functions for interacting with Ollama chat endpoints."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urljoin

import requests

from modules import config_manager as cfg
from modules import logging_manager as log_mgr

logger = log_mgr.get_logger()

_DEFAULT_MODEL = cfg.DEFAULT_MODEL
_api_url_override: Optional[str] = None
_model = _DEFAULT_MODEL
_debug_enabled = False

TokenUsage = Dict[str, int]
Validator = Callable[[str], bool]


@dataclass
class LLMResponse:
    """Container for responses returned by :func:`send_chat_request`."""

    text: str
    status_code: int
    token_usage: TokenUsage
    raw: Optional[Any] = None
    error: Optional[str] = None


def set_model(model: Optional[str]) -> None:
    """Configure the Ollama model used for chat requests."""

    global _model
    _model = model or _DEFAULT_MODEL


def get_model() -> str:
    """Return the configured model name."""

    return _model


def set_api_url(url: Optional[str]) -> None:
    """Configure the Ollama chat endpoint base URL."""

    global _api_url_override
    _api_url_override = url


def get_api_url() -> str:
    """Return the configured Ollama chat endpoint URL."""

    return _api_url_override or cfg.OLLAMA_API_URL


def set_debug(enabled: bool) -> None:
    """Toggle verbose debug logging for LLM requests."""

    global _debug_enabled
    _debug_enabled = bool(enabled)


def is_debug_enabled() -> bool:
    """Return whether debug logging is enabled for LLM operations."""

    return _debug_enabled


def _log_debug(message: str, *args: Any) -> None:
    if _debug_enabled:
        logger.debug(message, *args)


def _log_token_usage(usage: TokenUsage) -> None:
    """Emit token usage diagnostics when debug logging is enabled."""

    if not usage:
        return
    _log_debug(
        "Token usage - prompt: %s, completion: %s",
        usage.get("prompt_eval_count", 0),
        usage.get("eval_count", 0),
    )


def _extract_token_usage(data: Dict[str, Any]) -> TokenUsage:
    usage: TokenUsage = {}
    for key in ("prompt_eval_count", "eval_count"):
        value = data.get(key)
        if isinstance(value, int):
            usage[key] = value
    return usage


def _merge_token_usage(existing: TokenUsage, new_data: Dict[str, Any]) -> None:
    for key, value in _extract_token_usage(new_data).items():
        existing[key] = value


def _parse_stream(response: requests.Response) -> LLMResponse:
    full_text = ""
    token_usage: TokenUsage = {}
    raw_chunks: List[Dict[str, Any]] = []

    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            _log_debug("Skipping non-JSON line from stream: %s", line)
            continue
        raw_chunks.append(payload)
        message = payload.get("message", {}).get("content")
        if message:
            full_text += message
        elif "response" in payload and isinstance(payload["response"], str):
            full_text += payload["response"]
        _merge_token_usage(token_usage, payload)

    response_payload = LLMResponse(
        text=full_text,
        status_code=response.status_code,
        token_usage=token_usage,
        raw=raw_chunks,
    )
    _log_token_usage(token_usage)
    return response_payload


def _parse_json_response(response: requests.Response) -> LLMResponse:
    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        return LLMResponse(
            text="",
            status_code=response.status_code,
            token_usage={},
            raw=response.text,
            error=f"Invalid JSON response: {exc}",
        )

    token_usage: TokenUsage = {}
    _merge_token_usage(token_usage, data)

    message = data.get("message", {}).get("content")
    if not message and isinstance(data.get("response"), str):
        message = data["response"]

    if isinstance(message, str):
        text = message
    else:
        text = ""

    response_payload = LLMResponse(
        text=text,
        status_code=response.status_code,
        token_usage=token_usage,
        raw=data,
    )
    _log_token_usage(token_usage)
    return response_payload


def _execute_request(payload: Dict[str, Any], timeout: Optional[int] = None) -> LLMResponse:
    timeout = timeout or 90
    stream = bool(payload.get("stream", False))
    api_url = get_api_url()
    _log_debug("Dispatching LLM request to %s with stream=%s", api_url, stream)
    _log_debug("Payload: %s", json.dumps(payload, indent=2, ensure_ascii=False))

    response = requests.post(api_url, json=payload, stream=stream, timeout=timeout)

    if response.status_code != 200:
        _log_debug("Received non-200 response: %s - %s", response.status_code, response.text[:300])
        return LLMResponse(
            text="",
            status_code=response.status_code,
            token_usage={},
            raw=response.text,
            error=f"HTTP {response.status_code}",
        )

    parsed = _parse_stream(response) if stream else _parse_json_response(response)
    parsed.raw = parsed.raw or response.text
    return parsed


def send_chat_request(
    payload: Dict[str, Any],
    *,
    max_attempts: int = 3,
    timeout: Optional[int] = None,
    validator: Optional[Validator] = None,
    backoff_seconds: float = 1.0,
) -> LLMResponse:
    """Send a chat request with retries and optional response validation."""

    if "model" not in payload:
        payload["model"] = _model
    last_error: Optional[str] = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = _execute_request(payload, timeout=timeout)
        except requests.exceptions.RequestException as exc:
            last_error = str(exc)
            _log_debug("Request error on attempt %s/%s: %s", attempt, max_attempts, exc)
            time.sleep(backoff_seconds * attempt)
            continue

        if result.error:
            last_error = result.error
            _log_debug(
                "LLM returned error on attempt %s/%s: %s", attempt, max_attempts, result.error
            )
        else:
            text = result.text.strip()
            if validator and not validator(text):
                last_error = "Validation failed"
                _log_debug("Validator rejected response on attempt %s/%s", attempt, max_attempts)
            elif not text:
                last_error = "Empty response"
                _log_debug("Empty response on attempt %s/%s", attempt, max_attempts)
            else:
                return result

        time.sleep(backoff_seconds * attempt)

    return LLMResponse(
        text="",
        status_code=0,
        token_usage={},
        raw=None,
        error=last_error,
    )


def list_available_tags() -> Optional[Dict[str, Any]]:
    """Fetch available model tags from the Ollama server."""

    api_url = get_api_url()
    tags_url = urljoin(api_url.rstrip("/") + "/", "../tags")
    try:
        response = requests.get(tags_url, timeout=10)
        if response.status_code == 200:
            return response.json()
        _log_debug("Tags endpoint returned %s: %s", response.status_code, response.text[:200])
    except requests.exceptions.RequestException as exc:  # pragma: no cover - network
        _log_debug("Failed to reach tags endpoint: %s", exc)
    return None


def health_check() -> bool:
    """Simple health check against the Ollama server."""

    tags = list_available_tags()
    return bool(tags)
