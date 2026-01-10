"""Access control helpers for jobs and library items."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, List, Mapping, Optional, Sequence


AccessPermission = str
AccessVisibility = str
AccessSubjectType = str

_ALLOWED_PERMISSIONS = {"view", "edit"}
_ALLOWED_VISIBILITY = {"private", "public"}
_ALLOWED_SUBJECT_TYPES = {"user", "role"}


def normalize_role(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized == "standard_user":
        normalized = "viewer"
    return normalized or None


def is_admin_role(value: Optional[str]) -> bool:
    return normalize_role(value) == "admin"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_visibility(value: Optional[str], default: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in _ALLOWED_VISIBILITY:
        return normalized
    return default


def _normalize_permissions(values: Iterable[Any]) -> List[str]:
    collected: list[str] = []
    for entry in values:
        if not isinstance(entry, str):
            continue
        normalized = entry.strip().lower()
        if normalized in _ALLOWED_PERMISSIONS:
            collected.append(normalized)
    if "edit" in collected and "view" not in collected:
        collected.append("view")
    return sorted(set(collected), key=lambda item: ("view", "edit").index(item))


def _normalize_subject_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    return normalized if normalized in _ALLOWED_SUBJECT_TYPES else None


def _normalize_subject_id(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    trimmed = value.strip()
    return trimmed or None


@dataclass(frozen=True)
class AccessGrant:
    subject_type: AccessSubjectType
    subject_id: str
    permissions: Sequence[AccessPermission]
    granted_by: Optional[str] = None
    granted_at: Optional[str] = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> Optional["AccessGrant"]:
        subject_type = _normalize_subject_type(str(payload.get("subject_type") or payload.get("subjectType") or ""))
        subject_id = _normalize_subject_id(str(payload.get("subject_id") or payload.get("subjectId") or ""))
        if not subject_type or not subject_id:
            return None
        raw_permissions = payload.get("permissions") or []
        if isinstance(raw_permissions, str):
            raw_permissions = [raw_permissions]
        if not isinstance(raw_permissions, Iterable):
            raw_permissions = []
        permissions = _normalize_permissions(raw_permissions)
        if not permissions:
            return None
        granted_by = _normalize_subject_id(
            str(payload.get("granted_by") or payload.get("grantedBy") or "")
        )
        granted_at = _normalize_subject_id(
            str(payload.get("granted_at") or payload.get("grantedAt") or "")
        )
        return cls(
            subject_type=subject_type,
            subject_id=subject_id,
            permissions=tuple(permissions),
            granted_by=granted_by,
            granted_at=granted_at,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "permissions": list(self.permissions),
        }
        if self.granted_by:
            payload["granted_by"] = self.granted_by
        if self.granted_at:
            payload["granted_at"] = self.granted_at
        return payload


@dataclass(frozen=True)
class AccessPolicy:
    visibility: AccessVisibility
    grants: Sequence[AccessGrant] = field(default_factory=tuple)
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "visibility": self.visibility,
            "grants": [grant.to_dict() for grant in self.grants],
        }
        if self.updated_by:
            payload["updated_by"] = self.updated_by
        if self.updated_at:
            payload["updated_at"] = self.updated_at
        return payload


def resolve_access_policy(
    payload: Mapping[str, Any] | AccessPolicy | None,
    *,
    default_visibility: str = "private",
) -> AccessPolicy:
    if isinstance(payload, AccessPolicy):
        return payload
    raw = dict(payload or {})
    visibility = _normalize_visibility(raw.get("visibility"), default_visibility)
    raw_grants = raw.get("grants") or []
    grants: list[AccessGrant] = []
    if isinstance(raw_grants, Sequence):
        for entry in raw_grants:
            if isinstance(entry, Mapping):
                grant = AccessGrant.from_payload(entry)
                if grant:
                    grants.append(grant)
    updated_by = _normalize_subject_id(str(raw.get("updated_by") or raw.get("updatedBy") or ""))
    updated_at = _normalize_subject_id(str(raw.get("updated_at") or raw.get("updatedAt") or ""))
    return AccessPolicy(
        visibility=visibility,
        grants=tuple(grants),
        updated_by=updated_by,
        updated_at=updated_at,
    )


def can_access(
    policy: AccessPolicy,
    *,
    owner_id: Optional[str],
    user_id: Optional[str],
    user_role: Optional[str],
    permission: str,
) -> bool:
    normalized_permission = (permission or "").strip().lower()
    if normalized_permission not in _ALLOWED_PERMISSIONS:
        return False
    normalized_role = normalize_role(user_role)
    if is_admin_role(normalized_role):
        return True
    if normalized_permission == "edit" and normalized_role == "viewer":
        return False
    if owner_id and user_id and owner_id == user_id:
        return True
    if normalized_permission == "view" and policy.visibility == "public":
        return True
    if not user_id and not normalized_role:
        return False

    role_value = normalized_role or ""
    for grant in policy.grants:
        if grant.subject_type == "user" and user_id and grant.subject_id == user_id:
            if normalized_permission in grant.permissions:
                return True
        if grant.subject_type == "role" and role_value and grant.subject_id == role_value:
            if normalized_permission in grant.permissions:
                return True
    return False


def merge_access_policy(
    existing: AccessPolicy,
    *,
    visibility: Optional[str] = None,
    grants: Optional[Iterable[Mapping[str, Any]]] = None,
    actor_id: Optional[str] = None,
) -> AccessPolicy:
    resolved_visibility = _normalize_visibility(visibility, existing.visibility)
    if grants is None:
        return AccessPolicy(
            visibility=resolved_visibility,
            grants=existing.grants,
            updated_by=actor_id or existing.updated_by,
            updated_at=_now_iso() if actor_id else existing.updated_at,
        )

    now = _now_iso()
    existing_index = {
        (grant.subject_type, grant.subject_id): grant for grant in existing.grants
    }
    merged: list[AccessGrant] = []
    for entry in grants:
        if not isinstance(entry, Mapping):
            continue
        grant = AccessGrant.from_payload(entry)
        if not grant:
            continue
        existing_grant = existing_index.get((grant.subject_type, grant.subject_id))
        granted_by = grant.granted_by or (
            existing_grant.granted_by if existing_grant and existing_grant.permissions == grant.permissions else None
        )
        granted_at = grant.granted_at or (
            existing_grant.granted_at if existing_grant and existing_grant.permissions == grant.permissions else None
        )
        if not granted_by:
            granted_by = actor_id
        if not granted_at:
            granted_at = now
        merged.append(
            AccessGrant(
                subject_type=grant.subject_type,
                subject_id=grant.subject_id,
                permissions=tuple(grant.permissions),
                granted_by=granted_by,
                granted_at=granted_at,
            )
        )

    merged.sort(key=lambda grant: (grant.subject_type, grant.subject_id))
    return AccessPolicy(
        visibility=resolved_visibility,
        grants=tuple(merged),
        updated_by=actor_id or existing.updated_by,
        updated_at=now if actor_id else existing.updated_at,
    )


def default_job_access(owner_id: Optional[str]) -> AccessPolicy:
    visibility = "private" if owner_id else "public"
    return AccessPolicy(visibility=visibility, grants=tuple())


def default_library_access() -> AccessPolicy:
    return AccessPolicy(visibility="public", grants=tuple())


__all__ = [
    "AccessGrant",
    "AccessPolicy",
    "can_access",
    "default_job_access",
    "default_library_access",
    "is_admin_role",
    "merge_access_policy",
    "normalize_role",
    "resolve_access_policy",
]
