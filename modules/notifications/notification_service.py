"""High-level notification dispatch service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from .apns_service import APNsConfig, APNsService, APNsResponse, NotificationRequest
from ..user_management.user_store_base import UserStoreBase
from .. import logging_manager as log_mgr

logger = log_mgr.logger


@dataclass
class NotificationResult:
    """Result of sending notifications to a user's devices."""

    sent: int
    failed: int
    reason: Optional[str] = None
    invalid_tokens: Optional[List[str]] = None


class NotificationService:
    """Orchestrate push notification delivery to user devices."""

    def __init__(
        self,
        apns_service: Optional[APNsService],
        user_store: UserStoreBase,
        api_base_url: Optional[str] = None,
    ) -> None:
        self._apns = apns_service
        self._user_store = user_store
        self._api_base_url = (api_base_url or "").rstrip("/")

    @property
    def is_enabled(self) -> bool:
        """Check if push notifications are enabled."""
        return self._apns is not None

    def _get_user_tokens(self, user_id: str) -> List[Dict[str, Any]]:
        """Get device tokens for a user."""
        user = self._user_store.get_user(user_id)
        if not user:
            return []
        return user.metadata.get("apns_device_tokens", [])

    def _get_user_preferences(self, user_id: str) -> Dict[str, bool]:
        """Get notification preferences for a user."""
        user = self._user_store.get_user(user_id)
        if not user:
            return {"job_completed": True, "job_failed": True}
        return user.metadata.get(
            "notification_preferences",
            {"job_completed": True, "job_failed": True},
        )

    def _cleanup_invalid_tokens(self, user_id: str, invalid_tokens: Set[str]) -> None:
        """Remove invalid device tokens from user metadata."""
        if not invalid_tokens:
            return

        user = self._user_store.get_user(user_id)
        if not user:
            return

        tokens = user.metadata.get("apns_device_tokens", [])
        updated_tokens = [t for t in tokens if t.get("token") not in invalid_tokens]

        if len(updated_tokens) != len(tokens):
            metadata = dict(user.metadata)
            metadata["apns_device_tokens"] = updated_tokens
            try:
                self._user_store.update_user(user_id, metadata=metadata)
                logger.info(
                    "Removed %d invalid device tokens for user %s",
                    len(tokens) - len(updated_tokens),
                    user_id,
                )
            except Exception as e:
                logger.error("Failed to cleanup invalid tokens: %s", e)

    async def notify_job_completed(
        self,
        user_id: str,
        job_id: str,
        job_label: Optional[str],
        status: str,
        *,
        subtitle: Optional[str] = None,
        cover_url: Optional[str] = None,
        input_language: Optional[str] = None,
        target_language: Optional[str] = None,
        chapter_count: Optional[int] = None,
        sentence_count: Optional[int] = None,
    ) -> NotificationResult:
        """Send job completion notification to all user devices.

        Args:
            user_id: The user to notify
            job_id: The job ID
            job_label: The job title/label for the notification body
            status: Job status ("completed" or "failed")
            subtitle: Optional subtitle (e.g., author name)
            cover_url: Optional cover image URL for rich notifications
            input_language: Optional source language code
            target_language: Optional target language code
            chapter_count: Optional number of chapters
            sentence_count: Optional number of sentences
        """
        if not self.is_enabled:
            return NotificationResult(sent=0, failed=0, reason="notifications_disabled")

        user = self._user_store.get_user(user_id)
        if not user:
            logger.debug("User %s not found for notification", user_id)
            return NotificationResult(sent=0, failed=0, reason="user_not_found")

        tokens = user.metadata.get("apns_device_tokens", [])
        if not tokens:
            logger.debug("No device tokens registered for user %s", user_id)
            return NotificationResult(sent=0, failed=0, reason="no_devices")

        prefs = user.metadata.get(
            "notification_preferences",
            {"job_completed": True, "job_failed": True},
        )

        # Check preferences
        if status == "completed" and not prefs.get("job_completed", True):
            logger.debug("Job completed notifications disabled for user %s", user_id)
            return NotificationResult(sent=0, failed=0, reason="disabled_by_preference")

        if status == "failed" and not prefs.get("job_failed", True):
            logger.debug("Job failed notifications disabled for user %s", user_id)
            return NotificationResult(sent=0, failed=0, reason="disabled_by_preference")

        # Build notification content
        if status == "completed":
            title = "Job Complete"
            body = job_label or f"Job {job_id[:8]}... has finished successfully"
        else:
            title = "Job Failed"
            body = job_label or f"Job {job_id[:8]}... encountered an error"

        # Custom data for deep linking and rich notification content
        data: Dict[str, Any] = {
            "job_id": job_id,
            "action": "open_job",
            "status": status,
        }

        # Add optional metadata for rich notifications
        if job_label:
            data["title"] = job_label
        if subtitle:
            data["subtitle"] = subtitle
        if input_language:
            data["input_language"] = input_language
        if target_language:
            data["target_language"] = target_language
        if chapter_count is not None:
            data["chapter_count"] = chapter_count
        if sentence_count is not None:
            data["sentence_count"] = sentence_count

        # Build full cover URL if we have a base URL and relative cover path
        full_cover_url: Optional[str] = None
        if cover_url:
            if cover_url.startswith(("http://", "https://")):
                full_cover_url = cover_url
            elif self._api_base_url:
                # Ensure cover_url starts with / for proper joining
                if not cover_url.startswith("/"):
                    cover_url = "/" + cover_url
                full_cover_url = f"{self._api_base_url}{cover_url}"

        if full_cover_url:
            data["cover_url"] = full_cover_url

        # Enable mutable_content if we have a cover URL (for Notification Service Extension)
        has_rich_content = bool(full_cover_url)

        # Build notification requests for all devices
        requests = [
            NotificationRequest(
                device_token=t["token"],
                title=title,
                body=body,
                data=data,
                thread_id=f"job-{job_id}",
                mutable_content=has_rich_content,
            )
            for t in tokens
            if t.get("token")
        ]

        if not requests:
            return NotificationResult(sent=0, failed=0, reason="no_valid_tokens")

        # Send notifications
        results = await self._apns.send_batch(requests)

        # Count successes and failures
        sent = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)

        # Collect invalid tokens for cleanup
        invalid_tokens = {r.device_token for r in results if r.is_unregistered}
        if invalid_tokens:
            self._cleanup_invalid_tokens(user_id, invalid_tokens)

        logger.info(
            "Sent %d/%d notifications for job %s to user %s",
            sent,
            len(requests),
            job_id[:8],
            user_id,
        )

        return NotificationResult(
            sent=sent,
            failed=failed,
            invalid_tokens=list(invalid_tokens) if invalid_tokens else None,
        )

    async def send_test_notification(self, user_id: str) -> NotificationResult:
        """Send a test notification to all user devices."""
        if not self.is_enabled:
            return NotificationResult(sent=0, failed=0, reason="notifications_disabled")

        user = self._user_store.get_user(user_id)
        if not user:
            return NotificationResult(sent=0, failed=0, reason="user_not_found")

        tokens = user.metadata.get("apns_device_tokens", [])
        if not tokens:
            return NotificationResult(sent=0, failed=0, reason="no_devices")

        requests = [
            NotificationRequest(
                device_token=t["token"],
                title="Test Notification",
                body="Push notifications are working correctly!",
                data={"action": "test", "timestamp": datetime.now(timezone.utc).isoformat()},
            )
            for t in tokens
            if t.get("token")
        ]

        if not requests:
            return NotificationResult(sent=0, failed=0, reason="no_valid_tokens")

        results = await self._apns.send_batch(requests)

        sent = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)

        invalid_tokens = {r.device_token for r in results if r.is_unregistered}
        if invalid_tokens:
            self._cleanup_invalid_tokens(user_id, invalid_tokens)

        return NotificationResult(
            sent=sent,
            failed=failed,
            invalid_tokens=list(invalid_tokens) if invalid_tokens else None,
        )

    async def send_rich_test_notification(
        self,
        user_id: str,
        *,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        cover_url: Optional[str] = None,
    ) -> NotificationResult:
        """Send a rich test notification with cover image to all user devices.

        Args:
            user_id: The user to notify
            title: Custom title (default: "Rich Test Notification")
            subtitle: Custom subtitle (default: "Author Name")
            cover_url: Cover image URL (default: sample cover)
        """
        if not self.is_enabled:
            return NotificationResult(sent=0, failed=0, reason="notifications_disabled")

        user = self._user_store.get_user(user_id)
        if not user:
            return NotificationResult(sent=0, failed=0, reason="user_not_found")

        tokens = user.metadata.get("apns_device_tokens", [])
        if not tokens:
            return NotificationResult(sent=0, failed=0, reason="no_devices")

        # Default values for rich notification
        notification_title = title or "Sample Book Title"
        notification_subtitle = subtitle or "Sample Author"

        # Build full cover URL
        full_cover_url: Optional[str] = None
        if cover_url:
            if cover_url.startswith(("http://", "https://")):
                full_cover_url = cover_url
            elif self._api_base_url:
                if not cover_url.startswith("/"):
                    cover_url = "/" + cover_url
                full_cover_url = f"{self._api_base_url}{cover_url}"
        else:
            # Use a public placeholder image for testing
            # This is an Open Library cover image that's publicly accessible
            full_cover_url = "https://covers.openlibrary.org/b/id/8739161-L.jpg"

        # Build notification data with sample metadata (mimics job completion)
        data: Dict[str, Any] = {
            "action": "test_rich",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": notification_title,
            "subtitle": notification_subtitle,
            "input_language": "English",
            "target_language": "Arabic",
            "chapter_count": 12,
            "sentence_count": 1547,
        }

        if full_cover_url:
            data["cover_url"] = full_cover_url

        has_rich_content = bool(full_cover_url)

        requests = [
            NotificationRequest(
                device_token=t["token"],
                title="Job Complete",
                body=notification_title,
                data=data,
                thread_id="test-rich-notification",
                mutable_content=has_rich_content,
            )
            for t in tokens
            if t.get("token")
        ]

        if not requests:
            return NotificationResult(sent=0, failed=0, reason="no_valid_tokens")

        results = await self._apns.send_batch(requests)

        sent = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)

        invalid_tokens = {r.device_token for r in results if r.is_unregistered}
        if invalid_tokens:
            self._cleanup_invalid_tokens(user_id, invalid_tokens)

        return NotificationResult(
            sent=sent,
            failed=failed,
            invalid_tokens=list(invalid_tokens) if invalid_tokens else None,
        )

    def register_device_token(
        self,
        user_id: str,
        token: str,
        device_name: str,
        bundle_id: str,
        environment: str = "development",
    ) -> bool:
        """Register a device token for push notifications."""
        user = self._user_store.get_user(user_id)
        if not user:
            logger.warning("Cannot register device token: user %s not found", user_id)
            return False

        tokens: List[Dict[str, Any]] = list(user.metadata.get("apns_device_tokens", []))
        now = datetime.now(timezone.utc).isoformat()

        # Check if token already exists
        existing = next((t for t in tokens if t.get("token") == token), None)

        if existing:
            # Update existing token
            existing["device_name"] = device_name
            existing["last_used_at"] = now
            existing["bundle_id"] = bundle_id
            existing["environment"] = environment
        else:
            # Add new token
            tokens.append({
                "token": token,
                "device_name": device_name,
                "bundle_id": bundle_id,
                "environment": environment,
                "created_at": now,
                "last_used_at": now,
            })

        metadata = dict(user.metadata)
        metadata["apns_device_tokens"] = tokens

        try:
            self._user_store.update_user(user_id, metadata=metadata)
            logger.info("Registered device token for user %s: %s", user_id, device_name)
            return True
        except Exception as e:
            logger.error("Failed to register device token: %s", e)
            return False

    def unregister_device_token(self, user_id: str, token: str) -> bool:
        """Remove a device token for a user."""
        user = self._user_store.get_user(user_id)
        if not user:
            return False

        tokens = user.metadata.get("apns_device_tokens", [])
        updated_tokens = [t for t in tokens if t.get("token") != token]

        if len(updated_tokens) == len(tokens):
            # Token not found
            return False

        metadata = dict(user.metadata)
        metadata["apns_device_tokens"] = updated_tokens

        try:
            self._user_store.update_user(user_id, metadata=metadata)
            logger.info("Unregistered device token for user %s", user_id)
            return True
        except Exception as e:
            logger.error("Failed to unregister device token: %s", e)
            return False

    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get notification preferences and device list for a user."""
        user = self._user_store.get_user(user_id)
        if not user:
            return {
                "job_completed": True,
                "job_failed": True,
                "devices": [],
            }

        prefs = user.metadata.get(
            "notification_preferences",
            {"job_completed": True, "job_failed": True},
        )
        tokens = user.metadata.get("apns_device_tokens", [])

        devices = [
            {
                "device_name": t.get("device_name", "Unknown Device"),
                "bundle_id": t.get("bundle_id", ""),
                "environment": t.get("environment", "development"),
                "registered_at": t.get("created_at", ""),
                "last_used_at": t.get("last_used_at", ""),
            }
            for t in tokens
        ]

        return {
            "job_completed": prefs.get("job_completed", True),
            "job_failed": prefs.get("job_failed", True),
            "devices": devices,
        }

    def update_preferences(
        self,
        user_id: str,
        job_completed: Optional[bool] = None,
        job_failed: Optional[bool] = None,
    ) -> bool:
        """Update notification preferences for a user."""
        user = self._user_store.get_user(user_id)
        if not user:
            return False

        prefs = dict(user.metadata.get(
            "notification_preferences",
            {"job_completed": True, "job_failed": True},
        ))

        if job_completed is not None:
            prefs["job_completed"] = job_completed
        if job_failed is not None:
            prefs["job_failed"] = job_failed

        metadata = dict(user.metadata)
        metadata["notification_preferences"] = prefs

        try:
            self._user_store.update_user(user_id, metadata=metadata)
            logger.info("Updated notification preferences for user %s", user_id)
            return True
        except Exception as e:
            logger.error("Failed to update notification preferences: %s", e)
            return False
