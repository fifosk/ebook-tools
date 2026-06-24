#!/usr/bin/env python3
"""Repo-owned Apple deploy readiness hook for the shared device pipeline.

The shared deploy helper still calls this legacy filename for app-local
readiness. For ebook-tools it performs only token-safe checks: backend health
and the public runtime descriptor used by Apple surfaces.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://api.langtools.fifosk.synology.me"
DEFAULT_HEALTH_PATH = "/_health"
DEFAULT_RUNTIME_PATH = "/api/system/runtime"
AUTH_DESCRIPTOR = {
    "loginPath": "/api/auth/login",
    "sessionPath": "/api/auth/session",
}
CLIENT_CONFIG_DESCRIPTOR = {
    "sessionTokenStorage": "device-keychain",
    "legacyTokenMigration": "userdefaults-authToken",
}
CREATION_DESCRIPTOR = {
    "bookOptionsPath": "/api/books/options",
    "bookJobsPath": "/api/books/jobs",
    "pipelineFilesPath": "/api/pipelines/files",
    "pipelineContentIndexPath": "/api/pipelines/files/content-index",
    "pipelineUploadPath": "/api/pipelines/files/upload",
    "pipelineJobsPath": "/api/pipelines",
    "pipelineIntakeStatusPath": "/api/pipelines/intake/status",
    "subtitleSourcesPath": "/api/subtitles/sources",
    "subtitleDeleteSourcePath": "/api/subtitles/delete-source",
    "subtitleModelsPath": "/api/subtitles/models",
    "subtitleJobsPath": "/api/subtitles/jobs",
    "youtubeLibraryPath": "/api/subtitles/youtube/library",
    "youtubeSubtitleStreamsPath": "/api/subtitles/youtube/subtitle-streams",
    "youtubeExtractSubtitlesPath": "/api/subtitles/youtube/extract-subtitles",
    "subtitleTvMetadataPreviewPath": "/api/subtitles/metadata/tv/lookup",
    "subtitleTvMetadataCacheClearPath": "/api/subtitles/metadata/tv/cache/clear",
    "youtubeMetadataPreviewPath": "/api/subtitles/metadata/youtube/lookup",
    "youtubeMetadataCacheClearPath": "/api/subtitles/metadata/youtube/cache/clear",
    "youtubeDubPath": "/api/subtitles/youtube/dub",
}
EXPECTED_ROOT_VALUES = {
    "app": "ebook-tools",
    "service": "ebook-tools-api",
    "status": "ok",
}
EXPECTED_APPLE_PIPELINE_VALUES = {
    "manifestId": "ebook-tools",
}
EXPECTED_AUTH_VALUES = {
    "loginPath": AUTH_DESCRIPTOR["loginPath"],
    "sessionPath": AUTH_DESCRIPTOR["sessionPath"],
}
EXPECTED_CLIENT_CONFIG_VALUES = {
    "sessionTokenStorage": CLIENT_CONFIG_DESCRIPTOR["sessionTokenStorage"],
    "legacyTokenMigration": CLIENT_CONFIG_DESCRIPTOR["legacyTokenMigration"],
}


def endpoint_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def json_request(base_url: str, path: str, *, timeout: float) -> dict[str, Any]:
    url = endpoint_url(base_url, path)
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(128 * 1024).decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read(2048).decode("utf-8", errors="replace")
        message = body.strip() or exc.reason
        raise RuntimeError(f"{path} returned HTTP {exc.code}: {message}") from exc
    except URLError as exc:
        raise RuntimeError(f"{path} failed: {exc.reason}") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path} did not return JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} returned a JSON {type(payload).__name__}, expected object")
    return payload


def validate_health(payload: Mapping[str, Any]) -> list[str]:
    status = str(payload.get("status", "")).lower()
    if status not in {"ok", "healthy", "pass", "up"}:
        return [f"health status={payload.get('status')!r}"]
    return []


def validate_runtime_descriptor(payload: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    failures.extend(_validate_mapping_values(payload, EXPECTED_ROOT_VALUES, "runtime"))
    failures.extend(
        _validate_mapping_values(
            _mapping_child(payload, "applePipeline"),
            EXPECTED_APPLE_PIPELINE_VALUES,
            "runtime.applePipeline",
        )
    )
    failures.extend(
        _validate_mapping_values(
            _mapping_child(payload, "auth"),
            EXPECTED_AUTH_VALUES,
            "runtime.auth",
        )
    )
    failures.extend(
        _validate_mapping_values(
            _mapping_child(payload, "clientConfig"),
            EXPECTED_CLIENT_CONFIG_VALUES,
            "runtime.clientConfig",
        )
    )
    creation = _mapping_child(payload, "creation")
    if not creation:
        failures.append("runtime.creation=<missing>")
    else:
        for key, expected in CREATION_DESCRIPTOR.items():
            actual = creation.get(key)
            if actual != expected:
                failures.append(f"runtime.creation.{key}={actual!r} expected {expected!r}")
    return failures


def check_readiness(
    base_url: str,
    *,
    health_path: str = DEFAULT_HEALTH_PATH,
    runtime_path: str = DEFAULT_RUNTIME_PATH,
    timeout: float = 10.0,
) -> dict[str, Any]:
    health_payload = json_request(base_url, health_path, timeout=timeout)
    health_failures = validate_health(health_payload)
    if health_failures:
        raise RuntimeError("; ".join(health_failures))

    runtime_payload = json_request(base_url, runtime_path, timeout=timeout)
    runtime_failures = validate_runtime_descriptor(runtime_payload)
    if runtime_failures:
        raise RuntimeError("Runtime descriptor is not Apple-ready: " + "; ".join(runtime_failures))

    return {
        "base_url": base_url,
        "health_path": health_path,
        "runtime_path": runtime_path,
        "creation_paths": len(CREATION_DESCRIPTOR),
    }


def _mapping_child(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    child = payload.get(key)
    return child if isinstance(child, Mapping) else {}


def _validate_mapping_values(
    payload: Mapping[str, Any],
    expected_values: Mapping[str, Any],
    label: str,
) -> list[str]:
    failures: list[str] = []
    for key, expected in expected_values.items():
        actual = payload.get(key)
        if actual != expected:
            failures.append(f"{label}.{key}={actual!r} expected {expected!r}")
    return failures


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--health-path", default=DEFAULT_HEALTH_PATH)
    parser.add_argument("--runtime-path", default=DEFAULT_RUNTIME_PATH)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--remote-host", default="")
    parser.add_argument("--tailscale-url", default="")
    parser.add_argument("--use-remote-env-tokens", action="store_true")
    parser.add_argument("--require-separate-read-token", action="store_true")
    parser.add_argument("--require-write-token", action="store_true")
    parser.add_argument("--skip-apple-build", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = check_readiness(
            args.base_url,
            health_path=args.health_path,
            runtime_path=args.runtime_path,
            timeout=args.timeout,
        )
    except RuntimeError as exc:
        print(f"ebook-tools Apple deploy readiness failed: {exc}", file=sys.stderr)
        return 1

    print(
        "ebook-tools Apple deploy readiness passed: "
        f"{summary['base_url']} advertised {summary['creation_paths']} Create paths"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
