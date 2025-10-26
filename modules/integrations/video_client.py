"""HTTP client utilities for the video rendering API."""

from __future__ import annotations

import base64
import logging
import time
from io import BytesIO
from typing import Iterable, Mapping, MutableMapping, Optional, Sequence
from uuid import uuid4

import requests
from pydub import AudioSegment

from modules import logging_manager as log_mgr
from modules.media.exceptions import MediaBackendError


class VideoAPIClient:
    """Wrapper around the web API video rendering endpoints."""

    def __init__(
        self,
        base_url: str,
        *,
        session: Optional[requests.Session] = None,
        timeout: float = 300.0,
        poll_interval: float = 2.0,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url must be a non-empty string")
        self._base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._timeout = timeout
        self._poll_interval = poll_interval
        self._logger = logger or log_mgr.get_logger().getChild("integrations.video")

    def render(
        self,
        *,
        slides: Sequence[str],
        audio_segments: Sequence[AudioSegment],
        options: Mapping[str, object],
        output_filename: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
        correlation_id: Optional[str] = None,
    ) -> Mapping[str, object]:
        """Submit a rendering job and block until completion."""

        if len(slides) != len(audio_segments):
            raise ValueError("Slides and audio_segments must have matching lengths")

        request_headers: MutableMapping[str, str] = {
            "content-type": "application/json",
        }
        if headers:
            request_headers.update({str(k): str(v) for k, v in headers.items()})
        request_id = correlation_id or uuid4().hex
        request_headers.setdefault("x-correlation-id", request_id)

        payload = {
            "slides": list(slides),
            "audio": [self._encode_audio(segment) for segment in audio_segments],
            "options": dict(options),
        }
        if output_filename:
            payload["output_filename"] = output_filename

        submit_url = f"{self._base_url}/api/video"
        self._logger.info(
            "Submitting video rendering job",
            extra={
                "event": "integrations.video.submit",
                "attributes": {
                    "url": submit_url,
                    "slides": len(slides),
                    "audio_tracks": len(audio_segments),
                },
            },
        )

        try:
            response = self._session.post(
                submit_url,
                json=payload,
                headers=request_headers,
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            self._logger.error(
                "Video job submission failed",
                extra={
                    "event": "integrations.video.transport_error",
                    "attributes": {"url": submit_url},
                },
                exc_info=True,
            )
            raise MediaBackendError("Video job submission failed") from exc

        if response.status_code >= 400:
            self._logger.error(
                "Video job rejected with status %s",
                response.status_code,
                extra={
                    "event": "integrations.video.error_response",
                    "attributes": {
                        "url": submit_url,
                        "status_code": response.status_code,
                        "body": response.text,
                    },
                },
            )
            raise MediaBackendError(
                f"Video API responded with status {response.status_code}"
            )

        submission = response.json()
        job_id = submission.get("job_id")
        if not job_id:
            raise MediaBackendError("Video API response missing job_id")

        self._logger.info(
            "Video job %s accepted",
            job_id,
            extra={
                "event": "integrations.video.accepted",
                "attributes": {"job_id": job_id},
            },
        )

        deadline = time.monotonic() + self._timeout
        status_url = f"{self._base_url}/api/video/{job_id}"
        while time.monotonic() < deadline:
            try:
                status_resp = self._session.get(
                    status_url,
                    headers=request_headers,
                    timeout=self._poll_interval,
                )
            except requests.RequestException as exc:
                self._logger.warning(
                    "Video job status check failed",
                    extra={
                        "event": "integrations.video.status_error",
                        "attributes": {"job_id": job_id},
                    },
                    exc_info=True,
                )
                time.sleep(self._poll_interval)
                continue

            if status_resp.status_code >= 400:
                self._logger.warning(
                    "Video job status request returned HTTP %s",
                    status_resp.status_code,
                    extra={
                        "event": "integrations.video.status_http_error",
                        "attributes": {
                            "job_id": job_id,
                            "status_code": status_resp.status_code,
                        },
                    },
                )
                time.sleep(self._poll_interval)
                continue

            payload = status_resp.json()
            status = payload.get("status", "").lower()
            if status in {"completed", "failed"}:
                if status == "failed":
                    message = payload.get("error") or "Video rendering failed"
                    self._logger.error(
                        "Video job %s failed",
                        job_id,
                        extra={
                            "event": "integrations.video.failed",
                            "attributes": {"job_id": job_id},
                        },
                    )
                    raise MediaBackendError(message)
                self._logger.info(
                    "Video job %s completed",
                    job_id,
                    extra={
                        "event": "integrations.video.completed",
                        "attributes": {"job_id": job_id},
                    },
                )
                return payload

            time.sleep(self._poll_interval)

        raise MediaBackendError("Timed out waiting for video job completion")

    def concatenate(
        self,
        video_paths: Iterable[str],
        *,
        options: Mapping[str, object] | None = None,
        headers: Optional[Mapping[str, str]] = None,
        correlation_id: Optional[str] = None,
    ) -> Mapping[str, object]:
        """Delegate concatenation to the video API using a synthetic job."""

        slides = ["" for _ in video_paths]
        audio_segments: list[AudioSegment] = []
        payload_options = dict(options or {})
        payload_options["video_paths"] = list(video_paths)
        return self.render(
            slides=slides,
            audio_segments=audio_segments,
            options=payload_options,
            output_filename=None,
            headers=headers,
            correlation_id=correlation_id,
        )

    def _encode_audio(self, segment: AudioSegment) -> Mapping[str, object]:
        buffer = BytesIO()
        segment.export(buffer, format="mp3")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return {"data": encoded, "mime_type": "audio/mpeg", "format": "mp3"}

__all__ = ["VideoAPIClient"]
