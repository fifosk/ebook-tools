"""Draw Things / Stable Diffusion HTTP client helpers."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple
from urllib.parse import urljoin

import requests


class DrawThingsError(RuntimeError):
    """Raised when the Draw Things API returns an error or cannot be decoded."""


@dataclass(frozen=True, slots=True)
class DrawThingsImageRequest:
    """Payload used to request a txt2img image from a Draw Things instance."""

    prompt: str
    negative_prompt: str = ""
    width: int = 512
    height: int = 512
    steps: int = 24
    cfg_scale: float = 7.0
    sampler_name: Optional[str] = None
    seed: Optional[int] = None

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "width": int(self.width),
            "height": int(self.height),
            "steps": int(self.steps),
            "cfg_scale": float(self.cfg_scale),
            "batch_size": 1,
            "n_iter": 1,
        }
        if self.sampler_name:
            payload["sampler_name"] = self.sampler_name
        if self.seed is not None:
            payload["seed"] = int(self.seed)
        return payload


def _decode_base64_image(value: str) -> Optional[bytes]:
    candidate = value.strip()
    if not candidate:
        return None
    if "," in candidate and candidate.lstrip().lower().startswith("data:"):
        _, _, candidate = candidate.partition(",")
    try:
        return base64.b64decode(candidate, validate=False)
    except Exception:
        return None


class DrawThingsClient:
    """Minimal client for Draw Things' txt2img-compatible HTTP API."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 180.0,
        txt2img_path: str = "/sdapi/v1/txt2img",
    ) -> None:
        trimmed = (base_url or "").strip().rstrip("/")
        if not trimmed:
            raise ValueError("DrawThingsClient base_url cannot be empty")
        self._base_url = trimmed + "/"
        self._timeout = max(float(timeout_seconds), 1.0)
        self._txt2img_url = urljoin(self._base_url, txt2img_path.lstrip("/"))

    @property
    def base_url(self) -> str:  # pragma: no cover - trivial
        return self._base_url.rstrip("/")

    def txt2img(self, request: DrawThingsImageRequest) -> Tuple[bytes, Mapping[str, Any]]:
        try:
            response = requests.post(
                self._txt2img_url,
                json=request.as_payload(),
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise DrawThingsError(f"DrawThings request failed: {exc}") from exc

        content_type = (response.headers.get("content-type") or "").lower()
        if "application/json" in content_type or response.text.lstrip().startswith("{"):
            try:
                payload: Any = response.json()
            except json.JSONDecodeError as exc:
                raise DrawThingsError("DrawThings response was not valid JSON") from exc
            if not isinstance(payload, Mapping):
                raise DrawThingsError("DrawThings JSON response did not contain an object")
            if not response.ok:
                detail = payload.get("error") or payload.get("detail") or response.text
                raise DrawThingsError(f"DrawThings request failed ({response.status_code}): {detail}")
            images = payload.get("images")
            if isinstance(images, list) and images:
                decoded = _decode_base64_image(str(images[0]))
                if decoded:
                    return decoded, payload
            raise DrawThingsError("DrawThings response did not contain image data")

        if not response.ok:
            raise DrawThingsError(
                f"DrawThings request failed ({response.status_code}): {response.text}"
            )
        return response.content, {}
