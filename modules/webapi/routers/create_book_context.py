"""Generated-book context and metadata text helpers shared by Create routes."""

from __future__ import annotations

import re

SOURCE_BOOK_CONTEXT_FIELDS = (
    "source_book_title",
    "source_book_author",
    "source_book_genre",
    "source_book_summary",
)

SUMMARY_MAX_SENTENCES = 4
SUMMARY_MAX_CHARACTERS = 600


def build_summary(topic: str, genre: str) -> str:
    topic_text = topic.strip()
    genre_text = genre.strip()
    if topic_text and genre_text:
        return f"{genre_text} story about {topic_text}."
    if genre_text:
        return f"{genre_text} story."
    if topic_text:
        return f"Story about {topic_text}."
    return "Synthetic book generated via create-book workflow."


def normalize_optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def source_book_context(payload: object) -> dict[str, str]:
    context: dict[str, str] = {}
    for field_name in SOURCE_BOOK_CONTEXT_FIELDS:
        value = normalize_optional_text(getattr(payload, field_name, None))
        if value:
            context[field_name] = value
    return context


def limit_summary_length(summary: str) -> str:
    cleaned = summary.strip()
    if not cleaned:
        return cleaned

    primary_paragraph = cleaned.split("\n\n", 1)[0].strip()
    sentences = re.split(r"(?<=[.!?])\s+", primary_paragraph)

    limited_sentences: list[str] = []
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue
        limited_sentences.append(stripped)
        if len(limited_sentences) >= SUMMARY_MAX_SENTENCES:
            break

    short_summary = " ".join(limited_sentences) if limited_sentences else primary_paragraph
    if len(short_summary) <= SUMMARY_MAX_CHARACTERS:
        return short_summary

    truncated = short_summary[: SUMMARY_MAX_CHARACTERS - 1].rsplit(" ", 1)[0]
    return truncated + "\u2026"
