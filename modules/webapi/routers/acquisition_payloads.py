"""Token-safe acquisition route payload helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from modules.services.acquisition import (
    AcquisitionArtifact,
    AcquisitionCandidate,
    AcquisitionJobStatus,
)
from modules.services.acquisition.provider_roots import resolve_manual_download_roots
from modules.services.acquisition.url_safety import (
    looks_sensitive_key,
    strip_sensitive_url_parts,
)

from ..schemas.acquisition import (
    AcquisitionArtifactResponse,
    AcquisitionCandidatePayload,
    AcquisitionJobStatusResponse,
    AcquisitionPreparedArtifactResponse,
    AcquisitionSubtitleHintPayload,
)


def public_metadata_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        public: dict[str, Any] = {}
        for key, nested in value.items():
            key_text = str(key)
            if looks_sensitive_key(key_text):
                continue
            public[key_text] = public_metadata_value(nested)
        return public
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [public_metadata_value(item) for item in value]
    if isinstance(value, str):
        return strip_sensitive_url_parts(value)
    return value


def public_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    sanitized = public_metadata_value(metadata)
    return sanitized if isinstance(sanitized, dict) else {}


def metadata_string_values(
    value: Any,
    *,
    safe_roots: tuple[Path, ...] = (),
) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        values: list[str] = []
        seen_values: set[str] = set()
        for item in value:
            normalized = normalize_completed_file_value(item, safe_roots=safe_roots)
            if normalized and normalized not in seen_values:
                seen_values.add(normalized)
                values.append(normalized)
        return values
    normalized = normalize_completed_file_value(value, safe_roots=safe_roots)
    return [normalized] if normalized else []


def normalize_completed_file_value(
    value: Any,
    *,
    safe_roots: tuple[Path, ...] = (),
) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = _normalize_optional_text(strip_sensitive_url_parts(value))
    if not normalized:
        return None
    try:
        parsed = urlsplit(normalized)
    except ValueError:
        return None
    if parsed.scheme in {"http", "https", "magnet"}:
        return None
    if parsed.scheme or parsed.netloc:
        return None
    path = Path(normalized).expanduser()
    if path.is_absolute():
        return safe_absolute_completed_file_path(path, safe_roots)
    if any(part == ".." for part in path.parts):
        return None
    return normalized


def safe_absolute_completed_file_path(
    path: Path,
    safe_roots: tuple[Path, ...],
) -> str | None:
    if not safe_roots:
        return None
    resolved_path = path.resolve()
    for root in safe_roots:
        resolved_root = root.expanduser().resolve()
        try:
            resolved_path.relative_to(resolved_root)
        except ValueError:
            continue
        return resolved_path.as_posix()
    return None


def job_metadata_completed_files(
    metadata: Mapping[str, Any],
    *,
    safe_roots: tuple[Path, ...],
) -> list[str]:
    for key in ("completed_files", "completed_paths", "files"):
        values = metadata_string_values(metadata.get(key), safe_roots=safe_roots)
        if values:
            return values
    return metadata_string_values(
        metadata.get("completed_file")
        or metadata.get("completed_path")
        or metadata.get("local_path"),
        safe_roots=safe_roots,
    )


def sanitize_job_completed_file_metadata(
    metadata: Mapping[str, Any],
    *,
    safe_roots: tuple[Path, ...],
) -> dict[str, Any]:
    sanitized = dict(metadata)
    for key in ("completed_files", "completed_paths", "files"):
        if key not in sanitized:
            continue
        values = metadata_string_values(sanitized.get(key), safe_roots=safe_roots)
        if values:
            sanitized[key] = values
        else:
            sanitized.pop(key, None)
    for key in ("completed_file", "completed_path", "local_path"):
        if key not in sanitized:
            continue
        values = metadata_string_values(sanitized.get(key), safe_roots=safe_roots)
        if values:
            sanitized[key] = values[0]
        else:
            sanitized.pop(key, None)
    return sanitized


def job_completed_files(
    job: AcquisitionJobStatus,
    metadata: Mapping[str, Any],
    *,
    safe_roots: tuple[Path, ...],
) -> list[str]:
    completed_files = metadata_string_values(
        list(job.completed_files),
        safe_roots=safe_roots,
    )
    if completed_files:
        return completed_files
    return job_metadata_completed_files(metadata, safe_roots=safe_roots)


def candidate_payload(candidate: AcquisitionCandidate) -> AcquisitionCandidatePayload:
    return AcquisitionCandidatePayload(
        candidate_id=candidate.candidate_id,
        provider=candidate.provider,
        media_kind=candidate.media_kind,
        title=candidate.title,
        rights=candidate.rights,
        capabilities=list(candidate.capabilities),
        candidate_token=candidate.candidate_token,
        subtitle=candidate.subtitle,
        contributors=list(candidate.contributors),
        language=candidate.language,
        year=candidate.year,
        published_at=candidate.published_at,
        source_url=(
            strip_sensitive_url_parts(candidate.source_url)
            if candidate.source_url
            else None
        ),
        thumbnail_url=(
            strip_sensitive_url_parts(candidate.thumbnail_url)
            if candidate.thumbnail_url
            else None
        ),
        cover_url=(
            strip_sensitive_url_parts(candidate.cover_url)
            if candidate.cover_url
            else None
        ),
        local_path=candidate.local_path,
        size_bytes=candidate.size_bytes,
        modified_at=candidate.modified_at,
        duration_seconds=candidate.duration_seconds,
        subtitles=[
            AcquisitionSubtitleHintPayload(
                path=subtitle.path,
                filename=subtitle.filename,
                language=subtitle.language,
                format=subtitle.format,
            )
            for subtitle in candidate.subtitles
        ],
        metadata=public_metadata(candidate.metadata),
        requires_confirmation=candidate.requires_confirmation,
        policy_notes=list(candidate.policy_notes),
    )


def artifact_payload(artifact: AcquisitionArtifact) -> AcquisitionArtifactResponse:
    return AcquisitionArtifactResponse(
        provider=artifact.provider,
        media_kind=artifact.media_kind,
        status=artifact.status,
        artifact_id=artifact.artifact_id,
        artifact_path=artifact.artifact_path,
        local_path=artifact.local_path,
        filename=artifact.filename,
        size_bytes=artifact.size_bytes,
        modified_at=artifact.modified_at,
        next_actions=list(artifact.next_actions),
        metadata=public_metadata(artifact.metadata),
    )


def prepared_artifact_payload(artifact) -> AcquisitionPreparedArtifactResponse:
    return AcquisitionPreparedArtifactResponse(
        provider=artifact.provider,
        media_kind=artifact.media_kind,
        source_kind=artifact.source_kind,
        local_path=artifact.local_path,
        input_file=artifact.input_file,
        video_path=artifact.video_path,
        subtitle_path=artifact.subtitle_path,
        subtitles=[
            AcquisitionSubtitleHintPayload(
                path=str(subtitle.get("path") or ""),
                filename=str(subtitle.get("filename") or ""),
                language=subtitle.get("language")
                if isinstance(subtitle.get("language"), str)
                else None,
                format=subtitle.get("format")
                if isinstance(subtitle.get("format"), str)
                else None,
            )
            for subtitle in artifact.subtitles
            if subtitle.get("path") and subtitle.get("filename")
        ],
        next_actions=list(artifact.next_actions),
        metadata=public_metadata(artifact.metadata),
    )


def job_payload(
    job: AcquisitionJobStatus,
    *,
    config: Mapping[str, Any] | None = None,
) -> AcquisitionJobStatusResponse:
    safe_roots = resolve_manual_download_roots(config or {})
    metadata = sanitize_job_completed_file_metadata(
        public_metadata(job.metadata),
        safe_roots=safe_roots,
    )
    return AcquisitionJobStatusResponse(
        provider=job.provider,
        task_id=job.task_id,
        status=job.status,
        progress=job.progress,
        message=job.message,
        external_task_id=job.external_task_id,
        raw_status=job.raw_status,
        started_at=job.started_at,
        updated_at=job.updated_at,
        completed_files=job_completed_files(job, metadata, safe_roots=safe_roots),
        next_actions=list(job.next_actions),
        metadata=metadata,
    )


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
