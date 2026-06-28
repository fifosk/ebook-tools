#!/usr/bin/env python3
"""Validate ebook-tools app-owned Apple pipeline manifest handoffs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


DEFAULT_PIPELINE_ROOT = Path("/Users/fifo/Projects/home/apple-device-app-pipeline")
DEFAULT_APP_ID = "ebook-tools"
REQUIRED_TOKEN_KEYS = ("E2E_AUTH_TOKEN", "EBOOKTOOLS_SESSION_TOKEN")
REQUIRED_FIELDS = ("credentialEnvironment", "remoteEnvironmentAllowlist")


def resolve_pipeline_root(raw: str | None = None) -> Path:
    if raw:
        return Path(raw).expanduser()
    return Path(os.environ.get("APPLE_PIPELINE_ROOT", DEFAULT_PIPELINE_ROOT)).expanduser()


def manifest_path(pipeline_root: Path, app_id: str = DEFAULT_APP_ID) -> Path:
    return pipeline_root / "apps" / f"{app_id}.json"


def validate_manifest_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    contract = payload.get("simulatorContract")
    if not isinstance(contract, dict):
        return ["simulatorContract must be an object"]

    for field in REQUIRED_FIELDS:
        values = contract.get(field)
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            errors.append(f"simulatorContract.{field} must be a string list")
            continue
        missing = [key for key in REQUIRED_TOKEN_KEYS if key not in values]
        if missing:
            errors.append(
                f"simulatorContract.{field} missing token env keys: {', '.join(missing)}"
            )
    return errors


def validate_manifest(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"{path} is not valid JSON: {error}"]
    if not isinstance(payload, dict):
        return [f"{path} must contain a JSON object"]
    return validate_manifest_payload(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pipeline-root",
        default=None,
        help="Path to the shared apple-device-app-pipeline checkout.",
    )
    parser.add_argument(
        "--app",
        default=DEFAULT_APP_ID,
        help="Shared pipeline app manifest id.",
    )
    parser.add_argument(
        "--require",
        action="store_true",
        help="Fail instead of skipping when the shared pipeline manifest is absent.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = manifest_path(resolve_pipeline_root(args.pipeline_root), args.app)
    if not path.exists():
        message = f"apple shared pipeline manifest not found: {path}"
        if args.require:
            print(f"ERROR: {message}", file=sys.stderr)
            return 1
        print(f"apple shared pipeline manifest token env checks skipped: {message}")
        return 0

    errors = validate_manifest(path)
    if errors:
        print(f"apple shared pipeline manifest token env checks failed: {path}", file=sys.stderr)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"apple shared pipeline manifest token env checks passed: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
