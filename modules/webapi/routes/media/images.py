"""Routes for sentence image metadata and regeneration."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool

from .... import config_manager as cfg
from .... import logging_manager
from ....metadata_manager import MetadataLoader
from ....images.drawthings import (
    DrawThingsError,
    DrawThingsImageRequest,
    normalize_drawthings_base_urls,
    resolve_drawthings_client,
)
from ....images.prompting import (
    build_sentence_image_negative_prompt,
    build_sentence_image_prompt,
    sentence_batches_to_diffusion_prompt_plan,
    sentence_to_diffusion_prompt,
)
from ....images.visual_prompting import GLOBAL_NEGATIVE_CANON, VisualPromptOrchestrator
from ....images.style_templates import normalize_image_style_template
from ....services.file_locator import FileLocator
from ....library import LibraryRepository
from ...dependencies import (
    RequestUserContext,
    get_file_locator,
    get_library_repository,
    get_pipeline_job_manager,
    get_request_user,
)

from ...schemas.images import (
    SentenceImageInfoResponse,
    SentenceImageInfoBatchResponse,
    SentenceImageRegenerateRequest,
    SentenceImageRegenerateResponse,
)
from .common import _resolve_job_path, _resolve_job_root

router = APIRouter()
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
    # Prefer variant-specific text (v3 chunks omit top-level "text")
    original = entry.get("original")
    if isinstance(original, Mapping):
        original_text = original.get("text")
        if isinstance(original_text, str) and original_text.strip():
            return original_text.strip()
    # Backward compat: top-level text (v1/v2 chunks)
    text_value = entry.get("text")
    if isinstance(text_value, str) and text_value.strip():
        return text_value.strip()
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


def _load_image_manifest(job_root: Path) -> Optional[Mapping[str, Any]]:
    """Load the image manifest if it exists, returning the ``images`` dict or None."""
    manifest_path = job_root / "metadata" / "image_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, Mapping):
        return None
    images = raw.get("images")
    return images if isinstance(images, Mapping) else None


def _extract_sentence_image(
    entry: Mapping[str, Any],
    manifest_entry: Optional[Mapping[str, Any]] = None,
) -> tuple[Optional[str], Optional[str]]:
    # Prefer manifest entry (new jobs with image_manifest.json)
    if isinstance(manifest_entry, Mapping):
        prompt = manifest_entry.get("prompt")
        negative = manifest_entry.get("negativePrompt") or manifest_entry.get("negative_prompt")
        prompt_str = prompt.strip() if isinstance(prompt, str) and prompt.strip() else None
        negative_str = negative.strip() if isinstance(negative, str) and negative.strip() else None
        if prompt_str is not None:
            return prompt_str, negative_str
    # Fallback to inline image dict (old chunks)
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
    manifest_entry: Optional[Mapping[str, Any]] = None,
) -> SentenceImageInfoResponse:
    range_fragment = chunk.get("range_fragment") or chunk.get("rangeFragment")
    range_fragment_str = (
        str(range_fragment).strip()
        if isinstance(range_fragment, str) and range_fragment.strip()
        else None
    )
    prompt, negative_prompt = _extract_sentence_image(sentence_entry, manifest_entry)
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


def _resolve_job_image_prompt_pipeline(job_root: Path) -> str:
    manifest_path = job_root / "metadata" / "job.json"
    if not manifest_path.exists():
        return "prompt_plan"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return "prompt_plan"
    if not isinstance(payload, Mapping):
        return "prompt_plan"
    request_payload = payload.get("request")
    if not isinstance(request_payload, Mapping):
        return "prompt_plan"
    pipeline_overrides = request_payload.get("pipeline_overrides")
    config_payload = request_payload.get("config")
    raw_value = None
    if isinstance(pipeline_overrides, Mapping):
        raw_value = pipeline_overrides.get("image_prompt_pipeline")
    if raw_value is None and isinstance(config_payload, Mapping):
        raw_value = config_payload.get("image_prompt_pipeline")
    normalized = str(raw_value or "prompt_plan").strip().lower()
    if normalized in {"visual_canon", "visual-canon", "canon"}:
        return "visual_canon"
    return "prompt_plan"


def _resolve_visual_canon_prompt(
    *,
    job_root: Path,
    sentence_number: int,
    sentence_text: str,
) -> tuple[str, str]:
    metadata_root = job_root / "metadata"
    media_metadata: dict[str, Any] = {}
    content_index_payload: Optional[Mapping[str, Any]] = None

    canon_path = metadata_root / "visual_canon.json"
    if not canon_path.exists():
        raise ValueError("Visual canon missing for this job.")

    book_path = metadata_root / "book.json"
    if book_path.exists():
        try:
            loaded = json.loads(book_path.read_text(encoding="utf-8"))
            if isinstance(loaded, Mapping):
                media_metadata = dict(loaded)
        except Exception:
            media_metadata = {}

    content_index_path = metadata_root / "content_index.json"
    if content_index_path.exists():
        try:
            loaded = json.loads(content_index_path.read_text(encoding="utf-8"))
            if isinstance(loaded, Mapping):
                content_index_payload = dict(loaded)
        except Exception:
            content_index_payload = None

    scenes_root = metadata_root / "scenes"
    if not scenes_root.exists() or not any(scenes_root.glob("*.json")):
        raise ValueError("Scene metadata missing for visual canon prompts.")

    total_sentences = None
    if content_index_payload:
        total_candidate = content_index_payload.get("total_sentences")
        try:
            total_sentences = int(total_candidate)
        except (TypeError, ValueError):
            total_sentences = None
    if total_sentences is None:
        for key in ("total_sentences", "book_sentence_count"):
            try:
                total_sentences = int(media_metadata.get(key))
            except (TypeError, ValueError):
                total_sentences = None
            if total_sentences:
                break
    if not total_sentences:
        raise ValueError("Total sentence count unavailable for visual canon prompt.")

    dummy_sentences = [""] * total_sentences
    orchestrator = VisualPromptOrchestrator(
        job_root=job_root,
        media_metadata=media_metadata,
        full_sentences=dummy_sentences,
        content_index=content_index_payload,
    )
    orchestrator.prepare()
    result = orchestrator.build_sentence_prompt(
        sentence_number=sentence_number,
        sentence_text=sentence_text,
    )
    return result.positive_prompt, result.negative_prompt


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
        permission="edit",
    )

    def _load_batch() -> Tuple[List[SentenceImageInfoResponse], List[int]]:
        loader = MetadataLoader(job_root)
        manifest_images = _load_image_manifest(job_root)
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
            m_entry = (
                manifest_images.get(str(sentence_number))
                if isinstance(manifest_images, Mapping)
                else None
            )
            items.append(
                _build_sentence_image_info_response(
                    job_id=job_id,
                    sentence_number=sentence_number,
                    chunk=chunk,
                    sentence_entry=entry,
                    manifest_entry=m_entry,
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
    manifest_images = await run_in_threadpool(_load_image_manifest, job_root)
    manifest_entry = (
        manifest_images.get(str(sentence_number))
        if isinstance(manifest_images, Mapping)
        else None
    )
    response = _build_sentence_image_info_response(
        job_id=job_id,
        sentence_number=sentence_number,
        chunk=chunk,
        sentence_entry=sentence_entry,
        manifest_entry=manifest_entry,
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
    prompt_pipeline = _resolve_job_image_prompt_pipeline(job_root)

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

    regen_manifest_images = await run_in_threadpool(_load_image_manifest, job_root)
    regen_manifest_entry = (
        regen_manifest_images.get(str(sentence_number))
        if isinstance(regen_manifest_images, Mapping)
        else None
    )
    stored_prompt, stored_negative = _extract_sentence_image(sentence_entry, regen_manifest_entry)
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

    sentence_text = _extract_sentence_text(sentence_entry) or ""
    if prompt_pipeline == "visual_canon":
        if use_llm_prompt or not prompt:
            try:
                prompt, negative_prompt = await run_in_threadpool(
                    _resolve_visual_canon_prompt,
                    job_root=job_root,
                    sentence_number=sentence_number,
                    sentence_text=sentence_text,
                )
            except Exception as exc:
                LOGGER.warning(
                    "Unable to rebuild visual canon prompt: %s",
                    exc,
                    extra={
                        "event": "webapi.image.visual_canon.error",
                        "attributes": {"error": str(exc)},
                        "console_suppress": True,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="visual canon prompt is unavailable for this job",
                ) from exc
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="visual canon prompt missing for this sentence",
            )
        if not negative_prompt:
            negative_prompt = GLOBAL_NEGATIVE_CANON
        prompt_full = prompt
        negative_full = negative_prompt
    else:
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
                    diffusion = await run_in_threadpool(
                        sentence_to_diffusion_prompt,
                        sentence_text,
                        context_sentences=(),
                    )
            else:
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
                prompt = (diffusion.prompt or "").strip() or sentence_text.strip()
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
                sentence["imagePath"] = relative_path
                updated = True
            if updated:
                _atomic_write_json(chunk_path, raw)

        # Update image manifest if it exists
        manifest_path = job_root / "metadata" / "image_manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                manifest = None
            if isinstance(manifest, dict) and isinstance(manifest.get("images"), dict):
                key = str(sentence_number)
                existing_entry = manifest["images"].get(key, {})
                if not isinstance(existing_entry, dict):
                    existing_entry = {}
                existing_entry["path"] = relative_path
                existing_entry["prompt"] = prompt_full
                if negative_full:
                    existing_entry["negativePrompt"] = negative_full
                else:
                    existing_entry.pop("negativePrompt", None)
                    existing_entry.pop("negative_prompt", None)
                manifest["images"][key] = existing_entry
                _atomic_write_json(manifest_path, manifest)

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
