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
import unicodedata
from typing import Optional

# ── Shared tone-diacritic helpers (Thai + Lao) ──────────────────────────────
# Map numeric tone digits 1–5 to combining diacritics. Convention matches
# common Thai textbooks: 1 mid = bare, 2 low = grave, 3 falling = circumflex,
# 4 high = acute, 5 rising = caron. Lao reuses the same marks via its own
# tone-mark → digit mapping so output style is consistent across the two
# Southeast Asian tonal languages.
_TONE_DIACRITIC_BY_DIGIT = {
    "1": "",
    "2": "\u0300",   # combining grave
    "3": "\u0302",   # combining circumflex
    "4": "\u0301",   # combining acute
    "5": "\u030c",   # combining caron
}

# Vowels that can carry a tone diacritic. Includes ASCII vowels plus the
# IPA vowels that surface in tltk_ipa output (ɛ ɤ ɯ ɔ ɐ).
_TONE_BEARING_VOWELS = set("aeiouyAEIOUY\u0250\u025b\u0254\u0264\u026f\u028c")


def _apply_tone_diacritic(syllable: str, combining: str) -> str:
    """Place ``combining`` over the first tone-bearing vowel in ``syllable``.

    Uses NFC after injection so the result is a pre-composed character where
    one exists (ā, à, á, â, ǎ for Latin vowels) and a decomposed base+mark
    pair otherwise (e.g. ɛ̂). No-ops when the syllable has no vowel.
    """
    if not combining or not syllable:
        return syllable
    for i, ch in enumerate(syllable):
        if ch in _TONE_BEARING_VOWELS:
            return unicodedata.normalize(
                "NFC", syllable[: i + 1] + combining + syllable[i + 1 :]
            )
    return syllable


def _strip_and_diacriticize_syllable(syl: str) -> str:
    """Strip trailing tone digit from ``syl`` and apply the matching diacritic.

    ``sa2`` → ``sà``, ``baːn3`` → ``bâːn``, ``di:1`` → ``di:`` (mid tone bare).
    """
    if not syl:
        return syl
    if syl[-1] in _TONE_DIACRITIC_BY_DIGIT:
        digit = syl[-1]
        base = syl[:-1]
        return _apply_tone_diacritic(base, _TONE_DIACRITIC_BY_DIGIT[digit])
    return syl

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
    if lowered in {"vi", "vie", "vietnamese"}:
        return "vietnamese"
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
    if "vietnamese" in lowered:
        return "vietnamese"
    return ""


def _map_punct(token: str) -> str:
    return "".join(_CJK_PUNCT_TO_ASCII.get(ch, ch) for ch in token)


def _chinese_word_aligned(translation: str) -> Optional[str]:
    """Return hyphen-joined pinyin with tone diacritics, one token per word.

    Uses ``pypinyin.pinyin`` with ``Style.TONE`` — Mandarin tones are rendered
    with the standard diacritic convention learners recognise from textbooks
    (nǐ, hǎo, mā, dà). Neutral tone carries no mark. Returns None when
    pypinyin is unavailable or the input has no Chinese characters.
    """
    if not _HAN_RANGE.search(translation):
        return None
    try:
        from pypinyin import pinyin, Style
    except ImportError:
        return None

    out: list[str] = []
    for word in translation.split():
        if _HAN_RANGE.search(word):
            # pinyin() returns a list of candidate-lists; take the first
            # candidate for each syllable. Style.TONE puts the tone diacritic
            # over the appropriate vowel of each syllable (standard pinyin
            # convention, e.g. 你好 → nǐ hǎo).
            raw = pinyin(word, style=Style.TONE, heteronym=False)
            syllables = [
                group[0].strip() for group in raw if group and group[0].strip()
            ]
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
    """Return hyphen-joined tone-numbered romanization per Thai word.

    Uses pythainlp's ``tltk_ipa`` engine which emits each syllable as
    ``syllable + tone-digit`` joined with ``.``, e.g. ``sa2.wat2.di:1``.
    We split on ``.`` to recover syllables, strip the IPA length marker
    ``ː``/``:``, and hyphen-join them so each Thai word maps to exactly
    one romanized token with embedded tone numbers (1–5).

    Falls back to the tone-less ``romanize`` engine if tltk is unavailable.
    Returns None when pythainlp is not installed or the input has no Thai.
    """
    if not _THAI_RANGE.search(translation):
        return None
    try:
        from pythainlp.transliterate import transliterate, romanize
    except ImportError:
        return None

    def _romanize_plain(word: str) -> str:
        """Last-resort romanization: RTGS (no tones) then strip any residue."""
        try:
            plain = (romanize(word) or "").strip().replace(" ", "")
        except Exception:
            plain = ""
        # If even romanize() left Thai characters behind, drop them. Better
        # to ship a short ASCII token than a mixed-script one that will
        # confuse the word-highlighter.
        plain = "".join(c for c in plain if not _THAI_RANGE.match(c))
        return plain

    def _tone_romanize(word: str) -> str:
        try:
            raw = transliterate(word, engine="tltk_ipa") or ""
        except Exception:
            raw = ""
        raw = raw.strip()
        # Guard: tltk_ipa silently returns partial output on compound / rare
        # words (e.g. กระเป๋า → "" or "กระเป๋า" unchanged). When that happens
        # the transliteration line ends up mixing Latin and Thai, which
        # breaks both highlighting and learner readability. Detect any
        # residual Thai script and fall back to the plain RTGS romanizer.
        if not raw or _THAI_RANGE.search(raw):
            plain = _romanize_plain(word)
            return plain if plain else word
        # Normalize the IPA length marker to ASCII so output is greppable.
        raw = raw.replace("ː", ":")
        # tltk emits each syllable as <chars><tone-digit>, '.' separated.
        # Convert the trailing digit into a combining diacritic on the first
        # vowel so readers see Thai tones as ā/à/á/â/ǎ — same diacritic
        # system used for Mandarin pinyin, matching how learner materials
        # frequently present tones.
        syllables = [
            _strip_and_diacriticize_syllable(s.strip().replace(" ", ""))
            for s in raw.split(".")
            if s.strip()
        ]
        result = "-".join(syllables) if syllables else word
        # Safety net in case the pre-tltk Thai slipped past tltk but after
        # our syllable split somehow survived (shouldn't happen, but zero
        # cost to enforce).
        if _THAI_RANGE.search(result):
            plain = _romanize_plain(word)
            return plain if plain else result
        return result

    out: list[str] = []
    for word in translation.split():
        if _THAI_RANGE.search(word):
            out.append(_tone_romanize(word))
        else:
            out.append(_map_punct(word))
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
        # Guard: some ICU transliterators leave the script untouched when
        # they encounter a character outside their table (silently no-op).
        # If the output still contains the source script, treat it as a
        # failure so the caller can fall back (e.g. to a char-level map).
        if script_pattern.search(romanized):
            return None
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


# ── Vietnamese ──────────────────────────────────────────────────────────────
# Vietnamese is already written in the Latin alphabet (quốc ngữ) with its
# tone information carried by combining diacritics. There is nothing to
# "transliterate" — the translation line itself is the learner-readable
# tone-marked form. For a transliteration TRACK we still need 1:1 token
# coverage, so we emit the ASCII-folded form of each Vietnamese word as a
# pronunciation-aid: 'Tôi yêu đọc sách' → 'Toi yeu doc sach'. Learners who
# can't yet read the diacritics can follow along with the ASCII row.
_VI_CHAR_MAP = {"đ": "d", "Đ": "D"}


def _vietnamese_word_aligned(translation: str) -> Optional[str]:
    """Return the ASCII-folded (no-diacritic) Vietnamese, one token per word."""
    if not translation or not translation.strip():
        return None
    # Only engage when the text actually has Vietnamese-style diacritics or
    # characters specific to the language. Avoids hijacking plain English.
    has_vi = any(
        unicodedata.combining(c) or c in _VI_CHAR_MAP for c in translation
    )
    if not has_vi:
        # Fall through to LLM-provided transliteration when the translation
        # happens to be plain ASCII.
        return None
    out: list[str] = []
    for word in translation.split():
        decomposed = unicodedata.normalize("NFD", word)
        folded = "".join(
            _VI_CHAR_MAP.get(c, c)
            for c in decomposed
            if unicodedata.category(c) != "Mn"
        )
        out.append(folded if folded else word)
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
# Tone marks are rendered as combining diacritics placed over the next vowel
# that follows them (same convention we use for Thai, so the two languages
# read consistently). Tone-mark → Thai-tone-number mapping is approximate —
# proper Lao tonology depends on consonant-class × vowel-length × mark —
# but this is good enough for learner-facing output.
_LAO_TONE_MARKS = {
    "\u0ec8": "2",  # ່ mai ek    → low → grave
    "\u0ec9": "3",  # ້ mai tho   → falling → circumflex
    "\u0eca": "5",  # ໊ mai ti    → rising → caron
    "\u0ecb": "4",  # ໋ mai catawa → high → acute
}
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
    # Final and tone marks — tone marks handled separately, ໌ (silent) elided
    "ຳ": "am", "໌": "",
    # Digits
    "໐": "0", "໑": "1", "໒": "2", "໓": "3", "໔": "4",
    "໕": "5", "໖": "6", "໗": "7", "໘": "8", "໙": "9",
}


def _lao_char_fallback(word: str) -> str:
    """Char-level Lao → Latin with tone diacritics injected on vowels.

    Each Lao tone mark encountered stashes a pending combining diacritic;
    the next romanized character that is a tone-bearing vowel absorbs it
    (via NFC composition). If no vowel follows (rare), the pending mark
    is dropped. Result: ``ຂ້ອຍ → khôny``, ``ອ່ານ → àan`` (rather than
    the old ``khony2`` / ``oan1`` digit-suffix form).
    """
    out: list[str] = []
    pending_combining = ""
    for ch in word:
        if ch in _LAO_TONE_MARKS:
            digit = _LAO_TONE_MARKS[ch]
            pending_combining = _TONE_DIACRITIC_BY_DIGIT.get(digit, "")
            continue
        if ch in _LAO_CHAR_MAP:
            mapped = _LAO_CHAR_MAP[ch]
            if pending_combining and mapped:
                # Apply the diacritic to the first tone-bearing vowel within
                # this mapped group; if none, attach to the next group.
                placed = _apply_tone_diacritic(mapped, pending_combining)
                if placed != mapped:
                    pending_combining = ""
                    mapped = placed
            out.append(mapped)
        elif _LAO_RANGE.match(ch):
            continue
        else:
            out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


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
    if key == "vietnamese":
        return _vietnamese_word_aligned(translation)
    return None


__all__ = ["generate_word_aligned_transliteration"]
