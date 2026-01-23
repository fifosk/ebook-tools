"""Batch translation processing for LLM-based translation.

This module handles batch processing of translation and transliteration requests,
including batch building, payload parsing, validation, and LLM communication.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.progress_tracker import ProgressTracker
    from modules.transliteration import TransliterationService

from modules import config_manager as cfg, logging_manager as log_mgr
from modules import llm_batch, prompt_templates, text_normalization as text_norm
from modules import translation_validation as tv
from modules.llm_client import LLMClient
from modules.retry_annotations import is_failure_annotation
from modules.translation_logging import (
    BatchStatsRecorder,
    resolve_llm_batch_log_dir,
    write_llm_batch_artifact,
    TRANSLITERATION_SUBDIR,
)
from modules.transliteration import is_python_transliteration_mode

logger = log_mgr.logger

# Constants
_LLM_REQUEST_ATTEMPTS = 4
_TRANSLATION_RESPONSE_ATTEMPTS = 5
_TRANSLATION_RETRY_DELAY_SECONDS = 1.0


def normalize_llm_batch_size(value: Optional[int]) -> Optional[int]:
    """Normalize batch size to valid range.

    Args:
        value: Batch size to normalize

    Returns:
        Normalized batch size, or None if invalid
    """
    if value is None:
        return None
    try:
        size = int(value)
    except (TypeError, ValueError):
        return None
    if size <= 1:
        return None
    return size


def build_translation_batches(
    sentences: Sequence[str],
    targets: Sequence[str],
    *,
    batch_size: int,
) -> List[Tuple[str, List[Tuple[int, str]]]]:
    """Build batches of sentences grouped by target language.

    Groups consecutive sentences with the same target language into batches
    of up to batch_size items.

    Args:
        sentences: Sentences to translate
        targets: Target language for each sentence
        batch_size: Maximum batch size

    Returns:
        List of (target_language, [(idx, sentence), ...]) tuples
    """
    batches: List[Tuple[str, List[Tuple[int, str]]]] = []
    current_target: Optional[str] = None
    current_items: List[Tuple[int, str]] = []
    for idx, (sentence, target) in enumerate(zip(sentences, targets)):
        if current_target is None:
            current_target = target
        if target != current_target or len(current_items) >= batch_size:
            if current_items:
                batches.append((current_target or "", list(current_items)))
            current_items = []
            current_target = target
        current_items.append((idx, sentence))
    if current_items:
        batches.append((current_target or "", list(current_items)))
    return batches


def chunk_batch_items(
    items: Sequence[Tuple[int, str]],
    *,
    batch_size: int,
) -> List[List[Tuple[int, str]]]:
    """Split batch items into chunks of batch_size.

    Args:
        items: Items to chunk
        batch_size: Maximum chunk size

    Returns:
        List of item chunks
    """
    if batch_size <= 0:
        return [list(items)]
    return [
        list(items[idx : idx + batch_size]) for idx in range(0, len(items), batch_size)
    ]


def extract_batch_items(payload: Any) -> Optional[List[Mapping[str, Any]]]:
    """Extract items list from LLM batch response payload.

    Handles both {"items": [...]} and direct list responses.

    Args:
        payload: Response payload from LLM

    Returns:
        List of item dictionaries, or None if invalid
    """
    if isinstance(payload, Mapping):
        items = payload.get("items")
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        items = payload
    else:
        return None
    if not isinstance(items, list):
        return None
    return [item for item in items if isinstance(item, Mapping)]


def coerce_batch_item_id(
    item: Mapping[str, Any],
    fallback_id: Optional[int],
) -> Optional[int]:
    """Extract item ID from batch response item.

    Tries multiple common field names (id, index, sentence_id, etc.)
    and coerces to integer if possible.

    Args:
        item: Response item dictionary
        fallback_id: Fallback ID if none found

    Returns:
        Item ID, or fallback_id if extraction fails
    """
    for key in ("id", "index", "sentence_id", "sentence", "sentence_number"):
        value = item.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit():
                return int(stripped)
    return fallback_id


def coerce_text_value(value: Any) -> str:
    """Coerce a value to string, returning empty string for None.

    Args:
        value: Value to coerce

    Returns:
        String representation
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def parse_batch_translation_payload(
    payload: Any,
    *,
    input_ids: Sequence[int],
    include_transliteration: bool,
) -> Dict[int, Tuple[str, str]]:
    """Parse LLM batch translation response into results dict.

    Extracts translation and optionally transliteration from each item,
    handling inline transliterations and various field name variations.

    Args:
        payload: LLM response payload
        input_ids: Input item IDs for positional fallback
        include_transliteration: Whether to extract transliteration

    Returns:
        Dict mapping item_id -> (translation, transliteration)
    """
    items = extract_batch_items(payload)
    if not items:
        return {}
    use_positional = len(items) == len(input_ids)
    results: Dict[int, Tuple[str, str]] = {}
    for idx, item in enumerate(items):
        fallback_id = input_ids[idx] if use_positional else None
        item_id = coerce_batch_item_id(item, fallback_id)
        if item_id is None or item_id in results:
            continue
        raw_translation = coerce_text_value(item.get("translation"))
        raw_transliteration = coerce_text_value(
            item.get("transliteration") or item.get("romanization") or item.get("translit")
        )
        if include_transliteration and raw_translation and not raw_transliteration:
            translation_line, inline_translit = text_norm.split_translation_and_transliteration(
                raw_translation
            )
            if inline_translit:
                raw_translation = translation_line or raw_translation
                raw_transliteration = inline_translit
        translation = text_norm.collapse_whitespace(raw_translation.strip())
        transliteration = text_norm.collapse_whitespace(raw_transliteration.strip())
        if include_transliteration and transliteration and not text_norm.is_latin_heavy(transliteration):
            transliteration = ""
        results[item_id] = (translation, transliteration)
    return results


def parse_batch_transliteration_payload(
    payload: Any,
    *,
    input_ids: Sequence[int],
) -> Dict[int, str]:
    """Parse LLM batch transliteration response into results dict.

    Args:
        payload: LLM response payload
        input_ids: Input item IDs for positional fallback

    Returns:
        Dict mapping item_id -> transliteration
    """
    items = extract_batch_items(payload)
    if not items:
        return {}
    use_positional = len(items) == len(input_ids)
    results: Dict[int, str] = {}
    for idx, item in enumerate(items):
        fallback_id = input_ids[idx] if use_positional else None
        item_id = coerce_batch_item_id(item, fallback_id)
        if item_id is None or item_id in results:
            continue
        raw_text = coerce_text_value(
            item.get("transliteration") or item.get("romanization") or item.get("translit")
        )
        transliteration = text_norm.collapse_whitespace(raw_text.strip())
        results[item_id] = transliteration
    return results


def validate_batch_translation(
    original_sentence: str,
    translation_text: str,
    target_language: str,
) -> Optional[str]:
    """Validate a batch translation result.

    Checks for common translation issues like transliteration, truncation,
    missing diacritics, and script mismatches.

    Args:
        original_sentence: Original sentence
        translation_text: Translation to validate
        target_language: Target language

    Returns:
        Error message if validation fails, None if valid
    """
    if not tv.is_valid_translation(translation_text):
        return "Invalid or placeholder translation"
    if tv.is_probable_transliteration(original_sentence, translation_text, target_language):
        return "Transliteration returned instead of translation"
    if tv.is_translation_too_short(original_sentence, translation_text):
        return "Translation shorter than expected"
    missing_diacritics, label = tv.missing_required_diacritics(translation_text, target_language)
    if missing_diacritics:
        return f"Missing {label or 'required diacritics'}"
    script_mismatch, script_label = tv.unexpected_script_used(translation_text, target_language)
    if script_mismatch:
        return f"Unexpected script used; expected {script_label or 'target script'}"
    return None


def validate_batch_transliteration(transliteration_text: str) -> Optional[str]:
    """Validate a batch transliteration result.

    Args:
        transliteration_text: Transliteration to validate

    Returns:
        Error message if validation fails, None if valid
    """
    candidate = transliteration_text or ""
    if not candidate:
        return "Empty transliteration received"
    if not text_norm.is_latin_heavy(candidate):
        return "Non-Latin transliteration received"
    return None


def translate_llm_batch_items(
    batch_items: Sequence[Tuple[int, str]],
    input_language: str,
    target_language: str,
    *,
    include_transliteration: bool,
    resolved_client: LLMClient,
    progress_tracker: Optional["ProgressTracker"],
    timeout_seconds: float,
    batch_log_dir: Optional[Path] = None,
) -> Tuple[Dict[int, Tuple[str, str]], Optional[str], float]:
    """Translate a batch of items using the LLM.

    Args:
        batch_items: Sequence of (item_id, sentence) tuples
        input_language: Source language
        target_language: Target language
        include_transliteration: Whether to request transliteration
        resolved_client: LLM client to use
        progress_tracker: Optional progress tracker
        timeout_seconds: Request timeout
        batch_log_dir: Optional directory for batch logging

    Returns:
        Tuple of (results_dict, error, elapsed_seconds)
        results_dict maps item_id -> (translation, transliteration)
    """
    system_prompt = prompt_templates.make_translation_batch_prompt(
        input_language,
        target_language,
        include_transliteration=include_transliteration,
    )
    request_items = [
        {"id": item_id, "text": sentence} for item_id, sentence in batch_items
    ]
    user_payload = llm_batch.build_json_batch_payload(request_items)
    request_payload = prompt_templates.make_sentence_payload(
        user_payload,
        model=resolved_client.model,
        stream=False,
        system_prompt=system_prompt,
    )
    input_ids = [item_id for item_id, _sentence in batch_items]

    def _payload_has_items(payload: Any) -> bool:
        items = extract_batch_items(payload)
        return bool(items)

    start_time = time.perf_counter()
    last_error: Optional[str] = None
    for attempt in range(1, _TRANSLATION_RESPONSE_ATTEMPTS + 1):
        response = llm_batch.request_json_batch(
            client=resolved_client,
            system_prompt=system_prompt,
            items=request_items,
            timeout_seconds=timeout_seconds,
            max_attempts=_LLM_REQUEST_ATTEMPTS,
            validator=_payload_has_items,
        )
        write_llm_batch_artifact(
            log_dir=batch_log_dir,
            request_items=request_items,
            input_language=input_language,
            target_language=target_language,
            include_transliteration=include_transliteration,
            system_prompt=system_prompt,
            user_payload=user_payload,
            request_payload=request_payload,
            response_payload=response.payload,
            response_raw_text=response.raw_text,
            response_error=response.error,
            elapsed_seconds=response.elapsed,
            attempt=attempt,
            timeout_seconds=timeout_seconds,
            client=resolved_client,
        )
        if response.payload is not None:
            parsed = parse_batch_translation_payload(
                response.payload,
                input_ids=input_ids,
                include_transliteration=include_transliteration,
            )
            if parsed:
                elapsed = time.perf_counter() - start_time
                return parsed, None, elapsed
            last_error = "Empty translation payload"
        else:
            last_error = response.error or "Invalid translation response"
        if progress_tracker is not None and last_error:
            progress_tracker.record_retry("translation", last_error)
        if attempt < _TRANSLATION_RESPONSE_ATTEMPTS:
            time.sleep(_TRANSLATION_RETRY_DELAY_SECONDS)
    elapsed = time.perf_counter() - start_time
    return {}, last_error, elapsed


def transliterate_llm_batch_items(
    batch_items: Sequence[Tuple[int, str]],
    target_language: str,
    *,
    resolved_client: LLMClient,
    progress_tracker: Optional["ProgressTracker"],
    timeout_seconds: float,
    batch_log_dir: Optional[Path] = None,
) -> Tuple[Dict[int, str], Optional[str], float]:
    """Transliterate a batch of items using the LLM.

    Args:
        batch_items: Sequence of (item_id, text) tuples
        target_language: Language of the text to transliterate
        resolved_client: LLM client to use
        progress_tracker: Optional progress tracker
        timeout_seconds: Request timeout
        batch_log_dir: Optional directory for batch logging

    Returns:
        Tuple of (results_dict, error, elapsed_seconds)
        results_dict maps item_id -> transliteration
    """
    system_prompt = prompt_templates.make_transliteration_batch_prompt(target_language)
    request_items = [
        {"id": item_id, "text": sentence} for item_id, sentence in batch_items
    ]
    user_payload = llm_batch.build_json_batch_payload(request_items)
    request_payload = prompt_templates.make_sentence_payload(
        user_payload,
        model=resolved_client.model,
        stream=False,
        system_prompt=system_prompt,
    )
    input_ids = [item_id for item_id, _sentence in batch_items]

    def _payload_has_items(payload: Any) -> bool:
        items = extract_batch_items(payload)
        return bool(items)

    start_time = time.perf_counter()
    last_error: Optional[str] = None
    for attempt in range(1, _TRANSLATION_RESPONSE_ATTEMPTS + 1):
        response = llm_batch.request_json_batch(
            client=resolved_client,
            system_prompt=system_prompt,
            items=request_items,
            timeout_seconds=timeout_seconds,
            max_attempts=_LLM_REQUEST_ATTEMPTS,
            validator=_payload_has_items,
        )
        write_llm_batch_artifact(
            operation="transliteration",
            log_dir=batch_log_dir,
            request_items=request_items,
            input_language=target_language,
            target_language="latin",
            include_transliteration=True,
            system_prompt=system_prompt,
            user_payload=user_payload,
            request_payload=request_payload,
            response_payload=response.payload,
            response_raw_text=response.raw_text,
            response_error=response.error,
            elapsed_seconds=response.elapsed,
            attempt=attempt,
            timeout_seconds=timeout_seconds,
            client=resolved_client,
        )
        if response.payload is not None:
            parsed = parse_batch_transliteration_payload(
                response.payload,
                input_ids=input_ids,
            )
            if parsed:
                elapsed = time.perf_counter() - start_time
                return parsed, None, elapsed
            last_error = "Empty transliteration payload"
        else:
            last_error = response.error or "Invalid transliteration response"
        if progress_tracker is not None and last_error:
            progress_tracker.record_retry("transliteration", last_error)
        if attempt < _TRANSLATION_RESPONSE_ATTEMPTS:
            time.sleep(_TRANSLATION_RETRY_DELAY_SECONDS)
    elapsed = time.perf_counter() - start_time
    return {}, last_error, elapsed


def resolve_batch_transliterations(
    batch_items: Sequence[Tuple[int, str]],
    target_language: str,
    *,
    transliterator: "TransliterationService",
    transliteration_mode: Optional[str],
    transliteration_client: Optional[LLMClient],
    local_client: LLMClient,
    progress_tracker: Optional["ProgressTracker"],
    batch_size: Optional[int],
    batch_log_dir: Optional[Path],
    batch_stats: Optional[BatchStatsRecorder],
) -> Dict[int, str]:
    """Resolve transliterations for a batch of items.

    First attempts local Python transliteration, then falls back to LLM
    batch transliteration for items that couldn't be handled locally.

    Args:
        batch_items: Sequence of (item_id, text) tuples
        target_language: Language of the text
        transliterator: Transliteration service to use
        transliteration_mode: Mode for transliteration
        transliteration_client: Optional dedicated LLM client for transliteration
        local_client: Fallback LLM client
        progress_tracker: Optional progress tracker
        batch_size: Maximum batch size for LLM requests
        batch_log_dir: Optional directory for batch logging
        batch_stats: Optional batch statistics recorder

    Returns:
        Dict mapping item_id -> transliteration
    """
    if not batch_items:
        return {}

    resolved_client = transliteration_client or local_client
    python_only = is_python_transliteration_mode(transliteration_mode)
    results: Dict[int, str] = {}

    if python_only:
        for idx, text in batch_items:
            result = transliterator.transliterate(
                text,
                target_language,
                client=resolved_client,
                progress_tracker=progress_tracker,
                mode=transliteration_mode,
            )
            results[idx] = text_norm.collapse_whitespace(result.text.strip())
        return results

    pending: List[Tuple[int, str]] = []
    for idx, text in batch_items:
        local_result = transliterator.transliterate(
            text,
            target_language,
            client=resolved_client,
            progress_tracker=progress_tracker,
            mode="python",
        )
        local_text = text_norm.collapse_whitespace(local_result.text.strip())
        if local_text and not is_failure_annotation(local_text) and not text_norm.is_placeholder_value(local_text):
            results[idx] = local_text
        else:
            pending.append((idx, text))

    if not pending:
        return results

    use_batch = bool(batch_size and len(pending) > 1)
    if use_batch and not prompt_templates.transliteration_supports_json_batch(
        resolved_client.model
    ):
        if resolved_client.debug_enabled:
            logger.debug(
                "Disabling JSON batch transliteration for model %s",
                resolved_client.model,
            )
        use_batch = False

    if use_batch:
        chunks = chunk_batch_items(pending, batch_size=batch_size or len(pending))
        if batch_stats is not None:
            batch_stats.add_total(len(chunks))
        for chunk in chunks:
            batch_map, _error, _elapsed = transliterate_llm_batch_items(
                chunk,
                target_language,
                resolved_client=resolved_client,
                progress_tracker=progress_tracker,
                timeout_seconds=cfg.get_translation_llm_timeout_seconds(),
                batch_log_dir=batch_log_dir,
            )
            if batch_stats is not None:
                batch_stats.record(_elapsed, len(chunk))
            for idx, text in chunk:
                transliteration = text_norm.collapse_whitespace(
                    (batch_map.get(idx) or "").strip()
                )
                error = validate_batch_transliteration(transliteration)
                if error:
                    if progress_tracker is not None:
                        progress_tracker.record_retry("transliteration", error)
                    transliteration = ""
                if transliteration:
                    results[idx] = transliteration
                    continue
                fallback_result = transliterator.transliterate(
                    text,
                    target_language,
                    client=resolved_client,
                    progress_tracker=progress_tracker,
                    mode=transliteration_mode,
                )
                results[idx] = text_norm.collapse_whitespace(
                    fallback_result.text.strip()
                )
        return results

    for idx, text in pending:
        fallback_result = transliterator.transliterate(
            text,
            target_language,
            client=resolved_client,
            progress_tracker=progress_tracker,
            mode=transliteration_mode,
        )
        results[idx] = text_norm.collapse_whitespace(fallback_result.text.strip())
    return results
