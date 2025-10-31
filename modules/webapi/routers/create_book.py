"""FastAPI router for creating synthetic book pipeline jobs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from modules.epub_utils import create_epub_from_sentences
from modules.llm_client_manager import client_scope
from modules.user_management import AuthService
from modules.user_management.user_store_base import UserRecord

from ..dependencies import (
    RuntimeContextProvider,
    get_auth_service,
    get_runtime_context_provider,
)
from ..schemas.create_book import BookCreationRequest, BookCreationResponse

router = APIRouter(prefix="/api/books", tags=["books"])

_ALLOWED_ROLES = frozenset({"editor", "admin"})
_PLACEHOLDER_SENTENCES = frozenset(
    {
        "this is a sample sentence",
        "this is a sample sentense",
        "sample sentence",
    }
)


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token.strip() or None
    return authorization.strip() or None


def _require_authorised_user(
    authorization: str | None,
    auth_service: AuthService,
) -> tuple[str, UserRecord]:
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session token")
    user = auth_service.authenticate(token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")
    user_roles = set(user.roles or [])
    if _ALLOWED_ROLES and not (_ALLOWED_ROLES & user_roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return token, user


def _slugify(value: str) -> str:
    normalised = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalised or "book"


def _build_summary(topic: str, genre: str) -> str:
    topic_text = topic.strip()
    genre_text = genre.strip()
    if topic_text and genre_text:
        return f"{genre_text} story about {topic_text}."
    if genre_text:
        return f"{genre_text} story."
    if topic_text:
        return f"Story about {topic_text}."
    return "Synthetic book generated via create-book workflow."


def _parse_sentences(payload: str, expected: int) -> list[str]:
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

    if not isinstance(data, Iterable):
        raise ValueError("LLM response did not contain a sentence list")

    sentences: list[str] = []
    seen_lower: set[str] = set()
    for item in data:
        sentence = str(item).strip()
        if not sentence:
            continue
        lowered = sentence.lower()
        if lowered in seen_lower or lowered in _PLACEHOLDER_SENTENCES:
            continue
        seen_lower.add(lowered)
        sentences.append(sentence)

    if len(sentences) < expected:
        raise ValueError("LLM response contained insufficient unique sentences")
    return sentences[:expected]


def _generate_sentences(
    *,
    count: int,
    input_language: str,
    topic: str,
    target_language: str,
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

    user_prompt = (
        "Create a JSON array named sentences containing exactly "
        f"{count} distinctive {input_language.strip()} sentences about {topic.strip()}. "
        "Ensure every sentence is unique, avoids filler text, and stays under 20 words."
        f"{target_clause} Return only the JSON payload."
    )

    last_error: str | None = None
    with client_scope(None) as client:
        for attempt in range(1, 4):
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
                return _parse_sentences(response.text.strip(), count)
            except ValueError as exc:
                last_error = str(exc)
        raise RuntimeError(last_error or "Failed to generate sentences")


def _resolve_user_role(user: UserRecord) -> str | None:
    if not user.roles:
        return None
    for role in user.roles:
        if role in _ALLOWED_ROLES:
            return role
    return user.roles[0]


def _relative_epub_path(epub_path: Path, books_dir: Path) -> str:
    try:
        return epub_path.relative_to(books_dir).as_posix()
    except ValueError:
        return epub_path.as_posix()


@router.post("/create", response_model=BookCreationResponse)
async def create_book(
    payload: BookCreationRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    auth_service: AuthService = Depends(get_auth_service),
) -> BookCreationResponse:
    _, user = _require_authorised_user(authorization, auth_service)

    messages: list[str] = []
    warnings: list[str] = []

    try:
        sentences = await run_in_threadpool(
            _generate_sentences,
            count=payload.num_sentences,
            input_language=payload.input_language,
            topic=payload.topic,
            target_language=payload.output_language,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Sentence generation failed: {exc}",
        ) from exc

    sentence_count = len(sentences)
    messages.append(f"Generated {sentence_count} unique sentences using the language model.")
    if sentence_count < payload.num_sentences:
        warnings.append(
            f"Requested {payload.num_sentences} sentences, but only {sentence_count} unique sentences were returned."
        )
    sentences_preview = sentences[: min(5, sentence_count)]

    resolved_config = context_provider.resolve_config({})
    config_payload = dict(resolved_config)

    base_slug = _slugify(payload.book_name)
    unique_suffix = uuid4().hex[:8]
    base_output = f"{base_slug}-{unique_suffix}"
    selected_voice = payload.voice or str(config_payload.get("selected_voice") or "gTTS")
    if payload.voice:
        messages.append(f"Voice override set to '{payload.voice}'.")
    else:
        messages.append(f"Using configured default voice '{selected_voice}'.")
    target_language = payload.output_language or payload.input_language

    config_payload.update(
        {
            "input_language": payload.input_language,
            "target_languages": [target_language],
            "selected_voice": selected_voice,
            "generate_audio": bool(config_payload.get("generate_audio", True)),
            "generate_video": False,
            "sentences_per_output_file": payload.num_sentences,
            "book_title": payload.book_name,
            "book_author": payload.author or "Me",
            "book_summary": _build_summary(payload.topic, payload.genre),
            "book_genre": payload.genre,
            "book_topic": payload.topic,
            "base_output_file": base_output,
        }
    )

    context = context_provider.build_context(config_payload, {})
    books_dir = context.books_dir
    books_dir.mkdir(parents=True, exist_ok=True)
    epub_path = books_dir / f"{base_output}.epub"
    config_payload["input_file"] = str(epub_path)

    try:
        await run_in_threadpool(create_epub_from_sentences, sentences, epub_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare EPUB: {exc}",
        ) from exc

    relative_epub_path = _relative_epub_path(epub_path, books_dir)
    messages.append(f"Seed EPUB created at {relative_epub_path}.")
    messages.append("Seed EPUB prepared; configure pipeline settings before submitting a job.")

    book_metadata = {
        "book_title": payload.book_name,
        "book_author": payload.author or "Me",
        "book_genre": payload.genre,
        "book_topic": payload.topic,
        "source_language": payload.input_language,
        "target_language": target_language,
        "selected_voice": selected_voice,
        "sentence_count": payload.num_sentences,
        "generated_sentences": list(sentences),
        "job_label": payload.book_name,
        "created_via": "create_book_api",
        "seed_epub_path": relative_epub_path,
    }

    creation_summary = {
        "epub_path": relative_epub_path,
        "messages": list(messages),
        "warnings": list(warnings),
        "sentences_preview": list(sentences_preview),
    }

    additional_metadata = {
        "creation_messages": list(messages),
        "creation_warnings": list(warnings),
        "creation_sentences_preview": list(sentences_preview),
        "creation_summary": creation_summary,
    }

    book_metadata.update(additional_metadata)
    metadata = dict(book_metadata)

    return BookCreationResponse(
        job_id=None,
        status="prepared",
        metadata=metadata,
        messages=list(messages),
        warnings=list(warnings),
        epub_path=relative_epub_path,
        input_file=str(epub_path),
        sentences_preview=list(sentences_preview),
    )
