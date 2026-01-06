from __future__ import annotations

import queue
from typing import List, Optional, Sequence, Tuple

from .. import translation_engine
from ..translation_engine import ThreadWorkerPool
from ..transliteration import TransliterationService, get_transliterator
from .. import text_normalization as text_norm


def translate_sentence_simple(
    sentence: str,
    input_language: str,
    target_language: str,
    *,
    include_transliteration: bool = False,
    translation_provider: Optional[str] = None,
    client=None,
    progress_tracker=None,
):
    """Translate a sentence using the configured translation engine."""

    return translation_engine.translate_sentence_simple(
        sentence,
        input_language,
        target_language,
        include_transliteration=include_transliteration,
        translation_provider=translation_provider,
        client=client,
        progress_tracker=progress_tracker,
    )


def transliterate_sentence(
    translated_sentence: str,
    target_language: str,
    *,
    client=None,
    transliterator: Optional[TransliterationService] = None,
    transliteration_mode: Optional[str] = None,
    progress_tracker=None,
) -> str:
    """Return a transliteration for ``translated_sentence`` when supported."""

    service = transliterator or get_transliterator()
    result = service.transliterate(
        translated_sentence,
        target_language,
        client=client,
        mode=transliteration_mode,
        progress_tracker=progress_tracker,
    )
    return result.text


def translate_batch(
    sentences: Sequence[str],
    input_language: str,
    target_languages: Sequence[str],
    *,
    include_transliteration: bool = False,
    translation_provider: Optional[str] = None,
    max_workers: Optional[int] = None,
    client=None,
    worker_pool=None,
    progress_tracker=None,
) -> List[str]:
    """Translate ``sentences`` sequentially for the provided ``target_languages``."""

    return translation_engine.translate_batch(
        sentences,
        input_language,
        target_languages,
        include_transliteration=include_transliteration,
        translation_provider=translation_provider,
        max_workers=max_workers,
        client=client,
        worker_pool=worker_pool,
        progress_tracker=progress_tracker,
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

    return text_norm.split_translation_and_transliteration(text)


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
    translation_provider: Optional[str] = None,
    transliteration_mode: Optional[str] = None,
    transliteration_client=None,
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
        translation_provider=translation_provider,
        transliteration_mode=transliteration_mode,
        transliteration_client=transliteration_client,
        include_transliteration=include_transliteration,
    )
