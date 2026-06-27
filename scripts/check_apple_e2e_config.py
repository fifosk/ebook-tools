#!/usr/bin/env python3
"""Validate Apple XCUITest configuration before starting Xcode."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_API_BASE_URL = "https://api.langtools.fifosk.synology.me"


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def resolve_config(env_file: Path) -> tuple[str, str, str]:
    file_values = load_env_file(env_file)
    username = os.environ.get("E2E_USERNAME") or file_values.get("E2E_USERNAME", "")
    password = os.environ.get("E2E_PASSWORD") or file_values.get("E2E_PASSWORD", "")
    api_base_url = (
        os.environ.get("E2E_API_BASE_URL")
        or file_values.get("E2E_API_BASE_URL")
        or DEFAULT_API_BASE_URL
    )
    return username.strip(), password.strip(), api_base_url.strip().rstrip("/")


def validate_config(env_file: Path) -> list[str]:
    username, password, api_base_url = resolve_config(env_file)
    errors: list[str] = []
    if not username:
        errors.append("E2E_USERNAME is required")
    if not password:
        errors.append("E2E_PASSWORD is required")
    parsed_url = urlparse(api_base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        errors.append("E2E_API_BASE_URL must be an absolute HTTP(S) URL")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env", help="Path to optional .env file")
    parser.add_argument("--profile", default="local", help="Apple E2E profile name for diagnostics")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env_file = Path(args.env_file)
    errors = validate_config(env_file)
    if errors:
        print(
            "Apple E2E config preflight failed "
            f"profile={args.profile} env_file={env_file}: " + "; ".join(errors)
        )
        return 2
    username, _, api_base_url = resolve_config(env_file)
    print(
        "Apple E2E config preflight passed "
        f"profile={args.profile} env_file={env_file} username={username} api_base_url={api_base_url}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
