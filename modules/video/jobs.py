"""Background job orchestration for standalone video rendering tasks."""

from __future__ import annotations

from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from io import BytesIO
import threading
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Sequence
from uuid import uuid4

from pydub import AudioSegment

from modules import logging_manager as log_mgr
from modules.progress_tracker import ProgressEvent, ProgressTracker
from modules.services.file_locator import FileLocator
from modules.video.api import VideoService
from modules.video.backends import VideoRenderOptions


logger = log_mgr.logger


class VideoJobStatus(str, Enum):
    """Enumeration of possible job lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class VideoAudioSource:
    """Description of an audio input that should back a rendered slide."""

    data: bytes | None = None
    path: Path | None = None
    mime_type: str | None = None
    format_hint: str | None = None


@dataclass(slots=True)
class VideoRenderTask:
    """Work item describing a single video rendering request."""

    slides: Sequence[str]
    audio_sources: Sequence[VideoAudioSource]
    options: VideoRenderOptions
    output_filename: str


@dataclass(slots=True)
class VideoJobResult:
    """Metadata describing the rendered video artifact."""

    path: Path
    relative_path: str
    url: str | None


@dataclass(slots=True)
class VideoJob:
    """Container tracking the execution state for a submitted job."""

    job_id: str
    status: VideoJobStatus
    created_at: datetime
    tracker: ProgressTracker
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    last_event: ProgressEvent | None = None
    result: VideoJobResult | None = None
    generated_files: Dict[str, object] | None = None


class VideoJobManager:
    """Coordinate background execution of :class:`VideoRenderTask` instances."""

    def __init__(
        self,
        *,
        locator: FileLocator | None = None,
        max_workers: int | None = None,
        executor_factory: Callable[[int], Executor] | None = None,
        video_service_factory: Callable[[], VideoService] | None = None,
    ) -> None:
        self._locator = locator or FileLocator()
        resolved_workers = max(1, int(max_workers or 2))
        factory = executor_factory or (lambda workers: ThreadPoolExecutor(max_workers=workers))
        self._executor = factory(resolved_workers)
        self._video_service_factory = video_service_factory or VideoService
        self._jobs: Dict[str, VideoJob] = {}
        self._lock = threading.RLock()

    @property
    def locator(self) -> FileLocator:
        """Return the file locator used for artifact storage."""

        return self._locator

    def list(self) -> list[VideoJob]:
        """Return a snapshot of all known jobs."""

        with self._lock:
            return list(self._jobs.values())

    def get(self, job_id: str) -> VideoJob | None:
        """Return the job registered under ``job_id`` if present."""

        with self._lock:
            return self._jobs.get(job_id)

    def submit(
        self,
        task: VideoRenderTask,
        *,
        video_service: VideoService | None = None,
    ) -> VideoJob:
        """Register ``task`` for background execution."""

        if len(task.slides) != len(task.audio_sources):
            raise ValueError("Each slide must have a corresponding audio track.")

        job_id = str(uuid4())
        tracker = ProgressTracker(total_blocks=len(task.slides))
        job = VideoJob(
            job_id=job_id,
            status=VideoJobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            tracker=tracker,
        )

        tracker.register_observer(lambda event: self._record_event(job_id, event))

        with self._lock:
            self._jobs[job_id] = job

        service = video_service or self._video_service_factory()
        self._executor.submit(self._execute_job, job_id, task, service)
        return job

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _record_event(self, job_id: str, event: ProgressEvent) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.last_event = event

    def _execute_job(
        self,
        job_id: str,
        task: VideoRenderTask,
        service: VideoService,
    ) -> None:
        job = self.get(job_id)
        if job is None:
            return

        start_time = datetime.now(timezone.utc)
        with self._lock:
            job.status = VideoJobStatus.RUNNING
            job.started_at = start_time

        tracker = job.tracker
        tracker.publish_start({"stage": "video_render", "total": len(task.slides)})

        try:
            output_path = self._reserve_output_path(job_id, task.output_filename)
            audio_segments = self._load_audio_segments(task.audio_sources)

            tracker.publish_progress({"stage": "render", "message": "Rendering video"})
            rendered_path = Path(
                service.render(task.slides, audio_segments, str(output_path), task.options)
            )
            if not rendered_path.is_absolute():
                rendered_path = output_path

            for index, _ in enumerate(task.slides):
                sentence_number = task.options.batch_start + index
                tracker.record_media_completion(index, sentence_number)

            job_dir = self._locator.resolve_path(job_id)
            try:
                relative_path = rendered_path.relative_to(job_dir).as_posix()
            except ValueError:
                relative_path = rendered_path.name

            artifact_url = self._locator.resolve_url(job_id, relative_path)
            job.generated_files = {
                "files": [
                    {
                        "type": "video",
                        "path": relative_path,
                        "url": artifact_url,
                    }
                ]
            }

            with self._lock:
                job.result = VideoJobResult(
                    path=rendered_path,
                    relative_path=relative_path,
                    url=artifact_url,
                )
                job.status = VideoJobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)

            tracker.mark_finished(reason="completed", forced=False)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception(
                "Video job %s failed", job_id, extra={"event": "video.job.failed"}
            )
            tracker.record_error(exc, metadata={"stage": "render"})
            tracker.mark_finished(reason="error", forced=True)
            with self._lock:
                job.status = VideoJobStatus.FAILED
                job.error = str(exc)
                job.completed_at = datetime.now(timezone.utc)

    def _reserve_output_path(self, job_id: str, requested_name: str) -> Path:
        job_dir = self._locator.resolve_path(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)

        candidate_name = Path(requested_name or "rendered.mp4").name or "rendered.mp4"
        if not candidate_name.lower().endswith(".mp4"):
            candidate_name = f"{candidate_name}.mp4"

        stem = Path(candidate_name).stem
        suffix = Path(candidate_name).suffix

        candidate = job_dir / candidate_name
        counter = 1
        while candidate.exists():
            candidate = job_dir / f"{stem}-{counter}{suffix}"
            counter += 1
        return candidate

    def _load_audio_segments(
        self, sources: Iterable[VideoAudioSource]
    ) -> List[AudioSegment]:
        segments: List[AudioSegment] = []
        for index, source in enumerate(sources):
            try:
                segment = self._load_audio_segment(source)
            except Exception as exc:  # pragma: no cover - defensive logging
                raise ValueError(f"Failed to load audio track {index + 1}: {exc}") from exc
            segments.append(segment)
        return segments

    def _load_audio_segment(self, source: VideoAudioSource) -> AudioSegment:
        audio_format = self._resolve_audio_format(source)
        if source.data is not None:
            buffer = BytesIO(source.data)
            return AudioSegment.from_file(buffer, format=audio_format)
        if source.path is not None:
            return AudioSegment.from_file(source.path, format=audio_format)
        raise ValueError("Audio source must define inline data or a file path")

    def _resolve_audio_format(self, source: VideoAudioSource) -> str:
        if source.format_hint:
            return source.format_hint
        if source.mime_type:
            normalized = source.mime_type.lower()
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
            if normalized in mapping:
                return mapping[normalized]
            if normalized.startswith("audio/"):
                return normalized.split("/", 1)[1]
        if source.path is not None:
            suffix = source.path.suffix.lstrip(".")
            if suffix:
                return suffix
        return "mp3"


__all__ = [
    "VideoAudioSource",
    "VideoJob",
    "VideoJobManager",
    "VideoJobResult",
    "VideoJobStatus",
    "VideoRenderTask",
]
