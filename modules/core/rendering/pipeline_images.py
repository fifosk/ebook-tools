"""Image generation orchestration for the rendering pipeline."""

from __future__ import annotations

import concurrent.futures
import json
import queue
import threading
from collections import deque
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from modules import output_formatter
from modules.logging_manager import logger
from modules.images.drawthings import (
    DrawThingsClientLike,
    resolve_drawthings_client,
)
from modules.images.visual_prompting import VisualPromptOrchestrator

from .pipeline_image_generation import (
    ImageGenerationContext,
    ImageGenerationTask,
    generate_sentence_images,
)
from .pipeline_image_prompt_plan import (
    PromptPlanContext,
    PromptPlanState,
    build_prompt_plan,
)
from .pipeline_image_state import (
    _ImageGenerationState,
    _SentenceImageResult,
    _resolve_job_root,
    _resolve_media_root,
)


class ImagePipelineCoordinator:
    """Handle prompt planning + image generation for pipeline runs."""

    def __init__(
        self,
        *,
        config,
        progress,
        state,
        base_dir: str,
        base_name: str,
        book_metadata: Mapping[str, Any],
        full_sentences: Sequence[str],
        sentences: Sequence[str],
        start_sentence: int,
        total_refined: int,
        total_fully: int,
        sentences_per_file: int,
        generate_images: bool,
        stop_event: threading.Event,
    ) -> None:
        self._config = config
        self._progress = progress
        self._state = state
        self._stop_event = stop_event

        self._base_dir_path = Path(base_dir)
        self._base_name = base_name
        self._book_metadata = book_metadata
        self._full_sentences = full_sentences
        self._start_sentence = start_sentence
        self._total_refined = total_refined
        self._total_fully = total_fully
        self._sentences_per_file = sentences_per_file
        self._target_sentences = [str(entry) for entry in (sentences or ())]
        self._final_sentence_number = start_sentence + max(total_refined - 1, 0)

        self._media_root = _resolve_media_root(self._base_dir_path)
        self._job_root = _resolve_job_root(self._media_root)

        self._generate_images = bool(generate_images)
        self._image_state: Optional[_ImageGenerationState] = None
        if self._generate_images:
            self._image_state = _ImageGenerationState()
            self._state.image_state = self._image_state

        self._image_base_urls = list(self._config.image_api_base_urls or ())
        if not self._image_base_urls and self._config.image_api_base_url:
            self._image_base_urls.append(self._config.image_api_base_url)
        self._image_cluster_nodes: list[dict[str, object]] = []
        self._image_cluster_available: list[str] = []
        self._image_cluster_unavailable: list[str] = []

        self._image_prompt_pipeline = str(
            getattr(self._config, "image_prompt_pipeline", "prompt_plan")
            or "prompt_plan"
        ).strip().lower()
        self._use_visual_canon_pipeline = self._image_prompt_pipeline in {
            "visual_canon",
            "visual-canon",
            "canon",
        }

        self._image_client: Optional[DrawThingsClientLike] = None
        self._image_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self._image_futures: set[concurrent.futures.Future] = set()
        self._visual_prompt_orchestrator: Optional[VisualPromptOrchestrator] = None

        if self._generate_images:
            self._configure_drawthings_client()
            if self._image_client is not None:
                max_workers = (
                    1
                    if self._use_visual_canon_pipeline
                    else max(1, int(self._config.image_concurrency or 1))
                )
                self._image_executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=max_workers
                )

        if self._image_base_urls:
            self._image_cluster_nodes = [
                {"base_url": url, "active": url in self._image_cluster_available}
                for url in self._image_base_urls
            ]

        if self._generate_images and self._image_cluster_nodes:
            self._update_image_cluster_stats()

        if self._generate_images and self._use_visual_canon_pipeline:
            self._configure_visual_canon()

        self._prompt_context_window = max(
            0,
            int(getattr(self._config, "image_prompt_context_sentences", 0) or 0),
        )
        self._recent_prompt_sentences: deque[str] = deque(
            maxlen=self._prompt_context_window
        )

        image_prompt_batching_enabled = bool(
            getattr(self._config, "image_prompt_batching_enabled", True)
        )
        image_prompt_batch_size = max(
            1,
            int(getattr(self._config, "image_prompt_batch_size", 10) or 10),
        )
        image_prompt_batch_size = min(image_prompt_batch_size, 50)
        if not image_prompt_batching_enabled:
            image_prompt_batch_size = 1
        if self._use_visual_canon_pipeline:
            if image_prompt_batch_size != 1:
                logger.info(
                    "Visual canon prompting forces image_prompt_batch_size=1 (was %s).",
                    image_prompt_batch_size,
                )
            image_prompt_batching_enabled = False
            image_prompt_batch_size = 1
        self._image_prompt_batch_size = image_prompt_batch_size

        image_prompt_plan_batch_size = max(
            1,
            int(getattr(self._config, "image_prompt_plan_batch_size", 50) or 50),
        )
        image_prompt_plan_batch_size = min(image_prompt_plan_batch_size, 50)
        self._image_prompt_plan_batch_size = image_prompt_plan_batch_size

        self._image_prompt_batches: list[list[str]] = []
        self._image_prompt_batch_starts: list[int] = []
        if image_prompt_batch_size > 1 and self._final_sentence_number >= start_sentence:
            for batch_start in range(
                start_sentence,
                self._final_sentence_number + 1,
                image_prompt_batch_size,
            ):
                offset_start = max(batch_start - start_sentence, 0)
                offset_end = min(
                    offset_start + image_prompt_batch_size, len(self._target_sentences)
                )
                self._image_prompt_batches.append(
                    list(self._target_sentences[offset_start:offset_end])
                )
                self._image_prompt_batch_starts.append(int(batch_start))

        self._image_task_total = 0
        if (
            self._generate_images
            and self._image_executor is not None
            and self._image_client is not None
        ):
            self._image_task_total = (
                len(self._image_prompt_batch_starts)
                if image_prompt_batch_size > 1
                else len(self._target_sentences)
            )
            if self._progress is not None and self._image_task_total > 0:
                self._progress.set_total(total_refined + self._image_task_total)

        if image_prompt_batch_size > 1:
            self._image_prompt_seed_sources = {
                batch_start: "\n".join(
                    str(sentence).strip()
                    for sentence in batch
                    if str(sentence).strip()
                ).strip()
                for batch_start, batch in zip(
                    self._image_prompt_batch_starts, self._image_prompt_batches
                )
            }
        else:
            self._image_prompt_seed_sources = {
                start_sentence + offset: str(sentence).strip()
                for offset, sentence in enumerate(self._target_sentences)
            }

        self._prompt_plan_state: Optional[PromptPlanState] = None
        if self._generate_images:
            self._prompt_plan_state = PromptPlanState()

        self._image_style_template = getattr(self._config, "image_style_template", None)
        self._image_seed_with_previous_image = bool(
            getattr(self._config, "image_seed_with_previous_image", False)
        )

        self._img2img_capability = {
            "enabled": True
            if self._use_visual_canon_pipeline
            else self._image_seed_with_previous_image
        }
        self._img2img_capability_lock = threading.Lock()
        self._prompt_plan_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self._prompt_plan_future: Optional[concurrent.futures.Future] = None
        self._pending_image_keys: set[int] = set()
        self._generation_context: Optional[ImageGenerationContext] = None

        self._scheduled_image_keys: set[int] = set()
        self._previous_image_future: Optional[concurrent.futures.Future] = None
        self._previous_image_key_sentence_number: Optional[int] = None
        if (
            self._generate_images
            and self._image_client is not None
            and self._prompt_plan_state is not None
        ):
            self._generation_context = ImageGenerationContext(
                config=self._config,
                progress=self._progress,
                base_dir_path=self._base_dir_path,
                media_root=self._media_root,
                image_client=self._image_client,
                prompt_plan_state=self._prompt_plan_state,
                image_prompt_seed_sources=self._image_prompt_seed_sources,
                image_prompt_batch_size=self._image_prompt_batch_size,
                image_style_template=self._image_style_template,
                visual_prompt_orchestrator=self._visual_prompt_orchestrator,
                img2img_capability=self._img2img_capability,
                img2img_capability_lock=self._img2img_capability_lock,
                image_task_total=self._image_task_total,
                total_refined=self._total_refined,
                total_fully=self._total_fully,
                start_sentence=self._start_sentence,
                sentences_per_file=self._sentences_per_file,
                final_sentence_number=self._final_sentence_number,
                base_name=self._base_name,
                update_cluster_stats=self._update_image_cluster_stats,
            )

        self._start_prompt_plan()

    @property
    def image_state(self) -> Optional[_ImageGenerationState]:
        return self._image_state

    @property
    def batch_size(self) -> int:
        return self._image_prompt_batch_size

    def _configure_drawthings_client(self) -> None:
        if not self._image_base_urls:
            logger.warning(
                "Image generation enabled but image_api_base_url(s) are not configured.",
                extra={
                    "event": "pipeline.image.missing_base_url",
                    "attributes": {
                        "image_prompt_pipeline": self._image_prompt_pipeline,
                        "image_api_base_url": self._config.image_api_base_url,
                        "image_api_base_urls": list(self._config.image_api_base_urls or ()),
                        "add_images": bool(self._generate_images),
                    },
                    "console_suppress": True,
                },
            )
            if self._progress is not None:
                self._progress.record_retry("image", "missing_base_url")
            return

        try:
            self._image_client, available_urls, unavailable_urls = resolve_drawthings_client(
                base_urls=self._image_base_urls,
                timeout_seconds=float(self._config.image_api_timeout_seconds),
            )
            self._image_cluster_available = list(available_urls or ())
            self._image_cluster_unavailable = list(unavailable_urls or ())
            if unavailable_urls:
                logger.warning(
                    "DrawThings endpoints unavailable: %s",
                    ", ".join(unavailable_urls),
                    extra={
                        "event": "pipeline.image.unavailable",
                        "attributes": {"unavailable": unavailable_urls},
                        "console_suppress": True,
                    },
                )
            if self._image_client is None:
                logger.warning(
                    "Image generation enabled but no DrawThings endpoints are reachable.",
                    extra={
                        "event": "pipeline.image.unreachable",
                        "attributes": {"configured": self._image_base_urls},
                        "console_suppress": True,
                    },
                )
        except Exception as exc:
            logger.warning("Unable to configure DrawThings client: %s", exc)
            self._image_client = None

    def _configure_visual_canon(self) -> None:
        if self._job_root is None:
            logger.warning(
                "Visual canon pipeline enabled but job root is unavailable; skipping image prompting.",
                extra={
                    "event": "pipeline.image.visual_canon.missing_job_root",
                    "console_suppress": True,
                },
            )
            self._use_visual_canon_pipeline = False
            return
        if self._image_client is None:
            self._use_visual_canon_pipeline = False
            return

        content_index_payload = None
        raw_content_index = self._book_metadata.get("content_index")
        if isinstance(raw_content_index, Mapping):
            content_index_payload = dict(raw_content_index)
        else:
            content_index_path = self._job_root / "metadata" / "content_index.json"
            if content_index_path.exists():
                try:
                    loaded = json.loads(content_index_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, Mapping):
                        content_index_payload = dict(loaded)
                except Exception:
                    content_index_payload = None
        try:
            orchestrator = VisualPromptOrchestrator(
                job_root=self._job_root,
                book_metadata=self._book_metadata,
                full_sentences=self._full_sentences,
                content_index=content_index_payload,
                scope_start_sentence=self._start_sentence,
                scope_end_sentence=self._final_sentence_number,
                lazy_scenes=True,
            )
            orchestrator.prepare()
            self._visual_prompt_orchestrator = orchestrator
        except Exception as exc:
            logger.warning(
                "Unable to prepare visual canon prompts: %s",
                exc,
                extra={
                    "event": "pipeline.image.visual_canon.error",
                    "attributes": {"error": str(exc)},
                    "console_suppress": True,
                },
            )
            self._visual_prompt_orchestrator = None
            self._use_visual_canon_pipeline = False

    def _update_image_cluster_stats(self) -> None:
        if self._progress is None or not self._image_cluster_nodes:
            return
        stats_list: list[dict[str, object]] = []
        if self._image_client is not None and hasattr(self._image_client, "snapshot_stats"):
            try:
                stats_list = list(self._image_client.snapshot_stats())
            except Exception:
                stats_list = []
        stats_by_url: dict[str, dict[str, object]] = {}
        for entry in stats_list:
            if not isinstance(entry, Mapping):
                continue
            base_url = entry.get("base_url")
            if isinstance(base_url, str) and base_url:
                stats_by_url[base_url] = dict(entry)
        nodes_payload: list[dict[str, object]] = []
        for node in self._image_cluster_nodes:
            base_url = node.get("base_url")
            if not isinstance(base_url, str):
                continue
            entry = dict(node)
            stats = stats_by_url.get(base_url)
            if stats:
                entry["processed"] = stats.get("processed", 0)
                entry["total_seconds"] = stats.get("total_seconds")
                entry["avg_seconds_per_image"] = stats.get("avg_seconds_per_image")
            else:
                entry.setdefault("processed", 0)
                entry.setdefault("avg_seconds_per_image", None)
            nodes_payload.append(entry)
        self._progress.update_generated_files_metadata(
            {"image_cluster": {"nodes": nodes_payload, "unavailable": self._image_cluster_unavailable}}
        )

    def _start_prompt_plan(self) -> None:
        state = self._prompt_plan_state
        if state is None:
            return
        if (
            self._image_executor is not None
            and self._image_client is not None
            and self._generate_images
            and not self._use_visual_canon_pipeline
        ):
            context_window = max(
                0,
                int(getattr(self._config, "image_prompt_context_sentences", 0) or 0),
            )
            window_start_idx = max(self._start_sentence - 1, 0)
            window_end_idx = min(
                window_start_idx + self._total_refined, self._total_fully
            )
            prefix_start = max(0, window_start_idx - context_window)
            suffix_end = min(self._total_fully, window_end_idx + context_window)
            context_prefix = (
                tuple(self._full_sentences[prefix_start:window_start_idx])
                if prefix_start < window_start_idx
                else ()
            )
            context_suffix = (
                tuple(self._full_sentences[window_end_idx:suffix_end])
                if window_end_idx < suffix_end
                else ()
            )
            prompt_plan_path = (
                (self._job_root / "metadata" / "image_prompt_plan.json")
                if self._job_root is not None
                else None
            )

            prompt_plan_context = PromptPlanContext(
                image_prompt_batch_size=self._image_prompt_batch_size,
                image_prompt_plan_batch_size=self._image_prompt_plan_batch_size,
                image_prompt_batches=self._image_prompt_batches,
                image_prompt_batch_starts=self._image_prompt_batch_starts,
                target_sentences=self._target_sentences,
                full_sentences=self._full_sentences,
                start_sentence=self._start_sentence,
                total_refined=self._total_refined,
                total_fully=self._total_fully,
                image_prompt_seed_sources=self._image_prompt_seed_sources,
                image_style_template=self._image_style_template,
                image_seed_with_previous_image=self._image_seed_with_previous_image,
                base_dir_path=self._base_dir_path,
                media_root=self._media_root,
                image_client=self._image_client,
                config=self._config,
                progress=self._progress,
                prompt_plan_path=prompt_plan_path,
                context_prefix=context_prefix,
                context_suffix=context_suffix,
                context_window=context_window,
                prefix_start=prefix_start,
                window_start_idx=window_start_idx,
                window_end_idx=window_end_idx,
                suffix_end=suffix_end,
            )

            self._prompt_plan_executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=1
            )
            self._prompt_plan_future = self._prompt_plan_executor.submit(
                build_prompt_plan, state, prompt_plan_context
            )
        else:
            state.ready_event.set()

    def _should_schedule(self) -> bool:
        return (
            self._image_executor is not None
            and self._image_state is not None
            and self._image_client is not None
            and not self._stop_event.is_set()
        )

    def _resolve_image_key(self, sentence_number: int) -> int:
        image_key_sentence_number = int(sentence_number)
        if self._image_prompt_batch_size > 1:
            image_key_sentence_number = self._start_sentence + (
                (sentence_number - self._start_sentence) // self._image_prompt_batch_size
            ) * self._image_prompt_batch_size
            image_key_sentence_number = max(
                self._start_sentence, int(image_key_sentence_number)
            )
        return image_key_sentence_number

    def _build_fallback_prompt(self, sentence_number: int, default_text: str) -> str:
        fallback_prompt_text = str(default_text or "").strip()
        if self._image_prompt_batch_size > 1:
            offset_start = max(sentence_number - self._start_sentence, 0)
            offset_end = min(
                offset_start + self._image_prompt_batch_size, len(self._target_sentences)
            )
            batch_items = [
                str(entry).strip()
                for entry in self._target_sentences[offset_start:offset_end]
                if str(entry).strip()
            ]
            if batch_items:
                fallback_prompt_text = "Batch narrative:\n" + "\n".join(
                    f"- {entry}" for entry in batch_items
                )
        return fallback_prompt_text

    def _prompt_plan_has_key(self, sentence_number: int) -> bool:
        state = self._prompt_plan_state
        if state is None:
            return False
        with state.lock:
            return sentence_number in state.prompt_plan

    def decorate_metadata(self, metadata_payload: dict[str, Any], *, sentence_number: int) -> None:
        if not self._generate_images:
            return
        if self._image_prompt_batch_size <= 1:
            return
        batch_start_sentence_number = self._start_sentence + (
            (sentence_number - self._start_sentence) // self._image_prompt_batch_size
        ) * self._image_prompt_batch_size
        batch_start_sentence_number = max(
            self._start_sentence, int(batch_start_sentence_number)
        )
        batch_end_sentence_number = min(
            batch_start_sentence_number + self._image_prompt_batch_size - 1,
            self._final_sentence_number,
        )
        relative_path = (
            f"media/images/batches/batch_{batch_start_sentence_number:05d}.png"
        )
        image_payload = metadata_payload.get("image")
        if isinstance(image_payload, Mapping):
            image_payload = dict(image_payload)
        else:
            image_payload = {}
        image_payload.setdefault("path", relative_path)
        image_payload.setdefault("batch_start_sentence", batch_start_sentence_number)
        image_payload.setdefault("batch_end_sentence", batch_end_sentence_number)
        image_payload.setdefault("batch_size", self._image_prompt_batch_size)
        metadata_payload["image"] = image_payload
        metadata_payload["imagePath"] = relative_path

    def handle_sentence(
        self,
        *,
        sentence_number: int,
        sentence_for_prompt: str,
        sentence_text: str,
    ) -> None:
        if not self._generate_images:
            return
        if self._image_prompt_batch_size > 1:
            image_key_sentence_number = self._resolve_image_key(sentence_number)
        else:
            image_key_sentence_number = int(sentence_number)

        context_sentences = (
            tuple(self._recent_prompt_sentences)
            if self._prompt_context_window > 0
            else ()
        )

        if self._should_schedule():
            fallback_prompt_text = self._build_fallback_prompt(
                image_key_sentence_number, sentence_for_prompt
            )
            if self._use_visual_canon_pipeline or self._prompt_plan_has_key(
                image_key_sentence_number
            ):
                self._submit_sentence_image(
                    sentence_number=image_key_sentence_number,
                    sentence_for_prompt=fallback_prompt_text,
                    sentence_text=str(sentence_text or "").strip(),
                    context_sentences=context_sentences,
                )
            else:
                self._pending_image_keys.add(image_key_sentence_number)

        if self._prompt_context_window > 0:
            self._recent_prompt_sentences.append(str(sentence_for_prompt or "").strip())

    def tick(self) -> None:
        if not self._generate_images:
            return
        self._drain_prompt_plan_queue()
        self._drain_image_futures(wait=False)
        if (
            self._pending_image_keys
            and self._should_schedule()
            and not self._use_visual_canon_pipeline
        ):
            ready_numbers = sorted(self._pop_ready_image_keys())
            for sentence_number in ready_numbers:
                offset_start = sentence_number - self._start_sentence
                if offset_start < 0 or offset_start >= len(self._target_sentences):
                    continue
                fallback_prompt_text = self._build_fallback_prompt(
                    sentence_number,
                    str(self._target_sentences[offset_start]).strip(),
                )
                self._submit_sentence_image(
                    sentence_number=sentence_number,
                    sentence_for_prompt=fallback_prompt_text,
                    sentence_text=str(self._target_sentences[offset_start]).strip(),
                )

    def finalize_pending(self) -> None:
        if not self._generate_images:
            return
        state = self._prompt_plan_state
        if state is None:
            return
        if (
            not self._pending_image_keys
            or not self._should_schedule()
            or self._use_visual_canon_pipeline
        ):
            return
        if self._prompt_plan_future is not None and not state.ready_event.is_set():
            try:
                self._prompt_plan_future.result()
            except Exception:
                pass
        self._drain_prompt_plan_queue()
        ready_numbers = sorted(self._pop_ready_image_keys())
        if state.ready_event.is_set() and self._pending_image_keys:
            ready_numbers.extend(sorted(self._pending_image_keys))
            self._pending_image_keys.clear()
        for sentence_number in ready_numbers:
            offset_start = sentence_number - self._start_sentence
            if offset_start < 0 or offset_start >= len(self._target_sentences):
                continue
            fallback_prompt_text = self._build_fallback_prompt(
                sentence_number,
                str(self._target_sentences[offset_start]).strip(),
            )
            self._submit_sentence_image(
                sentence_number=sentence_number,
                sentence_for_prompt=fallback_prompt_text,
                sentence_text=str(self._target_sentences[offset_start]).strip(),
            )

    def shutdown(self, *, cancelled: bool) -> None:
        if self._prompt_plan_executor is not None:
            if cancelled and self._prompt_plan_future is not None:
                self._prompt_plan_future.cancel()
            self._prompt_plan_executor.shutdown(wait=False)
        if self._image_executor is not None:
            if cancelled:
                for future in list(self._image_futures):
                    future.cancel()
            if self._image_futures:
                self._drain_image_futures(wait=True)
            self._image_executor.shutdown(wait=True)

    def _drain_prompt_plan_queue(self) -> None:
        state = self._prompt_plan_state
        if state is None:
            return
        while True:
            try:
                keys = state.ready_queue.get_nowait()
            except queue.Empty:
                break
            for key in keys:
                self._pending_image_keys.add(int(key))

    def _pop_ready_image_keys(self) -> list[int]:
        if not self._pending_image_keys:
            return []
        state = self._prompt_plan_state
        if state is None:
            return []
        with state.lock:
            ready = [key for key in self._pending_image_keys if key in state.prompt_plan]
        if not ready:
            return []
        for key in ready:
            self._pending_image_keys.discard(key)
        return ready

    def _extract_image_results(self, image_result) -> list[_SentenceImageResult]:
        if isinstance(image_result, _SentenceImageResult):
            return [image_result]
        if isinstance(image_result, Sequence):
            return [
                item
                for item in image_result
                if isinstance(item, _SentenceImageResult)
            ]
        return []

    def _drain_image_futures(self, *, wait: bool) -> None:
        if not self._image_futures:
            return
        if wait:
            futures = list(self._image_futures)
            self._image_futures.clear()
            iterable = concurrent.futures.as_completed(futures)
        else:
            futures = [future for future in list(self._image_futures) if future.done()]
            for future in futures:
                self._image_futures.discard(future)
            iterable = futures

        for future in iterable:
            try:
                image_result = future.result()
            except Exception:
                continue
            if self._image_state is None:
                continue
            results = self._extract_image_results(image_result)
            if not results:
                continue

            updated_chunks: dict[str, _SentenceImageResult] = {}
            for item in results:
                if self._image_state.apply(item):
                    updated_chunks[item.chunk_id] = item

            if self._progress is None:
                continue
            for chunk_id, item in updated_chunks.items():
                snapshot = self._image_state.snapshot_chunk(chunk_id)
                if snapshot:
                    self._progress.record_generated_chunk(
                        chunk_id=str(snapshot.get("chunk_id") or chunk_id),
                        start_sentence=int(
                            snapshot.get("start_sentence") or item.start_sentence
                        ),
                        end_sentence=int(
                            snapshot.get("end_sentence") or item.end_sentence
                        ),
                        range_fragment=str(
                            snapshot.get("range_fragment") or item.range_fragment
                        ),
                        files=snapshot.get("files") or {},
                        extra_files=snapshot.get("extra_files") or [],
                        sentences=snapshot.get("sentences") or [],
                        audio_tracks=snapshot.get("audio_tracks") or None,
                        timing_tracks=snapshot.get("timing_tracks") or None,
                    )

    def _submit_sentence_image(
        self,
        *,
        sentence_number: int,
        sentence_for_prompt: str,
        sentence_text: str,
        context_sentences: tuple[str, ...] = (),
    ) -> None:
        if not self._should_schedule():
            return
        if self._generation_context is None:
            return
        prompt_state = self._prompt_plan_state
        if prompt_state is None:
            return

        image_key_sentence_number = int(sentence_number)
        if image_key_sentence_number in self._scheduled_image_keys:
            return

        batch_start_sentence_number = image_key_sentence_number
        batch_end_sentence_number = (
            min(
                batch_start_sentence_number + self._image_prompt_batch_size - 1,
                self._final_sentence_number,
            )
            if self._image_prompt_batch_size > 1
            else batch_start_sentence_number
        )
        applies_sentence_numbers = tuple(
            range(batch_start_sentence_number, batch_end_sentence_number + 1)
        )

        offset = max(batch_start_sentence_number - self._start_sentence, 0)
        chunk_start = self._start_sentence + (
            offset // max(1, self._sentences_per_file)
        ) * max(1, self._sentences_per_file)
        chunk_end = min(
            chunk_start + max(1, self._sentences_per_file) - 1,
            self._final_sentence_number,
        )
        range_fragment = output_formatter.format_sentence_range(
            chunk_start, chunk_end, self._total_fully
        )
        chunk_id = f"{range_fragment}_{self._base_name}"
        if self._image_prompt_batch_size > 1:
            images_dir = self._media_root / "images" / "batches"
            image_path = images_dir / f"batch_{batch_start_sentence_number:05d}.png"
        else:
            images_dir = self._media_root / "images" / range_fragment
            image_path = images_dir / f"sentence_{batch_start_sentence_number:05d}.png"

        previous_seed_future = None
        previous_key_sentence_number = batch_start_sentence_number - (
            self._image_prompt_batch_size if self._image_prompt_batch_size > 1 else 1
        )
        if (
            self._previous_image_future is not None
            and self._previous_image_key_sentence_number == previous_key_sentence_number
        ):
            with prompt_state.lock:
                previous_source = (
                    prompt_state.prompt_sources.get(previous_key_sentence_number) or ""
                )
            if previous_source in {"llm", "llm_retry"}:
                previous_seed_future = self._previous_image_future

        task = ImageGenerationTask(
            sentence_for_prompt=sentence_for_prompt,
            sentence_text=sentence_text,
            context_sentences=context_sentences,
            image_key_sentence_number=image_key_sentence_number,
            applies_sentence_numbers=applies_sentence_numbers,
            chunk_id=chunk_id,
            range_fragment=range_fragment,
            chunk_start=chunk_start,
            chunk_end=chunk_end,
            images_dir=images_dir,
            image_path=image_path,
            previous_seed_future=previous_seed_future,
            previous_key_sentence_number=previous_key_sentence_number,
        )

        future = self._image_executor.submit(
            generate_sentence_images, self._generation_context, task
        )
        self._image_futures.add(future)
        self._scheduled_image_keys.add(image_key_sentence_number)
        self._previous_image_future = future
        self._previous_image_key_sentence_number = image_key_sentence_number


__all__ = ["ImagePipelineCoordinator"]
