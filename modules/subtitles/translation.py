"""Translation helpers shared by subtitle processing and dubbing."""

from __future__ import annotations

import re
import unicodedata
from typing import Optional, TYPE_CHECKING

from modules.llm_client import create_client
from modules.retry_annotations import format_retry_failure, is_failure_annotation
from modules.translation_engine import _unexpected_script_used, translate_sentence_simple

from .common import logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from modules.progress_tracker import ProgressTracker


_REPEATED_CHAR_PATTERN = re.compile(r"(.)\1{11,}")


def _looks_like_gibberish_translation(*, source: str, candidate: str) -> bool:
    """Return True when a translation looks suspiciously corrupted/repetitive."""

    candidate_text = " ".join((candidate or "").split())
    if not candidate_text:
        return True

    source_text = " ".join((source or "").split())
    if source_text:
        # Hard guardrail: very large expansions are almost always a bad model response.
        if len(candidate_text) > max(600, len(source_text) * 10 + 200):
            return True

    if _REPEATED_CHAR_PATTERN.search(candidate_text):
        return True

    # Token repetition ("mmm mmm mmm ...", or the same word repeated).
    tokens = candidate_text.split()
    if len(tokens) >= 20:
        counts: dict[str, int] = {}
        max_count = 0
        for token in tokens:
            normalized = token.strip(".,!?؛،:;\"'()[]{}").lower()
            if not normalized:
                continue
            next_count = counts.get(normalized, 0) + 1
            counts[normalized] = next_count
            if next_count > max_count:
                max_count = next_count
        if max_count >= 10:
            return True
        if tokens and max_count / max(1, len(tokens)) >= 0.45:
            return True

    # Character diversity / letter ratio guard.
    non_space_chars = [ch for ch in candidate_text if not ch.isspace()]
    if len(non_space_chars) >= 80:
        unique_ratio = len(set(non_space_chars)) / max(1, len(non_space_chars))
        if unique_ratio < 0.12:
            return True

    if len(non_space_chars) >= 40:
        letter_or_number = sum(
            1
            for ch in non_space_chars
            if (category := unicodedata.category(ch)) and category[0] in {"L", "N"}
        )
        if letter_or_number / max(1, len(non_space_chars)) < 0.25:
            return True

    return False


def _translate_text(
    text: str,
    *,
    source_language: str,
    target_language: str,
    llm_model: Optional[str],
    translation_provider: Optional[str] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
) -> str:
    """
    Translate subtitle text with optional model override and enforce that the
    expected script dominates the output.
    """

    def _single_pass(client_override=None) -> str:
        return translate_sentence_simple(
            text,
            source_language,
            target_language,
            include_transliteration=False,
            client=client_override,
            translation_provider=translation_provider,
            progress_tracker=progress_tracker,
        )

    max_script_retries = 2
    last_error: Optional[str] = None

    def _attempt(client_override=None) -> Optional[str]:
        nonlocal last_error
        try:
            candidate = _single_pass(client_override)
        except Exception:  # pragma: no cover - log and re-raise via translation failure
            logger.error(
                "Unable to translate subtitle cue with model %s",
                llm_model or "default",
                exc_info=True,
            )
            raise
        if is_failure_annotation(candidate):
            return candidate
        mismatch, label = _unexpected_script_used(candidate, target_language)
        if mismatch:
            last_error = f"Unexpected script; expected {label or 'target script'}"
            logger.debug(
                "Retrying subtitle translation due to script mismatch (target=%s, reason=%s)",
                target_language,
                last_error,
            )
            return None
        if _looks_like_gibberish_translation(source=text, candidate=candidate):
            last_error = "Gibberish translation detected"
            logger.debug(
                "Retrying subtitle translation due to gibberish output (target=%s, source_len=%s, candidate_len=%s)",
                target_language,
                len(text or ""),
                len(candidate or ""),
            )
            return None
        return candidate

    if llm_model:
        with create_client(model=llm_model) as override_client:
            for _ in range(max_script_retries + 1):
                result = _attempt(override_client)
                if result is not None:
                    return result
    else:
        for _ in range(max_script_retries + 1):
            result = _attempt(None)
            if result is not None:
                return result

    return format_retry_failure(
        "translation",
        max_script_retries + 1,
        reason=last_error or "Unexpected script in translation",
    )


__all__ = ["_translate_text"]
