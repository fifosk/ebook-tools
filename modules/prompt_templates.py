"""Prompt templates used for communicating with the LLM."""

from __future__ import annotations

from typing import Dict, List, Optional

import regex

from modules import config_manager as cfg
from modules import language_policies
from modules.language_constants import LANGUAGE_CODES

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

_ROMANI_ALIASES = {"romani", "rom", "romany"}
_PASHTO_ALIASES = {"pashto", "ps", "pushto", "pashtu"}
_LANGUAGE_NAME_TO_CODE = {name.casefold(): code for name, code in LANGUAGE_CODES.items()}
_LANGUAGE_CODE_TO_NAME = {code.casefold(): name for name, code in LANGUAGE_CODES.items()}
_LANG_CODE_PATTERN = regex.compile(r"^[a-z]{2,3}(?:[_-][a-z0-9]{2,4})?$", regex.IGNORECASE)
_LANG_CODE_IN_PARENS = regex.compile(r"\(([a-z]{2,3}(?:[_-][a-z0-9]{2,4})?)\)", regex.IGNORECASE)


def _format_language_descriptor(language: str) -> str:
    cleaned = (language or "").strip()
    if not cleaned:
        return cleaned
    if _LANG_CODE_IN_PARENS.search(cleaned):
        return cleaned
    lowered = cleaned.casefold()
    code = _LANGUAGE_NAME_TO_CODE.get(lowered)
    if code:
        return f"{cleaned} ({code})"
    normalized = lowered.replace("_", "-")
    if _LANG_CODE_PATTERN.match(normalized):
        name = _LANGUAGE_CODE_TO_NAME.get(normalized)
        if name is None:
            base = normalized.split("-", 1)[0]
            name = _LANGUAGE_CODE_TO_NAME.get(base)
        if name:
            return f"{name} ({cleaned})"
    return cleaned

def make_translation_prompt(
    source_language: str,
    target_language: str,
    *,
    mode: str = "default",
    include_transliteration: bool = False,
) -> str:
    """Build a translation prompt tailored to the desired mode."""

    target_lower = (target_language or "").lower()
    source_descriptor = _format_language_descriptor(source_language)
    target_descriptor = _format_language_descriptor(target_language)

    instructions = [
        f"Translate the following text from {source_descriptor} to {target_descriptor}.",
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

    instructions.extend(
        language_policies.script_prompt_instructions(
            target_language,
            allow_transliteration=include_transliteration,
        )
    )

    if target_lower in _ROMANI_ALIASES:
        instructions.append(
            "Translate into Romani (ISO 639-2 rom, the Romany language of Roma communities), NOT Romanian. Use authentic Romani vocabulary and grammar and avoid Romanian words unless they are genuine Romani loanwords."
        )
    if target_lower in _PASHTO_ALIASES:
        instructions.append(
            "Translate into Pashto (ISO 639-1 ps), NOT Urdu or Hindi. Use authentic Pashto vocabulary and grammar, written in Pashto’s Arabic-derived script, and avoid Urdu/Hindi calques unless they are genuine Pashto usage."
        )

    for requirement in _DIACRITIC_REQUIREMENTS.values():
        if any(alias in target_lower for alias in requirement["aliases"]):
            instructions.append(requirement["instruction"])

    return "\n".join(instructions)


def make_translation_batch_prompt(
    source_language: str,
    target_language: str,
    *,
    mode: str = "default",
    include_transliteration: bool = False,
) -> str:
    """Build a translation prompt for JSON batch requests."""

    target_lower = (target_language or "").lower()
    source_descriptor = _format_language_descriptor(source_language)
    target_descriptor = _format_language_descriptor(target_language)

    instructions = [
        f"Translate each item from {source_descriptor} to {target_descriptor}.",
        "The input is a JSON object with an `items` array; each item includes an `id` and `text`.",
        "Return ONLY valid JSON with an `items` array of objects.",
        "Never include markdown, code fences, commentary, or labels.",
        "Do not include the source text in the response.",
        "The `translation` value must be a single-line string without line breaks.",
        "If you cannot translate an item, return an empty string for `translation`.",
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
        instructions.append("Each output item MUST include `id`, `translation`, and `transliteration` fields.")
        instructions.append(
            "The `translation` and `transliteration` values must be single-line strings without line breaks."
        )
        instructions.append(
            "Populate the `transliteration` field ONLY when a transliteration is appropriate; otherwise use an empty string."
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
                "When providing the Japanese transliteration (romaji), keep it on ONE LINE, separate words or phrases with SPACES (NOT per-character or per-syllable), avoid labels, and mimic the segmentation in the translation field."
            )
        if any(alias in target_lower for alias in _SEGMENTATION_REQUIREMENTS["khmer"]["aliases"]):
            instructions.append(
                "When providing the Khmer transliteration (Latin script), keep it on ONE LINE and separate words with SPACES; avoid labels or extra commentary."
            )
    else:
        instructions.append("Each output item MUST include `id` and `translation` fields.")
        instructions.append("Do NOT include a `transliteration` field in the response.")

    instructions.extend(
        language_policies.script_prompt_instructions(
            target_language,
            allow_transliteration=include_transliteration,
        )
    )

    if target_lower in _ROMANI_ALIASES:
        instructions.append(
            "Translate into Romani (ISO 639-2 rom, the Romany language of Roma communities), NOT Romanian. Use authentic Romani vocabulary and grammar and avoid Romanian words unless they are genuine Romani loanwords."
        )
    if target_lower in _PASHTO_ALIASES:
        instructions.append(
            "Translate into Pashto (ISO 639-1 ps), NOT Urdu or Hindi. Use authentic Pashto vocabulary and grammar, written in Pashto’s Arabic-derived script, and avoid Urdu/Hindi calques unless they are genuine Pashto usage."
        )

    for requirement in _DIACRITIC_REQUIREMENTS.values():
        if any(alias in target_lower for alias in requirement["aliases"]):
            instructions.append(requirement["instruction"])

    return "\n".join(instructions)


def make_transliteration_prompt(target_language: str) -> str:
    """Prompt for requesting a transliteration from the model."""

    target_lower = (target_language or "").lower()
    target_descriptor = _format_language_descriptor(target_language)
    instructions = [
        f"Transliterate the following sentence in {target_descriptor} for English pronunciation.",
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
