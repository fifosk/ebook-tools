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
_THAI_RANGE = re.compile(r"[\u0e00-\u0e7f]")


def _normalize_language(value: str) -> str:
    lowered = (value or "").strip().lower()
    lowered = re.sub(r"\(.*?\)", "", lowered).strip()
    if lowered in {"zh", "zh-cn", "zh-tw", "cmn", "mandarin", "chinese"}:
        return "chinese"
    if lowered in {"ja", "jpn", "japanese"}:
        return "japanese"
    if lowered in {"ko", "kor", "korean"}:
        return "korean"
    if lowered in {"th", "tha", "thai"}:
        return "thai"
    if "chinese" in lowered:
        return "chinese"
    if "japanese" in lowered:
        return "japanese"
    if "korean" in lowered:
        return "korean"
    if "thai" in lowered:
        return "thai"
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
    """Return hyphen-joined hepburn, one token per space-separated Japanese word.

    Uses ``pykakasi`` to convert each space-separated word to hepburn syllables.
    pykakasi may return multiple entries per word when it recognizes internal
    morpheme boundaries; we hyphen-join those entries to keep 1:1 token
    alignment with the LLM-emitted translation spacing. Returns None when
    pykakasi is unavailable or the input has no kana/kanji.
    """
    if not _HIRAGANA_KATAKANA.search(translation) and not _HAN_RANGE.search(translation):
        return None
    try:
        import pykakasi
    except ImportError:
        return None

    kks = pykakasi.kakasi()
    out: list[str] = []
    for word in translation.split():
        # Words composed purely of ASCII/latin/punctuation are passed through
        # (with CJK punctuation mapped). This preserves any romaji or numerics
        # that the LLM may have left inline.
        if not (_HIRAGANA_KATAKANA.search(word) or _HAN_RANGE.search(word)):
            out.append(_map_punct(word))
            continue
        parts = kks.convert(word)
        syllables = [
            (p.get("hepburn") or "").strip()
            for p in parts
            if (p.get("hepburn") or "").strip()
        ]
        out.append("-".join(syllables) if syllables else word)
    return " ".join(out)


def _thai_word_aligned(translation: str) -> Optional[str]:
    """Return hyphen-joined RTGS romanization, one token per space-separated Thai word.

    Uses ``pythainlp.transliterate.romanize`` (Royal Thai General System) on
    each syllable of each LLM-spaced word. Syllables within a word are
    hyphen-joined; words are space-separated. Returns None when pythainlp
    is unavailable or the input has no Thai characters.
    """
    if not _THAI_RANGE.search(translation):
        return None
    try:
        from pythainlp.transliterate import romanize
        from pythainlp.tokenize import syllable_tokenize
    except ImportError:
        return None

    out: list[str] = []
    for word in translation.split():
        if not _THAI_RANGE.search(word):
            out.append(_map_punct(word))
            continue
        try:
            syllables = syllable_tokenize(word) or [word]
        except Exception:
            syllables = [word]
        romanized = []
        for s in syllables:
            s = s.strip()
            if not s:
                continue
            try:
                r = romanize(s).strip()
            except Exception:
                r = ""
            if r:
                romanized.append(r.replace(" ", ""))
        out.append("-".join(romanized) if romanized else word)
    return " ".join(out)


def _korean_word_aligned(translation: str) -> Optional[str]:
    """Return hyphen-joined romanization, one token per space-separated Korean word.

    Uses ``hangul_romanize`` per-syllable so each Hangul syllable block becomes
    one romanization unit; units within a word are hyphen-joined. Returns None
    when hangul_romanize is unavailable or the input has no Hangul.
    """
    if not _HANGUL.search(translation):
        return None
    try:
        from hangul_romanize import Transliter
        from hangul_romanize.rule import academic
    except ImportError:
        return None

    transliter = Transliter(academic)
    out: list[str] = []
    for word in translation.split():
        if not _HANGUL.search(word):
            out.append(_map_punct(word))
            continue
        # Per-syllable romanization so multi-syllable Korean words become
        # hyphen-joined (한국어 → han-gug-eo rather than hanguk-eo as a single
        # opaque run).
        syllables: list[str] = []
        for ch in word:
            if "\uac00" <= ch <= "\ud7a3":
                rom = transliter.translit(ch).strip()
                if rom:
                    syllables.append(rom)
            # Jamo and compatibility jamo are rarer; let the transliter handle
            # them as part of the whole-word fallback below.
        if syllables:
            out.append("-".join(syllables))
        else:
            # Fallback: whole-word romanize (covers jamo-only content).
            whole = transliter.translit(word).strip()
            out.append(whole.replace(" ", "-") if whole else word)
    return " ".join(out)


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
    if key == "thai":
        return _thai_word_aligned(translation)
    return None


__all__ = ["generate_word_aligned_transliteration"]
