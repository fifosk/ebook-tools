"""Translation engine utilities for ebook-tools."""

from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import dataclass
from queue import Full, Queue
import threading
import time
from typing import Iterable, Iterator, List, Optional, Sequence, TYPE_CHECKING

import regex

if TYPE_CHECKING:
    from concurrent.futures import Future
    from modules.progress_tracker import ProgressTracker

from modules import config_manager as cfg
from modules import fallbacks
from modules import logging_manager as log_mgr
from modules import observability, prompt_templates
from modules import llm_client_manager
from modules import language_policies
from modules import text_normalization as text_norm
from modules.text import split_highlight_tokens
from modules.retry_annotations import format_retry_failure, is_failure_annotation
from modules.llm_client import LLMClient
from modules.transliteration import TransliterationService, get_transliterator
from modules.language_constants import LANGUAGE_CODES

logger = log_mgr.logger

_TRANSLATION_RESPONSE_ATTEMPTS = 5
_TRANSLATION_RETRY_DELAY_SECONDS = 1.0
_LLM_REQUEST_ATTEMPTS = 4
_GOOGLETRANS_PROVIDER_ALIASES = {
    "google",
    "googletrans",
    "googletranslate",
    "google-translate",
    "gtranslate",
    "gtrans",
}
_LANG_CODE_PATTERN = regex.compile(r"^[a-z]{2,3}([_-][a-z0-9]{2,4})?$", regex.IGNORECASE)
_SEGMENTATION_LANGS = {
    # Thai family
    "thai",
    "th",
    # Khmer / Cambodian
    "khmer",
    "km",
    "cambodian",
    # Burmese / Myanmar
    "burmese",
    "myanmar",
    "my",
    # Japanese
    "japanese",
    "ja",
    "日本語",
    # Korean (should already have spaces, but enforce retries if omitted)
    "korean",
    "ko",
    # Chinese (added cautiously; can be removed if character-level is preferred)
    "chinese",
    "zh",
    "zh-cn",
    "zh-tw",
}
_LATIN_LETTER_PATTERN = regex.compile(r"\p{Latin}")
_NON_LATIN_LETTER_PATTERN = regex.compile(r"(?!\p{Latin})\p{L}")
_ZERO_WIDTH_SPACE_PATTERN = regex.compile(r"[\u200B\u200C\u200D\u2060]+")
_DIACRITIC_PATTERNS = {
    "arabic": {
        "aliases": ("arabic", "ar"),
        "pattern": regex.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]"),
        "label": "Arabic diacritics (tashkil)",
        "script_pattern": regex.compile(r"[\u0600-\u06FF]"),
    },
    "hebrew": {
        "aliases": ("hebrew", "he", "iw"),
        "pattern": regex.compile(r"[\u0591-\u05C7]"),
        "label": "Hebrew niqqud",
        "script_pattern": regex.compile(r"[\u0590-\u05FF]"),
    },
}

_GOOGLETRANS_LOCAL = threading.local()
_GOOGLETRANS_HEALTH_LOCK = threading.Lock()
_GOOGLETRANS_HEALTH_STATE = {
    "checked": False,
    "ok": False,
    "reason": None,
}


def _check_googletrans_health() -> tuple[bool, Optional[str]]:
    with _GOOGLETRANS_HEALTH_LOCK:
        if _GOOGLETRANS_HEALTH_STATE["checked"]:
            return _GOOGLETRANS_HEALTH_STATE["ok"], _GOOGLETRANS_HEALTH_STATE["reason"]

        reason: Optional[str] = None
        try:
            import httpcore  # noqa: F401
        except Exception as exc:
            reason = f"httpcore import failed: {exc}"
        else:
            if not hasattr(httpcore, "SyncHTTPTransport"):
                reason = "httpcore.SyncHTTPTransport missing"

        if reason is None:
            try:
                from googletrans import Translator

                Translator()
            except Exception as exc:
                reason = f"googletrans init failed: {exc}"

        ok = reason is None
        _GOOGLETRANS_HEALTH_STATE["checked"] = True
        _GOOGLETRANS_HEALTH_STATE["ok"] = ok
        _GOOGLETRANS_HEALTH_STATE["reason"] = reason
        if not ok:
            logger.warning("Googletrans health check failed: %s", reason)
        return ok, reason


def _normalize_translation_provider(value: Optional[str]) -> str:
    if not value:
        return "llm"
    normalized = value.strip().lower()
    if normalized in _GOOGLETRANS_PROVIDER_ALIASES:
        return "googletrans"
    if normalized in {"llm", "ollama", "default"}:
        return "llm"
    return "llm"


def _resolve_googletrans_language(value: Optional[str], *, fallback: Optional[str]) -> Optional[str]:
    if value is None:
        return fallback
    cleaned = value.strip()
    if not cleaned:
        return fallback
    normalized = cleaned.replace("_", "-").strip().lower()
    if not normalized:
        return fallback
    if _LANG_CODE_PATTERN.match(normalized):
        return normalized
    for name, code in LANGUAGE_CODES.items():
        if normalized == name.strip().lower():
            return code.lower()
    try:
        from googletrans import LANGUAGES
    except Exception:
        return fallback or normalized
    for code, name in LANGUAGES.items():
        if normalized == name.strip().lower():
            return code.lower()
    return fallback or normalized


def _get_googletrans_translator():
    translator = getattr(_GOOGLETRANS_LOCAL, "translator", None)
    if translator is None:
        from googletrans import Translator

        translator = Translator()
        if hasattr(translator, "raise_exception") and not hasattr(translator, "raise_Exception"):
            setattr(translator, "raise_Exception", translator.raise_exception)
        _GOOGLETRANS_LOCAL.translator = translator
    return translator


def _translate_with_googletrans(
    sentence: str,
    input_language: str,
    target_language: str,
    *,
    progress_tracker: Optional["ProgressTracker"] = None,
) -> tuple[str, Optional[str]]:
    health_ok, health_reason = _check_googletrans_health()
    if not health_ok:
        failure_reason = f"googletrans health check failed: {health_reason}"
        if progress_tracker is not None:
            progress_tracker.record_retry("translation", failure_reason)
        return (
            format_retry_failure(
                "translation",
                _TRANSLATION_RESPONSE_ATTEMPTS,
                reason=failure_reason,
            ),
            failure_reason,
        )

    last_error: Optional[str] = None
    for attempt in range(1, _TRANSLATION_RESPONSE_ATTEMPTS + 1):
        try:
            translator = _get_googletrans_translator()
            src_code = _resolve_googletrans_language(input_language, fallback="auto") or "auto"
            dest_code = _resolve_googletrans_language(target_language, fallback=None) or "en"
            result = translator.translate(sentence, src=src_code, dest=dest_code)
            candidate = text_norm.collapse_whitespace((result.text or "").strip())
            if candidate and not text_norm.is_placeholder_translation(candidate):
                return candidate, None
            last_error = "Empty translation response"
        except Exception as exc:  # pragma: no cover - network/remote errors
            last_error = str(exc) or "Google Translate request failed"
        if progress_tracker is not None and last_error:
            progress_tracker.record_retry("translation", last_error)
        if attempt < _TRANSLATION_RESPONSE_ATTEMPTS:
            time.sleep(_TRANSLATION_RETRY_DELAY_SECONDS)
    failure_reason = last_error or "Google Translate error"
    return (
        format_retry_failure(
            "translation",
            _TRANSLATION_RESPONSE_ATTEMPTS,
            reason=failure_reason,
        ),
        failure_reason,
    )


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
    wrapped_sentence = f"{prompt_templates.SOURCE_START}\n{sentence}\n{prompt_templates.SOURCE_END}"
    system_prompt = prompt_templates.make_translation_prompt(
        input_language,
        target_language,
        include_transliteration=include_transliteration,
    )
    payload = prompt_templates.make_sentence_payload(
        wrapped_sentence,
        model=resolved_client.model,
        stream=True,
        system_prompt=system_prompt,
    )

    start_time = time.perf_counter()
    last_error: Optional[str] = None
    best_translation: Optional[str] = None
    best_score = -1
    fatal_violation = False
    for attempt in range(1, _TRANSLATION_RESPONSE_ATTEMPTS + 1):
        attempt_error: Optional[str] = None
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


class ThreadWorkerPool:
    """Threaded worker pool implementation for translation tasks."""

    mode = "thread"

    def __init__(self, *, max_workers: Optional[int] = None) -> None:
        self.max_workers = max(1, max_workers or cfg.get_thread_count())
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self._shutdown = False
        observability.worker_pool_event(
            "created", mode=self.mode, max_workers=self.max_workers
        )

    def _ensure_executor(self) -> concurrent.futures.ThreadPoolExecutor:
        if self._executor is None:
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers
            )
            observability.worker_pool_event(
                "executor_initialized", mode=self.mode, max_workers=self.max_workers
            )
        return self._executor

    def submit(self, func, *args, **kwargs) -> Future:
        observability.record_metric(
            "worker_pool.tasks_submitted",
            1.0,
            {"mode": self.mode, "max_workers": self.max_workers},
        )
        return self._ensure_executor().submit(func, *args, **kwargs)

    def iter_completed(self, futures: Iterable[Future]) -> Iterator[Future]:
        return concurrent.futures.as_completed(futures)

    def shutdown(self, wait: bool = True) -> None:
        if self._shutdown:
            return
        if self._executor is not None:
            self._executor.shutdown(wait=wait)
        self._shutdown = True
        observability.worker_pool_event(
            "shutdown", mode=self.mode, max_workers=self.max_workers
        )

    def __enter__(self) -> "ThreadWorkerPool":  # pragma: no cover - trivial
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - trivial
        self.shutdown()


class AsyncWorkerPool:
    """Asynchronous worker pool backed by an event loop."""

    mode = "async"

    def __init__(
        self,
        *,
        max_workers: Optional[int] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self.max_workers = max(1, max_workers or cfg.get_thread_count())
        self._loop = loop or asyncio.get_event_loop()
        self._shutdown = False
        observability.worker_pool_event(
            "created", mode=self.mode, max_workers=self.max_workers
        )

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def submit(self, func, *args, **kwargs) -> asyncio.Future:
        result = func(*args, **kwargs)
        observability.record_metric(
            "worker_pool.tasks_submitted",
            1.0,
            {"mode": self.mode, "max_workers": self.max_workers},
        )
        if asyncio.iscoroutine(result) or isinstance(result, asyncio.Future):
            return asyncio.ensure_future(result, loop=self._loop)
        return self._loop.run_in_executor(None, lambda: result)

    async def iter_completed(self, futures: Iterable[asyncio.Future]) -> Iterator:
        for awaitable in asyncio.as_completed(list(futures)):
            yield await awaitable

    def shutdown(self, wait: bool = True) -> None:  # pragma: no cover - interface parity
        if self._shutdown:
            return
        self._shutdown = True
        observability.worker_pool_event(
            "shutdown", mode=self.mode, max_workers=self.max_workers
        )

    def __enter__(self) -> "AsyncWorkerPool":  # pragma: no cover - trivial
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - trivial
        self.shutdown()


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


def _valid_translation(text: str) -> bool:
    return not text_norm.is_placeholder_translation(text)


def _letter_count(value: str) -> int:
    return sum(1 for char in value if char.isalpha())


def _has_non_latin_letters(value: str) -> bool:
    return bool(_NON_LATIN_LETTER_PATTERN.search(value))


def _latin_fraction(value: str) -> float:
    if not value:
        return 0.0
    latin = len(_LATIN_LETTER_PATTERN.findall(value))
    non_latin = len(_NON_LATIN_LETTER_PATTERN.findall(value))
    total = latin + non_latin
    if total == 0:
        return 0.0
    return latin / total


def _is_probable_transliteration(
    original_sentence: str, translation_text: str, target_language: str
) -> bool:
    """
    Return True when the response likely contains only a Latin transliteration
    even though the target language expects non-Latin script output.
    """

    target_lower = (target_language or "").lower()
    if not translation_text or not _has_non_latin_letters(original_sentence):
        return False
    if not language_policies.is_non_latin_language_hint(target_language):
        return False
    return _latin_fraction(translation_text) >= 0.6


def _is_translation_too_short(
    original_sentence: str, translation_text: str
) -> bool:
    """
    Heuristic for truncated translations. Skip very short inputs to avoid
    over-triggering on single words.
    """

    translation_text = translation_text or ""
    original_letters = _letter_count(original_sentence)
    if original_letters <= 12:
        return False
    translation_letters = _letter_count(translation_text)
    if translation_letters == 0:
        return True
    if original_letters >= 80 and translation_letters < 15:
        return True
    ratio = translation_letters / float(original_letters)
    return original_letters >= 30 and ratio < 0.28


def _missing_required_diacritics(
    translation_text: str, target_language: str
) -> tuple[bool, Optional[str]]:
    """
    Return (True, label) when the target language expects diacritics but none
    are present in the translation.
    """

    target_lower = (target_language or "").lower()
    for requirement in _DIACRITIC_PATTERNS.values():
        if any(alias in target_lower for alias in requirement["aliases"]):
            pattern = requirement["pattern"]
            script_pattern = requirement.get("script_pattern")
            if script_pattern and not script_pattern.search(translation_text or ""):
                # Skip if the translation doesn't use the expected script; avoids
                # misfiring when target_language is mismatched.
                return False, None
            if not pattern.search(translation_text or ""):
                return True, requirement["label"]
            return False, None
    return False, None


def _script_counts(value: str) -> dict[str, int]:
    """
    Return counts of matched characters per known script block.
    """

    return language_policies.script_counts(value)


def _unexpected_script_used(
    translation_text: str, target_language: str
) -> tuple[bool, Optional[str]]:
    """
    Return (True, label) when the translation contains non-Latin script but
    does not sufficiently include the expected script for the target language.
    """

    candidate = translation_text or ""
    if not candidate:
        return False, None
    if not _NON_LATIN_LETTER_PATTERN.search(candidate):
        return False, None

    policy = language_policies.script_policy_for(target_language)
    if policy is None:
        return False, None

    script_distribution = _script_counts(candidate)
    total_non_latin = len(_NON_LATIN_LETTER_PATTERN.findall(candidate))

    expected_pattern = policy.script_pattern
    expected_label = policy.script_label
    expected_matches = expected_pattern.findall(candidate)
    expected_count = len(expected_matches)
    if expected_count == 0:
        return True, expected_label
    if total_non_latin > 0:
        expected_ratio = expected_count / float(total_non_latin)
        other_count = total_non_latin - expected_count

        # Reject when other scripts meaningfully appear (e.g., Georgian/Tamil in Kannada)
        # or when the expected script is not clearly dominant.
        dominant_script = max(
            script_distribution.items(), key=lambda item: item[1], default=(None, 0)
        )
        dominant_label, dominant_count = dominant_script

        if expected_ratio < 0.85 or other_count > max(2, expected_count * 0.1):
            offenders = [
                label
                for label, count in script_distribution.items()
                if label != expected_label and count > 0
            ]
            offender_label = f" (found {', '.join(offenders)})" if offenders else ""
            return True, f"{expected_label}{offender_label}"

        if dominant_label and dominant_label != expected_label and dominant_count > expected_count:
            return True, f"{expected_label} (found {dominant_label})"
    return False, None


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

    provider = _normalize_translation_provider(translation_provider)
    timeout_seconds = cfg.get_translation_llm_timeout_seconds()
    fallback_model = cfg.get_translation_fallback_model()
    fallback_active = fallbacks.is_llm_fallback_active(progress_tracker)

    if provider == "googletrans" and not fallback_active:
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
            trigger="googletrans_error",
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


def _is_segmentation_ok(
    original_sentence: str,
    translation: str,
    target_language: str,
    *,
    translation_text: Optional[str] = None,
) -> bool:
    """
    Require word-like spacing for select languages; otherwise retry.

    We bypass this check when the original sentence is a single word to avoid
    retry loops on very short content.
    """

    def _segmentation_thresholds(lang: str, source_words: int) -> tuple[int, int]:
        if lang in {"khmer", "km", "cambodian"}:
            # Khmer: enforce closer parity to source word count.
            required_min = max(2, int(source_words * 0.6))
            max_reasonable = max(source_words * 2, required_min + 1)
            return required_min, max_reasonable
        return max(4, int(source_words * 0.6)), source_words * 4

    lang = (target_language or "").strip().lower()
    if lang not in _SEGMENTATION_LANGS:
        return True
    original_word_count = max(len(original_sentence.split()), 1)
    if original_word_count <= 1:
        return True
    candidate = translation_text or translation
    candidate = _ZERO_WIDTH_SPACE_PATTERN.sub(" ", candidate)
    tokens = split_highlight_tokens(candidate)
    token_count = len(tokens)
    if token_count <= 1:
        return False
    if lang in {"khmer", "km", "cambodian"} and token_count > 2:
        short_tokens = sum(1 for token in tokens if len(token) <= 2)
        if short_tokens / float(token_count) > 0.1:
            return False
    # Accept if segmentation yields enough tokens and isn't clearly over-split.
    required_min, max_reasonable = _segmentation_thresholds(lang, original_word_count)
    if token_count < required_min:
        return False
    if token_count > max_reasonable:
        return False
    return True



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
    translation_provider: Optional[str] = None,
    max_workers: Optional[int] = None,
    client: Optional[LLMClient] = None,
    worker_pool: Optional[ThreadWorkerPool] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
) -> List[str]:
    """Translate ``sentences`` concurrently while preserving order."""

    if not sentences:
        return []

    targets = _normalize_target_sequence(target_language, len(sentences))
    worker_count = max_workers or cfg.get_thread_count()
    worker_count = max(1, min(worker_count, len(sentences)))

    results: List[str] = ["" for _ in sentences]

    with llm_client_manager.client_scope(client) as resolved_client:
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

        try:
            if not sentences:
                for _ in range(max(1, consumer_count)):
                    _enqueue_with_backpressure(
                        output_queue, None, stop_event=stop_event
                    )
                return

            futures_map: dict = {}

            def _translate(index: int, sentence: str, target: str) -> TranslationTask:
                start_time = time.perf_counter()
                try:
                    translation = translate_sentence_simple(
                        sentence,
                        input_language,
                        target,
                        include_transliteration=include_transliteration,
                        translation_provider=translation_provider,
                        client=local_client,
                        progress_tracker=progress_tracker,
                    )
                    transliteration_text = ""
                    if (
                        include_transliteration
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
                return TranslationTask(
                    index=index,
                    sentence_number=start_sentence + index,
                    sentence=sentence,
                    target_language=target,
                    translation=translation,
                    transliteration=transliteration_text,
                )

            try:
                if pool_mode != "thread":
                    raise RuntimeError(
                        "start_translation_pipeline requires a threaded worker pool in synchronous mode"
                    )
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
