"""Schemas for access control payloads."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


AccessPermission = Literal["view", "edit"]
AccessVisibility = Literal["private", "public"]
AccessSubjectType = Literal["user", "role"]


class AccessGrantPayload(BaseModel):
    subject_type: AccessSubjectType = Field(alias="subjectType")
    subject_id: str = Field(alias="subjectId")
    permissions: List[AccessPermission] = Field(default_factory=list)
    granted_by: Optional[str] = Field(default=None, alias="grantedBy")
    granted_at: Optional[str] = Field(default=None, alias="grantedAt")

    model_config = ConfigDict(populate_by_name=True)


class AccessPolicyPayload(BaseModel):
    visibility: AccessVisibility
    grants: List[AccessGrantPayload] = Field(default_factory=list)
    updated_by: Optional[str] = Field(default=None, alias="updatedBy")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class AccessPolicyUpdateRequest(BaseModel):
    visibility: Optional[AccessVisibility] = None
    grants: Optional[List[AccessGrantPayload]] = None

    model_config = ConfigDict(populate_by_name=True)
