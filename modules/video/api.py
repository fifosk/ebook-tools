"""Video service abstractions for rendering slide videos."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence, TYPE_CHECKING

from pydub import AudioSegment

from modules import logging_manager as log_mgr, observability
from modules.config.loader import RenderingConfig, get_rendering_config

from .backends import BaseVideoRenderer, VideoRenderOptions, create_video_renderer

RendererFactory = Callable[[str, Mapping[str, object] | None], BaseVideoRenderer]


if TYPE_CHECKING:  # pragma: no cover - typing helper
    from modules.integrations.video_client import VideoAPIClient
else:  # pragma: no cover - runtime fallback when integrations are unavailable
    VideoAPIClient = Any  # type: ignore[assignment]

logger = log_mgr.get_logger().getChild("video.api")


class VideoService:
    """High-level API that resolves and invokes video rendering backends."""

    def __init__(
        self,
        *,
        backend: str | None = None,
        backend_settings: Mapping[str, Mapping[str, object]] | None = None,
        renderer_factory: RendererFactory | None = None,
        config: RenderingConfig | None = None,
    ) -> None:
        self._config = config or get_rendering_config()
        self._backend_name = (backend or self._config.video_backend).lower()
        self._backend_settings = backend_settings or {}
        self._renderer_factory = renderer_factory or create_video_renderer
        self._renderer: BaseVideoRenderer | None = None
        self._api_client: VideoAPIClient | None = None

    @property
    def renderer(self) -> BaseVideoRenderer:
        """Return the resolved renderer instance, constructing it on demand."""

        if self._backend_name == "api":
            raise ValueError("API video backend does not expose a local renderer")

        if self._renderer is None:
            settings = dict(self._config.video_backend_settings.get(self._backend_name, {}))
            overrides = self._backend_settings.get(self._backend_name)
            if isinstance(overrides, Mapping):
                settings.update(overrides)
            self._renderer = self._renderer_factory(self._backend_name, settings)
        return self._renderer

    def _resolve_api_client(self) -> VideoAPIClient | None:
        if self._api_client is not None:
            return self._api_client
        backend_settings = self._backend_settings.get(self._backend_name, {})
        base_url = None
        timeout: Optional[float] = None
        poll_interval: Optional[float] = None
        if isinstance(backend_settings, Mapping):
            base_url = backend_settings.get("base_url") or backend_settings.get("api_base_url")
            timeout_value = backend_settings.get("timeout")
            if timeout_value is not None:
                try:
                    timeout = float(timeout_value)
                except (TypeError, ValueError):
                    timeout = None
            poll_value = backend_settings.get("poll_interval")
            if poll_value is not None:
                try:
                    poll_interval = float(poll_value)
                except (TypeError, ValueError):
                    poll_interval = None
        if base_url is None:
            base_url = os.environ.get("EBOOK_VIDEO_API_BASE_URL")
        if not base_url:
            return None
        try:
            from modules.integrations.video_client import VideoAPIClient as RuntimeVideoClient
        except ImportError as exc:  # pragma: no cover - optional dependency safeguard
            logger.warning(
                "Video API client dependencies missing; using local renderer.",
                extra={"event": "video.api.client_unavailable"},
                exc_info=exc,
            )
            return None
        self._api_client = RuntimeVideoClient(
            base_url,
            timeout=timeout or 300.0,
            poll_interval=poll_interval or 2.0,
        )
        return self._api_client

    def _options_payload(self, options: VideoRenderOptions) -> Mapping[str, object] | None:
        if options.cover_image is not None:
            return None
        if options.slide_render_options is not None:
            return None
        payload: dict[str, object] = {
            "batch_start": options.batch_start,
            "batch_end": options.batch_end,
            "book_author": options.book_author,
            "book_title": options.book_title,
            "macos_reading_speed": options.macos_reading_speed,
            "input_language": options.input_language,
            "total_sentences": options.total_sentences,
            "tempo": options.tempo,
            "sync_ratio": options.sync_ratio,
            "word_highlighting": options.word_highlighting,
            "highlight_granularity": options.highlight_granularity,
            "cleanup": options.cleanup,
            "slide_size": list(options.slide_size),
            "initial_font_size": options.initial_font_size,
            "bg_color": list(options.bg_color) if options.bg_color is not None else None,
            "template_name": options.template_name,
            "default_font_path": options.default_font_path,
        }
        if options.cumulative_word_counts is not None:
            payload["cumulative_word_counts"] = list(options.cumulative_word_counts)
        if options.total_word_count is not None:
            payload["total_word_count"] = options.total_word_count
        return payload

    def render(
        self,
        slides: Sequence[str],
        audio_tracks: Sequence[AudioSegment],
        output_path: str,
        options: VideoRenderOptions,
    ) -> str:
        """Render ``slides`` and ``audio_tracks`` into ``output_path``."""

        api_client = self._resolve_api_client()
        if self._backend_name == "api" and api_client is not None:
            option_payload = self._options_payload(options)
            if option_payload is not None:
                attributes = {
                    "backend": self._backend_name,
                    "slides": len(slides),
                    "audio_tracks": len(audio_tracks),
                    "output_filename": Path(output_path).name,
                }
                logger.info(
                    "Dispatching remote video render request",
                    extra={
                        "event": "video.api.render.start",
                        "attributes": attributes,
                        "console_suppress": True,
                    },
                )
                start = time.perf_counter()
                try:
                    result = api_client.render(
                        slides=slides,
                        audio_segments=audio_tracks,
                        options=option_payload,
                        output_filename=attributes["output_filename"],
                    )
                except Exception:
                    duration_ms = (time.perf_counter() - start) * 1000.0
                    observability.record_metric(
                        "video.api.render.duration",
                        duration_ms,
                        {**attributes, "status": "error"},
                    )
                    logger.error(
                        "Remote video render failed",
                        extra={
                            "event": "video.api.render.error",
                            "attributes": attributes,
                            "console_suppress": True,
                        },
                        exc_info=True,
                    )
                    raise
                duration_ms = (time.perf_counter() - start) * 1000.0
                observability.record_metric(
                    "video.api.render.duration",
                    duration_ms,
                    {**attributes, "status": "success"},
                )
                logger.info(
                    "Remote video render completed",
                    extra={
                        "event": "video.api.render.complete",
                        "attributes": {**attributes, "duration_ms": round(duration_ms, 2)},
                        "console_suppress": True,
                    },
                )
                result_payload = result.get("result") if isinstance(result, Mapping) else None
                if isinstance(result_payload, Mapping):
                    path = result_payload.get("path")
                    if isinstance(path, str) and path:
                        return path
                return output_path

        return self.renderer.render_slides(slides, audio_tracks, output_path, options)

    def concatenate(self, video_paths: Sequence[str], output_path: str) -> str:
        """Concatenate ``video_paths`` into ``output_path`` using the active backend."""

        api_client = self._resolve_api_client()
        if self._backend_name == "api" and api_client is not None:
            attributes = {
                "backend": self._backend_name,
                "segment_count": len(video_paths),
                "output_filename": Path(output_path).name,
            }
            logger.info(
                "Dispatching remote video concatenate request",
                extra={
                    "event": "video.api.concatenate.start",
                    "attributes": attributes,
                    "console_suppress": True,
                },
            )
            start = time.perf_counter()
            try:
                result = api_client.concatenate(video_paths, correlation_id=None)
            except Exception:
                duration_ms = (time.perf_counter() - start) * 1000.0
                observability.record_metric(
                    "video.api.concatenate.duration",
                    duration_ms,
                    {**attributes, "status": "error"},
                )
                logger.error(
                    "Remote video concatenate failed",
                    extra={
                        "event": "video.api.concatenate.error",
                        "attributes": attributes,
                        "console_suppress": True,
                    },
                    exc_info=True,
                )
                raise
            duration_ms = (time.perf_counter() - start) * 1000.0
            observability.record_metric(
                "video.api.concatenate.duration",
                duration_ms,
                {**attributes, "status": "success"},
            )
            logger.info(
                "Remote video concatenate completed",
                extra={
                    "event": "video.api.concatenate.complete",
                    "attributes": {**attributes, "duration_ms": round(duration_ms, 2)},
                    "console_suppress": True,
                },
            )
            result_payload = result.get("result") if isinstance(result, Mapping) else None
            if isinstance(result_payload, Mapping):
                path = result_payload.get("path")
                if isinstance(path, str) and path:
                    return path
            return output_path

        return self.renderer.concatenate(video_paths, output_path)


__all__ = ["VideoService"]
