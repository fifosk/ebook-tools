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

    return "\n".join(instructions)


def make_transliteration_prompt(target_language: str) -> str:
    """Prompt for requesting a transliteration from the model."""

    return (
        f"Transliterate the following sentence in {target_language} for English pronunciation.\n"
        "Provide ONLY the transliteration on a SINGLE LINE without ANY additional text or commentary."
    )


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
