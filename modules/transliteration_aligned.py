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
_KHMER_RANGE = re.compile(r"[\u1780-\u17ff]")
_MYANMAR_RANGE = re.compile(r"[\u1000-\u109f\uaa60-\uaa7f\ua9e0-\ua9ff]")
_LAO_RANGE = re.compile(r"[\u0e80-\u0eff]")


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
    if lowered in {"km", "khm", "khmer", "cambodian"}:
        return "khmer"
    if lowered in {"my", "mya", "bur", "burmese", "myanmar"}:
        return "burmese"
    if lowered in {"lo", "lao", "laotian", "laos"}:
        return "lao"
    if "chinese" in lowered:
        return "chinese"
    if "japanese" in lowered:
        return "japanese"
    if "korean" in lowered:
        return "korean"
    if "thai" in lowered:
        return "thai"
    if "khmer" in lowered or "cambodian" in lowered:
        return "khmer"
    if "burmese" in lowered or "myanmar" in lowered:
        return "burmese"
    if "laotian" in lowered or "lao" in lowered:
        return "lao"
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


_ICU_TRANSLITERATOR_CACHE: dict[str, object] = {}


def _get_icu_transliterator(name: str):
    """Lazy-initialize an ICU transliterator; cache for reuse. Returns None if PyICU unavailable."""
    if name in _ICU_TRANSLITERATOR_CACHE:
        return _ICU_TRANSLITERATOR_CACHE[name]
    try:
        from icu import Transliterator  # type: ignore
    except ImportError:
        _ICU_TRANSLITERATOR_CACHE[name] = None
        return None
    try:
        translit = Transliterator.createInstance(name)
    except Exception:
        _ICU_TRANSLITERATOR_CACHE[name] = None
        return None
    _ICU_TRANSLITERATOR_CACHE[name] = translit
    return translit


def _romanize_icu_per_word(
    translation: str,
    script_pattern: "re.Pattern[str]",
    icu_instance_name: str,
) -> Optional[str]:
    """Shared per-word romanization via an ICU transliterator.

    Splits ``translation`` on whitespace, transliterates each script-bearing
    word independently, and collapses any internal whitespace in ICU's output
    with hyphens so each translation word maps to exactly one output token.
    Non-script tokens (punctuation) pass through via :func:`_map_punct`.
    Returns None when ICU is unavailable or the text has no target script.
    """
    if not script_pattern.search(translation):
        return None
    translit = _get_icu_transliterator(icu_instance_name)
    if translit is None:
        return None
    out: list[str] = []
    for word in translation.split():
        if not script_pattern.search(word):
            out.append(_map_punct(word))
            continue
        try:
            romanized = translit.transliterate(word)
        except Exception:
            romanized = ""
        romanized = (romanized or "").strip()
        # ICU often inserts spaces between syllables — collapse to hyphens so
        # the result is exactly one token per translation word.
        romanized = re.sub(r"\s+", "-", romanized)
        out.append(romanized if romanized else word)
    return " ".join(out)


# ── Khmer → Latin pure-Python fallback ──────────────────────────────────────
# ICU 72 on Debian bookworm ships without Khmer-Latin data (it was added in
# ICU 74 via CLDR 44). Rather than bumping the base image, we fall back to
# a compact character-level romanization table. Linguistically imperfect but
# deterministic and round-trippable, which is all we need for 1:1 alignment.
_KHMER_CHAR_MAP = {
    # Consonants
    "ក": "k", "ខ": "kh", "គ": "k", "ឃ": "kh", "ង": "ng",
    "ច": "ch", "ឆ": "chh", "ជ": "ch", "ឈ": "chh", "ញ": "nh",
    "ដ": "d", "ឋ": "th", "ឌ": "d", "ឍ": "th", "ណ": "n",
    "ត": "t", "ថ": "th", "ទ": "t", "ធ": "th", "ន": "n",
    "ប": "b", "ផ": "ph", "ព": "p", "ភ": "ph", "ម": "m",
    "យ": "y", "រ": "r", "ល": "l", "វ": "v",
    "ស": "s", "ហ": "h", "ឡ": "l", "អ": "a",
    # Independent vowels
    "ឥ": "i", "ឦ": "i", "ឧ": "u", "ឨ": "u", "ឩ": "u", "ឪ": "uv",
    "ឫ": "ru", "ឬ": "ru", "ឭ": "lu", "ឮ": "lu",
    "ឯ": "e", "ឰ": "ai", "ឱ": "o", "ឲ": "o", "ឳ": "au",
    # Dependent vowel signs
    "ា": "a", "ិ": "i", "ី": "i", "ឹ": "oe", "ឺ": "oe",
    "ុ": "u", "ូ": "u", "ួ": "uo", "ើ": "oe", "ឿ": "ueu",
    "ៀ": "ie", "េ": "e", "ែ": "ae", "ៃ": "ai",
    "ោ": "o", "ៅ": "au",
    # Diacritics
    "ំ": "m", "ះ": "h", "ៈ": "",
    "្": "",  # Coeng (subscript marker) — elide
    "៉": "", "៊": "", "់": "", "៌": "", "៍": "",
    "៎": "", "៏": "", "័": "",
    # Digits
    "០": "0", "១": "1", "២": "2", "៣": "3", "៤": "4",
    "៥": "5", "៦": "6", "៧": "7", "៨": "8", "៩": "9",
    # Spaces / punctuation
    "។": ".", "៕": ".", "៖": ":", "ៗ": "",
}


def _khmer_char_fallback(word: str) -> str:
    out = []
    for ch in word:
        if ch in _KHMER_CHAR_MAP:
            out.append(_KHMER_CHAR_MAP[ch])
        elif _KHMER_RANGE.match(ch):
            # Unknown Khmer char — elide rather than emit raw script so the
            # romanization stays ASCII-clean.
            continue
        else:
            out.append(ch)
    return "".join(out)


def _khmer_word_aligned(translation: str) -> Optional[str]:
    """Return romanized Khmer, one token per space-separated word.

    First try PyICU's ``Khmer-Latin`` transliterator. When unavailable
    (e.g. Debian bookworm / ICU 72), fall back to a compact char-level
    map so the output still aligns 1:1 with the translation tokens.
    """
    result = _romanize_icu_per_word(translation, _KHMER_RANGE, "Khmer-Latin")
    if result is not None:
        return result
    if not _KHMER_RANGE.search(translation):
        return None
    out: list[str] = []
    for word in translation.split():
        if _KHMER_RANGE.search(word):
            romanized = _khmer_char_fallback(word).strip()
            out.append(romanized if romanized else word)
        else:
            out.append(_map_punct(word))
    return " ".join(out)


def _burmese_word_aligned(translation: str) -> Optional[str]:
    """Return hyphen-joined ICU Myanmar→Latin romanization, one token per word.

    Uses PyICU's ``Myanmar-Latin`` transliterator (CLDR standard). Each
    Myanmar word from the LLM-emitted space-segmented translation becomes a
    single romanized token with syllables hyphen-joined internally.
    """
    return _romanize_icu_per_word(translation, _MYANMAR_RANGE, "Myanmar-Latin")


# ── Lao → Latin pure-Python fallback ────────────────────────────────────────
# Same rationale as Khmer above: ICU 72 on bookworm lacks the Lao-Latin table.
# BGN/PCGN-inspired char-level map; imperfect phonetics but deterministic.
_LAO_CHAR_MAP = {
    # Consonants
    "ກ": "k", "ຂ": "kh", "ຄ": "kh", "ງ": "ng",
    "ຈ": "ch", "ສ": "s", "ຊ": "x", "ຍ": "ny",
    "ດ": "d", "ຕ": "t", "ຖ": "th", "ທ": "th", "ນ": "n",
    "ບ": "b", "ປ": "p", "ຜ": "ph", "ຝ": "f",
    "ພ": "ph", "ຟ": "f", "ມ": "m",
    "ຢ": "y", "ຣ": "r", "ລ": "l", "ວ": "v", "ຫ": "h",
    "ອ": "o", "ຮ": "h", "ໜ": "n", "ໝ": "m",
    # Vowels
    "ະ": "a", "າ": "a", "ິ": "i", "ີ": "i", "ຶ": "ue",
    "ື": "ue", "ຸ": "u", "ູ": "u",
    "ເ": "e", "ແ": "ae", "ໂ": "o", "ໃ": "ai", "ໄ": "ai",
    "ຽ": "ia", "ໍ": "o",
    # Final and tone marks
    "ຳ": "am", "່": "", "້": "", "໊": "", "໋": "", "໌": "",
    # Digits
    "໐": "0", "໑": "1", "໒": "2", "໓": "3", "໔": "4",
    "໕": "5", "໖": "6", "໗": "7", "໘": "8", "໙": "9",
}


def _lao_char_fallback(word: str) -> str:
    out = []
    for ch in word:
        if ch in _LAO_CHAR_MAP:
            out.append(_LAO_CHAR_MAP[ch])
        elif _LAO_RANGE.match(ch):
            continue
        else:
            out.append(ch)
    return "".join(out)


def _lao_word_aligned(translation: str) -> Optional[str]:
    """Return romanized Lao, one token per space-separated word.

    Tries PyICU's ``Lao-Latin`` first; falls back to a char-level map when
    ICU is too old to bundle that transliterator (Debian 12 ships ICU 72).
    """
    result = _romanize_icu_per_word(translation, _LAO_RANGE, "Lao-Latin")
    if result is not None:
        return result
    if not _LAO_RANGE.search(translation):
        return None
    out: list[str] = []
    for word in translation.split():
        if _LAO_RANGE.search(word):
            romanized = _lao_char_fallback(word).strip()
            out.append(romanized if romanized else word)
        else:
            out.append(_map_punct(word))
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
    if key == "khmer":
        return _khmer_word_aligned(translation)
    if key == "burmese":
        return _burmese_word_aligned(translation)
    if key == "lao":
        return _lao_word_aligned(translation)
    return None


__all__ = ["generate_word_aligned_transliteration"]
