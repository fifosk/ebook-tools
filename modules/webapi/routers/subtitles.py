"""Routes exposing subtitle job orchestration."""

from __future__ import annotations

import json
from datetime import datetime
import tempfile
from pathlib import Path
from typing import Optional, Union

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from modules import logging_manager as log_mgr
from modules.services import SubtitleService, SubtitleSubmission
from modules.services.llm_models import list_available_llm_models
from modules.services.job_manager import PipelineJobManager
from modules.services.subtitle_service import SUPPORTED_EXTENSIONS
from modules.subtitles import SubtitleColorPalette, SubtitleJobOptions

from ..dependencies import (
    RequestUserContext,
    get_pipeline_job_manager,
    get_request_user,
    get_subtitle_service,
)
from ..schemas import (
    PipelineSubmissionResponse,
    SubtitleSourceEntry,
    SubtitleSourceListResponse,
    LLMModelListResponse,
    SubtitleDeleteRequest,
    SubtitleDeleteResponse,
)

# Import from modular components
from .subtitle_utils import (
    as_bool,
    coerce_int,
    parse_ass_font_size,
    parse_ass_emphasis_scale,
    parse_time_offset,
    parse_end_time,
    infer_language_from_name,
    youtube_router,
    metadata_router,
    _looks_like_youtube_subtitle,
)

router = APIRouter(prefix="/api/subtitles", tags=["subtitles"])
logger = log_mgr.get_logger().getChild("webapi.subtitles")
_ALLOWED_ROLES = {"editor", "admin"}

# Include sub-routers
router.include_router(youtube_router)
router.include_router(metadata_router)


def _ensure_editor(request_user: RequestUserContext) -> None:
    role = (request_user.user_role or "").strip().lower()
    if role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("/sources", response_model=SubtitleSourceListResponse)
def list_subtitle_sources(
    directory: Optional[str] = None,
    service: SubtitleService = Depends(get_subtitle_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> SubtitleSourceListResponse:
    """Return discoverable subtitle files (.srt/.vtt plus generated .ass)."""

    _ensure_editor(request_user)
    base_path = Path(directory).expanduser() if directory else None
    try:
        entries = service.list_sources(base_path)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    payload = []
    for path in entries:
        try:
            stat = path.stat()
            modified_at = datetime.fromtimestamp(stat.st_mtime)
        except Exception:
            modified_at = None
        payload.append(
            SubtitleSourceEntry(
                name=path.name,
                path=path.as_posix(),
                format=path.suffix.lstrip(".").lower(),
                language=infer_language_from_name(path),
                modified_at=modified_at,
            )
        )
    return SubtitleSourceListResponse(sources=payload)


@router.post("/delete-source", response_model=SubtitleDeleteResponse)
def delete_subtitle_source(
    payload: SubtitleDeleteRequest,
    service: SubtitleService = Depends(get_subtitle_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> SubtitleDeleteResponse:
    """Delete a subtitle source and any mirrored HTML transcript."""

    _ensure_editor(request_user)
    base_dir = Path(payload.base_dir).expanduser() if payload.base_dir else service.default_source_dir
    subtitle_path = Path(payload.subtitle_path).expanduser()
    try:
        result = service.delete_source(subtitle_path, base_dir=base_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("Unable to delete subtitle %s", subtitle_path, exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to delete subtitle: {exc}",
        ) from exc

    return SubtitleDeleteResponse(
        subtitle_path=subtitle_path.as_posix(),
        base_dir=base_dir.as_posix(),
        removed=[path.as_posix() for path in result.removed],
        missing=[path.as_posix() for path in result.missing],
    )


@router.get("/models", response_model=LLMModelListResponse)
def list_subtitle_models(
    request_user: RequestUserContext = Depends(get_request_user),
) -> LLMModelListResponse:
    """Return available LLM models for subtitle translations."""

    _ensure_editor(request_user)
    try:
        models = list_available_llm_models()
    except Exception as exc:
        logger.error("Unable to query LLM model tags", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to query LLM model list.",
        ) from exc

    return LLMModelListResponse(models=models)


@router.post(
    "/jobs",
    response_model=PipelineSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_subtitle_job(
    input_language: str = Form(...),
    target_language: str = Form(...),
    original_language: Optional[str] = Form(None),
    llm_model: Optional[str] = Form(None),
    translation_provider: Optional[str] = Form(None),
    transliteration_mode: Optional[str] = Form(None),
    transliteration_model: Optional[str] = Form(None),
    enable_transliteration: Union[str, bool] = Form(False),
    highlight: Union[str, bool] = Form(True),
    show_original: Union[str, bool] = Form(True),
    generate_audio_book: Union[str, bool] = Form(True),
    batch_size: Optional[str] = Form(None),
    translation_batch_size: Optional[str] = Form(None),
    worker_count: Optional[str] = Form(None),
    start_time: Optional[str] = Form("00:00"),
    end_time: Optional[str] = Form(None),
    source_path: Optional[str] = Form(None),
    media_metadata_json: Optional[str] = Form(None),
    cleanup_source: Union[str, bool] = Form(False),
    mirror_batches_to_source_dir: Union[str, bool] = Form(True),
    output_format: str = Form("srt"),
    subtitle_color_original: Optional[str] = Form(None),
    subtitle_color_translation: Optional[str] = Form(None),
    subtitle_color_transliteration: Optional[str] = Form(None),
    subtitle_color_highlight_current: Optional[str] = Form(None),
    subtitle_color_highlight_prior: Optional[str] = Form(None),
    ass_font_size: Optional[str] = Form(None),
    ass_emphasis_scale: Optional[str] = Form(None),
    file: UploadFile | None = File(None),
    service: SubtitleService = Depends(get_subtitle_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Submit a subtitle processing job."""

    _ensure_editor(request_user)
    if file is None and not source_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either an upload or source_path must be provided.",
        )
    if file is not None and source_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one of upload or source_path may be provided.",
        )

    color_payload = {
        "original": subtitle_color_original,
        "translation": subtitle_color_translation,
        "transliteration": subtitle_color_transliteration,
        "highlight_current": subtitle_color_highlight_current,
        "highlight_prior": subtitle_color_highlight_prior,
    }
    palette_mapping = {
        key: value
        for key, value in color_payload.items()
        if value is not None and str(value).strip()
    }

    try:
        start_offset_seconds = parse_time_offset(start_time)
        end_offset_seconds = parse_end_time(end_time, start_offset_seconds)
        palette = SubtitleColorPalette.from_mapping(palette_mapping if palette_mapping else None)
        resolved_input_language = (input_language or "").strip()
        if not resolved_input_language:
            resolved_input_language = "English"
        resolved_target_language = (target_language or "").strip()
        resolved_original_language = (original_language or "").strip()
        if not resolved_original_language:
            resolved_original_language = resolved_input_language
        resolved_llm_model = (llm_model or "").strip() or None
        resolved_translation_provider = (translation_provider or "").strip() or None
        resolved_transliteration_mode = (transliteration_mode or "").strip() or None
        resolved_transliteration_model = (transliteration_model or "").strip() or None
        options_model = SubtitleJobOptions(
            input_language=resolved_input_language,
            target_language=resolved_target_language,
            original_language=resolved_original_language,
            show_original=as_bool(show_original, True),
            enable_transliteration=as_bool(enable_transliteration, False),
            highlight=as_bool(highlight, True),
            generate_audio_book=as_bool(generate_audio_book, True),
            batch_size=coerce_int(batch_size),
            translation_batch_size=coerce_int(translation_batch_size),
            worker_count=coerce_int(worker_count),
            mirror_batches_to_source_dir=as_bool(mirror_batches_to_source_dir, True),
            start_time_offset=start_offset_seconds,
            end_time_offset=end_offset_seconds,
            output_format=output_format,
            color_palette=palette,
            llm_model=resolved_llm_model,
            transliteration_model=resolved_transliteration_model,
            translation_provider=resolved_translation_provider,
            transliteration_mode=resolved_transliteration_mode,
            ass_font_size=parse_ass_font_size(ass_font_size),
            ass_emphasis_scale=parse_ass_emphasis_scale(ass_emphasis_scale),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    cleanup_flag = as_bool(cleanup_source, False)
    temp_file: Optional[Path] = None
    media_metadata: Optional[dict] = None

    if media_metadata_json is not None and str(media_metadata_json).strip():
        try:
            candidate = json.loads(str(media_metadata_json))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="media_metadata_json must be valid JSON",
            ) from exc
        if not isinstance(candidate, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="media_metadata_json must be a JSON object",
            )
        media_metadata = candidate

    try:
        if file is not None:
            filename = file.filename or "subtitle.srt"
            suffix = Path(filename).suffix or ".srt"
            if suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported subtitle extension '{suffix}'.",
                )
            with tempfile.NamedTemporaryFile("wb", suffix=suffix, delete=False) as handle:
                contents = await file.read()
                if not contents:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Uploaded subtitle file is empty.",
                    )
                handle.write(contents)
                temp_file = Path(handle.name)
            source_path_resolved = temp_file
            original_name = filename
            cleanup_flag = True
        else:
            assert source_path is not None  # for mypy
            source_path_resolved = Path(source_path).expanduser()
            if not source_path_resolved.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Subtitle source '{source_path_resolved}' does not exist.",
                )
            if source_path_resolved.suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported subtitle extension '{source_path_resolved.suffix}'.",
                )
            original_name = source_path_resolved.name
    except HTTPException:
        if temp_file is not None:
            temp_file.unlink(missing_ok=True)
        raise
    except OSError as exc:
        if temp_file is not None:
            temp_file.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to prepare subtitle upload.",
        ) from exc

    try:
        object.__setattr__(
            options_model,
            "source_is_youtube",
            _looks_like_youtube_subtitle(source_path_resolved),
        )
    except Exception:
        # Defensive: keep options intact if tagging fails.
        pass

    submission = SubtitleSubmission(
        source_path=source_path_resolved,
        original_name=original_name,
        options=options_model,
        cleanup=cleanup_flag,
        media_metadata=media_metadata,
    )

    try:
        job = service.enqueue(
            submission,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except Exception:
        if temp_file is not None:
            temp_file.unlink(missing_ok=True)
        raise

    return PipelineSubmissionResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        job_type=job.job_type,
    )


@router.get("/jobs/{job_id}/result")
def get_subtitle_job_result(
    job_id: str,
    job_manager: PipelineJobManager = Depends(get_pipeline_job_manager),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return the final payload for a subtitle job."""

    job = job_manager.get(
        job_id,
        user_id=request_user.user_id,
        user_role=request_user.user_role,
    )
    if job.job_type != "subtitle":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subtitle job not found")
    return job.result_payload or {}
