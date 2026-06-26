#!/usr/bin/env python3
"""Repo-owned Apple deploy readiness hook for the shared device pipeline.

The shared deploy helper still calls this legacy filename for app-local
readiness. For ebook-tools it performs only token-safe checks: backend health
and the public runtime descriptor used by Apple surfaces.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections.abc import Mapping
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

_RUNTIME_DESCRIPTOR_PATH = ROOT_DIR / "modules" / "webapi" / "runtime_descriptor.py"
_RUNTIME_DESCRIPTOR_SPEC = importlib.util.spec_from_file_location(
    "ebook_tools_runtime_descriptor",
    _RUNTIME_DESCRIPTOR_PATH,
)
if _RUNTIME_DESCRIPTOR_SPEC is None or _RUNTIME_DESCRIPTOR_SPEC.loader is None:
    raise RuntimeError(f"Unable to load runtime descriptor from {_RUNTIME_DESCRIPTOR_PATH}")
_runtime_descriptor = importlib.util.module_from_spec(_RUNTIME_DESCRIPTOR_SPEC)
_RUNTIME_DESCRIPTOR_SPEC.loader.exec_module(_runtime_descriptor)

APPLE_PIPELINE_DESCRIPTOR = _runtime_descriptor.APPLE_PIPELINE_DESCRIPTOR
AUTH_DESCRIPTOR = _runtime_descriptor.AUTH_DESCRIPTOR
CLIENT_CONFIG_DESCRIPTOR = _runtime_descriptor.CLIENT_CONFIG_DESCRIPTOR
CREATION_DESCRIPTOR = _runtime_descriptor.CREATION_DESCRIPTOR
LIBRARY_ACTIONS_DESCRIPTOR = _runtime_descriptor.LIBRARY_ACTIONS_DESCRIPTOR
OFFLINE_EXPORTS_DESCRIPTOR = _runtime_descriptor.OFFLINE_EXPORTS_DESCRIPTOR
PLAYBACK_STATE_DESCRIPTOR = _runtime_descriptor.PLAYBACK_STATE_DESCRIPTOR
NOTIFICATIONS_DESCRIPTOR = _runtime_descriptor.NOTIFICATIONS_DESCRIPTOR

DEFAULT_BASE_URL = "https://api.langtools.fifosk.synology.me"
DEFAULT_HEALTH_PATH = "/_health"
DEFAULT_RUNTIME_PATH = "/api/system/runtime"
EXPECTED_ROOT_VALUES = {
    "app": "ebook-tools",
    "service": "ebook-tools-api",
    "status": "ok",
}
RUNTIME_SECTION_DESCRIPTORS = {
    "auth": AUTH_DESCRIPTOR,
    "clientConfig": CLIENT_CONFIG_DESCRIPTOR,
    "applePipeline": APPLE_PIPELINE_DESCRIPTOR,
    "creation": CREATION_DESCRIPTOR,
    "libraryActions": LIBRARY_ACTIONS_DESCRIPTOR,
    "offlineExports": OFFLINE_EXPORTS_DESCRIPTOR,
    "playbackState": PLAYBACK_STATE_DESCRIPTOR,
    "notifications": NOTIFICATIONS_DESCRIPTOR,
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
    for section_name, descriptor in RUNTIME_SECTION_DESCRIPTORS.items():
        section = _mapping_child(payload, section_name)
        if not section:
            failures.append(f"runtime.{section_name}=<missing>")
            continue
        failures.extend(
            _validate_mapping_values(
                section,
                descriptor,
                f"runtime.{section_name}",
            )
        )
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
        "library_action_paths": len(LIBRARY_ACTIONS_DESCRIPTOR),
        "offline_export_paths": len(OFFLINE_EXPORTS_DESCRIPTOR),
        "playback_state_paths": len(PLAYBACK_STATE_DESCRIPTOR),
        "notification_paths": len(NOTIFICATIONS_DESCRIPTOR),
        "runtime_sections": len(RUNTIME_SECTION_DESCRIPTORS),
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
        actual = _normalize_descriptor_value(payload.get(key))
        normalized_expected = _normalize_descriptor_value(expected)
        if actual != normalized_expected:
            failures.append(f"{label}.{key}={actual!r} expected {normalized_expected!r}")
    return failures


def _normalize_descriptor_value(value: Any) -> Any:
    return list(value) if isinstance(value, tuple) else value


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
        f"{summary['base_url']} advertised {summary['runtime_sections']} Apple runtime sections"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
