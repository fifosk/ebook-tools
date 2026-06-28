#!/usr/bin/env python3
"""Validate Xcode is ready before starting Apple simulator E2E runs."""

from __future__ import annotations

import argparse
import shutil
import subprocess


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(
        part.strip() for part in (result.stdout, result.stderr) if part.strip()
    )


def _is_license_failure(output: str) -> bool:
    lower_output = output.lower()
    return "license" in lower_output and (
        "not agreed" in lower_output
        or "agree" in lower_output
        or "accept" in lower_output
    )


def _attended_admin_hint() -> str:
    return (
        "If this check is running over SSH or CI, complete the command once "
        "in an attended admin terminal on that Mac, then rerun this preflight"
    )


def _license_failure_message() -> str:
    return (
        "Xcode license is not accepted; run "
        "'sudo xcodebuild -license' or 'sudo xcodebuild -runFirstLaunch' on this Mac. "
        + _attended_admin_hint()
    )


def _first_launch_failure_message() -> str:
    return (
        "Xcode first-launch tasks are incomplete; run "
        "'sudo xcodebuild -runFirstLaunch' on this Mac. "
        + _attended_admin_hint()
    )


def resolve_xcodebuild(candidate: str) -> str | None:
    if "/" in candidate:
        return candidate if shutil.which(candidate) or candidate.startswith("/") else None
    return shutil.which(candidate)


def run_xcodebuild_probe(resolved: str, args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [resolved, *args],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def validate_xcodebuild(xcodebuild: str, timeout: int = 30) -> list[str]:
    resolved = resolve_xcodebuild(xcodebuild)
    if not resolved:
        return [f"xcodebuild not found at {xcodebuild}"]
    try:
        license_result = run_xcodebuild_probe(resolved, ["-license", "check"], timeout)
        if license_result.returncode != 0:
            license_output = _combined_output(license_result)
            if _is_license_failure(license_output):
                return [_license_failure_message()]

        result = run_xcodebuild_probe(resolved, ["-checkFirstLaunchStatus"], timeout)
    except FileNotFoundError:
        return [f"xcodebuild not found at {resolved}"]
    except subprocess.TimeoutExpired:
        return [f"xcodebuild readiness check timed out after {timeout}s"]

    if result.returncode == 0:
        return []

    combined_output = _combined_output(result)
    if _is_license_failure(combined_output):
        return [_license_failure_message()]
    return [_first_launch_failure_message()]


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
