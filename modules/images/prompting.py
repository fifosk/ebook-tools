"""Prompt helpers for diffusion image generation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from modules.llm_client_manager import client_scope


@dataclass(frozen=True, slots=True)
class DiffusionPrompt:
    prompt: str
    negative_prompt: str = ""


COMIC_BASE_PROMPT = (
    "glyph-style clipart icon, flat vector illustration,\n"
    "clean crisp edges, bold outline, clear silhouette,\n"
    "high contrast, simple shapes, minimal detail,\n"
    "limited color palette, solid fills,\n"
    "no gradients, no shading,\n"
    "white background, minimal clutter,\n"
    "single focused scene, centered composition,\n"
    "leave empty space for labels (no text),\n"
    "single image, no collage"
)

COMIC_NEGATIVE_PROMPT = (
    "blurry, haze, fog, smoke, soft focus, low contrast,\n"
    "lowres, jpeg artifacts, grain, noise,\n"
    "photorealistic, realistic lighting, photograph,\n"
    "3d render, CGI, depth of field, bokeh,\n"
    "text, letters, words, watermark, logo, signature,\n"
    "comic page, multiple panels, panel grid, collage, montage, split panel, page layout,\n"
    "complex background, clutter, intricate detail,\n"
    "oversaturated, gradients, heavy shading, dramatic lighting"
)

_COMIC_PROMPT_MARKERS = (
    "glyph-style clipart icon",
    "single framed comic panel",
    "one-panel comic illustration",
)
_COMIC_NEGATIVE_MARKER = "blurry, haze"

_LEGACY_IMAGE_STYLE_SUFFIX = "monochrome, black and white, low detail, simple line art, high contrast"
_LEGACY_IMAGE_NEGATIVE_SUFFIX = "color, photorealistic, high detail, text, watermark, logo"


def stable_diffusion_seed(text: str) -> int:
    """Return a stable 31-bit seed derived from ``text``."""

    cleaned = (text or "").strip()
    digest = hashlib.md5(cleaned.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little", signed=False) & 0x7FFFFFFF


def _strip_legacy_suffix(value: str, suffix: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    escaped = re.escape(suffix)
    cleaned = re.sub(rf"(?:,\s*)?{escaped}\s*$", "", candidate, flags=re.IGNORECASE).strip()
    return cleaned.rstrip(",").strip()


def build_sentence_image_prompt(scene_description: str) -> str:
    """Return a full diffusion prompt for sentence images with the comic base prompt appended."""

    candidate = _strip_legacy_suffix(scene_description, _LEGACY_IMAGE_STYLE_SUFFIX)
    if not candidate:
        return COMIC_BASE_PROMPT
    candidate_lower = candidate.lower()
    if any(marker.lower() in candidate_lower for marker in _COMIC_PROMPT_MARKERS):
        return candidate
    return f"{candidate},\n{COMIC_BASE_PROMPT}"


def build_sentence_image_negative_prompt(extra_negative: str) -> str:
    """Return the full negative prompt for sentence images (always includes the base negative prompt)."""

    candidate = _strip_legacy_suffix(extra_negative, _LEGACY_IMAGE_NEGATIVE_SUFFIX)
    if not candidate:
        return COMIC_NEGATIVE_PROMPT
    if _COMIC_NEGATIVE_MARKER.lower() in candidate.lower():
        return candidate
    return f"{COMIC_NEGATIVE_PROMPT}, {candidate}"


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
    context_sentences: Sequence[str] | None = None,
    timeout_seconds: int = 90,
) -> DiffusionPrompt:
    """Convert ``sentence`` into an SD-optimised scene description using the configured LLM."""

    cleaned = (sentence or "").strip()
    if not cleaned:
        return DiffusionPrompt(prompt="")

    system_prompt = (
        "You convert natural language sentences into Stable Diffusion 1.5 scene descriptions.\n"
        "Return JSON only with keys: prompt, negative_prompt.\n"
        "The `prompt` must describe the concrete scene only; do NOT include style keywords.\n"
        "Constraints:\n"
        "- Keep it short (<= 25 words).\n"
        "- Use English.\n"
        "- Reduce to the simplest literal depiction (icon-friendly).\n"
        "- Focus on clear, concrete objects and actions.\n"
        "- Keep the background simple.\n"
        "- Avoid extra props/characters unless essential.\n"
        "- Do NOT request readable text (letters/words).\n"
        "- Avoid sensitive content.\n"
    )

    context_items = [str(item).strip() for item in (context_sentences or ()) if str(item).strip()]
    if context_items:
        context_items = context_items[-10:]
        context_block = "\n".join(f"- {entry}" for entry in context_items)
        user_prompt = (
            "Convert the CURRENT sentence into a concise scene description for Stable Diffusion 1.5.\n"
            "Use the context sentences only to keep characters and setting consistent.\n"
            "Do not include style keywords.\n"
            "Context (previous sentences):\n"
            f"{context_block}\n"
            f"Current sentence: {cleaned}\n"
            "Return JSON only."
        )
    else:
        user_prompt = (
            "Convert this sentence into a concise scene description for Stable Diffusion 1.5.\n"
            "Do not include style keywords.\n"
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
