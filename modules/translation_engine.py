"""Translation engine utilities for ebook-tools."""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
from dataclasses import dataclass
from queue import Full, Queue
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple, TYPE_CHECKING

import regex

if TYPE_CHECKING:
    from concurrent.futures import Future
    from modules.progress_tracker import ProgressTracker

from modules import config_manager as cfg
from modules import fallbacks
from modules import logging_manager as log_mgr
from modules import observability, prompt_templates
from modules import llm_batch
from modules import llm_client_manager
from modules import language_policies
from modules import text_normalization as text_norm
from modules import translation_validation as tv
from modules.text import split_highlight_tokens, align_token_counts
from modules.retry_annotations import format_retry_failure, is_failure_annotation
from modules.llm_client import LLMClient
from modules.transliteration import (
    TransliterationService,
    get_transliterator,
    is_python_transliteration_mode,
)
from modules.translation_providers import (
    check_googletrans_health,
    normalize_translation_provider,
    resolve_googletrans_language,
    translate_with_googletrans,
)
from modules.translation_workers import AsyncWorkerPool, ThreadWorkerPool
from modules.translation_logging import (
    BatchStatsRecorder,
    resolve_llm_batch_log_dir,
    sanitize_batch_component,
    write_llm_batch_artifact,
    TRANSLATION_SUBDIR,
    TRANSLITERATION_SUBDIR,
)
from modules.translation_batch import (
    normalize_llm_batch_size,
    build_translation_batches,
    chunk_batch_items,
    extract_batch_items,
    coerce_batch_item_id,
    coerce_text_value,
    parse_batch_translation_payload,
    parse_batch_transliteration_payload,
    validate_batch_translation,
    validate_batch_transliteration,
    translate_llm_batch_items,
    transliterate_llm_batch_items,
    resolve_batch_transliterations,
)

logger = log_mgr.logger

_TRANSLATION_RESPONSE_ATTEMPTS = 5
_TRANSLATION_RETRY_DELAY_SECONDS = 1.0
_LLM_REQUEST_ATTEMPTS = 4
# Batch logging constants moved to translation_logging module
_LLM_BATCH_TRANSLATION_SUBDIR = TRANSLATION_SUBDIR
_LLM_BATCH_TRANSLITERATION_SUBDIR = TRANSLITERATION_SUBDIR


def _should_include_transliteration(
    include_transliteration: bool,
    target_language: str,
) -> bool:
    return bool(
        include_transliteration
        and language_policies.is_non_latin_language_hint(target_language)
    )


# BatchStatsRecorder class moved to translation_logging module
_BatchStatsRecorder = BatchStatsRecorder


# Batch logging functions moved to translation_logging module
_resolve_llm_batch_log_dir = resolve_llm_batch_log_dir
_sanitize_batch_component = sanitize_batch_component
_write_llm_batch_artifact = write_llm_batch_artifact


# GoogleTrans provider functions delegated to translation_providers module
_check_googletrans_health = check_googletrans_health
_normalize_translation_provider = normalize_translation_provider
_resolve_googletrans_language = resolve_googletrans_language
_translate_with_googletrans = translate_with_googletrans

# Batch processing functions delegated to translation_batch module
_normalize_llm_batch_size = normalize_llm_batch_size
_build_translation_batches = build_translation_batches
_chunk_batch_items = chunk_batch_items
_extract_batch_items = extract_batch_items
_coerce_batch_item_id = coerce_batch_item_id
_coerce_text_value = coerce_text_value
_parse_batch_translation_payload = parse_batch_translation_payload
_parse_batch_transliteration_payload = parse_batch_transliteration_payload
_validate_batch_translation = validate_batch_translation
_validate_batch_transliteration = validate_batch_transliteration
_translate_llm_batch_items = translate_llm_batch_items
_transliterate_llm_batch_items = transliterate_llm_batch_items
_resolve_batch_transliterations = resolve_batch_transliterations


def _translate_with_llm(
    sentence: str,
    input_language: str,
    target_language: str,
    *,
    include_transliteration: bool,
    resolved_client: LLMClient,
    progress_tracker: Optional["ProgressTracker"],
    timeout_seconds: float,
) -> tuple[str, Optional[str], float]:
    payload, _system_prompt, request_mode = prompt_templates.make_translation_payload(
        sentence,
        input_language,
        target_language,
        model=resolved_client.model,
        stream=True,
        include_transliteration=include_transliteration,
        llm_source=resolved_client.llm_source,
    )

    start_time = time.perf_counter()
    last_error: Optional[str] = None
    best_translation: Optional[str] = None
    best_score = -1
    fatal_violation = False
    for attempt in range(1, _TRANSLATION_RESPONSE_ATTEMPTS + 1):
        attempt_error: Optional[str] = None
        if request_mode == "completion":
            response = resolved_client.send_completion_request(
                payload,
                max_attempts=_LLM_REQUEST_ATTEMPTS,
                timeout=timeout_seconds,
                validator=_valid_translation,
                backoff_seconds=1.0,
            )
        else:
            response = resolved_client.send_chat_request(
                payload,
                max_attempts=_LLM_REQUEST_ATTEMPTS,
                timeout=timeout_seconds,
                validator=_valid_translation,
                backoff_seconds=1.0,
            )

        if response.text:
            cleaned_text = text_norm.collapse_whitespace(response.text.strip())
            if cleaned_text and not text_norm.is_placeholder_translation(cleaned_text):
                translation_text, transliteration_text = text_norm.split_translation_and_transliteration(
                    cleaned_text
                )
                score = _letter_count(translation_text)
                if score > best_score:
                    best_translation = cleaned_text
                    best_score = score
                if _is_probable_transliteration(
                    sentence, translation_text, target_language
                ):
                    attempt_error = "Transliteration returned instead of translation"
                    if resolved_client.debug_enabled:
                        logger.debug(
                            "Retrying translation due to transliteration on attempt %s/%s",
                            attempt,
                            _TRANSLATION_RESPONSE_ATTEMPTS,
                        )
                elif _is_translation_too_short(sentence, translation_text):
                    attempt_error = "Translation shorter than expected"
                    if resolved_client.debug_enabled:
                        logger.debug(
                            "Retrying translation due to short response (%s/%s)",
                            attempt,
                            _TRANSLATION_RESPONSE_ATTEMPTS,
                        )
                else:
                    missing_diacritics, label = _missing_required_diacritics(
                        translation_text, target_language
                    )
                    if missing_diacritics:
                        attempt_error = f"Missing {label or 'required diacritics'}"
                        if resolved_client.debug_enabled:
                            logger.debug(
                                "Retrying translation due to missing diacritics (%s/%s)",
                                attempt,
                                _TRANSLATION_RESPONSE_ATTEMPTS,
                            )
                    if not attempt_error:
                        script_mismatch, script_label = _unexpected_script_used(
                            translation_text, target_language
                        )
                        if script_mismatch:
                            attempt_error = (
                                f"Unexpected script used; expected {script_label or 'target script'}"
                            )
                            fatal_violation = True
                            if resolved_client.debug_enabled:
                                logger.debug(
                                    "Retrying translation due to unexpected script (%s/%s)",
                                    attempt,
                                    _TRANSLATION_RESPONSE_ATTEMPTS,
                                )
                if not attempt_error and _is_segmentation_ok(
                    sentence, cleaned_text, target_language, translation_text=translation_text
                ):
                    # Check token alignment between translation and transliteration
                    if include_transliteration and transliteration_text:
                        token_alignment_error = tv.get_token_alignment_error(
                            translation_text, transliteration_text, target_language
                        )
                        if token_alignment_error:
                            attempt_error = token_alignment_error
                            if resolved_client.debug_enabled:
                                logger.debug(
                                    "Retrying translation due to token count mismatch (%s/%s): %s",
                                    attempt,
                                    _TRANSLATION_RESPONSE_ATTEMPTS,
                                    token_alignment_error,
                                )
                    if not attempt_error:
                        elapsed = time.perf_counter() - start_time
                        return cleaned_text, None, elapsed
                if not attempt_error:
                    attempt_error = "Unsegmented translation received"
                    if resolved_client.debug_enabled:
                        logger.debug(
                            "Retrying translation due to missing word spacing (%s/%s)",
                            attempt,
                            _TRANSLATION_RESPONSE_ATTEMPTS,
                        )
            else:
                attempt_error = "Placeholder translation received"
                if resolved_client.debug_enabled:
                    logger.debug(
                        "Retrying translation due to placeholder response (%s/%s)",
                        attempt,
                        _TRANSLATION_RESPONSE_ATTEMPTS,
                    )
        else:
            attempt_error = response.error or "Empty translation response"
            if resolved_client.debug_enabled and response.error:
                logger.debug(
                    "Translation attempt %s/%s failed: %s",
                    attempt,
                    _TRANSLATION_RESPONSE_ATTEMPTS,
                    response.error,
                )

        if attempt_error:
            last_error = attempt_error
            if resolved_client.debug_enabled:
                logger.debug(
                    "Translation attempt %s/%s failed validation: %s",
                    attempt,
                    _TRANSLATION_RESPONSE_ATTEMPTS,
                    attempt_error,
                )
            if progress_tracker is not None:
                progress_tracker.record_retry("translation", attempt_error)

        if attempt < _TRANSLATION_RESPONSE_ATTEMPTS:
            time.sleep(_TRANSLATION_RETRY_DELAY_SECONDS)

    elapsed = time.perf_counter() - start_time
    if resolved_client.debug_enabled and last_error:
        logger.debug("Translation failed after retries: %s", last_error)
    if fatal_violation:
        return (
            format_retry_failure(
                "translation",
                _TRANSLATION_RESPONSE_ATTEMPTS,
                reason=last_error or "script validation failed",
            ),
            last_error,
            elapsed,
        )
    if last_error and "diacritic" in last_error.lower() and best_translation:
        if resolved_client.debug_enabled:
            logger.debug(
                "Returning best available translation without diacritics after retries"
            )
        return best_translation, last_error, elapsed
    if last_error and best_translation:
        if resolved_client.debug_enabled:
            logger.debug(
                "Returning best available translation after retries despite error: %s",
                last_error,
            )
        return best_translation, last_error, elapsed
    failure_reason = last_error or "no response from LLM"
    return (
        format_retry_failure(
            "translation",
            _TRANSLATION_RESPONSE_ATTEMPTS,
            reason=failure_reason,
        ),
        failure_reason,
        elapsed,
    )


def _is_timeout_error(reason: Optional[str]) -> bool:
    if not reason:
        return False
    lowered = reason.lower()
    return "timeout" in lowered or "timed out" in lowered


# Worker pool classes moved to translation_workers module


@dataclass(slots=True)
class TranslationTask:
    """Unit of work produced by the translation pipeline."""

    index: int
    sentence_number: int
    sentence: str
    target_language: str
    translation: str
    transliteration: str = ""


def configure_default_client(**kwargs) -> None:
    """Adjust the fallback client settings used when no explicit client is provided."""

    llm_client_manager.configure_default_client(**kwargs)


# Validation functions delegated to translation_validation module
_valid_translation = tv.is_valid_translation
_letter_count = tv.letter_count
_is_probable_transliteration = tv.is_probable_transliteration
_is_translation_too_short = tv.is_translation_too_short
_missing_required_diacritics = tv.missing_required_diacritics
_unexpected_script_used = tv.unexpected_script_used


def translate_sentence_simple(
    sentence: str,
    input_language: str,
    target_language: str,
    *,
    include_transliteration: bool = False,
    translation_provider: Optional[str] = None,
    client: Optional[LLMClient] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
) -> str:
    """Translate a sentence using the configured translation provider."""

    include_transliteration = _should_include_transliteration(
        include_transliteration, target_language
    )
    provider = _normalize_translation_provider(translation_provider)
    timeout_seconds = cfg.get_translation_llm_timeout_seconds()
    fallback_model = cfg.get_translation_fallback_model()
    fallback_active = fallbacks.is_llm_fallback_active(progress_tracker)

    if provider == "googletrans" and not fallback_active:
        trigger = "googletrans_error"
        dest_code = _resolve_googletrans_language(target_language, fallback=None)
        if not dest_code:
            google_error = f"Unsupported googletrans language: {target_language}"
            google_text = format_retry_failure(
                "translation",
                _TRANSLATION_RESPONSE_ATTEMPTS,
                reason=google_error,
            )
            trigger = "googletrans_unsupported_language"
        else:
            google_text, google_error = _translate_with_googletrans(
                sentence,
                input_language,
                target_language,
                progress_tracker=progress_tracker,
            )
        if not is_failure_annotation(google_text):
            return google_text
        fallback_reason = google_error or "Google Translate error"
        detail = fallbacks.record_translation_fallback(
            progress_tracker,
            trigger=trigger,
            reason=fallback_reason,
            source_provider="googletrans",
            fallback_model=fallback_model,
        )
        model_override = (detail or {}).get("fallback_model") if detail else None
        model_override = model_override or fallback_model
        if model_override:
            fallback_client = fallbacks.get_fallback_llm_client(model_override)
            with llm_client_manager.client_scope(fallback_client) as resolved_client:
                translation, _error, _elapsed = _translate_with_llm(
                    sentence,
                    input_language,
                    target_language,
                    include_transliteration=include_transliteration,
                    resolved_client=resolved_client,
                    progress_tracker=progress_tracker,
                    timeout_seconds=timeout_seconds,
                )
                return translation
        return google_text

    if provider == "googletrans" and fallback_active:
        model_override = fallbacks.get_llm_fallback_model(progress_tracker) or fallback_model
        fallback_client = (
            fallbacks.get_fallback_llm_client(model_override) if model_override else None
        )
        with llm_client_manager.client_scope(fallback_client or client) as resolved_client:
            translation, _error, _elapsed = _translate_with_llm(
                sentence,
                input_language,
                target_language,
                include_transliteration=include_transliteration,
                resolved_client=resolved_client,
                progress_tracker=progress_tracker,
                timeout_seconds=timeout_seconds,
            )
            return translation

    model_override = fallbacks.get_llm_fallback_model(progress_tracker) or None
    fallback_client = (
        fallbacks.get_fallback_llm_client(model_override) if fallback_active and model_override else None
    )
    with llm_client_manager.client_scope(fallback_client or client) as resolved_client:
        current_model = resolved_client.model
        translation, last_error, elapsed = _translate_with_llm(
            sentence,
            input_language,
            target_language,
            include_transliteration=include_transliteration,
            resolved_client=resolved_client,
            progress_tracker=progress_tracker,
            timeout_seconds=timeout_seconds,
        )

    if not fallback_active:
        if timeout_seconds > 0 and elapsed > timeout_seconds:
            reason = f"LLM response exceeded {timeout_seconds:.0f}s ({elapsed:.1f}s)"
            fallbacks.record_translation_fallback(
                progress_tracker,
                trigger="llm_timeout",
                reason=reason,
                source_provider="llm",
                fallback_model=fallback_model,
                elapsed_seconds=elapsed,
            )
        if is_failure_annotation(translation):
            reason = last_error or "LLM translation failed"
            trigger = "llm_timeout" if _is_timeout_error(reason) else "llm_error"
            detail = fallbacks.record_translation_fallback(
                progress_tracker,
                trigger=trigger,
                reason=reason,
                source_provider="llm",
                fallback_model=fallback_model,
            )
            model_override = (detail or {}).get("fallback_model") if detail else None
            model_override = model_override or fallback_model
            if model_override and current_model.strip().lower() != model_override.strip().lower():
                fallback_client = fallbacks.get_fallback_llm_client(model_override)
                with llm_client_manager.client_scope(fallback_client) as resolved_client:
                    translation, _error, _elapsed = _translate_with_llm(
                        sentence,
                        input_language,
                        target_language,
                        include_transliteration=include_transliteration,
                        resolved_client=resolved_client,
                        progress_tracker=progress_tracker,
                        timeout_seconds=timeout_seconds,
                    )
    return translation


_is_segmentation_ok = tv.is_segmentation_ok


def _normalize_target_sequence(
    target_language: str | Sequence[str],
    sentence_count: int,
) -> List[str]:
    if isinstance(target_language, str):
        return [target_language] * sentence_count
    if not target_language:
        return [""] * sentence_count
    if len(target_language) == 1 and sentence_count > 1:
        return list(target_language) * sentence_count
    if len(target_language) != sentence_count:
        raise ValueError("target_language sequence length must match sentences")
    return list(target_language)


def translate_batch(
    sentences: Sequence[str],
    input_language: str,
    target_language: str | Sequence[str],
    *,
    include_transliteration: bool = False,
    transliteration_mode: Optional[str] = None,
    transliteration_client: Optional[LLMClient] = None,
    transliterator: Optional[TransliterationService] = None,
    translation_provider: Optional[str] = None,
    max_workers: Optional[int] = None,
    llm_batch_size: Optional[int] = None,
    client: Optional[LLMClient] = None,
    worker_pool: Optional[ThreadWorkerPool] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
    sentence_numbers: Optional[Sequence[int]] = None,
) -> List[str]:
    """Translate ``sentences`` concurrently while preserving order."""

    if not sentences:
        return []

    targets = _normalize_target_sequence(target_language, len(sentences))
    worker_count = max_workers or cfg.get_thread_count()
    worker_count = max(1, min(worker_count, len(sentences)))
    provider = _normalize_translation_provider(translation_provider)
    transliterator = transliterator or get_transliterator()
    include_transliteration_any = include_transliteration and any(
        language_policies.is_non_latin_language_hint(target) for target in targets
    )

    results: List[str] = ["" for _ in sentences]
    sentence_ids: Optional[List[int]] = None
    if sentence_numbers is not None:
        try:
            sentence_ids = [int(value) for value in sentence_numbers]
        except (TypeError, ValueError):
            sentence_ids = None
        if sentence_ids is not None and len(sentence_ids) != len(sentences):
            sentence_ids = None

    with llm_client_manager.client_scope(client) as resolved_client:
        batch_size = (
            _normalize_llm_batch_size(llm_batch_size) if provider == "llm" else None
        )
        if batch_size and not prompt_templates.translation_supports_json_batch(
            resolved_client.model
        ):
            if resolved_client.debug_enabled:
                logger.debug(
                    "Disabling JSON batch translation for model %s",
                    resolved_client.model,
                )
            batch_size = None
        batch_log_dir = _resolve_llm_batch_log_dir() if batch_size else None
        transliteration_batch_size = (
            _normalize_llm_batch_size(llm_batch_size) if include_transliteration_any else None
        )
        transliteration_batch_log_dir = (
            _resolve_llm_batch_log_dir(_LLM_BATCH_TRANSLITERATION_SUBDIR)
            if transliteration_batch_size
            else None
        )
        batch_stats = None
        transliteration_stats = None
        if batch_size:
            batches = _build_translation_batches(
                sentences, targets, batch_size=batch_size
            )
            batch_stats = _BatchStatsRecorder(
                batch_size=batch_size,
                progress_tracker=progress_tracker,
                metadata_key="translation_batch_stats",
                total_batches=len(batches),
                items_total=len(sentences),
            )
            batch_stats.set_total(len(batches), items_total=len(sentences))
            if transliteration_batch_size:
                transliteration_stats = _BatchStatsRecorder(
                    batch_size=transliteration_batch_size,
                    progress_tracker=progress_tracker,
                    metadata_key="transliteration_batch_stats",
                    items_total=len(sentences),
                )
            pool = worker_pool or ThreadWorkerPool(max_workers=worker_count)
            own_pool = worker_pool is None
            pool_mode = getattr(pool, "mode", "thread")
            if pool_mode != "thread":
                raise RuntimeError(
                    "translate_batch does not support asynchronous worker pools in synchronous mode"
                )

            def _translate_batch(
                target: str, items: Sequence[Tuple[int, str]]
            ) -> List[Tuple[int, str]]:
                include_transliteration_for_target = _should_include_transliteration(
                    include_transliteration_any, target
                )
                translation_map, _error, elapsed = _translate_llm_batch_items(
                    items,
                    input_language,
                    target,
                    include_transliteration=include_transliteration_for_target,
                    resolved_client=resolved_client,
                    progress_tracker=progress_tracker,
                    timeout_seconds=cfg.get_translation_llm_timeout_seconds(),
                    batch_log_dir=batch_log_dir,
                )
                batch_stats.record(elapsed, len(items))
                per_item_elapsed = (
                    elapsed / float(len(items)) if items else 0.0
                )
                mode_label = f"{pool_mode}-batch"
                for idx, _sentence in items:
                    _log_translation_timing(idx, per_item_elapsed, mode_label)
                resolved_items: Dict[int, Tuple[str, str]] = {}
                pending_transliteration: List[Tuple[int, str]] = []
                for idx, sentence in items:
                    translation, transliteration = translation_map.get(idx, ("", ""))
                    translation_error = _validate_batch_translation(
                        sentence, translation, target
                    )
                    if translation_error:
                        if progress_tracker is not None:
                            progress_tracker.record_retry(
                                "translation", translation_error
                            )
                        fallback = translate_sentence_simple(
                            sentence,
                            input_language,
                            target,
                            include_transliteration=include_transliteration_for_target,
                            translation_provider=translation_provider,
                            client=resolved_client,
                            progress_tracker=progress_tracker,
                        )
                        translation_only, inline_transliteration = text_norm.split_translation_and_transliteration(
                            fallback
                        )
                        translation = text_norm.collapse_whitespace(
                            (translation_only or fallback).strip()
                        )
                        transliteration = text_norm.collapse_whitespace(
                            (inline_transliteration or "").strip()
                        )
                    resolved_items[idx] = (translation, transliteration)
                    if (
                        include_transliteration_for_target
                        and translation
                        and not transliteration
                        and not text_norm.is_placeholder_translation(translation)
                        and not is_failure_annotation(translation)
                    ):
                        pending_transliteration.append((idx, translation))

                transliteration_map: Dict[int, str] = {}
                if include_transliteration_for_target and pending_transliteration:
                    transliteration_map = _resolve_batch_transliterations(
                        pending_transliteration,
                        target,
                        transliterator=transliterator,
                        transliteration_mode=transliteration_mode,
                        transliteration_client=transliteration_client,
                        local_client=resolved_client,
                        progress_tracker=progress_tracker,
                        batch_size=transliteration_batch_size,
                        batch_log_dir=transliteration_batch_log_dir,
                        batch_stats=transliteration_stats,
                    )

                batch_results: List[Tuple[int, str]] = []
                for idx, _sentence in items:
                    translation, transliteration = resolved_items.get(idx, ("", ""))
                    if include_transliteration_for_target and not transliteration:
                        transliteration = transliteration_map.get(idx, "")
                    if include_transliteration_for_target and transliteration:
                        combined = f"{translation}\n{transliteration}"
                    else:
                        combined = translation
                    batch_results.append((idx, combined))
                if progress_tracker is not None:
                    for idx, _sentence in items:
                        sentence_number = (
                            sentence_ids[idx] if sentence_ids is not None else idx + 1
                        )
                        progress_tracker.record_translation_completion(idx, sentence_number)
                return batch_results

            try:
                future_map = {
                    pool.submit(_translate_batch, target, items): (target, items)
                    for target, items in batches
                }
                for future in pool.iter_completed(future_map):
                    try:
                        batch_result = future.result()
                    except Exception as exc:  # pragma: no cover - defensive logging
                        logger.error("Batch translation failed: %s", exc)
                        batch_result = []
                    for idx, text in batch_result:
                        results[idx] = text
            finally:
                if own_pool:
                    pool.shutdown()
            return results

        def _translate(index: int, sentence: str, target: str) -> str:
            return translate_sentence_simple(
                sentence,
                input_language,
                target,
                include_transliteration=include_transliteration,
                translation_provider=translation_provider,
                client=resolved_client,
                progress_tracker=progress_tracker,
            )

        pool = worker_pool or ThreadWorkerPool(max_workers=worker_count)
        if getattr(pool, "mode", "thread") != "thread":
            raise RuntimeError(
                "translate_batch does not support asynchronous worker pools in synchronous mode"
            )

        own_pool = worker_pool is None
        try:
            future_map = {
                pool.submit(_translate, idx, sentence, target): idx
                for idx, (sentence, target) in enumerate(zip(sentences, targets))
            }
            for future in pool.iter_completed(future_map):
                idx = future_map[future]
                try:
                    results[idx] = future.result()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error("Translation failed for sentence %s: %s", idx, exc)
                    results[idx] = "N/A"
                if progress_tracker is not None:
                    sentence_number = sentence_ids[idx] if sentence_ids is not None else idx + 1
                    progress_tracker.record_translation_completion(idx, sentence_number)
        finally:
            if own_pool:
                pool.shutdown()

    return results


def _enqueue_with_backpressure(
    queue: Queue[Optional[TranslationTask]],
    task: Optional[TranslationTask],
    *,
    stop_event: Optional[threading.Event],
) -> bool:
    while True:
        if stop_event and stop_event.is_set():
            return False
        try:
            queue.put(task, timeout=0.1)
            return True
        except Full:
            continue


def _log_translation_timing(sentence_number: int, elapsed: float, mode: str) -> None:
    observability.record_metric(
        "translation.duration_seconds",
        elapsed,
        {"mode": mode},
    )
    logger.debug(
        "Producer translated sentence %s in %.3fs",
        sentence_number,
        elapsed,
    )


def start_translation_pipeline(
    sentences: Sequence[str],
    input_language: str,
    target_language: Sequence[str],
    *,
    start_sentence: int,
    output_queue: Queue[Optional[TranslationTask]],
    consumer_count: int,
    stop_event: Optional[threading.Event] = None,
    max_workers: Optional[int] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
    client: Optional[LLMClient] = None,
    worker_pool: Optional[ThreadWorkerPool] = None,
    transliterator: Optional[TransliterationService] = None,
    translation_provider: Optional[str] = None,
    transliteration_mode: Optional[str] = None,
    transliteration_client: Optional[LLMClient] = None,
    include_transliteration: bool = False,
    llm_batch_size: Optional[int] = None,
) -> threading.Thread:
    """Spawn a background producer thread that streams translations into ``output_queue``."""

    worker_count = max_workers or cfg.get_thread_count()
    worker_count = max(1, min(worker_count, len(sentences) or 1))
    transliterator = transliterator or get_transliterator()

    active_context = cfg.get_runtime_context(None)

    def _producer() -> None:
        if active_context is not None:
            cfg.set_runtime_context(active_context)

        local_client, owns_client = llm_client_manager.acquire_client(client)
        pool = worker_pool or ThreadWorkerPool(max_workers=worker_count)
        own_pool = worker_pool is None
        pool_mode = getattr(pool, "mode", "thread")
        provider = _normalize_translation_provider(translation_provider)
        include_transliteration_any = include_transliteration and any(
            language_policies.is_non_latin_language_hint(target) for target in target_language
        )
        batch_size = (
            _normalize_llm_batch_size(llm_batch_size) if provider == "llm" else None
        )
        if batch_size and not prompt_templates.translation_supports_json_batch(
            local_client.model
        ):
            if local_client.debug_enabled:
                logger.debug(
                    "Disabling JSON batch translation for model %s",
                    local_client.model,
                )
            batch_size = None
        batch_log_dir = _resolve_llm_batch_log_dir() if batch_size else None
        transliteration_batch_size = (
            _normalize_llm_batch_size(llm_batch_size) if include_transliteration_any else None
        )
        transliteration_batch_log_dir = (
            _resolve_llm_batch_log_dir(_LLM_BATCH_TRANSLITERATION_SUBDIR)
            if transliteration_batch_size
            else None
        )
        batch_stats = None
        transliteration_stats = None

        try:
            if not sentences:
                for _ in range(max(1, consumer_count)):
                    _enqueue_with_backpressure(
                        output_queue, None, stop_event=stop_event
                    )
                return

            futures_map: dict = {}
            batches: List[Tuple[str, List[Tuple[int, str]]]] = []
            if batch_size:
                batches = _build_translation_batches(
                    sentences, target_language, batch_size=batch_size
                )
                batch_stats = _BatchStatsRecorder(
                    batch_size=batch_size,
                    progress_tracker=progress_tracker,
                    metadata_key="translation_batch_stats",
                    total_batches=len(batches),
                    items_total=len(sentences),
                )
                batch_stats.set_total(len(batches), items_total=len(sentences))
                if transliteration_batch_size:
                    transliteration_stats = _BatchStatsRecorder(
                        batch_size=transliteration_batch_size,
                        progress_tracker=progress_tracker,
                        metadata_key="transliteration_batch_stats",
                        items_total=len(sentences),
                    )

            def _translate(index: int, sentence: str, target: str) -> TranslationTask:
                start_time = time.perf_counter()
                include_transliteration_for_target = _should_include_transliteration(
                    include_transliteration_any, target
                )
                try:
                    translation = translate_sentence_simple(
                        sentence,
                        input_language,
                        target,
                        include_transliteration=include_transliteration_for_target,
                        translation_provider=translation_provider,
                        client=local_client,
                        progress_tracker=progress_tracker,
                    )
                    transliteration_text = ""
                    if (
                        include_transliteration_for_target
                        and not text_norm.is_placeholder_translation(translation)
                        and not is_failure_annotation(translation)
                    ):
                        translation_only, inline_transliteration = text_norm.split_translation_and_transliteration(
                            translation
                        )
                        transliteration_text = inline_transliteration.strip()
                        transliteration_source = translation_only or translation
                        if transliteration_source and not transliteration_text:
                            transliteration_result = transliterator.transliterate(
                                transliteration_source,
                                target,
                                client=transliteration_client or local_client,
                                progress_tracker=progress_tracker,
                                mode=transliteration_mode,
                            )
                            transliteration_text = transliteration_result.text.strip()
                finally:
                    elapsed = time.perf_counter() - start_time
                    _log_translation_timing(start_sentence + index, elapsed, pool_mode)
                # Apply token alignment for CJK languages
                if translation and transliteration_text:
                    _, aligned_translit, _ = align_token_counts(
                        translation, transliteration_text, target
                    )
                    transliteration_text = aligned_translit
                return TranslationTask(
                    index=index,
                    sentence_number=start_sentence + index,
                    sentence=sentence,
                    target_language=target,
                    translation=translation,
                    transliteration=transliteration_text,
                )

            def _translate_batch(
                target: str, items: Sequence[Tuple[int, str]]
            ) -> List[TranslationTask]:
                include_transliteration_for_target = _should_include_transliteration(
                    include_transliteration_any, target
                )
                translation_map, _error, elapsed = _translate_llm_batch_items(
                    items,
                    input_language,
                    target,
                    include_transliteration=include_transliteration_for_target,
                    resolved_client=local_client,
                    progress_tracker=progress_tracker,
                    timeout_seconds=cfg.get_translation_llm_timeout_seconds(),
                    batch_log_dir=batch_log_dir,
                )
                if batch_stats is not None:
                    batch_stats.record(elapsed, len(items))
                per_item_elapsed = (
                    elapsed / float(len(items)) if items else 0.0
                )
                mode_label = f"{pool_mode}-batch"
                resolved_items: Dict[int, Tuple[str, str]] = {}
                pending_transliteration: List[Tuple[int, str]] = []
                for idx, sentence in items:
                    _log_translation_timing(
                        start_sentence + idx, per_item_elapsed, mode_label
                    )
                    translation, transliteration = translation_map.get(idx, ("", ""))
                    translation_error = _validate_batch_translation(
                        sentence, translation, target
                    )
                    if translation_error:
                        if progress_tracker is not None:
                            progress_tracker.record_retry(
                                "translation", translation_error
                            )
                        fallback = translate_sentence_simple(
                            sentence,
                            input_language,
                            target,
                            include_transliteration=include_transliteration_for_target,
                            translation_provider=translation_provider,
                            client=local_client,
                            progress_tracker=progress_tracker,
                        )
                        translation_only, inline_transliteration = text_norm.split_translation_and_transliteration(
                            fallback
                        )
                        translation = text_norm.collapse_whitespace(
                            (translation_only or fallback).strip()
                        )
                        transliteration = text_norm.collapse_whitespace(
                            (inline_transliteration or "").strip()
                        )
                    resolved_items[idx] = (translation, transliteration)
                    if (
                        include_transliteration_for_target
                        and translation
                        and not transliteration
                        and not text_norm.is_placeholder_translation(translation)
                        and not is_failure_annotation(translation)
                    ):
                        pending_transliteration.append((idx, translation))

                transliteration_map: Dict[int, str] = {}
                if include_transliteration_for_target and pending_transliteration:
                    transliteration_map = _resolve_batch_transliterations(
                        pending_transliteration,
                        target,
                        transliterator=transliterator,
                        transliteration_mode=transliteration_mode,
                        transliteration_client=transliteration_client,
                        local_client=local_client,
                        progress_tracker=progress_tracker,
                        batch_size=transliteration_batch_size,
                        batch_log_dir=transliteration_batch_log_dir,
                        batch_stats=transliteration_stats,
                    )

                tasks: List[TranslationTask] = []
                for idx, sentence in items:
                    translation, transliteration = resolved_items.get(idx, ("", ""))
                    if include_transliteration_for_target and not transliteration:
                        transliteration = transliteration_map.get(idx, "")
                    # Apply token alignment for CJK languages
                    if translation and transliteration:
                        _, aligned_translit, _ = align_token_counts(
                            translation, transliteration, target
                        )
                        transliteration = aligned_translit
                    tasks.append(
                        TranslationTask(
                            index=idx,
                            sentence_number=start_sentence + idx,
                            sentence=sentence,
                            target_language=target,
                            translation=translation,
                            transliteration=transliteration,
                        )
                    )
                return tasks

            try:
                if pool_mode != "thread":
                    raise RuntimeError(
                        "start_translation_pipeline requires a threaded worker pool in synchronous mode"
                    )
                if batch_size:
                    futures_map = {
                        pool.submit(_translate_batch, target, items): (target, items)
                        for target, items in batches
                    }
                    for future in pool.iter_completed(futures_map):
                        if stop_event and stop_event.is_set():
                            break
                        target, items = futures_map[future]
                        try:
                            tasks = future.result()
                        except Exception as exc:  # pragma: no cover - defensive logging
                            logger.error(
                                "Batch translation failed for %s: %s",
                                target or "unknown target",
                                exc,
                            )
                            tasks = []
                            for idx, sentence in items:
                                fallback = translate_sentence_simple(
                                    sentence,
                                    input_language,
                                    target,
                                    include_transliteration=include_transliteration,
                                    translation_provider=translation_provider,
                                    client=local_client,
                                    progress_tracker=progress_tracker,
                                )
                                translation_only, inline_transliteration = text_norm.split_translation_and_transliteration(
                                    fallback
                                )
                                translation_text = text_norm.collapse_whitespace(
                                    (translation_only or fallback).strip()
                                )
                                transliteration_text = text_norm.collapse_whitespace(
                                    (inline_transliteration or "").strip()
                                )
                                # Apply token alignment for CJK languages
                                if translation_text and transliteration_text:
                                    _, aligned_translit, _ = align_token_counts(
                                        translation_text, transliteration_text, target
                                    )
                                    transliteration_text = aligned_translit
                                tasks.append(
                                    TranslationTask(
                                        index=idx,
                                        sentence_number=start_sentence + idx,
                                        sentence=sentence,
                                        target_language=target,
                                        translation=translation_text,
                                        transliteration=transliteration_text,
                                    )
                                )
                        for task in tasks:
                            if progress_tracker:
                                progress_tracker.record_translation_completion(
                                    task.index, task.sentence_number
                                )
                            if not _enqueue_with_backpressure(
                                output_queue, task, stop_event=stop_event
                            ):
                                break
                    else:
                        # Only executed if loop did not break
                        pass
                else:
                    futures_map = {
                        pool.submit(_translate, idx, sentence, target): idx
                        for idx, (sentence, target) in enumerate(zip(sentences, target_language))
                    }
                    for future in pool.iter_completed(futures_map):
                        if stop_event and stop_event.is_set():
                            break
                        idx = futures_map[future]
                        try:
                            task = future.result()
                        except Exception as exc:  # pragma: no cover - defensive logging
                            sentence_number = start_sentence + idx
                            logger.error(
                                "Translation failed for sentence %s: %s", sentence_number, exc
                            )
                            task = TranslationTask(
                                index=idx,
                                sentence_number=sentence_number,
                                sentence=sentences[idx],
                                target_language=target_language[idx],
                                translation="N/A",
                            )
                        if progress_tracker:
                            progress_tracker.record_translation_completion(
                                task.index, task.sentence_number
                            )
                        if not _enqueue_with_backpressure(
                            output_queue, task, stop_event=stop_event
                        ):
                            break
                    else:
                        # Only executed if loop did not break
                        pass
            finally:
                if own_pool:
                    pool.shutdown()
        finally:
            for _ in range(max(1, consumer_count)):
                _enqueue_with_backpressure(
                    output_queue, None, stop_event=stop_event
                )
            llm_client_manager.release_client(local_client, owns_client)
            if active_context is not None:
                cfg.clear_runtime_context()

    thread = threading.Thread(target=_producer, name="TranslationProducer", daemon=True)
    thread.start()
    return thread
