"""Utility functions for interacting with Ollama chat endpoints."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from ollama import Client
from ollama import RequestError, ResponseError

from modules import config_manager as cfg
from modules import logging_manager as log_mgr

logger = log_mgr.get_logger()

_DEFAULT_MODEL = cfg.DEFAULT_MODEL
_REMOTE_HOSTS = (
    "https://ollama.com",
    "https://api.ollama.com",
)
_LOCAL_HOST = "http://localhost:11434"
_api_url_override: Optional[str] = None
_model = _DEFAULT_MODEL
_debug_enabled = False
_client_cache: Dict[Tuple[str, Optional[str]], Client] = {}

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


def _log_info(message: str, *args: Any) -> None:
    logger.info(message, *args)


def _log_warning(message: str, *args: Any) -> None:
    logger.warning(message, *args)


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


def _summarize_text(text: str, *, limit: int = 200) -> str:
    """Return a condensed single-line preview of ``text`` for logging."""

    if not text:
        return ""

    condensed = " ".join(text.split())
    if len(condensed) > limit:
        return condensed[:limit].rstrip() + "…"
    return condensed


def _coerce_text(value: Union[str, Dict[str, Any], Iterable[Any], None]) -> str:
    """Normalise Ollama SDK response fragments into a plain string."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Prefer explicit ``text`` payloads, then nested ``content``-style fields.
        for key in (
            "text",
            "content",
            "value",
            "values",
            "data",
            "message",
            "response",
            "output",
            "outputs",
            "parts",
        ):
            if key in value:
                coerced = _coerce_text(value.get(key))
                if coerced:
                    return coerced
        # Fall back to scanning all values to capture deeply nested strings.
        aggregate = "".join(
            _coerce_text(item)
            for item in value.values()
            if isinstance(item, (str, dict, list, tuple, set)) or item is None
        )
        return aggregate
    if isinstance(value, (list, tuple, set)):
        return "".join(_coerce_text(item) for item in value)
    return ""


def _normalize_host(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    trimmed = url.strip()
    if not trimmed:
        return None
    trimmed = trimmed.rstrip("/")
    for suffix in ("/api/chat", "/api/generate", "/api"):
        if trimmed.endswith(suffix):
            trimmed = trimmed[: -len(suffix)]
            break
    return trimmed or None


def _resolve_host_chain() -> Iterable[Tuple[str, Optional[str]]]:
    api_key = os.getenv("OLLAMA_API_KEY") or None
    hosts: List[Tuple[str, Optional[str]]] = []
    seen: set[str] = set()

    def _append(host: Optional[str], key: Optional[str]) -> None:
        if not host or host in seen:
            return
        seen.add(host)
        hosts.append((host, key if key else None))

    remote_hosts = [
        host
        for host in (
            _normalize_host(candidate)
            for candidate in _REMOTE_HOSTS
        )
        if host
    ]
    configured_host = _normalize_host(cfg.OLLAMA_API_URL)
    override_host = _normalize_host(_api_url_override) if _api_url_override else None
    local_host = _normalize_host(_LOCAL_HOST)

    remote_host_set = set(remote_hosts)

    if override_host:
        key = api_key if api_key and override_host in remote_host_set else None
        _append(override_host, key)

    if api_key:
        for candidate in remote_hosts:
            _append(candidate, api_key)

    if configured_host:
        key = api_key if api_key and configured_host in remote_host_set else None
        _append(configured_host, key)

    _append(local_host, None)

    return hosts


def _get_client(host: str, api_key: Optional[str]) -> Client:
    cache_key = (host, api_key)
    if cache_key in _client_cache:
        return _client_cache[cache_key]

    if api_key:
        try:
            client = Client(host=host, api_key=api_key)
        except TypeError:
            headers = {"Authorization": f"Bearer {api_key}"}
            try:
                client = Client(host=host, headers=headers)
            except TypeError:
                client = Client(host=host)
                transport = getattr(client, "_client", None)
                if transport and hasattr(transport, "headers"):
                    transport.headers.update(headers)
    else:
        client = Client(host=host)

    _client_cache[cache_key] = client
    return client


def _chat_with_client(
    client: Client,
    host: str,
    payload: Dict[str, Any],
    *,
    stream: bool,
    timeout: Optional[int],
) -> LLMResponse:
    request_payload = dict(payload)
    request_payload.pop("stream", None)
    _log_debug("Dispatching LLM request to %s with stream=%s", host, stream)
    _log_debug("Payload: %s", json.dumps(request_payload, indent=2, ensure_ascii=False))

    try:
        response = client.chat(stream=stream, timeout=timeout, **request_payload)
    except TypeError:
        response = client.chat(stream=stream, **request_payload)

    token_usage: TokenUsage = {}

    if stream:
        full_text = ""
        raw_chunks: List[Dict[str, Any]] = []

        def _append_text(part: Any) -> None:
            nonlocal full_text
            text = _coerce_text(part)
            if text:
                full_text += text

        for chunk in response:
            if not isinstance(chunk, dict):
                continue
            raw_chunks.append(chunk)

            message = chunk.get("message")
            _append_text(message)

            delta = chunk.get("delta")
            _append_text(delta)

            response_text = chunk.get("response")
            _append_text(response_text)

            content = chunk.get("content")
            _append_text(content)

            _merge_token_usage(token_usage, chunk)
        reply = LLMResponse(
            text=full_text,
            status_code=200,
            token_usage=token_usage,
            raw=raw_chunks,
        )
    else:
        if not isinstance(response, dict):
            data: Dict[str, Any] = {}
        else:
            data = response
        _merge_token_usage(token_usage, data)
        message = _coerce_text(data.get("message"))
        if not message:
            message = _coerce_text(data.get("response"))
        if not message:
            message = _coerce_text(data.get("content"))
        reply = LLMResponse(
            text=message or "",
            status_code=200,
            token_usage=token_usage,
            raw=data,
        )

    _log_token_usage(token_usage)
    return reply


def _execute_request(payload: Dict[str, Any], timeout: Optional[int] = None) -> LLMResponse:
    timeout = timeout or 90
    stream = bool(payload.get("stream", False))

    for host, api_key in _resolve_host_chain():
        credential_state = "present" if api_key else "absent"
        _log_info(
            "Attempting Ollama request via %s (API key %s)",
            host,
            credential_state,
        )
        try:
            client = _get_client(host, api_key)
        except Exception as exc:  # pragma: no cover - defensive
            _log_debug("Failed to initialise Ollama client for %s: %s", host, exc)
            last_error = str(exc)
            continue

        try:
            result = _chat_with_client(client, host, payload, stream=stream, timeout=timeout)
            _log_info("Ollama request succeeded via %s", host)
            return result
        except (RequestError, ResponseError, OSError) as exc:
            last_error = str(exc)
            _log_warning("LLM request failed for %s: %s", host, exc)
            continue
        except Exception as exc:  # pragma: no cover - unexpected failure
            last_error = str(exc)
            _log_warning("Unexpected error during LLM request for %s: %s", host, exc)
            continue

    failure_reason = last_error if 'last_error' in locals() else "Unable to reach Ollama service"
    _log_warning("Exhausted host chain for Ollama request: %s", failure_reason)
    return LLMResponse(
        text="",
        status_code=0,
        token_usage={},
        raw=None,
        error=failure_reason,
    )


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
        result = _execute_request(payload, timeout=timeout)

        if result.error:
            last_error = result.error
            _log_debug(
                "LLM returned error on attempt %s/%s: %s", attempt, max_attempts, result.error
            )
        else:
            text = result.text.strip()
            if validator and not validator(text):
                preview = _summarize_text(text)
                last_error = (
                    f"Validation failed (response excerpt: {preview})"
                    if preview
                    else "Validation failed"
                )
                _log_warning(
                    "Validator rejected response on attempt %s/%s: %s",
                    attempt,
                    max_attempts,
                    preview or "<empty response>",
                )
            elif not text:
                last_error = "Empty response"
                _log_debug("Empty response on attempt %s/%s", attempt, max_attempts)
            else:
                return result

        time.sleep(backoff_seconds * attempt)

    _log_warning(
        "LLM request failed after %s attempts (last error: %s)",
        max_attempts,
        last_error or "unknown",
    )
    return LLMResponse(
        text="",
        status_code=0,
        token_usage={},
        raw=None,
        error=last_error,
    )


def list_available_tags() -> Optional[Dict[str, Any]]:
    """Fetch available model tags from the Ollama server."""

    for host, api_key in _resolve_host_chain():
        try:
            client = _get_client(host, api_key)
            _log_info(
                "Fetching Ollama model list via %s (API key %s)",
                host,
                "present" if api_key else "absent",
            )
            return client.list()
        except (RequestError, ResponseError, OSError) as exc:
            _log_warning("Unable to list models from %s: %s", host, exc)
            continue
        except Exception as exc:  # pragma: no cover - unexpected failure
            _log_warning("Unexpected error listing models from %s: %s", host, exc)
            continue
    return None


def health_check() -> bool:
    """Simple health check against the Ollama server."""

    tags = list_available_tags()
    return bool(tags)
