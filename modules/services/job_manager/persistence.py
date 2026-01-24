"""Helpers for serializing pipeline job state to persistent metadata."""

from __future__ import annotations

import copy
import json
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Mapping, Optional, Tuple

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

# Import from modular components
from .language_metadata import apply_language_metadata
from .highlighting_policy import ensure_timing_manifest, resolve_highlighting_policy
from .cover_asset import mirror_cover_asset, cleanup_cover_assets
from .chunk_persistence import (
    normalize_audio_track_entry,
    coerce_chunk_id,
    write_chunk_metadata,
)

_LOGGER = logging_manager.get_logger().getChild("job_manager.persistence")


class PipelineJobPersistence:
    """Serialize and deserialize :class:`PipelineJob` instances."""

    def __init__(self, file_locator: FileLocator) -> None:
        self._file_locator = file_locator

    def snapshot(self, job: PipelineJob) -> PipelineJobMetadata:
        """Return a metadata snapshot for ``job``.

        Performance note: This method is called on every progress event update.
        We avoid unnecessary copy.deepcopy() calls by:
        1. Using serialization functions that already return fresh dicts
        2. Using shallow copies where deep isolation isn't needed
        3. Only deep-copying mutable structures that could be modified externally
        """

        # serialize_progress_event returns a fresh dict - no copy needed
        last_event = (
            serialize_progress_event(job.last_event)
            if job.last_event is not None
            else None
        )

        # serialize_pipeline_response returns a fresh dict - no copy needed
        # For result_payload, we only need a shallow copy since it's not modified
        if job.result_payload is not None:
            result_payload = job.result_payload  # Already a dict, copied in to_dict()
        elif job.result is not None:
            result_payload = serialize_pipeline_response(job.result)
        else:
            result_payload = None

        # serialize_pipeline_request returns a fresh dict - no copy needed
        if job.request is not None:
            request_payload = serialize_pipeline_request(job.request)
        else:
            request_payload = job.request_payload  # Will be copied in to_dict()

        # resume_context: use existing or fall back to request_payload
        # Shallow reference is fine - _stable_copy handles isolation in to_dict()
        resume_context = job.resume_context if job.resume_context is not None else request_payload

        # _normalize_generated_files already creates new dicts internally
        normalized_files = self._normalize_generated_files(job.job_id, job.generated_files)
        job.generated_files = normalized_files
        if isinstance(normalized_files, Mapping):
            complete_flag = normalized_files.get("complete")
            if isinstance(complete_flag, bool):
                job.media_completed = complete_flag

        # Retry summary: shallow dict of dicts with int values - safe to share
        retry_summary = job.retry_summary or (job.tracker.get_retry_counts() if job.tracker else None)
        if retry_summary:
            job.retry_summary = retry_summary

        # Build metadata snapshot - references are safe because:
        # 1. PipelineJobMetadata.to_dict() uses _stable_copy() for serialization
        # 2. These dicts are not mutated after creation
        snapshot = PipelineJobMetadata(
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            last_event=last_event,
            result=result_payload,
            request_payload=request_payload,
            resume_context=resume_context,
            tuning_summary=job.tuning_summary,
            retry_summary=retry_summary,
            user_id=job.user_id,
            user_role=job.user_role,
            access=job.access,
            generated_files=normalized_files,
            media_completed=job.media_completed,
        )
        chunk_manifest = self._persist_metadata_files(job, snapshot)
        manifest_source = chunk_manifest if chunk_manifest is not None else snapshot.chunk_manifest
        if manifest_source is not None:
            snapshot.chunk_manifest = manifest_source
            job.chunk_manifest = manifest_source
        else:
            snapshot.chunk_manifest = None
            job.chunk_manifest = None
        return snapshot

    def build_job(self, metadata: PipelineJobMetadata) -> PipelineJob:
        """Return a :class:`PipelineJob` hydrated from ``metadata``.

        Performance note: This creates a new PipelineJob that owns its data.
        Since the job will be the sole owner of these references after creation,
        we avoid deepcopy and use the references directly. The metadata object
        is typically discarded after this call.
        """

        # Use references directly - the job becomes the owner of this data
        request_payload = metadata.request_payload
        resume_context = metadata.resume_context if metadata.resume_context is not None else request_payload
        result_payload = metadata.result

        # _normalize_generated_files already creates new dicts
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
            tuning_summary=metadata.tuning_summary,
            retry_summary=metadata.retry_summary,
            user_id=metadata.user_id,
            user_role=metadata.user_role,
            access=metadata.access,
            generated_files=normalized_files,
        )
        job.chunk_manifest = metadata.chunk_manifest
        job.media_completed = bool(metadata.media_completed)
        if isinstance(normalized_files, Mapping):
            complete_flag = normalized_files.get("complete")
            if isinstance(complete_flag, bool):
                job.media_completed = complete_flag

        if metadata.last_event is not None:
            job.last_event = deserialize_progress_event(metadata.last_event)

        return job

    def _persist_metadata_files(
        self,
        job: PipelineJob,
        snapshot: PipelineJobMetadata,
    ) -> Optional[Dict[str, Any]]:
        try:
            metadata_root = self._file_locator.metadata_root(job.job_id)
            metadata_root.mkdir(parents=True, exist_ok=True)
            job_root = self._file_locator.job_root(job.job_id)
        except Exception:  # pragma: no cover - defensive logging
            _LOGGER.debug("Unable to prepare metadata directory", exc_info=True)
            return None

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
        apply_language_metadata(
            book_metadata,
            snapshot.request_payload if isinstance(snapshot.request_payload, Mapping) else None,
            snapshot.resume_context if isinstance(snapshot.resume_context, Mapping) else None,
            result_payload,
        )

        cover_asset = mirror_cover_asset(job.job_id, metadata_root, book_metadata, self._file_locator)
        if cover_asset:
            book_metadata["job_cover_asset"] = cover_asset
            book_metadata.setdefault("job_cover_asset_url", f"/api/pipelines/{job.job_id}/cover")
        else:
            book_metadata.pop("job_cover_asset", None)
            book_metadata.pop("job_cover_asset_url", None)
        raw_content_index = book_metadata.get("content_index")
        content_index_written = False
        content_index_total_sentences: Optional[int] = None
        if isinstance(raw_content_index, Mapping):
            try:
                content_index_payload = copy.deepcopy(dict(raw_content_index))
                content_index_path = metadata_root / "content_index.json"
                content_index_path.write_text(
                    json.dumps(content_index_payload, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
                content_index_written = True
                relative_path = Path("metadata") / "content_index.json"
                book_metadata["content_index_path"] = relative_path.as_posix()
                url_candidate = self._file_locator.resolve_url(
                    job.job_id, relative_path.as_posix()
                )
                if url_candidate:
                    book_metadata["content_index_url"] = url_candidate
                chapter_list = content_index_payload.get("chapters")
                chapter_count = (
                    len(chapter_list) if isinstance(chapter_list, list) else 0
                )
                alignment = None
                alignment_payload = content_index_payload.get("alignment")
                if isinstance(alignment_payload, Mapping):
                    alignment = alignment_payload.get("status")
                book_metadata["content_index_summary"] = {
                    "chapter_count": chapter_count,
                    "alignment": alignment,
                }
                total_candidate = content_index_payload.get("total_sentences")
                try:
                    total_value = int(total_candidate)
                except (TypeError, ValueError):
                    total_value = None
                if total_value and total_value > 0:
                    content_index_total_sentences = total_value
            except Exception:  # pragma: no cover - defensive logging
                _LOGGER.debug(
                    "Unable to persist content index for job %s",
                    job.job_id,
                    exc_info=True,
                )
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
        wrote_sentences = False
        if isinstance(sentences, list) and sentences:
            if not content_index_written:
                try:
                    (metadata_root / "sentences.json").write_text(
                        json.dumps(sentences, indent=2),
                        encoding="utf-8",
                    )
                    wrote_sentences = True
                except Exception:  # pragma: no cover - defensive logging
                    _LOGGER.debug("Unable to persist refined sentences", exc_info=True)
            else:
                wrote_sentences = True
            if content_index_total_sentences is None:
                content_index_total_sentences = len(sentences)

        if content_index_total_sentences and content_index_total_sentences > 0:
            book_metadata.setdefault("total_sentences", content_index_total_sentences)
            book_metadata.setdefault("book_sentence_count", content_index_total_sentences)

        if wrote_sentences:
            result_payload.pop("refined_sentences", None)
            if isinstance(job.result_payload, Mapping):
                job.result_payload = dict(job.result_payload)
                job.result_payload.pop("refined_sentences", None)

        prompt_plan_summary: Optional[Dict[str, Any]] = None
        prompt_plan_summary_path = metadata_root / "image_prompt_plan_summary.json"
        if prompt_plan_summary_path.exists():
            try:
                raw_summary = json.loads(prompt_plan_summary_path.read_text(encoding="utf-8"))
                if isinstance(raw_summary, Mapping):
                    prompt_plan_summary = copy.deepcopy(dict(raw_summary))
            except Exception:  # pragma: no cover - defensive logging
                _LOGGER.debug(
                    "Unable to load image prompt plan summary for job %s",
                    job.job_id,
                    exc_info=True,
                )

        chunk_manifest = None
        generated_payload = snapshot.generated_files
        if isinstance(generated_payload, Mapping) or prompt_plan_summary is not None:
            if isinstance(generated_payload, Mapping):
                generated_payload = dict(generated_payload)
            else:
                generated_payload = {"chunks": [], "files": []}
            if prompt_plan_summary is not None:
                generated_payload["image_prompt_plan_summary"] = prompt_plan_summary
            updated_generated, chunk_manifest = write_chunk_metadata(
                job.job_id,
                metadata_root,
                generated_payload,
                self._file_locator,
            )
            snapshot.generated_files = copy.deepcopy(updated_generated)
            if isinstance(result_payload, Mapping):
                result_payload["generated_files"] = copy.deepcopy(updated_generated)
            if job.result_payload is not None:
                job.result_payload["generated_files"] = copy.deepcopy(updated_generated)
            if job.result is not None:
                job.result.generated_files = copy.deepcopy(updated_generated)
            job.generated_files = copy.deepcopy(updated_generated)

        if chunk_manifest is not None:
            if isinstance(result_payload, Mapping):
                result_payload["chunk_manifest"] = copy.deepcopy(chunk_manifest)
            if job.result_payload is not None:
                job.result_payload["chunk_manifest"] = copy.deepcopy(chunk_manifest)
            if job.result is not None:
                job.result.chunk_manifest = copy.deepcopy(chunk_manifest)
            job.chunk_manifest = copy.deepcopy(chunk_manifest)
            snapshot.chunk_manifest = copy.deepcopy(chunk_manifest)

        manifest_payload = ensure_timing_manifest(snapshot.result, job_root)
        snapshot.result = manifest_payload
        timing_tracks = manifest_payload.get("timing_tracks")
        snapshot.timing_tracks = copy.deepcopy(timing_tracks) if timing_tracks else None

        if job.result_payload is not None:
            job.result_payload = ensure_timing_manifest(job.result_payload, job_root)
        if job.result is not None and timing_tracks:
            try:
                job.result.metadata.update({"timing_tracks": copy.deepcopy(timing_tracks)})
            except Exception:  # pragma: no cover - defensive logging
                _LOGGER.debug("Unable to attach timing tracks to job result", exc_info=True)

        return chunk_manifest

    def _merge_generated_files(
        self,
        existing: Optional[Any],
        update: Mapping[str, Any],
    ) -> Dict[str, Any]:
        if not isinstance(existing, Mapping):
            return copy.deepcopy(dict(update))

        existing_chunks = existing.get("chunks")
        update_chunks = update.get("chunks")

        merged_chunks: list[Dict[str, Any]] = []
        index_by_chunk_id: Dict[str, int] = {}

        if isinstance(existing_chunks, list):
            for entry in existing_chunks:
                if not isinstance(entry, Mapping):
                    continue
                chunk_copy = copy.deepcopy(dict(entry))
                chunk_id = coerce_chunk_id(chunk_copy)
                if chunk_id:
                    index_by_chunk_id[chunk_id] = len(merged_chunks)
                merged_chunks.append(chunk_copy)

        if isinstance(update_chunks, list):
            for entry in update_chunks:
                if not isinstance(entry, Mapping):
                    continue
                chunk_copy = copy.deepcopy(dict(entry))
                chunk_id = coerce_chunk_id(chunk_copy)
                if not chunk_id:
                    continue
                existing_index = index_by_chunk_id.get(chunk_id)
                if existing_index is None:
                    index_by_chunk_id[chunk_id] = len(merged_chunks)
                    merged_chunks.append(chunk_copy)
                else:
                    merged_chunks[existing_index] = chunk_copy

        merged: Dict[str, Any] = {"chunks": merged_chunks}

        complete_flag = update.get("complete")
        if isinstance(complete_flag, bool):
            merged["complete"] = complete_flag
        else:
            existing_complete = existing.get("complete")
            if isinstance(existing_complete, bool):
                merged["complete"] = existing_complete

        for key, value in existing.items():
            if key in {"chunks", "files", "complete"}:
                continue
            merged[key] = copy.deepcopy(value)
        for key, value in update.items():
            if key in {"chunks", "files", "complete"}:
                continue
            merged[key] = copy.deepcopy(value)

        return merged

    def apply_event(self, job: PipelineJob, event: ProgressEvent) -> PipelineJobMetadata:
        """Update ``job`` using ``event`` and return the persisted metadata."""

        job.last_event = event
        metadata = event.metadata
        if isinstance(metadata, Mapping):
            generated = metadata.get("generated_files")
            if generated is not None:
                if isinstance(generated, Mapping):
                    job.generated_files = self._merge_generated_files(job.generated_files, generated)
                    complete_flag = job.generated_files.get("complete")
                    if isinstance(complete_flag, bool):
                        job.media_completed = complete_flag
                else:
                    job.generated_files = copy.deepcopy(generated)
                job.chunk_manifest = None

        return self.snapshot(job)

    def _normalize_generated_files(
        self, job_id: str, raw: Optional[Any]
    ) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        if not isinstance(raw, Mapping):
            # Non-mapping values are rare edge cases; return as-is
            return raw  # type: ignore[return-value]

        chunks_raw = raw.get("chunks", [])
        if not isinstance(chunks_raw, list):
            return None

        job_root = self._file_locator.resolve_path(job_id)
        normalized_chunks: list[Dict[str, Any]] = []
        for chunk in chunks_raw:
            if not isinstance(chunk, Mapping):
                continue
            has_metadata_file = False
            metadata_path = chunk.get("metadata_path")
            if isinstance(metadata_path, str) and metadata_path.strip():
                has_metadata_file = True

            chunk_entry: Dict[str, Any] = {
                "chunk_id": chunk.get("chunk_id"),
                "range_fragment": chunk.get("range_fragment"),
                "start_sentence": chunk.get("start_sentence"),
                "end_sentence": chunk.get("end_sentence"),
                "files": [],
            }
            if has_metadata_file:
                chunk_entry["metadata_path"] = metadata_path.strip()
            metadata_url = chunk.get("metadata_url")
            if isinstance(metadata_url, str) and metadata_url.strip():
                chunk_entry["metadata_url"] = metadata_url
            sentence_count = chunk.get("sentence_count")
            if isinstance(sentence_count, int):
                chunk_entry["sentence_count"] = sentence_count
            sentences_raw = chunk.get("sentences")
            if isinstance(sentences_raw, list) and not has_metadata_file:
                # Sentences are read-only after normalization; shallow copy suffices
                chunk_entry["sentences"] = list(sentences_raw)
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
            audio_tracks_raw = chunk.get("audio_tracks") or chunk.get("audioTracks")
            if isinstance(audio_tracks_raw, Mapping) and not has_metadata_file:
                normalized_tracks: Dict[str, Dict[str, Any]] = {}
                for track_key, track_value in audio_tracks_raw.items():
                    if not isinstance(track_key, str):
                        continue
                    normalized_entry = normalize_audio_track_entry(track_value)
                    if normalized_entry:
                        normalized_tracks[track_key] = normalized_entry
                if normalized_tracks:
                    chunk_entry["audio_tracks"] = normalized_tracks
                    chunk_entry["audioTracks"] = normalized_tracks

            timing_tracks_raw = chunk.get("timing_tracks") or chunk.get("timingTracks")
            if isinstance(timing_tracks_raw, Mapping) and not has_metadata_file:
                normalized_timing = copy.deepcopy(dict(timing_tracks_raw))
                chunk_entry["timing_tracks"] = normalized_timing
                chunk_entry["timingTracks"] = normalized_timing
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

        extras: Dict[str, Any] = {}
        for key, value in raw.items():
            if key in {"chunks", "files", "complete"}:
                continue
            extras[key] = copy.deepcopy(value)

        if not normalized_chunks and not files_index and not extras:
            return None

        complete_flag = raw.get("complete")
        payload: Dict[str, Any] = {"chunks": normalized_chunks, "files": files_index}
        if isinstance(complete_flag, bool):
            payload["complete"] = complete_flag
        if extras:
            payload.update(extras)
        return payload


# Re-export for backward compatibility
__all__ = [
    "PipelineJobPersistence",
    "resolve_highlighting_policy",
    "ensure_timing_manifest",
]
