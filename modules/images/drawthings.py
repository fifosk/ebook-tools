"""Draw Things / Stable Diffusion HTTP client helpers."""

from __future__ import annotations

import base64
import json
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple
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


@dataclass(frozen=True, slots=True)
class DrawThingsImageToImageRequest:
    """Payload used to request an img2img image from a Draw Things instance."""

    prompt: str
    init_image: bytes
    negative_prompt: str = ""
    denoising_strength: float = 0.45
    width: int = 512
    height: int = 512
    steps: int = 24
    cfg_scale: float = 7.0
    sampler_name: Optional[str] = None
    seed: Optional[int] = None

    def as_payload(self) -> dict[str, Any]:
        init_encoded = base64.b64encode(self.init_image).decode("ascii")
        payload: dict[str, Any] = {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "init_images": [init_encoded],
            "denoising_strength": float(self.denoising_strength),
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
        img2img_path: str = "/sdapi/v1/img2img",
    ) -> None:
        trimmed = (base_url or "").strip().rstrip("/")
        if not trimmed:
            raise ValueError("DrawThingsClient base_url cannot be empty")
        self._base_url = trimmed + "/"
        self._timeout = max(float(timeout_seconds), 1.0)
        self._txt2img_url = urljoin(self._base_url, txt2img_path.lstrip("/"))
        self._img2img_url = urljoin(self._base_url, img2img_path.lstrip("/"))

    @property
    def base_url(self) -> str:  # pragma: no cover - trivial
        return self._base_url.rstrip("/")

    def _post_image(self, url: str, payload: Mapping[str, Any]) -> Tuple[bytes, Mapping[str, Any]]:
        try:
            response = requests.post(
                url,
                json=dict(payload),
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

    def txt2img(self, request: DrawThingsImageRequest) -> Tuple[bytes, Mapping[str, Any]]:
        return self._post_image(self._txt2img_url, request.as_payload())

    def img2img(self, request: DrawThingsImageToImageRequest) -> Tuple[bytes, Mapping[str, Any]]:
        return self._post_image(self._img2img_url, request.as_payload())


def normalize_drawthings_base_urls(
    *,
    base_url: Optional[str] = None,
    base_urls: Optional[Sequence[str] | str] = None,
) -> list[str]:
    candidates: list[str] = []
    if base_urls:
        if isinstance(base_urls, str):
            candidates.extend(base_urls.split(","))
        else:
            candidates.extend(
                str(entry) for entry in base_urls if entry is not None
            )
    if base_url:
        candidates.append(str(base_url))

    cleaned: list[str] = []
    seen: set[str] = set()
    for entry in candidates:
        normalized = (entry or "").strip().rstrip("/")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def probe_drawthings_base_urls(
    base_urls: Sequence[str],
    *,
    timeout_seconds: float = 2.0,
) -> tuple[list[str], list[str]]:
    available: list[str] = []
    unavailable: list[str] = []
    timeout = max(float(timeout_seconds), 0.5)
    for base_url in base_urls:
        try:
            requests.get(base_url, timeout=timeout)
        except requests.RequestException:
            unavailable.append(base_url)
        else:
            available.append(base_url)
    return available, unavailable


class DrawThingsClusterClient:
    """Client wrapper that balances requests across multiple Draw Things nodes."""

    def __init__(self, clients: Sequence[DrawThingsClient]) -> None:
        if not clients:
            raise ValueError("DrawThingsClusterClient requires at least one client")
        self._clients = list(clients)
        self._available: queue.Queue[int] = queue.Queue(maxsize=len(self._clients))
        self._stats_lock = threading.Lock()
        self._stats: dict[str, dict[str, float | int]] = {}
        self._stats_order: list[str] = []
        for idx in range(len(self._clients)):
            self._available.put(idx)
        for client in self._clients:
            base_url = client.base_url
            self._stats[base_url] = {"processed": 0, "total_seconds": 0.0}
            self._stats_order.append(base_url)

    @property
    def base_urls(self) -> tuple[str, ...]:  # pragma: no cover - trivial
        return tuple(client.base_url for client in self._clients)

    @property
    def base_url(self) -> str:  # pragma: no cover - helper for logging
        return ",".join(self.base_urls)

    def _with_client(
        self,
        action: Callable[[DrawThingsClient], Tuple[bytes, Mapping[str, Any]]],
    ) -> Tuple[bytes, Mapping[str, Any]]:
        idx = self._available.get()
        client = self._clients[idx]
        start = time.perf_counter()
        try:
            result = action(client)
        except DrawThingsError as exc:
            raise DrawThingsError(f"{client.base_url}: {exc}") from exc
        else:
            elapsed = time.perf_counter() - start
            with self._stats_lock:
                stats = self._stats.setdefault(
                    client.base_url, {"processed": 0, "total_seconds": 0.0}
                )
                stats["processed"] = int(stats.get("processed", 0)) + 1
                stats["total_seconds"] = float(stats.get("total_seconds", 0.0)) + elapsed
            return result
        finally:
            self._available.put(idx)

    def txt2img(self, request: DrawThingsImageRequest) -> Tuple[bytes, Mapping[str, Any]]:
        return self._with_client(lambda client: client.txt2img(request))

    def img2img(self, request: DrawThingsImageToImageRequest) -> Tuple[bytes, Mapping[str, Any]]:
        return self._with_client(lambda client: client.img2img(request))

    def snapshot_stats(self) -> list[dict[str, object]]:
        with self._stats_lock:
            snapshots = {
                base_url: {
                    "processed": int(stats.get("processed", 0)),
                    "total_seconds": float(stats.get("total_seconds", 0.0)),
                }
                for base_url, stats in self._stats.items()
            }
            ordered_urls = list(self._stats_order)
        result: list[dict[str, object]] = []
        for base_url in ordered_urls:
            stats = snapshots.get(base_url, {"processed": 0, "total_seconds": 0.0})
            processed = int(stats.get("processed", 0))
            total_seconds = float(stats.get("total_seconds", 0.0))
            avg_seconds = total_seconds / processed if processed > 0 else None
            entry: dict[str, object] = {
                "base_url": base_url,
                "processed": processed,
                "total_seconds": round(total_seconds, 3),
                "avg_seconds_per_image": round(avg_seconds, 3)
                if avg_seconds is not None
                else None,
            }
            result.append(entry)
        return result


DrawThingsClientLike = DrawThingsClient | DrawThingsClusterClient


def resolve_drawthings_client(
    *,
    base_url: Optional[str] = None,
    base_urls: Optional[Sequence[str] | str] = None,
    timeout_seconds: float = 180.0,
    probe_timeout_seconds: float = 2.0,
) -> tuple[Optional[DrawThingsClientLike], list[str], list[str]]:
    normalized = normalize_drawthings_base_urls(base_url=base_url, base_urls=base_urls)
    if not normalized:
        return None, [], []
    available, unavailable = probe_drawthings_base_urls(
        normalized, timeout_seconds=probe_timeout_seconds
    )
    if not available:
        return None, available, unavailable
    timeout = max(float(timeout_seconds), 1.0)
    clients = [DrawThingsClient(base_url, timeout_seconds=timeout) for base_url in available]
    return DrawThingsClusterClient(clients), available, unavailable
