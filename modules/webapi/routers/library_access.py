"""Access-policy helpers shared by Library routes."""

from __future__ import annotations

from fastapi import HTTPException, status

from ...library import LibraryEntry
from ...permissions import can_access, resolve_access_policy
from ..dependencies import RequestUserContext


def library_owner_id(item: LibraryEntry) -> str | None:
    if item.owner_id:
        return item.owner_id
    metadata = item.metadata.data if hasattr(item.metadata, "data") else {}
    owner = metadata.get("user_id") or metadata.get("owner_id")
    if isinstance(owner, str):
        trimmed = owner.strip()
        return trimmed or None
    return None


def resolve_library_access(item: LibraryEntry):
    metadata = item.metadata.data if hasattr(item.metadata, "data") else {}
    return resolve_access_policy(metadata.get("access"), default_visibility="public")


def ensure_library_access(
    item: LibraryEntry,
    request_user: RequestUserContext,
    *,
    permission: str,
) -> None:
    policy = resolve_library_access(item)
    owner_id = library_owner_id(item)
    if can_access(
        policy,
        owner_id=owner_id,
        user_id=request_user.user_id,
        user_role=request_user.user_role,
        permission=permission,
    ):
        return
    detail = "Not authorized to access library item"
    if permission == "edit":
        detail = "Not authorized to modify library item"
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
