"""Logging utilities for pipeline job lifecycle events."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, ContextManager, Optional

from ... import logging_manager as log_mgr
from ... import observability
from .job import PipelineJobStatus

if TYPE_CHECKING:
    from .job import PipelineJob

logger = log_mgr.logger


def _job_correlation_id(job: "PipelineJob") -> Optional[str]:
    """Extract correlation ID from job request."""

    request = job.request
    if request is None:
        return None
    return request.correlation_id


@contextmanager
def _log_context(job: "PipelineJob"):
    """Context manager for job-scoped logging."""

    with log_mgr.log_context(
        job_id=job.job_id,
        correlation_id=_job_correlation_id(job),
    ):
        yield


def log_job_started(job: "PipelineJob") -> None:
    """Log pipeline job start event."""

    with _log_context(job):
        logger.info(
            "Pipeline job started",
            extra={
                "event": "pipeline.job.started",
                "status": PipelineJobStatus.RUNNING.value,
                "console_suppress": True,
            },
        )


def log_job_finished(job: "PipelineJob", status: PipelineJobStatus) -> None:
    """Log pipeline job completion event."""

    with _log_context(job):
        if status == PipelineJobStatus.PAUSED:
            logger.info(
                "Pipeline job paused",
                extra={
                    "event": "pipeline.job.paused",
                    "status": status.value,
                    "console_suppress": True,
                },
            )
        else:
            logger.info(
                "Pipeline job finished",
                extra={
                    "event": "pipeline.job.finished",
                    "status": status.value,
                    "console_suppress": True,
                },
            )


def log_job_error(job: "PipelineJob", exc: Exception) -> None:
    """Log pipeline job error event."""

    with _log_context(job):
        logger.error(
            "Pipeline job encountered an error",
            extra={
                "event": "pipeline.job.error",
                "status": PipelineJobStatus.FAILED.value,
                "attributes": {"error": str(exc)},
            },
        )


def log_job_interrupted(job: "PipelineJob", status: PipelineJobStatus) -> None:
    """Log pipeline job interruption event."""

    with _log_context(job):
        logger.info(
            "Pipeline job interrupted",
            extra={
                "event": "pipeline.job.interrupted",
                "status": status.value,
                "console_suppress": True,
            },
        )


def log_generic_job_started(job: "PipelineJob") -> None:
    """Log generic background job start event."""

    with _log_context(job):
        logger.info(
            "Background job started",
            extra={
                "event": f"{job.job_type}.job.started",
                "status": PipelineJobStatus.RUNNING.value,
                "console_suppress": True,
            },
        )


def log_generic_job_finished(job: "PipelineJob", status: PipelineJobStatus) -> None:
    """Log generic background job completion event."""

    with _log_context(job):
        logger.info(
            "Background job finished",
            extra={
                "event": f"{job.job_type}.job.finished",
                "status": status.value,
                "console_suppress": True,
            },
        )


def log_generic_job_submitted(job: "PipelineJob") -> None:
    """Log generic background job submission event."""

    with _log_context(job):
        logger.info(
            "Background job submitted",
            extra={
                "event": f"{job.job_type}.job.submitted",
                "status": job.status.value,
                "console_suppress": True,
            },
        )


def log_generic_job_error(job: "PipelineJob", exc: Exception) -> None:
    """Log generic background job error event."""

    with _log_context(job):
        logger.error(
            "Background job encountered an error",
            extra={
                "event": f"{job.job_type}.job.error",
                "status": PipelineJobStatus.FAILED.value,
                "attributes": {"error": str(exc)},
            },
        )


def pipeline_operation_context(job: "PipelineJob") -> ContextManager[object]:
    """Return observability context for a pipeline operation."""

    return observability.pipeline_operation(
        "job",
        attributes={
            "job_id": job.job_id,
            "correlation_id": _job_correlation_id(job),
        },
    )


def record_job_metric(name: str, value: float, attributes: dict[str, str]) -> None:
    """Record a job-related metric."""

    observability.record_metric(name, value, attributes)


__all__ = [
    "_job_correlation_id",
    "_log_context",
    "log_job_started",
    "log_job_finished",
    "log_job_error",
    "log_job_interrupted",
    "log_generic_job_started",
    "log_generic_job_finished",
    "log_generic_job_submitted",
    "log_generic_job_error",
    "pipeline_operation_context",
    "record_job_metric",
]
