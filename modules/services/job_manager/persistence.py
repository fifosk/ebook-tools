"""Helpers for serializing pipeline job state to persistent metadata."""

from __future__ import annotations

import copy
import glob
import json
import os
import shutil
import tempfile
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

_LOGGER = logging_manager.get_logger().getChild("job_manager.persistence")


def _iterate_sentence_entries(payload: Any) -> list[Mapping[str, Any]]:
    """Return flattened sentence entries from a chunk payload."""

    entries: list[Mapping[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            entries.extend(_iterate_sentence_entries(item))
    elif isinstance(payload, Mapping):
        sentences = payload.get("sentences")
        if isinstance(sentences, list):
            for sentence in sentences:
                entries.extend(_iterate_sentence_entries(sentence))
        else:
            entries.append(payload)  # Treat mapping as a sentence-level entry
        chunks = payload.get("chunks")
        if isinstance(chunks, list):
            for chunk in chunks:
                entries.extend(_iterate_sentence_entries(chunk))
    return entries


def _normalize_audio_track_entry(value: Any) -> Optional[Dict[str, Any]]:
    """Return a normalized audio track entry with stable fields."""

    if isinstance(value, Mapping):
        entry: Dict[str, Any] = {}
        path = value.get("path")
        url = value.get("url")
        duration = value.get("duration")
        sample_rate = value.get("sampleRate") or value.get("sample_rate")
        if isinstance(path, str) and path.strip():
            entry["path"] = path.strip()
        if isinstance(url, str) and url.strip():
            entry["url"] = url.strip()
        try:
            entry["duration"] = round(float(duration), 6)
        except (TypeError, ValueError):
            pass
        try:
            entry["sampleRate"] = int(sample_rate)
        except (TypeError, ValueError):
            pass
        return entry or None
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed:
            return {"path": trimmed}
    return None


def _normalize_track_token(
    token_entry: Mapping[str, Any],
    *,
    track: str,
    fallback_sentence: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return a normalized token record for aggregated timing indexes."""

    try:
        start_val = float(
            token_entry.get("start")
            or token_entry.get("t0")
            or token_entry.get("begin")
            or 0.0
        )
        end_val = float(
            token_entry.get("end")
            or token_entry.get("t1")
            or token_entry.get("stop")
            or start_val
        )
    except (TypeError, ValueError):
        return None
    if end_val < start_val:
        end_val = start_val
    lane = token_entry.get("lane")
    if not isinstance(lane, str) or not lane.strip():
        lane = "trans" if track == "translation" else "mix"
    sentence_ref = token_entry.get("sentenceIdx") or token_entry.get("sentence_id") or fallback_sentence
    if sentence_ref is not None:
        sentence_ref = str(sentence_ref)
    record: Dict[str, Any] = {
        "start": round(start_val, 6),
        "end": round(end_val, 6),
        "lane": lane,
    }
    if sentence_ref:
        record["sentenceIdx"] = sentence_ref
    word_idx = token_entry.get("wordIdx")
    if isinstance(word_idx, (int, float)):
        record["wordIdx"] = int(word_idx)
    text_value = token_entry.get("text") or token_entry.get("token")
    if isinstance(text_value, str) and text_value:
        record["text"] = text_value
    policy_value = token_entry.get("policy")
    if isinstance(policy_value, str) and policy_value:
        record["policy"] = policy_value
    source_value = token_entry.get("source")
    if isinstance(source_value, str) and source_value:
        record["source"] = source_value
    fallback_flag = token_entry.get("fallback")
    if isinstance(fallback_flag, bool):
        record["fallback"] = fallback_flag
    return record


def build_timing_index(job_dir: str | os.PathLike[str]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Scan ``storage/<job_id>/metadata/chunk_*.json`` and aggregate word timings.
    """

    job_path = Path(job_dir)
    metadata_dir = job_path / "metadata"
    if not metadata_dir.exists():
        return {"mix": [], "translation": []}

    aggregated: Dict[str, List[Dict[str, Any]]] = {"mix": [], "translation": []}
    pattern = metadata_dir / "chunk_*.json"
    for chunk_path in sorted(glob.glob(os.fspath(pattern))):
        try:
            with open(chunk_path, "r", encoding="utf-8") as handle:
                chunk_payload = json.load(handle)
        except (OSError, json.JSONDecodeError):  # pragma: no cover - defensive guard
            continue

        chunk_tracks = chunk_payload.get("timingTracks")
        if isinstance(chunk_tracks, Mapping):
            for track_name in ("mix", "translation"):
                track_entries = chunk_tracks.get(track_name)
                if not isinstance(track_entries, list):
                    continue
                for token_entry in track_entries:
                    if not isinstance(token_entry, Mapping):
                        continue
                    normalized = _normalize_track_token(token_entry, track=track_name)
                    if normalized:
                        aggregated.setdefault(track_name, []).append(normalized)
            continue

        # Fallback for legacy payloads with per-sentence tracks.
        for entry in _iterate_sentence_entries(chunk_payload):
            if not isinstance(entry, Mapping):
                continue
            timing_tracks = entry.get("timingTracks")
            if not isinstance(timing_tracks, Mapping):
                continue
            translation_track = timing_tracks.get("translation")
            if not isinstance(translation_track, list):
                continue
            sentence_id = entry.get("sentence_id") or entry.get("id") or entry.get("sentence_number")
            sentence_id_str = str(sentence_id) if sentence_id is not None else None
            for token_entry in translation_track:
                if not isinstance(token_entry, Mapping):
                    continue
                normalized = _normalize_track_token(
                    token_entry,
                    track="translation",
                    fallback_sentence=sentence_id_str,
                )
                if normalized:
                    aggregated.setdefault("translation", []).append(normalized)

    aggregated.setdefault("mix", [])
    aggregated.setdefault("translation", [])
    return aggregated


def _extract_highlighting_policy(entry: Mapping[str, Any]) -> Optional[str]:
    """Return the highlighting policy encoded on a sentence entry."""

    summary = entry.get("highlighting_summary")
    if isinstance(summary, Mapping):
        policy = summary.get("policy")
        if isinstance(policy, str) and policy.strip():
            return policy.strip()
    policy = entry.get("highlighting_policy") or entry.get("alignment_policy")
    if isinstance(policy, str) and policy.strip():
        return policy.strip()
    return None


def resolve_highlighting_policy(job_dir: str | os.PathLike[str]) -> Optional[str]:
    """Inspect chunk metadata files to determine the active highlighting policy."""

    job_path = Path(job_dir)
    metadata_dir = job_path / "metadata"
    if not metadata_dir.exists():
        return None

    pattern = metadata_dir / "chunk_*.json"
    for chunk_path in sorted(glob.glob(os.fspath(pattern))):
        try:
            with open(chunk_path, "r", encoding="utf-8") as handle:
                chunk_payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        for entry in _iterate_sentence_entries(chunk_payload):
            if isinstance(entry, Mapping):
                policy = _extract_highlighting_policy(entry)
                if policy:
                    return policy
    return None


def ensure_timing_manifest(
    manifest: Mapping[str, Any] | None,
    job_dir: str | os.PathLike[str],
) -> Dict[str, Any]:
    """
    Attach aggregated timing index and playback metadata to ``manifest``.
    """

    manifest_payload = dict(manifest or {})
    job_path = Path(job_dir)
    index = build_timing_index(job_path)
    has_tracks = any(index.get(name) for name in ("mix", "translation"))
    if has_tracks:
        metadata_dir = job_path / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        timing_path = metadata_dir / "timing_index.json"
        try:
            with timing_path.open("w", encoding="utf-8") as handle:
                json.dump(index, handle, ensure_ascii=False, indent=2)
        except OSError:  # pragma: no cover - defensive guard
            _LOGGER.debug("Unable to persist timing index at %s", timing_path, exc_info=True)
        else:
            tracks = manifest_payload.setdefault("timing_tracks", {})
            tracks["translation"] = "metadata/timing_index.json"
            tracks["mix"] = "metadata/timing_index.json"
    policy = resolve_highlighting_policy(job_path)
    if policy:
        manifest_payload["highlighting_policy"] = policy
    return manifest_payload


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
        chunk_manifest = self._persist_metadata_files(job, snapshot)
        manifest_source = chunk_manifest if chunk_manifest is not None else snapshot.chunk_manifest
        if manifest_source is not None:
            snapshot.chunk_manifest = copy.deepcopy(manifest_source)
            job.chunk_manifest = copy.deepcopy(manifest_source)
        else:
            snapshot.chunk_manifest = None
            job.chunk_manifest = None
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
        job.chunk_manifest = (
            copy.deepcopy(metadata.chunk_manifest)
            if metadata.chunk_manifest is not None
            else None
        )
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

        chunk_manifest = None
        generated_payload = snapshot.generated_files
        if isinstance(generated_payload, Mapping):
            updated_generated, chunk_manifest = self._write_chunk_metadata(
                job.job_id,
                metadata_root,
                generated_payload,
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
                job.chunk_manifest = None

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

    def _write_chunk_metadata(
        self,
        job_id: str,
        metadata_root: Path,
        generated: Mapping[str, Any],
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        chunks_raw = generated.get("chunks")
        payload = dict(generated)
        if not isinstance(chunks_raw, list):
            payload["chunks"] = []
            self._cleanup_unused_chunk_files(metadata_root, set())
            return payload, None

        updated_chunks: list[Dict[str, Any]] = []
        manifest_entries: list[Dict[str, Any]] = []
        preserved_files: set[str] = set()

        for index, chunk in enumerate(chunks_raw):
            if not isinstance(chunk, Mapping):
                continue
            chunk_entry = {
                key: copy.deepcopy(value)
                for key, value in chunk.items()
                if key != "sentences"
            }
            sentences_raw = chunk.get("sentences")
            sentences: list[Any]
            if isinstance(sentences_raw, list):
                sentences = copy.deepcopy(sentences_raw)
            else:
                sentences = []

            metadata_path_str = chunk_entry.get("metadata_path")
            metadata_url_str = chunk_entry.get("metadata_url")

            sentence_count = chunk_entry.get("sentence_count")
            if not isinstance(sentence_count, int):
                sentence_count = len(sentences)

            wrote_chunk_file = False
            if sentences:
                filename = self._format_chunk_filename(index)
                destination = metadata_root / filename
                chunk_payload = {
                    "version": 1,
                    "chunk_id": chunk_entry.get("chunk_id"),
                    "range_fragment": chunk_entry.get("range_fragment"),
                    "start_sentence": chunk_entry.get("start_sentence"),
                    "end_sentence": chunk_entry.get("end_sentence"),
                    "sentence_count": len(sentences),
                    "sentences": sentences,
                }
                audio_tracks_raw = chunk_entry.get("audio_tracks") or chunk_entry.get("audioTracks")
                if isinstance(audio_tracks_raw, Mapping):
                    normalized_tracks: Dict[str, Dict[str, Any]] = {}
                    for track_key, track_value in audio_tracks_raw.items():
                        if not isinstance(track_key, str):
                            continue
                        normalized_entry = _normalize_audio_track_entry(track_value)
                        if normalized_entry:
                            normalized_tracks[track_key] = normalized_entry
                    if normalized_tracks:
                        chunk_payload["audioTracks"] = normalized_tracks
                        chunk_entry["audio_tracks"] = normalized_tracks
                        chunk_entry["audioTracks"] = normalized_tracks
                timing_tracks_raw = chunk_entry.get("timing_tracks") or chunk_entry.get("timingTracks")
                if isinstance(timing_tracks_raw, Mapping):
                    normalized_timing = copy.deepcopy(dict(timing_tracks_raw))
                    chunk_payload["timingTracks"] = normalized_timing
                    chunk_entry["timing_tracks"] = normalized_timing
                try:
                    self._write_chunk_file(destination, chunk_payload)
                except Exception:  # pragma: no cover - defensive logging
                    _LOGGER.debug(
                        "Unable to persist chunk metadata for job %s", job_id, exc_info=True
                    )
                    chunk_entry["sentences"] = sentences
                else:
                    metadata_rel = Path("metadata") / filename
                    metadata_path_str = metadata_rel.as_posix()
                    chunk_entry["metadata_path"] = metadata_path_str
                    url_candidate = self._file_locator.resolve_url(job_id, metadata_path_str)
                    if url_candidate:
                        chunk_entry["metadata_url"] = url_candidate
                        metadata_url_str = url_candidate
                    sentence_count = len(sentences)
                    preserved_files.add(destination.name)
                    wrote_chunk_file = True
            elif isinstance(metadata_path_str, str):
                preserved_files.add(Path(metadata_path_str).name)
                if not metadata_url_str:
                    url_candidate = self._file_locator.resolve_url(job_id, metadata_path_str)
                    if url_candidate:
                        chunk_entry["metadata_url"] = url_candidate
                        metadata_url_str = url_candidate

            chunk_entry["sentence_count"] = sentence_count

            manifest_entries.append(
                {
                    "index": index,
                    "chunk_id": chunk_entry.get("chunk_id"),
                    "path": metadata_path_str if isinstance(metadata_path_str, str) else None,
                    "url": metadata_url_str if isinstance(metadata_url_str, str) else None,
                    "sentence_count": chunk_entry.get("sentence_count"),
                }
            )
            updated_chunks.append(chunk_entry)

        self._cleanup_unused_chunk_files(metadata_root, preserved_files)

        payload["chunks"] = updated_chunks
        chunk_manifest: Optional[Dict[str, Any]]
        if updated_chunks:
            chunk_manifest = {
                "chunk_count": len(updated_chunks),
                "chunks": manifest_entries,
            }
        else:
            chunk_manifest = None
        return payload, chunk_manifest

    def _write_chunk_file(self, destination: Path, payload: Mapping[str, Any]) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
        tmp_handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=destination.parent, delete=False
        )
        try:
            with tmp_handle as handle:
                handle.write(serialized)
                handle.flush()
            Path(tmp_handle.name).replace(destination)
        except Exception:
            Path(tmp_handle.name).unlink(missing_ok=True)
            raise

    def _cleanup_unused_chunk_files(self, metadata_root: Path, preserved: set[str]) -> None:
        for existing in metadata_root.glob("chunk_*.json"):
            if existing.name in preserved:
                continue
            try:
                existing.unlink()
            except FileNotFoundError:
                continue
            except OSError:  # pragma: no cover - defensive logging
                _LOGGER.debug(
                    "Unable to remove stale chunk metadata file %s", existing, exc_info=True
                )

    @staticmethod
    def _format_chunk_filename(index: int) -> str:
        return f"chunk_{index:04d}.json"

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
            metadata_path = chunk.get("metadata_path")
            if isinstance(metadata_path, str) and metadata_path.strip():
                chunk_entry["metadata_path"] = metadata_path
            metadata_url = chunk.get("metadata_url")
            if isinstance(metadata_url, str) and metadata_url.strip():
                chunk_entry["metadata_url"] = metadata_url
            sentence_count = chunk.get("sentence_count")
            if isinstance(sentence_count, int):
                chunk_entry["sentence_count"] = sentence_count
            sentences_raw = chunk.get("sentences")
            if isinstance(sentences_raw, list):
                chunk_entry["sentences"] = copy.deepcopy(sentences_raw)
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
            if isinstance(audio_tracks_raw, Mapping):
                normalized_tracks: Dict[str, Dict[str, Any]] = {}
                for track_key, track_value in audio_tracks_raw.items():
                    if not isinstance(track_key, str):
                        continue
                    normalized_entry = _normalize_audio_track_entry(track_value)
                    if normalized_entry:
                        normalized_tracks[track_key] = normalized_entry
                if normalized_tracks:
                    chunk_entry["audio_tracks"] = normalized_tracks
                    chunk_entry["audioTracks"] = normalized_tracks
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
