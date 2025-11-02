"""Helpers for serializing pipeline job state to persistent metadata."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Mapping, Optional

from ..file_locator import FileLocator
from ... import config_manager as cfg
from ... import logging_manager
from ..pipeline_service import (
    serialize_pipeline_request,
    serialize_pipeline_response,
)
from .job import PipelineJob
from .metadata import PipelineJobMetadata
from .progress import deserialize_progress_event, serialize_progress_event
from ...progress_tracker import ProgressEvent

_LOGGER = logging_manager.get_logger().getChild("job_manager.persistence")


class PipelineJobPersistence:
    """Serialize and deserialize :class:`PipelineJob` instances."""

    def __init__(self, file_locator: FileLocator) -> None:
        self._file_locator = file_locator

    def snapshot(self, job: PipelineJob) -> PipelineJobMetadata:
        """Return a metadata snapshot for ``job``."""

        last_event = (
            serialize_progress_event(job.last_event)
            if job.last_event is not None
            else None
        )
        result_payload = (
            copy.deepcopy(job.result_payload)
            if job.result_payload is not None
            else (
                serialize_pipeline_response(job.result)
                if job.result is not None
                else None
            )
        )
        if job.request is not None:
            request_payload = serialize_pipeline_request(job.request)
        else:
            request_payload = (
                copy.deepcopy(job.request_payload) if job.request_payload is not None else None
            )
        resume_context = (
            copy.deepcopy(job.resume_context)
            if job.resume_context is not None
            else (copy.deepcopy(request_payload) if request_payload is not None else None)
        )

        normalized_files = self._normalize_generated_files(job.job_id, job.generated_files)
        job.generated_files = copy.deepcopy(normalized_files) if normalized_files is not None else None
        if isinstance(normalized_files, Mapping):
            complete_flag = normalized_files.get("complete")
            if isinstance(complete_flag, bool):
                job.media_completed = complete_flag

        snapshot = PipelineJobMetadata(
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            last_event=copy.deepcopy(last_event) if last_event is not None else None,
            result=result_payload,
            request_payload=request_payload,
            resume_context=resume_context,
            tuning_summary=copy.deepcopy(job.tuning_summary)
            if job.tuning_summary is not None
            else None,
            user_id=job.user_id,
            user_role=job.user_role,
            generated_files=copy.deepcopy(normalized_files)
            if normalized_files is not None
            else None,
            media_completed=job.media_completed,
        )
        self._persist_metadata_files(job, snapshot)
        return snapshot

    def build_job(self, metadata: PipelineJobMetadata) -> PipelineJob:
        """Return a :class:`PipelineJob` hydrated from ``metadata``."""

        request_payload = (
            copy.deepcopy(metadata.request_payload)
            if metadata.request_payload is not None
            else None
        )
        resume_context = (
            copy.deepcopy(metadata.resume_context)
            if metadata.resume_context is not None
            else (copy.deepcopy(request_payload) if request_payload is not None else None)
        )
        result_payload = (
            copy.deepcopy(metadata.result) if metadata.result is not None else None
        )

        normalized_files = self._normalize_generated_files(
            metadata.job_id, metadata.generated_files
        )

        job = PipelineJob(
            job_id=metadata.job_id,
            job_type=metadata.job_type,
            status=metadata.status,
            created_at=metadata.created_at,
            started_at=metadata.started_at,
            completed_at=metadata.completed_at,
            error_message=metadata.error_message,
            result_payload=result_payload,
            request_payload=request_payload,
            resume_context=resume_context,
            tuning_summary=copy.deepcopy(metadata.tuning_summary)
            if metadata.tuning_summary is not None
            else None,
            user_id=metadata.user_id,
            user_role=metadata.user_role,
            generated_files=copy.deepcopy(normalized_files)
            if normalized_files is not None
            else None,
        )
        job.media_completed = bool(metadata.media_completed)
        if isinstance(normalized_files, Mapping):
            complete_flag = normalized_files.get("complete")
            if isinstance(complete_flag, bool):
                job.media_completed = complete_flag

        if metadata.last_event is not None:
            job.last_event = deserialize_progress_event(metadata.last_event)

        return job

    def _persist_metadata_files(self, job: PipelineJob, snapshot: PipelineJobMetadata) -> None:
        try:
            metadata_root = self._file_locator.metadata_root(job.job_id)
            metadata_root.mkdir(parents=True, exist_ok=True)
        except Exception:  # pragma: no cover - defensive logging
            _LOGGER.debug("Unable to prepare metadata directory", exc_info=True)
            return

        result_payload_raw = snapshot.result or {}
        if isinstance(result_payload_raw, Mapping):
            result_payload = dict(result_payload_raw)
        else:
            result_payload = {}

        raw_book_metadata = result_payload.get("book_metadata")
        book_metadata: Dict[str, Any]
        if isinstance(raw_book_metadata, Mapping):
            book_metadata = dict(raw_book_metadata)
        else:
            book_metadata = {}

        cover_asset = self._mirror_cover_asset(job.job_id, metadata_root, book_metadata)
        if cover_asset:
            book_metadata["job_cover_asset"] = cover_asset
        else:
            book_metadata.pop("job_cover_asset", None)
        result_payload["book_metadata"] = book_metadata
        snapshot.result = result_payload

        if job.result_payload is not None:
            job.result_payload = dict(job.result_payload)
            job.result_payload["book_metadata"] = copy.deepcopy(book_metadata)
        if job.result is not None:
            if cover_asset:
                job.result.metadata.update({"job_cover_asset": cover_asset})
            else:
                job.result.metadata.values.pop("job_cover_asset", None)

        try:
            (metadata_root / "book.json").write_text(
                json.dumps(dict(book_metadata), indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except Exception:  # pragma: no cover - defensive logging
            _LOGGER.debug("Unable to persist book metadata", exc_info=True)

        sentences = result_payload.get("refined_sentences")
        if isinstance(sentences, list) and sentences:
            try:
                (metadata_root / "sentences.json").write_text(
                    json.dumps(sentences, indent=2),
                    encoding="utf-8",
                )
            except Exception:  # pragma: no cover - defensive logging
                _LOGGER.debug("Unable to persist refined sentences", exc_info=True)

    def apply_event(self, job: PipelineJob, event: ProgressEvent) -> PipelineJobMetadata:
        """Update ``job`` using ``event`` and return the persisted metadata."""

        job.last_event = event
        metadata = event.metadata
        if isinstance(metadata, Mapping):
            generated = metadata.get("generated_files")
            if generated is not None:
                job.generated_files = copy.deepcopy(generated)
                if isinstance(generated, Mapping) and "complete" in generated:
                    job.media_completed = bool(generated.get("complete"))

        return self.snapshot(job)

    def _mirror_cover_asset(
        self,
        job_id: str,
        metadata_root: Path,
        book_metadata: Mapping[str, Any],
    ) -> Optional[str]:
        raw_value = book_metadata.get("book_cover_file")
        if not isinstance(raw_value, str) or not raw_value.strip():
            self._cleanup_cover_assets(metadata_root)
            return None

        source = self._resolve_cover_source(job_id, metadata_root, raw_value)
        if source is None:
            self._cleanup_cover_assets(metadata_root)
            return None

        try:
            return self._copy_cover_asset(metadata_root, source)
        except Exception:  # pragma: no cover - defensive logging
            _LOGGER.debug("Unable to mirror cover asset for job %s", job_id, exc_info=True)
            return None

    def _resolve_cover_source(
        self,
        job_id: str,
        metadata_root: Path,
        raw_value: str,
    ) -> Optional[Path]:
        candidate = Path(raw_value.strip())
        search_paths: list[Path] = []

        if candidate.is_absolute():
            search_paths.append(candidate)
        else:
            normalised = raw_value.strip().lstrip("/\\")
            relative_candidate = Path(normalised)
            relative_variants = [relative_candidate]

            parts = [part.lower() for part in relative_candidate.parts]
            if parts and parts[0] in {"storage", "metadata"} and len(parts) > 1:
                relative_variants.append(Path(*relative_candidate.parts[1:]))
            if parts and parts[0] == "covers" and len(parts) > 1:
                relative_variants.append(Path(*relative_candidate.parts[1:]))

            for relative in relative_variants:
                search_paths.append(metadata_root / relative)
                try:
                    search_paths.append(self._file_locator.resolve_path(job_id, relative))
                except ValueError:
                    pass
                search_paths.append(self._file_locator.storage_root / relative)

                covers_root = cfg.resolve_directory(None, cfg.DEFAULT_COVERS_RELATIVE)
                search_paths.append(covers_root / relative)

                resolved_script = cfg.resolve_file_path(relative)
                if resolved_script is not None:
                    search_paths.append(resolved_script)

        seen: set[Path] = set()
        for path in search_paths:
            try:
                resolved = path.resolve()
            except FileNotFoundError:
                continue
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            if resolved.is_file():
                return resolved
        return None

    def _copy_cover_asset(self, metadata_root: Path, source: Path) -> str:
        metadata_root.mkdir(parents=True, exist_ok=True)
        try:
            resolved_source = source.resolve()
        except OSError:
            resolved_source = source

        suffix = resolved_source.suffix.lower() or ".jpg"
        if not suffix.startswith("."):
            suffix = f".{suffix}"
        destination_name = f"cover{suffix}"
        destination_path = metadata_root / destination_name
        destination_abs = destination_path.parent.resolve() / destination_path.name

        if destination_abs != resolved_source:
            should_copy = True
            if destination_path.exists():
                try:
                    src_stat = resolved_source.stat()
                    dest_stat = destination_path.stat()
                    if (
                        src_stat.st_size == dest_stat.st_size
                        and int(src_stat.st_mtime) == int(dest_stat.st_mtime)
                    ):
                        should_copy = False
                except OSError:
                    pass
            if should_copy:
                shutil.copy2(resolved_source, destination_path)

        for existing in metadata_root.glob("cover.*"):
            if existing.name == destination_name:
                continue
            try:
                existing.unlink()
            except FileNotFoundError:
                continue
            except OSError:
                _LOGGER.debug("Unable to remove stale cover asset %s", existing, exc_info=True)

        relative_path = Path("metadata") / destination_name
        return relative_path.as_posix()

    def _cleanup_cover_assets(self, metadata_root: Path) -> None:
        for existing in metadata_root.glob("cover.*"):
            try:
                existing.unlink()
            except FileNotFoundError:
                continue
            except OSError:
                _LOGGER.debug("Unable to remove cover asset %s", existing, exc_info=True)

    def _normalize_generated_files(
        self, job_id: str, raw: Optional[Any]
    ) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        if not isinstance(raw, Mapping):
            return copy.deepcopy(raw)  # type: ignore[return-value]

        chunks_raw = raw.get("chunks", [])
        if not isinstance(chunks_raw, list):
            return None

        job_root = self._file_locator.resolve_path(job_id)
        normalized_chunks: list[Dict[str, Any]] = []
        for chunk in chunks_raw:
            if not isinstance(chunk, Mapping):
                continue
            chunk_entry: Dict[str, Any] = {
                "chunk_id": chunk.get("chunk_id"),
                "range_fragment": chunk.get("range_fragment"),
                "start_sentence": chunk.get("start_sentence"),
                "end_sentence": chunk.get("end_sentence"),
                "files": [],
            }
            files_raw = chunk.get("files", [])
            if not isinstance(files_raw, list):
                files_raw = []
            for file_entry in files_raw:
                if not isinstance(file_entry, Mapping):
                    continue
                normalized_entry: Dict[str, Any] = {}
                file_type = file_entry.get("type")
                if file_type is not None:
                    normalized_entry["type"] = file_type

                relative_path_value = file_entry.get("relative_path")
                relative_path: Optional[str] = None
                path_candidate: Optional[Path] = None

                if relative_path_value:
                    relative_candidate = PurePosixPath(
                        str(relative_path_value).replace("\\", "/")
                    )
                    if not relative_candidate.is_absolute() and ".." not in relative_candidate.parts:
                        relative_path = relative_candidate.as_posix()
                        path_candidate = job_root.joinpath(*relative_candidate.parts)

                path_value = file_entry.get("path")
                if path_candidate is None and path_value:
                    path_candidate = Path(str(path_value))
                    if not path_candidate.is_absolute():
                        path_candidate = job_root / path_candidate

                if path_candidate is not None:
                    normalized_entry["path"] = path_candidate.as_posix()
                    if relative_path is None:
                        try:
                            relative_candidate = path_candidate.relative_to(job_root)
                        except ValueError:
                            relative_candidate = None
                        else:
                            relative_path = relative_candidate.as_posix()

                url: Optional[str] = None
                if relative_path:
                    normalized_entry["relative_path"] = relative_path
                    try:
                        url = self._file_locator.resolve_url(job_id, relative_path)
                    except ValueError:
                        url = None
                if url:
                    normalized_entry["url"] = url
                chunk_entry.setdefault("files", []).append(normalized_entry)
            normalized_chunks.append(chunk_entry)

        files_index: list[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for chunk in normalized_chunks:
            chunk_id = chunk.get("chunk_id")
            range_fragment = chunk.get("range_fragment")
            start_sentence = chunk.get("start_sentence")
            end_sentence = chunk.get("end_sentence")
            for entry in chunk.get("files", []):
                path_value = entry.get("path")
                file_type = entry.get("type")
                if not path_value:
                    continue
                key = (str(path_value), str(file_type))
                if key in seen:
                    continue
                seen.add(key)
                record = dict(entry)
                record["chunk_id"] = chunk_id
                if range_fragment is not None and "range_fragment" not in record:
                    record["range_fragment"] = range_fragment
                if start_sentence is not None and "start_sentence" not in record:
                    record["start_sentence"] = start_sentence
                if end_sentence is not None and "end_sentence" not in record:
                    record["end_sentence"] = end_sentence
                files_index.append(record)

        if not normalized_chunks and not files_index:
            return None
        complete_flag = raw.get("complete")
        payload: Dict[str, Any] = {"chunks": normalized_chunks, "files": files_index}
        if isinstance(complete_flag, bool):
            payload["complete"] = complete_flag
        return payload


__all__ = ["PipelineJobPersistence"]
