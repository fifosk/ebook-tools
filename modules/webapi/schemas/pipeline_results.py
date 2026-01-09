"""Schemas representing pipeline results and responses."""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ...core.config import PipelineConfig
from ...services.pipeline_service import PipelineResponse


class PipelineResponsePayload(BaseModel):
    """Serializable representation of :class:`PipelineResponse`."""

    success: Optional[bool] = None
    pipeline_config: Optional[Dict[str, Any]] = None
    refined_sentences: Optional[List[str]] = None
    refined_updated: bool = False
    written_blocks: Optional[List[str]] = None
    audio_segments: Optional[List[float]] = None
    batch_video_files: Optional[List[str]] = None
    base_dir: Optional[str] = None
    base_output_stem: Optional[str] = None
    stitched_documents: Dict[str, str] = Field(default_factory=dict)
    stitched_audio_path: Optional[str] = None
    stitched_video_path: Optional[str] = None
    book_metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_files: Dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def _serialize_pipeline_config(config: PipelineConfig) -> Dict[str, Any]:
        data = {
            "working_dir": str(config.working_dir),
            "output_dir": str(config.output_dir) if config.output_dir else None,
            "tmp_dir": str(config.tmp_dir),
            "books_dir": str(config.books_dir),
            "ollama_model": config.ollama_model,
            "ollama_url": config.ollama_url,
            "llm_source": config.llm_source,
            "local_ollama_url": config.local_ollama_url,
            "cloud_ollama_url": config.cloud_ollama_url,
            "ffmpeg_path": config.ffmpeg_path,
            "thread_count": config.thread_count,
            "queue_size": config.queue_size,
            "pipeline_enabled": config.pipeline_enabled,
            "max_words": config.max_words,
            "split_on_comma_semicolon": config.split_on_comma_semicolon,
            "debug": config.debug,
            "generate_audio": config.generate_audio,
            "audio_mode": config.audio_mode,
            "selected_voice": config.selected_voice,
            "audio_api_base_url": config.audio_api_base_url,
            "audio_api_timeout_seconds": config.audio_api_timeout_seconds,
            "audio_api_poll_interval_seconds": config.audio_api_poll_interval_seconds,
            "tempo": config.tempo,
            "macos_reading_speed": config.macos_reading_speed,
            "sync_ratio": config.sync_ratio,
            "word_highlighting": config.word_highlighting,
            "highlight_granularity": config.highlight_granularity,
            "voice_overrides": dict(config.voice_overrides),
            "image_api_base_url": config.image_api_base_url,
            "image_api_base_urls": list(config.image_api_base_urls),
            "image_api_timeout_seconds": config.image_api_timeout_seconds,
            "image_concurrency": config.image_concurrency,
            "image_width": config.image_width,
            "image_height": config.image_height,
            "image_steps": config.image_steps,
            "image_cfg_scale": config.image_cfg_scale,
            "image_sampler_name": config.image_sampler_name,
            "image_style_template": getattr(config, "image_style_template", None),
            "image_prompt_pipeline": getattr(config, "image_prompt_pipeline", None),
            "image_prompt_batching_enabled": getattr(config, "image_prompt_batching_enabled", None),
            "image_prompt_batch_size": getattr(config, "image_prompt_batch_size", None),
            "image_prompt_plan_batch_size": getattr(config, "image_prompt_plan_batch_size", None),
            "image_blank_detection_enabled": getattr(config, "image_blank_detection_enabled", None),
        }
        return data

    @classmethod
    def from_response(cls, response: PipelineResponse) -> "PipelineResponsePayload":
        audio_segments: Optional[List[float]] = None
        if response.audio_segments:
            audio_segments = [segment.duration_seconds for segment in response.audio_segments]

        pipeline_config_data: Optional[Dict[str, Any]] = None
        if response.pipeline_config is not None:
            pipeline_config_data = cls._serialize_pipeline_config(response.pipeline_config)

        return cls(
            success=response.success,
            pipeline_config=pipeline_config_data,
            refined_sentences=response.refined_sentences,
            refined_updated=response.refined_updated,
            written_blocks=response.written_blocks,
            audio_segments=audio_segments,
            batch_video_files=response.batch_video_files,
            base_dir=str(response.base_dir) if response.base_dir else None,
            base_output_stem=response.base_output_stem,
            stitched_documents=dict(response.stitched_documents),
            stitched_audio_path=response.stitched_audio_path,
            stitched_video_path=response.stitched_video_path,
            book_metadata=dict(response.book_metadata),
            generated_files=copy.deepcopy(response.generated_files),
        )
