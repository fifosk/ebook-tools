from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple

from modules.progress_tracker import ProgressTracker
from modules.retry_annotations import is_failure_annotation
from modules.subtitles.translation import _translate_text as _translate_subtitle_text
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
