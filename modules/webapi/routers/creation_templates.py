"""Routes for reusable cross-surface creation templates."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modules import logging_manager as log_mgr

from ..dependencies import (
    RequestUserContext,
    get_creation_template_service,
    get_request_user,
)
from ..route_telemetry import log_started_route_result
from ..schemas.creation_templates import (
    CreationTemplateDeleteResponse,
    CreationTemplateEntryPayload,
    CreationTemplateListResponse,
    CreationTemplatePayload,
)
from ...services.creation_template_service import (
    CreationTemplateService,
    normalize_creation_template_filter_mode,
)


router = APIRouter(prefix="/api/creation/templates", tags=["creation-templates"])
logger = log_mgr.get_logger()


def _log_template_route_result(
    *,
    operation: str,
    result: str,
    started_at: float,
    template_count: int | None = None,
    deleted: bool | None = None,
) -> None:
    log_started_route_result(
        logger,
        metric_name="CREATION_TEMPLATE_ROUTE_DURATION",
        message="Creation template route",
        operation=operation,
        result=result,
        started_at=started_at,
        templates=template_count,
        deleted=deleted,
    )


def _require_user(request_user: RequestUserContext) -> str:
    if not request_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session token",
        )
    return request_user.user_id


@router.get("", response_model=CreationTemplateListResponse)
def list_creation_templates(
    mode: str | None = Query(default=None),
    request_user: RequestUserContext = Depends(get_request_user),
    template_service: CreationTemplateService = Depends(get_creation_template_service),
) -> CreationTemplateListResponse:
    started_at = time.perf_counter()
    try:
        user_id = _require_user(request_user)
    except HTTPException:
        _log_template_route_result(
            operation="list",
            result="unauthorized",
            started_at=started_at,
        )
        raise

    normalized_mode = normalize_creation_template_filter_mode(mode)
    if mode is not None and mode.strip() and normalized_mode is None:
        _log_template_route_result(
            operation="list",
            result="success",
            started_at=started_at,
            template_count=0,
        )
        return CreationTemplateListResponse(templates=[])

    try:
        entries = template_service.list_templates(user_id, mode=normalized_mode)
    except Exception:
        _log_template_route_result(operation="list", result="error", started_at=started_at)
        raise
    _log_template_route_result(
        operation="list",
        result="success",
        started_at=started_at,
        template_count=len(entries),
    )
    return CreationTemplateListResponse(
        templates=[CreationTemplateEntryPayload(**entry.__dict__) for entry in entries]
    )


@router.post("", response_model=CreationTemplateEntryPayload)
def save_creation_template(
    payload: CreationTemplatePayload,
    request_user: RequestUserContext = Depends(get_request_user),
    template_service: CreationTemplateService = Depends(get_creation_template_service),
) -> CreationTemplateEntryPayload:
    started_at = time.perf_counter()
    try:
        user_id = _require_user(request_user)
    except HTTPException:
        _log_template_route_result(
            operation="save",
            result="unauthorized",
            started_at=started_at,
        )
        raise

    try:
        entry = template_service.save_template(user_id, payload.model_dump())
    except Exception:
        _log_template_route_result(operation="save", result="error", started_at=started_at)
        raise
    _log_template_route_result(operation="save", result="success", started_at=started_at)
    return CreationTemplateEntryPayload(**entry.__dict__)


@router.get("/{template_id}", response_model=CreationTemplateEntryPayload)
def get_creation_template(
    template_id: str,
    request_user: RequestUserContext = Depends(get_request_user),
    template_service: CreationTemplateService = Depends(get_creation_template_service),
) -> CreationTemplateEntryPayload:
    started_at = time.perf_counter()
    try:
        user_id = _require_user(request_user)
    except HTTPException:
        _log_template_route_result(
            operation="get",
            result="unauthorized",
            started_at=started_at,
        )
        raise

    canonical_template_id = template_service.canonical_template_id(template_id)
    if not canonical_template_id:
        _log_template_route_result(operation="get", result="not_found", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creation template not found",
        )

    try:
        entry = template_service.get_template(user_id, canonical_template_id)
    except Exception:
        _log_template_route_result(operation="get", result="error", started_at=started_at)
        raise
    if entry is None:
        _log_template_route_result(operation="get", result="not_found", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creation template not found",
        )
    _log_template_route_result(operation="get", result="success", started_at=started_at)
    return CreationTemplateEntryPayload(**entry.__dict__)


@router.delete("/{template_id}", response_model=CreationTemplateDeleteResponse)
def delete_creation_template(
    template_id: str,
    request_user: RequestUserContext = Depends(get_request_user),
    template_service: CreationTemplateService = Depends(get_creation_template_service),
) -> CreationTemplateDeleteResponse:
    started_at = time.perf_counter()
    try:
        user_id = _require_user(request_user)
    except HTTPException:
        _log_template_route_result(
            operation="delete",
            result="unauthorized",
            started_at=started_at,
        )
        raise

    canonical_template_id = template_service.canonical_template_id(template_id)
    if not canonical_template_id:
        _log_template_route_result(
            operation="delete",
            result="success",
            started_at=started_at,
            deleted=False,
        )
        return CreationTemplateDeleteResponse(deleted=False, template_id="")

    try:
        deleted = template_service.delete_template(user_id, canonical_template_id)
    except Exception:
        _log_template_route_result(operation="delete", result="error", started_at=started_at)
        raise
    _log_template_route_result(
        operation="delete",
        result="success",
        started_at=started_at,
        deleted=deleted,
    )
    return CreationTemplateDeleteResponse(
        deleted=deleted,
        template_id=template_service.canonical_template_id(template_id),
    )
