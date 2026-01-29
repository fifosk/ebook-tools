"""Pydantic schemas for push notification API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DeviceRegistrationRequest(BaseModel):
    """Request payload for registering a device token."""

    token: str = Field(..., description="APNs device token (hex string)")
    device_name: str = Field(..., description="Human-readable device name")
    bundle_id: str = Field(..., description="App bundle identifier")
    environment: str = Field("development", description="APNs environment (development or production)")


class DeviceRegistrationResponse(BaseModel):
    """Response for device registration."""

    registered: bool
    device_id: Optional[str] = None


class DeviceInfo(BaseModel):
    """Information about a registered device."""

    device_name: str
    bundle_id: str
    environment: str
    registered_at: str
    last_used_at: str


class NotificationPreferencesRequest(BaseModel):
    """Request payload for updating notification preferences."""

    job_completed: bool = True
    job_failed: bool = True


class NotificationPreferencesResponse(BaseModel):
    """Response containing notification preferences and registered devices."""

    job_completed: bool
    job_failed: bool
    devices: List[DeviceInfo] = Field(default_factory=list)


class TestNotificationResponse(BaseModel):
    """Response for test notification request."""

    sent: int
    failed: int
    message: Optional[str] = None
