"""Prompt templates used for communicating with the LLM."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import regex

from modules import config_manager as cfg
from modules import language_policies
from modules.language_constants import LANGUAGE_CODES

SOURCE_START = "<<<BEGIN_SOURCE_TEXT>>>"
SOURCE_END = "<<<END_SOURCE_TEXT>>>"

# Languages where we want explicit word/phrase spacing in the translation.
# Each config includes:
# - aliases: language identifiers
# - example: example with proper spacing
# - translit_example: matching transliteration example (for token alignment)
_SEGMENTATION_REQUIREMENTS = {
    "thai": {
        "aliases": ("thai", "th"),
        "example": "ข้าม กัน อย่าง น่าสนใจ เมื่อ เกือบ ศตวรรษ ที่ แล้ว",
        "translit_example": "kham kan yang na-son-jai muea kuap sat-ta-wat thi laeo",
    },
    "burmese": {
        "aliases": ("burmese", "myanmar", "my"),
        "example": "ကျော် ခဲ့ စိတ်ဝင်စား နီးပါး ရာစုနှစ် ဖြစ် ခဲ့",
        "translit_example": "kyaw khe seit-win-sa ni-pa ya-su-hnit phyit khe",
    },
    "japanese": {
        "aliases": ("japanese", "ja", "日本語"),
        "example": "その年の 株式市場の 崩壊は 大恐慌を 引き起こし 彼の遺産を 歴史に 刻み込んだ",
        "translit_example": "sono-toshi-no kabushiki-shijou-no houkai-wa daikyoukou-wo hikiokooshi kare-no-isan-wo rekishi-ni kizamikonda",
    },
    "khmer": {
        "aliases": ("khmer", "cambodian", "km"),
        "example": "អាប្រាហាំ ហ្សឺម៉ង់ស្គី គឺជា អ្នកអភិវឌ្ឍន៍ អចលនទ្រព្យ ដែលមាន ទ្រព្យសម្បត្តិ រាប់លាន",
        "translit_example": "abraham zermansky kuochea nak-a-phi-vat achal-na-trop dael-mean trop-som-bat reab-lean",
    },
    "korean": {
        "aliases": ("korean", "ko"),
        "example": "그 해의 주식시장 붕괴는 대공황을 일으켜 그의 유산을 역사에 새겼다",
        "translit_example": "geu hae-ui jusik-sijang bung-goe-neun daegonghwang-eul il-eukyeo geu-ui yusan-eul yeoksa-e saegyeotda",
    },
    "chinese": {
        "aliases": ("chinese", "zh", "zh-cn", "zh-tw"),
        "example": "罗谢 带领 科勒 通过 无障碍 坡道",
        "translit_example": "luo-xie dai-ling ke-le tong-guo wu-zhang-ai po-dao",
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
_TRANSLATEGEMMA_MODEL_HINTS = ("translategemma", "translate-gemma", "translate_gemma")
_TRANSLATEGEMMA_LANG_CODE_PATTERN = regex.compile(r"^[a-z]{2}(?:[_-][a-z]{2})?$", regex.IGNORECASE)
_LANGUAGE_ALIAS_TOKEN_PATTERN = regex.compile(r"[a-z0-9]+")
_LANGUAGE_ALIAS_SAFE_PATTERN = regex.compile(r"^[a-z0-9_-]+$")


def _language_alias_tokens(value: Optional[str]) -> set[str]:
    if not value:
        return set()
    return set(_LANGUAGE_ALIAS_TOKEN_PATTERN.findall(value.lower()))


def _language_matches_alias(
    target_lower: str,
    target_tokens: set[str],
    alias: str,
) -> bool:
    alias_lower = (alias or "").lower()
    if not alias_lower:
        return False
    if _LANGUAGE_ALIAS_SAFE_PATTERN.match(alias_lower):
        if alias_lower in target_tokens:
            return True
        if "-" in alias_lower or "_" in alias_lower:
            alias_tokens = _LANGUAGE_ALIAS_TOKEN_PATTERN.findall(alias_lower)
            return bool(alias_tokens) and all(token in target_tokens for token in alias_tokens)
        return False
    return alias_lower in target_lower


def _language_matches_any(
    target_lower: str,
    target_tokens: set[str],
    aliases: Iterable[str],
) -> bool:
    return any(
        _language_matches_alias(target_lower, target_tokens, alias) for alias in aliases
    )


def is_translategemma_model(model: Optional[str]) -> bool:
    if not isinstance(model, str):
        return False
    normalized = model.strip().lower()
    if not normalized:
        return False
    return any(hint in normalized for hint in _TRANSLATEGEMMA_MODEL_HINTS)


def resolve_translategemma_language_code(language: Optional[str]) -> Optional[str]:
    if not isinstance(language, str):
        return None
    cleaned = language.strip()
    if not cleaned:
        return None
    match = _LANG_CODE_IN_PARENS.search(cleaned)
    candidate = match.group(1) if match else cleaned
    normalized = candidate.strip().replace("_", "-")
    if not normalized:
        return None
    if not _LANG_CODE_PATTERN.match(normalized):
        mapped = _LANGUAGE_NAME_TO_CODE.get(normalized.casefold())
        if not mapped:
            return None
        normalized = mapped.replace("_", "-")
    if not _TRANSLATEGEMMA_LANG_CODE_PATTERN.match(normalized):
        return None
    base, sep, region = normalized.partition("-")
    if not region:
        return base.lower()
    return f"{base.lower()}-{region.upper()}"


def _resolve_language_code_for_prompt(language: Optional[str]) -> Optional[str]:
    if not isinstance(language, str):
        return None
    cleaned = language.strip()
    if not cleaned:
        return None
    match = _LANG_CODE_IN_PARENS.search(cleaned)
    candidate = match.group(1) if match else cleaned
    normalized = candidate.strip().replace("_", "-")
    if not normalized:
        return None
    if not _LANG_CODE_PATTERN.match(normalized):
        mapped = _LANGUAGE_NAME_TO_CODE.get(normalized.casefold())
        if not mapped:
            return None
        normalized = mapped.replace("_", "-")
    base, _sep, region = normalized.partition("-")
    if not region:
        return base.lower()
    return f"{base.lower()}-{region.upper()}"


def resolve_translategemma_language_name(
    language: Optional[str],
    code: Optional[str],
) -> str:
    if isinstance(language, str):
        cleaned = language.strip()
        if cleaned:
            normalized = cleaned.replace("_", "-")
            if not _LANG_CODE_PATTERN.match(normalized):
                return cleaned
    if code:
        normalized_code = code.replace("_", "-").lower()
        name = _LANGUAGE_CODE_TO_NAME.get(normalized_code)
        if name is None and "-" in normalized_code:
            base = normalized_code.split("-", 1)[0]
            name = _LANGUAGE_CODE_TO_NAME.get(base)
        if name:
            return name
    if isinstance(language, str) and language.strip():
        return language.strip()
    return code or "Unknown"


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
    target_tokens = _language_alias_tokens(target_language)
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
        if _language_matches_any(target_lower, target_tokens, config["aliases"]):
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
        if language_policies.is_non_latin_language_hint(target_language):
            instructions.append(
                "Append a transliteration on the SECOND LINE for EVERY response; do NOT leave it blank unless the source text is empty."
            )
        else:
            instructions.append(
                "If a transliteration is appropriate, append ONLY the transliteration on the SECOND LINE, without prefixes, labels, commentary, or delimiter characters."
            )

        # Add critical token alignment instruction for CJK and spaceless languages
        for lang_name, config in _SEGMENTATION_REQUIREMENTS.items():
            if _language_matches_any(target_lower, target_tokens, config["aliases"]):
                example = config.get("example", "")
                translit_example = config.get("translit_example", "")
                if example and translit_example:
                    instructions.append(
                        f"CRITICAL: The translation and transliteration MUST have the SAME number of space-separated tokens for synchronized word highlighting. "
                        f"Each space-separated word/phrase in the translation must correspond exactly to one space-separated romanization in the transliteration. "
                        f'EXAMPLE alignment:\n  Translation: "{example}"\n  Transliteration: "{translit_example}"'
                    )
                else:
                    instructions.append(
                        "CRITICAL: The translation and transliteration MUST have the SAME number of space-separated tokens. "
                        "Each space-separated word/phrase in the translation must correspond exactly to one space-separated romanization in the transliteration."
                    )
                break

        if _language_matches_any(
            target_lower,
            target_tokens,
            _SEGMENTATION_REQUIREMENTS["thai"]["aliases"],
        ):
            instructions.append(
                "When providing the Thai transliteration, keep it on a single line, separate words with spaces (use hyphens only for syllable breaks inside a word), and avoid any labels."
            )
        if _language_matches_any(
            target_lower,
            target_tokens,
            _SEGMENTATION_REQUIREMENTS["burmese"]["aliases"],
        ):
            instructions.append(
                "When providing the Burmese transliteration, keep it on a single line, separate words with spaces (use hyphens only for syllable breaks inside a word), and avoid any labels."
            )
        if _language_matches_any(
            target_lower,
            target_tokens,
            _SEGMENTATION_REQUIREMENTS["japanese"]["aliases"],
        ):
            instructions.append(
                "When providing the Japanese transliteration (romaji), keep it on ONE LINE, separate words or phrases with SPACES (NOT per-character or per-syllable), avoid labels, and MATCH the segmentation in the translation line exactly."
            )
        if _language_matches_any(
            target_lower,
            target_tokens,
            _SEGMENTATION_REQUIREMENTS["khmer"]["aliases"],
        ):
            instructions.append(
                "When providing the Khmer transliteration (Latin script), keep it on ONE LINE and separate words with SPACES; avoid labels or extra commentary."
            )
        if _language_matches_any(
            target_lower,
            target_tokens,
            _SEGMENTATION_REQUIREMENTS["chinese"]["aliases"],
        ):
            instructions.append(
                "PINYIN FORMATTING: Join ALL syllables of each Chinese word with HYPHENS, then separate different words with SPACES. "
                "The pinyin token count MUST match the Chinese word count. "
                "WRONG: 罗谢 带领 → luo xie dai ling (4 tokens). "
                "CORRECT: 罗谢 带领 → luo-xie dai-ling (2 tokens)."
            )
        if _language_matches_any(
            target_lower,
            target_tokens,
            _SEGMENTATION_REQUIREMENTS["korean"]["aliases"],
        ):
            instructions.append(
                "ROMANIZATION: Join ALL syllables of each Korean word with HYPHENS, then separate different words with SPACES. "
                "The romanization token count MUST match the Korean word count. "
                "WRONG: 안녕 하세요 → an nyeong ha se yo (5 tokens). "
                "CORRECT: 안녕 하세요 → an-nyeong ha-se-yo (2 tokens)."
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
        if _language_matches_any(target_lower, target_tokens, requirement["aliases"]):
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
    target_tokens = _language_alias_tokens(target_language)
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
        "CRITICAL: Each input sentence MUST produce EXACTLY ONE translation. "
        "Never combine multiple sentences into one translation. "
        "Never split one sentence into multiple translations. "
        "Preserve the 1:1 correspondence between input and output items.",
    ]

    if mode == "literal":
        instructions.append("Ensure the translation is as literal as possible while remaining grammatical.")
    elif mode == "fluency":
        instructions.append("Focus on producing a fluent, idiomatic translation that reads naturally.")

    for lang_name, config in _SEGMENTATION_REQUIREMENTS.items():
        if _language_matches_any(target_lower, target_tokens, config["aliases"]):
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
        if language_policies.is_non_latin_language_hint(target_language):
            instructions.append(
                "Populate the `transliteration` field for EVERY item (Latin script), leaving it blank only when the source text is empty."
            )
        else:
            instructions.append(
                "Populate the `transliteration` field ONLY when a transliteration is appropriate; otherwise use an empty string."
            )

        # Add critical token alignment instruction for CJK and spaceless languages
        for lang_name, config in _SEGMENTATION_REQUIREMENTS.items():
            if _language_matches_any(target_lower, target_tokens, config["aliases"]):
                example = config.get("example", "")
                translit_example = config.get("translit_example", "")
                if example and translit_example:
                    instructions.append(
                        f"CRITICAL: The `translation` and `transliteration` fields MUST have the SAME number of space-separated tokens for synchronized word highlighting. "
                        f"Each space-separated word/phrase in translation must correspond exactly to one space-separated romanization in transliteration. "
                        f'EXAMPLE alignment:\n  translation: "{example}"\n  transliteration: "{translit_example}"'
                    )
                else:
                    instructions.append(
                        "CRITICAL: The `translation` and `transliteration` fields MUST have the SAME number of space-separated tokens. "
                        "Each space-separated word/phrase in translation must correspond exactly to one space-separated romanization in transliteration."
                    )
                break

        if _language_matches_any(
            target_lower,
            target_tokens,
            _SEGMENTATION_REQUIREMENTS["thai"]["aliases"],
        ):
            instructions.append(
                "When providing the Thai transliteration, keep it on a single line, separate words with spaces (use hyphens only for syllable breaks inside a word), and avoid any labels."
            )
        if _language_matches_any(
            target_lower,
            target_tokens,
            _SEGMENTATION_REQUIREMENTS["burmese"]["aliases"],
        ):
            instructions.append(
                "When providing the Burmese transliteration, keep it on a single line, separate words with spaces (use hyphens only for syllable breaks inside a word), and avoid any labels."
            )
        if _language_matches_any(
            target_lower,
            target_tokens,
            _SEGMENTATION_REQUIREMENTS["japanese"]["aliases"],
        ):
            instructions.append(
                "When providing the Japanese transliteration (romaji), keep it on ONE LINE, separate words or phrases with SPACES (NOT per-character or per-syllable), avoid labels, and MATCH the segmentation in the translation field exactly."
            )
        if _language_matches_any(
            target_lower,
            target_tokens,
            _SEGMENTATION_REQUIREMENTS["khmer"]["aliases"],
        ):
            instructions.append(
                "When providing the Khmer transliteration (Latin script), keep it on ONE LINE and separate words with SPACES; avoid labels or extra commentary."
            )
        if _language_matches_any(
            target_lower,
            target_tokens,
            _SEGMENTATION_REQUIREMENTS["chinese"]["aliases"],
        ):
            instructions.append(
                "PINYIN FORMATTING: Join ALL syllables of each Chinese word with HYPHENS, then separate different words with SPACES. "
                "The pinyin token count MUST match the Chinese word count. "
                "WRONG: 罗谢 带领 → luo xie dai ling (4 tokens). "
                "CORRECT: 罗谢 带领 → luo-xie dai-ling (2 tokens)."
            )
        if _language_matches_any(
            target_lower,
            target_tokens,
            _SEGMENTATION_REQUIREMENTS["korean"]["aliases"],
        ):
            instructions.append(
                "ROMANIZATION: Join ALL syllables of each Korean word with HYPHENS, then separate different words with SPACES. "
                "The romanization token count MUST match the Korean word count. "
                "WRONG: 안녕 하세요 → an nyeong ha se yo (5 tokens). "
                "CORRECT: 안녕 하세요 → an-nyeong ha-se-yo (2 tokens)."
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
        if _language_matches_any(target_lower, target_tokens, requirement["aliases"]):
            instructions.append(requirement["instruction"])

    return "\n".join(instructions)


def translation_supports_json_batch(model: Optional[str]) -> bool:
    return not is_translategemma_model(model)


def transliteration_supports_json_batch(model: Optional[str]) -> bool:
    return not is_translategemma_model(model)


def make_translation_payload(
    sentence: str,
    source_language: str,
    target_language: str,
    *,
    model: Optional[str] = None,
    stream: bool = True,
    include_transliteration: bool = False,
    llm_source: Optional[str] = None,
) -> tuple[Dict[str, object], Optional[str], str]:
    if is_translategemma_model(model) and (llm_source or "").strip().lower() == "lmstudio":
        completion_payload = make_translategemma_completion_payload(
            sentence,
            source_language,
            target_language,
            model=model,
        )
        if completion_payload is not None:
            return completion_payload, None, "completion"

    if is_translategemma_model(model):
        source_code = resolve_translategemma_language_code(source_language)
        target_code = resolve_translategemma_language_code(target_language)
        if source_code and target_code:
            content = [
                {
                    "type": "text",
                    "source_lang_code": source_code,
                    "target_lang_code": target_code,
                    "text": sentence,
                }
            ]
            payload = make_sentence_payload(
                content,
                model=model,
                stream=stream,
            )
            return payload, None, "chat"

    wrapped_sentence = f"{SOURCE_START}\n{sentence}\n{SOURCE_END}"
    system_prompt = make_translation_prompt(
        source_language,
        target_language,
        include_transliteration=include_transliteration,
    )
    payload = make_sentence_payload(
        wrapped_sentence,
        model=model,
        stream=stream,
        system_prompt=system_prompt,
    )
    return payload, system_prompt, "chat"


def make_translategemma_completion_payload(
    sentence: str,
    source_language: str,
    target_language: str,
    *,
    model: Optional[str] = None,
) -> Optional[Dict[str, object]]:
    prompt = make_translategemma_completion_prompt(
        sentence,
        source_language,
        target_language,
    )
    if prompt is None:
        return None
    resolved_model = model or cfg.DEFAULT_MODEL
    return {
        "model": resolved_model,
        "prompt": prompt,
        "stream": False,
        "stop": ["<end_of_turn>"],
    }


def make_translategemma_completion_prompt(
    sentence: str,
    source_language: str,
    target_language: str,
) -> Optional[str]:
    source_code = resolve_translategemma_language_code(source_language)
    target_code = resolve_translategemma_language_code(target_language)
    if not source_code:
        source_code = _resolve_language_code_for_prompt(source_language)
    if not target_code:
        target_code = _resolve_language_code_for_prompt(target_language)
    if not source_code:
        source_code = "xx"
    if not target_code:
        target_code = "xx"
    source_name = resolve_translategemma_language_name(source_language, source_code)
    target_name = resolve_translategemma_language_name(target_language, target_code)
    cleaned_sentence = (sentence or "").strip()
    return (
        "<bos><start_of_turn>user\n"
        f"You are a professional {source_name} ({source_code}) to {target_name} ({target_code}) translator. "
        "Your goal is to accurately convey the meaning and nuances of the original "
        f"{source_name} text while adhering to {target_name} grammar, vocabulary, and cultural sensitivities.\n"
        f"Produce only the {target_name} translation, without any additional explanations or commentary. "
        f"Please translate the following {source_name} text into {target_name}:\n\n\n"
        f"{cleaned_sentence}\n"
        "<end_of_turn>\n"
        "<start_of_turn>model\n"
    )


def make_transliteration_prompt(target_language: str) -> str:
    """Prompt for requesting a transliteration from the model."""

    target_lower = (target_language or "").lower()
    target_tokens = _language_alias_tokens(target_language)
    target_descriptor = _format_language_descriptor(target_language)
    instructions = [
        f"Transliterate the following sentence in {target_descriptor} for English pronunciation.",
        "Provide ONLY the transliteration on a SINGLE LINE without ANY additional text or commentary.",
        "Preserve word boundaries with spaces; do not add labels or punctuation beyond what is needed for pronunciation.",
    ]

    for requirement in _DIACRITIC_REQUIREMENTS.values():
        if _language_matches_any(target_lower, target_tokens, requirement["aliases"]):
            instructions.append(
                "Honor the vowel marks present in the source (tashkil/niqqud) and reflect them in the transliteration so the vowels are explicit; if marks are missing, infer a fully vowelled reading."
            )

    return "\n".join(instructions)


def make_transliteration_batch_prompt(target_language: str) -> str:
    """Build a transliteration prompt for JSON batch requests."""

    target_lower = (target_language or "").lower()
    target_tokens = _language_alias_tokens(target_language)
    target_descriptor = _format_language_descriptor(target_language)

    instructions = [
        f"Transliterate each item in {target_descriptor} into Latin script for English pronunciation.",
        "The input is a JSON object with an `items` array; each item includes an `id` and `text`.",
        "Return ONLY valid JSON with an `items` array of objects.",
        "Never include markdown, code fences, commentary, or labels.",
        "Do not include the source text in the response.",
        "Each output item MUST include `id` and `transliteration` fields.",
        "The `transliteration` value must be a single-line string without line breaks.",
        "Preserve word boundaries with spaces; avoid labels or extra commentary.",
        "If you cannot transliterate an item, return an empty string for `transliteration`.",
        "Use Latin script only for the transliteration output.",
    ]

    if _language_matches_any(
        target_lower, target_tokens, _SEGMENTATION_REQUIREMENTS["thai"]["aliases"]
    ):
        instructions.append(
            "When providing the Thai transliteration, keep it on a single line, separate words with spaces (use hyphens only for syllable breaks inside a word), and avoid any labels."
        )
    if _language_matches_any(
        target_lower, target_tokens, _SEGMENTATION_REQUIREMENTS["burmese"]["aliases"]
    ):
        instructions.append(
            "When providing the Burmese transliteration, keep it on a single line, separate words with spaces (use hyphens only for syllable breaks inside a word), and avoid any labels."
        )
    if _language_matches_any(
        target_lower, target_tokens, _SEGMENTATION_REQUIREMENTS["japanese"]["aliases"]
    ):
        instructions.append(
            "When providing the Japanese transliteration (romaji), keep it on ONE LINE, separate words or phrases with SPACES (NOT per-character or per-syllable), avoid labels, and mimic natural phrase boundaries."
        )
    if _language_matches_any(
        target_lower, target_tokens, _SEGMENTATION_REQUIREMENTS["khmer"]["aliases"]
    ):
        instructions.append(
            "When providing the Khmer transliteration (Latin script), keep it on ONE LINE and separate words with SPACES; avoid labels or extra commentary."
        )

    for requirement in _DIACRITIC_REQUIREMENTS.values():
        if _language_matches_any(target_lower, target_tokens, requirement["aliases"]):
            instructions.append(
                "Honor the vowel marks present in the source (tashkil/niqqud) and reflect them in the transliteration so the vowels are explicit; if marks are missing, infer a fully vowelled reading."
            )

    return "\n".join(instructions)


def make_sentence_payload(
    sentence: object,
    *,
    model: Optional[str] = None,
    stream: bool = True,
    system_prompt: Optional[str] = None,
    additional_messages: Optional[List[Dict[str, object]]] = None,
) -> Dict[str, object]:
    """Build a chat payload using the configured defaults.

    ``sentence`` can be a string or structured content payload (e.g., a list of content blocks).
    """

    if model is None:
        model = cfg.DEFAULT_MODEL

    messages: List[Dict[str, object]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if additional_messages:
        messages.extend(additional_messages)
    messages.append({"role": "user", "content": sentence})

    return {"model": model, "messages": messages, "stream": stream}
