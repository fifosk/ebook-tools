#!/usr/bin/env python3
"""Verify Apple app bundles carry current git build metadata stamps."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _git_value(args: list[str]) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def _read_stamp(app_bundle: Path, name: str) -> str | None:
    try:
        return (app_bundle / name).read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return None


def verify_bundle(
    app_bundle: Path,
    *,
    expected_branch: str | None = None,
    expected_commit: str | None = None,
) -> list[str]:
    if not app_bundle.is_dir():
        return [f"Apple app bundle does not exist: {app_bundle}"]

    expected_branch = expected_branch or _git_value(["rev-parse", "--abbrev-ref", "HEAD"])
    expected_commit = expected_commit or _git_value(["rev-parse", "--short=12", "HEAD"])
    branch = _read_stamp(app_bundle, "branch.stamp")
    commit = _read_stamp(app_bundle, "commit.stamp")

    failures: list[str] = []
    if not branch:
        failures.append(f"Apple app bundle missing branch.stamp: {app_bundle}")
    elif branch != expected_branch:
        failures.append(f"Apple app bundle branch.stamp {branch} does not match {expected_branch}")

    if not commit:
        failures.append(f"Apple app bundle missing commit.stamp: {app_bundle}")
    elif commit != expected_commit:
        failures.append(f"Apple app bundle commit.stamp {commit} does not match {expected_commit}")

    return failures


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, type=Path, help="Built .app bundle to verify.")
    parser.add_argument("--branch", default="", help="Expected branch; defaults to current git branch.")
    parser.add_argument("--commit", default="", help="Expected commit; defaults to current git short SHA.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    failures = verify_bundle(
        args.app,
        expected_branch=args.branch.strip() or None,
        expected_commit=args.commit.strip() or None,
    )
    if failures:
        print("Apple build metadata validation failed", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"Apple build metadata validated: {args.app}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
