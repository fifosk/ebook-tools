"""Offline export bundle routes."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from ..dependencies import RequestUserContext, get_export_service, get_request_user
from ..route_telemetry import record_started_route_duration
from ..schemas.exports import ExportRequestPayload, ExportResponse
from modules.services.export_service import ExportService, ExportServiceError


router = APIRouter(prefix="/api/exports", tags=["exports"])
LOGGER = logging.getLogger(__name__)


def _record_export_route_duration(operation: str, result: str, started_at: float) -> None:
    """Record token-safe export route timing if metrics are available."""

    record_started_route_duration(
        "EXPORT_ROUTE_DURATION",
        operation,
        result,
        started_at,
    )


def _log_export_route(
    operation: str,
    result: str,
    started_at: float,
    *,
    source_kind: str | None = None,
    player_type: str | None = None,
) -> None:
    """Log aggregate export route timing without identifiers or file paths."""

    duration_ms = (time.perf_counter() - started_at) * 1000.0
    _record_export_route_duration(operation, result, started_at)
    log_method = LOGGER.info if result != "success" or duration_ms >= 250 else LOGGER.debug
    log_method(
        "Offline export route operation=%s result=%s source_kind=%s player_type=%s duration_ms=%.1f",
        operation,
        result,
        source_kind or "unknown",
        player_type or "unknown",
        duration_ms,
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
    except KeyError as exc:
        _log_export_route(
            "create",
            "not_found",
            started_at,
            source_kind=payload.source_kind,
            player_type=payload.player_type,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        _log_export_route(
            "create",
            "forbidden",
            started_at,
            source_kind=payload.source_kind,
            player_type=payload.player_type,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ExportServiceError as exc:
        _log_export_route(
            "create",
            "bad_request",
            started_at,
            source_kind=payload.source_kind,
            player_type=payload.player_type,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    _log_export_route(
        "create",
        "success",
        started_at,
        source_kind=payload.source_kind,
        player_type=payload.player_type,
    )
    return ExportResponse(
        export_id=result.export_id,
        download_url=f"/api/exports/{result.export_id}/download",
        filename=result.download_name,
        created_at=result.created_at,
    )


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    _log_export_route("download", "success", started_at)
    return FileResponse(
        path=result.zip_path,
        filename=result.download_name,
        media_type="application/zip",
    )
