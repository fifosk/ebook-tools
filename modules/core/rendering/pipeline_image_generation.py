"""Image generation workers for the rendering pipeline."""

from __future__ import annotations

import concurrent.futures
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from PIL import Image

from modules import output_formatter
from modules.images.drawthings import (
    DrawThingsClientLike,
    DrawThingsError,
    DrawThingsImageRequest,
    DrawThingsImageToImageRequest,
)
from modules.images.prompting import (
    DiffusionPrompt,
    build_sentence_image_negative_prompt,
    build_sentence_image_prompt,
    stable_diffusion_seed,
)
from modules.images.visual_prompting import VisualPromptOrchestrator
from modules.logging_manager import logger

from .pipeline_image_prompt_plan import PromptPlanState
from .pipeline_image_state import _SentenceImageResult, _job_relative_path


@dataclass(frozen=True)
class ImageGenerationContext:
    config: Any
    progress: Optional[object]
    base_dir_path: Path
    media_root: Path
    image_client: DrawThingsClientLike
    prompt_plan_state: PromptPlanState
    image_prompt_seed_sources: Mapping[int, str]
    image_prompt_batch_size: int
    image_style_template: Optional[str]
    visual_prompt_orchestrator: Optional[VisualPromptOrchestrator]
    img2img_capability: dict[str, bool]
    img2img_capability_lock: threading.Lock
    image_task_total: int
    total_refined: int
    total_fully: int
    start_sentence: int
    sentences_per_file: int
    final_sentence_number: int
    base_name: str
    update_cluster_stats: Optional[Callable[[], None]] = None


@dataclass(frozen=True)
class ImageGenerationTask:
    sentence_for_prompt: str
    sentence_text: str
    context_sentences: tuple[str, ...]
    image_key_sentence_number: int
    applies_sentence_numbers: tuple[int, ...]
    chunk_id: str
    range_fragment: str
    chunk_start: int
    chunk_end: int
    images_dir: Path
    image_path: Path
    previous_seed_future: Optional[concurrent.futures.Future]
    previous_key_sentence_number: int


def generate_sentence_images(
    context: ImageGenerationContext, task: ImageGenerationTask
) -> list[_SentenceImageResult]:
    success = False
    image_key_sentence_number = int(task.image_key_sentence_number)
    baseline_seed_image_path: Optional[Path] = None
    try:
        prompt_extra: dict[str, Any] = {}
        denoise_strength = 0.5
        seed_image_path: Optional[Path] = None
        if context.visual_prompt_orchestrator is not None:
            prompt_result = context.visual_prompt_orchestrator.build_sentence_prompt(
                sentence_number=image_key_sentence_number,
                sentence_text=task.sentence_text,
            )
            prompt_full = prompt_result.positive_prompt
            negative_full = prompt_result.negative_prompt
            with context.img2img_capability_lock:
                allow_img2img = bool(context.img2img_capability.get("enabled"))
            if prompt_result.generation_mode != "img2img":
                allow_img2img = False
            elif not allow_img2img:
                raise ValueError("txt2img used mid-scene")
            seed = stable_diffusion_seed(prompt_full or task.sentence_text)
            seed_image_path = prompt_result.init_image
            denoise_strength = float(prompt_result.denoise_strength)
            init_relative = (
                _job_relative_path(seed_image_path, base_dir=context.base_dir_path)
                if seed_image_path is not None
                else None
            )
            prompt_extra = {
                "scene_id": prompt_result.scene_id,
                "sentence_index": int(prompt_result.sentence_index),
                "sentence_delta": prompt_result.sentence_delta,
                "generation_mode": prompt_result.generation_mode,
                "init_image": init_relative,
                "denoise_strength": denoise_strength,
                "reuse_previous_image": bool(prompt_result.reuse_previous_image),
            }
        else:
            with context.prompt_plan_state.lock:
                diffusion = context.prompt_plan_state.prompt_plan.get(
                    image_key_sentence_number
                )
                current_source = (
                    context.prompt_plan_state.prompt_sources.get(image_key_sentence_number)
                    or ""
                )
                baseline_prompt = context.prompt_plan_state.baseline_prompt
                baseline_seed_image_path = (
                    context.prompt_plan_state.baseline_seed_image_path
                )
            if diffusion is None:
                diffusion = DiffusionPrompt(
                    prompt=str(task.sentence_for_prompt).strip()
                )
            scene_description = (
                (diffusion.prompt or "").strip()
                or (task.sentence_for_prompt or "").strip()
            )
            negative = (diffusion.negative_prompt or "").strip()
            baseline_scene = (baseline_prompt.prompt or "").strip()
            baseline_negative = (baseline_prompt.negative_prompt or "").strip()

            with context.img2img_capability_lock:
                allow_img2img = bool(context.img2img_capability.get("enabled"))

            use_baseline_fallback = (
                allow_img2img
                and current_source == "fallback"
                and task.previous_seed_future is None
                and bool(baseline_scene)
            )
            if use_baseline_fallback:
                scene_description = baseline_scene
                negative = baseline_negative
            prompt_full = build_sentence_image_prompt(
                scene_description,
                style_template=context.image_style_template,
            )
            negative_full = build_sentence_image_negative_prompt(
                negative,
                style_template=context.image_style_template,
            )
            seed_source = context.image_prompt_seed_sources.get(image_key_sentence_number)
            if use_baseline_fallback and baseline_scene:
                seed = stable_diffusion_seed(baseline_scene)
            else:
                seed = stable_diffusion_seed(seed_source or task.sentence_for_prompt)

            if allow_img2img and task.previous_seed_future is not None:
                try:
                    task.previous_seed_future.result()
                    if context.image_prompt_batch_size > 1:
                        candidate = (
                            context.media_root
                            / "images"
                            / "batches"
                            / f"batch_{task.previous_key_sentence_number:05d}.png"
                        )
                    else:
                        prev_offset = max(
                            task.previous_key_sentence_number - context.start_sentence, 0
                        )
                        prev_chunk_start = context.start_sentence + (
                            prev_offset // max(1, context.sentences_per_file)
                        ) * max(1, context.sentences_per_file)
                        prev_chunk_end = min(
                            prev_chunk_start + max(1, context.sentences_per_file) - 1,
                            context.final_sentence_number,
                        )
                        prev_range_fragment = output_formatter.format_sentence_range(
                            prev_chunk_start,
                            prev_chunk_end,
                            context.total_fully,
                        )
                        candidate = (
                            context.media_root
                            / "images"
                            / prev_range_fragment
                            / f"sentence_{task.previous_key_sentence_number:05d}.png"
                        )
                    if candidate.exists():
                        seed_image_path = candidate
                except Exception:
                    seed_image_path = None

            if (
                seed_image_path is None
                and allow_img2img
                and baseline_seed_image_path is not None
                and baseline_seed_image_path.exists()
            ):
                seed_image_path = baseline_seed_image_path

        blank_detection_enabled = bool(
            getattr(context.config, "image_blank_detection_enabled", False)
        )
        visual_img2img_required = (
            context.visual_prompt_orchestrator is not None and seed_image_path is not None
        )
        max_image_retries = 2
        task.images_dir.mkdir(parents=True, exist_ok=True)

        import io

        def _is_likely_blank(converted: Image.Image) -> bool:
            try:
                from PIL import ImageStat

                stats = ImageStat.Stat(converted.convert("L"))
                mean = float(stats.mean[0]) if stats.mean else 0.0
                stddev = (
                    float(stats.stddev[0]) if getattr(stats, "stddev", None) else 0.0
                )
            except Exception:
                return False

            if stddev >= 2.0:
                return False
            return mean < 8.0 or mean > 247.0

        last_raw_bytes: Optional[bytes] = None
        for attempt in range(max_image_retries + 1):
            seed_value = int(seed + attempt * 9973) if attempt else int(seed)

            def _txt2img() -> bytes:
                request = DrawThingsImageRequest(
                    prompt=prompt_full,
                    negative_prompt=negative_full,
                    width=int(context.config.image_width or 512),
                    height=int(context.config.image_height or 512),
                    steps=int(context.config.image_steps or 24),
                    cfg_scale=float(context.config.image_cfg_scale or 7.0),
                    sampler_name=context.config.image_sampler_name,
                    seed=seed_value,
                )
                image_bytes, _payload = context.image_client.txt2img(request)
                return image_bytes

            try:
                use_img2img_attempt = (
                    attempt == 0 and seed_image_path is not None and allow_img2img
                )
                if use_img2img_attempt:
                    try:
                        request = DrawThingsImageToImageRequest(
                            prompt=prompt_full,
                            negative_prompt=negative_full,
                            init_image=seed_image_path.read_bytes(),
                            denoising_strength=denoise_strength,
                            width=int(context.config.image_width or 512),
                            height=int(context.config.image_height or 512),
                            steps=int(context.config.image_steps or 24),
                            cfg_scale=float(context.config.image_cfg_scale or 7.0),
                            sampler_name=context.config.image_sampler_name,
                            seed=seed_value,
                        )
                        image_bytes, _payload = context.image_client.img2img(request)
                    except DrawThingsError as exc:
                        message = str(exc)
                        if (
                            "(404)" in message
                            or " 404" in message
                            or "not found" in message.lower()
                        ):
                            with context.img2img_capability_lock:
                                context.img2img_capability["enabled"] = False
                            if context.visual_prompt_orchestrator is not None:
                                context.visual_prompt_orchestrator.mark_img2img_unavailable()
                                raise
                        if context.visual_prompt_orchestrator is not None:
                            raise
                        image_bytes = _txt2img()
                else:
                    image_bytes = _txt2img()
            except DrawThingsError:
                raise
            except Exception:
                raise

            last_raw_bytes = image_bytes

            try:
                with Image.open(io.BytesIO(image_bytes)) as loaded:
                    converted = loaded.convert("RGB")
                    if (
                        blank_detection_enabled
                        and attempt < max_image_retries
                        and _is_likely_blank(converted)
                    ):
                        if context.progress is not None:
                            try:
                                context.progress.record_retry("image", "blank_image")
                            except Exception:
                                pass
                        if not visual_img2img_required:
                            seed_image_path = None
                        continue
                    output = io.BytesIO()
                    converted.save(output, format="PNG")
                    task.image_path.write_bytes(output.getvalue())
                    last_raw_bytes = None
                    break
            except Exception:
                if attempt < max_image_retries:
                    if context.progress is not None:
                        try:
                            context.progress.record_retry("image", "invalid_image_bytes")
                        except Exception:
                            pass
                    if not visual_img2img_required:
                        seed_image_path = None
                    continue
                break

        if last_raw_bytes is not None:
            task.image_path.write_bytes(last_raw_bytes)
        relative_path = _job_relative_path(task.image_path, base_dir=context.base_dir_path)
        if context.visual_prompt_orchestrator is not None:
            try:
                context.visual_prompt_orchestrator.record_image_path(
                    sentence_number=image_key_sentence_number,
                    relative_path=relative_path,
                    image_path=task.image_path,
                )
            except Exception:
                logger.debug(
                    "Unable to record visual canon scene image path.",
                    exc_info=True,
                )
        results: list[_SentenceImageResult] = []
        for sentence_number in task.applies_sentence_numbers:
            offset = max(sentence_number - context.start_sentence, 0)
            sentence_chunk_start = context.start_sentence + (
                offset // max(1, context.sentences_per_file)
            ) * max(1, context.sentences_per_file)
            sentence_chunk_end = min(
                sentence_chunk_start + max(1, context.sentences_per_file) - 1,
                context.final_sentence_number,
            )
            sentence_range_fragment = output_formatter.format_sentence_range(
                sentence_chunk_start, sentence_chunk_end, context.total_fully
            )
            sentence_chunk_id = f"{sentence_range_fragment}_{context.base_name}"
            results.append(
                _SentenceImageResult(
                    chunk_id=sentence_chunk_id,
                    range_fragment=sentence_range_fragment,
                    start_sentence=sentence_chunk_start,
                    end_sentence=sentence_chunk_end,
                    sentence_number=sentence_number,
                    relative_path=relative_path,
                    prompt=prompt_full,
                    negative_prompt=negative_full,
                    extra=dict(prompt_extra),
                )
            )
        success = True
        if context.update_cluster_stats is not None:
            try:
                context.update_cluster_stats()
            except Exception:
                pass
        return results
    except DrawThingsError as exc:
        if context.progress is not None:
            try:
                context.progress.record_retry("image", "drawthings_error")
            except Exception:
                pass
        logger.warning(
            "DrawThings image generation failed",
            extra={
                "event": "pipeline.image.error",
                "attributes": {
                    "sentence_number": image_key_sentence_number,
                    "range_fragment": task.range_fragment,
                    "error": str(exc),
                },
                "console_suppress": True,
            },
        )
        raise
    except Exception as exc:  # pragma: no cover - defensive logging
        if context.progress is not None:
            try:
                context.progress.record_retry("image", "exception")
            except Exception:
                pass
        logger.warning(
            "Image generation failed",
            extra={
                "event": "pipeline.image.error",
                "attributes": {
                    "sentence_number": image_key_sentence_number,
                    "range_fragment": task.range_fragment,
                    "error": str(exc),
                },
                "console_suppress": True,
            },
        )
        raise
    finally:
        if context.progress is not None and context.image_task_total > 0:
            try:
                context.progress.record_step_completion(
                    stage="image",
                    index=int(image_key_sentence_number),
                    metadata={
                        "sentence_total": int(context.total_refined),
                        "image_total": int(context.image_task_total),
                        "image_batch_size": int(context.image_prompt_batch_size),
                        "image_key_sentence": int(image_key_sentence_number),
                        "image_success": success,
                    },
                )
            except Exception:
                pass


__all__ = [
    "ImageGenerationContext",
    "ImageGenerationTask",
    "generate_sentence_images",
]
