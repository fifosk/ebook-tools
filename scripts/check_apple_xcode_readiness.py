#!/usr/bin/env python3
"""Validate Xcode is ready before starting Apple simulator E2E runs."""

from __future__ import annotations

import argparse
import shutil
import subprocess


def resolve_xcodebuild(candidate: str) -> str | None:
    if "/" in candidate:
        return candidate if shutil.which(candidate) or candidate.startswith("/") else None
    return shutil.which(candidate)


def validate_xcodebuild(xcodebuild: str, timeout: int = 30) -> list[str]:
    resolved = resolve_xcodebuild(xcodebuild)
    if not resolved:
        return [f"xcodebuild not found at {xcodebuild}"]
    try:
        result = subprocess.run(
            [resolved, "-checkFirstLaunchStatus"],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return [f"xcodebuild not found at {resolved}"]
    except subprocess.TimeoutExpired:
        return [f"xcodebuild readiness check timed out after {timeout}s"]

    if result.returncode == 0:
        return []

    combined_output = "\n".join(
        part.strip() for part in (result.stdout, result.stderr) if part.strip()
    )
    lower_output = combined_output.lower()
    if "license" in lower_output:
        return [
            "Xcode license is not accepted; run "
            "'sudo xcodebuild -license' or 'sudo xcodebuild -runFirstLaunch' on this Mac"
        ]
    return [
        "Xcode first-launch tasks are incomplete; run "
        "'sudo xcodebuild -runFirstLaunch' on this Mac"
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--xcodebuild",
        default="/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild",
        help="Path to xcodebuild",
    )
    parser.add_argument("--profile", default="local", help="Apple E2E profile name")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors = validate_xcodebuild(args.xcodebuild)
    if errors:
        print(
            "Apple Xcode readiness preflight failed "
            f"profile={args.profile}: " + "; ".join(errors)
        )
        return 69
    print(
        "Apple Xcode readiness preflight passed "
        f"profile={args.profile} xcodebuild={args.xcodebuild}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
