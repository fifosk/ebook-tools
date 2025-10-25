"""Worker tuning utilities for pipeline jobs."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from ... import config_manager as cfg
from ...translation_engine import ThreadWorkerPool
from ..pipeline_service import PipelineRequest
from .job import PipelineJob


class PipelineJobTuner:
    """Encapsulate worker sizing and tuning behaviour for jobs."""

    def __init__(
        self,
        *,
        worker_pool_factory: Optional[Callable[[PipelineRequest], ThreadWorkerPool]] = None,
        executor_slots_getter: Optional[Callable[[], Optional[int]]] = None,
    ) -> None:
        self._worker_pool_factory = worker_pool_factory or self._default_worker_pool_factory
        self._executor_slots_getter = executor_slots_getter or (lambda: None)

    def build_tuning_summary(self, request: PipelineRequest) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        thread_count = self._resolve_thread_count(request)
        if thread_count is not None:
            summary["thread_count"] = thread_count
        queue_size = self._resolve_queue_size(request)
        if queue_size is not None:
            summary["queue_size"] = queue_size
        job_max_workers = self._resolve_job_max_workers(request)
        if job_max_workers is not None:
            summary["job_max_workers"] = job_max_workers
        slide_workers = request.pipeline_overrides.get("slide_parallel_workers")
        if slide_workers is None:
            slide_workers = request.config.get("slide_parallel_workers")
        slide_workers_value = self._coerce_non_negative_int(slide_workers)
        if slide_workers_value is not None:
            summary["slide_parallel_workers"] = slide_workers_value
        slide_mode = request.pipeline_overrides.get("slide_parallelism") or request.config.get(
            "slide_parallelism"
        )
        if slide_mode:
            summary["slide_parallelism"] = slide_mode
        executor_slots = self._executor_slots_getter()
        if isinstance(executor_slots, int) and executor_slots > 0:
            summary["job_worker_slots"] = executor_slots
        pipeline_mode_override = request.pipeline_overrides.get("pipeline_mode")
        pipeline_mode = pipeline_mode_override
        if pipeline_mode is None and request.context is not None:
            pipeline_mode = request.context.pipeline_enabled
        if pipeline_mode is None:
            pipeline_mode = request.config.get("pipeline_mode")
        if pipeline_mode is not None:
            summary["pipeline_mode"] = bool(pipeline_mode)
        hardware_defaults = cfg.get_hardware_tuning_defaults()
        hardware_profile = hardware_defaults.get("profile")
        if isinstance(hardware_profile, str) and hardware_profile:
            summary.setdefault("hardware_profile", hardware_profile)
        detected_cpu = hardware_defaults.get("detected_cpu_count")
        if isinstance(detected_cpu, int) and detected_cpu > 0:
            summary.setdefault("detected_cpu_cores", detected_cpu)
        detected_memory = hardware_defaults.get("detected_memory_gib")
        if isinstance(detected_memory, (int, float)) and detected_memory > 0:
            summary.setdefault("detected_memory_gib", detected_memory)
        return summary

    def acquire_worker_pool(
        self, job: PipelineJob
    ) -> tuple[Optional[ThreadWorkerPool], bool]:
        request = job.request
        if request is None:
            return None, False
        if request.translation_pool is not None:
            pool = request.translation_pool
            self._maybe_update_translation_pool_summary(job, pool)
            return pool, False
        pool = self._worker_pool_factory(request)
        request.translation_pool = pool
        self._maybe_update_translation_pool_summary(job, pool)
        return pool, True

    def _default_worker_pool_factory(self, request: PipelineRequest) -> ThreadWorkerPool:
        max_workers = self._resolve_thread_count(request)
        return ThreadWorkerPool(max_workers=max_workers)

    def _maybe_update_translation_pool_summary(
        self, job: PipelineJob, pool: Optional[ThreadWorkerPool]
    ) -> None:
        if job.tuning_summary is None or pool is None:
            return
        worker_count = getattr(pool, "max_workers", None)
        if worker_count is not None:
            job.tuning_summary["translation_pool_workers"] = int(worker_count)
        pool_mode = getattr(pool, "mode", None)
        if pool_mode:
            job.tuning_summary["translation_pool_mode"] = pool_mode

    @staticmethod
    def _coerce_non_negative_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        return number if number >= 0 else None

    def _resolve_thread_count(self, request: PipelineRequest) -> Optional[int]:
        candidate = request.pipeline_overrides.get("thread_count")
        if candidate is None and request.context is not None:
            candidate = request.context.thread_count
        if candidate is None:
            candidate = request.config.get("thread_count")
        value = self._coerce_non_negative_int(candidate)
        if value is None:
            return None
        return max(1, value)

    def _resolve_queue_size(self, request: PipelineRequest) -> Optional[int]:
        candidate = request.pipeline_overrides.get("queue_size")
        if candidate is None and request.context is not None:
            candidate = request.context.queue_size
        if candidate is None:
            candidate = request.config.get("queue_size")
        return self._coerce_non_negative_int(candidate)

    def _resolve_job_max_workers(self, request: PipelineRequest) -> Optional[int]:
        candidate = request.pipeline_overrides.get("job_max_workers")
        if candidate is None:
            candidate = request.config.get("job_max_workers")
        if candidate is None:
            candidate = getattr(cfg.get_settings(), "job_max_workers", None)
        value = self._coerce_non_negative_int(candidate)
        if value is None or value <= 0:
            defaults = cfg.get_hardware_tuning_defaults()
            recommended = defaults.get("job_max_workers")
            if isinstance(recommended, int) and recommended > 0:
                return recommended
            return None
        return value
