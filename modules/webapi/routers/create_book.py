"""FastAPI router for creating synthetic book pipeline jobs."""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime
from dataclasses import replace as dataclass_replace
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from modules import logging_manager as log_mgr
from modules.epub_utils import create_epub_from_sentences
from modules.images.drawthings import (
    DrawThingsImageRequest,
    normalize_drawthings_base_urls,
    resolve_drawthings_client,
)
from modules.images.prompting import (
    build_sentence_image_negative_prompt,
    build_sentence_image_prompt,
)
from modules.images.style_templates import resolve_image_style_template
from modules.llm_client_manager import client_scope
from modules.user_management import AuthService
from modules.user_management.user_store_base import UserRecord

from ...services.job_manager.job import PipelineJobStatus
from ...services.pipeline_service import (
    PipelineService,
    serialize_pipeline_request,
    serialize_pipeline_response,
)
from ...services.file_locator import FileLocator
from ..dependencies import (
    RequestUserContext,
    RuntimeContextProvider,
    get_auth_service,
    get_pipeline_job_manager,
    get_pipeline_service,
    get_request_user,
    get_runtime_context_provider,
)
from ..schemas import PipelineSubmissionResponse
from ..schemas.create_book import (
    BookCreationRequest,
    BookCreationResponse,
    BookGenerationJobSubmission,
)

router = APIRouter(prefix="/api/books", tags=["books"])

_ALLOWED_ROLES = frozenset({"editor", "admin"})
_PLACEHOLDER_SENTENCES = frozenset(
    {
        "this is a sample sentence",
        "this is a sample sentense",
        "sample sentence",
    }
)
_MAX_METADATA_SENTENCES = 50
_SUMMARY_MAX_SENTENCES = 4
_SUMMARY_MAX_CHARACTERS = 600

logger = log_mgr.get_logger()


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


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).strip()


def _normalize_optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _extract_json_object(payload: str) -> dict[str, Any] | None:
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


def _limit_summary_length(summary: str) -> str:
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
        if len(limited_sentences) >= _SUMMARY_MAX_SENTENCES:
            break

    short_summary = " ".join(limited_sentences) if limited_sentences else primary_paragraph
    if len(short_summary) <= _SUMMARY_MAX_CHARACTERS:
        return short_summary

    truncated = short_summary[: _SUMMARY_MAX_CHARACTERS - 1].rsplit(" ", 1)[0]
    return truncated + "…"


def _coerce_int(value: object, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_float(value: object, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _generate_llm_metadata(
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
    sentence_block = sentence_block[:_MAX_METADATA_SENTENCES]

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
            payload = _extract_json_object(response.text or "")
            if payload is not None:
                return payload
            last_error = "LLM response was not valid JSON."
    raise RuntimeError(last_error or "Failed to generate metadata via LLM.")


def _generate_cover_image(
    *,
    prompt: str,
    negative_prompt: str | None,
    output_dir: Path,
    config: dict[str, Any],
) -> tuple[str | None, str | None, str | None, str | None]:
    base_urls = normalize_drawthings_base_urls(
        base_url=config.get("image_api_base_url"),
        base_urls=config.get("image_api_base_urls"),
    )
    if not base_urls:
        return None, None, None, "unconfigured"

    style_value = config.get("image_style_template")
    style_template = resolve_image_style_template(style_value)
    prompt_text = _collapse_whitespace(prompt)
    if not prompt_text:
        return None, None, None, None

    full_prompt = build_sentence_image_prompt(
        prompt_text,
        style_template=style_template.template_id,
    )
    full_negative = build_sentence_image_negative_prompt(
        _collapse_whitespace(negative_prompt or ""),
        style_template=style_template.template_id,
    )

    width = max(64, _coerce_int(config.get("image_width"), 512))
    height = max(64, _coerce_int(config.get("image_height"), 512))
    steps = max(1, _coerce_int(config.get("image_steps"), int(style_template.default_steps)))
    cfg_scale = _coerce_float(config.get("image_cfg_scale"), style_template.default_cfg_scale)
    sampler_name = _normalize_optional_text(config.get("image_sampler_name"))
    if not sampler_name:
        sampler_name = style_template.default_sampler_name

    request = DrawThingsImageRequest(
        prompt=full_prompt,
        negative_prompt=full_negative,
        width=width,
        height=height,
        steps=steps,
        cfg_scale=cfg_scale,
        sampler_name=sampler_name,
    )
    timeout_seconds = max(1.0, _coerce_float(config.get("image_api_timeout_seconds"), 180.0))
    client, _available_urls, unavailable_urls = resolve_drawthings_client(
        base_urls=base_urls,
        timeout_seconds=timeout_seconds,
    )
    if unavailable_urls:
        logger.warning(
            "DrawThings endpoints unavailable: %s",
            ", ".join(unavailable_urls),
            extra={
                "event": "webapi.cover.unavailable",
                "attributes": {"unavailable": unavailable_urls},
                "console_suppress": True,
            },
        )
    if client is None:
        return None, None, None, "unavailable"
    image_bytes, _payload = client.txt2img(request)

    output_dir.mkdir(parents=True, exist_ok=True)
    cover_path = output_dir / "cover.png"
    cover_path.write_bytes(image_bytes)
    return str(cover_path), full_prompt, full_negative, None


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


def _ensure_book_role(request_user: RequestUserContext) -> None:
    role = (request_user.user_role or "").strip().lower()
    if _ALLOWED_ROLES and role not in _ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def _maybe_update_voice_selection(
    request: PipelineRequest,
    generator_voice: str | None,
) -> str:
    current_voice = request.inputs.selected_voice
    if generator_voice and generator_voice.strip():
        request.inputs.selected_voice = generator_voice.strip()
        return request.inputs.selected_voice
    if current_voice and current_voice.strip():
        return current_voice
    configured = request.config.get("selected_voice")
    if isinstance(configured, str) and configured.strip():
        request.inputs.selected_voice = configured.strip()
        return request.inputs.selected_voice
    return "gTTS"


def _execute_book_job(
    job,
    *,
    generator: BookGenerationJobSubmission,
    context_provider: RuntimeContextProvider,
    pipeline_service: PipelineService,
    file_locator: FileLocator,
) -> None:
    tracker = job.tracker
    stop_event = job.stop_event
    generator_payload = generator.generator
    pipeline_payload = generator.pipeline

    def _publish_progress(metadata: dict[str, object]) -> None:
        if tracker is not None:
            tracker.publish_progress(metadata)

    def _check_cancelled(stage: str) -> None:
        if stop_event is not None and stop_event.is_set():
            job.status = PipelineJobStatus.CANCELLED
            job.error_message = f"Cancelled during {stage}"
            raise RuntimeError(job.error_message)

    _publish_progress({"stage": "book_generation", "message": "Preparing job context."})
    resolved_config = context_provider.resolve_config(pipeline_payload.config)
    overrides = dict(pipeline_payload.environment_overrides)
    overrides.update(pipeline_payload.pipeline_overrides)
    context = context_provider.build_context(resolved_config, overrides)

    request = pipeline_payload.to_pipeline_request(
        context=context,
        resolved_config=resolved_config,
    )
    cover_config = dict(resolved_config)
    cover_config.update(pipeline_payload.pipeline_overrides)
    request.progress_tracker = tracker
    request.stop_event = stop_event
    request.correlation_id = request.correlation_id or job.job_id
    request.job_id = job.job_id

    input_language = (
        generator_payload.input_language
        or request.inputs.input_language
        or resolved_config.get("input_language")
        or ""
    ).strip()
    if not input_language:
        raise RuntimeError("Input language is required to generate a book.")
    request.inputs.input_language = input_language
    target_language = (
        generator_payload.output_language
        or (request.inputs.target_languages[0] if request.inputs.target_languages else None)
        or input_language
    )
    if target_language and target_language not in request.inputs.target_languages:
        request.inputs.target_languages.insert(0, target_language)

    base_output = request.inputs.base_output_file.strip() or _slugify(generator_payload.book_name)
    request.inputs.base_output_file = base_output

    data_root = file_locator.data_root(job.job_id)
    data_root.mkdir(parents=True, exist_ok=True)

    media_root = file_locator.media_root(job.job_id)
    media_root.mkdir(parents=True, exist_ok=True)
    request.environment_overrides = dict(request.environment_overrides)
    request.environment_overrides.setdefault("output_dir", str(media_root))
    job_storage_url = file_locator.resolve_url(job.job_id, "media")
    if job_storage_url:
        request.environment_overrides.setdefault("job_storage_url", job_storage_url)
    context = dataclass_replace(request.context, output_dir=media_root)
    request.context = context

    if request.inputs.sentences_per_output_file < 1:
        fallback_chunk_size = resolved_config.get("sentences_per_output_file") or 1
        try:
            resolved_chunk_size = int(fallback_chunk_size)
        except (TypeError, ValueError):
            resolved_chunk_size = 1
        request.inputs.sentences_per_output_file = max(1, resolved_chunk_size)
    selected_voice = _maybe_update_voice_selection(request, generator_payload.voice)

    epub_path = data_root / f"{base_output}.epub"
    request.inputs.input_file = str(epub_path)

    _check_cancelled("sentence generation")
    _publish_progress(
        {
            "stage": "book_generation",
            "message": "Requesting source sentences from the language model.",
            "target_language": target_language or input_language,
        }
    )
    sentences = _generate_sentences(
        count=generator_payload.num_sentences,
        input_language=input_language,
        topic=generator_payload.topic,
        target_language=target_language or input_language,
    )
    sentence_count = len(sentences)
    warnings: list[str] = []
    if sentence_count < generator_payload.num_sentences:
        warnings.append(
            f"Requested {generator_payload.num_sentences} sentences, but only {sentence_count} unique sentences were returned."
        )
    sentences_preview = sentences[: min(5, sentence_count)]
    _publish_progress(
        {
            "stage": "book_generation",
            "message": f"Generated {sentence_count} sentences. Preparing EPUB…",
            "generated_sentences": sentence_count,
        }
    )

    metadata_messages: list[str] = []
    metadata_warnings: list[str] = []
    llm_summary: str | None = None
    llm_genre: str | None = None
    cover_prompt: str | None = None
    cover_negative_prompt: str | None = None
    cover_file_path: str | None = None
    cover_prompt_used: str | None = None
    cover_negative_used: str | None = None
    cover_skip_reason: str | None = None

    _check_cancelled("metadata generation")
    if sentences:
        _publish_progress(
            {
                "stage": "book_generation",
                "message": "Generating metadata summary and cover prompt.",
            }
        )
        try:
            llm_payload = _generate_llm_metadata(
                book_title=generator_payload.book_name,
                topic=generator_payload.topic,
                seed_genre=generator_payload.genre,
                author=generator_payload.author or "Me",
                input_language=input_language,
                sentences=sentences,
            )
        except Exception as exc:
            metadata_warnings.append(f"Metadata generation failed: {exc}")
            logger.warning("Metadata generation failed for job %s: %s", job.job_id, exc)
        else:
            llm_summary = _normalize_optional_text(llm_payload.get("summary"))
            if llm_summary:
                llm_summary = _limit_summary_length(llm_summary)
                metadata_messages.append("Generated metadata summary using the LLM.")
            llm_genre = _normalize_optional_text(llm_payload.get("genre"))
            if llm_genre:
                metadata_messages.append("Classified book genre using the LLM.")
            cover_prompt = _normalize_optional_text(llm_payload.get("cover_prompt"))
            cover_negative_prompt = _normalize_optional_text(
                llm_payload.get("cover_negative_prompt")
            )
            if cover_prompt:
                metadata_messages.append("Prepared a cover prompt using the LLM.")
            else:
                metadata_warnings.append("LLM did not return a cover prompt.")

    if cover_prompt:
        _check_cancelled("cover generation")
        _publish_progress(
            {
                "stage": "book_generation",
                "message": "Generating cover art via diffusion.",
            }
        )
        try:
            (
                cover_file_path,
                cover_prompt_used,
                cover_negative_used,
                cover_skip_reason,
            ) = _generate_cover_image(
                prompt=cover_prompt,
                negative_prompt=cover_negative_prompt,
                output_dir=data_root,
                config=cover_config,
            )
            if cover_file_path:
                metadata_messages.append("Generated cover art using the diffusion model.")
            else:
                if cover_skip_reason == "unavailable":
                    metadata_warnings.append(
                        "Cover generation skipped because DrawThings endpoints are unavailable."
                    )
                elif cover_skip_reason == "unconfigured":
                    metadata_warnings.append(
                        "Cover generation skipped because image_api_base_url(s) are not configured."
                    )
                else:
                    metadata_warnings.append("Cover generation skipped.")
        except Exception as exc:
            metadata_warnings.append(f"Cover generation failed: {exc}")
            logger.warning("Cover generation failed for job %s: %s", job.job_id, exc)

    _check_cancelled("epub preparation")
    create_epub_from_sentences(sentences, epub_path, book_title=generator_payload.book_name)
    relative_epub_path = _relative_epub_path(epub_path, data_root)

    summary = llm_summary or _build_summary(generator_payload.topic, generator_payload.genre)
    current_year = str(datetime.now().year)
    creation_messages = [
        f"Generated {sentence_count} unique sentences using the language model.",
        *metadata_messages,
        f"Seed EPUB created at {relative_epub_path}.",
        "Seed EPUB prepared; continuing with pipeline processing.",
    ]
    creation_summary = {
        "epub_path": relative_epub_path,
        "messages": list(creation_messages),
        "warnings": list(warnings) + list(metadata_warnings),
        "sentences_preview": list(sentences_preview),
    }

    metadata_updates = {
        "book_title": generator_payload.book_name,
        "book_author": generator_payload.author or "Me",
        "book_genre": llm_genre or generator_payload.genre,
        "book_topic": generator_payload.topic,
        "book_summary": summary,
        "book_year": current_year,
        "source_language": input_language,
        "target_language": target_language or input_language,
        "selected_voice": selected_voice,
        "sentence_count": generator_payload.num_sentences,
        "generated_sentences": list(sentences),
        "job_label": generator_payload.book_name,
        "created_via": "book_generation_job",
        "seed_epub_path": relative_epub_path,
        "creation_messages": creation_messages,
        "creation_warnings": list(warnings) + list(metadata_warnings),
        "creation_sentences_preview": list(sentences_preview),
        "creation_summary": creation_summary,
    }
    if cover_file_path:
        metadata_updates["book_cover_file"] = cover_file_path
    cover_prompt_value = cover_prompt_used or cover_prompt
    cover_negative_value = cover_negative_used or cover_negative_prompt
    if cover_prompt_value:
        metadata_updates["book_cover_prompt"] = cover_prompt_value
    if cover_negative_value:
        metadata_updates["book_cover_negative_prompt"] = cover_negative_value
    request.inputs.media_metadata.update(metadata_updates)
    request.pipeline_overrides = dict(request.pipeline_overrides)
    request.pipeline_overrides.setdefault(
        "book_generation",
        {
            "topic": generator_payload.topic,
            "book_name": generator_payload.book_name,
            "genre": generator_payload.genre,
            "num_sentences": generator_payload.num_sentences,
        },
    )

    serialized_request = serialize_pipeline_request(request)
    job.request_payload = copy.deepcopy(serialized_request)
    job.resume_context = copy.deepcopy(serialized_request)
    job.request = request

    _publish_progress(
        {"stage": "book_generation", "message": "Seed EPUB prepared; starting pipeline run."}
    )
    _check_cancelled("pipeline")
    response = pipeline_service.run_sync(request)
    job.result = response
    job.result_payload = serialize_pipeline_response(response)
    job.generated_files = copy.deepcopy(response.generated_files)
    job.media_completed = bool(response.success)
    if job.status != PipelineJobStatus.CANCELLED:
        job.status = (
            PipelineJobStatus.COMPLETED if response.success else PipelineJobStatus.FAILED
        )
        job.error_message = None if response.success else "Pipeline execution reported failure."
    else:
        job.error_message = job.error_message or "Job cancelled during pipeline execution."


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
        await run_in_threadpool(
            create_epub_from_sentences,
            sentences,
            epub_path,
            book_title=payload.book_name,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare EPUB: {exc}",
        ) from exc

    relative_epub_path = _relative_epub_path(epub_path, books_dir)
    messages.append(f"Seed EPUB created at {relative_epub_path}.")
    messages.append("Seed EPUB prepared; configure pipeline settings before submitting a job.")

    media_metadata = {
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

    media_metadata.update(additional_metadata)
    metadata = dict(media_metadata)

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


@router.post("/jobs", response_model=PipelineSubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_book_job(
    payload: BookGenerationJobSubmission,
    request_user: RequestUserContext = Depends(get_request_user),
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    job_manager=Depends(get_pipeline_job_manager),
):
    _ensure_book_role(request_user)

    generator_payload = payload.generator
    request_payload = payload.pipeline.model_dump()
    request_payload["book_generation"] = generator_payload.model_dump()

    def _worker(job):
        _execute_book_job(
            job,
            generator=payload,
            context_provider=context_provider,
            pipeline_service=pipeline_service,
            file_locator=job_manager.file_locator if hasattr(job_manager, "file_locator") else FileLocator(),
        )

    job = job_manager.submit_background_job(
        job_type="book",
        worker=_worker,
        request_payload=request_payload,
        user_id=request_user.user_id,
        user_role=request_user.user_role,
    )

    return PipelineSubmissionResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        job_type=job.job_type,
    )
