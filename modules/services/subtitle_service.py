"""Background service coordinating subtitle processing jobs."""

from __future__ import annotations

import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional

from modules import logging_manager as log_mgr
from modules.services.file_locator import FileLocator
from modules.services.job_manager import PipelineJobManager, PipelineJobStatus
from modules.subtitles import SubtitleJobOptions
from modules.subtitles.processing import (
    DEFAULT_OUTPUT_SUFFIX,
    SubtitleJobCancelled,
    SubtitleProcessingError,
    load_subtitle_cues,
    process_subtitle_file,
)

logger = log_mgr.get_logger().getChild("services.subtitles")

SUPPORTED_EXTENSIONS = {".srt", ".vtt"}


@dataclass(frozen=True)
class SubtitleSubmission:
    """Description of a subtitle submission request."""

    source_path: Path
    original_name: str
    options: SubtitleJobOptions
    cleanup: bool = False


class SubtitleService:
    """Coordinate ingestion and processing of subtitle jobs."""

    def __init__(
        self,
        job_manager: PipelineJobManager,
        *,
        locator: Optional[FileLocator] = None,
        default_source_dir: Optional[Path] = None,
    ) -> None:
        self._job_manager = job_manager
        self._locator = locator or job_manager.file_locator
        self._default_source_dir = (
            Path(default_source_dir).expanduser()
            if default_source_dir is not None
            else Path("/Volumes/Data/Download/Subs")
        )
        self._default_source_dir = self._default_source_dir.resolve()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def enqueue(
        self,
        submission: SubtitleSubmission,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ):
        """Register ``submission`` for processing and return the job handle."""

        resolved_source = submission.source_path.expanduser().resolve()
        if not resolved_source.exists():
            raise FileNotFoundError(f"Subtitle source '{resolved_source}' does not exist")
        if resolved_source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported subtitle extension '{resolved_source.suffix}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        options = submission.options
        source_name = submission.original_name or resolved_source.name
        def _setup(job):
            data_root = self._locator.data_root(job.job_id)
            data_root.mkdir(parents=True, exist_ok=True)
            target_path = data_root / source_name
            shutil.copy2(resolved_source, target_path)
            if submission.cleanup:
                try:
                    resolved_source.unlink(missing_ok=True)  # type: ignore[arg-type]
                except Exception:  # pragma: no cover - best effort
                    logger.debug(
                        "Unable to delete temporary subtitle source %s",
                        resolved_source,
                        exc_info=True,
                    )
            job.request_payload = {
                "source_file": target_path.name,
                "options": options.to_dict(),
                "submitted_source": str(resolved_source),
                "original_name": source_name,
                "cleanup": submission.cleanup,
            }
            tracker_local = job.tracker
            if tracker_local is not None:
                try:
                    cues = load_subtitle_cues(target_path)
                except Exception as exc:
                    raise SubtitleProcessingError(
                        f"Failed to parse {target_path.name}: {exc}"
                    ) from exc
                tracker_local.set_total(len(cues))

        def _worker(job):
            tracker_local = job.tracker
            stop_event = job.stop_event or threading.Event()
            data_root = self._locator.data_root(job.job_id)
            source_file = (job.request_payload or {}).get("source_file") if job.request_payload else None
            if not source_file:
                job.status = PipelineJobStatus.FAILED
                job.error_message = "Missing source file for subtitle job"
                return
            input_path = data_root / str(source_file)
            subtitles_root = self._locator.subtitles_root(job.job_id)
            subtitles_root.mkdir(parents=True, exist_ok=True)
            target_fragment = options.target_language.lower().replace(" ", "-")
            source_stem = Path(source_file).stem
            output_name = f"{source_stem}.{target_fragment}.{DEFAULT_OUTPUT_SUFFIX}"
            output_path = subtitles_root / output_name

            try:
                result = process_subtitle_file(
                    input_path,
                    output_path,
                    options,
                    tracker=tracker_local,
                    stop_event=stop_event,
                )
            except SubtitleJobCancelled:
                job.status = PipelineJobStatus.CANCELLED
                job.error_message = None
                return
            except Exception as exc:
                job.status = PipelineJobStatus.FAILED
                job.error_message = str(exc)
                raise

            job.status = PipelineJobStatus.COMPLETED
            job.error_message = None
            relative_path = output_path.relative_to(self._locator.job_root(job.job_id)).as_posix()
            result_payload: Dict[str, object] = {
                "subtitle": {
                    "output_path": output_path.as_posix(),
                    "relative_path": relative_path,
                    "metadata": {
                        **result.metadata,
                        "download_url": self._locator.resolve_url(job.job_id, relative_path),
                    },
                    "cues": result.cue_count,
                    "translated": result.translated_count,
                }
            }
            job.result_payload = result_payload
            file_entry = {
                "type": "subtitle",
                "name": output_path.name,
                "relative_path": relative_path,
                "url": self._locator.resolve_url(job.job_id, relative_path),
                "path": output_path.as_posix(),
            }
            job.generated_files = {
                "chunks": [
                    {
                        "chunk_id": "subtitle",
                        "range_fragment": None,
                        "start_sentence": 1,
                        "end_sentence": result.translated_count,
                        "files": [file_entry],
                    }
                ],
                "files": [file_entry],
                "complete": True,
            }
            job.media_completed = True

        return self._job_manager.submit_background_job(
            job_type="subtitle",
            worker=_worker,
            request_payload={
                "source_path": str(resolved_source),
                "original_name": source_name,
                "options": options.to_dict(),
            },
            user_id=user_id,
            user_role=user_role,
            setup=_setup,
        )

    def list_sources(self, directory: Optional[Path] = None) -> List[Path]:
        """Return discovered subtitle files under ``directory``."""

        base = (directory or self._default_source_dir).expanduser()
        if not base.exists():
            return []
        entries: List[Path] = []
        for candidate in base.iterdir():
            if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
                entries.append(candidate.resolve())
        entries.sort()
        return entries

    def default_source_directory(self) -> Path:
        """Return the configured directory for local subtitle discovery."""

        return self._default_source_dir
