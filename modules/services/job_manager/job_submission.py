"""Job submission logic extracted from PipelineJobManager."""

from __future__ import annotations

import copy
import threading
from dataclasses import replace as dataclass_replace
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Mapping, Optional
from uuid import uuid4

from ... import config_manager as cfg
from ... import logging_manager as log_mgr
from ...permissions import default_job_access
from ...progress_tracker import ProgressTracker
from ..pipeline_service import PipelineRequest, serialize_pipeline_request
from .backpressure import BackpressureAction, BackpressureController, QueueFullError
from .job import PipelineJob, PipelineJobStatus
from .source_persistence import persist_source_file

if TYPE_CHECKING:
    from ..file_locator import FileLocator
    from .job_tuner import PipelineJobTuner

logger = log_mgr.logger


def apply_backpressure(
    backpressure: Optional[BackpressureController],
    bypass: bool = False,
) -> None:
    """Check backpressure and delay/reject as needed."""

    if backpressure is None or bypass:
        return

    action, delay = backpressure.check()
    if action == BackpressureAction.REJECT:
        state = backpressure.get_state()
        raise QueueFullError(
            "Job queue is full, try again later",
            queue_depth=state.queue_depth,
            hard_limit=backpressure.policy.hard_limit,
        )
    elif action == BackpressureAction.DELAY and delay > 0:
        import time
        time.sleep(delay)


def create_pipeline_job(
    request: PipelineRequest,
    *,
    file_locator: "FileLocator",
    tuner: "PipelineJobTuner",
    user_id: Optional[str] = None,
    user_role: Optional[str] = None,
    event_observer: Optional[Callable[[str, Any], None]] = None,
) -> PipelineJob:
    """Create a new PipelineJob from a PipelineRequest.

    Sets up all required directories, attaches tracker and stop_event,
    and persists source file.
    """

    job_id = str(uuid4())
    tracker = request.progress_tracker or ProgressTracker()
    request.progress_tracker = tracker
    stop_event = request.stop_event or threading.Event()
    request.stop_event = stop_event

    request.correlation_id = request.correlation_id or job_id
    request.job_id = job_id

    # Create job directories
    job_root = file_locator.resolve_path(job_id)
    job_root.mkdir(parents=True, exist_ok=True)

    media_root = file_locator.media_root(job_id)
    media_root.mkdir(parents=True, exist_ok=True)

    metadata_root = file_locator.metadata_root(job_id)
    metadata_root.mkdir(parents=True, exist_ok=True)

    data_root = file_locator.data_root(job_id)
    data_root.mkdir(parents=True, exist_ok=True)

    # Persist source file
    source_relative = persist_source_file(job_id, request, file_locator)
    if source_relative:
        request.inputs.book_metadata.update(
            {
                "source_path": source_relative,
                "source_file": source_relative,
            }
        )

    # Set environment overrides
    environment_overrides = dict(request.environment_overrides)
    environment_overrides.setdefault("output_dir", str(media_root))
    job_storage_url = file_locator.resolve_url(job_id, "media")
    if job_storage_url:
        environment_overrides.setdefault("job_storage_url", job_storage_url)
    request.environment_overrides = environment_overrides

    # Build runtime context
    context = request.context
    if context is not None:
        context = dataclass_replace(context, output_dir=media_root)
    else:
        context = cfg.build_runtime_context(
            dict(request.config),
            dict(environment_overrides),
        )
        context = dataclass_replace(context, output_dir=media_root)
    request.context = context

    request_payload = serialize_pipeline_request(request)
    job = PipelineJob(
        job_id=job_id,
        job_type="book",
        status=PipelineJobStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        request=request,
        tracker=tracker,
        stop_event=stop_event,
        request_payload=request_payload,
        resume_context=copy.deepcopy(request_payload),
        user_id=user_id,
        user_role=user_role,
        access=default_job_access(user_id).to_dict(),
    )

    tuning_summary = tuner.build_tuning_summary(request)
    job.tuning_summary = tuning_summary if tuning_summary else None

    # Register event observer
    if event_observer is not None:
        tracker.register_observer(lambda event: event_observer(job_id, event))

    return job


def create_background_job(
    *,
    job_type: str,
    file_locator: "FileLocator",
    tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
    request_payload: Optional[Mapping[str, Any]] = None,
    user_id: Optional[str] = None,
    user_role: Optional[str] = None,
    setup: Optional[Callable[["PipelineJob"], None]] = None,
    event_observer: Optional[Callable[[str, Any], None]] = None,
) -> PipelineJob:
    """Create a non-pipeline job for asynchronous execution."""

    normalized_type = job_type or "custom"
    job_id = str(uuid4())
    tracker = tracker or ProgressTracker()
    stop_event = stop_event or threading.Event()

    job_root = file_locator.resolve_path(job_id)
    job_root.mkdir(parents=True, exist_ok=True)
    file_locator.metadata_root(job_id).mkdir(parents=True, exist_ok=True)
    file_locator.data_root(job_id).mkdir(parents=True, exist_ok=True)

    job = PipelineJob(
        job_id=job_id,
        job_type=normalized_type,
        status=PipelineJobStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        request=None,
        tracker=tracker,
        stop_event=stop_event,
        request_payload=dict(request_payload) if request_payload else None,
        resume_context=None,
        user_id=user_id,
        user_role=user_role,
        access=default_job_access(user_id).to_dict(),
    )

    if setup is not None:
        setup(job)

    if event_observer is not None:
        tracker.register_observer(lambda event: event_observer(job_id, event))

    return job


__all__ = [
    "apply_backpressure",
    "create_pipeline_job",
    "create_background_job",
]
