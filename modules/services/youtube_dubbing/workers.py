from __future__ import annotations

from typing import Optional

from modules import config_manager as cfg

from .common import _ENCODING_WORKER_CAP, _LLM_WORKER_CAP


def _resolve_worker_count(total_items: int, requested: Optional[int] = None) -> int:
    settings = cfg.get_settings()
    configured = requested if requested is not None else settings.job_max_workers
    if configured is None or configured <= 0:
        return max(1, min(settings.job_max_workers or 1, total_items))
    return max(1, min(configured, total_items))


def _resolve_llm_worker_count(total_items: int) -> int:
    settings = cfg.get_settings()
    # Prefer an explicit LLM-specific override when present, otherwise fall back to
    # the general job worker limit to stay compatible with older configs.
    configured = getattr(settings, "llm_max_workers", None)
    if configured is None:
        configured = getattr(settings, "job_max_workers", None)
    if configured is None or configured <= 0:
        configured = 1
    return max(1, min(_LLM_WORKER_CAP, min(int(configured), total_items)))


def _resolve_encoding_worker_count(total_items: int, requested: Optional[int] = None) -> int:
    settings = cfg.get_settings()
    configured = requested if requested is not None else settings.job_max_workers
    if configured is None or configured <= 0:
        return max(1, min(settings.job_max_workers or 1, total_items, _ENCODING_WORKER_CAP))
    return max(1, min(configured, total_items, _ENCODING_WORKER_CAP))


__all__ = [
    "_resolve_encoding_worker_count",
    "_resolve_llm_worker_count",
    "_resolve_worker_count",
]
