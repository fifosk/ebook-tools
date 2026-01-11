from __future__ import annotations

import contextlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple

from modules.llm_client import create_client
from modules import text_normalization as text_norm
from modules.progress_tracker import ProgressTracker
from modules.retry_annotations import is_failure_annotation
from modules.subtitles.translation import (
    _looks_like_gibberish_translation,
    _translate_text as _translate_subtitle_text,
)
from modules.translation_engine import translate_batch
from modules.transliteration import TransliterationService

from .common import _AssDialogue, logger
from .language import _transliterate_text
from .workers import _resolve_llm_worker_count


def translate_dialogues(
    dialogues: List[_AssDialogue],
    *,
    source_language: Optional[str],
    target_language: str,
    translation_provider: Optional[str] = None,
    translation_batch_size: Optional[int] = None,
    include_transliteration: bool,
    transliterator: Optional[TransliterationService],
    llm_model: Optional[str],
    transliteration_mode: Optional[str] = None,
    tracker: Optional[ProgressTracker],
    offset: int,
    total_dialogues: int,
) -> List[_AssDialogue]:
    """Translate and optionally transliterate dialogues in parallel."""

    needs_translation = source_language and target_language and source_language.lower() != target_language.lower()
    needs_llm = needs_translation or (include_transliteration and transliterator is not None)
    if not needs_llm:
        return [
            _AssDialogue(
                start=entry.start,
                end=entry.end,
                translation=entry.translation,
                original=entry.original,
                transliteration=entry.transliteration,
                rtl_normalized=entry.rtl_normalized,
                speech_offset=entry.speech_offset,
                speech_duration=entry.speech_duration,
            )
            for entry in dialogues
        ]

    resolved_transliteration_mode = (transliteration_mode or "").strip().lower().replace("_", "-")
    allow_llm_transliteration = (
        include_transliteration
        and transliterator is not None
        and resolved_transliteration_mode != "python"
    )
    use_llm_batching = (
        needs_translation
        and (translation_provider or "llm") == "llm"
        and translation_batch_size is not None
        and translation_batch_size > 1
    )

    if use_llm_batching:
        sentences = [entry.translation for entry in dialogues]
        sentence_numbers = [offset + idx + 1 for idx in range(len(sentences))]
        client_context = (
            create_client(model=llm_model) if llm_model else contextlib.nullcontext()
        )
        try:
            with client_context as client:
                resolved_client = client if llm_model else None
                translations = translate_batch(
                    sentences,
                    source_language or target_language,
                    target_language,
                    include_transliteration=allow_llm_transliteration,
                    translation_provider=translation_provider,
                    llm_batch_size=translation_batch_size,
                    client=resolved_client,
                    max_workers=_resolve_llm_worker_count(len(dialogues)),
                    progress_tracker=tracker,
                    sentence_numbers=sentence_numbers,
                )
        except Exception:  # pragma: no cover - fall back to per-entry processing
            translations = []
        if len(translations) == len(dialogues):
            results: List[_AssDialogue] = []
            for idx, entry in enumerate(dialogues):
                translated_text = entry.translation
                transliteration_text = entry.transliteration
                translated_flag = False
                inline_translit = ""
                if needs_translation:
                    raw_candidate = (translations[idx] or "").strip()
                    if raw_candidate and not is_failure_annotation(raw_candidate):
                        translation_line, inline_translit = text_norm.split_translation_and_transliteration(
                            raw_candidate
                        )
                        translation_line = text_norm.collapse_whitespace(
                            (translation_line or raw_candidate).strip()
                        )
                        inline_translit = text_norm.collapse_whitespace(inline_translit or "")
                        if inline_translit and not text_norm.is_latin_heavy(inline_translit):
                            inline_translit = ""
                    else:
                        translation_line = ""
                    if not translation_line or _looks_like_gibberish_translation(
                        source=entry.translation,
                        candidate=translation_line,
                    ):
                        try:
                            translated_text = _translate_subtitle_text(
                                entry.translation,
                                source_language=source_language or target_language,
                                target_language=target_language,
                                llm_model=llm_model,
                                translation_provider=translation_provider,
                                progress_tracker=tracker,
                            )
                        except Exception:
                            translated_text = entry.translation
                        else:
                            if is_failure_annotation(translated_text):
                                translated_text = entry.translation
                        inline_translit = ""
                    else:
                        translated_text = translation_line
                    translated_flag = True
                if include_transliteration and transliterator is not None and not transliteration_text:
                    try:
                        if allow_llm_transliteration and inline_translit:
                            transliteration_text = inline_translit
                        else:
                            transliteration_text = _transliterate_text(
                                transliterator,
                                translated_text or entry.translation,
                                target_language,
                                transliteration_mode=transliteration_mode,
                                llm_model=llm_model,
                                progress_tracker=tracker,
                            )
                    except Exception:
                        transliteration_text = None
                results.append(
                    _AssDialogue(
                        start=entry.start,
                        end=entry.end,
                        translation=translated_text,
                        original=entry.original,
                        transliteration=transliteration_text,
                        rtl_normalized=entry.rtl_normalized,
                        speech_offset=entry.speech_offset,
                        speech_duration=entry.speech_duration,
                    )
                )
                if tracker is not None and translated_flag:
                    tracker.record_step_completion(
                        stage="translation",
                        index=offset + idx + 1,
                        total=total_dialogues,
                        metadata={"start": entry.start, "end": entry.end},
                    )
            return results

    def _process(idx: int, entry: _AssDialogue) -> Tuple[int, _AssDialogue, bool]:
        translated_text = entry.translation
        transliteration_text = entry.transliteration
        rtl_normalized = entry.rtl_normalized
        translated_flag = False
        if needs_translation:
            try:
                translated_text = _translate_subtitle_text(
                    entry.translation,
                    source_language=source_language or target_language,
                    target_language=target_language,
                    llm_model=llm_model,
                    translation_provider=translation_provider,
                    progress_tracker=tracker,
                )
                translated_flag = True
                if is_failure_annotation(translated_text):
                    translated_text = entry.translation
            except Exception:
                translated_text = entry.translation
        if include_transliteration and transliterator is not None and not transliteration_text:
            try:
                transliteration_text = _transliterate_text(
                    transliterator,
                    translated_text or entry.translation,
                    target_language,
                    transliteration_mode=transliteration_mode,
                    llm_model=llm_model,
                    progress_tracker=tracker,
                )
            except Exception:
                transliteration_text = None
        return idx, _AssDialogue(
            start=entry.start,
            end=entry.end,
            translation=translated_text,
            original=entry.original,
            transliteration=transliteration_text,
            rtl_normalized=rtl_normalized,
            speech_offset=entry.speech_offset,
            speech_duration=entry.speech_duration,
        ), translated_flag

    workers = _resolve_llm_worker_count(len(dialogues))
    if workers <= 1:
        results = []
        for local_idx, entry in enumerate(dialogues):
            idx, dialogue, translated_flag = _process(local_idx, entry)
            results.append(dialogue)
            if tracker is not None and translated_flag:
                tracker.record_step_completion(
                    stage="translation",
                    index=offset + idx + 1,
                    total=total_dialogues,
                    metadata={"start": entry.start, "end": entry.end},
                )
        return results

    resolved: List[Optional[_AssDialogue]] = [None] * len(dialogues)
    futures = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for local_idx, entry in enumerate(dialogues):
            futures.append(executor.submit(_process, local_idx, entry))
        for future in as_completed(futures):
            idx, dialogue, translated_flag = future.result()
            resolved[idx] = dialogue
            if tracker is not None and translated_flag:
                tracker.record_step_completion(
                    stage="translation",
                    index=offset + idx + 1,
                    total=total_dialogues,
                    metadata={"start": dialogue.start, "end": dialogue.end},
                )
    return [entry for entry in resolved if entry is not None]


__all__ = ["translate_dialogues"]
