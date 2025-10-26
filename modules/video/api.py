"""Video service abstractions for rendering slide videos."""

from __future__ import annotations

from typing import Callable, Mapping, Sequence

from pydub import AudioSegment

from modules.config.loader import RenderingConfig, get_rendering_config

from .backends import BaseVideoRenderer, VideoRenderOptions, create_video_renderer

RendererFactory = Callable[[str, Mapping[str, object] | None], BaseVideoRenderer]


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

    @property
    def renderer(self) -> BaseVideoRenderer:
        """Return the resolved renderer instance, constructing it on demand."""

        if self._renderer is None:
            settings = dict(self._config.video_backend_settings.get(self._backend_name, {}))
            overrides = self._backend_settings.get(self._backend_name)
            if isinstance(overrides, Mapping):
                settings.update(overrides)
            self._renderer = self._renderer_factory(self._backend_name, settings)
        return self._renderer

    def render(
        self,
        slides: Sequence[str],
        audio_tracks: Sequence[AudioSegment],
        output_path: str,
        options: VideoRenderOptions,
    ) -> str:
        """Render ``slides`` and ``audio_tracks`` into ``output_path``."""

        return self.renderer.render_slides(slides, audio_tracks, output_path, options)

    def concatenate(self, video_paths: Sequence[str], output_path: str) -> str:
        """Concatenate ``video_paths`` into ``output_path`` using the active backend."""

        return self.renderer.concatenate(video_paths, output_path)


__all__ = ["VideoService"]
