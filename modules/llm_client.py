"""Utility classes for interacting with Ollama chat endpoints."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urljoin

import requests

from modules import config_manager as cfg
from modules import logging_manager as log_mgr

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

    def resolve_api_url(self) -> str:
        """Return the concrete API URL, honoring the runtime context defaults."""

        return self.api_url or cfg.get_ollama_url()

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


class LLMClient:
    """Stateless helper for issuing chat requests against the Ollama API."""

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
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                self._log_debug("Skipping non-JSON line from stream: %s", line)
                continue
            raw_chunks.append(payload)
            message = payload.get("message", {}).get("content")
            if message:
                full_text += message
            elif "response" in payload and isinstance(payload["response"], str):
                full_text += payload["response"]
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
    def _execute_request(
        self, payload: Dict[str, Any], *, timeout: Optional[int] = None
    ) -> LLMResponse:
        timeout = timeout or 90
        stream = bool(payload.get("stream", False))
        api_url = self.api_url
        self._log_debug("Dispatching LLM request to %s with stream=%s", api_url, stream)
        self._log_debug("Payload: %s", json.dumps(payload, indent=2, ensure_ascii=False))

        headers: Dict[str, str] = {}
        if self._settings.api_key:
            headers["Authorization"] = f"Bearer {self._settings.api_key}"

        response = self._session.post(
            api_url,
            json=payload,
            headers=headers or None,
            stream=stream,
            timeout=timeout,
        )

        if response.status_code != 200:
            body_preview = response.text[:300]
            self._log_debug(
                "Received non-200 response: %s - %s",
                response.status_code,
                body_preview,
            )
            error_message = f"HTTP {response.status_code}"
            if body_preview:
                error_message = f"{error_message}: {body_preview}"
            return LLMResponse(
                text="",
                status_code=response.status_code,
                token_usage={},
                raw=response.text,
                error=error_message,
            )

        parsed = self._parse_stream(response) if stream else self._parse_json_response(response)
        parsed.raw = parsed.raw or response.text
        return parsed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
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

        working_payload = dict(payload)
        working_payload.setdefault("model", self.model)
        last_error: Optional[str] = None

        for attempt in range(1, max_attempts + 1):
            try:
                result = self._execute_request(working_payload, timeout=timeout)
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
    session: Optional[requests.Session] = None,
) -> LLMClient:
    """Return a new :class:`LLMClient` with the provided configuration."""

    settings = ClientSettings(
        model=model or cfg.DEFAULT_MODEL,
        api_url=api_url,
        debug=debug,
        api_key=api_key,
    )
    return LLMClient(settings=settings, session=session)
