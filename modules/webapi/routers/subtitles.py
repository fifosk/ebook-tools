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

from modules.services import SubtitleService, SubtitleSubmission
from modules.services.job_manager import PipelineJobManager
from modules.services.subtitle_service import SUPPORTED_EXTENSIONS
from modules.subtitles import SubtitleJobOptions

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
)

router = APIRouter(prefix="/api/subtitles", tags=["subtitles"])


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


@router.post(
    "/jobs",
    response_model=PipelineSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_subtitle_job(
    input_language: str = Form(...),
    target_language: str = Form(...),
    enable_transliteration: Union[str, bool] = Form(False),
    highlight: Union[str, bool] = Form(True),
    batch_size: Optional[str] = Form(None),
    worker_count: Optional[str] = Form(None),
    source_path: Optional[str] = Form(None),
    cleanup_source: Union[str, bool] = Form(False),
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

    options_model = SubtitleJobOptions(
        input_language=input_language.strip(),
        target_language=target_language.strip(),
        enable_transliteration=_as_bool(enable_transliteration, False),
        highlight=_as_bool(highlight, True),
        batch_size=_coerce_int(batch_size),
        worker_count=_coerce_int(worker_count),
    )
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
