"""Prompt helpers for diffusion image generation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from modules.llm_client_manager import client_scope
from modules.images.style_templates import IMAGE_STYLE_TEMPLATES, resolve_image_style_template


_MAX_LLM_CONTEXT_SENTENCES = 50
_PROMPT_MAP_MAX_TARGET_SENTENCES = 50
_PROMPT_MAP_OVERLAP_SENTENCES = 4
_PROMPT_MAP_FULL_RETRY_ATTEMPTS = 1
_PROMPT_MAP_MISSING_RETRY_ATTEMPTS = 2
_PROMPT_MAP_MISSING_CONTEXT_RADIUS = 2
_SCENE_PROMPT_MAX_WORDS = 45
_BASELINE_NOTES_MAX_CHARS = 800
_STYLE_LEAK_PHRASES = tuple(
    dict.fromkeys(
        [
            # Current + legacy story-reel style phrases (keep for sanitizing stored prompts).
            "photorealistic cinematic film still",
            "cinematic film still",
            "35mm photography",
            "photo-realistic",
            "photorealistic",
            "high-quality color comic panel",
            "graphic novel illustration",
            "comic panel",
            "cinematic storybook illustration",
            "cohesive visual style across frames",
            # Template markers (preferred going forward).
            *[
                marker
                for template in IMAGE_STYLE_TEMPLATES.values()
                for marker in template.prompt_markers
                if marker
            ],
        ]
    ).keys()
)


@dataclass(frozen=True, slots=True)
class DiffusionPrompt:
    prompt: str
    negative_prompt: str = ""


@dataclass(frozen=True, slots=True)
class DiffusionPromptPlan:
    prompts: list[DiffusionPrompt]
    sources: list[str]
    continuity_bible: str
    baseline_prompt: DiffusionPrompt
    baseline_notes: str
    baseline_source: str
    quality: dict[str, Any]


_PHOTOREALISTIC_TEMPLATE = IMAGE_STYLE_TEMPLATES["photorealistic"]
STORY_REEL_BASE_PROMPT = _PHOTOREALISTIC_TEMPLATE.base_prompt
STORY_REEL_NEGATIVE_PROMPT = _PHOTOREALISTIC_TEMPLATE.negative_prompt

_STYLE_PROMPT_MARKERS = tuple(
    dict.fromkeys(
        [
            # Template markers.
            *[
                marker
                for template in IMAGE_STYLE_TEMPLATES.values()
                for marker in template.prompt_markers
                if marker
            ],
            # Generic story-reel markers (still present in stored prompts).
            "cinematic film still",
            "cohesive visual style across frames",
            # Legacy glyph-style prompt marker (keep for compatibility with stored prompts).
            "glyph-style clipart icon",
            "single framed comic panel",
            "one-panel comic illustration",
        ]
    ).keys()
)
_STYLE_NEGATIVE_MARKERS = (
    "watermark, logo, signature",
    "blurry, haze",
)

_LEGACY_IMAGE_STYLE_SUFFIX = "monochrome, black and white, low detail, simple line art, high contrast"
_LEGACY_IMAGE_NEGATIVE_SUFFIX = "color, photorealistic, high detail, text, watermark, logo"


def stable_diffusion_seed(text: str) -> int:
    """Return a stable 31-bit seed derived from ``text``."""

    cleaned = (text or "").strip()
    digest = hashlib.md5(cleaned.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little", signed=False) & 0x7FFFFFFF


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).strip()


def _sanitize_scene_prompt(value: str, *, fallback: str) -> str:
    candidate = _collapse_whitespace(value)
    if not candidate:
        candidate = _collapse_whitespace(fallback)
    if not candidate:
        return ""

    for phrase in _STYLE_LEAK_PHRASES:
        if phrase.lower() in candidate.lower():
            candidate = re.sub(re.escape(phrase), "", candidate, flags=re.IGNORECASE)

    candidate = re.sub(r"\s*,\s*", ", ", candidate)
    candidate = candidate.strip(" ,")
    candidate = _collapse_whitespace(candidate)

    words = candidate.split()
    if len(words) > _SCENE_PROMPT_MAX_WORDS:
        candidate = " ".join(words[:_SCENE_PROMPT_MAX_WORDS]).rstrip(",").strip()

    if not candidate:
        candidate = _collapse_whitespace(fallback)
    return candidate


def _sanitize_negative_prompt(value: str) -> str:
    return _collapse_whitespace(value)


def _sanitize_baseline_notes(value: Any) -> str:
    candidate = _collapse_whitespace(str(value or ""))
    if not candidate:
        return ""
    if len(candidate) > _BASELINE_NOTES_MAX_CHARS:
        candidate = candidate[:_BASELINE_NOTES_MAX_CHARS].rstrip()
    return candidate


def _strip_legacy_suffix(value: str, suffix: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    escaped = re.escape(suffix)
    cleaned = re.sub(rf"(?:,\s*)?{escaped}\s*$", "", candidate, flags=re.IGNORECASE).strip()
    return cleaned.rstrip(",").strip()


def build_sentence_image_prompt(scene_description: str, *, style_template: str | None = None) -> str:
    """Return a full diffusion prompt for sentence images with the selected style appended."""

    candidate = _strip_legacy_suffix(scene_description, _LEGACY_IMAGE_STYLE_SUFFIX)
    if not candidate:
        return resolve_image_style_template(style_template).base_prompt
    candidate_lower = candidate.lower()
    if any(marker.lower() in candidate_lower for marker in _STYLE_PROMPT_MARKERS):
        return candidate
    return f"{candidate},\n{resolve_image_style_template(style_template).base_prompt}"


def build_sentence_image_negative_prompt(
    extra_negative: str,
    *,
    style_template: str | None = None,
) -> str:
    """Return the full negative prompt for sentence images (always includes the base negative prompt)."""

    candidate = _strip_legacy_suffix(extra_negative, _LEGACY_IMAGE_NEGATIVE_SUFFIX)
    if not candidate:
        return resolve_image_style_template(style_template).negative_prompt
    candidate_lower = candidate.lower()
    if any(marker.lower() in candidate_lower for marker in _STYLE_NEGATIVE_MARKERS):
        return candidate
    return f"{resolve_image_style_template(style_template).negative_prompt}, {candidate}"


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
        "You convert book sentences into Stable Diffusion 1.5 scene descriptions for a coherent story reel.\n"
        "The visual style is applied separately; do NOT include style keywords.\n"
        "Return JSON only with keys: prompt, negative_prompt.\n"
        "The `prompt` must describe the concrete scene only; do NOT include style keywords.\n"
        "Constraints:\n"
        "- Use English.\n"
        "- Keep it concise (<= 45 words).\n"
        "- Describe a single framed moment (characters, action, setting, time of day, mood, framing).\n"
        "- Keep recurring characters/setting consistent with the provided context.\n"
        "- Do NOT request readable text (letters/words).\n"
        "- Avoid graphic sexual content or violence; if implied, depict it non-graphically.\n"
    )

    context_items = [str(item).strip() for item in (context_sentences or ()) if str(item).strip()]
    if context_items:
        context_items = context_items[-_MAX_LLM_CONTEXT_SENTENCES:]
        context_block = "\n".join(f"- {entry}" for entry in context_items)
        user_prompt = (
            "Convert the CURRENT sentence into a concise scene description for Stable Diffusion 1.5.\n"
            "Use the context sentences only to keep characters and setting consistent.\n"
            "Do not include style keywords.\n"
            "Context (nearby sentences):\n"
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
    prompt = _sanitize_scene_prompt(prompt, fallback=cleaned)
    negative_prompt = _sanitize_negative_prompt(negative_prompt)
    return DiffusionPrompt(prompt=prompt, negative_prompt=negative_prompt)


def _prompt_map_missing_retry(
    *,
    sentences: Sequence[str],
    missing_indices: Sequence[int],
    context_prefix: Sequence[str] | None = None,
    context_suffix: Sequence[str] | None = None,
    continuity_bible: str | None = None,
    baseline_prompt: DiffusionPrompt | None = None,
    baseline_notes: str | None = None,
    context_radius: int = _PROMPT_MAP_MISSING_CONTEXT_RADIUS,
    timeout_seconds: int = 150,
) -> tuple[dict[int, DiffusionPrompt], str]:
    if not sentences or not missing_indices:
        return {}, (continuity_bible or "").strip()

    total = len(sentences)
    radius = max(0, int(context_radius))
    missing_payload = []
    for raw_index in missing_indices:
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            continue
        if index < 0 or index >= total:
            continue
        start = max(0, index - radius)
        end = min(total, index + radius + 1)
        before = [str(entry).strip() for entry in sentences[start:index] if str(entry).strip()]
        after = [str(entry).strip() for entry in sentences[index + 1 : end] if str(entry).strip()]
        missing_payload.append(
            {
                "index": index,
                "sentence": str(sentences[index]).strip(),
                "context_before": before,
                "context_after": after,
            }
        )

    payload = {
        "context_prefix": [str(entry).strip() for entry in (context_prefix or ()) if str(entry).strip()][
            -_MAX_LLM_CONTEXT_SENTENCES:
        ],
        "context_suffix": [str(entry).strip() for entry in (context_suffix or ()) if str(entry).strip()][
            : _MAX_LLM_CONTEXT_SENTENCES
        ],
        "continuity_bible": (continuity_bible or "").strip(),
        "baseline": {
            "prompt": (baseline_prompt.prompt if baseline_prompt else "").strip(),
            "negative_prompt": (baseline_prompt.negative_prompt if baseline_prompt else "").strip(),
            "notes": _sanitize_baseline_notes(baseline_notes),
        },
        "missing": missing_payload,
    }

    system_prompt = (
        "You fix missing Stable Diffusion 1.5 scene descriptions for a book photorealistic story reel.\n"
        "The user provides JSON with:\n"
        "- context_prefix/context_suffix: optional sentences outside the range (context only)\n"
        "- continuity_bible: notes for character/location consistency\n"
        "- baseline: an anchor frame description + layout notes for the overall reel\n"
        "- missing: array of missing entries with {index, sentence, context_before, context_after}\n"
        "\n"
        "Output JSON ONLY with keys:\n"
        '- continuity_bible: updated notes (<= 120 words). Keep it stable once established.\n'
        '- prompts: array with EXACTLY one entry per missing item.\n'
        "\n"
        "Each prompts[] entry MUST include:\n"
        "- index: integer (0-based index into the original sentence list)\n"
        "- prompt: English scene description ONLY (no style keywords), <= 45 words\n"
        "- negative_prompt: optional, keep empty unless needed\n"
        "\n"
        "Rules:\n"
        "- Do NOT include style keywords.\n"
        "- Do NOT request readable text.\n"
        "- If violence/sex is implied, depict it non-graphically.\n"
    )

    user_prompt = (
        "Generate prompts for the missing entries only.\n"
        "Return JSON only.\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
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
                "options": {"temperature": 0.15, "top_p": 0.9},
            },
            timeout=int(timeout_seconds),
        )
        if response.error:
            last_text = response.text.strip() if response.text else ""
        else:
            last_text = response.text.strip()

    parsed = _extract_json_object(last_text)
    if parsed is None:
        return {}, (continuity_bible or "").strip()

    raw_prompts = parsed.get("prompts")
    if not isinstance(raw_prompts, list) or not raw_prompts:
        return {}, (continuity_bible or "").strip()

    resolved: dict[int, DiffusionPrompt] = {}
    fallback_sentences = [str(entry).strip() for entry in sentences]
    for position, entry in enumerate(raw_prompts):
        if not isinstance(entry, Mapping):
            continue
        raw_index = entry.get("index", position)
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            continue
        if index < 0 or index >= total:
            continue
        if index in resolved:
            continue
        prompt_raw = entry.get("prompt")
        negative_raw = entry.get("negative_prompt") if "negative_prompt" in entry else entry.get("negativePrompt")
        prompt = str(prompt_raw).strip() if prompt_raw is not None else ""
        negative_prompt = str(negative_raw).strip() if negative_raw is not None else ""
        prompt = _sanitize_scene_prompt(prompt, fallback=fallback_sentences[index])
        negative_prompt = _sanitize_negative_prompt(negative_prompt)
        resolved[index] = DiffusionPrompt(prompt=prompt, negative_prompt=negative_prompt)

    continuity = parsed.get("continuity_bible")
    continuity_text = str(continuity).strip() if continuity is not None else (continuity_bible or "").strip()
    return resolved, continuity_text


def _prompt_map_batch(
    sentences: Sequence[str],
    *,
    context_prefix: Sequence[str] | None = None,
    context_suffix: Sequence[str] | None = None,
    continuity_bible: str | None = None,
    baseline_prompt: DiffusionPrompt | None = None,
    baseline_notes: str | None = None,
    baseline_source: str | None = None,
    timeout_seconds: int = 180,
) -> DiffusionPromptPlan:
    expected_count = len(sentences or ())
    if expected_count == 0:
        baseline = baseline_prompt or DiffusionPrompt(prompt="")
        return DiffusionPromptPlan(
            prompts=[],
            sources=[],
            continuity_bible=(continuity_bible or "").strip(),
            baseline_prompt=baseline,
            baseline_notes=_sanitize_baseline_notes(baseline_notes),
            baseline_source=str(baseline_source or "fallback"),
            quality={
                "version": 1,
                "total_sentences": 0,
                "llm_requests": 0,
                "initial_missing": 0,
                "final_fallback": 0,
                "retry_attempts": 0,
                "retry_requested": 0,
                "retry_recovered": 0,
                "retry_recovered_unique": 0,
                "initial_coverage_rate": 1.0,
                "llm_coverage_rate": 1.0,
                "fallback_rate": 0.0,
                "retry_success_rate": None,
                "recovery_rate": None,
                "errors": [],
            },
        )

    fallback_baseline = ""
    for entry in sentences or ():
        fallback_baseline = str(entry).strip()
        if fallback_baseline:
            break
    if not fallback_baseline:
        for entry in reversed(tuple(context_prefix or ())):
            fallback_baseline = str(entry).strip()
            if fallback_baseline:
                break
    if not fallback_baseline:
        for entry in context_suffix or ():
            fallback_baseline = str(entry).strip()
            if fallback_baseline:
                break

    baseline_prompt_in = baseline_prompt or DiffusionPrompt(prompt=_sanitize_scene_prompt("", fallback=fallback_baseline))
    baseline_notes_in = _sanitize_baseline_notes(baseline_notes)
    baseline_source_in = str(baseline_source or "fallback")

    payload = {
        "context_prefix": [str(entry).strip() for entry in (context_prefix or ()) if str(entry).strip()][
            -_MAX_LLM_CONTEXT_SENTENCES:
        ],
        "sentences": [str(entry).strip() for entry in (sentences or ())],
        "context_suffix": [str(entry).strip() for entry in (context_suffix or ()) if str(entry).strip()][
            : _MAX_LLM_CONTEXT_SENTENCES
        ],
        "continuity_bible": (continuity_bible or "").strip(),
        "baseline": {
            "prompt": (baseline_prompt_in.prompt or "").strip(),
            "negative_prompt": (baseline_prompt_in.negative_prompt or "").strip(),
            "notes": baseline_notes_in,
        },
    }

    system_prompt = (
        "You create coherent Stable Diffusion 1.5 scene descriptions for a book's photorealistic story reel.\n"
        "The user provides a JSON payload with:\n"
        "- context_prefix: optional sentences before the target range (context only)\n"
        "- sentences: the target sentences that each need an image prompt\n"
        "- context_suffix: optional sentences after the target range (context only)\n"
        "- continuity_bible: optional notes from earlier chunks\n"
        "- baseline: an anchor frame description + layout notes for the overall reel\n"
        "\n"
        "Goal:\n"
        "- Maintain continuity across all prompts (recurring characters, locations, era, visual motifs).\n"
        "- Each target sentence corresponds to ONE realistic frame capturing the key moment.\n"
        "- Use the baseline anchor to keep characters and camera framing consistent across the reel.\n"
        "\n"
        "Output JSON ONLY with keys:\n"
        '- continuity_bible: a compact update (<= 120 words). Keep it stable once established.\n'
        '- baseline: anchor frame description + layout notes (keep stable once established).\n'
        '- prompts: array with EXACTLY one entry per target sentence, in order.\n'
        "\n"
        "The baseline object MUST include:\n"
        "- prompt: English anchor scene description ONLY (no style keywords), <= 45 words\n"
        "- negative_prompt: optional, keep empty unless needed\n"
        "- notes: layout/continuity notes for consistent framing, <= 120 words\n"
        "\n"
        "Each prompts[] entry MUST be an object with:\n"
        "- index: integer (0-based within the provided sentences array)\n"
        "- prompt: English scene description ONLY (no style keywords), <= 45 words\n"
        "- negative_prompt: optional, keep empty unless needed\n"
        "\n"
        "Rules:\n"
        "- Do NOT include style keywords (we add them separately).\n"
        "- Do NOT request readable text.\n"
        "- If the text implies violence or sex, keep depictions non-graphic.\n"
    )

    user_prompt = (
        "Build a consistent prompt plan for the target sentences.\n"
        "Return JSON only.\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )

    errors: list[str] = []
    llm_requests = 0
    parsed: Optional[Mapping[str, Any]] = None
    raw_prompts: Optional[list[Any]] = None
    last_text = ""

    for attempt in range(max(1, _PROMPT_MAP_FULL_RETRY_ATTEMPTS + 1)):
        llm_requests += 1
        with client_scope(None) as client:
            response = client.send_chat_request(
                {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.2, "top_p": 0.9},
                },
                timeout=int(timeout_seconds),
            )
            if response.error:
                last_text = response.text.strip() if response.text else ""
                errors.append(str(response.error))
            else:
                last_text = response.text.strip()

        candidate = _extract_json_object(last_text)
        prompts_candidate = None if candidate is None else candidate.get("prompts")
        if isinstance(candidate, Mapping) and isinstance(prompts_candidate, list) and prompts_candidate:
            parsed = candidate
            raw_prompts = prompts_candidate
            break
        errors.append("LLM did not return valid prompts JSON")

    if parsed is None or raw_prompts is None:
        fallback_sentences = [str(entry).strip() for entry in (sentences or ())]
        prompts = [
            DiffusionPrompt(prompt=_sanitize_scene_prompt("", fallback=fallback)) for fallback in fallback_sentences
        ]
        sources = ["fallback"] * expected_count
        baseline_prompt_out = DiffusionPrompt(prompt=_sanitize_scene_prompt("", fallback=fallback_baseline))
        baseline_source_out = baseline_source_in
        quality = {
            "version": 1,
            "total_sentences": expected_count,
            "llm_requests": llm_requests,
            "initial_missing": expected_count,
            "final_fallback": expected_count,
            "retry_attempts": 0,
            "retry_requested": 0,
            "retry_recovered": 0,
            "retry_recovered_unique": 0,
            "initial_coverage_rate": 0.0 if expected_count else 1.0,
            "llm_coverage_rate": 0.0 if expected_count else 1.0,
            "fallback_rate": 1.0 if expected_count else 0.0,
            "retry_success_rate": None,
            "recovery_rate": None,
            "errors": errors,
        }
        return DiffusionPromptPlan(
            prompts=prompts,
            sources=sources,
            continuity_bible=(continuity_bible or "").strip(),
            baseline_prompt=baseline_prompt_out,
            baseline_notes=baseline_notes_in,
            baseline_source=str(baseline_source_out),
            quality=quality,
        )

    baseline_payload = parsed.get("baseline")
    baseline_prompt_out = baseline_prompt_in
    baseline_notes_out = baseline_notes_in
    baseline_source_out = baseline_source_in
    if isinstance(baseline_payload, Mapping):
        raw_prompt = baseline_payload.get("prompt")
        raw_negative = (
            baseline_payload.get("negative_prompt")
            if "negative_prompt" in baseline_payload
            else baseline_payload.get("negativePrompt")
        )
        raw_notes = baseline_payload.get("notes") if "notes" in baseline_payload else baseline_payload.get("layout_notes")
        prompt_candidate = str(raw_prompt).strip() if raw_prompt is not None else ""
        negative_candidate = str(raw_negative).strip() if raw_negative is not None else ""
        notes_candidate = _sanitize_baseline_notes(raw_notes)
        if prompt_candidate:
            baseline_prompt_out = DiffusionPrompt(
                prompt=_sanitize_scene_prompt(prompt_candidate, fallback=fallback_baseline),
                negative_prompt=_sanitize_negative_prompt(negative_candidate),
            )
            baseline_source_out = "llm"
        if notes_candidate:
            baseline_notes_out = notes_candidate

    output: list[DiffusionPrompt | None] = [None] * expected_count
    sources: list[str | None] = [None] * expected_count
    fallback_sentences = [str(entry).strip() for entry in (sentences or ())]

    for position, entry in enumerate(raw_prompts):
        if not isinstance(entry, Mapping):
            continue
        raw_index = entry.get("index", position)
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            index = position
        if index < 0 or index >= expected_count:
            continue
        prompt_raw = entry.get("prompt")
        negative_raw = entry.get("negative_prompt") if "negative_prompt" in entry else entry.get("negativePrompt")
        prompt = str(prompt_raw).strip() if prompt_raw is not None else ""
        negative_prompt = str(negative_raw).strip() if negative_raw is not None else ""
        prompt = _sanitize_scene_prompt(prompt, fallback=fallback_sentences[index])
        negative_prompt = _sanitize_negative_prompt(negative_prompt)
        output[index] = DiffusionPrompt(prompt=prompt, negative_prompt=negative_prompt)
        sources[index] = "llm"

    missing = [idx for idx, item in enumerate(output) if item is None]
    initial_missing = len(missing)
    retry_requested = 0
    retry_recovered = 0
    recovered_unique: set[int] = set()
    retry_attempts_used = 0

    continuity = parsed.get("continuity_bible")
    continuity_text = str(continuity).strip() if continuity is not None else ""

    for _attempt in range(max(0, _PROMPT_MAP_MISSING_RETRY_ATTEMPTS)):
        if not missing:
            break
        retry_attempts_used += 1
        retry_requested += len(missing)
        llm_requests += 1
        recovered_map, continuity_text = _prompt_map_missing_retry(
            sentences=sentences,
            missing_indices=missing,
            context_prefix=context_prefix,
            context_suffix=context_suffix,
            continuity_bible=continuity_text or (continuity_bible or None),
            baseline_prompt=baseline_prompt_out,
            baseline_notes=baseline_notes_out,
            context_radius=_PROMPT_MAP_MISSING_CONTEXT_RADIUS,
            timeout_seconds=min(int(timeout_seconds), 180),
        )
        recovered_this = 0
        for idx in missing:
            if idx not in recovered_map:
                continue
            output[idx] = recovered_map[idx]
            sources[idx] = "llm_retry"
            recovered_unique.add(idx)
            recovered_this += 1
        retry_recovered += recovered_this
        missing = [idx for idx, item in enumerate(output) if item is None]
        if recovered_this == 0:
            break

    filled: list[DiffusionPrompt] = []
    final_sources: list[str] = []
    final_fallback = 0
    for index, item in enumerate(output):
        if item is None:
            fallback = _sanitize_scene_prompt("", fallback=fallback_sentences[index])
            filled.append(DiffusionPrompt(prompt=fallback))
            final_sources.append("fallback")
            final_fallback += 1
        else:
            filled.append(item)
            final_sources.append(str(sources[index] or "llm"))

    initial_coverage_rate = (
        (expected_count - initial_missing) / expected_count if expected_count else 1.0
    )
    llm_coverage_rate = (
        (expected_count - final_fallback) / expected_count if expected_count else 1.0
    )
    retry_success_rate = (
        retry_recovered / retry_requested if retry_requested else None
    )
    recovery_rate = (
        len(recovered_unique) / initial_missing if initial_missing else None
    )

    quality = {
        "version": 1,
        "total_sentences": expected_count,
        "llm_requests": llm_requests,
        "initial_missing": initial_missing,
        "final_fallback": final_fallback,
        "retry_attempts": retry_attempts_used,
        "retry_requested": retry_requested,
        "retry_recovered": retry_recovered,
        "retry_recovered_unique": len(recovered_unique),
        "initial_coverage_rate": round(initial_coverage_rate, 6),
        "llm_coverage_rate": round(llm_coverage_rate, 6),
        "fallback_rate": round(final_fallback / expected_count, 6) if expected_count else 0.0,
        "retry_success_rate": round(retry_success_rate, 6) if retry_success_rate is not None else None,
        "recovery_rate": round(recovery_rate, 6) if recovery_rate is not None else None,
        "errors": errors,
    }
    return DiffusionPromptPlan(
        prompts=filled,
        sources=final_sources,
        continuity_bible=continuity_text,
        baseline_prompt=baseline_prompt_out,
        baseline_notes=baseline_notes_out,
        baseline_source=baseline_source_out,
        quality=quality,
    )


def sentences_to_diffusion_prompt_plan(
    sentences: Sequence[str],
    *,
    context_prefix: Sequence[str] | None = None,
    context_suffix: Sequence[str] | None = None,
    timeout_seconds: int = 240,
) -> DiffusionPromptPlan:
    """Generate a consistent scene-description prompt plan for ``sentences``.

    The configured LLM receives the full sentence range (plus optional prefix/suffix context) and
    returns a JSON prompt plan. If the range is too large, the helper falls back to chunked requests
    with overlapping context and a shared continuity bible.
    """

    targets = [str(entry) for entry in (sentences or ())]
    if not targets:
        return DiffusionPromptPlan(
            prompts=[],
            sources=[],
            continuity_bible="",
            baseline_prompt=DiffusionPrompt(prompt=""),
            baseline_notes="",
            baseline_source="fallback",
            quality={
                "version": 1,
                "total_sentences": 0,
                "llm_requests": 0,
                "initial_missing": 0,
                "final_fallback": 0,
                "retry_attempts": 0,
                "retry_requested": 0,
                "retry_recovered": 0,
                "retry_recovered_unique": 0,
                "initial_coverage_rate": 1.0,
                "llm_coverage_rate": 1.0,
                "fallback_rate": 0.0,
                "retry_success_rate": None,
                "recovery_rate": None,
                "errors": [],
            },
        )

    total = len(targets)
    if total <= _PROMPT_MAP_MAX_TARGET_SENTENCES:
        return _prompt_map_batch(
            targets,
            context_prefix=context_prefix,
            context_suffix=context_suffix,
            continuity_bible=None,
            baseline_prompt=None,
            baseline_notes=None,
            baseline_source=None,
            timeout_seconds=timeout_seconds,
        )

    overlap = max(0, min(_PROMPT_MAP_OVERLAP_SENTENCES, total))
    continuity_bible = ""
    baseline_prompt: DiffusionPrompt | None = None
    baseline_notes = ""
    baseline_source: str | None = None
    planned_prompts: list[DiffusionPrompt] = []
    planned_sources: list[str] = []
    errors: list[str] = []
    llm_requests = 0
    initial_missing = 0
    final_fallback = 0
    retry_attempts = 0
    retry_requested = 0
    retry_recovered = 0
    retry_recovered_unique = 0
    start = 0
    while start < total:
        end = min(start + _PROMPT_MAP_MAX_TARGET_SENTENCES, total)
        before = []
        after = []
        if start == 0 and context_prefix:
            before.extend([str(entry) for entry in context_prefix])
        if start > 0 and overlap:
            before.extend(targets[max(0, start - overlap) : start])
        if end < total and overlap:
            after.extend(targets[end : min(total, end + overlap)])
        if end >= total and context_suffix:
            after.extend([str(entry) for entry in context_suffix])

        plan = _prompt_map_batch(
            targets[start:end],
            context_prefix=before,
            context_suffix=after,
            continuity_bible=continuity_bible or None,
            baseline_prompt=baseline_prompt,
            baseline_notes=baseline_notes,
            baseline_source=baseline_source,
            timeout_seconds=timeout_seconds,
        )
        planned_prompts.extend(plan.prompts)
        planned_sources.extend(plan.sources)
        continuity_bible = plan.continuity_bible
        if baseline_prompt is None:
            baseline_prompt = plan.baseline_prompt
            baseline_notes = plan.baseline_notes
            baseline_source = plan.baseline_source
        else:
            if baseline_source == "fallback" and plan.baseline_source == "llm":
                baseline_prompt = plan.baseline_prompt
                baseline_notes = plan.baseline_notes or baseline_notes
                baseline_source = plan.baseline_source
            elif not baseline_notes and plan.baseline_notes:
                baseline_notes = plan.baseline_notes
        chunk_quality = plan.quality or {}
        llm_requests += int(chunk_quality.get("llm_requests") or 0)
        initial_missing += int(chunk_quality.get("initial_missing") or 0)
        final_fallback += int(chunk_quality.get("final_fallback") or 0)
        retry_attempts += int(chunk_quality.get("retry_attempts") or 0)
        retry_requested += int(chunk_quality.get("retry_requested") or 0)
        retry_recovered += int(chunk_quality.get("retry_recovered") or 0)
        retry_recovered_unique += int(chunk_quality.get("retry_recovered_unique") or 0)
        batch_errors = chunk_quality.get("errors")
        if isinstance(batch_errors, list):
            errors.extend([str(entry) for entry in batch_errors if str(entry).strip()])
        start = end

    if len(planned_prompts) != total or len(planned_sources) != total:
        padded_prompts = planned_prompts[:total]
        padded_sources = planned_sources[:total]
        while len(padded_prompts) < total:
            fallback = _sanitize_scene_prompt("", fallback=targets[len(padded_prompts)])
            padded_prompts.append(DiffusionPrompt(prompt=fallback))
            padded_sources.append("fallback")
            final_fallback += 1
        while len(padded_sources) < total:
            padded_sources.append("fallback")
        planned_prompts = padded_prompts
        planned_sources = padded_sources
        errors.append("Prompt plan length mismatch; padded missing entries with fallbacks.")

    initial_coverage_rate = (total - initial_missing) / total if total else 1.0
    llm_coverage_rate = (total - final_fallback) / total if total else 1.0
    retry_success_rate = retry_recovered / retry_requested if retry_requested else None
    recovery_rate = retry_recovered_unique / initial_missing if initial_missing else None

    quality = {
        "version": 1,
        "total_sentences": total,
        "llm_requests": llm_requests,
        "initial_missing": initial_missing,
        "final_fallback": final_fallback,
        "retry_attempts": retry_attempts,
        "retry_requested": retry_requested,
        "retry_recovered": retry_recovered,
        "retry_recovered_unique": retry_recovered_unique,
        "initial_coverage_rate": round(initial_coverage_rate, 6),
        "llm_coverage_rate": round(llm_coverage_rate, 6),
        "fallback_rate": round(final_fallback / total, 6) if total else 0.0,
        "retry_success_rate": round(retry_success_rate, 6) if retry_success_rate is not None else None,
        "recovery_rate": round(recovery_rate, 6) if recovery_rate is not None else None,
        "errors": errors,
    }

    return DiffusionPromptPlan(
        prompts=planned_prompts,
        sources=planned_sources,
        continuity_bible=continuity_bible,
        baseline_prompt=baseline_prompt
        or DiffusionPrompt(prompt=_sanitize_scene_prompt("", fallback=targets[0])),
        baseline_notes=baseline_notes,
        baseline_source=str(baseline_source or "fallback"),
        quality=quality,
    )


def sentence_batches_to_diffusion_prompt_plan(
    sentence_batches: Sequence[Sequence[str]],
    *,
    context_prefix: Sequence[str] | None = None,
    context_suffix: Sequence[str] | None = None,
    timeout_seconds: int = 240,
) -> DiffusionPromptPlan:
    """Generate a diffusion prompt plan for grouped sentences.

    Each batch becomes a single prompt target so the resulting prompt represents the batch narrative
    (one image persists across the batch in the interactive reader).
    """

    combined: list[str] = []
    for batch in sentence_batches or ():
        items = [str(entry).strip() for entry in (batch or ()) if str(entry).strip()]
        if not items:
            combined.append("")
            continue
        combined.append("Batch narrative:\n" + "\n".join(f"- {entry}" for entry in items))

    return sentences_to_diffusion_prompt_plan(
        combined,
        context_prefix=context_prefix,
        context_suffix=context_suffix,
        timeout_seconds=timeout_seconds,
    )


def sentences_to_diffusion_prompt_map(
    sentences: Sequence[str],
    *,
    context_prefix: Sequence[str] | None = None,
    context_suffix: Sequence[str] | None = None,
    timeout_seconds: int = 240,
) -> list[DiffusionPrompt]:
    """Backward-compatible helper returning only prompts."""

    plan = sentences_to_diffusion_prompt_plan(
        sentences,
        context_prefix=context_prefix,
        context_suffix=context_suffix,
        timeout_seconds=timeout_seconds,
    )
    return plan.prompts
