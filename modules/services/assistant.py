"""Assistant services for lightweight LLM-powered helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from modules import logging_manager as log_mgr
from modules import prompt_templates
from modules.llm_client import LLMResponse, create_client

logger = log_mgr.get_logger().getChild("services.assistant")


def build_lookup_system_prompt(*, input_language: str, lookup_language: str) -> str:
    resolved_input = (input_language or "").strip() or "the input language"
    resolved_lookup = (lookup_language or "").strip() or "English"
    return "\n".join(
        [
            "You are MyLinguist, a fast lookup dictionary assistant.",
            f"The user will provide a word, phrase, or sentence in {resolved_input}.",
            f"Respond in {resolved_lookup}.",
            f"The user's text is between {prompt_templates.SOURCE_START} and {prompt_templates.SOURCE_END}.",
            "Never include those markers (or variations such as <<<, >>>, <<, >>) in your response.",
            "Be concise and helpful. Avoid filler, safety disclaimers, and meta commentary.",
            "",
            "You MUST respond with a valid JSON object. No text before or after the JSON.",
            "Use this exact structure:",
            "",
            "{",
            '  "type": "word" | "phrase" | "sentence",',
            '  "definition": "Main definition or meaning (required)",',
            '  "part_of_speech": "noun/verb/adj/etc or null",',
            '  "pronunciation": "IPA or common reading, or null",',
            '  "etymology": "Brief origin/root, or null if uncertain",',
            '  "example": "One short example usage, or null",',
            '  "example_translation": "Translation of example in the lookup language, or null",',
            '  "example_transliteration": "Romanized version of example if non-Latin, or null",',
            '  "idioms": ["List of idioms if sentence type, or null"],',
            '  "related_languages": [',
            '    {"language": "Persian", "word": "کتاب", "transliteration": "ketāb"},',
            '    {"language": "Turkish", "word": "kitap", "transliteration": null}',
            "  ]",
            "}",
            "",
            "Rules:",
            "- type: 'word' for single words, 'phrase' for short phrases, 'sentence' for full sentences",
            "- definition: REQUIRED. One-line definition for words/phrases, brief meaning/paraphrase for sentences",
            "- part_of_speech: Include when clear (noun, verb, adjective, adverb, etc.), null otherwise",
            "- pronunciation: IPA or common reading if known, null if not",
            "- etymology: Brief origin/root if you know it. If uncertain, use null (do NOT guess)",
            "- example: One short example usage, null if not needed",
            "- example_translation: Translation of the example sentence in the lookup language. Always provide when example is in a different language than the lookup language",
            "- example_transliteration: If the example sentence uses non-Latin script, provide the romanized transliteration here. null if Latin script or no example",
            "- idioms: For sentences only, list key idioms or tricky segments. null for words/phrases",
            "- related_languages: For words/phrases, show 3 related languages. Include transliteration for non-Latin scripts. null for sentences",
            "",
            "IMPORTANT: For any non-Latin scripts (Arabic, Chinese, Japanese, Korean, Hebrew, Russian, Greek, Thai, Hindi, etc.), ALWAYS include transliteration:",
            "- In the transliteration field for related_languages entries",
            "- In the example_transliteration field when the example sentence uses non-Latin script",
            "",
            "Keep the response concise. Omit fields that are not applicable by setting them to null.",
        ]
    )


@dataclass(slots=True)
class AssistantLookupResult:
    answer: str
    model: str
    token_usage: Dict[str, int]
    source: Optional[str] = None


def _coerce_history_messages(
    history: Sequence[Dict[str, str]] | None, *, max_messages: int = 10
) -> List[Dict[str, str]]:
    if not history:
        return []
    buffer: List[Dict[str, str]] = []
    for message in list(history)[-max_messages:]:
        role = (message.get("role") or "").strip()
        content = (message.get("content") or "").strip()
        if role not in {"user", "assistant"}:
            continue
        if not content:
            continue
        buffer.append({"role": role, "content": content})
    return buffer


def lookup_dictionary_entry(
    *,
    query: str,
    input_language: str,
    lookup_language: str,
    llm_model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    history: Sequence[Dict[str, str]] | None = None,
    timeout_seconds: int = 45,
) -> AssistantLookupResult:
    question = (query or "").strip()
    if not question:
        raise ValueError("Query cannot be empty.")

    resolved_prompt = (system_prompt or "").strip() or build_lookup_system_prompt(
        input_language=input_language, lookup_language=lookup_language
    )
    additional_messages = _coerce_history_messages(history)
    wrapped_query = f"{prompt_templates.SOURCE_START}\n{question}\n{prompt_templates.SOURCE_END}"

    with create_client(model=(llm_model or "").strip() or None) as client:
        payload = prompt_templates.make_sentence_payload(
            wrapped_query,
            model=client.model,
            stream=False,
            system_prompt=resolved_prompt,
            additional_messages=additional_messages,
        )
        response: LLMResponse = client.send_chat_request(
            payload, max_attempts=2, timeout=timeout_seconds
        )

    if response.error:
        raise RuntimeError(response.error)

    answer = (response.text or "").strip()
    if not answer:
        raise RuntimeError("Empty response from LLM.")

    return AssistantLookupResult(
        answer=answer,
        model=(llm_model or "").strip() or client.model,
        token_usage=dict(response.token_usage or {}),
        source=response.source,
    )


__all__ = [
    "AssistantLookupResult",
    "build_lookup_system_prompt",
    "lookup_dictionary_entry",
]
