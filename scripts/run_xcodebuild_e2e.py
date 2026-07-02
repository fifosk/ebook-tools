#!/usr/bin/env python3
"""Run an Xcode E2E command with a narrow retry for simulator service flakes."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


RETRYABLE_XCODE_SERVICE_PATTERNS = (
    "Failed to start remote service \"com.apple.mobile.notification_proxy\"",
    "Could not establish a secure connection to the device",
)


def is_retryable_xcode_service_failure(output: str) -> bool:
    """Return whether xcodebuild failed before app assertions on a known service flake."""

    return all(pattern in output for pattern in RETRYABLE_XCODE_SERVICE_PATTERNS)


def remove_paths(paths: list[Path]) -> None:
    for path in paths:
        if not path.exists() and not path.is_symlink():
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()


def tail_text(output: str, line_count: int) -> str:
    lines = output.splitlines()
    if line_count <= 0 or len(lines) <= line_count:
        return output.rstrip()
    return "\n".join(lines[-line_count:])


def run_attempt(command: list[str]) -> tuple[int, str]:
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return process.returncode, process.stdout


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run xcodebuild E2E with a retry for known Xcode/CoreDevice service flakes."
    )
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--tail-lines", type=int, default=30)
    parser.add_argument("--cleanup-path", action="append", default=[])
    parser.add_argument("--label", default="xcodebuild E2E")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("a command must follow --")
    args.attempts = max(1, args.attempts)
    args.cleanup_path = [Path(path) for path in args.cleanup_path]
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    last_output = ""
    last_status = 0

    for attempt in range(1, args.attempts + 1):
        if attempt > 1:
            remove_paths(args.cleanup_path)
        last_status, last_output = run_attempt(args.command)
        if last_status == 0:
            trimmed = tail_text(last_output, args.tail_lines)
            if trimmed:
                print(trimmed)
            return 0
        should_retry = (
            attempt < args.attempts
            and is_retryable_xcode_service_failure(last_output)
        )
        trimmed = tail_text(last_output, args.tail_lines)
        if trimmed:
            print(trimmed)
        if should_retry:
            print(
                f"{args.label} failed on a retryable Xcode service error; "
                f"retrying attempt {attempt + 1}/{args.attempts}.",
                file=sys.stderr,
            )
            continue
        return last_status

    return last_status


if __name__ == "__main__":
    raise SystemExit(main())
