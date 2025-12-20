"""Offline export bundle routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from ..dependencies import RequestUserContext, get_export_service, get_request_user
from ..schemas.exports import ExportRequestPayload, ExportResponse
from modules.services.export_service import ExportService, ExportServiceError


router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.post("", response_model=ExportResponse)
def create_export(
    payload: ExportRequestPayload,
    export_service: ExportService = Depends(get_export_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> ExportResponse:
    try:
        result = export_service.create_export(
            source_kind=payload.source_kind,
            source_id=payload.source_id,
            player_type=payload.player_type,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ExportServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

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
    try:
        result = export_service.resolve_export_download(export_id)
    except ExportServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FileResponse(
        path=result.zip_path,
        filename=result.download_name,
        media_type="application/zip",
    )
