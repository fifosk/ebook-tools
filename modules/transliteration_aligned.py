"""Deterministic, word-aligned transliteration for CJK target languages.

The LLM-generated transliteration is prone to subtle alignment errors: it may
merge two Chinese words into one hyphen-joined pinyin run, or split a single
word into multiple syllables. The post-processing ``align_token_counts`` pass
can force the counts to match but only by merging/splitting tokens blindly —
the result is numerically aligned but semantically mis-paired.

This module bypasses the LLM for transliteration. Given a translation string
that already carries LLM-emitted word boundaries (space-separated words), it
produces a transliteration with one token per translation token: multi-syllable
words become hyphen-joined syllables, single-syllable words are plain
syllables, punctuation tokens pass through as their ASCII equivalent.

Currently implemented:
    - Chinese → pypinyin

Stubbed for future work (return None → caller falls back to LLM):
    - Japanese → pykakasi with fugashi word boundaries
    - Korean   → hangul-romanize

Each language can be added by implementing a ``_<lang>_word_aligned`` function
and wiring it into ``generate_word_aligned_transliteration``.
"""

from __future__ import annotations

import re
from typing import Optional

# Chinese full-width punctuation → ASCII equivalent, so the transliteration
# line has one-char ASCII punctuation tokens that match their Chinese
# counterparts positionally.
_CJK_PUNCT_TO_ASCII = {
    "。": ".",
    "，": ",",
    "、": ",",
    "？": "?",
    "！": "!",
    "：": ":",
    "；": ";",
    "（": "(",
    "）": ")",
    "【": "[",
    "】": "]",
    "《": "<",
    "》": ">",
    "〈": "<",
    "〉": ">",
    "「": '"',
    "」": '"',
    "『": '"',
    "』": '"',
    "〜": "~",
}

_HAN_RANGE = re.compile(r"[\u3400-\u9fff]")
_HIRAGANA_KATAKANA = re.compile(r"[\u3040-\u30ff]")
_HANGUL = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")


def _normalize_language(value: str) -> str:
    lowered = (value or "").strip().lower()
    lowered = re.sub(r"\(.*?\)", "", lowered).strip()
    if lowered in {"zh", "zh-cn", "zh-tw", "cmn", "mandarin", "chinese"}:
        return "chinese"
    if lowered in {"ja", "jpn", "japanese"}:
        return "japanese"
    if lowered in {"ko", "kor", "korean"}:
        return "korean"
    if "chinese" in lowered:
        return "chinese"
    if "japanese" in lowered:
        return "japanese"
    if "korean" in lowered:
        return "korean"
    return ""


def _map_punct(token: str) -> str:
    return "".join(_CJK_PUNCT_TO_ASCII.get(ch, ch) for ch in token)


def _chinese_word_aligned(translation: str) -> Optional[str]:
    """Return hyphen-joined pinyin, one token per space-separated Chinese word.

    Uses ``pypinyin.lazy_pinyin``. Returns None when pypinyin is unavailable
    or the input has no Chinese characters (caller should keep the LLM output).
    """
    if not _HAN_RANGE.search(translation):
        return None
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        return None

    out: list[str] = []
    for word in translation.split():
        if _HAN_RANGE.search(word):
            syllables = [s for s in lazy_pinyin(word) if s and s.strip()]
            out.append("-".join(syllables) if syllables else word)
        else:
            out.append(_map_punct(word))
    return " ".join(out)


def _japanese_word_aligned(translation: str) -> Optional[str]:
    """Placeholder: return None so caller falls back to LLM.

    TODO: use fugashi to re-segment the translation (in case spacing was lost)
    and pykakasi to produce per-word hepburn, hyphen-join syllables within
    each word (e.g. ``日本語`` → ``nihongo`` as a single hyphen-free token,
    multi-word phrases use spaces between).
    """
    return None


def _korean_word_aligned(translation: str) -> Optional[str]:
    """Placeholder: return None so caller falls back to LLM.

    TODO: use hangul_romanize per syllable, then hyphen-join syllables within
    each space-separated Korean word.
    """
    return None


def generate_word_aligned_transliteration(
    translation: str, target_language: str
) -> Optional[str]:
    """Deterministically produce a transliteration 1:1 aligned with translation tokens.

    Returns None when no deterministic transliterator is available for the
    language, or when the input doesn't contain the expected script. The
    caller should retain the LLM-generated transliteration in that case.
    """
    if not translation:
        return None
    key = _normalize_language(target_language)
    if key == "chinese":
        return _chinese_word_aligned(translation)
    if key == "japanese":
        return _japanese_word_aligned(translation)
    if key == "korean":
        return _korean_word_aligned(translation)
    return None


__all__ = ["generate_word_aligned_transliteration"]
