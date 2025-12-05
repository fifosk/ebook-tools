"""Translation helpers shared by subtitle processing and dubbing."""

from __future__ import annotations

from typing import Optional

from modules.llm_client import create_client
from modules.retry_annotations import format_retry_failure, is_failure_annotation
from modules.translation_engine import _unexpected_script_used, translate_sentence_simple

from .common import logger


def _translate_text(
    text: str,
    *,
    source_language: str,
    target_language: str,
    llm_model: Optional[str],
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
