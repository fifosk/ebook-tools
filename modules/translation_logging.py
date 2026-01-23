"""Batch translation logging and statistics tracking.

This module provides functionality for logging LLM batch translation requests
and tracking batch processing statistics for progress reporting.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, TYPE_CHECKING

import regex

if TYPE_CHECKING:
    from modules.progress_tracker import ProgressTracker
    from modules.llm_client import LLMClient

from modules import config_manager as cfg, logging_manager as log_mgr

logger = log_mgr.logger

# Constants for batch logging
_BATCH_LOG_FILENAME_SAFE = regex.compile(r"[^A-Za-z0-9._-]+")
_LLM_BATCH_LOG_DIRNAME = "llm_batches"
_LLM_BATCH_TRANSLATION_SUBDIR = "translation"
_LLM_BATCH_TRANSLITERATION_SUBDIR = "transliteration"


class BatchStatsRecorder:
    """Records and publishes batch processing statistics to progress tracker.

    Thread-safe statistics tracker for batch translation/transliteration operations.
    Maintains running totals, averages, and publishes updates to progress tracker.
    """

    def __init__(
        self,
        *,
        batch_size: int,
        progress_tracker: Optional["ProgressTracker"],
        metadata_key: str,
        total_batches: Optional[int] = None,
        items_total: Optional[int] = None,
    ) -> None:
        self._batch_size = batch_size
        self._progress_tracker = progress_tracker
        self._metadata_key = metadata_key
        self._total_batches = total_batches
        self._items_total = items_total
        self._batches_completed = 0
        self._items_completed = 0
        self._total_batch_seconds = 0.0
        self._last_batch_seconds = 0.0
        self._last_batch_items = 0
        self._lock = threading.Lock()

    def set_total(
        self,
        total_batches: Optional[int],
        *,
        items_total: Optional[int] = None,
    ) -> None:
        """Set the total number of expected batches and items."""
        if total_batches is None:
            return
        with self._lock:
            self._total_batches = max(0, int(total_batches))
            if items_total is not None:
                self._items_total = max(0, int(items_total))
            payload = self._build_payload_locked()
        self._publish(payload)

    def add_total(self, delta: int) -> None:
        """Add to the total number of expected batches."""
        if delta <= 0:
            return
        with self._lock:
            if self._total_batches is None:
                self._total_batches = 0
            self._total_batches += int(delta)
            payload = self._build_payload_locked()
        self._publish(payload)

    def record(self, elapsed_seconds: float, item_count: int) -> None:
        """Record completion of a batch with timing and item count."""
        safe_elapsed = max(0.0, float(elapsed_seconds))
        safe_items = max(0, int(item_count))
        if safe_items == 0:
            return
        with self._lock:
            self._batches_completed += 1
            self._items_completed += safe_items
            self._total_batch_seconds += safe_elapsed
            self._last_batch_seconds = safe_elapsed
            self._last_batch_items = safe_items
            payload = self._build_payload_locked()
        self._publish(payload)

    def _build_payload_locked(self) -> Dict[str, object]:
        """Build statistics payload (must be called with lock held)."""
        avg_batch = (
            self._total_batch_seconds / self._batches_completed
            if self._batches_completed
            else 0.0
        )
        avg_item = (
            self._total_batch_seconds / self._items_completed
            if self._items_completed
            else 0.0
        )
        payload: Dict[str, object] = {
            "batch_size": self._batch_size,
            "batches_completed": self._batches_completed,
            "items_completed": self._items_completed,
            "avg_batch_seconds": round(avg_batch, 3),
            "avg_item_seconds": round(avg_item, 3),
            "last_batch_seconds": round(self._last_batch_seconds, 3),
            "last_batch_items": self._last_batch_items,
            "last_updated": round(time.time(), 3),
        }
        if self._total_batches is not None:
            payload["batches_total"] = self._total_batches
        if self._items_total is not None:
            payload["items_total"] = self._items_total
        return payload

    def _publish(self, payload: Dict[str, object]) -> None:
        """Publish statistics to progress tracker."""
        if self._progress_tracker is None:
            return
        self._progress_tracker.update_generated_files_metadata(
            {self._metadata_key: payload}
        )


def resolve_llm_batch_log_dir(
    subdir: str = _LLM_BATCH_TRANSLATION_SUBDIR,
) -> Optional[Path]:
    """Resolve the directory for LLM batch logs.

    Args:
        subdir: Subdirectory name (translation or transliteration)

    Returns:
        Path to batch log directory, or None if cannot be resolved
    """
    context = cfg.get_runtime_context(None)
    if context is None:
        return None
    try:
        output_dir = Path(context.output_dir)
    except Exception:
        return None
    if output_dir.name == "media":
        metadata_root = output_dir.parent / "metadata"
    else:
        metadata_root = output_dir / "metadata"
    return metadata_root / _LLM_BATCH_LOG_DIRNAME / subdir


def sanitize_batch_component(value: str) -> str:
    """Sanitize a string for use in batch log filenames.

    Args:
        value: String to sanitize (e.g., language name)

    Returns:
        Sanitized string safe for filenames
    """
    cleaned = _BATCH_LOG_FILENAME_SAFE.sub("_", value.strip().lower())
    cleaned = cleaned.strip("._-")
    return cleaned or "unknown"


def write_llm_batch_artifact(
    *,
    operation: str = "translation",
    log_dir: Optional[Path],
    request_items: Sequence[Mapping[str, Any]],
    input_language: str,
    target_language: str,
    include_transliteration: bool,
    system_prompt: str,
    user_payload: str,
    request_payload: Mapping[str, Any],
    response_payload: Optional[Any],
    response_raw_text: str,
    response_error: Optional[str],
    elapsed_seconds: float,
    attempt: int,
    timeout_seconds: float,
    client: "LLMClient",
) -> None:
    """Write a batch translation/transliteration request artifact to disk.

    Creates a JSON file with complete request/response details for debugging
    and analysis. Files are named with timestamp, batch range, and target language.

    Args:
        operation: Operation type (translation or transliteration)
        log_dir: Directory to write log to (uses default if None)
        request_items: Batch items sent in request
        input_language: Source language
        target_language: Target language
        include_transliteration: Whether transliteration was included
        system_prompt: System prompt used
        user_payload: User payload sent
        request_payload: Complete request payload
        response_payload: Parsed response payload
        response_raw_text: Raw response text
        response_error: Error message if failed
        elapsed_seconds: Request duration
        attempt: Attempt number (for retries)
        timeout_seconds: Timeout used for request
        client: LLM client used for request
    """
    resolved_dir = log_dir or resolve_llm_batch_log_dir()
    if resolved_dir is None:
        return
    try:
        resolved_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # pragma: no cover - best-effort logging
        logger.debug("Unable to prepare LLM batch log dir %s: %s", resolved_dir, exc)
        return

    # Extract batch ID range for filename
    batch_ids = [
        item.get("id")
        for item in request_items
        if isinstance(item.get("id"), int)
    ]
    first_id = batch_ids[0] if batch_ids else 0
    last_id = batch_ids[-1] if batch_ids else first_id
    target_label = sanitize_batch_component(target_language or "auto")

    # Generate timestamp with milliseconds and thread ID
    timestamp = time.time()
    stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime(timestamp))
    millis = int((timestamp % 1) * 1000)
    thread_id = threading.get_ident()
    filename = f"batch_{stamp}{millis:03d}_{first_id:04d}-{last_id:04d}_{target_label}_t{thread_id}_a{attempt}.json"

    # Build complete payload
    payload = {
        "timestamp": round(timestamp, 3),
        "elapsed_seconds": round(float(elapsed_seconds), 3),
        "attempt": int(attempt),
        "timeout_seconds": float(timeout_seconds),
        "batch_size": len(request_items),
        "operation": operation,
        "input_language": input_language,
        "target_language": target_language,
        "include_transliteration": bool(include_transliteration),
        "model": client.model,
        "llm_source": client.llm_source,
        "system_prompt": system_prompt,
        "user_payload": user_payload,
        "request_payload": request_payload,
        "request_items": list(request_items),
        "response_payload": response_payload,
        "response_raw_text": response_raw_text,
        "response_error": response_error,
    }

    try:
        (resolved_dir / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:  # pragma: no cover - best-effort logging
        logger.debug("Unable to write LLM batch log %s: %s", filename, exc)


# Export subdirectory constants for use by translation_engine
TRANSLATION_SUBDIR = _LLM_BATCH_TRANSLATION_SUBDIR
TRANSLITERATION_SUBDIR = _LLM_BATCH_TRANSLITERATION_SUBDIR
