from __future__ import annotations

import html
from pathlib import Path
from typing import Optional, Sequence

from modules.transliteration import TransliterationService

from .common import _AssDialogue, _WHITESPACE_PATTERN, logger
from .dialogues import (
    _HTML_TAG_PATTERN,
    _clip_dialogues_to_window,
    _merge_overlapping_dialogues,
    _parse_batch_start_seconds,
    _parse_dialogues,
    _seconds_to_vtt_timestamp,
)
from .language import _find_language_token, _language_uses_non_latin, _normalize_rtl_word_order, _transliterate_text
from .video_utils import _probe_duration_seconds

_WEBVTT_HEADER = "WEBVTT\n\n"
_WEBVTT_STYLE_BLOCK = """STYLE
::cue(.original) { color: #facc15; }
::cue(.transliteration) { color: #f97316; }
::cue(.translation) { color: #22c55e; }

"""


def _write_webvtt(
    dialogues: Sequence[_AssDialogue],
    destination: Path,
    *,
    target_language: Optional[str] = None,
    include_transliteration: bool = False,
    transliterator: Optional[TransliterationService] = None,
) -> Path:
    """Serialize dialogues into a WebVTT file."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    resolved_language = target_language or _find_language_token(destination)

    def _clean_line(value: str) -> str:
        if not value:
            return ""
        unescaped = html.unescape(value)
        stripped = _HTML_TAG_PATTERN.sub("", unescaped)
        return _WHITESPACE_PATTERN.sub(" ", stripped).strip()

    def _resolve_transliteration(entry: _AssDialogue) -> str:
        if not include_transliteration:
            return entry.transliteration or ""
        if entry.transliteration:
            return entry.transliteration
        if transliterator is None or resolved_language is None:
            return ""
        try:
            return _transliterate_text(
                transliterator,
                entry.translation,
                resolved_language,
            )
        except Exception:
            return ""

    def _format_lines(entry: _AssDialogue) -> str:
        original = _clean_line(entry.original)
        transliteration = _normalize_rtl_word_order(
            _clean_line(_resolve_transliteration(entry)),
            resolved_language,
            force=False,
        )
        translation = _normalize_rtl_word_order(
            _clean_line(entry.translation),
            resolved_language,
            force=True,
        )

        # Deduplicate content: skip lines that are identical (case-insensitive, trimmed).
        seen: set[str] = set()
        payload_lines: list[str] = []

        def _add_line(label: str | None, css_class: str) -> None:
            if not label:
                return
            normalised = label.strip().lower()
            if not normalised or normalised in seen:
                return
            seen.add(normalised)
            payload_lines.append(f"<c.{css_class}>{html.escape(label)}</c>")

        _add_line(original, "original")
        _add_line(transliteration, "transliteration")
        _add_line(translation, "translation")

        if payload_lines:
            return "\n".join(payload_lines)
        return translation or original or transliteration or ""

    with destination.open("w", encoding="utf-8") as handle:
        handle.write(_WEBVTT_HEADER)
        handle.write(_WEBVTT_STYLE_BLOCK)
        for index, entry in enumerate(dialogues, 1):
            start_ts = _seconds_to_vtt_timestamp(entry.start)
            end_ts = _seconds_to_vtt_timestamp(entry.end)
            if entry.end <= entry.start:
                continue
            payload = _format_lines(entry)
            if not payload.strip():
                continue
            handle.write(f"{index}\n{start_ts} --> {end_ts}\n{payload}\n\n")
    return destination


def _ensure_webvtt_variant(
    source: Path,
    storage_root: Optional[Path],
    *,
    target_language: Optional[str] = None,
    include_transliteration: bool = False,
    transliterator: Optional[TransliterationService] = None,
) -> Optional[Path]:
    """Create (or refresh) a WebVTT sibling for ``source`` inside ``storage_root`` if possible."""

    if storage_root is None:
        return None
    try:
        if source.suffix.lower() == ".vtt":
            return source
        dialogues = _parse_dialogues(source)
        dialogues = _merge_overlapping_dialogues(dialogues)
        if not dialogues:
            return None
        target = storage_root / f"{source.stem}.vtt"
        # Always rewrite so latest RTL/transliteration rules apply.
        return _write_webvtt(
            dialogues,
            target,
            target_language=target_language or _find_language_token(source),
            include_transliteration=include_transliteration,
            transliterator=transliterator if include_transliteration else None,
        )
    except Exception:
        logger.debug("Unable to create WebVTT variant for %s", source, exc_info=True)
        return None


def _ensure_webvtt_for_video(
    subtitle_source: Path,
    video_path: Path,
    storage_root: Optional[Path],
    *,
    target_language: Optional[str] = None,
    include_transliteration: bool = False,
    transliterator: Optional[TransliterationService] = None,
) -> Optional[Path]:
    """Create (or refresh) a VTT aligned to the rendered video (including batch offsets)."""

    if storage_root is None:
        return None
    try:
        window_start = _parse_batch_start_seconds(video_path) or 0.0
        duration = _probe_duration_seconds(video_path)
        window_end = window_start + duration if duration > 0 else None
        dialogues = _parse_dialogues(subtitle_source)
        dialogues = _merge_overlapping_dialogues(dialogues)
        clipped = _clip_dialogues_to_window(dialogues, start_offset=window_start, end_offset=window_end)
        if not clipped:
            return None
        source_span = max((entry.end for entry in clipped), default=0.0)
        scale = None
        if source_span and source_span > 0 and duration and duration > 0:
            scale = max(duration / source_span, 0.0001)
        # Shift to the video timeline (batch starts at 0) and scale to the rendered duration.
        shifted = []
        for entry in clipped:
            local_start = entry.start
            local_end = entry.end
            if scale is not None:
                local_start *= scale
                local_end *= scale
            shifted.append(
                _AssDialogue(
                    start=local_start,
                    end=local_end,
                    translation=entry.translation,
                    original=entry.original,
                    transliteration=entry.transliteration,
                    rtl_normalized=entry.rtl_normalized,
                )
            )
        shifted = _merge_overlapping_dialogues(shifted)
        if not shifted:
            return None
        target = storage_root / f"{video_path.stem}.vtt"
        # Always rewrite so latest RTL/transliteration rules apply.
        return _write_webvtt(
            shifted,
            target,
            target_language=target_language or _find_language_token(subtitle_source),
            include_transliteration=include_transliteration,
            transliterator=transliterator if include_transliteration else None,
        )
    except Exception:
        logger.debug("Unable to create aligned WebVTT for %s", video_path, exc_info=True)
        return None


__all__ = [
    "_WEBVTT_HEADER",
    "_WEBVTT_STYLE_BLOCK",
    "_ensure_webvtt_for_video",
    "_ensure_webvtt_variant",
    "_write_webvtt",
    "logger",
]
