from __future__ import annotations

import queue
from typing import Iterable, List, Optional, Sequence, Tuple

from .. import translation_engine
from ..translation_engine import ThreadWorkerPool
from ..transliteration import TransliterationService, get_transliterator


def translate_sentence_simple(
    sentence: str,
    input_language: str,
    target_language: str,
    *,
    include_transliteration: bool = False,
    client=None,
):
    """Translate a sentence using the configured translation engine."""

    return translation_engine.translate_sentence_simple(
        sentence,
        input_language,
        target_language,
        include_transliteration=include_transliteration,
        client=client,
    )


def transliterate_sentence(
    translated_sentence: str,
    target_language: str,
    *,
    client=None,
    transliterator: Optional[TransliterationService] = None,
) -> str:
    """Return a transliteration for ``translated_sentence`` when supported."""

    service = transliterator or get_transliterator()
    result = service.transliterate(translated_sentence, target_language, client=client)
    return result.text


def translate_batch(
    sentences: Sequence[str],
    input_language: str,
    target_languages: Sequence[str],
    *,
    include_transliteration: bool = False,
    max_workers: Optional[int] = None,
    client=None,
    worker_pool=None,
) -> List[str]:
    """Translate ``sentences`` sequentially for the provided ``target_languages``."""

    return translation_engine.translate_batch(
        sentences,
        input_language,
        target_languages,
        include_transliteration=include_transliteration,
        max_workers=max_workers,
        client=client,
        worker_pool=worker_pool,
    )


def build_target_sequence(
    target_languages: Sequence[str],
    total_sentences: int,
    *,
    start_sentence: int,
) -> List[str]:
    """Return the repeating sequence of target languages for ``total_sentences``."""

    if not target_languages:
        return ["" for _ in range(total_sentences)]

    cycle_length = len(target_languages)
    return [
        target_languages[((start_sentence + idx) - start_sentence) % cycle_length]
        for idx in range(total_sentences)
    ]


def create_translation_queue(max_size: int) -> "queue.Queue":
    """Return a bounded queue used to hand off translation results."""

    return queue.Queue(maxsize=max_size)


def split_translation_and_transliteration(text: str) -> Tuple[str, str]:
    """Separate a combined translation/transliteration response."""

    if not text:
        return "", ""

    translation_line = ""
    transliteration_parts: List[str] = []
    normalized = text.replace("\r\n", "\n").split("\n")

    def _strip_known_prefix(value: str, prefixes: Iterable[str]) -> str:
        lowered = value.lower()
        for prefix in prefixes:
            if lowered.startswith(prefix):
                return value[len(prefix) :].strip()
        return value

    translation_prefixes = (
        "translation:",
        "translated:",
        "translated text:",
        "result:",
        "output:",
    )
    transliteration_prefixes = (
        "transliteration:",
        "romanization:",
        "romanisation:",
    )

    for raw_line in normalized:
        line = raw_line.strip()
        if not line:
            continue
        if not translation_line:
            translation_line = _strip_known_prefix(line, translation_prefixes)
            continue
        cleaned = _strip_known_prefix(line, transliteration_prefixes)
        transliteration_parts.append(cleaned)

    transliteration_text = " ".join(part for part in transliteration_parts if part).strip()
    return translation_line.strip(), transliteration_text


def start_translation_pipeline(
    sentences: Sequence[str],
    input_language: str,
    target_sequence: Sequence[str],
    *,
    start_sentence: int,
    output_queue: "queue.Queue",
    consumer_count: int,
    stop_event=None,
    worker_count: Optional[int] = None,
    progress_tracker=None,
    client=None,
    worker_pool: Optional[ThreadWorkerPool] = None,
    transliterator: Optional[TransliterationService] = None,
    include_transliteration: bool = False,
):
    """Start the background translation pipeline using the translation engine."""

    return translation_engine.start_translation_pipeline(
        sentences,
        input_language,
        target_sequence,
        start_sentence=start_sentence,
        output_queue=output_queue,
        consumer_count=consumer_count,
        stop_event=stop_event,
        max_workers=worker_count,
        progress_tracker=progress_tracker,
        client=client,
        worker_pool=worker_pool,
        transliterator=transliterator,
        include_transliteration=include_transliteration,
    )
