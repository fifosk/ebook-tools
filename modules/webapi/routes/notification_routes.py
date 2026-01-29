"""API routes for push notification management."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_notification_service, get_request_user, RequestUserContext
from ...notifications import (
    NotificationService,
    DeviceRegistrationRequest,
    DeviceRegistrationResponse,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
    DeviceInfo,
    TestNotificationResponse,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _require_authenticated_user(user: RequestUserContext) -> str:
    """Ensure the user is authenticated and return the user ID."""
    if not user.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user.user_id


@router.post("/devices", response_model=DeviceRegistrationResponse)
async def register_device(
    request: DeviceRegistrationRequest,
    user: RequestUserContext = Depends(get_request_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> DeviceRegistrationResponse:
    """Register a device token for push notifications."""
    user_id = _require_authenticated_user(user)

    success = notification_service.register_device_token(
        user_id=user_id,
        token=request.token,
        device_name=request.device_name,
        bundle_id=request.bundle_id,
        environment=request.environment,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register device token",
        )

    return DeviceRegistrationResponse(registered=True, device_id=request.token[:16])


@router.delete("/devices/{token}")
async def unregister_device(
    token: str,
    user: RequestUserContext = Depends(get_request_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> dict:
    """Remove a device token."""
    user_id = _require_authenticated_user(user)

    success = notification_service.unregister_device_token(
        user_id=user_id,
        token=token,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device token not found",
        )

    return {"unregistered": True}


@router.post("/test", response_model=TestNotificationResponse)
async def send_test_notification(
    user: RequestUserContext = Depends(get_request_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> TestNotificationResponse:
    """Send a test notification to all registered devices."""
    user_id = _require_authenticated_user(user)

    if not notification_service.is_enabled:
        return TestNotificationResponse(
            sent=0,
            failed=0,
            message="Push notifications are not configured on the server",
        )

    result = await notification_service.send_test_notification(user_id)

    if result.reason == "no_devices":
        return TestNotificationResponse(
            sent=0,
            failed=0,
            message="No devices registered. Enable notifications on your device first.",
        )

    return TestNotificationResponse(
        sent=result.sent,
        failed=result.failed,
        message=f"Sent to {result.sent} device(s)" if result.sent > 0 else result.reason,
    )


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_preferences(
    user: RequestUserContext = Depends(get_request_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationPreferencesResponse:
    """Get notification preferences for the current user."""
    user_id = _require_authenticated_user(user)

    prefs = notification_service.get_preferences(user_id)

    devices = [
        DeviceInfo(
            device_name=d["device_name"],
            bundle_id=d["bundle_id"],
            environment=d["environment"],
            registered_at=d["registered_at"],
            last_used_at=d["last_used_at"],
        )
        for d in prefs.get("devices", [])
    ]

    return NotificationPreferencesResponse(
        job_completed=prefs.get("job_completed", True),
        job_failed=prefs.get("job_failed", True),
        devices=devices,
    )


@router.put("/preferences")
async def update_preferences(
    request: NotificationPreferencesRequest,
    user: RequestUserContext = Depends(get_request_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> dict:
    """Update notification preferences."""
    user_id = _require_authenticated_user(user)

    success = notification_service.update_preferences(
        user_id=user_id,
        job_completed=request.job_completed,
        job_failed=request.job_failed,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences",
        )

    return {"updated": True}
