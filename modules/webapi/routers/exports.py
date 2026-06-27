"""Offline export bundle routes."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from ..dependencies import RequestUserContext, get_export_service, get_request_user
from ..route_telemetry import log_started_route_result
from ..schemas.exports import ExportRequestPayload, ExportResponse
from modules.services.export_service import ExportService, ExportServiceError


router = APIRouter(prefix="/api/exports", tags=["exports"])
LOGGER = logging.getLogger(__name__)

EXPORT_SOURCE_NOT_FOUND_MESSAGE = "Offline export source not found."
EXPORT_FORBIDDEN_MESSAGE = "Not authorized to create offline export."
EXPORT_CREATE_FAILED_MESSAGE = "Unable to create offline export."
EXPORT_DOWNLOAD_UNAVAILABLE_MESSAGE = "Offline export is unavailable."


def _log_export_route(
    operation: str,
    result: str,
    started_at: float,
    *,
    source_kind: str | None = None,
    player_type: str | None = None,
) -> None:
    """Log aggregate export route timing without identifiers or file paths."""

    log_started_route_result(
        LOGGER,
        metric_name="EXPORT_ROUTE_DURATION",
        message="Offline export route",
        operation=operation,
        result=result,
        started_at=started_at,
        duration_first=False,
        source_kind=source_kind or "unknown",
        player_type=player_type or "unknown",
    )


@router.post("", response_model=ExportResponse)
def create_export(
    payload: ExportRequestPayload,
    export_service: ExportService = Depends(get_export_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> ExportResponse:
    started_at = time.perf_counter()
    try:
        result = export_service.create_export(
            source_kind=payload.source_kind,
            source_id=payload.source_id,
            player_type=payload.player_type,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
        response_payload = ExportResponse(
            export_id=result.export_id,
            download_url=f"/api/exports/{result.export_id}/download",
            filename=result.download_name,
            created_at=result.created_at,
        )
    except KeyError as exc:
        _log_export_route(
            "create",
            "not_found",
            started_at,
            source_kind=payload.source_kind,
            player_type=payload.player_type,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EXPORT_SOURCE_NOT_FOUND_MESSAGE,
        ) from exc
    except PermissionError as exc:
        _log_export_route(
            "create",
            "forbidden",
            started_at,
            source_kind=payload.source_kind,
            player_type=payload.player_type,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=EXPORT_FORBIDDEN_MESSAGE,
        ) from exc
    except ExportServiceError as exc:
        _log_export_route(
            "create",
            "bad_request",
            started_at,
            source_kind=payload.source_kind,
            player_type=payload.player_type,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=EXPORT_CREATE_FAILED_MESSAGE,
        ) from exc
    except Exception as exc:
        _log_export_route(
            "create",
            "error",
            started_at,
            source_kind=payload.source_kind,
            player_type=payload.player_type,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=EXPORT_CREATE_FAILED_MESSAGE,
        ) from exc

    _log_export_route(
        "create",
        "success",
        started_at,
        source_kind=payload.source_kind,
        player_type=payload.player_type,
    )
    return response_payload


@router.get("/{export_id}/download")
def download_export(
    export_id: str,
    export_service: ExportService = Depends(get_export_service),
) -> FileResponse:
    started_at = time.perf_counter()
    try:
        result = export_service.resolve_export_download(export_id)
    except ExportServiceError as exc:
        _log_export_route("download", "not_found", started_at)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EXPORT_DOWNLOAD_UNAVAILABLE_MESSAGE,
        ) from exc
    except Exception as exc:
        _log_export_route("download", "error", started_at)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=EXPORT_DOWNLOAD_UNAVAILABLE_MESSAGE,
        ) from exc

    _log_export_route("download", "success", started_at)
    return FileResponse(
        path=result.zip_path,
        filename=result.download_name,
        media_type="application/zip",
    )
