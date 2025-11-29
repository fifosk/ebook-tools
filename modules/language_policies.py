"""Shared language/script policies for prompts and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import regex


SCRIPT_ENFORCEMENT_SUFFIX = (
    "Use only the required target script throughout the response; do NOT mix other writing systems or transliteration. "
    "If unsure, still answer in the target script; never substitute another script."
)


@dataclass(frozen=True)
class ScriptPolicy:
    """Configuration for enforcing a target writing system."""

    key: str
    aliases: tuple[str, ...]
    script_label: str
    script_pattern: regex.Pattern
    instruction: str

    def matches(self, target_language: str) -> bool:
        target_lower = (target_language or "").lower()
        return any(alias in target_lower for alias in self.aliases)


_SCRIPT_POLICIES: tuple[ScriptPolicy, ...] = (
    ScriptPolicy(
        key="serbian_cyrillic",
        aliases=("serbian", "sr", "sr-rs", "sr_cyrl", "sr-cyrl"),
        script_label="Cyrillic",
        script_pattern=regex.compile(r"[\u0400-\u04FF]"),
        instruction="Always respond in Serbian Cyrillic (ћирилица); do NOT use Latin script.",
    ),
    ScriptPolicy(
        key="russian_cyrillic",
        aliases=("russian", "ru", "ru-ru"),
        script_label="Cyrillic",
        script_pattern=regex.compile(r"[\u0400-\u04FF]"),
        instruction="Always respond in Russian Cyrillic; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="ukrainian_cyrillic",
        aliases=("ukrainian", "uk", "uk-ua"),
        script_label="Cyrillic",
        script_pattern=regex.compile(r"[\u0400-\u04FF]"),
        instruction="Always respond in Ukrainian Cyrillic; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="bulgarian_cyrillic",
        aliases=("bulgarian", "bg", "bg-bg"),
        script_label="Cyrillic",
        script_pattern=regex.compile(r"[\u0400-\u04FF]"),
        instruction="Always respond in Bulgarian Cyrillic; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="greek",
        aliases=("greek", "el", "el-gr"),
        script_label="Greek",
        script_pattern=regex.compile(r"[\u0370-\u03FF]"),
        instruction="Always respond in Greek script with proper tonos/dialytika accents; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="hindi_devanagari",
        aliases=("hindi", "hi", "hi-in"),
        script_label="Devanagari",
        script_pattern=regex.compile(r"[\u0900-\u097F]"),
        instruction="Always respond in Devanagari script; include matras and do NOT use Latin script or transliteration.",
    ),
    ScriptPolicy(
        key="marathi_devanagari",
        aliases=("marathi", "mr", "mr-in"),
        script_label="Devanagari",
        script_pattern=regex.compile(r"[\u0900-\u097F]"),
        instruction="Always respond in Devanagari script; include matras and do NOT use Latin script or transliteration.",
    ),
    ScriptPolicy(
        key="sanskrit_devanagari",
        aliases=("sanskrit", "sa"),
        script_label="Devanagari",
        script_pattern=regex.compile(r"[\u0900-\u097F]"),
        instruction="Always respond in Devanagari script; include matras and do NOT use Latin script or transliteration.",
    ),
    ScriptPolicy(
        key="bengali_script",
        aliases=("bengali", "bn", "bn-bd", "bangla"),
        script_label="Bengali",
        script_pattern=regex.compile(r"[\u0980-\u09FF]"),
        instruction="Always respond in Bengali script; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="gujarati_script",
        aliases=("gujarati", "gu", "gu-in"),
        script_label="Gujarati",
        script_pattern=regex.compile(r"[\u0A80-\u0AFF]"),
        instruction="Always respond in Gujarati script; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="tamil_script",
        aliases=("tamil", "ta", "ta-in"),
        script_label="Tamil",
        script_pattern=regex.compile(r"[\u0B80-\u0BFF]"),
        instruction="Always respond in Tamil script; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="telugu_script",
        aliases=("telugu", "te", "te-in"),
        script_label="Telugu",
        script_pattern=regex.compile(r"[\u0C00-\u0C7F]"),
        instruction="Always respond in Telugu script; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="kannada_script",
        aliases=("kannada", "kn", "kn-in"),
        script_label="Kannada",
        script_pattern=regex.compile(r"[\u0C80-\u0CFF]"),
        instruction=(
            "Always respond ONLY in Kannada script (Unicode U+0C80-U+0CFF); do NOT use Latin letters, transliteration, "
            "or any other script (e.g., Tamil, Devanagari, Georgian, Arabic). Use one script consistently across the "
            "entire response; if you cannot respond in Kannada script, return an empty string."
        ),
    ),
    ScriptPolicy(
        key="malayalam_script",
        aliases=("malayalam", "ml", "ml-in"),
        script_label="Malayalam",
        script_pattern=regex.compile(r"[\u0D00-\u0D7F]"),
        instruction="Always respond in Malayalam script; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="punjabi_gurmukhi",
        aliases=("punjabi", "pa", "pa-in"),
        script_label="Gurmukhi",
        script_pattern=regex.compile(r"[\u0A00-\u0A7F]"),
        instruction="Always respond in Gurmukhi script for Punjabi; do NOT use Latin letters or Shahmukhi/Arabic transliteration unless explicitly requested.",
    ),
    ScriptPolicy(
        key="sinhala_script",
        aliases=("sinhala", "si", "si-lk"),
        script_label="Sinhala",
        script_pattern=regex.compile(r"[\u0D80-\u0DFF]"),
        instruction="Always respond in Sinhala script; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="lao_script",
        aliases=("lao", "lo", "lo-la"),
        script_label="Lao",
        script_pattern=regex.compile(r"[\u0E80-\u0EFF]"),
        instruction="Always respond in Lao script; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="khmer_script",
        aliases=("khmer", "km", "km-kh", "cambodian"),
        script_label="Khmer",
        script_pattern=regex.compile(r"[\u1780-\u17FF]"),
        instruction="Always respond in Khmer script; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="burmese_script",
        aliases=("burmese", "myanmar", "my"),
        script_label="Myanmar",
        script_pattern=regex.compile(r"[\u1000-\u109F]"),
        instruction="Always respond in Burmese (Myanmar) script; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="thai_script",
        aliases=("thai", "th"),
        script_label="Thai",
        script_pattern=regex.compile(r"[\u0E00-\u0E7F]"),
        instruction="Always respond in Thai script; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="georgian_script",
        aliases=("georgian", "ka", "ka-ge"),
        script_label="Georgian",
        script_pattern=regex.compile(r"[\u10A0-\u10FF]"),
        instruction="Always respond in Georgian script; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="armenian_script",
        aliases=("armenian", "hy", "hy-am"),
        script_label="Armenian",
        script_pattern=regex.compile(r"[\u0530-\u058F]"),
        instruction="Always respond in Armenian script; do NOT use Latin letters or transliteration.",
    ),
    ScriptPolicy(
        key="syriac_script",
        aliases=("syriac", "syr", "syc"),
        script_label="Syriac",
        script_pattern=regex.compile(r"[\u0700-\u074F]"),
        instruction="Always respond in Syriac script; do NOT use Latin letters or transliteration.",
    ),
)


SCRIPT_BLOCKS: Dict[str, regex.Pattern] = {
    "Devanagari": regex.compile(r"[\u0900-\u097F]"),
    "Bengali": regex.compile(r"[\u0980-\u09FF]"),
    "Gurmukhi": regex.compile(r"[\u0A00-\u0A7F]"),
    "Gujarati": regex.compile(r"[\u0A80-\u0AFF]"),
    "Oriya": regex.compile(r"[\u0B00-\u0B7F]"),
    "Tamil": regex.compile(r"[\u0B80-\u0BFF]"),
    "Telugu": regex.compile(r"[\u0C00-\u0C7F]"),
    "Kannada": regex.compile(r"[\u0C80-\u0CFF]"),
    "Malayalam": regex.compile(r"[\u0D00-\u0D7F]"),
    "Sinhala": regex.compile(r"[\u0D80-\u0DFF]"),
    "Thai": regex.compile(r"[\u0E00-\u0E7F]"),
    "Lao": regex.compile(r"[\u0E80-\u0EFF]"),
    "Tibetan": regex.compile(r"[\u0F00-\u0FFF]"),
    "Myanmar": regex.compile(r"[\u1000-\u109F]"),
    "Georgian": regex.compile(r"[\u10A0-\u10FF]"),
    "Arabic": regex.compile(r"[\u0600-\u06FF]"),
    "Hebrew": regex.compile(r"[\u0590-\u05FF]"),
    "Cyrillic": regex.compile(r"[\u0400-\u04FF]"),
    "Greek": regex.compile(r"[\u0370-\u03FF]"),
    "Armenian": regex.compile(r"[\u0530-\u058F]"),
    "Syriac": regex.compile(r"[\u0700-\u074F]"),
    "Han": regex.compile(r"\p{Han}"),
    "Hangul": regex.compile(r"[\uAC00-\uD7A3\u1100-\u11FF]"),
    "Hiragana": regex.compile(r"[\u3040-\u309F]"),
    "Katakana": regex.compile(r"[\u30A0-\u30FF]"),
}


_EXTRA_NON_LATIN_HINTS: Set[str] = {
    "arabic",
    "ar",
    "hebrew",
    "he",
    "iw",
    "chinese",
    "zh",
    "zh-cn",
    "zh-tw",
    "japanese",
    "ja",
    "korean",
    "ko",
    "cyrillic",
    "urdu",
    "ur",
    "myanmar",
    "burmese",
    "khmer",
    "km",
    "cambodian",
    "thai",
    "th",
    "lao",
    "lo",
    "georgian",
    "ka",
    "armenian",
    "hy",
    "syriac",
    "syr",
    "sinhala",
    "si",
}


def script_policy_for(target_language: str) -> Optional[ScriptPolicy]:
    """Return the script policy associated with the target language, if any."""

    for policy in _SCRIPT_POLICIES:
        if policy.matches(target_language):
            return policy
    return None


def script_prompt_instructions(target_language: str) -> List[str]:
    """Return the prompt lines needed to enforce a target script."""

    policy = script_policy_for(target_language)
    if not policy:
        return []
    return [policy.instruction, SCRIPT_ENFORCEMENT_SUFFIX]


def script_counts(value: str) -> Dict[str, int]:
    """Return counts of matched characters per known script block."""

    counts: Dict[str, int] = {}
    for label, pattern in SCRIPT_BLOCKS.items():
        matches = pattern.findall(value)
        if matches:
            counts[label] = len(matches)
    return counts


def _build_non_latin_hint_set() -> Set[str]:
    hints: Set[str] = set()
    for policy in _SCRIPT_POLICIES:
        hints.update(alias.lower() for alias in policy.aliases)
    hints.update(_EXTRA_NON_LATIN_HINTS)
    return hints


NON_LATIN_LANGUAGE_HINTS: Set[str] = _build_non_latin_hint_set()


def is_non_latin_language_hint(target_language: str) -> bool:
    """Return True when the target language normally expects non-Latin script."""

    target_lower = (target_language or "").lower()
    return any(alias in target_lower for alias in NON_LATIN_LANGUAGE_HINTS)


__all__ = [
    "NON_LATIN_LANGUAGE_HINTS",
    "SCRIPT_BLOCKS",
    "SCRIPT_ENFORCEMENT_SUFFIX",
    "ScriptPolicy",
    "is_non_latin_language_hint",
    "script_counts",
    "script_policy_for",
    "script_prompt_instructions",
]
