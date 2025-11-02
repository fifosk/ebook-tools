"""Coordinate state transitions for pipeline jobs with policy enforcement."""

from __future__ import annotations

import copy
import threading
from datetime import datetime, timezone
from typing import Callable, Mapping, MutableMapping, Optional

from .job import PipelineJob, PipelineJobStatus, PipelineJobTransitionError
from .lifecycle import apply_pause_transition, apply_resume_transition
from .persistence import PipelineJobPersistence
from .request_factory import PipelineRequestFactory
from .stores import JobStore


AuthorizationCallback = Callable[[PipelineJob, Optional[str], Optional[str]], None]


class PipelineJobTransitionCoordinator:
    """Apply mutations to jobs while enforcing authorization and state rules."""

    def __init__(
        self,
        *,
        lock: threading.RLock,
        jobs: MutableMapping[str, PipelineJob],
        store: JobStore,
        persistence: PipelineJobPersistence,
        request_factory: PipelineRequestFactory,
        authorize: AuthorizationCallback,
    ) -> None:
        self._lock = lock
        self._jobs = jobs
        self._store = store
        self._persistence = persistence
        self._request_factory = request_factory
        self._authorize = authorize

    def _mutate_job(
        self,
        job_id: str,
        mutator: Callable[[PipelineJob], None],
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        enforce_authorization: bool = True,
    ) -> PipelineJob:
        """Apply ``mutator`` to ``job_id`` and persist the resulting state."""

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                metadata = self._store.get(job_id)
                job = self._persistence.build_job(metadata)

            if enforce_authorization:
                self._authorize(job, user_id=user_id, user_role=user_role)

            try:
                mutator(job)
            except ValueError as exc:  # pragma: no cover - defensive guard
                raise PipelineJobTransitionError(job_id, job, str(exc)) from exc

            if job.status in (
                PipelineJobStatus.PENDING,
                PipelineJobStatus.RUNNING,
                PipelineJobStatus.PAUSING,
                PipelineJobStatus.PAUSED,
            ):
                self._jobs[job_id] = job
            else:
                self._jobs.pop(job_id, None)

            snapshot = self._persistence.snapshot(job)

        self._store.update(snapshot)
        return job

    def pause_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Mark ``job_id`` as paused and persist the updated status."""

        def _pause(job: PipelineJob) -> None:
            if job.job_type != "pipeline":
                raise ValueError(
                    f"Pause is not supported for job type '{job.job_type}'"
                )
            apply_pause_transition(job)
            event = job.stop_event
            if event is None and job.request is not None:
                event = job.request.stop_event
            if event is None:
                event = threading.Event()
            event.set()
            job.stop_event = event
            if job.request is not None:
                job.request.stop_event = event
            if job.tracker is not None:
                job.media_completed = job.tracker.is_complete()

        return self._mutate_job(
            job_id,
            _pause,
            user_id=user_id,
            user_role=user_role,
        )

    def resume_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Resume ``job_id`` from a paused state and persist the change."""

        def _resume(job: PipelineJob) -> None:
            if job.job_type != "pipeline":
                raise ValueError(
                    f"Resume is not supported for job type '{job.job_type}'"
                )
            apply_resume_transition(job)
            payload = job.resume_context or job.request_payload
            if payload is None:
                raise ValueError(
                    f"Job {job.job_id} is missing resume context and cannot be resumed"
                )
            stop_event = threading.Event()
            request = self._request_factory.hydrate_request(
                job,
                payload,
                stop_event=stop_event,
            )
            job.request = request
            job.stop_event = stop_event
            job.request.stop_event = stop_event
            job.result = None
            job.result_payload = None
            job.error_message = None
            job.started_at = None
            job.completed_at = None
            job.owns_translation_pool = False
            if job.request is not None:
                job.request.translation_pool = None
            job.media_completed = False

        return self._mutate_job(
            job_id,
            _resume,
            user_id=user_id,
            user_role=user_role,
        )

    def cancel_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Cancel ``job_id`` and persist the terminal state."""

        def _cancel(job: PipelineJob) -> None:
            if job.status in (
                PipelineJobStatus.COMPLETED,
                PipelineJobStatus.FAILED,
                PipelineJobStatus.CANCELLED,
            ):
                raise ValueError(
                    f"Cannot cancel job {job.job_id} in terminal state {job.status.value}"
                )
            tracker = job.tracker
            if tracker is not None:
                generated_snapshot = tracker.get_generated_files()
                if generated_snapshot:
                    job.generated_files = copy.deepcopy(generated_snapshot)
            event = job.stop_event
            if event is None and job.request is not None:
                event = job.request.stop_event
            if event is None:
                event = threading.Event()
            event.set()
            job.stop_event = event
            if job.request is not None:
                job.request.stop_event = event
            job.status = PipelineJobStatus.CANCELLED
            job.completed_at = job.completed_at or datetime.now(timezone.utc)

        return self._mutate_job(
            job_id,
            _cancel,
            user_id=user_id,
            user_role=user_role,
        )

    def delete_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Remove ``job_id`` from in-memory tracking and persistence."""

        with self._lock:
            job = self._jobs.pop(job_id, None)

            if job is None:
                metadata = self._store.get(job_id)
                job = self._persistence.build_job(metadata)
            else:
                snapshot = self._persistence.snapshot(job)
                try:
                    self._store.update(snapshot)
                except Exception:  # pragma: no cover - best-effort update
                    pass

        self._authorize(job, user_id=user_id, user_role=user_role)

        if job.status not in (
            PipelineJobStatus.COMPLETED,
            PipelineJobStatus.FAILED,
            PipelineJobStatus.CANCELLED,
            PipelineJobStatus.PAUSED,
        ):
            raise ValueError(
                f"Cannot delete job {job.job_id} from state {job.status.value}"
            )

        self._store.delete(job_id)
        return job

    def finish_job(
        self,
        job_id: str,
        *,
        status: PipelineJobStatus = PipelineJobStatus.COMPLETED,
        error_message: Optional[str] = None,
        result_payload: Optional[Mapping[str, object]] = None,
    ) -> PipelineJob:
        """Persist a terminal state for ``job_id`` and return the updated job."""

        if status not in (
            PipelineJobStatus.COMPLETED,
            PipelineJobStatus.FAILED,
            PipelineJobStatus.CANCELLED,
        ):
            raise ValueError(f"Unsupported terminal status: {status}")

        def _finish(job: PipelineJob) -> None:
            job.status = status
            job.error_message = error_message
            if result_payload is not None:
                job.result_payload = copy.deepcopy(dict(result_payload))
            job.completed_at = job.completed_at or datetime.now(timezone.utc)

        return self._mutate_job(
            job_id,
            _finish,
            enforce_authorization=False,
        )


__all__ = ["PipelineJobTransitionCoordinator", "AuthorizationCallback"]
