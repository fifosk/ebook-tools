"""Synology Download Station handoff for reviewed acquisition jobs."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from .references import resolve_acquisition_reference
from .tokens import decode_acquisition_token


@dataclass(frozen=True)
class DownloadStationConfig:
    """Server-side Download Station settings. Never serialize credentials."""

    base_url: str
    account: str
    password: str
    destination: str | None = None
    verify_tls: bool = True
    timeout_seconds: float = 15.0


@dataclass(frozen=True)
class AcquisitionJobStatus:
    """Token-safe downloader job status returned to Web and Apple clients."""

    provider: str
    task_id: str
    status: str
    progress: float | None = None
    message: str | None = None
    external_task_id: str | None = None
    raw_status: str | None = None
    started_at: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_files: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


class DownloadStationError(RuntimeError):
    """Token-safe Download Station adapter error."""

    def __init__(self, *, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.public_message = message


def enqueue_download_station_task(
    *,
    source_uri: str,
    confirmed: bool,
    destination: str | None = None,
    config: Mapping[str, Any] | None = None,
    session: requests.Session | None = None,
) -> AcquisitionJobStatus:
    """Create a reviewed Download Station task from a URI or magnet link."""

    if not confirmed:
        raise ValueError("confirmation is required before downloader handoff")
    normalized_uri = _validate_source_uri(source_uri)
    settings = resolve_download_station_config(config or {})
    client = _DownloadStationClient(settings, session=session)
    task_id = client.create_task(
        source_uri=normalized_uri,
        destination=destination or settings.destination,
    )
    return AcquisitionJobStatus(
        provider="download_station",
        task_id=task_id or "download_station:submitted",
        status="submitted",
        external_task_id=task_id,
        message=(
            "Download Station accepted the reviewed task."
            if task_id
            else "Download Station accepted the reviewed task; scan manual downloads after it completes."
        ),
        next_actions=("poll_download", "discover_manual_downloads", "import_local"),
        metadata={"source_kind": "download_station"},
    )


def resolve_download_station_candidate_source_uri(
    *,
    candidate_token: str,
    config: Mapping[str, Any] | None = None,
) -> str:
    """Resolve a reviewed discovery candidate token into a Download Station URI."""

    payload = decode_acquisition_token(candidate_token)
    provider = _string_value(payload.get("provider"))
    media_kind = _string_value(payload.get("media_kind"))
    source_ref = _string_value(payload.get("source_ref"))
    if provider != "newznab_torznab" or media_kind != "video" or not source_ref:
        raise ValueError("candidate_token does not reference a Download Station source")
    reference = resolve_acquisition_reference(
        source_ref,
        provider=provider,
        media_kind=media_kind,
        config=config or {},
    )
    return _validate_source_uri(_string_value(reference.get("source_uri")))


def poll_download_station_task(
    *,
    task_id: str,
    config: Mapping[str, Any] | None = None,
    session: requests.Session | None = None,
) -> AcquisitionJobStatus:
    """Poll a Download Station task by its provider task id."""

    normalized_task_id = (task_id or "").strip()
    if not normalized_task_id:
        raise ValueError("task_id is required")
    if normalized_task_id == "download_station:submitted":
        return AcquisitionJobStatus(
            provider="download_station",
            task_id=normalized_task_id,
            status="submitted",
            message=(
                "Download Station did not return a provider task id; use manual downloads discovery after completion."
            ),
            next_actions=("discover_manual_downloads", "import_local"),
        )
    settings = resolve_download_station_config(config or {})
    client = _DownloadStationClient(settings, session=session)
    task = client.get_task_info(normalized_task_id)
    raw_status = _string_value(task.get("status")) or "unknown"
    progress = _task_progress(task)
    status = _normalize_task_status(raw_status)
    completed_files = _completed_files(task) if status == "completed" else ()
    next_actions = (
        ("discover_manual_downloads", "import_local")
        if status == "completed"
        else ("poll_download",)
    )
    return AcquisitionJobStatus(
        provider="download_station",
        task_id=normalized_task_id,
        status=status,
        progress=progress,
        message=_task_message(task, raw_status),
        external_task_id=normalized_task_id,
        raw_status=raw_status,
        completed_files=completed_files,
        next_actions=next_actions,
        metadata={"source_kind": "download_station"},
    )


def resolve_download_station_config(config: Mapping[str, Any]) -> DownloadStationConfig:
    """Resolve Download Station settings from config/env without exposing them."""

    base_url = _first_config_or_env(
        config,
        ("download_station_url", "synology_download_station_url"),
        ("SYNOLOGY_DOWNLOAD_STATION_URL", "EBOOK_DOWNLOAD_STATION_URL"),
    )
    host = _first_config_or_env(
        config,
        ("download_station_host", "synology_download_station_host"),
        ("SYNOLOGY_DOWNLOAD_STATION_HOST", "EBOOK_DOWNLOAD_STATION_HOST"),
    )
    if not base_url and host:
        base_url = host if "://" in host else f"https://{host}"
    account = _first_config_or_env(
        config,
        ("download_station_account", "download_station_username", "synology_download_station_username"),
        (
            "SYNOLOGY_DOWNLOAD_STATION_ACCOUNT",
            "SYNOLOGY_DOWNLOAD_STATION_USERNAME",
            "EBOOK_DOWNLOAD_STATION_USERNAME",
        ),
    )
    password = _first_config_or_env(
        config,
        ("download_station_password", "synology_download_station_password"),
        ("SYNOLOGY_DOWNLOAD_STATION_PASSWORD", "EBOOK_DOWNLOAD_STATION_PASSWORD"),
    )
    if not base_url or not account or not password:
        raise DownloadStationError(
            reason="not_configured",
            message="Synology Download Station is not fully configured on the backend.",
        )
    return DownloadStationConfig(
        base_url=_normalize_base_url(base_url),
        account=account,
        password=password,
        destination=_first_config_or_env(
            config,
            ("download_station_destination", "download_station_completed_share"),
            ("SYNOLOGY_DOWNLOAD_STATION_DESTINATION", "EBOOK_DOWNLOAD_STATION_DESTINATION"),
        ),
        verify_tls=_bool_config(config.get("download_station_verify_tls"), default=True),
        timeout_seconds=_float_config(config.get("download_station_timeout_seconds"), default=15.0),
    )


class _DownloadStationClient:
    def __init__(
        self,
        settings: DownloadStationConfig,
        *,
        session: requests.Session | None,
    ) -> None:
        self._settings = settings
        self._session = session or requests.Session()

    def create_task(self, *, source_uri: str, destination: str | None) -> str | None:
        api_info = self._api_info()
        sid = self._login(api_info)
        try:
            task_api = api_info.get("SYNO.DownloadStation.Task", {})
            params: dict[str, Any] = {
                "api": "SYNO.DownloadStation.Task",
                "version": _api_version(task_api, default=1),
                "method": "create",
                "uri": source_uri,
                "_sid": sid,
            }
            if destination:
                params["destination"] = destination
            payload = self._post(_api_path(task_api, "DownloadStation/task.cgi"), params=params)
            data = payload.get("data")
            if isinstance(data, Mapping):
                return (
                    _string_value(data.get("task_id"))
                    or _string_value(data.get("taskId"))
                    or _string_value(data.get("id"))
                )
            return None
        finally:
            self._logout(api_info, sid)

    def get_task_info(self, task_id: str) -> Mapping[str, Any]:
        api_info = self._api_info()
        sid = self._login(api_info)
        try:
            task_api = api_info.get("SYNO.DownloadStation.Task", {})
            payload = self._get(
                _api_path(task_api, "DownloadStation/task.cgi"),
                params={
                    "api": "SYNO.DownloadStation.Task",
                    "version": _api_version(task_api, default=1),
                    "method": "getinfo",
                    "id": task_id,
                    "additional": "detail,transfer,file",
                    "_sid": sid,
                },
            )
            data = payload.get("data")
            if not isinstance(data, Mapping):
                raise DownloadStationError(
                    reason="invalid_response",
                    message="Download Station returned an invalid task response.",
                )
            tasks = data.get("tasks")
            if isinstance(tasks, list) and tasks and isinstance(tasks[0], Mapping):
                return tasks[0]
            raise DownloadStationError(
                reason="not_found",
                message="Download Station task was not found.",
            )
        finally:
            self._logout(api_info, sid)

    def _api_info(self) -> Mapping[str, Mapping[str, Any]]:
        payload = self._get(
            "query.cgi",
            params={
                "api": "SYNO.API.Info",
                "version": 1,
                "method": "query",
                "query": "SYNO.API.Auth,SYNO.DownloadStation.Task",
            },
        )
        data = payload.get("data")
        if not isinstance(data, Mapping):
            return {}
        return {
            str(key): value
            for key, value in data.items()
            if isinstance(value, Mapping)
        }

    def _login(self, api_info: Mapping[str, Mapping[str, Any]]) -> str:
        auth_api = api_info.get("SYNO.API.Auth", {})
        payload = self._get(
            _api_path(auth_api, "auth.cgi"),
            params={
                "api": "SYNO.API.Auth",
                "version": _api_version(auth_api, default=2),
                "method": "login",
                "account": self._settings.account,
                "passwd": self._settings.password,
                "session": "DownloadStation",
                "format": "sid",
            },
        )
        data = payload.get("data")
        sid = _string_value(data.get("sid")) if isinstance(data, Mapping) else None
        if not sid:
            raise DownloadStationError(
                reason="auth_failed",
                message="Download Station authentication did not return a session id.",
            )
        return sid

    def _logout(self, api_info: Mapping[str, Mapping[str, Any]], sid: str) -> None:
        auth_api = api_info.get("SYNO.API.Auth", {})
        try:
            self._get(
                _api_path(auth_api, "auth.cgi"),
                params={
                    "api": "SYNO.API.Auth",
                    "version": _api_version(auth_api, default=2),
                    "method": "logout",
                    "session": "DownloadStation",
                    "_sid": sid,
                },
            )
        except DownloadStationError:
            return

    def _get(self, path: str, *, params: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._request("get", path, params=params)

    def _post(self, path: str, *, params: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._request("post", path, params=params)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        url = _webapi_url(self._settings.base_url, path)
        try:
            requester = getattr(self._session, method)
            response = requester(
                url,
                params=dict(params),
                timeout=self._settings.timeout_seconds,
                verify=self._settings.verify_tls,
            )
            response.raise_for_status()
            payload = response.json()
        except DownloadStationError:
            raise
        except Exception as exc:
            raise DownloadStationError(
                reason="request_failed",
                message="Download Station request failed. Check backend NAS configuration.",
            ) from exc
        if not isinstance(payload, Mapping):
            raise DownloadStationError(
                reason="invalid_response",
                message="Download Station returned an invalid response.",
            )
        if payload.get("success") is False:
            raise DownloadStationError(
                reason=f"api_error_{_synology_error_code(payload)}",
                message="Download Station rejected the request.",
            )
        return payload


def _validate_source_uri(source_uri: str) -> str:
    value = (source_uri or "").strip()
    if not value:
        raise ValueError("source_uri is required")
    if value.startswith("magnet:?"):
        return value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_uri must be an http(s) URL or magnet link")
    return value


def _webapi_url(base_url: str, path: str) -> str:
    clean_path = path.lstrip("/")
    return urljoin(f"{base_url.rstrip('/')}/webapi/", clean_path)


def _api_path(api_info: Mapping[str, Any], default: str) -> str:
    return _string_value(api_info.get("path")) or default


def _api_version(api_info: Mapping[str, Any], *, default: int) -> int:
    for key in ("maxVersion", "max_version", "version"):
        value = api_info.get(key)
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            continue
    return default


def _normalize_base_url(raw_url: str) -> str:
    value = raw_url.strip()
    if "://" not in value:
        value = f"https://{value}"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise DownloadStationError(
            reason="invalid_config",
            message="Download Station backend URL is invalid.",
        )
    return value.rstrip("/")


def _first_config_or_env(
    config: Mapping[str, Any],
    config_keys: tuple[str, ...],
    env_keys: tuple[str, ...],
) -> str | None:
    for key in config_keys:
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in env_keys:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def _bool_config(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _float_config(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _task_progress(task: Mapping[str, Any]) -> float | None:
    size = _int_value(task.get("size"))
    downloaded = _int_value(task.get("size_downloaded"))
    additional = task.get("additional")
    if isinstance(additional, Mapping):
        transfer = additional.get("transfer")
        if isinstance(transfer, Mapping):
            downloaded = downloaded or _int_value(transfer.get("size_downloaded"))
        detail = additional.get("detail")
        if isinstance(detail, Mapping):
            size = size or _int_value(detail.get("size"))
    if size and downloaded is not None:
        return max(0.0, min(1.0, downloaded / size))
    return None


def _normalize_task_status(raw_status: str) -> str:
    normalized = raw_status.casefold()
    if normalized in {"finished", "finish", "completed", "complete", "seeding"}:
        return "completed"
    if normalized in {"downloading", "waiting", "extracting", "hash_checking"}:
        return "running"
    if normalized in {"paused", "error", "broken", "failed"}:
        return "failed" if normalized != "paused" else "paused"
    return "unknown"


def _completed_files(task: Mapping[str, Any]) -> tuple[str, ...]:
    additional = task.get("additional")
    if not isinstance(additional, Mapping):
        return ()
    files = additional.get("file")
    if not isinstance(files, list):
        return ()
    paths: list[str] = []
    for item in files:
        if not isinstance(item, Mapping):
            continue
        filename = _string_value(item.get("filename")) or _string_value(item.get("name"))
        if filename:
            paths.append(filename)
    return tuple(paths)


def _task_message(task: Mapping[str, Any], raw_status: str) -> str:
    title = _string_value(task.get("title"))
    if title:
        return f"Download Station task {title} is {raw_status}."
    return f"Download Station task is {raw_status}."


def _synology_error_code(payload: Mapping[str, Any]) -> str:
    error = payload.get("error")
    if isinstance(error, Mapping):
        code = error.get("code")
        if code is not None:
            return str(code)
    return "unknown"


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
