"""Configuration preparation helpers for the pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ... import logging_manager as log_mgr
from ...core.config import PipelineConfig, build_pipeline_config
from ..pipeline_types import ConfigPhaseResult

if TYPE_CHECKING:  # pragma: no cover - import for typing only
    from ... import config_manager as cfg
    from ..pipeline_service import PipelineRequest

configure_logging_level = log_mgr.configure_logging_level


def prepare_configuration(
    request: "PipelineRequest",
    context: "cfg.RuntimeContext",
) -> ConfigPhaseResult:
    """Build the :class:`PipelineConfig` for ``request`` using ``context``."""

    overrides = {**request.environment_overrides, **request.pipeline_overrides}
    selected_voice = request.inputs.selected_voice
    if selected_voice and "selected_voice" not in overrides:
        overrides["selected_voice"] = selected_voice

    pipeline_config: PipelineConfig = build_pipeline_config(
        context, request.config, overrides=overrides
    )
    pipeline_config.apply_runtime_settings()
    configure_logging_level(pipeline_config.debug)

    return ConfigPhaseResult(
        pipeline_config=pipeline_config,
        generate_audio=pipeline_config.generate_audio,
        audio_mode=pipeline_config.audio_mode,
    )
