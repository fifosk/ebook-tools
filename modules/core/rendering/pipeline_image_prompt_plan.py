"""Prompt plan builder for image generation."""

from __future__ import annotations

import datetime
import threading
import queue
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from PIL import Image

from modules.logging_manager import logger
from modules.images.drawthings import DrawThingsClientLike, DrawThingsImageRequest
from modules.images.prompting import (
    DiffusionPrompt,
    DiffusionPromptPlan,
    build_sentence_image_negative_prompt,
    build_sentence_image_prompt,
    sentence_batches_to_diffusion_prompt_plan,
    sentences_to_diffusion_prompt_plan,
    stable_diffusion_seed,
)

from .pipeline_image_state import _atomic_write_json, _job_relative_path


@dataclass
class PromptPlanState:
    """Shared prompt-plan state for async planning."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    ready_queue: queue.Queue[list[int]] = field(default_factory=queue.Queue)
    ready_event: threading.Event = field(default_factory=threading.Event)
    prompt_plan: dict[int, DiffusionPrompt] = field(default_factory=dict)
    prompt_sources: dict[int, str] = field(default_factory=dict)
    baseline_prompt: DiffusionPrompt = field(
        default_factory=lambda: DiffusionPrompt(prompt="")
    )
    baseline_notes: str = ""
    baseline_source: str = "fallback"
    quality: dict[str, Any] = field(default_factory=dict)
    baseline_seed_image_path: Optional[Path] = None
    baseline_seed_relative_path: Optional[str] = None
    baseline_seed_error: Optional[str] = None


@dataclass(frozen=True)
class PromptPlanContext:
    image_prompt_batch_size: int
    image_prompt_plan_batch_size: int
    image_prompt_batches: Sequence[Sequence[str]]
    image_prompt_batch_starts: Sequence[int]
    target_sentences: Sequence[str]
    full_sentences: Sequence[str]
    start_sentence: int
    total_refined: int
    total_fully: int
    image_prompt_seed_sources: Mapping[int, str]
    image_style_template: Optional[str]
    image_seed_with_previous_image: bool
    base_dir_path: Path
    media_root: Path
    image_client: Optional[DrawThingsClientLike]
    config: Any
    progress: Optional[object]
    prompt_plan_path: Optional[Path]
    context_prefix: Sequence[str]
    context_suffix: Sequence[str]
    context_window: int
    prefix_start: int
    window_start_idx: int
    window_end_idx: int
    suffix_end: int


def build_prompt_plan(state: PromptPlanState, context: PromptPlanContext) -> None:
    """Build and persist the prompt plan, updating the shared state."""

    def _queue_prompt_keys(keys: list[int]) -> None:
        if keys:
            state.ready_queue.put(keys)

    def _handle_prompt_chunk(
        start_idx: int, end_idx: int, plan: DiffusionPromptPlan
    ) -> None:
        if end_idx <= start_idx:
            return
        chunk_len = len(plan.prompts)
        if chunk_len <= 0:
            return
        keys: list[int] = []
        for offset in range(chunk_len):
            global_index = start_idx + offset
            if context.image_prompt_batch_size > 1:
                if global_index >= len(context.image_prompt_batch_starts):
                    continue
                key = int(context.image_prompt_batch_starts[global_index])
            else:
                key = int(context.start_sentence + global_index)
            keys.append(key)
        if not keys:
            return
        with state.lock:
            for offset, key in enumerate(keys):
                state.prompt_plan[key] = plan.prompts[offset]
                if offset < len(plan.sources):
                    state.prompt_sources[key] = str(plan.sources[offset])
                else:
                    state.prompt_sources[key] = "fallback"
            state.baseline_prompt = plan.baseline_prompt
            state.baseline_notes = plan.baseline_notes
            state.baseline_source = plan.baseline_source
        _queue_prompt_keys(keys)

    try:
        prompt_plan_error: Optional[str] = None
        planned: list[DiffusionPrompt] = []
        planned_sources: list[str] = []
        baseline_prompt = DiffusionPrompt(prompt="")
        baseline_notes = ""
        baseline_source = "fallback"
        quality: dict[str, Any] = {}

        try:
            if context.image_prompt_batch_size > 1:
                planned_plan = sentence_batches_to_diffusion_prompt_plan(
                    context.image_prompt_batches,
                    context_prefix=context.context_prefix,
                    context_suffix=context.context_suffix,
                    chunk_size=context.image_prompt_plan_batch_size,
                    on_chunk=_handle_prompt_chunk,
                )
                expected = len(context.image_prompt_batch_starts)
            else:
                planned_plan = sentences_to_diffusion_prompt_plan(
                    context.target_sentences,
                    context_prefix=context.context_prefix,
                    context_suffix=context.context_suffix,
                    chunk_size=context.image_prompt_plan_batch_size,
                    on_chunk=_handle_prompt_chunk,
                )
                expected = len(context.target_sentences)
            planned = planned_plan.prompts
            planned_sources = planned_plan.sources
            baseline_prompt = planned_plan.baseline_prompt
            baseline_notes = planned_plan.baseline_notes
            baseline_source = planned_plan.baseline_source
            quality = (
                dict(planned_plan.quality)
                if isinstance(planned_plan.quality, dict)
                else {}
            )
            if len(planned) != expected or len(planned_sources) != expected:
                raise ValueError("Prompt plan length mismatch")
            if context.image_prompt_batch_size > 1:
                quality = dict(quality)
                quality.setdefault("total_batches", expected)
                quality.setdefault("total_sentences", len(context.target_sentences))
                quality.setdefault("prompt_batch_size", context.image_prompt_batch_size)
            if context.image_prompt_plan_batch_size:
                quality = dict(quality)
                quality.setdefault(
                    "prompt_plan_batch_size", context.image_prompt_plan_batch_size
                )
        except Exception as exc:
            prompt_plan_error = str(exc)
            baseline_prompt = DiffusionPrompt(
                prompt=str(context.target_sentences[0]).strip()
                if context.target_sentences
                else ""
            )
            baseline_notes = ""
            baseline_source = "fallback"
            if context.image_prompt_batch_size > 1:
                planned = [
                    DiffusionPrompt(
                        prompt="\n".join(
                            str(sentence).strip()
                            for sentence in batch
                            if str(sentence).strip()
                        ).strip()
                    )
                    for batch in context.image_prompt_batches
                ]
                planned_sources = ["fallback"] * len(planned)
            else:
                planned = [
                    DiffusionPrompt(prompt=str(sentence).strip())
                    for sentence in context.target_sentences
                ]
                planned_sources = ["fallback"] * len(planned)
            quality = {
                "version": 1,
                "total_sentences": len(context.target_sentences),
                "llm_requests": 0,
                "initial_missing": len(planned),
                "final_fallback": len(planned),
                "retry_attempts": 0,
                "retry_requested": 0,
                "retry_recovered": 0,
                "retry_recovered_unique": 0,
                "initial_coverage_rate": 0.0 if planned else 1.0,
                "llm_coverage_rate": 0.0 if planned else 1.0,
                "fallback_rate": 1.0 if planned else 0.0,
                "retry_success_rate": None,
                "recovery_rate": None,
                "errors": [prompt_plan_error],
            }
            if context.image_prompt_batch_size > 1:
                quality["total_batches"] = len(planned)
                quality["prompt_batch_size"] = context.image_prompt_batch_size
            if context.image_prompt_plan_batch_size:
                quality["prompt_plan_batch_size"] = (
                    context.image_prompt_plan_batch_size
                )
            if context.progress is not None:
                try:
                    context.progress.record_retry("image", "prompt_plan_error")
                except Exception:
                    pass
            logger.warning(
                "Unable to precompute image prompts: %s",
                exc,
                extra={
                    "event": "pipeline.image.prompt_plan.error",
                    "attributes": {"error": str(exc)},
                    "console_suppress": True,
                },
            )

        if context.image_prompt_batch_size > 1:
            plan_map = {
                int(batch_start): prompt
                for batch_start, prompt in zip(
                    context.image_prompt_batch_starts, planned
                )
            }
            source_map = {
                int(batch_start): str(source)
                for batch_start, source in zip(
                    context.image_prompt_batch_starts, planned_sources
                )
            }
        else:
            plan_map = {
                context.start_sentence + offset: prompt
                for offset, prompt in enumerate(planned)
            }
            source_map = {
                context.start_sentence + offset: str(source)
                for offset, source in enumerate(planned_sources)
            }

        with state.lock:
            state.prompt_plan = plan_map
            state.prompt_sources = source_map
            state.baseline_prompt = baseline_prompt
            state.baseline_notes = baseline_notes
            state.baseline_source = baseline_source
            state.quality = quality

        end_sentence_number = context.start_sentence + max(context.total_refined - 1, 0)
        baseline_scene = (baseline_prompt.prompt or "").strip()
        baseline_negative = (baseline_prompt.negative_prompt or "").strip()
        baseline_seed_value = stable_diffusion_seed(
            baseline_scene or f"{context.start_sentence}-{end_sentence_number}"
        )
        baseline_seed_status = "disabled"
        baseline_seed_image_path_local: Optional[Path] = None
        baseline_seed_relative_path_local: Optional[str] = None
        baseline_seed_error_local: Optional[str] = None

        if context.image_seed_with_previous_image:
            baseline_seed_dir = context.media_root / "images" / "_seed"
            baseline_seed_image_path_local = baseline_seed_dir / (
                f"baseline_seed_{context.start_sentence:05d}_{end_sentence_number:05d}.png"
            )
            baseline_seed_relative_path_local = _job_relative_path(
                baseline_seed_image_path_local, base_dir=context.base_dir_path
            )
            baseline_seed_status = "skipped" if not baseline_scene else "ok"

            if baseline_scene and context.image_client is not None:
                try:
                    if not baseline_seed_image_path_local.exists():
                        baseline_prompt_full = build_sentence_image_prompt(
                            baseline_scene,
                            style_template=context.image_style_template,
                        )
                        baseline_negative_full = build_sentence_image_negative_prompt(
                            baseline_negative,
                            style_template=context.image_style_template,
                        )
                        request = DrawThingsImageRequest(
                            prompt=baseline_prompt_full,
                            negative_prompt=baseline_negative_full,
                            width=int(context.config.image_width or 512),
                            height=int(context.config.image_height or 512),
                            steps=int(context.config.image_steps or 24),
                            cfg_scale=float(context.config.image_cfg_scale or 7.0),
                            sampler_name=context.config.image_sampler_name,
                            seed=baseline_seed_value,
                        )
                        image_bytes, _ = context.image_client.txt2img(request)
                        baseline_seed_dir.mkdir(parents=True, exist_ok=True)
                        try:
                            import io

                            with Image.open(io.BytesIO(image_bytes)) as loaded:
                                converted = loaded.convert("RGB")
                                output = io.BytesIO()
                                converted.save(output, format="PNG")
                                baseline_seed_image_path_local.write_bytes(
                                    output.getvalue()
                                )
                        except Exception:
                            baseline_seed_image_path_local.write_bytes(image_bytes)
                except Exception as exc:
                    baseline_seed_error_local = str(exc)
                    baseline_seed_status = "error"
                    logger.warning(
                        "Unable to generate baseline seed image: %s",
                        exc,
                        extra={
                            "event": "pipeline.image.baseline_seed.error",
                            "attributes": {"error": str(exc)},
                            "console_suppress": True,
                        },
                    )

        with state.lock:
            state.baseline_seed_image_path = baseline_seed_image_path_local
            state.baseline_seed_relative_path = baseline_seed_relative_path_local
            state.baseline_seed_error = baseline_seed_error_local

        try:
            if context.prompt_plan_path is not None:
                context_prefix_payload = [
                    {
                        "sentence_number": idx + 1,
                        "sentence": str(context.full_sentences[idx]).strip(),
                    }
                    for idx in range(context.prefix_start, context.window_start_idx)
                ]
                context_suffix_payload = [
                    {
                        "sentence_number": idx + 1,
                        "sentence": str(context.full_sentences[idx]).strip(),
                    }
                    for idx in range(context.window_end_idx, context.suffix_end)
                ]
                prompts_payload = []
                if context.image_prompt_batch_size > 1:
                    for batch_index, batch_start in enumerate(
                        context.image_prompt_batch_starts
                    ):
                        offset_start = max(int(batch_start) - context.start_sentence, 0)
                        offset_end = min(
                            offset_start + context.image_prompt_batch_size,
                            len(context.target_sentences),
                        )
                        batch_sentences = [
                            str(entry).strip()
                            for entry in context.target_sentences[offset_start:offset_end]
                        ]
                        batch_end = int(batch_start) + max(
                            offset_end - offset_start - 1, 0
                        )
                        diffusion = plan_map.get(int(batch_start))
                        scene_prompt = (
                            (diffusion.prompt or "").strip() if diffusion else ""
                        )
                        scene_negative_prompt = (
                            (diffusion.negative_prompt or "").strip()
                            if diffusion
                            else ""
                        )
                        source = source_map.get(int(batch_start)) or (
                            "fallback" if diffusion is None else "llm"
                        )
                        if not scene_prompt:
                            scene_prompt = batch_sentences[0] if batch_sentences else ""
                        prompts_payload.append(
                            {
                                "batch_index": int(batch_index),
                                "start_sentence": int(batch_start),
                                "end_sentence": int(batch_end),
                                "sentences": [
                                    {
                                        "sentence_number": int(batch_start) + idx,
                                        "sentence": sentence,
                                    }
                                    for idx, sentence in enumerate(batch_sentences)
                                ],
                                "scene_prompt": scene_prompt,
                                "scene_negative_prompt": scene_negative_prompt,
                                "source": source,
                                "seed": stable_diffusion_seed(
                                    context.image_prompt_seed_sources.get(int(batch_start))
                                    or scene_prompt
                                ),
                            }
                        )
                else:
                    for offset, sentence_text in enumerate(context.target_sentences):
                        sentence_number = context.start_sentence + offset
                        diffusion = plan_map.get(sentence_number)
                        scene_prompt = ""
                        scene_negative_prompt = ""
                        source = source_map.get(sentence_number) or (
                            "fallback" if diffusion is None else "llm"
                        )
                        if diffusion is not None:
                            scene_prompt = (diffusion.prompt or "").strip()
                            scene_negative_prompt = (
                                diffusion.negative_prompt or ""
                            ).strip()
                        if not scene_prompt:
                            scene_prompt = str(sentence_text).strip()
                        prompts_payload.append(
                            {
                                "sentence_number": sentence_number,
                                "sentence": str(sentence_text).strip(),
                                "scene_prompt": scene_prompt,
                                "scene_negative_prompt": scene_negative_prompt,
                                "source": source,
                                "seed": stable_diffusion_seed(
                                    context.image_prompt_seed_sources.get(sentence_number)
                                    or str(sentence_text).strip()
                                ),
                            }
                        )

                payload = {
                    "version": 1,
                    "generated_at": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "start_sentence": context.start_sentence,
                    "end_sentence": end_sentence_number,
                    "context_window": context.context_window,
                    "prompt_batching_enabled": bool(context.image_prompt_batch_size > 1),
                    "prompt_batch_size": int(context.image_prompt_batch_size),
                    "prompt_plan_batch_size": int(context.image_prompt_plan_batch_size),
                    "style_prompt": build_sentence_image_prompt(
                        "",
                        style_template=context.image_style_template,
                    ),
                    "style_negative_prompt": build_sentence_image_negative_prompt(
                        "",
                        style_template=context.image_style_template,
                    ),
                    "style_template": context.image_style_template,
                    "baseline": {
                        "scene_prompt": baseline_scene,
                        "scene_negative_prompt": baseline_negative,
                        "notes": str(baseline_notes or "").strip(),
                        "source": str(baseline_source or "fallback"),
                        "seed": baseline_seed_value,
                        "seed_image_path": baseline_seed_relative_path_local,
                        "seed_image_status": baseline_seed_status,
                    },
                    "context_prefix": context_prefix_payload,
                    "context_suffix": context_suffix_payload,
                    "status": "ok" if plan_map else "error",
                    "quality": quality,
                    "prompts": prompts_payload,
                }
                if baseline_seed_error_local:
                    payload["baseline"]["seed_image_error"] = baseline_seed_error_local
                if prompt_plan_error:
                    payload["error"] = prompt_plan_error
                context.prompt_plan_path.parent.mkdir(parents=True, exist_ok=True)
                _atomic_write_json(context.prompt_plan_path, payload)
                summary_path = context.prompt_plan_path.with_name(
                    "image_prompt_plan_summary.json"
                )
                summary_payload = {
                    "version": payload.get("version", 1),
                    "generated_at": payload.get("generated_at"),
                    "start_sentence": payload.get("start_sentence"),
                    "end_sentence": payload.get("end_sentence"),
                    "context_window": payload.get("context_window"),
                    "prompt_batch_size": payload.get("prompt_batch_size"),
                    "prompt_plan_batch_size": payload.get("prompt_plan_batch_size"),
                    "status": payload.get("status"),
                    "quality": payload.get("quality") or {},
                    "baseline": {
                        "source": payload.get("baseline", {}).get("source"),
                        "seed_image_status": payload.get("baseline", {}).get(
                            "seed_image_status"
                        ),
                    },
                }
                if payload.get("error"):
                    summary_payload["error"] = payload.get("error")
                _atomic_write_json(summary_path, summary_payload)
        except Exception as exc:
            logger.warning(
                "Unable to persist image prompt plan: %s",
                exc,
                extra={
                    "event": "pipeline.image.prompt_plan.persist.error",
                    "attributes": {"error": str(exc)},
                    "console_suppress": True,
                },
            )
    finally:
        state.ready_event.set()


__all__ = ["PromptPlanContext", "PromptPlanState", "build_prompt_plan"]
