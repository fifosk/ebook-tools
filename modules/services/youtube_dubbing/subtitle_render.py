from __future__ import annotations

from typing import Optional, Sequence

from modules.subtitles.models import SubtitleCue
from modules.subtitles.render import CueTextRenderer, _SubtitleFileWriter, _build_output_cues
from modules.transliteration import TransliterationService

from .common import _AssDialogue
from .language import _normalize_rtl_word_order, _transliterate_text


def render_ass_for_block(
    dialogues: Sequence[_AssDialogue],
    writer: _SubtitleFileWriter,
    *,
    start_index: int,
    offset_seconds: float = 0.0,
    include_transliteration: bool,
    transliterator: Optional[TransliterationService],
    language_code: str,
    ass_renderer: CueTextRenderer,
) -> int:
    """Write translated cues to an ASS writer with optional transliteration."""

    next_index = start_index
    for entry in dialogues:
        transliteration = entry.transliteration or ""
        if include_transliteration and transliterator is not None and not transliteration:
            try:
                transliteration = _transliterate_text(
                    transliterator,
                    entry.translation,
                    language_code,
                )
            except Exception:
                transliteration = ""
        render_translation = _normalize_rtl_word_order(
            entry.translation,
            language_code,
            force=True,
        )
        render_transliteration = transliteration
        speech_offset = max(0.0, entry.speech_offset or 0.0)
        speech_duration = entry.speech_duration if entry.speech_duration is not None else None
        source_cue = SubtitleCue(
            index=next_index,
            start=max(0.0, entry.start - offset_seconds),
            end=max(0.0, entry.end - offset_seconds),
            lines=[entry.original],
        )
        rendered_cues = _build_output_cues(
            source_cue,
            render_translation,
            render_transliteration,
            highlight=True,
            show_original=True,
            renderer=ass_renderer,
            original_text=entry.original,
            # Drive highlights across the dubbed subtitle span; speech windows
            # can be noisy for some languages.
            active_start_offset=0.0,
            active_duration=None,
        )
        next_index = writer.write(rendered_cues)
    try:
        writer.handle.flush()
    except Exception:
        pass
    return next_index


__all__ = ["render_ass_for_block"]
