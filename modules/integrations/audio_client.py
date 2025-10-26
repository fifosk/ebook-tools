"""HTTP client for interacting with the audio synthesis API."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Any, Dict, Mapping, MutableMapping, Optional
from uuid import uuid4

import requests
from pydub import AudioSegment

from modules import logging_manager as log_mgr
from modules.audio.tts import get_voice_display_name
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
        requested_voice_name = get_voice_display_name(voice or "", language or "")
        if requested_voice_name:
            log_attributes["attributes"]["voice_name"] = requested_voice_name
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

        voice_attributes = self._build_voice_attributes(
            response.headers,
            requested_voice=voice,
            language=language,
        )

        success_attributes: Dict[str, Any] = {
            "url": url,
            "status_code": response.status_code,
            "content_length": len(response.content),
        }
        if voice_attributes:
            success_attributes.update(voice_attributes)

        self._logger.info(
            "Audio synthesis request completed",
            extra={
                "event": "integrations.audio.success",
                "attributes": success_attributes,
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

    @staticmethod
    def _build_voice_attributes(
        headers: Mapping[str, str] | None,
        *,
        requested_voice: Optional[str],
        language: Optional[str],
    ) -> Dict[str, Any]:
        """Extract voice-related attributes from response headers."""

        if not headers:
            headers = {}

        normalized: Dict[str, str] = {}
        for key, value in headers.items():
            if value is None:
                continue
            normalized[str(key).lower()] = str(value).strip()

        attributes: Dict[str, Any] = {}

        if requested_voice:
            attributes["requested_voice"] = requested_voice

        resolved_voice = normalized.get("x-selected-voice") or normalized.get(
            "x-resolved-voice"
        )
        if resolved_voice:
            attributes["resolved_voice"] = resolved_voice

        engine = normalized.get("x-synthesis-engine")
        if engine:
            attributes["voice_engine"] = engine

        macos_voice_name = normalized.get("x-macos-voice-name")
        macos_voice_lang = normalized.get("x-macos-voice-lang")
        macos_voice_quality = normalized.get("x-macos-voice-quality")
        macos_voice_gender = normalized.get("x-macos-voice-gender")

        if macos_voice_name:
            attributes["voice_name"] = macos_voice_name
        voice_language = macos_voice_lang or (language or "")
        if voice_language:
            attributes["voice_language"] = voice_language
        if macos_voice_quality:
            attributes["voice_quality"] = macos_voice_quality
        if macos_voice_gender:
            attributes["voice_gender"] = macos_voice_gender

        voice_roles: Dict[str, str] = {}
        for header, role in (
            ("x-voice-source", "source"),
            ("x-source-voice", "source"),
            ("x-voice-translation", "translation"),
            ("x-translation-voice", "translation"),
        ):
            value = normalized.get(header)
            if value:
                voice_roles[role] = value
        if voice_roles:
            attributes["voice_roles"] = voice_roles

        if "voice_name" not in attributes:
            candidate_voice = resolved_voice or requested_voice or ""
            if candidate_voice:
                display_name = get_voice_display_name(candidate_voice, voice_language)
                if display_name:
                    attributes["voice_name"] = display_name

        return attributes
