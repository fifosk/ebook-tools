"""Routes for pipeline media metadata and downloads."""

from __future__ import annotations

import copy
import json
import mimetypes
import re
import tempfile
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse

from ... import config_manager as cfg
from ... import logging_manager
from ...metadata_manager import MetadataLoader
from ...images.drawthings import (
    DrawThingsError,
    DrawThingsImageRequest,
    normalize_drawthings_base_urls,
    resolve_drawthings_client,
)
from ...images.prompting import (
    build_sentence_image_negative_prompt,
    build_sentence_image_prompt,
    sentence_batches_to_diffusion_prompt_plan,
    sentence_to_diffusion_prompt,
)
from ...images.style_templates import normalize_image_style_template
from ...services.file_locator import FileLocator
from ...services.pipeline_service import PipelineService
from ...library import LibraryRepository
from ..dependencies import (
    RequestUserContext,
    get_file_locator,
    get_library_repository,
    get_pipeline_job_manager,
    get_pipeline_service,
    get_request_user,
)

from ..jobs import PipelineJob
from ..schemas.images import (
    SentenceImageInfoResponse,
    SentenceImageInfoBatchResponse,
    SentenceImageRegenerateRequest,
    SentenceImageRegenerateResponse,
)
from ..schemas import PipelineMediaChunk, PipelineMediaFile, PipelineMediaResponse

router = APIRouter()
storage_router = APIRouter()
jobs_timing_router = APIRouter(prefix="/api/jobs", tags=["jobs"])
LOGGER = logging_manager.get_logger().getChild("webapi.media")


def _coerce_int_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float_default(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_bool_default(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp_handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    )
    try:
        with tmp_handle as handle:
            handle.write(serialized)
            handle.flush()
        Path(tmp_handle.name).replace(path)
    except Exception:
        Path(tmp_handle.name).unlink(missing_ok=True)
        raise


def _resolve_sentence_number(entry: Mapping[str, Any]) -> Optional[int]:
    raw_number = entry.get("sentence_number") or entry.get("sentenceNumber")
    try:
        return int(raw_number)
    except (TypeError, ValueError):
        return None


def _extract_sentence_text(entry: Mapping[str, Any]) -> Optional[str]:
    text_value = entry.get("text")
    if isinstance(text_value, str) and text_value.strip():
        return text_value.strip()
    original = entry.get("original")
    if isinstance(original, Mapping):
        original_text = original.get("text")
        if isinstance(original_text, str) and original_text.strip():
            return original_text.strip()
    return None


def _read_chunk_payload(
    *,
    job_root: Path,
    metadata_path: str,
) -> Optional[Mapping[str, Any]]:
    path_value = metadata_path.strip()
    if not path_value:
        return None
    chunk_path = _resolve_job_path(job_root, path_value)
    try:
        payload = json.loads(chunk_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, Mapping) else None


def _find_sentence_entry(
    *,
    chunk_payload: Mapping[str, Any],
    sentence_number: int,
) -> Optional[dict[str, Any]]:
    sentences = chunk_payload.get("sentences")
    if not isinstance(sentences, list):
        return None
    for entry in sentences:
        if not isinstance(entry, dict):
            continue
        if _resolve_sentence_number(entry) == sentence_number:
            return entry
    return None


def _collect_context_sentence_texts(
    *,
    loader: MetadataLoader,
    job_root: Path,
    sentence_number: int,
    count: int,
) -> list[str]:
    if count <= 0:
        return []
    cache: dict[str, Mapping[str, Any]] = {}
    collected: list[str] = []

    start = max(sentence_number - count, 1)
    for number in range(start, sentence_number):
        chunk = _resolve_chunk_for_sentence(loader, number)
        if not isinstance(chunk, Mapping):
            continue
        metadata_path = chunk.get("metadata_path")
        if not isinstance(metadata_path, str) or not metadata_path.strip():
            continue
        key = metadata_path.strip()
        payload = cache.get(key)
        if payload is None:
            loaded = _read_chunk_payload(job_root=job_root, metadata_path=key)
            if loaded is None:
                continue
            cache[key] = loaded
            payload = loaded
        entry = _find_sentence_entry(chunk_payload=payload, sentence_number=number)
        if not isinstance(entry, Mapping):
            continue
        text = _extract_sentence_text(entry)
        if text:
            collected.append(text)

    end = sentence_number + count
    for number in range(sentence_number + 1, end + 1):
        chunk = _resolve_chunk_for_sentence(loader, number)
        if not isinstance(chunk, Mapping):
            continue
        metadata_path = chunk.get("metadata_path")
        if not isinstance(metadata_path, str) or not metadata_path.strip():
            continue
        key = metadata_path.strip()
        payload = cache.get(key)
        if payload is None:
            loaded = _read_chunk_payload(job_root=job_root, metadata_path=key)
            if loaded is None:
                continue
            cache[key] = loaded
            payload = loaded
        entry = _find_sentence_entry(chunk_payload=payload, sentence_number=number)
        if not isinstance(entry, Mapping):
            continue
        text = _extract_sentence_text(entry)
        if text:
            collected.append(text)

    return collected


def _collect_sentence_range_texts(
    *,
    loader: MetadataLoader,
    job_root: Path,
    start_sentence: int,
    end_sentence: int,
) -> list[str]:
    if end_sentence < start_sentence:
        return []
    cache: dict[str, Mapping[str, Any]] = {}
    collected: list[str] = []

    for number in range(max(1, start_sentence), end_sentence + 1):
        chunk = _resolve_chunk_for_sentence(loader, number)
        if not isinstance(chunk, Mapping):
            continue
        metadata_path = chunk.get("metadata_path")
        if not isinstance(metadata_path, str) or not metadata_path.strip():
            continue
        key = metadata_path.strip()
        payload = cache.get(key)
        if payload is None:
            loaded = _read_chunk_payload(job_root=job_root, metadata_path=key)
            if loaded is None:
                continue
            cache[key] = loaded
            payload = loaded
        entry = _find_sentence_entry(chunk_payload=payload, sentence_number=number)
        if not isinstance(entry, Mapping):
            continue
        text = _extract_sentence_text(entry)
        if text:
            collected.append(text)
    return collected


def _extract_sentence_image(entry: Mapping[str, Any]) -> tuple[Optional[str], Optional[str]]:
    image = entry.get("image")
    if not isinstance(image, Mapping):
        return None, None
    prompt = image.get("prompt")
    negative = image.get("negative_prompt") or image.get("negativePrompt")
    prompt_str = prompt.strip() if isinstance(prompt, str) and prompt.strip() else None
    negative_str = negative.strip() if isinstance(negative, str) and negative.strip() else None
    return prompt_str, negative_str


def _extract_sentence_image_path(entry: Mapping[str, Any]) -> Optional[str]:
    image = entry.get("image")
    if isinstance(image, Mapping):
        path = image.get("path")
        if isinstance(path, str) and path.strip():
            return path.strip()
    for key in ("image_path", "imagePath"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_sentence_image_batch_range(entry: Mapping[str, Any]) -> tuple[Optional[int], Optional[int]]:
    image = entry.get("image")
    if not isinstance(image, Mapping):
        return None, None
    raw_start = image.get("batch_start_sentence") or image.get("batchStartSentence")
    raw_end = image.get("batch_end_sentence") or image.get("batchEndSentence")
    start: Optional[int]
    end: Optional[int]
    try:
        start = int(raw_start)
    except (TypeError, ValueError):
        start = None
    try:
        end = int(raw_end)
    except (TypeError, ValueError):
        end = None
    if start is None or end is None:
        return None, None
    if start <= 0 or end <= 0 or end < start:
        return None, None
    return start, end


MAX_SENTENCE_IMAGE_BATCH = 200


def _parse_sentence_numbers(values: Sequence[str]) -> List[int]:
    numbers: List[int] = []
    seen: set[int] = set()
    for raw in values:
        if raw is None:
            continue
        for part in str(raw).split(","):
            cleaned = part.strip()
            if not cleaned:
                continue
            try:
                number = int(cleaned)
            except (TypeError, ValueError):
                continue
            if number <= 0:
                continue
            if number in seen:
                continue
            seen.add(number)
            numbers.append(number)
    return numbers


def _build_sentence_image_info_response(
    *,
    job_id: str,
    sentence_number: int,
    chunk: Mapping[str, Any],
    sentence_entry: Mapping[str, Any],
) -> SentenceImageInfoResponse:
    range_fragment = chunk.get("range_fragment") or chunk.get("rangeFragment")
    range_fragment_str = (
        str(range_fragment).strip()
        if isinstance(range_fragment, str) and range_fragment.strip()
        else None
    )
    prompt, negative_prompt = _extract_sentence_image(sentence_entry)
    relative_path = _extract_sentence_image_path(sentence_entry)
    if not relative_path and range_fragment_str:
        relative_path = _resolve_image_relative_path(range_fragment_str, sentence_number)
    return SentenceImageInfoResponse(
        job_id=job_id,
        sentence_number=sentence_number,
        range_fragment=range_fragment_str,
        relative_path=relative_path,
        sentence=_extract_sentence_text(sentence_entry),
        prompt=prompt,
        negative_prompt=negative_prompt,
    )


def _resolve_chunk_for_sentence(
    loader: MetadataLoader,
    sentence_number: int,
) -> Mapping[str, Any] | None:
    for chunk in loader.iter_chunks():
        start = chunk.get("start_sentence") or chunk.get("startSentence")
        end = chunk.get("end_sentence") or chunk.get("endSentence")
        try:
            start_val = int(start)
            end_val = int(end)
        except (TypeError, ValueError):
            continue
        if start_val <= sentence_number <= end_val:
            return chunk
    return None


def _resolve_image_relative_path(range_fragment: str, sentence_number: int) -> str:
    return f"media/images/{range_fragment}/sentence_{sentence_number:05d}.png"


def _resolve_image_settings(config: Mapping[str, Any], request: SentenceImageRegenerateRequest) -> dict[str, Any]:
    width = max(
        64,
        _coerce_int_default(
            request.width,
            _coerce_int_default(config.get("image_width"), 512),
        ),
    )
    height = max(
        64,
        _coerce_int_default(
            request.height,
            _coerce_int_default(config.get("image_height"), 512),
        ),
    )
    steps = max(
        1,
        _coerce_int_default(
            request.steps,
            _coerce_int_default(config.get("image_steps"), 24),
        ),
    )
    cfg_scale = max(
        0.0,
        _coerce_float_default(
            request.cfg_scale,
            _coerce_float_default(config.get("image_cfg_scale"), 7.0),
        ),
    )
    sampler_name = request.sampler_name
    if isinstance(sampler_name, str):
        sampler_name = sampler_name.strip() or None
    if sampler_name is None:
        config_sampler = config.get("image_sampler_name")
        sampler_name = config_sampler.strip() if isinstance(config_sampler, str) and config_sampler.strip() else None
    seed = request.seed if isinstance(request.seed, int) else None
    return {
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "sampler_name": sampler_name,
        "seed": seed,
    }


def _normalise_prompt(prompt: str | None) -> str:
    candidate = (prompt or "").strip()
    return candidate


def _normalise_negative_prompt(negative: str | None) -> str:
    candidate = (negative or "").strip()
    return candidate


def _ensure_prompt_suffix(prompt: str, *, style_template: str) -> str:
    return build_sentence_image_prompt(prompt, style_template=style_template)


def _ensure_negative_suffix(negative: str, *, style_template: str) -> str:
    return build_sentence_image_negative_prompt(negative, style_template=style_template)


def _resolve_job_image_style_template(job_root: Path) -> str:
    manifest_path = job_root / "metadata" / "job.json"
    if not manifest_path.exists():
        return "photorealistic"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return "photorealistic"
    if not isinstance(payload, Mapping):
        return "photorealistic"
    request_payload = payload.get("request")
    if not isinstance(request_payload, Mapping):
        return "photorealistic"
    pipeline_overrides = request_payload.get("pipeline_overrides")
    config_payload = request_payload.get("config")
    style_value = None
    if isinstance(pipeline_overrides, Mapping):
        style_value = pipeline_overrides.get("image_style_template")
    if style_value is None and isinstance(config_payload, Mapping):
        style_value = config_payload.get("image_style_template")
    return normalize_image_style_template(style_value)


def _resolve_job_path(job_root: Path, relative_path: str) -> Path:
    normalized = relative_path.replace("\\", "/").strip()
    if not normalized:
        raise ValueError("Empty path")
    candidate = Path(normalized)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (job_root / candidate).resolve()
    try:
        resolved.relative_to(job_root)
    except ValueError as exc:
        raise ValueError("Path escapes job root") from exc
    return resolved


def _resolve_job_root(
    *,
    job_id: str,
    locator: FileLocator,
    library_repository: LibraryRepository,
    request_user: RequestUserContext,
    job_manager: Any,
) -> Path:
    try:
        job_manager.get(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError:
        entry = library_repository.get_entry_by_id(job_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        job_root = Path(entry.library_path)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    else:
        pipeline_root = locator.resolve_path(job_id)
        probe = pipeline_root / "metadata" / "job.json"
        if probe.exists():
            job_root = pipeline_root
        else:
            entry = library_repository.get_entry_by_id(job_id)
            if entry is not None:
                candidate_root = Path(entry.library_path)
                if candidate_root.exists():
                    job_root = candidate_root
                else:
                    job_root = pipeline_root
            else:
                job_root = pipeline_root

    if not job_root.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job_root


async def _load_sentence_image_info(
    *,
    sentence_number: int,
    job_root: Path,
) -> tuple[Mapping[str, Any], Mapping[str, Any], dict[str, Any]]:
    loader = MetadataLoader(job_root)
    chunk = _resolve_chunk_for_sentence(loader, sentence_number)
    if not isinstance(chunk, Mapping):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sentence chunk not found")
    metadata_path = chunk.get("metadata_path")
    if not isinstance(metadata_path, str) or not metadata_path.strip():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk metadata is unavailable")
    chunk_path = _resolve_job_path(job_root, metadata_path)
    try:
        chunk_payload = await run_in_threadpool(lambda: json.loads(chunk_path.read_text(encoding="utf-8")))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk metadata is unavailable") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to read chunk metadata") from exc
    sentences = chunk_payload.get("sentences") if isinstance(chunk_payload, Mapping) else None
    if not isinstance(sentences, list):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sentence metadata is unavailable")
    sentence_entry: dict[str, Any] | None = None
    for entry in sentences:
        if not isinstance(entry, Mapping):
            continue
        resolved = _resolve_sentence_number(entry)
        if resolved == sentence_number:
            sentence_entry = dict(entry)
            break
    if sentence_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sentence metadata is unavailable")
    return chunk, chunk_payload, sentence_entry


@router.get(
    "/jobs/{job_id}/media/images/sentences/batch",
    response_model=SentenceImageInfoBatchResponse,
)
async def get_sentence_image_info_batch(
    job_id: str,
    sentence_numbers: List[str] = Query(..., alias="sentence_numbers"),
    *,
    job_manager=Depends(get_pipeline_job_manager),
    locator: FileLocator = Depends(get_file_locator),
    library_repository: LibraryRepository = Depends(get_library_repository),
    request_user: RequestUserContext = Depends(get_request_user),
) -> SentenceImageInfoBatchResponse:
    """Return stored prompt/path metadata for multiple sentence images."""

    requested = _parse_sentence_numbers(sentence_numbers)
    if not requested:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No sentence numbers provided")
    if len(requested) > MAX_SENTENCE_IMAGE_BATCH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many sentence numbers (max {MAX_SENTENCE_IMAGE_BATCH})",
        )

    job_root = _resolve_job_root(
        job_id=job_id,
        locator=locator,
        library_repository=library_repository,
        request_user=request_user,
        job_manager=job_manager,
    )

    def _load_batch() -> Tuple[List[SentenceImageInfoResponse], List[int]]:
        loader = MetadataLoader(job_root)
        payload_cache: Dict[str, Mapping[str, Any]] = {}
        items: List[SentenceImageInfoResponse] = []
        missing: List[int] = []

        for sentence_number in requested:
            chunk = _resolve_chunk_for_sentence(loader, sentence_number)
            if not isinstance(chunk, Mapping):
                missing.append(sentence_number)
                continue
            metadata_path = chunk.get("metadata_path")
            if not isinstance(metadata_path, str) or not metadata_path.strip():
                missing.append(sentence_number)
                continue
            key = metadata_path.strip()
            payload = payload_cache.get(key)
            if payload is None:
                loaded = _read_chunk_payload(job_root=job_root, metadata_path=key)
                if loaded is None:
                    missing.append(sentence_number)
                    continue
                payload_cache[key] = loaded
                payload = loaded
            entry = _find_sentence_entry(chunk_payload=payload, sentence_number=sentence_number)
            if not isinstance(entry, Mapping):
                missing.append(sentence_number)
                continue
            items.append(
                _build_sentence_image_info_response(
                    job_id=job_id,
                    sentence_number=sentence_number,
                    chunk=chunk,
                    sentence_entry=entry,
                )
            )

        return items, missing

    start = time.perf_counter()
    items, missing = await run_in_threadpool(_load_batch)
    duration_ms = (time.perf_counter() - start) * 1000
    if duration_ms >= 250:
        LOGGER.info(
            "Sentence image batch lookup job_id=%s count=%s missing=%s duration_ms=%.1f",
            job_id,
            len(requested),
            len(missing),
            duration_ms,
        )
    else:
        LOGGER.debug(
            "Sentence image batch lookup job_id=%s count=%s missing=%s duration_ms=%.1f",
            job_id,
            len(requested),
            len(missing),
            duration_ms,
        )

    return SentenceImageInfoBatchResponse(job_id=job_id, items=items, missing=missing)


@router.get(
    "/jobs/{job_id}/media/images/sentences/{sentence_number}",
    response_model=SentenceImageInfoResponse,
)
async def get_sentence_image_info(
    job_id: str,
    sentence_number: int,
    *,
    job_manager=Depends(get_pipeline_job_manager),
    locator: FileLocator = Depends(get_file_locator),
    library_repository: LibraryRepository = Depends(get_library_repository),
    request_user: RequestUserContext = Depends(get_request_user),
) -> SentenceImageInfoResponse:
    """Return the stored prompt/path metadata for a sentence image."""

    start = time.perf_counter()
    job_root = _resolve_job_root(
        job_id=job_id,
        locator=locator,
        library_repository=library_repository,
        request_user=request_user,
        job_manager=job_manager,
    )

    chunk, _chunk_payload, sentence_entry = await _load_sentence_image_info(
        sentence_number=sentence_number,
        job_root=job_root,
    )
    response = _build_sentence_image_info_response(
        job_id=job_id,
        sentence_number=sentence_number,
        chunk=chunk,
        sentence_entry=sentence_entry,
    )
    duration_ms = (time.perf_counter() - start) * 1000
    if duration_ms >= 250:
        LOGGER.info(
            "Sentence image lookup job_id=%s sentence=%s duration_ms=%.1f",
            job_id,
            sentence_number,
            duration_ms,
        )
    else:
        LOGGER.debug(
            "Sentence image lookup job_id=%s sentence=%s duration_ms=%.1f",
            job_id,
            sentence_number,
            duration_ms,
        )
    return response


@router.post(
    "/jobs/{job_id}/media/images/sentences/{sentence_number}/regenerate",
    response_model=SentenceImageRegenerateResponse,
)
async def regenerate_sentence_image(
    job_id: str,
    sentence_number: int,
    payload: SentenceImageRegenerateRequest,
    *,
    job_manager=Depends(get_pipeline_job_manager),
    locator: FileLocator = Depends(get_file_locator),
    library_repository: LibraryRepository = Depends(get_library_repository),
    request_user: RequestUserContext = Depends(get_request_user),
) -> SentenceImageRegenerateResponse:
    """Regenerate and overwrite the stored sentence image using supplied prompt/settings."""

    job_root = _resolve_job_root(
        job_id=job_id,
        locator=locator,
        library_repository=library_repository,
        request_user=request_user,
        job_manager=job_manager,
    )
    style_template = _resolve_job_image_style_template(job_root)

    config = cfg.load_configuration(verbose=False)
    base_urls = normalize_drawthings_base_urls(
        base_url=config.get("image_api_base_url"),
        base_urls=config.get("image_api_base_urls"),
    )
    if not base_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_api_base_url(s) are not configured",
        )
    timeout_seconds = max(
        1.0,
        _coerce_float_default(config.get("image_api_timeout_seconds"), 180.0),
    )
    settings = _resolve_image_settings(config, payload)

    chunk, chunk_payload, sentence_entry = await _load_sentence_image_info(
        sentence_number=sentence_number,
        job_root=job_root,
    )
    range_fragment = chunk.get("range_fragment") or chunk.get("rangeFragment")
    range_fragment = (
        range_fragment.strip()
        if isinstance(range_fragment, str) and range_fragment.strip()
        else None
    )

    stored_prompt, stored_negative = _extract_sentence_image(sentence_entry)
    stored_image_path = _extract_sentence_image_path(sentence_entry)
    relative_path = None
    if isinstance(stored_image_path, str) and stored_image_path.strip():
        normalized = stored_image_path.strip().replace("\\", "/").lstrip("/")
        media_index = normalized.find("media/")
        if media_index >= 0:
            normalized = normalized[media_index:]
        relative_path = normalized or None
    if not relative_path:
        if not range_fragment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk range fragment missing")
        relative_path = _resolve_image_relative_path(range_fragment, sentence_number)

    prompt = _normalise_prompt(payload.prompt) or _normalise_prompt(stored_prompt)
    negative_prompt = _normalise_negative_prompt(payload.negative_prompt) or _normalise_negative_prompt(stored_negative)

    use_llm_prompt = bool(payload.use_llm_prompt)
    context_count = payload.context_sentences
    if not isinstance(context_count, int):
        context_count = _coerce_int_default(config.get("image_prompt_context_sentences"), 2)
    context_count = max(0, min(int(context_count), 50))

    if use_llm_prompt or not prompt:
        loader = MetadataLoader(job_root)
        batch_start, batch_end = _extract_sentence_image_batch_range(sentence_entry)
        if batch_start is not None and batch_end is not None:
            batch_texts = await run_in_threadpool(
                _collect_sentence_range_texts,
                loader=loader,
                job_root=job_root,
                start_sentence=batch_start,
                end_sentence=batch_end,
            )
            plan = await run_in_threadpool(
                sentence_batches_to_diffusion_prompt_plan,
                [batch_texts],
            )
            diffusion = plan.prompts[0] if plan.prompts else None
            if diffusion is None:
                sentence_text = _extract_sentence_text(sentence_entry) or ""
                diffusion = await run_in_threadpool(sentence_to_diffusion_prompt, sentence_text, context_sentences=())
        else:
            sentence_text = _extract_sentence_text(sentence_entry) or ""
            context_texts = await run_in_threadpool(
                _collect_context_sentence_texts,
                loader=loader,
                job_root=job_root,
                sentence_number=sentence_number,
                count=context_count,
            )
            diffusion = await run_in_threadpool(
                sentence_to_diffusion_prompt,
                sentence_text,
                context_sentences=context_texts,
            )
        if use_llm_prompt or not prompt:
            prompt = (diffusion.prompt or "").strip() or (_extract_sentence_text(sentence_entry) or "").strip()
        if not negative_prompt:
            negative_prompt = (diffusion.negative_prompt or "").strip()

    prompt_full = _ensure_prompt_suffix(prompt, style_template=style_template)
    negative_full = _ensure_negative_suffix(negative_prompt, style_template=style_template)

    client, _available_urls, unavailable_urls = resolve_drawthings_client(
        base_urls=base_urls,
        timeout_seconds=timeout_seconds,
    )
    if unavailable_urls:
        LOGGER.warning(
            "DrawThings endpoints unavailable: %s",
            ", ".join(unavailable_urls),
            extra={
                "event": "webapi.image.unavailable",
                "attributes": {"unavailable": unavailable_urls},
                "console_suppress": True,
            },
        )
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="DrawThings endpoints are unavailable",
        )
    blank_detection_enabled = _coerce_bool_default(
        config.get("image_blank_detection_enabled"), False
    )
    max_image_retries = 2
    try:
        seed_base = int(settings["seed"])
    except (TypeError, ValueError):
        seed_base = 0

    seed_used = seed_base
    final_bytes: bytes | None = None

    def _convert_and_check(payload: bytes) -> tuple[bytes, bool]:
        import io

        from PIL import Image, ImageStat

        with Image.open(io.BytesIO(payload)) as loaded:
            converted = loaded.convert("RGB")
            is_blank = False
            if blank_detection_enabled:
                stats = ImageStat.Stat(converted.convert("L"))
                mean = float(stats.mean[0]) if stats.mean else 0.0
                stddev = float(stats.stddev[0]) if getattr(stats, "stddev", None) else 0.0
                is_blank = stddev < 2.0 and (mean < 8.0 or mean > 247.0)
            output = io.BytesIO()
            converted.save(output, format="PNG")
            return output.getvalue(), is_blank

    for attempt in range(max_image_retries + 1):
        seed_used = seed_base + attempt * 9973
        request = DrawThingsImageRequest(
            prompt=prompt_full,
            negative_prompt=negative_full,
            width=int(settings["width"]),
            height=int(settings["height"]),
            steps=int(settings["steps"]),
            cfg_scale=float(settings["cfg_scale"]),
            sampler_name=settings["sampler_name"],
            seed=seed_used,
        )

        try:
            image_bytes, _api_payload = await run_in_threadpool(client.txt2img, request)
        except DrawThingsError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"DrawThings request failed: {exc}",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Image generation failed",
            ) from exc

        try:
            converted_bytes, is_blank = await run_in_threadpool(_convert_and_check, image_bytes)
        except Exception:
            if attempt < max_image_retries:
                continue
            final_bytes = image_bytes
            break

        if blank_detection_enabled and is_blank and attempt < max_image_retries:
            continue

        final_bytes = converted_bytes
        break

    if final_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image generation failed",
        )

    image_path = job_root / relative_path
    await run_in_threadpool(lambda: (image_path.parent.mkdir(parents=True, exist_ok=True), image_path.write_bytes(final_bytes)))

    def _update_job_metadata() -> None:
        loader = MetadataLoader(job_root)
        for chunk_meta in loader.iter_chunks():
            metadata_path = chunk_meta.get("metadata_path")
            if not isinstance(metadata_path, str) or not metadata_path.strip():
                continue
            chunk_path = _resolve_job_path(job_root, metadata_path.strip())
            try:
                raw = json.loads(chunk_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue
            sentences_payload = raw.get("sentences")
            if not isinstance(sentences_payload, list):
                continue
            updated = False
            for sentence in sentences_payload:
                if not isinstance(sentence, dict):
                    continue
                existing_path = _extract_sentence_image_path(sentence)
                if not existing_path:
                    continue
                if existing_path.replace("\\", "/").lstrip("/") != relative_path:
                    continue
                previous_image = sentence.get("image")
                preserved: dict[str, Any] = {}
                if isinstance(previous_image, Mapping):
                    preserved = {
                        key: value
                        for key, value in previous_image.items()
                        if key not in {"path", "prompt", "negative_prompt", "negativePrompt"}
                    }
                image_payload: dict[str, Any] = {**preserved, "path": relative_path, "prompt": prompt_full}
                if negative_full:
                    image_payload["negative_prompt"] = negative_full
                sentence["image"] = image_payload
                sentence["image_path"] = relative_path
                sentence["imagePath"] = relative_path
                updated = True
            if updated:
                _atomic_write_json(chunk_path, raw)

    await run_in_threadpool(_update_job_metadata)

    return SentenceImageRegenerateResponse(
        job_id=job_id,
        sentence_number=sentence_number,
        range_fragment=range_fragment,
        relative_path=relative_path,
        prompt=prompt_full,
        negative_prompt=negative_full,
        width=int(settings["width"]),
        height=int(settings["height"]),
        steps=int(settings["steps"]),
        cfg_scale=float(settings["cfg_scale"]),
        sampler_name=settings["sampler_name"],
        seed=seed_used,
    )


def normalize_timings(
    tokens: Sequence[Mapping[str, Any]],
    start_offset: float = 0.0,
    *,
    lane: str = "tran",
    seg_prefix: str = "seg",
) -> list[dict[str, Any]]:
    """Normalise timing tokens into the frontend payload format."""

    norm: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        raw_start = float(token.get("start", 0.0))
        raw_end = float(token.get("end", raw_start))
        t0 = round(raw_start - start_offset, 3)
        t1 = round(raw_end - start_offset, 3)
        norm.append(
            {
                "id": f"{seg_prefix}_{index}",
                "text": token.get("text", ""),
                "t0": max(t0, 0.0),
                "t1": max(t1, 0.0),
                "lane": lane,
                "segId": seg_prefix,
            }
        )
    return norm


def smooth_token_edges(
    tokens: Sequence[Mapping[str, Any]], min_len: float = 0.04
) -> list[dict[str, Any]]:
    """Ensure every token spans at least ``min_len`` seconds and clamps overlaps."""

    smoothed: list[dict[str, Any]] = []
    total = len(tokens)
    for index, token in enumerate(tokens):
        mutable = dict(token)
        start_val = float(mutable.get("start", 0.0))
        end_val = float(mutable.get("end", start_val))
        duration = end_val - start_val
        if duration < min_len:
            if index + 1 < total:
                next_start = float(tokens[index + 1].get("start", end_val))
            else:
                next_start = end_val + min_len
            end_val = min(next_start, start_val + min_len)
            mutable["end"] = end_val
        smoothed.append(mutable)
    return smoothed


def _iter_sentence_payloads(payload: Any) -> Iterator[Mapping[str, Any]]:
    """Yield flattened sentence entries from chunk payloads."""

    if isinstance(payload, Mapping):
        sentences = payload.get("sentences")
        if isinstance(sentences, Sequence) and not isinstance(sentences, (str, bytes)):
            for entry in sentences:
                yield from _iter_sentence_payloads(entry)
            return
        yield payload
        return
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        for entry in payload:
            yield from _iter_sentence_payloads(entry)


def _extract_highlighting_policy(entry: Mapping[str, Any]) -> Optional[str]:
    """Return the highlighting policy encoded on a sentence entry."""

    summary = entry.get("highlighting_summary")
    if isinstance(summary, Mapping):
        policy = summary.get("policy")
        if isinstance(policy, str) and policy.strip():
            return policy.strip()
    candidate = entry.get("highlighting_policy") or entry.get("alignment_policy")
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return None


def _extract_policy_from_timing_tracks(
    payload: Mapping[str, Any],
) -> tuple[Optional[str], bool]:
    tracks = payload.get("timingTracks") or payload.get("timing_tracks")
    if not isinstance(tracks, Mapping):
        tracks = None
    fallback: Optional[str] = None
    estimated = False
    top_level = payload.get("highlighting_policy")
    if isinstance(top_level, str) and top_level.strip():
        normalized = top_level.strip()
        if _is_estimated_policy(normalized):
            return normalized, True
        fallback = normalized
    if not isinstance(tracks, Mapping):
        return fallback, estimated
    for entries in tracks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            policy = entry.get("policy")
            if not isinstance(policy, str):
                continue
            normalized = policy.strip()
            if not normalized:
                continue
            if _is_estimated_policy(normalized):
                return normalized, True
            if fallback is None:
                fallback = normalized
    return fallback, estimated


def _is_estimated_policy(policy: Optional[str]) -> bool:
    if not isinstance(policy, str):
        return False
    normalized = policy.strip().lower()
    return normalized.startswith("estimated")


def _probe_highlighting_policy(
    metadata_root: Path,
    default_policy: Optional[str],
) -> tuple[Optional[str], bool]:
    """Resolve the highlighting policy and whether estimated timings exist."""

    normalized_default = None
    if isinstance(default_policy, str) and default_policy.strip():
        normalized_default = default_policy.strip()
    estimated_detected = _is_estimated_policy(normalized_default)
    fallback_policy: Optional[str] = normalized_default

    if metadata_root.exists():
        for chunk_path in sorted(metadata_root.glob("chunk_*.json")):
            try:
                with chunk_path.open("r", encoding="utf-8") as handle:
                    chunk_payload = json.load(handle)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(chunk_payload, Mapping):
                policy, estimated = _extract_policy_from_timing_tracks(chunk_payload)
                if policy:
                    if estimated:
                        return policy, True
                    if fallback_policy is None:
                        fallback_policy = policy
                estimated_detected = estimated_detected or estimated
            for entry in _iter_sentence_payloads(chunk_payload):
                if isinstance(entry, Mapping):
                    policy = _extract_highlighting_policy(entry)
                    if policy:
                        normalized = policy.strip()
                        if _is_estimated_policy(normalized):
                            return normalized, True
                        if fallback_policy is None:
                            fallback_policy = normalized
    if fallback_policy is not None:
        estimated_detected = estimated_detected or _is_estimated_policy(fallback_policy)
    return fallback_policy, estimated_detected


@jobs_timing_router.get("/{job_id}/timing", response_class=JSONResponse)
async def get_job_timing(
    job_id: str,
    *,
    job_manager = Depends(get_pipeline_job_manager),
    locator: FileLocator = Depends(get_file_locator),
    library_repository: LibraryRepository = Depends(get_library_repository),
    request_user: RequestUserContext = Depends(get_request_user),
) -> JSONResponse:
    """Return flattened per-word timing data for ``job_id``."""

    job_root: Path
    result_payload: Mapping[str, Any] = {}

    try:
        job: PipelineJob = job_manager.get(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:
        entry = library_repository.get_entry_by_id(job_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
        job_root = Path(entry.library_path)
        if not job_root.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
        loader = MetadataLoader(job_root)
        try:
            manifest = await run_in_threadpool(loader.load_manifest)
        except FileNotFoundError as load_exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from load_exc
        except Exception as load_exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to load job metadata") from load_exc
        result_value = manifest.get("result") if isinstance(manifest, Mapping) else None
        if isinstance(result_value, Mapping):
            result_payload = dict(result_value)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    else:
        job_root = locator.resolve_path(job_id)
        if not (job_root / "metadata" / "job.json").exists():
            entry = library_repository.get_entry_by_id(job_id)
            if entry is not None:
                candidate_root = Path(entry.library_path)
                if candidate_root.exists():
                    job_root = candidate_root
        result_payload = job.result_payload if isinstance(job.result_payload, Mapping) else {}

    timing_tracks = result_payload.get("timing_tracks") if isinstance(result_payload, Mapping) else None
    if not isinstance(timing_tracks, Mapping):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No timing track available")

    requested_tracks = {
        key: path
        for key, path in timing_tracks.items()
        if key in {"mix", "translation", "original"} and isinstance(path, str) and path.strip()
    }
    if not requested_tracks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No timing track available")

    resolved_paths: Dict[str, Path] = {}
    for track_name, rel_path in requested_tracks.items():
        try:
            abs_path = _resolve_job_path(job_root, rel_path)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timing index missing",
            ) from exc
        if not abs_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timing index missing")
        resolved_paths[track_name] = abs_path

    data_cache: Dict[Path, Any] = {}
    resolved_segments: Dict[str, List[Any]] = {"mix": [], "translation": [], "original": []}
    for track_name, abs_path in resolved_paths.items():
        if abs_path not in data_cache:
            try:
                with abs_path.open("r", encoding="utf-8") as handle:
                    data_cache[abs_path] = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Timing index missing",
                ) from exc
        payload = data_cache[abs_path]
        segments: list[Any]
        if isinstance(payload, Mapping):
            track_entries = payload.get(track_name)
            if isinstance(track_entries, list):
                segments = track_entries
            elif track_name == "translation" and isinstance(payload.get("segments"), list):
                segments = payload["segments"]  # legacy
            elif track_name == "translation" and isinstance(payload.get("translation"), list):
                segments = payload["translation"]
            else:
                segments = []
        elif isinstance(payload, list):
            segments = payload
        else:
            segments = []
        resolved_segments[track_name] = segments

    unique_paths = sorted({path for path in resolved_paths.values()})
    try:
        stats = [path.stat() for path in unique_paths]
        digest = "-".join(f"{st.st_mtime_ns:x}-{st.st_size:x}" for st in stats)
        etag = f'W/"{digest}"'
    except OSError:
        fallback_count = sum(len(resolved_segments.get(name, [])) for name in resolved_segments)
        etag = f'W/"{job_id}-{fallback_count}"'

    playback_meta = result_payload.get("timing_meta") if isinstance(result_payload, Mapping) else None
    playback_rate = 1.0
    if isinstance(playback_meta, Mapping):
        try:
            playback_rate = float(playback_meta.get("playbackRate", 1.0))
        except (TypeError, ValueError):
            playback_rate = 1.0

    highlighting_policy, has_estimated_segments = _probe_highlighting_policy(
        job_root / "metadata",
        result_payload.get("highlighting_policy") if isinstance(result_payload, Mapping) else None,
    )

    def _collect_audio_availability() -> Dict[str, Dict[str, Any]]:
        audio_summary: Dict[str, Dict[str, Any]] = {}
        generated_payload = result_payload.get("generated_files") if isinstance(result_payload, Mapping) else None
        chunk_audio_keys: set[str] = set()
        if isinstance(generated_payload, Mapping):
            chunks = generated_payload.get("chunks")
            if isinstance(chunks, list):
                for chunk in chunks:
                    if not isinstance(chunk, Mapping):
                        continue
                    tracks = chunk.get("audio_tracks") or chunk.get("audioTracks")
                    if not isinstance(tracks, Mapping):
                        continue
                    for raw_key, raw_value in tracks.items():
                        if not isinstance(raw_key, str):
                            continue
                        key = raw_key.strip()
                        if not key:
                            continue
                        if key == "trans":
                            key = "translation"
                        chunk_audio_keys.add(key)
        audio_summary["orig_trans"] = {
            "track": "mix",
            "available": "orig_trans" in chunk_audio_keys,
        }
        audio_summary["orig"] = {
            "track": "original",
            "available": "orig" in chunk_audio_keys or "original" in chunk_audio_keys,
        }
        audio_summary["translation"] = {
            "track": "translation",
            "available": "translation" in chunk_audio_keys or "trans" in chunk_audio_keys,
        }
        return audio_summary

    headers = {
        "Cache-Control": "public, max-age=60",
        "ETag": etag,
    }
    tracks_payload: Dict[str, Any] = {}
    for track_name, segments in resolved_segments.items():
        if not segments:
            continue
        tracks_payload[track_name] = {
            "track": track_name,
            "segments": segments,
            "playback_rate": playback_rate,
        }
    return JSONResponse(
        content={
            "job_id": job_id,
            "tracks": tracks_payload,
            "audio": _collect_audio_availability(),
            "highlighting_policy": highlighting_policy,
            "has_estimated_segments": has_estimated_segments,
        },
        headers=headers,
    )

def _resolve_media_path(
    job_id: str,
    entry: Mapping[str, Any],
    locator: FileLocator,
    job_root: Path,
) -> tuple[Optional[Path], Optional[str]]:
    """Return the absolute and relative paths for a generated media entry."""

    relative_value = entry.get("relative_path")
    resolved_path: Optional[Path] = None
    relative_path: Optional[str] = None

    if relative_value:
        relative_path = Path(str(relative_value)).as_posix()
        try:
            resolved_path = locator.resolve_path(job_id, relative_path)
        except ValueError:
            resolved_path = None

    path_value = entry.get("path")
    if resolved_path is None and path_value:
        candidate = Path(str(path_value))
        if candidate.is_absolute():
            resolved_path = candidate
            try:
                relative_candidate = candidate.relative_to(job_root)
            except ValueError:
                pass
            else:
                relative_path = relative_candidate.as_posix()
        else:
            try:
                resolved_path = locator.resolve_path(job_id, candidate)
            except ValueError:
                resolved_path = None
            else:
                relative_path = candidate.as_posix()

    return resolved_path, relative_path


def _coerce_int(value: Any) -> Optional[int]:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number


def _build_media_file(
    job_id: str,
    entry: Mapping[str, Any],
    locator: FileLocator,
    job_root: Path,
    *,
    source: str,
) -> tuple[Optional[PipelineMediaFile], Optional[str], tuple[str, str]]:
    file_type_raw = entry.get("type") or "unknown"
    file_type = str(file_type_raw).lower() or "unknown"

    resolved_path, relative_path = _resolve_media_path(job_id, entry, locator, job_root)

    url_value = entry.get("url")
    url: Optional[str] = url_value if isinstance(url_value, str) else None
    if not url and relative_path:
        try:
            url = locator.resolve_url(job_id, relative_path)
        except ValueError:
            url = None

    size: Optional[int] = None
    updated_at: Optional[datetime] = None
    if resolved_path is not None and resolved_path.exists():
        try:
            stat_result = resolved_path.stat()
        except OSError:
            pass
        else:
            size = int(stat_result.st_size)
            updated_at = datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc)

    name_value = entry.get("name")
    name = str(name_value) if name_value else None
    if not name:
        if resolved_path is not None:
            name = resolved_path.name
        elif relative_path:
            name = Path(relative_path).name
        else:
            path_value = entry.get("path")
            if path_value:
                name = Path(str(path_value)).name
    if not name:
        name = "media" if file_type == "unknown" else file_type

    path_value = entry.get("path") if isinstance(entry.get("path"), str) else None

    chunk_id_value = entry.get("chunk_id")
    chunk_id = str(chunk_id_value) if chunk_id_value not in {None, ""} else None
    range_fragment_value = entry.get("range_fragment")
    range_fragment = str(range_fragment_value) if range_fragment_value not in {None, ""} else None
    start_sentence = _coerce_int(entry.get("start_sentence"))
    end_sentence = _coerce_int(entry.get("end_sentence"))

    record = PipelineMediaFile(
        name=name,
        url=url,
        size=size,
        updated_at=updated_at,
        source=source,
        relative_path=relative_path,
        path=path_value,
        chunk_id=chunk_id,
        range_fragment=range_fragment,
        start_sentence=start_sentence,
        end_sentence=end_sentence,
        type=file_type,
    )
    signature_key = path_value or relative_path or url or name
    signature = (signature_key or name, file_type)
    return record, file_type, signature


def _serialize_media_entries(
    job_id: str,
    generated_files: Optional[Mapping[str, Any]],
    locator: FileLocator,
    *,
    source: str,
    metadata_loader: Optional[MetadataLoader] = None,
) -> tuple[Dict[str, List[PipelineMediaFile]], List[PipelineMediaChunk], bool]:
    """Return serialized media metadata grouped by type and chunk."""

    media_map: Dict[str, List[PipelineMediaFile]] = {}
    chunk_records: List[PipelineMediaChunk] = []
    complete = False

    if not isinstance(generated_files, Mapping):
        return media_map, chunk_records, complete

    job_root = locator.resolve_path(job_id)
    seen: set[tuple[str, str]] = set()

    loader = metadata_loader
    loader_attempted = metadata_loader is not None

    def _resolve_loader() -> Optional[MetadataLoader]:
        nonlocal loader, loader_attempted
        if loader is not None:
            return loader
        if loader_attempted:
            return None
        loader_attempted = True
        manifest_path = job_root / "metadata" / "job.json"
        if not manifest_path.exists():
            return None
        try:
            loader = MetadataLoader(job_root)
        except Exception:  # pragma: no cover - defensive logging
            loader = None
        return loader

    chunks_section = generated_files.get("chunks")
    if isinstance(chunks_section, list):
        for chunk in chunks_section:
            if not isinstance(chunk, Mapping):
                continue
            chunk_files: List[PipelineMediaFile] = []
            files_raw = chunk.get("files")
            if not isinstance(files_raw, list):
                files_raw = []
            for file_entry in files_raw:
                if not isinstance(file_entry, Mapping):
                    continue
                enriched_entry = dict(file_entry)
                enriched_entry.setdefault("chunk_id", chunk.get("chunk_id"))
                enriched_entry.setdefault("range_fragment", chunk.get("range_fragment"))
                enriched_entry.setdefault("start_sentence", chunk.get("start_sentence"))
                enriched_entry.setdefault("end_sentence", chunk.get("end_sentence"))
                record, file_type, signature = _build_media_file(
                    job_id,
                    enriched_entry,
                    locator,
                    job_root,
                    source=source,
                )
                if record is None or file_type is None:
                    continue
                if signature in seen:
                    chunk_files.append(record)
                    continue
                seen.add(signature)
                media_map.setdefault(file_type, []).append(record)
                chunk_files.append(record)
            if not chunk_files:
                continue

            summary: Mapping[str, Any] = chunk
            active_loader = _resolve_loader()
            if active_loader is not None:
                try:
                    summary = active_loader.load_chunk(chunk, include_sentences=False)
                except Exception:  # pragma: no cover - defensive logging
                    summary = chunk

            metadata_path = summary.get("metadata_path")
            metadata_url = summary.get("metadata_url")
            sentence_count = _coerce_int(summary.get("sentence_count"))

            sentences_payload: List[Any] = []
            if isinstance(metadata_path, str) and metadata_path.strip():
                sentences_payload = []
            else:
                if active_loader is not None:
                    sentences_payload = active_loader.load_chunk_sentences(chunk)
                else:
                    inline_sentences = summary.get("sentences") or chunk.get("sentences")
                    if isinstance(inline_sentences, list):
                        sentences_payload = copy.deepcopy(inline_sentences)
                if sentence_count is None:
                    sentence_count = len(sentences_payload)

            audio_tracks_payload: Dict[str, Dict[str, Any]] = {}

            def _register_track(raw_key: Any, raw_value: Any) -> None:
                if not isinstance(raw_key, str):
                    return
                key = raw_key.strip()
                if not key:
                    return

                entry: Dict[str, Any] = {}
                if isinstance(raw_value, str):
                    value = raw_value.strip()
                    if not value:
                        return
                    entry["path"] = value
                elif isinstance(raw_value, Mapping):
                    path_value = raw_value.get("path")
                    url_value = raw_value.get("url")
                    duration_value = raw_value.get("duration")
                    sample_rate_value = raw_value.get("sampleRate")
                    if isinstance(path_value, str) and path_value.strip():
                        entry["path"] = path_value.strip()
                    if isinstance(url_value, str) and url_value.strip():
                        entry["url"] = url_value.strip()
                    try:
                        entry["duration"] = round(float(duration_value), 6)
                    except (TypeError, ValueError):
                        pass
                    try:
                        entry["sampleRate"] = int(sample_rate_value)
                    except (TypeError, ValueError):
                        pass
                if not entry:
                    return

                existing = audio_tracks_payload.get(key, {})
                merged = dict(existing)
                merged.update(entry)
                audio_tracks_payload[key] = merged

            def _ingest_tracks(candidate: Any) -> None:
                if isinstance(candidate, Mapping):
                    for track_key, track_value in candidate.items():
                        _register_track(track_key, track_value)
                elif isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
                    for entry in candidate:
                        if not isinstance(entry, Mapping):
                            continue
                        track_key = entry.get("key") or entry.get("kind")
                        track_value = entry.get("url") or entry.get("path")
                        if track_value is None:
                            track_value = entry.get("source")
                        _register_track(track_key, track_value)

            _ingest_tracks(summary.get("audio_tracks"))
            _ingest_tracks(summary.get("audioTracks"))
            _ingest_tracks(chunk.get("audio_tracks"))
            _ingest_tracks(chunk.get("audioTracks"))

            chunk_records.append(
                PipelineMediaChunk(
                    chunk_id=str(summary.get("chunk_id")) if summary.get("chunk_id") else None,
                    range_fragment=str(summary.get("range_fragment"))
                    if summary.get("range_fragment")
                    else None,
                    start_sentence=_coerce_int(summary.get("start_sentence")),
                    end_sentence=_coerce_int(summary.get("end_sentence")),
                    files=chunk_files,
                    sentences=sentences_payload,
                    metadata_path=metadata_path if isinstance(metadata_path, str) else None,
                    metadata_url=metadata_url if isinstance(metadata_url, str) else None,
                    sentence_count=sentence_count,
                    audio_tracks=audio_tracks_payload,
                )
            )

    files_section = generated_files.get("files")
    if isinstance(files_section, list):
        for entry in files_section:
            if not isinstance(entry, Mapping):
                continue
            record, file_type, signature = _build_media_file(
                job_id,
                entry,
                locator,
                job_root,
                source=source,
            )
            if record is None or file_type is None:
                continue
            if signature in seen:
                continue
            seen.add(signature)
            media_map.setdefault(file_type, []).append(record)

    complete_flag = generated_files.get("complete")
    complete = bool(complete_flag) if isinstance(complete_flag, bool) else False

    return media_map, chunk_records, complete


@router.get("/jobs/{job_id}/media", response_model=PipelineMediaResponse)
async def get_job_media(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return generated media metadata for a job."""

    try:
        job = pipeline_service.get_job(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:  # pragma: no cover - FastAPI handles error path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    generated_payload: Optional[Mapping[str, Any]] = None
    if job.media_completed and job.generated_files is not None:
        generated_payload = job.generated_files
    elif job.tracker is not None:
        generated_payload = job.tracker.get_generated_files()
    elif job.generated_files is not None:
        generated_payload = job.generated_files

    media_entries, chunk_entries, complete = _serialize_media_entries(
        job.job_id,
        generated_payload,
        file_locator,
        source="completed",
    )
    return PipelineMediaResponse(media=media_entries, chunks=chunk_entries, complete=complete)


@router.get("/jobs/{job_id}/media/live", response_model=PipelineMediaResponse)
async def get_job_media_live(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return live generated media metadata from the active progress tracker."""

    try:
        job = pipeline_service.get_job(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:  # pragma: no cover - FastAPI handles error path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    generated_payload: Optional[Mapping[str, Any]] = None
    if job.media_completed and job.generated_files is not None:
        generated_payload = job.generated_files
    elif job.tracker is not None:
        generated_payload = job.tracker.get_generated_files()
    elif job.generated_files is not None:
        generated_payload = job.generated_files

    media_entries, chunk_entries, complete = _serialize_media_entries(
        job.job_id,
        generated_payload,
        file_locator,
        source="live",
    )
    return PipelineMediaResponse(media=media_entries, chunks=chunk_entries, complete=complete)


class _RangeParseError(Exception):
    """Raised when the supplied Range header cannot be satisfied."""


def _parse_byte_range(range_value: str, file_size: int) -> Tuple[int, int]:
    """Return the inclusive byte range requested by ``range_value``.

    ``range_value`` must follow the ``bytes=start-end`` syntax. Only a single range is
    supported and the resulting indices are clamped to the available file size. A
    :class:`_RangeParseError` is raised when the header is malformed or does not
    overlap the file contents.
    """

    if file_size <= 0:
        raise _RangeParseError

    header = range_value.strip()
    if not header.lower().startswith("bytes="):
        raise _RangeParseError

    raw_spec = header[len("bytes=") :].strip()
    if "," in raw_spec:
        raise _RangeParseError

    if "-" not in raw_spec:
        raise _RangeParseError

    start_token, end_token = raw_spec.split("-", 1)

    if not start_token:
        # suffix-byte-range-spec: bytes=-N
        if not end_token.isdigit():
            raise _RangeParseError
        length = int(end_token)
        if length <= 0:
            raise _RangeParseError
        start = max(file_size - length, 0)
        end = file_size - 1
    else:
        if not start_token.isdigit():
            raise _RangeParseError
        start = int(start_token)
        if start >= file_size:
            raise _RangeParseError

        if end_token:
            if not end_token.isdigit():
                raise _RangeParseError
            end = int(end_token)
            if end < start:
                raise _RangeParseError
            end = min(end, file_size - 1)
        else:
            end = file_size - 1

    return start, end


def _iter_file_chunks(path: Path, start: int, end: int) -> Iterator[bytes]:
    """Yield chunks from ``path`` between ``start`` and ``end`` (inclusive)."""

    chunk_size = 1 << 16
    total = max(end - start + 1, 0)
    if total <= 0:
        return

    with path.open("rb") as stream:
        stream.seek(start)
        remaining = total
        while remaining > 0:
            chunk = stream.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def _stream_local_file(resolved_path: Path, range_header: str | None = None) -> StreamingResponse:
    try:
        stat_result = resolved_path.stat()
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc

    file_size = int(stat_result.st_size)
    suffix = resolved_path.suffix.lower()
    media_type = mimetypes.guess_type(resolved_path.name)[0]
    if not media_type:
        if suffix == ".vtt":
            media_type = "text/vtt"
        elif suffix == ".srt":
            media_type = "text/x-srt"
        elif suffix == ".ass":
            media_type = "text/plain"
        elif suffix in {".m4v", ".mp4"}:
            media_type = "video/mp4"

    def _should_inline(content_type: str | None) -> bool:
        if not content_type:
            return False
        if content_type.startswith(("video/", "audio/", "image/")):
            return True
        if content_type in {"text/vtt"}:
            return True
        return False

    if range_header and "," in range_header:
        # Some clients (notably iOS) may request multiple ranges. We only support a single
        # contiguous range, so fall back to streaming the full payload instead of failing.
        range_header = None

    if range_header:
        try:
            start, end = _parse_byte_range(range_header, file_size)
        except _RangeParseError as exc:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail="Requested range not satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"},
            ) from exc
        status_code = status.HTTP_206_PARTIAL_CONTENT
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
        }
    else:
        start = 0
        end = file_size - 1 if file_size > 0 else -1
        status_code = status.HTTP_200_OK
        headers = {"Accept-Ranges": "bytes"}

    content_length = max(end - start + 1, 0)
    headers["Content-Length"] = str(content_length)
    # Latin-1 header encoding will fail on filenames with accents; provide a
    # safe ASCII fallback while still advertising the UTF-8 name via RFC 5987.
    original_name = resolved_path.name
    safe_ascii = re.sub(r"[^0-9A-Za-z._-]", "_", original_name) or "download"
    quoted_utf8 = urllib.parse.quote(original_name)
    disposition = "inline" if _should_inline(media_type) else "attachment"
    headers["Content-Disposition"] = (
        f'{disposition}; filename="{safe_ascii}"; filename*=UTF-8\'\'{quoted_utf8}'
    )

    body_iterator = _iter_file_chunks(resolved_path, start, end)
    return StreamingResponse(
        body_iterator,
        status_code=status_code,
        media_type=media_type or "application/octet-stream",
        headers=headers,
    )


async def _download_job_file(
    job_id: str,
    filename: str,
    file_locator: FileLocator,
    range_header: str | None,
):
    """Return a streaming response for the requested job file."""

    try:
        resolved_path = file_locator.resolve_path(job_id, filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc

    if not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return _stream_local_file(resolved_path, range_header)


def _resolve_cover_download_path(filename: str) -> Path:
    root = cfg.resolve_directory(None, cfg.DEFAULT_COVERS_RELATIVE)
    candidate = (root / filename).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return candidate


@storage_router.get("/jobs/{job_id}/files/{filename:path}")
async def download_job_file(
    job_id: str,
    filename: str,
    file_locator: FileLocator = Depends(get_file_locator),
    range_header: str | None = Header(default=None, alias="Range"),
):
    """Stream the requested job file supporting optional byte ranges."""

    return await _download_job_file(job_id, filename, file_locator, range_header)


@storage_router.get("/jobs/{job_id}/{filename:path}")
async def download_job_file_without_prefix(
    job_id: str,
    filename: str,
    file_locator: FileLocator = Depends(get_file_locator),
    range_header: str | None = Header(default=None, alias="Range"),
):
    """Stream job files that were referenced without the legacy ``/files`` prefix."""

    return await _download_job_file(job_id, filename, file_locator, range_header)


@storage_router.get("/covers/{filename:path}")
async def download_cover_file(
    filename: str,
    range_header: str | None = Header(default=None, alias="Range"),
):
    """Serve cover images stored in the shared covers directory."""

    resolved_path = _resolve_cover_download_path(filename)
    return _stream_local_file(resolved_path, range_header)


def register_exception_handlers(app) -> None:
    """Compatibility shim; legacy media routes register their own handlers."""
    return None


__all__ = ["router", "storage_router", "jobs_timing_router", "register_exception_handlers"]
