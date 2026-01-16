"""Utility classes for interacting with Ollama/OpenAI-compatible chat endpoints."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List, Optional, Sequence
from urllib.parse import urljoin

import requests

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules.llm_endpoints import LLMSource, ResolvedEndpoint, resolve_endpoints
from modules.llm_providers import (
    LMSTUDIO_LOCAL,
    OLLAMA_CLOUD,
    OLLAMA_LOCAL,
    split_llm_model_identifier,
)

logger = log_mgr.get_logger()

TokenUsage = Dict[str, int]
Validator = Callable[[str], bool]


@dataclass(frozen=True)
class ClientSettings:
    """Immutable collection of configuration parameters for an :class:`LLMClient`."""

    model: str = cfg.DEFAULT_MODEL
    api_url: Optional[str] = None
    debug: bool = False
    api_key: Optional[str] = None
    llm_source: str = cfg.DEFAULT_LLM_SOURCE
    local_api_url: Optional[str] = None
    cloud_api_url: Optional[str] = None
    lmstudio_api_url: Optional[str] = None
    fallback_sources: Sequence[str] = ()
    allow_fallback: bool = True
    cloud_api_key: Optional[str] = None

    def resolve_api_url(self) -> str:
        """Return the concrete API URL, honoring the runtime context defaults."""

        primary_source = LLMSource.from_value(self.llm_source)
        if primary_source == LLMSource.LMSTUDIO:
            if self.api_url:
                return self.api_url
            if self.lmstudio_api_url:
                return self.lmstudio_api_url
            return cfg.get_lmstudio_url()
        if primary_source == LLMSource.CLOUD:
            if self.api_url:
                return self.api_url
            if self.cloud_api_url:
                return self.cloud_api_url
            return cfg.get_cloud_ollama_url()
        if self.api_url:
            return self.api_url
        if self.local_api_url:
            return self.local_api_url
        return cfg.get_local_ollama_url()

    def with_updates(self, **updates: Any) -> "ClientSettings":
        """Return a copy of the settings with provided keyword overrides applied."""

        return replace(self, **updates)


@dataclass
class LLMResponse:
    """Container for responses returned by :class:`LLMClient.send_chat_request`."""

    text: str
    status_code: int
    token_usage: TokenUsage
    raw: Optional[Any] = None
    error: Optional[str] = None
    source: Optional[str] = None


class LLMClient:
    """Stateless helper for issuing chat requests against LLM chat APIs."""

    def __init__(
        self,
        settings: Optional[ClientSettings] = None,
        *,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._settings = settings or ClientSettings()
        self._session = session or requests.Session()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def settings(self) -> ClientSettings:
        """Return the immutable settings backing this client."""

        return self._settings

    @property
    def model(self) -> str:
        """Return the configured model name."""

        return self._settings.model

    @property
    def llm_source(self) -> str:
        """Return the logical LLM source backing this client."""

        return self._settings.llm_source

    @property
    def api_url(self) -> str:
        """Return the resolved API endpoint URL."""

        return self._settings.resolve_api_url()

    @property
    def api_key(self) -> Optional[str]:
        """Return the configured API key if available."""

        return self._settings.api_key

    @property
    def debug_enabled(self) -> bool:
        """Return whether verbose debug logging is enabled."""

        return bool(self._settings.debug)

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    def _log_debug(self, message: str, *args: Any) -> None:
        if self.debug_enabled:
            logger.debug(message, *args)

    def _log_token_usage(self, usage: TokenUsage) -> None:
        if not usage:
            return
        self._log_debug(
            "Token usage - prompt: %s, completion: %s",
            usage.get("prompt_eval_count", 0),
            usage.get("eval_count", 0),
        )

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------
    def _extract_token_usage(self, data: Dict[str, Any]) -> TokenUsage:
        usage: TokenUsage = {}
        if isinstance(data.get("usage"), dict):
            usage_payload = data["usage"]
            prompt_tokens = usage_payload.get("prompt_tokens")
            completion_tokens = usage_payload.get("completion_tokens")
            if isinstance(prompt_tokens, int):
                usage["prompt_eval_count"] = prompt_tokens
            if isinstance(completion_tokens, int):
                usage["eval_count"] = completion_tokens
        for key in ("prompt_eval_count", "eval_count"):
            value = data.get(key)
            if isinstance(value, int):
                usage[key] = value
        return usage

    def _merge_token_usage(self, existing: TokenUsage, new_data: Dict[str, Any]) -> None:
        for key, value in self._extract_token_usage(new_data).items():
            existing[key] = value

    def _parse_stream(self, response: requests.Response) -> LLMResponse:
        full_text = ""
        token_usage: TokenUsage = {}
        raw_chunks: List[Dict[str, Any]] = []

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            payload_text = line
            if isinstance(payload_text, bytes):
                encoding = response.encoding or "utf-8"
                try:
                    payload_text = payload_text.decode(encoding)
                except UnicodeDecodeError:
                    payload_text = payload_text.decode("utf-8", errors="replace")
            if payload_text.startswith("data:"):
                payload_text = payload_text[len("data:") :].strip()
                if payload_text == "[DONE]":
                    continue
            try:
                payload = json.loads(payload_text)
            except json.JSONDecodeError:
                self._log_debug("Skipping non-JSON line from stream: %s", line)
                continue
            raw_chunks.append(payload)
            message = payload.get("message", {}).get("content")
            if not message and isinstance(payload.get("response"), str):
                message = payload["response"]
            if not message and isinstance(payload.get("choices"), list):
                for choice in payload["choices"]:
                    if not isinstance(choice, dict):
                        continue
                    delta = choice.get("delta") if isinstance(choice.get("delta"), dict) else None
                    if delta and isinstance(delta.get("content"), str):
                        message = delta["content"]
                        break
                    message_text = choice.get("text")
                    if isinstance(message_text, str):
                        message = message_text
                        break
            if message:
                full_text += message
            self._merge_token_usage(token_usage, payload)

        response_payload = LLMResponse(
            text=full_text,
            status_code=response.status_code,
            token_usage=token_usage,
            raw=raw_chunks,
        )
        self._log_token_usage(token_usage)
        return response_payload

    def _parse_json_response(self, response: requests.Response) -> LLMResponse:
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
        self._merge_token_usage(token_usage, data)

        message = data.get("message", {}).get("content")
        if not message and isinstance(data.get("response"), str):
            message = data["response"]
        if not message and isinstance(data.get("choices"), list):
            for choice in data["choices"]:
                if not isinstance(choice, dict):
                    continue
                choice_message = choice.get("message")
                if isinstance(choice_message, dict) and isinstance(
                    choice_message.get("content"), str
                ):
                    message = choice_message["content"]
                    break
                choice_text = choice.get("text")
                if isinstance(choice_text, str):
                    message = choice_text
                    break

        text = message if isinstance(message, str) else ""

        response_payload = LLMResponse(
            text=text,
            status_code=response.status_code,
            token_usage=token_usage,
            raw=data,
        )
        self._log_token_usage(token_usage)
        return response_payload

    # ------------------------------------------------------------------
    # Request execution
    # ------------------------------------------------------------------
    def _retry_after_seconds(self, response: requests.Response) -> Optional[float]:
        header_value = response.headers.get("Retry-After")
        if not header_value:
            return None
        try:
            return float(header_value)
        except (TypeError, ValueError):
            return None

    def _completion_url(self, url: str) -> str:
        if "/chat/completions" in url:
            return url.replace("/chat/completions", "/completions")
        return url

    def _resolve_request_url(self, endpoint: ResolvedEndpoint, request_mode: str) -> str:
        if request_mode == "completion":
            return self._completion_url(endpoint.url)
        return endpoint.url

    def _execute_request(
        self,
        payload: Dict[str, Any],
        *,
        timeout: Optional[int] = None,
        request_mode: str = "chat",
    ) -> LLMResponse:
        timeout = timeout or 90
        base_payload = dict(payload)
        stream_requested = bool(base_payload.get("stream", False))
        endpoints = resolve_endpoints(self._settings)

        if not endpoints:
            return LLMResponse(
                text="",
                status_code=0,
                token_usage={},
                raw=None,
                error="No LLM endpoints available",
            )

        endpoint_errors: List[str] = []
        for endpoint in endpoints:
            attempt_payload = dict(base_payload)
            attempt_stream = stream_requested and endpoint.supports_stream
            if stream_requested and not attempt_stream:
                attempt_payload["stream"] = False

            headers = dict(endpoint.headers)
            endpoint_url = self._resolve_request_url(endpoint, request_mode)

            self._log_debug(
                "Dispatching LLM request to %s (%s) with stream=%s",
                endpoint_url,
                endpoint.source.value,
                attempt_stream,
            )
            self._log_debug(
                "Payload: %s",
                json.dumps(attempt_payload, indent=2, ensure_ascii=False),
            )

            try:
                response = self._session.post(
                    endpoint_url,
                    json=attempt_payload,
                    headers=headers or None,
                    stream=attempt_stream,
                    timeout=timeout,
                )
            except requests.exceptions.RequestException as exc:
                endpoint_errors.append(f"{endpoint.source.value}: {exc}")
                self._log_debug(
                    "Request error when contacting %s endpoint: %s",
                    endpoint.source.value,
                    exc,
                )
                continue

            if response.status_code == 429:
                retry_after = self._retry_after_seconds(response)
                if retry_after:
                    self._log_debug(
                        "Rate limited by %s endpoint; sleeping for %s seconds",
                        endpoint.source.value,
                        retry_after,
                    )
                    time.sleep(retry_after)
                endpoint_errors.append(
                    f"{endpoint.source.value}: rate limited ({response.status_code})"
                )
                continue

            if response.status_code != 200:
                body_preview = response.text[:300]
                self._log_debug(
                    "Received non-200 response from %s endpoint: %s - %s",
                    endpoint.source.value,
                    response.status_code,
                    body_preview,
                )
                error_message = f"HTTP {response.status_code}"
                if body_preview:
                    error_message = f"{error_message}: {body_preview}"
                endpoint_errors.append(f"{endpoint.source.value}: {error_message}")
                continue

            parsed = (
                self._parse_stream(response)
                if attempt_stream
                else self._parse_json_response(response)
            )
            parsed.raw = parsed.raw or response.text
            parsed.source = endpoint.source.value
            return parsed

        error_message = "; ".join(endpoint_errors) if endpoint_errors else "Unknown error"
        return LLMResponse(
            text="",
            status_code=0,
            token_usage={},
            raw=None,
            error=error_message,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def _send_request(
        self,
        payload: Dict[str, Any],
        *,
        request_mode: str,
        max_attempts: int = 3,
        timeout: Optional[int] = None,
        validator: Optional[Validator] = None,
        backoff_seconds: float = 1.0,
    ) -> LLMResponse:
        working_payload = dict(payload)
        working_payload.setdefault("model", self.model)
        last_error: Optional[str] = None

        for attempt in range(1, max_attempts + 1):
            try:
                result = self._execute_request(
                    working_payload,
                    timeout=timeout,
                    request_mode=request_mode,
                )
            except requests.exceptions.RequestException as exc:
                last_error = str(exc)
                self._log_debug("Request error on attempt %s/%s: %s", attempt, max_attempts, exc)
                time.sleep(backoff_seconds * attempt)
                continue

            if result.error:
                last_error = result.error
                self._log_debug(
                    "LLM returned error on attempt %s/%s: %s",
                    attempt,
                    max_attempts,
                    result.error,
                )
            else:
                text = result.text.strip()
                if validator and not validator(text):
                    last_error = "Validation failed"
                    self._log_debug(
                        "Validator rejected response on attempt %s/%s",
                        attempt,
                        max_attempts,
                    )
                elif not text:
                    last_error = "Empty response"
                    self._log_debug(
                        "Empty response on attempt %s/%s",
                        attempt,
                        max_attempts,
                    )
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

    def send_chat_request(
        self,
        payload: Dict[str, Any],
        *,
        max_attempts: int = 3,
        timeout: Optional[int] = None,
        validator: Optional[Validator] = None,
        backoff_seconds: float = 1.0,
    ) -> LLMResponse:
        """Send a chat request with retries and optional response validation."""

        return self._send_request(
            payload,
            request_mode="chat",
            max_attempts=max_attempts,
            timeout=timeout,
            validator=validator,
            backoff_seconds=backoff_seconds,
        )

    def send_completion_request(
        self,
        payload: Dict[str, Any],
        *,
        max_attempts: int = 3,
        timeout: Optional[int] = None,
        validator: Optional[Validator] = None,
        backoff_seconds: float = 1.0,
    ) -> LLMResponse:
        """Send a completion request with retries and optional response validation."""

        return self._send_request(
            payload,
            request_mode="completion",
            max_attempts=max_attempts,
            timeout=timeout,
            validator=validator,
            backoff_seconds=backoff_seconds,
        )

    def list_available_tags(self) -> Optional[Dict[str, Any]]:
        """Fetch available model tags from the Ollama server."""

        api_url = self.api_url
        tags_url = urljoin(api_url.rstrip("/") + "/", "../tags")
        try:
            response = self._session.get(tags_url, timeout=10)
            if response.status_code == 200:
                return response.json()
            self._log_debug(
                "Tags endpoint returned %s: %s",
                response.status_code,
                response.text[:200],
            )
        except requests.exceptions.RequestException as exc:  # pragma: no cover - network
            self._log_debug("Failed to reach tags endpoint: %s", exc)
        return None

    def health_check(self) -> bool:
        """Simple health check against the Ollama server."""

        tags = self.list_available_tags()
        return bool(tags)

    def close(self) -> None:
        """Release any network resources associated with this client."""

        self._session.close()

    # Context manager helpers -------------------------------------------------
    def __enter__(self) -> "LLMClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - trivial
        self.close()


def create_client(
    *,
    model: Optional[str] = None,
    api_url: Optional[str] = None,
    debug: bool = False,
    api_key: Optional[str] = None,
    llm_source: Optional[str] = None,
    local_api_url: Optional[str] = None,
    cloud_api_url: Optional[str] = None,
    lmstudio_api_url: Optional[str] = None,
    fallback_sources: Optional[Sequence[str]] = None,
    allow_fallback: bool = True,
    cloud_api_key: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> LLMClient:
    """Return a new :class:`LLMClient` with the provided configuration."""

    resolved_model = model or cfg.DEFAULT_MODEL
    provider, stripped_model = split_llm_model_identifier(resolved_model)
    if provider and stripped_model:
        resolved_model = stripped_model
        if provider == OLLAMA_LOCAL:
            llm_source = "local"
            api_url = local_api_url or cfg.get_local_ollama_url()
        elif provider == OLLAMA_CLOUD:
            llm_source = "cloud"
            api_url = cloud_api_url or cfg.get_cloud_ollama_url()
        elif provider == LMSTUDIO_LOCAL:
            llm_source = "lmstudio"
            api_url = lmstudio_api_url or cfg.get_lmstudio_url()

    settings = ClientSettings(
        model=resolved_model,
        api_url=api_url,
        debug=debug,
        api_key=api_key,
        llm_source=llm_source or cfg.get_llm_source(),
        local_api_url=local_api_url,
        cloud_api_url=cloud_api_url,
        lmstudio_api_url=lmstudio_api_url,
        fallback_sources=fallback_sources or (),
        allow_fallback=allow_fallback,
        cloud_api_key=cloud_api_key,
    )
    return LLMClient(settings=settings, session=session)
