"""Routes for reusable cross-surface creation templates."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import (
    RequestUserContext,
    get_creation_template_service,
    get_request_user,
)
from ..schemas.creation_templates import (
    CreationTemplateDeleteResponse,
    CreationTemplateEntryPayload,
    CreationTemplateListResponse,
    CreationTemplatePayload,
)
from ...services.creation_template_service import CreationTemplateService


router = APIRouter(prefix="/api/creation/templates", tags=["creation-templates"])


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
    user_id = _require_user(request_user)
    entries = template_service.list_templates(user_id, mode=mode)
    return CreationTemplateListResponse(
        templates=[CreationTemplateEntryPayload(**entry.__dict__) for entry in entries]
    )


@router.post("", response_model=CreationTemplateEntryPayload)
def save_creation_template(
    payload: CreationTemplatePayload,
    request_user: RequestUserContext = Depends(get_request_user),
    template_service: CreationTemplateService = Depends(get_creation_template_service),
) -> CreationTemplateEntryPayload:
    user_id = _require_user(request_user)
    entry = template_service.save_template(user_id, payload.model_dump())
    return CreationTemplateEntryPayload(**entry.__dict__)


@router.delete("/{template_id}", response_model=CreationTemplateDeleteResponse)
def delete_creation_template(
    template_id: str,
    request_user: RequestUserContext = Depends(get_request_user),
    template_service: CreationTemplateService = Depends(get_creation_template_service),
) -> CreationTemplateDeleteResponse:
    user_id = _require_user(request_user)
    deleted = template_service.delete_template(user_id, template_id)
    return CreationTemplateDeleteResponse(deleted=deleted, template_id=template_id)
