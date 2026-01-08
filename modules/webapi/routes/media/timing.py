"""Timing metadata routes for job playback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from ....metadata_manager import MetadataLoader
from ....library import LibraryRepository
from ....services.file_locator import FileLocator
from ...dependencies import (
    RequestUserContext,
    get_file_locator,
    get_library_repository,
    get_pipeline_job_manager,
    get_request_user,
)
from ...jobs import PipelineJob
from .common import _resolve_job_path

jobs_timing_router = APIRouter(prefix="/api/jobs", tags=["jobs"])

def normalize_timings(
    tokens: Sequence[Mapping[str, Any]],
    start_offset: float = 0.0,
    *,
    lane: str = "tran",
    seg_prefix: str = "seg",
) -> list[dict[str, Any]]:
    """Normalise timing tokens into the frontend payload format."""

    norm: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        raw_start = float(token.get("start", 0.0))
        raw_end = float(token.get("end", raw_start))
        t0 = round(raw_start - start_offset, 3)
        t1 = round(raw_end - start_offset, 3)
        norm.append(
            {
                "id": f"{seg_prefix}_{index}",
                "text": token.get("text", ""),
                "t0": max(t0, 0.0),
                "t1": max(t1, 0.0),
                "lane": lane,
                "segId": seg_prefix,
            }
        )
    return norm


def smooth_token_edges(
    tokens: Sequence[Mapping[str, Any]], min_len: float = 0.04
) -> list[dict[str, Any]]:
    """Ensure every token spans at least ``min_len`` seconds and clamps overlaps."""

    smoothed: list[dict[str, Any]] = []
    total = len(tokens)
    for index, token in enumerate(tokens):
        mutable = dict(token)
        start_val = float(mutable.get("start", 0.0))
        end_val = float(mutable.get("end", start_val))
        duration = end_val - start_val
        if duration < min_len:
            if index + 1 < total:
                next_start = float(tokens[index + 1].get("start", end_val))
            else:
                next_start = end_val + min_len
            end_val = min(next_start, start_val + min_len)
            mutable["end"] = end_val
        smoothed.append(mutable)
    return smoothed


def _iter_sentence_payloads(payload: Any) -> Iterator[Mapping[str, Any]]:
    """Yield flattened sentence entries from chunk payloads."""

    if isinstance(payload, Mapping):
        sentences = payload.get("sentences")
        if isinstance(sentences, Sequence) and not isinstance(sentences, (str, bytes)):
            for entry in sentences:
                yield from _iter_sentence_payloads(entry)
            return
        yield payload
        return
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        for entry in payload:
            yield from _iter_sentence_payloads(entry)


def _extract_highlighting_policy(entry: Mapping[str, Any]) -> Optional[str]:
    """Return the highlighting policy encoded on a sentence entry."""

    summary = entry.get("highlighting_summary")
    if isinstance(summary, Mapping):
        policy = summary.get("policy")
        if isinstance(policy, str) and policy.strip():
            return policy.strip()
    candidate = entry.get("highlighting_policy") or entry.get("alignment_policy")
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return None


def _extract_policy_from_timing_tracks(
    payload: Mapping[str, Any],
) -> tuple[Optional[str], bool]:
    tracks = payload.get("timingTracks") or payload.get("timing_tracks")
    if not isinstance(tracks, Mapping):
        tracks = None
    fallback: Optional[str] = None
    estimated = False
    top_level = payload.get("highlighting_policy")
    if isinstance(top_level, str) and top_level.strip():
        normalized = top_level.strip()
        if _is_estimated_policy(normalized):
            return normalized, True
        fallback = normalized
    if not isinstance(tracks, Mapping):
        return fallback, estimated
    for entries in tracks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            policy = entry.get("policy")
            if not isinstance(policy, str):
                continue
            normalized = policy.strip()
            if not normalized:
                continue
            if _is_estimated_policy(normalized):
                return normalized, True
            if fallback is None:
                fallback = normalized
    return fallback, estimated


def _is_estimated_policy(policy: Optional[str]) -> bool:
    if not isinstance(policy, str):
        return False
    normalized = policy.strip().lower()
    return normalized.startswith("estimated")


def _probe_highlighting_policy(
    metadata_root: Path,
    default_policy: Optional[str],
) -> tuple[Optional[str], bool]:
    """Resolve the highlighting policy and whether estimated timings exist."""

    normalized_default = None
    if isinstance(default_policy, str) and default_policy.strip():
        normalized_default = default_policy.strip()
    estimated_detected = _is_estimated_policy(normalized_default)
    fallback_policy: Optional[str] = normalized_default

    if metadata_root.exists():
        for chunk_path in sorted(metadata_root.glob("chunk_*.json")):
            try:
                with chunk_path.open("r", encoding="utf-8") as handle:
                    chunk_payload = json.load(handle)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(chunk_payload, Mapping):
                policy, estimated = _extract_policy_from_timing_tracks(chunk_payload)
                if policy:
                    if estimated:
                        return policy, True
                    if fallback_policy is None:
                        fallback_policy = policy
                estimated_detected = estimated_detected or estimated
            for entry in _iter_sentence_payloads(chunk_payload):
                if isinstance(entry, Mapping):
                    policy = _extract_highlighting_policy(entry)
                    if policy:
                        normalized = policy.strip()
                        if _is_estimated_policy(normalized):
                            return normalized, True
                        if fallback_policy is None:
                            fallback_policy = normalized
    if fallback_policy is not None:
        estimated_detected = estimated_detected or _is_estimated_policy(fallback_policy)
    return fallback_policy, estimated_detected


@jobs_timing_router.get("/{job_id}/timing", response_class=JSONResponse)
async def get_job_timing(
    job_id: str,
    *,
    job_manager = Depends(get_pipeline_job_manager),
    locator: FileLocator = Depends(get_file_locator),
    library_repository: LibraryRepository = Depends(get_library_repository),
    request_user: RequestUserContext = Depends(get_request_user),
) -> JSONResponse:
    """Return flattened per-word timing data for ``job_id``."""

    job_root: Path
    result_payload: Mapping[str, Any] = {}

    try:
        job: PipelineJob = job_manager.get(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:
        entry = library_repository.get_entry_by_id(job_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
        job_root = Path(entry.library_path)
        if not job_root.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
        loader = MetadataLoader(job_root)
        try:
            manifest = await run_in_threadpool(loader.load_manifest)
        except FileNotFoundError as load_exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from load_exc
        except Exception as load_exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to load job metadata") from load_exc
        result_value = manifest.get("result") if isinstance(manifest, Mapping) else None
        if isinstance(result_value, Mapping):
            result_payload = dict(result_value)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    else:
        job_root = locator.resolve_path(job_id)
        if not (job_root / "metadata" / "job.json").exists():
            entry = library_repository.get_entry_by_id(job_id)
            if entry is not None:
                candidate_root = Path(entry.library_path)
                if candidate_root.exists():
                    job_root = candidate_root
        result_payload = job.result_payload if isinstance(job.result_payload, Mapping) else {}

    timing_tracks = result_payload.get("timing_tracks") if isinstance(result_payload, Mapping) else None
    if not isinstance(timing_tracks, Mapping):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No timing track available")

    requested_tracks = {
        key: path
        for key, path in timing_tracks.items()
        if key in {"mix", "translation", "original"} and isinstance(path, str) and path.strip()
    }
    if not requested_tracks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No timing track available")

    resolved_paths: Dict[str, Path] = {}
    for track_name, rel_path in requested_tracks.items():
        try:
            abs_path = _resolve_job_path(job_root, rel_path)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timing index missing",
            ) from exc
        if not abs_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timing index missing")
        resolved_paths[track_name] = abs_path

    data_cache: Dict[Path, Any] = {}
    resolved_segments: Dict[str, List[Any]] = {"mix": [], "translation": [], "original": []}
    for track_name, abs_path in resolved_paths.items():
        if abs_path not in data_cache:
            try:
                with abs_path.open("r", encoding="utf-8") as handle:
                    data_cache[abs_path] = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Timing index missing",
                ) from exc
        payload = data_cache[abs_path]
        segments: list[Any]
        if isinstance(payload, Mapping):
            track_entries = payload.get(track_name)
            if isinstance(track_entries, list):
                segments = track_entries
            elif track_name == "translation" and isinstance(payload.get("segments"), list):
                segments = payload["segments"]  # legacy
            elif track_name == "translation" and isinstance(payload.get("translation"), list):
                segments = payload["translation"]
            else:
                segments = []
        elif isinstance(payload, list):
            segments = payload
        else:
            segments = []
        resolved_segments[track_name] = segments

    unique_paths = sorted({path for path in resolved_paths.values()})
    try:
        stats = [path.stat() for path in unique_paths]
        digest = "-".join(f"{st.st_mtime_ns:x}-{st.st_size:x}" for st in stats)
        etag = f'W/"{digest}"'
    except OSError:
        fallback_count = sum(len(resolved_segments.get(name, [])) for name in resolved_segments)
        etag = f'W/"{job_id}-{fallback_count}"'

    playback_meta = result_payload.get("timing_meta") if isinstance(result_payload, Mapping) else None
    playback_rate = 1.0
    if isinstance(playback_meta, Mapping):
        try:
            playback_rate = float(playback_meta.get("playbackRate", 1.0))
        except (TypeError, ValueError):
            playback_rate = 1.0

    highlighting_policy, has_estimated_segments = _probe_highlighting_policy(
        job_root / "metadata",
        result_payload.get("highlighting_policy") if isinstance(result_payload, Mapping) else None,
    )

    def _collect_audio_availability() -> Dict[str, Dict[str, Any]]:
        audio_summary: Dict[str, Dict[str, Any]] = {}
        generated_payload = result_payload.get("generated_files") if isinstance(result_payload, Mapping) else None
        chunk_audio_keys: set[str] = set()
        if isinstance(generated_payload, Mapping):
            chunks = generated_payload.get("chunks")
            if isinstance(chunks, list):
                for chunk in chunks:
                    if not isinstance(chunk, Mapping):
                        continue
                    tracks = chunk.get("audio_tracks") or chunk.get("audioTracks")
                    if not isinstance(tracks, Mapping):
                        continue
                    for raw_key, raw_value in tracks.items():
                        if not isinstance(raw_key, str):
                            continue
                        key = raw_key.strip()
                        if not key:
                            continue
                        if key == "trans":
                            key = "translation"
                        chunk_audio_keys.add(key)
        audio_summary["orig_trans"] = {
            "track": "mix",
            "available": "orig_trans" in chunk_audio_keys,
        }
        audio_summary["orig"] = {
            "track": "original",
            "available": "orig" in chunk_audio_keys or "original" in chunk_audio_keys,
        }
        audio_summary["translation"] = {
            "track": "translation",
            "available": "translation" in chunk_audio_keys or "trans" in chunk_audio_keys,
        }
        return audio_summary

    headers = {
        "Cache-Control": "public, max-age=60",
        "ETag": etag,
    }
    tracks_payload: Dict[str, Any] = {}
    for track_name, segments in resolved_segments.items():
        if not segments:
            continue
        tracks_payload[track_name] = {
            "track": track_name,
            "segments": segments,
            "playback_rate": playback_rate,
        }
    return JSONResponse(
        content={
            "job_id": job_id,
            "tracks": tracks_payload,
            "audio": _collect_audio_availability(),
            "highlighting_policy": highlighting_policy,
            "has_estimated_segments": has_estimated_segments,
        },
        headers=headers,
    )
