"""Fallback state helpers for translation and TTS pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import threading
import time
import weakref
from typing import Any, Dict, Optional, TYPE_CHECKING

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules.llm_client import LLMClient, create_client

if TYPE_CHECKING:  # pragma: no cover - typing only
    from modules.progress_tracker import ProgressTracker

logger = log_mgr.get_logger()


@dataclass
class FallbackState:
    """In-memory fallback state tied to a job's progress tracker."""

    translation: Optional[Dict[str, Any]] = None
    tts: Optional[Dict[str, Any]] = None
    llm_fallback_model: Optional[str] = None
    tts_fallback_voice: Optional[str] = None
    lock: threading.Lock = field(default_factory=threading.Lock)


_FALLBACKS: "weakref.WeakKeyDictionary[ProgressTracker, FallbackState]" = weakref.WeakKeyDictionary()
_FALLBACKS_LOCK = threading.Lock()


def _get_state(tracker: Optional["ProgressTracker"]) -> Optional[FallbackState]:
    if tracker is None:
        return None
    with _FALLBACKS_LOCK:
        state = _FALLBACKS.get(tracker)
        if state is None:
            state = FallbackState()
            _FALLBACKS[tracker] = state
        return state


def is_llm_fallback_active(tracker: Optional["ProgressTracker"]) -> bool:
    state = _get_state(tracker)
    return bool(state and state.llm_fallback_model)


def get_llm_fallback_model(tracker: Optional["ProgressTracker"]) -> Optional[str]:
    state = _get_state(tracker)
    if state and state.llm_fallback_model:
        return state.llm_fallback_model
    return None


def get_tts_fallback_voice(tracker: Optional["ProgressTracker"]) -> Optional[str]:
    state = _get_state(tracker)
    if state and state.tts_fallback_voice:
        return state.tts_fallback_voice
    return None


def _build_translation_detail(
    *,
    trigger: str,
    reason: str,
    source_provider: str,
    fallback_model: str,
    scope: str,
    elapsed_seconds: Optional[float],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "trigger": trigger,
        "scope": scope,
        "reason": reason,
        "source_provider": source_provider,
        "fallback_model": fallback_model,
        "fallback_provider": "llm",
        "timestamp": round(time.time(), 3),
    }
    if elapsed_seconds is not None:
        payload["elapsed_seconds"] = round(float(elapsed_seconds), 3)
    return payload


def record_translation_fallback(
    tracker: Optional["ProgressTracker"],
    *,
    trigger: str,
    reason: str,
    source_provider: str,
    fallback_model: Optional[str] = None,
    scope: str = "translation",
    elapsed_seconds: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    state = _get_state(tracker)
    if state is None:
        return None
    model = (fallback_model or cfg.get_translation_fallback_model() or "").strip()
    if not model:
        return None
    with state.lock:
        if state.translation is not None:
            return state.translation
        detail = _build_translation_detail(
            trigger=trigger,
            reason=reason,
            source_provider=source_provider,
            fallback_model=model,
            scope=scope,
            elapsed_seconds=elapsed_seconds,
        )
        state.translation = detail
        state.llm_fallback_model = model
        if tracker is not None:
            tracker.update_generated_files_metadata({"translation_fallback": detail})
            tracker.publish_progress({"stage": "translation.fallback", **detail})
        logger.warning(
            "Translation fallback activated (%s): %s", trigger, reason
        )
        return detail


def record_tts_fallback(
    tracker: Optional["ProgressTracker"],
    *,
    trigger: str,
    reason: str,
    source_voice: str,
    fallback_voice: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    state = _get_state(tracker)
    if state is None:
        return None
    voice = (fallback_voice or cfg.get_tts_fallback_voice() or "").strip()
    if not voice:
        return None
    with state.lock:
        if state.tts is not None:
            return state.tts
        detail = {
            "trigger": trigger,
            "reason": reason,
            "source_voice": source_voice,
            "fallback_voice": voice,
            "fallback_backend": "macos_say",
            "timestamp": round(time.time(), 3),
        }
        state.tts = detail
        state.tts_fallback_voice = voice
        if tracker is not None:
            tracker.update_generated_files_metadata({"tts_fallback": detail})
            tracker.publish_progress({"stage": "tts.fallback", **detail})
        logger.warning("TTS fallback activated (%s): %s", trigger, reason)
        return detail


@lru_cache(maxsize=4)
def get_fallback_llm_client(model: str) -> LLMClient:
    """Return a cached local LLM client for fallback usage."""

    return create_client(model=model, llm_source="local")


__all__ = [
    "get_fallback_llm_client",
    "get_llm_fallback_model",
    "get_tts_fallback_voice",
    "is_llm_fallback_active",
    "record_translation_fallback",
    "record_tts_fallback",
]
