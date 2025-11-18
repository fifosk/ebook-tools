"""Prompt templates used for communicating with the LLM."""

from __future__ import annotations

from typing import Dict, List, Optional

from modules import config_manager as cfg

SOURCE_START = "<<<BEGIN_SOURCE_TEXT>>>"
SOURCE_END = "<<<END_SOURCE_TEXT>>>"


def make_translation_prompt(
    source_language: str,
    target_language: str,
    *,
    mode: str = "default",
    include_transliteration: bool = False,
) -> str:
    """Build a translation prompt tailored to the desired mode."""

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

    if include_transliteration:
        instructions.append(
            "If a transliteration is appropriate, append ONLY the transliteration on the SECOND LINE, without prefixes, labels, commentary, or delimiter characters."
        )

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
