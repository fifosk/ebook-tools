"""Routes exposing subtitle job orchestration."""

from __future__ import annotations
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
)

router = APIRouter(prefix="/api/subtitles", tags=["subtitles"])
logger = log_mgr.get_logger().getChild("webapi.subtitles")


def _as_bool(value: Optional[str | bool], default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _coerce_int(value: Optional[str | int]) -> Optional[int]:
    if isinstance(value, int):
        return value
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(str(value).strip())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid batch_size") from exc


def _parse_timecode_to_seconds(value: str, *, allow_minutes_only: bool) -> float:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("Empty time value")
    segments = trimmed.split(":")
    hours = 0
    minutes_str: Optional[str] = None
    seconds_str: Optional[str] = None
    if len(segments) == 1:
        if not allow_minutes_only:
            raise ValueError("Time value must include ':' separators")
        try:
            minutes = int(segments[0])
        except ValueError as exc:
            raise ValueError("Relative time must be an integer minute value") from exc
        if minutes < 0:
            raise ValueError("Relative minutes must be non-negative")
        return float(minutes * 60)
    if len(segments) == 2:
        minutes_str, seconds_str = segments
    elif len(segments) == 3:
        hours_str, minutes_str, seconds_str = segments
        try:
            hours = int(hours_str)
        except ValueError as exc:
            raise ValueError("Hours component must be an integer") from exc
        if hours < 0:
            raise ValueError("Hours component cannot be negative")
    else:
        raise ValueError("Time value must be MM:SS or HH:MM:SS")

    if minutes_str is None or seconds_str is None:
        raise ValueError("Minutes and seconds components are required")
    try:
        minutes = int(minutes_str)
        seconds = int(seconds_str)
    except ValueError as exc:
        raise ValueError("Minutes and seconds must be integers") from exc
    if minutes < 0 or seconds < 0:
        raise ValueError("Minutes and seconds must be non-negative")
    if len(segments) == 3 and minutes >= 60:
        raise ValueError("Minutes must be between 00 and 59 when hours are provided")
    if seconds >= 60:
        raise ValueError("Seconds must be between 00 and 59")
    return float(hours * 3600 + minutes * 60 + seconds)


def _parse_time_offset(value: Optional[str]) -> float:
    if value is None:
        return 0.0
    trimmed = str(value).strip()
    if not trimmed:
        return 0.0
    try:
        return _parse_timecode_to_seconds(trimmed, allow_minutes_only=False)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be in MM:SS or HH:MM:SS format.",
        ) from exc


def _parse_end_time(value: Optional[str], start_seconds: float) -> Optional[float]:
    if value is None:
        return None
    trimmed = str(value).strip()
    if not trimmed:
        return None
    if trimmed.startswith("+"):
        relative_expr = trimmed[1:].strip()
        if not relative_expr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_time offset cannot be empty.",
            )
        try:
            delta = _parse_timecode_to_seconds(relative_expr, allow_minutes_only=True)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Relative end_time must be '+MM:SS', '+HH:MM:SS', or '+<minutes>'.",
            ) from exc
        end_seconds = start_seconds + delta
    else:
        try:
            end_seconds = _parse_timecode_to_seconds(trimmed, allow_minutes_only=False)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_time must be in MM:SS or HH:MM:SS format.",
            ) from exc
    if end_seconds <= start_seconds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be after start_time.",
        )
    return float(end_seconds)


@router.get("/sources", response_model=SubtitleSourceListResponse)
def list_subtitle_sources(
    directory: Optional[str] = None,
    service: SubtitleService = Depends(get_subtitle_service),
) -> SubtitleSourceListResponse:
    """Return discoverable subtitle files."""

    base_path = Path(directory).expanduser() if directory else None
    try:
        entries = service.list_sources(base_path)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    payload = [
        SubtitleSourceEntry(name=path.name, path=path.as_posix())
        for path in entries
    ]
    return SubtitleSourceListResponse(sources=payload)


@router.get("/models", response_model=LLMModelListResponse)
def list_subtitle_models() -> LLMModelListResponse:
    """Return available Ollama models for subtitle translations."""

    try:
        models = list_available_llm_models()
    except Exception as exc:
        logger.error("Unable to query Ollama model tags", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to query Ollama model list.",
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
    enable_transliteration: Union[str, bool] = Form(False),
    highlight: Union[str, bool] = Form(True),
    show_original: Union[str, bool] = Form(True),
    batch_size: Optional[str] = Form(None),
    worker_count: Optional[str] = Form(None),
    start_time: Optional[str] = Form("00:00"),
    end_time: Optional[str] = Form(None),
    source_path: Optional[str] = Form(None),
    cleanup_source: Union[str, bool] = Form(False),
    mirror_batches_to_source_dir: Union[str, bool] = Form(True),
    output_format: str = Form("srt"),
    subtitle_color_original: Optional[str] = Form(None),
    subtitle_color_translation: Optional[str] = Form(None),
    subtitle_color_transliteration: Optional[str] = Form(None),
    subtitle_color_highlight_current: Optional[str] = Form(None),
    subtitle_color_highlight_prior: Optional[str] = Form(None),
    file: UploadFile | None = File(None),
    service: SubtitleService = Depends(get_subtitle_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Submit a subtitle processing job."""

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
        start_offset_seconds = _parse_time_offset(start_time)
        end_offset_seconds = _parse_end_time(end_time, start_offset_seconds)
        palette = SubtitleColorPalette.from_mapping(palette_mapping if palette_mapping else None)
        resolved_input_language = (input_language or "").strip()
        if not resolved_input_language:
            resolved_input_language = "English"
        resolved_target_language = (target_language or "").strip()
        resolved_original_language = (original_language or "").strip()
        if not resolved_original_language:
            resolved_original_language = resolved_input_language
        resolved_llm_model = (llm_model or "").strip() or None
        options_model = SubtitleJobOptions(
            input_language=resolved_input_language,
            target_language=resolved_target_language,
            original_language=resolved_original_language,
            show_original=_as_bool(show_original, True),
            enable_transliteration=_as_bool(enable_transliteration, False),
            highlight=_as_bool(highlight, True),
            batch_size=_coerce_int(batch_size),
            worker_count=_coerce_int(worker_count),
            mirror_batches_to_source_dir=_as_bool(mirror_batches_to_source_dir, True),
            start_time_offset=start_offset_seconds,
            end_time_offset=end_offset_seconds,
            output_format=output_format,
            color_palette=palette,
            llm_model=resolved_llm_model,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    cleanup_flag = _as_bool(cleanup_source, False)
    temp_file: Optional[Path] = None

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

    submission = SubtitleSubmission(
        source_path=source_path_resolved,
        original_name=original_name,
        options=options_model,
        cleanup=cleanup_flag,
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
