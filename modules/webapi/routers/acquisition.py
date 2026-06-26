"""Discovery/acquisition provider routes."""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modules import logging_manager as log_mgr
from modules.permissions import normalize_role
from modules.services.acquisition import (
    AcquisitionArtifact,
    AcquisitionCandidate,
    AcquisitionJobStatus,
    AcquisitionProviderDiscoveryError,
    DownloadStationError,
    acquire_acquisition_candidate,
    discover_acquisition_candidates,
    enqueue_download_station_task,
    list_acquisition_providers,
    poll_download_station_task,
    prepare_acquisition_artifact,
    resolve_download_station_candidate_source_uri,
)

from ..dependencies import (
    RequestUserContext,
    RuntimeContextProvider,
    get_request_user,
    get_runtime_context_provider,
)
from ..route_telemetry import log_started_route_result
from ..schemas.acquisition import (
    AcquisitionAcquireRequest,
    AcquisitionArtifactResponse,
    AcquisitionCandidatePayload,
    AcquisitionDiscoveryResponse,
    AcquisitionJobCreateRequest,
    AcquisitionJobStatusResponse,
    AcquisitionPreparedArtifactResponse,
    AcquisitionProviderListResponse,
    AcquisitionProviderPayload,
    AcquisitionSubtitleHintPayload,
)


router = APIRouter(prefix="/api/acquisition", tags=["acquisition"])
LOGGER = log_mgr.get_logger().getChild("webapi.acquisition")
_ALLOWED_DISCOVERY_ROLES = {"admin", "editor"}
_SENSITIVE_METADATA_KEY_MARKERS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "secret",
    "sid",
    "token",
)


def _log_provider_route(
    result: str,
    started_at: float,
    *,
    operation: str = "providers",
    provider_count: int = 0,
) -> None:
    log_started_route_result(
        LOGGER,
        metric_name="ACQUISITION_ROUTE_DURATION",
        message=f"Acquisition {operation} route",
        operation=operation,
        result=result,
        started_at=started_at,
        include_operation=False,
        duration_first=False,
        providers=provider_count,
    )


def _log_unexpected_route_error(operation: str) -> None:
    LOGGER.warning(
        "Acquisition %s route failed unexpectedly; response detail suppressed",
        operation,
    )


def _ensure_discovery_user(
    request_user: RequestUserContext,
    *,
    operation: str,
    started_at: float,
) -> None:
    role = normalize_role(request_user.user_role) or ""
    if role not in _ALLOWED_DISCOVERY_ROLES:
        _log_provider_route("forbidden", started_at, operation=operation)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def _normalize_source_id_filters(source_ids: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_source_id in source_ids or []:
        source_id = str(raw_source_id).strip()
        if not source_id:
            continue
        key = source_id.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(source_id)
    return normalized


def _normalize_route_id(value: str) -> str:
    return str(value).strip()


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_optional_provider_id(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.casefold() if normalized else None


def _normalize_async_job_provider_id(
    value: str | None,
    *,
    operation: str,
    started_at: float,
) -> str:
    provider_id = str(value or "").strip().casefold()
    if not provider_id:
        _raise_bad_acquisition_route_id(
            operation=operation,
            started_at=started_at,
            detail="Missing acquisition provider",
        )
    if provider_id != "download_station":
        _log_provider_route("bad_request", started_at, operation=operation)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"provider {provider_id} does not support async acquisition jobs",
        )
    return provider_id


def _looks_sensitive_metadata_key(key: str) -> bool:
    normalized = key.replace("-", "_").casefold()
    return any(marker in normalized for marker in _SENSITIVE_METADATA_KEY_MARKERS)


def _public_metadata_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        public: dict[str, Any] = {}
        for key, nested in value.items():
            key_text = str(key)
            if _looks_sensitive_metadata_key(key_text):
                continue
            public[key_text] = _public_metadata_value(nested)
        return public
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_public_metadata_value(item) for item in value]
    if isinstance(value, str):
        return _strip_sensitive_url_query(value)
    return value


def _public_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    sanitized = _public_metadata_value(metadata)
    return sanitized if isinstance(sanitized, dict) else {}


def _metadata_string_values(value: Any) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        values: list[str] = []
        for item in value:
            if isinstance(item, str):
                normalized = _normalize_optional_text(_strip_sensitive_url_query(item))
                if normalized:
                    values.append(normalized)
        return values
    if isinstance(value, str):
        normalized = _normalize_optional_text(_strip_sensitive_url_query(value))
        return [normalized] if normalized else []
    return []


def _job_completed_files(job: AcquisitionJobStatus, metadata: Mapping[str, Any]) -> list[str]:
    completed_files = _metadata_string_values(list(job.completed_files))
    if completed_files:
        return completed_files
    for key in ("completed_files", "completed_paths", "files"):
        values = _metadata_string_values(metadata.get(key))
        if values:
            return values
    return _metadata_string_values(
        metadata.get("completed_file")
        or metadata.get("completed_path")
        or metadata.get("local_path")
    )


def _strip_sensitive_url_query(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if parsed.scheme not in {"http", "https", "magnet"} or not parsed.query:
        return value
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    public_pairs = [
        (key, item_value)
        for key, item_value in query_pairs
        if not _looks_sensitive_metadata_key(key)
    ]
    if len(public_pairs) == len(query_pairs):
        return value
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(public_pairs, doseq=True),
            parsed.fragment,
        )
    )


def _raise_bad_acquisition_route_id(
    *,
    operation: str,
    started_at: float,
    detail: str,
) -> None:
    _log_provider_route("bad_request", started_at, operation=operation)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _candidate_payload(candidate: AcquisitionCandidate) -> AcquisitionCandidatePayload:
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
            _strip_sensitive_url_query(candidate.source_url)
            if candidate.source_url
            else None
        ),
        thumbnail_url=(
            _strip_sensitive_url_query(candidate.thumbnail_url)
            if candidate.thumbnail_url
            else None
        ),
        cover_url=(
            _strip_sensitive_url_query(candidate.cover_url)
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
        metadata=_public_metadata(candidate.metadata),
        requires_confirmation=candidate.requires_confirmation,
        policy_notes=list(candidate.policy_notes),
    )


def _artifact_payload(artifact: AcquisitionArtifact) -> AcquisitionArtifactResponse:
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
        metadata=_public_metadata(artifact.metadata),
    )


def _prepared_artifact_payload(artifact) -> AcquisitionPreparedArtifactResponse:
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
                language=subtitle.get("language") if isinstance(subtitle.get("language"), str) else None,
                format=subtitle.get("format") if isinstance(subtitle.get("format"), str) else None,
            )
            for subtitle in artifact.subtitles
            if subtitle.get("path") and subtitle.get("filename")
        ],
        next_actions=list(artifact.next_actions),
        metadata=_public_metadata(artifact.metadata),
    )


def _job_payload(job: AcquisitionJobStatus) -> AcquisitionJobStatusResponse:
    metadata = _public_metadata(job.metadata)
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
        completed_files=_job_completed_files(job, metadata),
        next_actions=list(job.next_actions),
        metadata=metadata,
    )


@router.get(
    "/providers",
    response_model=AcquisitionProviderListResponse,
    status_code=status.HTTP_200_OK,
)
def list_providers(
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
) -> AcquisitionProviderListResponse:
    """Return configured/planned source discovery providers without secrets."""

    started_at = time.perf_counter()
    config = runtime_provider.resolve_config()
    registry = list_acquisition_providers(config=config)
    _log_provider_route("success", started_at, provider_count=len(registry.providers))
    return AcquisitionProviderListResponse(
        providers=[
            AcquisitionProviderPayload(**provider.as_dict())
            for provider in registry.providers
        ],
        policy_notes=list(registry.policy_notes),
        paths=dict(registry.paths),
        default_provider_ids={
            media_kind: list(provider_ids)
            for media_kind, provider_ids in registry.default_provider_ids.items()
        },
    )


@router.get(
    "/discover",
    response_model=AcquisitionDiscoveryResponse,
    status_code=status.HTTP_200_OK,
)
def discover(
    media_kind: str = Query(..., pattern="^(book|video)$"),
    q: str = Query(default=""),
    provider: str | None = Query(default=None),
    language: str | None = Query(default=None),
    source_id: list[str] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
) -> AcquisitionDiscoveryResponse:
    """Return normalized source candidates for Web and Apple Create."""

    started_at = time.perf_counter()
    _ensure_discovery_user(request_user, operation="discover", started_at=started_at)
    source_ids = _normalize_source_id_filters(source_id)
    provider_id = _normalize_optional_provider_id(provider)
    try:
        result = discover_acquisition_candidates(
            media_kind=media_kind,
            query=q,
            provider=provider_id,
            language=language,
            limit=limit,
            source_ids=source_ids,
            config=runtime_provider.resolve_config(),
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="discover")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except AcquisitionProviderDiscoveryError as exc:
        _log_provider_route(exc.reason or "provider_error", started_at, operation="discover")
        LOGGER.info(
            "Acquisition discovery provider failed provider=%s reason=%s",
            exc.provider,
            exc.reason,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.public_message,
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="discover")
        _log_unexpected_route_error("discover")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to query acquisition provider.",
        ) from exc

    _log_provider_route(
        "success",
        started_at,
        operation="discover",
        provider_count=len(result.providers_queried),
    )
    return AcquisitionDiscoveryResponse(
        candidates=[_candidate_payload(candidate) for candidate in result.candidates],
        policy_notes=list(result.policy_notes),
        providers_queried=list(result.providers_queried),
    )


@router.post(
    "/acquire",
    response_model=AcquisitionArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def acquire(
    payload: AcquisitionAcquireRequest,
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
) -> AcquisitionArtifactResponse:
    """Acquire a reviewed source candidate into an existing Create source root."""

    started_at = time.perf_counter()
    _ensure_discovery_user(request_user, operation="acquire", started_at=started_at)
    candidate_token = _normalize_route_id(payload.candidate_token)
    if not candidate_token:
        _raise_bad_acquisition_route_id(
            operation="acquire",
            started_at=started_at,
            detail="Missing acquisition candidate token",
        )
    try:
        artifact = acquire_acquisition_candidate(
            candidate_token=candidate_token,
            confirmed=payload.confirmed,
            filename=_normalize_optional_text(payload.filename),
            config=runtime_provider.resolve_config(),
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="acquire")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="acquire")
        _log_unexpected_route_error("acquire")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to acquire candidate.",
        ) from exc

    _log_provider_route("success", started_at, operation="acquire", provider_count=1)
    return _artifact_payload(artifact)


@router.post(
    "/artifacts/{artifact_id}/prepare",
    response_model=AcquisitionPreparedArtifactResponse,
    status_code=status.HTTP_200_OK,
)
def prepare_artifact(
    artifact_id: str,
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
) -> AcquisitionPreparedArtifactResponse:
    """Resolve a local/acquired artifact into fields existing Create forms use."""

    started_at = time.perf_counter()
    _ensure_discovery_user(request_user, operation="artifact_prepare", started_at=started_at)
    normalized_artifact_id = _normalize_route_id(artifact_id)
    if not normalized_artifact_id:
        _raise_bad_acquisition_route_id(
            operation="artifact_prepare",
            started_at=started_at,
            detail="Missing acquisition artifact id",
        )
    try:
        artifact = prepare_acquisition_artifact(
            artifact_id=normalized_artifact_id,
            config=runtime_provider.resolve_config(),
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="artifact_prepare")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="artifact_prepare")
        _log_unexpected_route_error("artifact_prepare")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to prepare acquisition artifact.",
        ) from exc

    _log_provider_route("success", started_at, operation="artifact_prepare", provider_count=1)
    return _prepared_artifact_payload(artifact)


@router.post(
    "/jobs",
    response_model=AcquisitionJobStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_job(
    payload: AcquisitionJobCreateRequest,
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
) -> AcquisitionJobStatusResponse:
    """Submit a reviewed async downloader handoff job."""

    started_at = time.perf_counter()
    _ensure_discovery_user(request_user, operation="job_create", started_at=started_at)
    _normalize_async_job_provider_id(
        payload.provider,
        operation="job_create",
        started_at=started_at,
    )
    try:
        config = runtime_provider.resolve_config()
        candidate_token = _normalize_optional_text(payload.candidate_token)
        source_uri = (
            resolve_download_station_candidate_source_uri(
                candidate_token=candidate_token,
                config=config,
            )
            if candidate_token
            else _normalize_optional_text(payload.source_uri)
        )
        job = enqueue_download_station_task(
            source_uri=source_uri or "",
            confirmed=payload.confirmed,
            destination=_normalize_optional_text(payload.destination),
            config=config,
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="job_create")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except DownloadStationError as exc:
        _log_provider_route(exc.reason or "provider_error", started_at, operation="job_create")
        LOGGER.info("Download Station handoff failed reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.public_message,
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="job_create")
        _log_unexpected_route_error("job_create")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to submit acquisition job.",
        ) from exc

    _log_provider_route("success", started_at, operation="job_create", provider_count=1)
    return _job_payload(job)


@router.get(
    "/jobs/{task_id}",
    response_model=AcquisitionJobStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_job(
    task_id: str,
    provider: str = "download_station",
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
) -> AcquisitionJobStatusResponse:
    """Poll an async acquisition/downloader job."""

    started_at = time.perf_counter()
    _ensure_discovery_user(request_user, operation="job_poll", started_at=started_at)
    normalized_task_id = _normalize_route_id(task_id)
    if not normalized_task_id:
        _raise_bad_acquisition_route_id(
            operation="job_poll",
            started_at=started_at,
            detail="Missing acquisition task id",
        )
    _normalize_async_job_provider_id(
        provider,
        operation="job_poll",
        started_at=started_at,
    )
    try:
        job = poll_download_station_task(
            task_id=normalized_task_id,
            config=runtime_provider.resolve_config(),
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="job_poll")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except DownloadStationError as exc:
        _log_provider_route(exc.reason or "provider_error", started_at, operation="job_poll")
        LOGGER.info("Download Station poll failed reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.public_message,
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="job_poll")
        _log_unexpected_route_error("job_poll")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to poll acquisition job.",
        ) from exc

    _log_provider_route("success", started_at, operation="job_poll", provider_count=1)
    return _job_payload(job)
