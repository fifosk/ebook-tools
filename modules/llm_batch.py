"""Helpers for LLM batch JSON requests."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence

from modules import prompt_templates
from modules.llm_client import LLMClient

JsonValidator = Callable[[Any], bool]


@dataclass(slots=True)
class JsonBatchResponse:
    """Parsed response payload from a JSON batch request."""

    payload: Optional[Any]
    raw_text: str
    error: Optional[str]
    elapsed: float


def build_json_batch_payload(items: Sequence[Mapping[str, Any]]) -> str:
    """Return a JSON payload string for the provided items."""

    return json.dumps({"items": list(items)}, ensure_ascii=False)


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) < 2:
        return stripped
    if lines[-1].strip().startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return stripped


def _extract_json_block(text: str) -> Optional[str]:
    start_candidates = [idx for idx in (text.find("{"), text.find("[")) if idx != -1]
    if not start_candidates:
        return None
    start = min(start_candidates)
    end = max(text.rfind("}"), text.rfind("]"))
    if end <= start:
        return None
    return text[start : end + 1].strip()


def parse_json_payload(text: str) -> Optional[Any]:
    """Return a JSON payload parsed from ``text`` when possible."""

    if not text:
        return None
    candidates = [text.strip(), _strip_code_fence(text)]
    extracted = _extract_json_block(text)
    if extracted:
        candidates.append(extracted)
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def request_json_batch(
    *,
    client: LLMClient,
    system_prompt: str,
    items: Sequence[Mapping[str, Any]],
    timeout_seconds: float,
    max_attempts: int = 3,
    validator: Optional[JsonValidator] = None,
) -> JsonBatchResponse:
    """Send a JSON batch request and parse the response."""

    user_payload = build_json_batch_payload(items)
    payload = prompt_templates.make_sentence_payload(
        user_payload,
        model=client.model,
        stream=False,
        system_prompt=system_prompt,
    )

    def _validate_response(text: str) -> bool:
        parsed = parse_json_payload(text)
        if parsed is None:
            return False
        if validator is None:
            return True
        try:
            return bool(validator(parsed))
        except Exception:
            return False

    start_time = time.perf_counter()
    response = client.send_chat_request(
        payload,
        max_attempts=max_attempts,
        timeout=timeout_seconds,
        validator=_validate_response,
    )
    elapsed = time.perf_counter() - start_time
    parsed = parse_json_payload(response.text)
    error = response.error
    if parsed is None:
        error = error or "Invalid JSON response"
    elif validator is not None and not validator(parsed):
        error = error or "JSON response failed validation"
    return JsonBatchResponse(
        payload=parsed,
        raw_text=response.text or "",
        error=error,
        elapsed=elapsed,
    )


__all__ = [
    "JsonBatchResponse",
    "build_json_batch_payload",
    "parse_json_payload",
    "request_json_batch",
]
