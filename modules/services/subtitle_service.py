"""Background service coordinating subtitle processing jobs."""

from __future__ import annotations

import os
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
    ASS_EXTENSION,
    DEFAULT_OUTPUT_SUFFIX,
    SRT_EXTENSION,
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
        self._default_source_dir = Path(
            default_source_dir
        ).expanduser() if default_source_dir is not None else Path(
            "/Volumes/Data/Download/Subtitles"
        ).expanduser()
        self._mirror_warning_logged = False

    @property
    def default_source_dir(self) -> Path:
        """Return the configured subtitle source directory used for mirroring."""

        return self._default_source_dir

    def _probe_directory(self, path: Path, *, require_write: bool) -> Optional[Path]:
        candidate = path.expanduser()
        try:
            resolved = candidate.resolve(strict=False)
        except OSError:
            logger.debug(
                "Unable to resolve subtitle directory %s",
                candidate,
                exc_info=True,
            )
            return None
        if not resolved.exists() or not resolved.is_dir():
            return None
        if not os.access(resolved, os.R_OK):
            return None
        if require_write and not os.access(resolved, os.W_OK):
            return None
        return resolved

    def _copy_html_companion(self, source_subtitle: Path, destination_dir: Path) -> None:
        """Best-effort copy of the generated HTML transcript to ``destination_dir``."""

        html_source = source_subtitle.parent / "html" / f"{source_subtitle.stem}.html"
        if not html_source.exists():
            return
        try:
            html_target_dir = destination_dir / "html"
            html_target_dir.mkdir(parents=True, exist_ok=True)
            html_target = html_target_dir / html_source.name
            if html_target == html_source:
                return
            shutil.copy2(html_source, html_target)
        except Exception:  # pragma: no cover - best effort mirror
            logger.warning(
                "Unable to mirror HTML transcript %s to %s",
                html_source,
                destination_dir,
                exc_info=True,
            )

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
            extension = ASS_EXTENSION if options.output_format == "ass" else SRT_EXTENSION
            output_name = f"{source_stem}.{target_fragment}.{DEFAULT_OUTPUT_SUFFIX}{extension}"
            output_path = subtitles_root / output_name
            try:
                output_path.unlink(missing_ok=True)
            except Exception:  # pragma: no cover - defensive cleanup
                logger.debug("Unable to remove existing subtitle output %s", output_path, exc_info=True)
            mirror_dir: Optional[Path] = None
            mirror_path: Optional[Path] = None
            if options.mirror_batches_to_source_dir:
                mirror_dir = self._probe_directory(
                    self._default_source_dir,
                    require_write=True,
                )
                if mirror_dir is None:
                    if not self._mirror_warning_logged:
                        logger.info(
                            "Subtitle mirror directory %s is unavailable; continuing without live mirroring.",
                            self._default_source_dir,
                        )
                        self._mirror_warning_logged = True
                else:
                    self._mirror_warning_logged = False
                    candidate = mirror_dir / output_name
                    if candidate != output_path:
                        mirror_path = candidate

            try:
                result = process_subtitle_file(
                    input_path,
                    output_path,
                    options,
                    mirror_output_path=mirror_path,
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
            export_path: Optional[Path] = None
            if mirror_path is not None:
                try:
                    if mirror_path.exists():
                        export_path = mirror_path
                except OSError:
                    logger.info(
                        "Unable to access mirrored subtitle output at %s; will attempt copy fallback.",
                        mirror_path,
                    )
            elif mirror_dir is not None:
                try:
                    export_candidate = mirror_dir / output_name
                    if export_candidate != output_path:
                        shutil.copy2(output_path, export_candidate)
                    self._copy_html_companion(output_path, mirror_dir)
                    export_path = export_candidate
                except Exception:  # pragma: no cover - best effort mirror
                    logger.warning(
                        "Unable to mirror subtitle output %s to %s",
                        output_path,
                        mirror_dir,
                        exc_info=True,
                    )
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
            if export_path is not None:
                subtitle_section = result_payload.get("subtitle")
                if isinstance(subtitle_section, dict):
                    metadata = subtitle_section.get("metadata")
                    if isinstance(metadata, dict):
                        metadata["export_path"] = export_path.as_posix()
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

        base_candidate = directory or self._default_source_dir
        resolved = self._probe_directory(base_candidate, require_write=False)
        if resolved is None:
            if directory is not None:
                raise FileNotFoundError(f"Subtitle directory '{base_candidate}' is not accessible")
            return []
        entries: List[Path] = []
        for candidate in resolved.iterdir():
            if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
                entries.append(candidate.resolve())
        entries.sort()
        return entries

    def default_source_directory(self) -> Path:
        """Return the configured directory for local subtitle discovery."""

        return self._default_source_dir
