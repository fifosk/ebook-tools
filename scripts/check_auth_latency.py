#!/usr/bin/env python3
"""Measure ebook-tools auth latency without printing credentials or tokens."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://api.langtools.fifosk.synology.me"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=None, help="API base URL. Defaults to E2E_API_BASE_URL or production.")
    parser.add_argument("--env-file", default=".env", help="Env file containing E2E_USERNAME/E2E_PASSWORD.")
    parser.add_argument("--runs", type=int, default=5, help="Number of login/session timing runs.")
    parser.add_argument("--timeout", type=float, default=12.0, help="Per-request timeout in seconds.")
    parser.add_argument(
        "--warn-total-seconds",
        type=float,
        default=1.0,
        help="Warn when any login or session request exceeds this duration.",
    )
    return parser.parse_args()


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float,
) -> tuple[int, float, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)

    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read()
            elapsed = time.perf_counter() - started
            data = json.loads(response_body.decode("utf-8")) if response_body else {}
            return response.status, elapsed, data
    except urllib.error.HTTPError as exc:
        exc.read()
        elapsed = time.perf_counter() - started
        return exc.code, elapsed, {}


def summarize(label: str, values: list[float]) -> str:
    if not values:
        return f"{label}: no successful samples"
    return (
        f"{label}: min={min(values):.3f}s "
        f"median={statistics.median(values):.3f}s "
        f"max={max(values):.3f}s"
    )


def main() -> int:
    args = parse_args()
    env = {**load_env_file(Path(args.env_file)), **os.environ}
    base_url = (args.base_url or env.get("E2E_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    username = env.get("E2E_USERNAME", "").strip()
    password = env.get("E2E_PASSWORD", "")

    if not username or not password:
        print("auth latency check skipped: E2E_USERNAME/E2E_PASSWORD are missing", file=sys.stderr)
        return 2

    login_samples: list[float] = []
    session_samples: list[float] = []
    had_warning = False

    for run in range(1, max(args.runs, 1) + 1):
        login_status, login_elapsed, login_payload = request_json(
            "POST",
            f"{base_url}/api/auth/login",
            payload={"username": username, "password": password},
            timeout=args.timeout,
        )
        print(f"login run={run} status={login_status} total={login_elapsed:.3f}s")
        if login_elapsed > args.warn_total_seconds:
            had_warning = True
        if login_status != 200:
            return 1

        token = str(login_payload.get("token") or "")
        if not token:
            print("auth latency check failed: login response did not include a token", file=sys.stderr)
            return 1
        login_samples.append(login_elapsed)

        session_status, session_elapsed, _ = request_json(
            "GET",
            f"{base_url}/api/auth/session",
            headers={"Authorization": f"Bearer {token}"},
            timeout=args.timeout,
        )
        print(f"session run={run} status={session_status} total={session_elapsed:.3f}s")
        if session_elapsed > args.warn_total_seconds:
            had_warning = True
        if session_status != 200:
            return 1
        session_samples.append(session_elapsed)

    print(summarize("login", login_samples))
    print(summarize("session", session_samples))
    if had_warning:
        print(f"warning: at least one request exceeded {args.warn_total_seconds:.3f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
