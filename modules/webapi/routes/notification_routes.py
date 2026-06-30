"""API routes for push notification management."""

from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from modules import logging_manager as log_mgr

from ..dependencies import get_notification_service, get_request_user, RequestUserContext
from ..route_telemetry import log_started_route_result
from ...notifications import (
    NotificationService,
    DeviceRegistrationRequest,
    DeviceRegistrationResponse,
    DeviceUnregistrationResponse,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateResponse,
    DeviceInfo,
    TestNotificationResponse,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
logger = log_mgr.get_logger()

NOTIFICATION_UNAVAILABLE_MESSAGE = "Unable to sync notification settings."
NOTIFICATION_DEVICE_TOKEN_NOT_FOUND_MESSAGE = "Device token not found"


def _notification_result_from_http_error(exc: HTTPException) -> str:
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return "unauthorized"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        return "not_found"
    if exc.status_code == status.HTTP_400_BAD_REQUEST:
        return "invalid"
    return "error"


def _log_notification_route_result(
    *,
    operation: str,
    result: str,
    started_at: float,
    sent: int | None = None,
    failed: int | None = None,
    devices: int | None = None,
) -> None:
    log_started_route_result(
        logger,
        metric_name="NOTIFICATION_ROUTE_DURATION",
        message="Notification route",
        operation=operation,
        result=result,
        started_at=started_at,
        sent=max(0, sent) if sent is not None else None,
        failed=max(0, failed) if failed is not None else None,
        devices=max(0, devices) if devices is not None else None,
    )


def _raise_notification_unavailable(*, operation: str, started_at: float) -> None:
    _log_notification_route_result(
        operation=operation,
        result="error",
        started_at=started_at,
    )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=NOTIFICATION_UNAVAILABLE_MESSAGE,
    )


def _normalize_route_id(value: str) -> str:
    return value.strip()


def _raise_device_token_not_found(*, operation: str, started_at: float) -> None:
    _log_notification_route_result(
        operation=operation,
        result="not_found",
        started_at=started_at,
    )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=NOTIFICATION_DEVICE_TOKEN_NOT_FOUND_MESSAGE,
    )


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
    started_at = time.perf_counter()
    try:
        user_id = _require_authenticated_user(user)
    except HTTPException as exc:
        _log_notification_route_result(
            operation="register_device",
            result=_notification_result_from_http_error(exc),
            started_at=started_at,
        )
        raise
    normalized_token = request.token.strip()
    if not normalized_token:
        _log_notification_route_result(
            operation="register_device",
            result="invalid",
            started_at=started_at,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device token is required",
        )

    try:
        success = notification_service.register_device_token(
            user_id=user_id,
            token=normalized_token,
            device_name=request.device_name,
            bundle_id=request.bundle_id,
            environment=request.environment,
        )
    except Exception:
        _raise_notification_unavailable(operation="register_device", started_at=started_at)

    if not success:
        _log_notification_route_result(
            operation="register_device",
            result="error",
            started_at=started_at,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register device token",
        )

    _log_notification_route_result(
        operation="register_device",
        result="success",
        started_at=started_at,
        devices=1,
    )
    return DeviceRegistrationResponse(registered=True, device_id=normalized_token[:16])


@router.delete("/devices/{device_id}", response_model=DeviceUnregistrationResponse)
async def unregister_device(
    device_id: str,
    user: RequestUserContext = Depends(get_request_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> DeviceUnregistrationResponse:
    """Remove a device token."""
    started_at = time.perf_counter()
    try:
        user_id = _require_authenticated_user(user)
    except HTTPException as exc:
        _log_notification_route_result(
            operation="unregister_device",
            result=_notification_result_from_http_error(exc),
            started_at=started_at,
        )
        raise
    normalized_device_id = _normalize_route_id(device_id)
    if not normalized_device_id:
        _raise_device_token_not_found(
            operation="unregister_device",
            started_at=started_at,
        )

    try:
        success = notification_service.unregister_device_token(
            user_id=user_id,
            token=normalized_device_id,
        )
    except Exception:
        _raise_notification_unavailable(operation="unregister_device", started_at=started_at)

    if not success:
        _log_notification_route_result(
            operation="unregister_device",
            result="not_found",
            started_at=started_at,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOTIFICATION_DEVICE_TOKEN_NOT_FOUND_MESSAGE,
        )

    response_payload = DeviceUnregistrationResponse(unregistered=True)
    _log_notification_route_result(
        operation="unregister_device",
        result="success",
        started_at=started_at,
    )
    return response_payload


@router.post("/test", response_model=TestNotificationResponse)
async def send_test_notification(
    user: RequestUserContext = Depends(get_request_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> TestNotificationResponse:
    """Send a test notification to all registered devices."""
    started_at = time.perf_counter()
    try:
        user_id = _require_authenticated_user(user)
    except HTTPException as exc:
        _log_notification_route_result(
            operation="test",
            result=_notification_result_from_http_error(exc),
            started_at=started_at,
        )
        raise

    if not notification_service.is_enabled:
        _log_notification_route_result(
            operation="test",
            result="disabled",
            started_at=started_at,
        )
        return TestNotificationResponse(
            sent=0,
            failed=0,
            message="Push notifications are not configured on the server",
        )

    try:
        result = await notification_service.send_test_notification(user_id)
    except Exception:
        _raise_notification_unavailable(operation="test", started_at=started_at)

    if result.reason == "no_devices":
        _log_notification_route_result(
            operation="test",
            result="no_devices",
            started_at=started_at,
            sent=result.sent,
            failed=result.failed,
        )
        return TestNotificationResponse(
            sent=0,
            failed=0,
            message="No devices registered. Enable notifications on your device first.",
        )

    _log_notification_route_result(
        operation="test",
        result="success",
        started_at=started_at,
        sent=result.sent,
        failed=result.failed,
    )
    return TestNotificationResponse(
        sent=result.sent,
        failed=result.failed,
        message=f"Sent to {result.sent} device(s)" if result.sent > 0 else result.reason,
    )


@router.post("/test/rich", response_model=TestNotificationResponse)
async def send_rich_test_notification(
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    cover_url: Optional[str] = None,
    user: RequestUserContext = Depends(get_request_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> TestNotificationResponse:
    """Send a rich test notification with cover image to all registered devices.

    This endpoint sends a notification that mimics a job completion notification,
    including cover art that will be downloaded by the Notification Service Extension.
    """
    started_at = time.perf_counter()
    try:
        user_id = _require_authenticated_user(user)
    except HTTPException as exc:
        _log_notification_route_result(
            operation="rich_test",
            result=_notification_result_from_http_error(exc),
            started_at=started_at,
        )
        raise

    if not notification_service.is_enabled:
        _log_notification_route_result(
            operation="rich_test",
            result="disabled",
            started_at=started_at,
        )
        return TestNotificationResponse(
            sent=0,
            failed=0,
            message="Push notifications are not configured on the server",
        )

    try:
        result = await notification_service.send_rich_test_notification(
            user_id,
            title=title,
            subtitle=subtitle,
            cover_url=cover_url,
        )
    except Exception:
        _raise_notification_unavailable(operation="rich_test", started_at=started_at)

    if result.reason == "no_devices":
        _log_notification_route_result(
            operation="rich_test",
            result="no_devices",
            started_at=started_at,
            sent=result.sent,
            failed=result.failed,
        )
        return TestNotificationResponse(
            sent=0,
            failed=0,
            message="No devices registered. Enable notifications on your device first.",
        )

    _log_notification_route_result(
        operation="rich_test",
        result="success",
        started_at=started_at,
        sent=result.sent,
        failed=result.failed,
    )
    return TestNotificationResponse(
        sent=result.sent,
        failed=result.failed,
        message=f"Rich notification sent to {result.sent} device(s)" if result.sent > 0 else result.reason,
    )


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_preferences(
    user: RequestUserContext = Depends(get_request_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationPreferencesResponse:
    """Get notification preferences for the current user."""
    started_at = time.perf_counter()
    try:
        user_id = _require_authenticated_user(user)
    except HTTPException as exc:
        _log_notification_route_result(
            operation="preferences_get",
            result=_notification_result_from_http_error(exc),
            started_at=started_at,
        )
        raise

    try:
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
        response_payload = NotificationPreferencesResponse(
            job_completed=prefs.get("job_completed", True),
            job_failed=prefs.get("job_failed", True),
            devices=devices,
        )
    except Exception:
        _raise_notification_unavailable(operation="preferences_get", started_at=started_at)

    _log_notification_route_result(
        operation="preferences_get",
        result="success",
        started_at=started_at,
        devices=len(devices),
    )
    return response_payload


@router.put("/preferences", response_model=NotificationPreferencesUpdateResponse)
async def update_preferences(
    request: NotificationPreferencesRequest,
    user: RequestUserContext = Depends(get_request_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationPreferencesUpdateResponse:
    """Update notification preferences."""
    started_at = time.perf_counter()
    try:
        user_id = _require_authenticated_user(user)
    except HTTPException as exc:
        _log_notification_route_result(
            operation="preferences_update",
            result=_notification_result_from_http_error(exc),
            started_at=started_at,
        )
        raise

    try:
        success = notification_service.update_preferences(
            user_id=user_id,
            job_completed=request.job_completed,
            job_failed=request.job_failed,
        )
    except Exception:
        _raise_notification_unavailable(operation="preferences_update", started_at=started_at)

    if not success:
        _log_notification_route_result(
            operation="preferences_update",
            result="error",
            started_at=started_at,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences",
        )

    response_payload = NotificationPreferencesUpdateResponse(updated=True)
    _log_notification_route_result(
        operation="preferences_update",
        result="success",
        started_at=started_at,
    )
    return response_payload
