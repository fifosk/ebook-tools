"""Synology Download Station client and configuration helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from .download_station_values import string_value as _string_value


@dataclass(frozen=True)
class DownloadStationConfig:
    """Server-side Download Station settings. Never serialize credentials."""

    base_url: str
    account: str
    password: str
    destination: str | None = None
    verify_tls: bool = True
    timeout_seconds: float = 15.0


class DownloadStationError(RuntimeError):
    """Token-safe Download Station adapter error."""

    def __init__(self, *, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.public_message = message


class DownloadStationClient:
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


def validate_source_uri(source_uri: str) -> str:
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


def _synology_error_code(payload: Mapping[str, Any]) -> str:
    error = payload.get("error")
    if isinstance(error, Mapping):
        code = error.get("code")
        if code is not None:
            return str(code)
    return "unknown"
