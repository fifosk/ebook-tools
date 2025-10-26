"""HTTP client for interacting with the audio synthesis API."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Mapping, MutableMapping, Optional
from uuid import uuid4

import requests
from pydub import AudioSegment

from modules import logging_manager as log_mgr
from modules.media.exceptions import MediaBackendError


class AudioAPIClient:
    """Lightweight helper for issuing requests to the audio synthesis API."""

    def __init__(
        self,
        base_url: str,
        *,
        session: Optional[requests.Session] = None,
        timeout: float = 60.0,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url must be a non-empty string")
        self._base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._timeout = timeout
        self._logger = logger or log_mgr.get_logger().getChild("integrations.audio")

    def synthesize(
        self,
        *,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[int] = None,
        language: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
        correlation_id: Optional[str] = None,
        return_metadata: bool = False,
    ) -> AudioSegment | tuple[AudioSegment, Mapping[str, str]]:
        """Send a synthesis request and return the resulting audio segment."""

        payload: MutableMapping[str, object] = {"text": text}
        if voice:
            payload["voice"] = voice
        if speed:
            payload["speed"] = speed
        if language:
            payload["language"] = language

        resolved_headers: MutableMapping[str, str] = {
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        if headers:
            resolved_headers.update({str(k): str(v) for k, v in headers.items()})
        request_id = correlation_id or uuid4().hex
        resolved_headers.setdefault("x-correlation-id", request_id)

        url = f"{self._base_url}/api/audio"
        log_attributes = {
            "event": "integrations.audio.request",
            "attributes": {
                "url": url,
                "voice": voice,
                "language": language,
                "speed": speed,
            },
        }
        self._logger.info("Dispatching audio synthesis request", extra=log_attributes)

        try:
            response = self._session.post(
                url,
                json=payload,
                headers=resolved_headers,
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            self._logger.error(
                "Audio synthesis request failed",
                extra={
                    "event": "integrations.audio.transport_error",
                    "attributes": {"url": url},
                },
                exc_info=True,
            )
            raise MediaBackendError("Audio synthesis request failed") from exc

        if response.status_code >= 400:
            self._logger.error(
                "Audio synthesis returned HTTP %s",
                response.status_code,
                extra={
                    "event": "integrations.audio.error_response",
                    "attributes": {
                        "url": url,
                        "status_code": response.status_code,
                        "body": response.text,
                    },
                },
            )
            raise MediaBackendError(
                f"Audio API responded with status {response.status_code}"
            )

        self._logger.info(
            "Audio synthesis request completed",
            extra={
                "event": "integrations.audio.success",
                "attributes": {
                    "url": url,
                    "status_code": response.status_code,
                    "content_length": len(response.content),
                },
            },
        )

        try:
            buffer = BytesIO(response.content)
            segment = AudioSegment.from_file(buffer, format="mp3")
        except Exception as exc:
            self._logger.error(
                "Failed to decode audio payload",
                extra={"event": "integrations.audio.decode_error"},
                exc_info=True,
            )
            raise MediaBackendError("Failed to decode audio payload") from exc

        if return_metadata:
            return segment, dict(response.headers)
        return segment
