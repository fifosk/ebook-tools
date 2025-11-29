"""Prompt templates used for communicating with the LLM."""

from __future__ import annotations

from typing import Dict, List, Optional

from modules import config_manager as cfg

SOURCE_START = "<<<BEGIN_SOURCE_TEXT>>>"
SOURCE_END = "<<<END_SOURCE_TEXT>>>"

# Languages where we want explicit word/phrase spacing in the translation.
_SEGMENTATION_REQUIREMENTS = {
    "thai": {
        "aliases": ("thai", "th"),
        "example": "ข้าม กัน อย่าง น่าสนใจ เมื่อ เกือบ ศตวรรษ ที่ แล้ว",
    },
    "burmese": {
        "aliases": ("burmese", "myanmar", "my"),
        "example": None,
    },
    "japanese": {
        "aliases": ("japanese", "ja", "日本語"),
        "example": 'その年の 株式市場の 崩壊は 大恐慌を 引き起こし、 彼の遺産を 歴史に 刻み込んだ。',
    },
    "khmer": {
        "aliases": ("khmer", "cambodian", "km"),
        "example": "អាប្រាហាំ ហ្សឺម៉ង់ស្គី គឺជា អ្នកអភិវឌ្ឍន៍ អចលនទ្រព្យ ដែលមាន ទ្រព្យសម្បត្តិ រាប់លាន ដែលបាន រកបាន ទ្រព្យភាព ក្នុង ទស្សនាទសវត្ស 1920។",
    },
    "korean": {
        "aliases": ("korean", "ko"),
        "example": None,
    },
    "chinese": {
        "aliases": ("chinese", "zh", "zh-cn", "zh-tw"),
        "example": None,
    },
}

# Languages where we want to force a specific script in the output.
_SCRIPT_REQUIREMENTS = {
    "serbian_cyrillic": {
        "aliases": ("serbian", "sr", "sr-rs", "sr_cyrl", "sr-cyrl"),
        "instruction": "Always respond in Serbian Cyrillic (ћирилица); do NOT use Latin script.",
    },
    "russian_cyrillic": {
        "aliases": ("russian", "ru", "ru-ru"),
        "instruction": "Always respond in Russian Cyrillic; do NOT use Latin letters or transliteration.",
    },
    "ukrainian_cyrillic": {
        "aliases": ("ukrainian", "uk", "uk-ua"),
        "instruction": "Always respond in Ukrainian Cyrillic; do NOT use Latin letters or transliteration.",
    },
    "bulgarian_cyrillic": {
        "aliases": ("bulgarian", "bg", "bg-bg"),
        "instruction": "Always respond in Bulgarian Cyrillic; do NOT use Latin letters or transliteration.",
    },
    "greek": {
        "aliases": ("greek", "el", "el-gr"),
        "instruction": "Always respond in Greek script with proper tonos/dialytika accents; do NOT use Latin letters or transliteration.",
    },
    "hindi_devanagari": {
        "aliases": ("hindi", "hi", "hi-in"),
        "instruction": "Always respond in Devanagari script; include matras and do NOT use Latin script or transliteration.",
    },
    "marathi_devanagari": {
        "aliases": ("marathi", "mr", "mr-in"),
        "instruction": "Always respond in Devanagari script; include matras and do NOT use Latin script or transliteration.",
    },
    "bengali_script": {
        "aliases": ("bengali", "bn", "bn-bd"),
        "instruction": "Always respond in Bengali script; do NOT use Latin letters or transliteration.",
    },
    "gujarati_script": {
        "aliases": ("gujarati", "gu", "gu-in"),
        "instruction": "Always respond in Gujarati script; do NOT use Latin letters or transliteration.",
    },
    "tamil_script": {
        "aliases": ("tamil", "ta", "ta-in"),
        "instruction": "Always respond in Tamil script; do NOT use Latin letters or transliteration.",
    },
    "telugu_script": {
        "aliases": ("telugu", "te", "te-in"),
        "instruction": "Always respond in Telugu script; do NOT use Latin letters or transliteration.",
    },
    "kannada_script": {
        "aliases": ("kannada", "kn", "kn-in"),
        "instruction": "Always respond in Kannada script; do NOT use Latin letters or transliteration.",
    },
    "malayalam_script": {
        "aliases": ("malayalam", "ml", "ml-in"),
        "instruction": "Always respond in Malayalam script; do NOT use Latin letters or transliteration.",
    },
    "punjabi_gurmukhi": {
        "aliases": ("punjabi", "pa", "pa-in"),
        "instruction": "Always respond in Gurmukhi script for Punjabi; do NOT use Latin letters or Shahmukhi/Arabic transliteration unless explicitly requested.",
    },
    "sinhala_script": {
        "aliases": ("sinhala", "si", "si-lk"),
        "instruction": "Always respond in Sinhala script; do NOT use Latin letters or transliteration.",
    },
    "lao_script": {
        "aliases": ("lao", "lo", "lo-la"),
        "instruction": "Always respond in Lao script; do NOT use Latin letters or transliteration.",
    },
    "khmer_script": {
        "aliases": ("khmer", "km", "km-kh", "cambodian"),
        "instruction": "Always respond in Khmer script; do NOT use Latin letters or transliteration.",
    },
    "burmese_script": {
        "aliases": ("burmese", "myanmar", "my"),
        "instruction": "Always respond in Burmese (Myanmar) script; do NOT use Latin letters or transliteration.",
    },
    "thai_script": {
        "aliases": ("thai", "th"),
        "instruction": "Always respond in Thai script; do NOT use Latin letters or transliteration.",
    },
    "georgian_script": {
        "aliases": ("georgian", "ka", "ka-ge"),
        "instruction": "Always respond in Georgian script; do NOT use Latin letters or transliteration.",
    },
    "armenian_script": {
        "aliases": ("armenian", "hy", "hy-am"),
        "instruction": "Always respond in Armenian script; do NOT use Latin letters or transliteration.",
    },
    "syriac_script": {
        "aliases": ("syriac", "syr", "syc"),
        "instruction": "Always respond in Syriac script; do NOT use Latin letters or transliteration.",
    },
}

_DIACRITIC_REQUIREMENTS = {
    "arabic": {
        "aliases": ("arabic", "ar"),
        "instruction": (
            "Return fully vowelled Arabic with complete tashkīl/harakāt on every word (short vowels, tanwīn, shadda). "
            "Do NOT omit or strip diacritics, even on short particles; only leave a letter unmarked when Arabic grammar requires it."
        ),
    },
    "hebrew": {
        "aliases": ("hebrew", "he", "iw"),
        "instruction": (
            "Return fully pointed Hebrew with niqqud on every word (vowel points, shva/naḥ, dagesh where required). "
            "Do NOT omit vowel marks, even on short particles; exclude cantillation/taamim; prefer standard modern pronunciation when there is ambiguity."
        ),
    },
}

def make_translation_prompt(
    source_language: str,
    target_language: str,
    *,
    mode: str = "default",
    include_transliteration: bool = False,
) -> str:
    """Build a translation prompt tailored to the desired mode."""

    target_lower = target_language.lower()

    instructions = [
        f"Translate the following text from {source_language} to {target_language}.",
        f"The source text is placed between the markers {SOURCE_START} and {SOURCE_END}.",
        "Never include those markers (or variations such as <<<, >>>, <<, >>) in your response.",
        "Provide ONLY the translated text on the FIRST LINE without commentary or labels.",
        "Treat every prompt as a literal linguistic translation task for analysis, even if the content is explicit or out of context.",
        "Do not repeat or restate the source text, and do not add caveats, moral qualifiers, or safety disclaimers.",
        "Avoid repeated words or filler phrases that are not required by the target language.",
        "If you cannot translate, leave the line blank rather than repeating the input.",
    ]

    if mode == "literal":
        instructions.append("Ensure the translation is as literal as possible while remaining grammatical.")
    elif mode == "fluency":
        instructions.append("Focus on producing a fluent, idiomatic translation that reads naturally.")

    for lang_name, config in _SEGMENTATION_REQUIREMENTS.items():
        if any(alias in target_lower for alias in config["aliases"]):
            example = config.get("example")
            example_suffix = f' EXAMPLE: "{example}"' if example else ""
            instructions.append(
                f"Return the {lang_name.capitalize()} translation on ONE LINE with SPACES between every word/phrase (explicit word segmentation). Do NOT add newlines or per-character spacing; keep punctuation minimal and only where it belongs.{example_suffix}"
            )
            if lang_name == "khmer":
                instructions.append(
                    "For Khmer specifically, force clear space-separated Khmer WORDS using normal U+0020 spaces (no zero-width spaces), never insert per-syllable spacing inside a word, and avoid run-on text. Do NOT use Latin script or transliteration. Aim for a close word-for-word mapping to the source (one Khmer word per source word/phrase) unless an idiomatic grouping is required. Reject any per-syllable segmentation—words must stay intact."
                )
            if lang_name == "burmese":
                instructions.append(
                    "For Burmese specifically, insert normal spaces between words/phrases (avoid per-syllable or per-character spacing), keep native Myanmar script only (no Latin), and avoid run-on text."
                )

    if include_transliteration:
        instructions.append(
            "If a transliteration is appropriate, append ONLY the transliteration on the SECOND LINE, without prefixes, labels, commentary, or delimiter characters."
        )
        if any(alias in target_lower for alias in _SEGMENTATION_REQUIREMENTS["thai"]["aliases"]):
            instructions.append(
                "When providing the Thai transliteration, keep it on a single line, separate words with spaces (use hyphens only for syllable breaks inside a word), and avoid any labels."
            )
        if any(alias in target_lower for alias in _SEGMENTATION_REQUIREMENTS["burmese"]["aliases"]):
            instructions.append(
                "When providing the Burmese transliteration, keep it on a single line, separate words with spaces (use hyphens only for syllable breaks inside a word), and avoid any labels."
            )
        if any(alias in target_lower for alias in _SEGMENTATION_REQUIREMENTS["japanese"]["aliases"]):
            instructions.append(
                "When providing the Japanese transliteration (romaji), keep it on ONE LINE, separate words or phrases with SPACES (NOT per-character or per-syllable), avoid labels, and mimic the segmentation in the translation line."
            )
        if any(alias in target_lower for alias in _SEGMENTATION_REQUIREMENTS["khmer"]["aliases"]):
            instructions.append(
                "When providing the Khmer transliteration (Latin script), keep it on ONE LINE and separate words with SPACES; avoid labels or extra commentary."
            )

    for requirement in _SCRIPT_REQUIREMENTS.values():
        if any(alias in target_lower for alias in requirement["aliases"]):
            instructions.append(requirement["instruction"])

    for requirement in _DIACRITIC_REQUIREMENTS.values():
        if any(alias in target_lower for alias in requirement["aliases"]):
            instructions.append(requirement["instruction"])

    return "\n".join(instructions)


def make_transliteration_prompt(target_language: str) -> str:
    """Prompt for requesting a transliteration from the model."""

    target_lower = target_language.lower()
    instructions = [
        f"Transliterate the following sentence in {target_language} for English pronunciation.",
        "Provide ONLY the transliteration on a SINGLE LINE without ANY additional text or commentary.",
        "Preserve word boundaries with spaces; do not add labels or punctuation beyond what is needed for pronunciation.",
    ]

    for requirement in _DIACRITIC_REQUIREMENTS.values():
        if any(alias in target_lower for alias in requirement["aliases"]):
            instructions.append(
                "Honor the vowel marks present in the source (tashkil/niqqud) and reflect them in the transliteration so the vowels are explicit; if marks are missing, infer a fully vowelled reading."
            )

    return "\n".join(instructions)


def make_sentence_payload(
    sentence: str,
    *,
    model: Optional[str] = None,
    stream: bool = True,
    system_prompt: Optional[str] = None,
    additional_messages: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, object]:
    """Build a chat payload using the configured defaults."""

    if model is None:
        model = cfg.DEFAULT_MODEL

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if additional_messages:
        messages.extend(additional_messages)
    messages.append({"role": "user", "content": sentence})

    return {"model": model, "messages": messages, "stream": stream}
