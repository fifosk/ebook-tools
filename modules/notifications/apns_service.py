"""Apple Push Notification service client using token-based authentication."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import jwt
except ImportError:
    jwt = None  # type: ignore

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from .. import logging_manager as log_mgr

logger = log_mgr.logger


@dataclass
class APNsConfig:
    """Configuration for APNs service."""

    key_id: str
    team_id: str
    bundle_id: str
    key_path: Path
    environment: str = "development"

    @property
    def apns_host(self) -> str:
        """Return the APNs host based on environment."""
        if self.environment == "production":
            return "api.push.apple.com"
        return "api.sandbox.push.apple.com"

    def is_valid(self) -> bool:
        """Check if the configuration has all required fields."""
        return bool(
            self.key_id
            and self.team_id
            and self.bundle_id
            and self.key_path
            and self.key_path.exists()
        )


@dataclass
class APNsResponse:
    """Response from APNs for a single notification."""

    success: bool
    device_token: str
    status_code: int = 200
    reason: Optional[str] = None
    apns_id: Optional[str] = None

    @property
    def is_unregistered(self) -> bool:
        """Check if the device token is invalid or unregistered."""
        return self.reason in (
            "BadDeviceToken",
            "Unregistered",
            "ExpiredToken",
            "DeviceTokenNotForTopic",
        )


@dataclass
class NotificationRequest:
    """Request to send a single push notification."""

    device_token: str
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    sound: str = "default"
    badge: Optional[int] = None
    category: Optional[str] = None
    thread_id: Optional[str] = None
    mutable_content: bool = False  # Enable Notification Service Extension


class APNsService:
    """Send push notifications via Apple's HTTP/2 APNs API."""

    # JWT tokens are valid for up to 1 hour, refresh at 50 minutes
    JWT_REFRESH_INTERVAL = 50 * 60

    def __init__(self, config: APNsConfig) -> None:
        self._config = config
        self._jwt_token: Optional[str] = None
        self._jwt_expires_at: float = 0
        self._private_key: Optional[str] = None

        if config.is_valid():
            self._load_private_key()

    def _load_private_key(self) -> None:
        """Load the private key from the .p8 file."""
        try:
            self._private_key = self._config.key_path.read_text()
        except Exception as e:
            logger.error("Failed to load APNs private key: %s", e)
            self._private_key = None

    def _generate_jwt(self) -> Optional[str]:
        """Generate a new JWT token for APNs authentication."""
        if jwt is None:
            logger.error("PyJWT not installed; cannot generate APNs token")
            return None

        if not self._private_key:
            logger.error("APNs private key not loaded")
            return None

        now = int(time.time())

        headers = {
            "alg": "ES256",
            "kid": self._config.key_id,
        }

        payload = {
            "iss": self._config.team_id,
            "iat": now,
        }

        try:
            token = jwt.encode(payload, self._private_key, algorithm="ES256", headers=headers)
            self._jwt_token = token
            self._jwt_expires_at = now + self.JWT_REFRESH_INTERVAL
            return token
        except Exception as e:
            logger.error("Failed to generate APNs JWT: %s", e)
            return None

    def _get_jwt(self) -> Optional[str]:
        """Get a valid JWT token, refreshing if necessary."""
        now = time.time()
        if self._jwt_token and now < self._jwt_expires_at:
            return self._jwt_token
        return self._generate_jwt()

    def _build_payload(self, request: NotificationRequest) -> Dict[str, Any]:
        """Build the APNs payload from a notification request."""
        alert = {
            "title": request.title,
            "body": request.body,
        }

        aps: Dict[str, Any] = {
            "alert": alert,
            "sound": request.sound,
        }

        if request.badge is not None:
            aps["badge"] = request.badge

        if request.category:
            aps["category"] = request.category

        if request.thread_id:
            aps["thread-id"] = request.thread_id

        if request.mutable_content:
            aps["mutable-content"] = 1

        payload: Dict[str, Any] = {"aps": aps}

        if request.data:
            payload.update(request.data)

        return payload

    async def send_notification(self, request: NotificationRequest) -> APNsResponse:
        """Send a single push notification."""
        if httpx is None:
            logger.error("httpx not installed; cannot send APNs notification")
            return APNsResponse(
                success=False,
                device_token=request.device_token,
                status_code=0,
                reason="httpx_not_installed",
            )

        if not self._config.is_valid():
            logger.error("APNs configuration is invalid")
            return APNsResponse(
                success=False,
                device_token=request.device_token,
                status_code=0,
                reason="invalid_config",
            )

        token = self._get_jwt()
        if not token:
            return APNsResponse(
                success=False,
                device_token=request.device_token,
                status_code=0,
                reason="jwt_generation_failed",
            )

        url = f"https://{self._config.apns_host}/3/device/{request.device_token}"
        payload = self._build_payload(request)

        headers = {
            "authorization": f"bearer {token}",
            "apns-topic": self._config.bundle_id,
            "apns-push-type": "alert",
            "apns-priority": "10",
        }

        try:
            async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)

                apns_id = response.headers.get("apns-id")

                if response.status_code == 200:
                    logger.debug(
                        "APNs notification sent successfully to %s",
                        request.device_token[:16] + "...",
                    )
                    return APNsResponse(
                        success=True,
                        device_token=request.device_token,
                        status_code=response.status_code,
                        apns_id=apns_id,
                    )

                # Parse error response
                try:
                    error_body = response.json()
                    reason = error_body.get("reason", "unknown")
                except Exception:
                    reason = f"http_{response.status_code}"

                logger.warning(
                    "APNs notification failed for %s: %s (status %d)",
                    request.device_token[:16] + "...",
                    reason,
                    response.status_code,
                )

                return APNsResponse(
                    success=False,
                    device_token=request.device_token,
                    status_code=response.status_code,
                    reason=reason,
                    apns_id=apns_id,
                )

        except Exception as e:
            logger.error("APNs request failed: %s", e)
            return APNsResponse(
                success=False,
                device_token=request.device_token,
                status_code=0,
                reason=str(e),
            )

    async def send_batch(self, requests: List[NotificationRequest]) -> List[APNsResponse]:
        """Send multiple notifications efficiently."""
        if not requests:
            return []

        results: List[APNsResponse] = []
        for request in requests:
            result = await self.send_notification(request)
            results.append(result)

        return results
