"""Service layer for orchestrating video generation tasks."""

from __future__ import annotations

import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence
from uuid import uuid4

from pydub import AudioSegment

from modules import logging_manager as log_mgr
from modules.progress_tracker import ProgressEvent, ProgressTracker
from modules.services.file_locator import FileLocator
from modules.services.job_manager import PipelineJobManager, PipelineJobStatus
from modules.services.video_payloads import VideoRenderRequestPayload
from modules.video.backends import BaseVideoRenderer, create_video_renderer
from modules.video.jobs import VideoAudioSource, VideoRenderTask

logger = log_mgr.get_logger().getChild("services.video")


@dataclass(frozen=True)
class VideoTaskSnapshot:
    """Immutable state representation returned to API layers."""

    request_id: str
    job_id: str
    status: str
    output_path: str | None
    logs_path: str | None
    logs_url: str | None
    error: str | None = None


@dataclass
class _VideoTaskState:
    request_id: str
    job_id: str
    task: VideoRenderTask
    tracker: ProgressTracker
    parameters: Dict[str, Any]
    status: str = "queued"
    logs_path: Path | None = None
    metadata_path: Path | None = None
    output_path: Path | None = None
    error: str | None = None
    future: Future[Any] | None = None
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None


class VideoService:
    """Coordinate video rendering tasks for existing pipeline jobs."""

    def __init__(
        self,
        job_manager: PipelineJobManager,
        *,
        locator: FileLocator | None = None,
        max_workers: int | None = None,
        renderer_factory: Callable[[], BaseVideoRenderer] | None = None,
    ) -> None:
        self._job_manager = job_manager
        self._locator = locator or job_manager.file_locator
        worker_count = max(1, int(max_workers or 2))
        self._executor = ThreadPoolExecutor(max_workers=worker_count)
        self._renderer_factory = renderer_factory or (lambda: create_video_renderer("ffmpeg", {}))
        self._renderer = self._renderer_factory()
        self._lock = threading.RLock()
        self._tasks: Dict[str, _VideoTaskState] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def enqueue(
        self,
        job_id: str,
        parameters: Mapping[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> VideoTaskSnapshot:
        """Schedule a video render task for ``job_id``."""

        job = self._job_manager.get(job_id)
        if job is None:
            raise KeyError(f"Unknown job_id '{job_id}'")
        if job.status in {PipelineJobStatus.CANCELLED, PipelineJobStatus.FAILED}:
            raise ValueError(f"Cannot generate video for job in status '{job.status.value}'")

        payload = VideoRenderRequestPayload.model_validate(dict(parameters))
        task = payload.to_task(self._locator)
        request_id = uuid4().hex
        video_root = self._video_root(job_id)
        video_root.mkdir(parents=True, exist_ok=True)
        logs_path = video_root / f"{request_id}.log"
        metadata_path = video_root / f"{request_id}.json"

        tracker = ProgressTracker(total_blocks=len(task.slides))
        state = _VideoTaskState(
            request_id=request_id,
            job_id=job_id,
            task=task,
            tracker=tracker,
            parameters=dict(parameters),
            logs_path=logs_path,
            metadata_path=metadata_path,
        )

        job_tracker = job.tracker
        if job_tracker is not None:
            tracker.register_observer(self._build_tracker_relay(job_tracker, state))

        with self._lock:
            self._tasks[job_id] = state
            self._write_metadata_unlocked(state)
        self._write_log(logs_path, f"Queued video request at {state.submitted_at.isoformat()}\n")

        state.future = self._executor.submit(
            self._run_task,
            state,
            correlation_id,
        )
        return self._build_snapshot(state)

    def get_status(self, job_id: str) -> VideoTaskSnapshot | None:
        """Return the current status snapshot for ``job_id`` if present."""

        with self._lock:
            state = self._tasks.get(job_id)
            if state is None:
                return None
            return self._build_snapshot(state)

    def get_preview_path(self, job_id: str) -> Path:
        """Return the rendered video path for ``job_id``."""

        with self._lock:
            state = self._tasks.get(job_id)
            if state is None or state.output_path is None:
                raise FileNotFoundError(f"No rendered video available for job '{job_id}'")
            return state.output_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _run_task(
        self,
        state: _VideoTaskState,
        correlation_id: str | None,
    ) -> None:
        job = self._job_manager.get(state.job_id)
        job_tracker = job.tracker if job is not None else None
        self._update_status(state, "running")
        started = datetime.now(timezone.utc)
        with self._lock:
            state.started_at = started
            self._write_metadata_unlocked(state)
        self._write_log(state.logs_path, f"Render started at {started.isoformat()}\n")

        if job_tracker is not None:
            job_tracker.publish_progress(
                {
                    "stage": "video",
                    "status": "running",
                    "request_id": state.request_id,
                    "correlation_id": correlation_id,
                }
            )

        try:
            audio_segments = self._load_audio_segments(state.task.audio_sources)
            output_path = self._render_video(state.job_id, state.task, audio_segments)
            self._finalize_success(state, output_path, job_tracker)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception(
                "Video generation failed for job %s",
                state.job_id,
                extra={
                    "event": "video.service.error",
                    "request_id": state.request_id,
                },
            )
            self._finalize_failure(state, exc, job_tracker)

    def _render_video(
        self,
        job_id: str,
        task: VideoRenderTask,
        audio_segments: Sequence[AudioSegment],
    ) -> Path:
        output_path = self._reserve_output_path(job_id, task.output_filename)
        rendered = Path(
            self._renderer.render_slides(
                task.slides,
                audio_segments,
                str(output_path),
                task.options,
            )
        )
        if not rendered.is_absolute():
            rendered = output_path
        return rendered

    def _load_audio_segments(self, sources: Iterable[VideoAudioSource]) -> list[AudioSegment]:
        segments: list[AudioSegment] = []
        for index, source in enumerate(sources, start=1):
            try:
                segments.append(self._load_audio_segment(source))
            except Exception as exc:  # pragma: no cover - defensive guard
                raise ValueError(f"Failed to load audio track {index}: {exc}") from exc
        return segments

    def _load_audio_segment(self, source: VideoAudioSource) -> AudioSegment:
        fmt = self._resolve_audio_format(source)
        if source.data is not None:
            return AudioSegment.from_file(BytesIO(source.data), format=fmt)
        if source.path is not None:
            return AudioSegment.from_file(source.path, format=fmt)
        raise ValueError("Audio source must define inline data or a file path")

    @staticmethod
    def _resolve_audio_format(source: VideoAudioSource) -> str:
        if source.format_hint:
            return source.format_hint
        if source.mime_type:
            mapping = {
                "audio/mpeg": "mp3",
                "audio/mp3": "mp3",
                "audio/wav": "wav",
                "audio/x-wav": "wav",
                "audio/aac": "aac",
                "audio/flac": "flac",
                "audio/ogg": "ogg",
                "audio/webm": "webm",
            }
            lowered = source.mime_type.lower()
            if lowered in mapping:
                return mapping[lowered]
            if lowered.startswith("audio/"):
                return lowered.split("/", 1)[1]
        if source.path is not None:
            suffix = source.path.suffix.lstrip(".")
            if suffix:
                return suffix
        return "mp3"

    def _finalize_success(
        self,
        state: _VideoTaskState,
        output_path: Path,
        job_tracker: ProgressTracker | None,
    ) -> None:
        completed = datetime.now(timezone.utc)
        state.tracker.publish_progress(
            {
                "stage": "video_render",
                "message": "Rendering completed.",
            }
        )
        for index, _ in enumerate(state.task.slides):
            sentence_number = state.task.options.batch_start + index
            state.tracker.record_media_completion(index, sentence_number)
        state.tracker.mark_finished(reason="completed", forced=False)
        with self._lock:
            state.status = "completed"
            state.output_path = output_path
            state.completed_at = completed
            self._write_metadata_unlocked(state)
        self._write_log(state.logs_path, f"Render completed at {completed.isoformat()}\n")

        relative_path = self._relative_to_job(state.job_id, output_path)
        if job_tracker is not None:
            job_tracker.publish_progress(
                {
                    "stage": "video",
                    "status": "completed",
                    "request_id": state.request_id,
                    "video_path": relative_path,
                }
            )
            job_tracker.record_generated_chunk(
                chunk_id=f"video-{state.request_id}",
                start_sentence=state.task.options.batch_start,
                end_sentence=state.task.options.batch_end,
                range_fragment=f"{state.task.options.batch_start}-{state.task.options.batch_end}",
                files={"video": relative_path},
                sentences=None,
            )

    def _finalize_failure(
        self,
        state: _VideoTaskState,
        exc: Exception,
        job_tracker: ProgressTracker | None,
    ) -> None:
        state.tracker.record_error(exc, metadata={"stage": "video_render"})
        state.tracker.mark_finished(reason="error", forced=True)
        completed = datetime.now(timezone.utc)
        with self._lock:
            state.status = "failed"
            state.error = str(exc)
            state.completed_at = completed
            self._write_metadata_unlocked(state)
        self._write_log(
            state.logs_path,
            f"Render failed at {completed.isoformat()}: {exc}\n",
        )
        if job_tracker is not None:
            job_tracker.publish_progress(
                {
                    "stage": "video",
                    "status": "failed",
                    "request_id": state.request_id,
                    "error": str(exc),
                }
            )
            job_tracker.record_error(exc, {"stage": "video"})

    def _build_snapshot(self, state: _VideoTaskState) -> VideoTaskSnapshot:
        output_relative = (
            self._relative_to_job(state.job_id, state.output_path) if state.output_path else None
        )
        logs_relative = (
            self._relative_to_job(state.job_id, state.logs_path) if state.logs_path else None
        )
        logs_url = self._locator.resolve_url(state.job_id, logs_relative) if logs_relative else None
        return VideoTaskSnapshot(
            request_id=state.request_id,
            job_id=state.job_id,
            status=state.status,
            output_path=output_relative,
            logs_path=logs_relative,
            logs_url=logs_url,
            error=state.error,
        )

    def _update_status(self, state: _VideoTaskState, status: str) -> None:
        with self._lock:
            state.status = status
            self._write_metadata_unlocked(state)

    def _reserve_output_path(self, job_id: str, requested_name: str) -> Path:
        video_dir = self._video_root(job_id)
        video_dir.mkdir(parents=True, exist_ok=True)
        candidate_name = Path(requested_name or "rendered.mp4").name or "rendered.mp4"
        if not candidate_name.lower().endswith(".mp4"):
            candidate_name = f"{candidate_name}.mp4"

        stem = Path(candidate_name).stem
        suffix = Path(candidate_name).suffix

        candidate = video_dir / candidate_name
        counter = 1
        while candidate.exists():
            candidate = video_dir / f"{stem}-{counter}{suffix}"
            counter += 1
        return candidate

    def _video_root(self, job_id: str) -> Path:
        return self._locator.media_root(job_id) / "video"

    def _relative_to_job(self, job_id: str, path: Path | None) -> str | None:
        if path is None:
            return None
        job_root = self._locator.resolve_path(job_id)
        try:
            return path.relative_to(job_root).as_posix()
        except ValueError:
            return path.name

    def _write_metadata_unlocked(self, state: _VideoTaskState) -> None:
        if state.metadata_path is None:
            return
        payload = {
            "request_id": state.request_id,
            "job_id": state.job_id,
            "status": state.status,
            "submitted_at": state.submitted_at.isoformat(),
            "started_at": state.started_at.isoformat() if state.started_at else None,
            "completed_at": state.completed_at.isoformat() if state.completed_at else None,
            "output_path": self._relative_to_job(state.job_id, state.output_path),
            "logs_path": self._relative_to_job(state.job_id, state.logs_path),
            "error": state.error,
            "parameters": dict(state.parameters),
        }
        state.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        state.metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _write_log(path: Path | None, message: str) -> None:
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(message)
        except OSError:  # pragma: no cover - best effort logging
            logger.debug("Unable to write video service log to %s", path, exc_info=True)

    @staticmethod
    def _build_tracker_relay(
        pipeline_tracker: ProgressTracker,
        state: _VideoTaskState,
    ):
        def _relay(event: ProgressEvent) -> None:
            metadata = dict(event.metadata)
            metadata.setdefault("stage", "video")
            metadata.setdefault("request_id", state.request_id)
            metadata.setdefault("status", state.status)
            metadata.setdefault("completed", event.snapshot.completed)
            metadata.setdefault("total", event.snapshot.total)
            pipeline_tracker.publish_progress(metadata)

        return _relay


__all__ = ["VideoService", "VideoTaskSnapshot"]
