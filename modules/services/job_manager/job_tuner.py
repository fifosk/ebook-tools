"""Worker tuning utilities for pipeline jobs."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from ... import config_manager as cfg
from ...translation_engine import ThreadWorkerPool
from ...llm_providers import is_local_llm_provider, split_llm_model_identifier
from ..pipeline_service import PipelineRequest
from .job import PipelineJob

_LLM_PROVIDER_ALIASES = {"llm", "ollama", "default"}
_LLM_BATCH_WORKERS = 1


class WorkerPoolCache:
    """Cache and reuse worker pools to reduce thread creation overhead.

    Pools are cached by their configuration (worker count) and reused
    when available. Idle pools are cleaned up after a timeout.
    """

    def __init__(
        self,
        *,
        max_cached_pools: int = 4,
        idle_timeout: float = 300.0,  # 5 minutes
    ) -> None:
        self._max_cached = max(1, max_cached_pools)
        self._idle_timeout = idle_timeout
        self._lock = threading.Lock()
        # List of (pool, worker_count, last_used_time, in_use)
        self._pools: List[Tuple[ThreadWorkerPool, int, float, bool]] = []

    def acquire(self, max_workers: int) -> Tuple[ThreadWorkerPool, bool]:
        """Acquire a pool with the specified worker count.

        Args:
            max_workers: Number of workers needed.

        Returns:
            Tuple of (pool, is_new) where is_new indicates if pool was created.
        """
        with self._lock:
            # Try to find an available pool with matching worker count
            for i, (pool, workers, _, in_use) in enumerate(self._pools):
                if workers == max_workers and not in_use:
                    self._pools[i] = (pool, workers, time.monotonic(), True)
                    return pool, False

            # Clean up idle pools if at capacity
            if len(self._pools) >= self._max_cached:
                self._cleanup_idle_locked()

            # Create new pool if still at capacity, reuse oldest idle
            if len(self._pools) >= self._max_cached:
                for i, (pool, workers, _, in_use) in enumerate(self._pools):
                    if not in_use:
                        # Shutdown old pool and create new one
                        try:
                            pool.shutdown(wait=False)
                        except Exception:
                            pass
                        new_pool = ThreadWorkerPool(max_workers=max_workers)
                        self._pools[i] = (new_pool, max_workers, time.monotonic(), True)
                        return new_pool, True

        # Create new pool
        pool = ThreadWorkerPool(max_workers=max_workers)
        with self._lock:
            if len(self._pools) < self._max_cached:
                self._pools.append((pool, max_workers, time.monotonic(), True))
        return pool, True

    def release(self, pool: ThreadWorkerPool) -> None:
        """Release a pool back to the cache for reuse."""
        with self._lock:
            for i, (p, workers, _, in_use) in enumerate(self._pools):
                if p is pool:
                    self._pools[i] = (p, workers, time.monotonic(), False)
                    return
            # Pool not in cache (was created when at capacity), shut it down
        try:
            pool.shutdown(wait=False)
        except Exception:
            pass

    def _cleanup_idle_locked(self) -> None:
        """Remove pools that have been idle too long. Must hold lock."""
        now = time.monotonic()
        to_remove = []
        for i, (pool, _, last_used, in_use) in enumerate(self._pools):
            if not in_use and (now - last_used) > self._idle_timeout:
                to_remove.append(i)
                try:
                    pool.shutdown(wait=False)
                except Exception:
                    pass
        for i in reversed(to_remove):
            self._pools.pop(i)

    def shutdown_all(self) -> None:
        """Shutdown all cached pools."""
        with self._lock:
            for pool, _, _, _ in self._pools:
                try:
                    pool.shutdown(wait=False)
                except Exception:
                    pass
            self._pools.clear()

    @property
    def cached_count(self) -> int:
        """Return number of pools in cache."""
        with self._lock:
            return len(self._pools)

    @property
    def in_use_count(self) -> int:
        """Return number of pools currently in use."""
        with self._lock:
            return sum(1 for _, _, _, in_use in self._pools if in_use)


class PipelineJobTuner:
    """Encapsulate worker sizing and tuning behaviour for jobs."""

    def __init__(
        self,
        *,
        worker_pool_factory: Optional[Callable[[PipelineRequest], ThreadWorkerPool]] = None,
        executor_slots_getter: Optional[Callable[[], Optional[int]]] = None,
        pool_cache: Optional[WorkerPoolCache] = None,
        enable_pool_caching: bool = True,
    ) -> None:
        self._worker_pool_factory = worker_pool_factory or self._default_worker_pool_factory
        self._executor_slots_getter = executor_slots_getter or (lambda: None)
        self._pool_cache = pool_cache if enable_pool_caching else None
        if self._pool_cache is None and enable_pool_caching:
            self._pool_cache = WorkerPoolCache()

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
        """Acquire a worker pool for the job, using cache if available.

        Args:
            job: The pipeline job needing a worker pool.

        Returns:
            Tuple of (pool, is_new) where is_new indicates if pool was created.
        """
        request = job.request
        if request is None:
            return None, False
        if request.translation_pool is not None:
            pool = request.translation_pool
            self._maybe_update_translation_pool_summary(job, pool)
            return pool, False

        # Determine required worker count
        max_workers = self._resolve_thread_count(request)
        if max_workers is None:
            max_workers = 4  # Default fallback

        # Try to get pool from cache
        if self._pool_cache is not None:
            pool, is_new = self._pool_cache.acquire(max_workers)
        else:
            pool = self._worker_pool_factory(request)
            is_new = True

        request.translation_pool = pool
        self._maybe_update_translation_pool_summary(job, pool)
        return pool, is_new

    def release_worker_pool(self, job: PipelineJob) -> None:
        """Release a job's worker pool back to the cache for reuse.

        Should be called when job completes or is cancelled.

        Args:
            job: The pipeline job whose pool should be released.
        """
        request = job.request
        if request is None:
            return
        pool = request.translation_pool
        if pool is None:
            return

        # Clear the reference so pool isn't used after release
        request.translation_pool = None

        if self._pool_cache is not None:
            self._pool_cache.release(pool)
        else:
            # No cache, shutdown directly
            try:
                pool.shutdown(wait=False)
            except Exception:
                pass

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
        thread_override = request.pipeline_overrides.get("thread_count")
        if thread_override is not None:
            value = self._coerce_non_negative_int(thread_override)
            if value is None:
                return None
            return max(1, value)

        candidate = None
        if request.context is not None:
            candidate = request.context.thread_count
        if candidate is None:
            candidate = request.config.get("thread_count")
        value = self._coerce_non_negative_int(candidate)
        if value is None:
            return None
        resolved = max(1, value)
        if self._should_limit_batch_workers(request):
            return min(resolved, _LLM_BATCH_WORKERS)
        return resolved

    @staticmethod
    def _should_limit_batch_workers(request: PipelineRequest) -> bool:
        inputs = request.inputs
        if inputs is None:
            return False
        try:
            batch_size = int(getattr(inputs, "translation_batch_size", 0) or 0)
        except (TypeError, ValueError):
            batch_size = 0
        if batch_size <= 1:
            return False
        provider = (getattr(inputs, "translation_provider", "") or "").strip().lower()
        if provider not in _LLM_PROVIDER_ALIASES:
            return False
        model_name = None
        for source in (request.pipeline_overrides, request.config):
            if not isinstance(source, dict):
                continue
            override_model = source.get("ollama_model") or source.get("llm_model")
            if isinstance(override_model, str) and override_model.strip():
                model_name = override_model.strip()
                break
        if model_name:
            provider, stripped_model = split_llm_model_identifier(model_name)
            local_flag = is_local_llm_provider(provider)
            if local_flag is not None:
                return local_flag
            candidate = stripped_model or model_name
            return "cloud" not in candidate.lower()
        llm_source = request.pipeline_overrides.get("llm_source")
        if llm_source is None and request.context is not None:
            llm_source = request.context.llm_source
        if llm_source is None:
            llm_source = request.config.get("llm_source")
        if not isinstance(llm_source, str):
            llm_source = cfg.get_llm_source()
        return llm_source.strip().lower() == "local"

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

    def shutdown(self) -> None:
        """Shutdown the tuner and release all cached resources."""
        if self._pool_cache is not None:
            self._pool_cache.shutdown_all()

    @property
    def pool_cache_stats(self) -> Dict[str, int]:
        """Return statistics about the worker pool cache."""
        if self._pool_cache is None:
            return {"enabled": 0, "cached": 0, "in_use": 0}
        return {
            "enabled": 1,
            "cached": self._pool_cache.cached_count,
            "in_use": self._pool_cache.in_use_count,
        }
