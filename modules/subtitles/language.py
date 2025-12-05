"""Language helpers for subtitle processing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, TYPE_CHECKING

from modules import prompt_templates
from modules.core.rendering.constants import LANGUAGE_CODES, NON_LATIN_LANGUAGES
from modules.llm_client import create_client

from .common import logger
from .text import _normalize_text

if TYPE_CHECKING:  # pragma: no cover
    from .models import SubtitleCue, SubtitleJobOptions


def _target_uses_non_latin_script(language: str) -> bool:
    """Return True when ``language`` should receive transliteration output."""

    normalized = (language or "").strip()
    if not normalized:
        return False
    normalized_lower = normalized.lower()
    # Accept both human-readable names and language codes.
    for candidate in NON_LATIN_LANGUAGES:
        if candidate.lower() == normalized_lower:
            return True
    for name, code in LANGUAGE_CODES.items():
        if name in NON_LATIN_LANGUAGES and code.lower() == normalized_lower:
            return True
    return False


def _normalize_language_label(value: str) -> str:
    normalized = (value or "").strip().casefold()
    normalized = normalized.replace("-", "").replace("_", "").replace(" ", "")
    return normalized


def _languages_match(first: str, second: str) -> bool:
    return _normalize_language_label(first) == _normalize_language_label(second)


def _gather_language_sample(
    cues: Sequence["SubtitleCue"],
    *,
    max_cues: int = 3,
    max_chars: int = 500,
) -> str:
    """Return a compact text sample from the first few subtitle cues."""

    buffer: List[str] = []
    total_chars = 0
    for cue in cues:
        text = _normalize_text(cue.as_text())
        if not text:
            continue
        buffer.append(text)
        total_chars += len(text)
        if len(buffer) >= max_cues or total_chars >= max_chars:
            break
    sample = "\n".join(buffer).strip()
    if len(sample) > max_chars:
        return sample[:max_chars]
    return sample


def _detect_language_from_sample(
    sample_text: str,
    *,
    llm_model: Optional[str] = None,
) -> Optional[str]:
    """Best-effort language detection using an LLM."""

    if not sample_text:
        return None
    try:
        with create_client(model=llm_model) as client:
            payload = prompt_templates.make_sentence_payload(
                f"{prompt_templates.SOURCE_START}\n{sample_text}\n{prompt_templates.SOURCE_END}",
                model=client.model,
                stream=False,
                system_prompt=(
                    "Identify the primary language of the provided subtitle excerpt. "
                    "Respond with ONLY the language name in English (e.g., 'English', 'Spanish') "
                    "without punctuation, commentary, or multiple options."
                ),
            )
            response = client.send_chat_request(payload, max_attempts=2, timeout=30)
    except Exception:  # pragma: no cover - best effort detection
        logger.warning("Unable to detect subtitle language from sample", exc_info=True)
        return None

    candidate = response.text.strip() if response and response.text else ""
    if not candidate:
        return None
    return candidate.splitlines()[0].strip()


def _resolve_language_context(
    cues: Sequence["SubtitleCue"],
    options: "SubtitleJobOptions",
) -> "SubtitleLanguageContext":
    sample = _gather_language_sample(cues)
    detected_language = _detect_language_from_sample(sample, llm_model=options.llm_model)
    detection_source = "llm_sample" if detected_language else "configured_input_language"
    resolved_detected = detected_language or options.input_language
    origin_language = options.original_language or resolved_detected
    translation_source_language = resolved_detected or origin_language
    return SubtitleLanguageContext(
        detected_language=resolved_detected,
        detection_source=detection_source,
        detection_sample=sample,
        translation_source_language=translation_source_language,
        origin_language=origin_language,
        origin_translation_needed=not _languages_match(resolved_detected, origin_language),
    )


@dataclass(slots=True)
class SubtitleLanguageContext:
    """Resolved language details for a subtitle job."""

    detected_language: str
    detection_source: str
    detection_sample: str
    translation_source_language: str
    origin_language: str
    origin_translation_needed: bool


__all__ = [
    "SubtitleLanguageContext",
    "_detect_language_from_sample",
    "_gather_language_sample",
    "_languages_match",
    "_normalize_language_label",
    "_resolve_language_context",
    "_target_uses_non_latin_script",
]
