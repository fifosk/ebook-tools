"""Prompt helpers for diffusion image generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from modules.llm_client_manager import client_scope


@dataclass(frozen=True, slots=True)
class DiffusionPrompt:
    prompt: str
    negative_prompt: str = ""


def _extract_json_object(text: str) -> Optional[Mapping[str, Any]]:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        parsed: Any = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, Mapping) else None


def sentence_to_diffusion_prompt(
    sentence: str,
    *,
    timeout_seconds: int = 90,
) -> DiffusionPrompt:
    """Convert ``sentence`` into an SD-optimised prompt using the configured LLM."""

    cleaned = (sentence or "").strip()
    if not cleaned:
        return DiffusionPrompt(prompt="")

    system_prompt = (
        "You convert natural language sentences into Stable Diffusion 1.5 prompts.\n"
        "Return JSON only with keys: prompt, negative_prompt.\n"
        "Constraints:\n"
        "- Keep it short (<= 25 words).\n"
        "- Use English.\n"
        "- Focus on the concrete visual scene.\n"
        "- Prefer black and white, low detail, simple line art.\n"
        "- Avoid sensitive content.\n"
    )

    user_prompt = (
        "Convert this sentence into a diffusion prompt optimised for Stable Diffusion 1.5.\n"
        f"Sentence: {cleaned}\n"
        "Return JSON only."
    )

    last_text = ""
    with client_scope(None) as client:
        response = client.send_chat_request(
            {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.3, "top_p": 0.9},
            },
            timeout=int(timeout_seconds),
        )
        if response.error:
            last_text = response.text.strip() if response.text else ""
        else:
            last_text = response.text.strip()

    payload = _extract_json_object(last_text)
    if payload is None:
        fallback_prompt = cleaned
        return DiffusionPrompt(prompt=fallback_prompt)

    prompt_raw = payload.get("prompt")
    negative_raw = payload.get("negative_prompt")
    prompt = str(prompt_raw).strip() if prompt_raw is not None else ""
    negative_prompt = str(negative_raw).strip() if negative_raw is not None else ""
    if not prompt:
        prompt = cleaned
    return DiffusionPrompt(prompt=prompt, negative_prompt=negative_prompt)

