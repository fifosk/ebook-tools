"""Batch LLM lookup for word definitions.

This module handles batched dictionary lookups using the LLM,
following the same patterns as the translation batch module.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.progress_tracker import ProgressTracker

from modules import llm_batch, prompt_templates
from modules.llm_client import LLMClient
from modules.translation_logging import write_llm_batch_artifact

from .models import LookupCache, LookupCacheEntry
from .tokenizer import normalize_word

# Constants
_LLM_REQUEST_ATTEMPTS = 3
_LOOKUP_RESPONSE_ATTEMPTS = 3
_LOOKUP_RETRY_DELAY_SECONDS = 1.0
_DEFAULT_BATCH_SIZE = 10
_DEFAULT_TIMEOUT_SECONDS = 45.0

LOOKUP_BATCH_SUBDIR = "lookup"


def build_lookup_system_prompt(
    input_language: str,
    definition_language: str,
) -> str:
    """Build the system prompt for batch word lookups.

    Args:
        input_language: Source language of the words.
        definition_language: Language for definitions.

    Returns:
        System prompt string.
    """
    resolved_input = (input_language or "").strip() or "the input language"
    resolved_definition = (definition_language or "").strip() or "English"

    return f"""You are MyLinguist, a dictionary assistant.
You will receive a batch of words in {resolved_input}.
For each word, provide a dictionary entry in {resolved_definition}.

Return ONLY valid JSON in this exact format:
{{
  "items": [
    {{
      "id": 0,
      "word": "original word",
      "type": "word",
      "definition": "Main definition (required)",
      "part_of_speech": "noun/verb/adj/etc or null",
      "pronunciation": "IPA or common reading, or null",
      "etymology": "Brief origin/root, or null",
      "example": "Short example usage, or null",
      "example_translation": "Translation of example in {resolved_definition}, or null",
      "example_transliteration": "Romanized version if non-Latin script, or null",
      "related_languages": [
        {{"language": "Persian", "word": "کتاب", "transliteration": "ketāb"}}
      ]
    }}
  ]
}}

Rules:
- Keep definitions concise (one line max)
- Include pronunciation for non-Latin scripts
- Include transliteration for related_languages entries with non-Latin scripts
- If uncertain about etymology, use null (do NOT guess)
- For Arabic: include full tashkīl/harakāt (diacritics)
- For Hebrew: include full niqqud (vowel points)
- related_languages: show up to 3 related cognates/borrowings. null if none
- Return items in the same order as input"""


def extract_batch_items(payload: Any) -> Optional[List[Mapping[str, Any]]]:
    """Extract items list from LLM batch response payload.

    Handles both {"items": [...]} and direct list responses.

    Args:
        payload: Response payload from LLM.

    Returns:
        List of item dictionaries, or None if invalid.
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

    Args:
        item: Response item dictionary.
        fallback_id: Fallback ID if none found.

    Returns:
        Item ID, or fallback_id if extraction fails.
    """
    for key in ("id", "index", "word_id"):
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


def parse_lookup_item(item: Mapping[str, Any]) -> Dict[str, Any]:
    """Parse a single lookup result item into LinguistLookupResult format.

    Args:
        item: Raw item from LLM response.

    Returns:
        Parsed lookup result dictionary.
    """
    result: Dict[str, Any] = {
        "type": str(item.get("type", "word")),
        "definition": str(item.get("definition", "")).strip(),
    }

    # Optional fields
    for field in (
        "part_of_speech",
        "pronunciation",
        "etymology",
        "example",
        "example_translation",
        "example_transliteration",
    ):
        value = item.get(field)
        if value is not None and str(value).strip():
            result[field] = str(value).strip()
        else:
            result[field] = None

    # Idioms (for sentences)
    idioms = item.get("idioms")
    if isinstance(idioms, list) and idioms:
        result["idioms"] = [str(i).strip() for i in idioms if i]
    else:
        result["idioms"] = None

    # Related languages
    related = item.get("related_languages")
    if isinstance(related, list) and related:
        parsed_related = []
        for entry in related:
            if isinstance(entry, Mapping):
                lang_entry = {
                    "language": str(entry.get("language", "")).strip(),
                    "word": str(entry.get("word", "")).strip(),
                }
                translit = entry.get("transliteration")
                if translit is not None and str(translit).strip():
                    lang_entry["transliteration"] = str(translit).strip()
                else:
                    lang_entry["transliteration"] = None
                if lang_entry["language"] and lang_entry["word"]:
                    parsed_related.append(lang_entry)
        result["related_languages"] = parsed_related if parsed_related else None
    else:
        result["related_languages"] = None

    return result


def parse_batch_lookup_payload(
    payload: Any,
    *,
    input_ids: Sequence[int],
    words: Sequence[str],
    input_language: str,
    definition_language: str,
) -> Dict[str, LookupCacheEntry]:
    """Parse LLM batch lookup response into cache entries.

    Args:
        payload: LLM response payload.
        input_ids: Input item IDs for positional fallback.
        words: Original words in order.
        input_language: Source language.
        definition_language: Definition language.

    Returns:
        Dict mapping normalized word -> LookupCacheEntry.
    """
    items = extract_batch_items(payload)
    if not items:
        return {}

    use_positional = len(items) == len(input_ids)
    results: Dict[str, LookupCacheEntry] = {}

    for idx, item in enumerate(items):
        fallback_id = input_ids[idx] if use_positional else None
        item_id = coerce_batch_item_id(item, fallback_id)

        if item_id is None:
            continue

        # Get the original word
        if 0 <= item_id < len(words):
            original_word = words[item_id]
        else:
            original_word = str(item.get("word", "")).strip()

        if not original_word:
            continue

        # Parse the lookup result
        lookup_result = parse_lookup_item(item)

        # Skip if no definition
        if not lookup_result.get("definition"):
            continue

        # Use normalize_word to strip diacritics, lowercase, etc.
        # This ensures consistent cache keys with what's used during lookup
        normalized = normalize_word(original_word)
        if not normalized:
            continue

        entry = LookupCacheEntry(
            word=original_word,
            word_normalized=normalized,
            input_language=input_language,
            definition_language=definition_language,
            lookup_result=lookup_result,
            audio_references=[],
            created_at=time.time(),
        )

        results[normalized] = entry

    return results


def lookup_words_batch(
    words: Sequence[str],
    input_language: str,
    definition_language: str,
    *,
    resolved_client: LLMClient,
    progress_tracker: Optional["ProgressTracker"] = None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    batch_log_dir: Optional[Path] = None,
) -> Tuple[Dict[str, LookupCacheEntry], Optional[str], float]:
    """Look up a batch of words using the LLM.

    Args:
        words: Words to look up.
        input_language: Source language.
        definition_language: Definition language.
        resolved_client: LLM client to use.
        progress_tracker: Optional progress tracker.
        timeout_seconds: Request timeout.
        batch_log_dir: Optional directory for batch logging.

    Returns:
        Tuple of (results_dict, error, elapsed_seconds).
        results_dict maps normalized word -> LookupCacheEntry.
    """
    system_prompt = build_lookup_system_prompt(input_language, definition_language)

    request_items = [{"id": idx, "text": word} for idx, word in enumerate(words)]
    user_payload = llm_batch.build_json_batch_payload(request_items)
    request_payload = prompt_templates.make_sentence_payload(
        user_payload,
        model=resolved_client.model,
        stream=False,
        system_prompt=system_prompt,
    )
    input_ids = list(range(len(words)))

    def _payload_has_items(payload: Any) -> bool:
        items = extract_batch_items(payload)
        return bool(items)

    start_time = time.perf_counter()
    last_error: Optional[str] = None

    for attempt in range(1, _LOOKUP_RESPONSE_ATTEMPTS + 1):
        response = llm_batch.request_json_batch(
            client=resolved_client,
            system_prompt=system_prompt,
            items=request_items,
            timeout_seconds=timeout_seconds,
            max_attempts=_LLM_REQUEST_ATTEMPTS,
            validator=_payload_has_items,
        )

        # Log batch artifact
        if batch_log_dir is not None:
            write_llm_batch_artifact(
                operation="lookup",
                log_dir=batch_log_dir,
                request_items=request_items,
                input_language=input_language,
                target_language=definition_language,
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
            parsed = parse_batch_lookup_payload(
                response.payload,
                input_ids=input_ids,
                words=words,
                input_language=input_language,
                definition_language=definition_language,
            )
            if parsed:
                elapsed = time.perf_counter() - start_time
                return parsed, None, elapsed
            last_error = "Empty lookup payload"
        else:
            last_error = response.error or "Invalid lookup response"

        if progress_tracker is not None and last_error:
            progress_tracker.record_retry("lookup_cache", last_error)

        if attempt < _LOOKUP_RESPONSE_ATTEMPTS:
            time.sleep(_LOOKUP_RETRY_DELAY_SECONDS)

    elapsed = time.perf_counter() - start_time
    return {}, last_error, elapsed


def build_lookup_cache_batch(
    words: Sequence[str],
    input_language: str,
    definition_language: str,
    *,
    llm_client: LLMClient,
    batch_size: int = _DEFAULT_BATCH_SIZE,
    progress_tracker: Optional["ProgressTracker"] = None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    batch_log_dir: Optional[Path] = None,
    existing_cache: Optional[LookupCache] = None,
    on_batch_complete: Optional[Callable[[Dict[str, LookupCacheEntry]], None]] = None,
) -> Tuple[Dict[str, LookupCacheEntry], int, float]:
    """Build lookup cache entries for a list of words.

    Chunks words into batches and makes LLM calls for definitions.

    Args:
        words: Words to look up.
        input_language: Source language.
        definition_language: Definition language.
        llm_client: LLM client to use.
        batch_size: Maximum words per batch.
        progress_tracker: Optional progress tracker.
        timeout_seconds: Request timeout per batch.
        batch_log_dir: Optional directory for batch logging.
        existing_cache: Optional existing cache to skip duplicates.
        on_batch_complete: Optional callback invoked after each batch with new entries.
            Use this to save the cache incrementally so lookups become available sooner.

    Returns:
        Tuple of (all_entries, llm_call_count, total_elapsed).
    """
    if not words:
        return {}, 0, 0.0

    # Filter out words already in cache
    words_to_lookup = []
    for word in words:
        normalized = normalize_word(word)
        if not normalized:
            continue
        if existing_cache is not None and existing_cache.get(normalized):
            continue
        words_to_lookup.append(word)

    if not words_to_lookup:
        return {}, 0, 0.0

    # Chunk into batches
    batches: List[List[str]] = []
    for i in range(0, len(words_to_lookup), batch_size):
        batches.append(words_to_lookup[i : i + batch_size])

    all_entries: Dict[str, LookupCacheEntry] = {}
    total_elapsed = 0.0
    llm_call_count = 0

    for batch_idx, batch in enumerate(batches):
        entries, _error, elapsed = lookup_words_batch(
            batch,
            input_language,
            definition_language,
            resolved_client=llm_client,
            progress_tracker=progress_tracker,
            timeout_seconds=timeout_seconds,
            batch_log_dir=batch_log_dir,
        )

        all_entries.update(entries)
        total_elapsed += elapsed
        llm_call_count += 1

        # Invoke callback to allow incremental saves after each batch
        if on_batch_complete is not None and entries:
            on_batch_complete(entries)

        # Publish progress after each batch
        if progress_tracker is not None:
            progress_tracker.publish_progress(
                {
                    "stage": "lookup_cache",
                    "message": f"Building lookup cache: {len(all_entries)} words cached",
                    "lookup_cache_progress": {
                        "batches_completed": batch_idx + 1,
                        "batches_total": len(batches),
                        "words_to_lookup": len(words_to_lookup),
                        "cached_entries": len(all_entries),
                        "llm_calls": llm_call_count,
                    },
                }
            )

    return all_entries, llm_call_count, total_elapsed


__all__ = [
    "LOOKUP_BATCH_SUBDIR",
    "build_lookup_cache_batch",
    "build_lookup_system_prompt",
    "lookup_words_batch",
    "parse_batch_lookup_payload",
]
