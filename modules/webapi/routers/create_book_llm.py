"""Generated-book LLM prompt and response helpers."""

from __future__ import annotations

import json
from typing import Any

from modules.llm_client_manager import client_scope

PLACEHOLDER_SENTENCES = frozenset(
    {
        "this is a sample sentence",
        "this is a sample sentense",
        "sample sentence",
    }
)
MAX_METADATA_SENTENCES = 50


def extract_json_object(payload: str) -> dict[str, Any] | None:
    raw = (payload or "").strip()
    if not raw:
        return None
    try:
        parsed: Any = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def generate_llm_metadata(
    *,
    book_title: str,
    topic: str,
    seed_genre: str,
    author: str,
    input_language: str,
    sentences: list[str],
) -> dict[str, Any]:
    if not sentences:
        return {}
    sentence_block = [entry.strip() for entry in sentences if entry.strip()]
    if not sentence_block:
        return {}
    sentence_block = sentence_block[:MAX_METADATA_SENTENCES]

    system_prompt = (
        "You are a publishing editor helping generate metadata for a synthetic audiobook. "
        "Return JSON only with keys: summary, genre, cover_prompt, cover_negative_prompt.\n"
        "- summary: 2-4 sentences (<= 80 words), in the input language.\n"
        "- genre: a concise 1-3 word genre label.\n"
        "- cover_prompt: English-only scene description for diffusion (no style keywords, no text).\n"
        "- cover_negative_prompt: optional English list of things to avoid.\n"
        "Do not add extra keys or commentary."
    )
    user_payload = {
        "book_title": book_title,
        "topic": topic,
        "seed_genre": seed_genre,
        "author": author,
        "input_language": input_language,
        "sentences": sentence_block,
    }
    user_prompt = "```json\n" + json.dumps(user_payload, ensure_ascii=False, indent=2) + "\n```"

    last_error: str | None = None
    with client_scope(None) as client:
        if not getattr(client, "model", None):
            raise RuntimeError("LLM model is not configured.")
        for _ in range(2):
            response = client.send_chat_request(
                {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.4, "top_p": 0.9},
                },
                timeout=180,
            )
            if response.error:
                last_error = response.error
                continue
            payload = extract_json_object(response.text or "")
            if payload is not None:
                return payload
            last_error = "LLM response was not valid JSON."
    raise RuntimeError(last_error or "Failed to generate metadata via LLM.")


def parse_sentences(payload: str, expected: int) -> list[str]:
    try:
        data: Any = json.loads(payload)
    except json.JSONDecodeError:
        start = payload.find("[")
        end = payload.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("LLM response was not valid JSON")
        data = json.loads(payload[start : end + 1])

    if isinstance(data, dict):
        data = data.get("sentences")

    if not isinstance(data, list):
        raise ValueError("LLM response did not contain a sentence list")

    sentences: list[str] = []
    seen_lower: set[str] = set()
    for item in data:
        if not isinstance(item, str):
            continue
        sentence = item.strip()
        if not sentence:
            continue
        lowered = sentence.lower()
        if lowered in seen_lower or lowered in PLACEHOLDER_SENTENCES:
            continue
        seen_lower.add(lowered)
        sentences.append(sentence)

    if len(sentences) < expected:
        raise ValueError("LLM response contained insufficient unique sentences")
    return sentences[:expected]


def generate_sentences(
    *,
    count: int,
    input_language: str,
    topic: str,
    target_language: str,
    source_book_title: str | None = None,
    source_book_author: str | None = None,
    source_book_genre: str | None = None,
    source_book_summary: str | None = None,
) -> list[str]:
    system_prompt = (
        "You generate evaluation data for an e-book creation pipeline. "
        "Respond with JSON only."
    )
    target_clause = ""
    if target_language and target_language.strip():
        target_clause = (
            " Craft sentences that translate cleanly into "
            f"{target_language.strip()}."
        )
    source_context_parts = []
    if source_book_title and source_book_title.strip():
        source_context_parts.append(f"title {source_book_title.strip()!r}")
    if source_book_author and source_book_author.strip():
        source_context_parts.append(f"author {source_book_author.strip()!r}")
    if source_book_genre and source_book_genre.strip():
        source_context_parts.append(f"genre {source_book_genre.strip()!r}")
    if source_book_summary and source_book_summary.strip():
        source_context_parts.append(f"summary {source_book_summary.strip()!r}")
    source_context = ""
    if source_context_parts:
        source_context = (
            " Treat this as continuation or homage context, without copying "
            "protected text: " + "; ".join(source_context_parts) + "."
        )

    user_prompt = (
        "Create a JSON array named sentences containing exactly "
        f"{count} distinctive {input_language.strip()} sentences about {topic.strip()}. "
        "Ensure every sentence is unique, avoids filler text, and stays under 20 words."
        f"{source_context}{target_clause} Return only the JSON payload."
    )

    last_error: str | None = None
    with client_scope(None) as client:
        for _ in range(1, 4):
            response = client.send_chat_request(
                {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.7, "top_p": 0.9},
                },
                timeout=180,
            )
            if response.error:
                last_error = response.error
                continue
            try:
                return parse_sentences(response.text.strip(), count)
            except ValueError as exc:
                last_error = str(exc)
        raise RuntimeError(last_error or "Failed to generate sentences")
