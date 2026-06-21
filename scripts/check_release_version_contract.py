#!/usr/bin/env python3
"""Validate ebook-tools Apple release version and changelog consistency."""

from __future__ import annotations

import json
import plistlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}\.\d{2}$")


def read_plist_version(path: Path) -> str:
    with path.open("rb") as handle:
        payload = plistlib.load(handle)
    value = str(payload.get("EBOOK_TOOLS_RELEASE_VERSION", "")).strip()
    if not value:
        raise AssertionError(f"{path} is missing EBOOK_TOOLS_RELEASE_VERSION")
    return value


def require_contains(path: Path, pattern: str, description: str) -> None:
    text = path.read_text(encoding="utf-8")
    if not re.search(pattern, text, re.MULTILINE):
        raise AssertionError(f"{path} is missing {description}")


def latest_changelog_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^###\s+(\d{4}\.\d{2}\.\d{2}\.\d{2})\s*$", text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"{path} is missing a YYYY.MM.DD.xx version heading")
    return match.group(1)


def assert_journey_checks_version_badge(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for step in payload.get("steps", []):
        if step.get("action") == "assert_visible" and step.get("selector") == "appVersionBadge":
            return
    raise AssertionError(f"{path} does not assert appVersionBadge visibility")


def validate(root: Path = ROOT) -> None:
    info_version = read_plist_version(
        root / "ios/InteractiveReader/InteractiveReader/Supporting/Info.plist"
    )
    tvos_version = read_plist_version(
        root / "ios/InteractiveReader/InteractiveReader/Supporting/Info-tvOS.plist"
    )
    changelog_version = latest_changelog_version(root / "CHANGELOG.md")

    versions = {
        "Info.plist": info_version,
        "Info-tvOS.plist": tvos_version,
        "CHANGELOG.md": changelog_version,
    }
    if len(set(versions.values())) != 1:
        details = ", ".join(f"{name}={version}" for name, version in versions.items())
        raise AssertionError(f"Release version mismatch: {details}")

    release = info_version
    if not VERSION_RE.fullmatch(release):
        raise AssertionError(f"Release version {release!r} does not match YYYY.MM.DD.xx")

    app_theme = root / "ios/InteractiveReader/InteractiveReader/Features/Shared/AppTheme.swift"
    require_contains(
        app_theme,
        rf'readInfoValue\("EBOOK_TOOLS_RELEASE_VERSION"\) \?\? "{re.escape(release)}"',
        "AppVersion fallback release",
    )
    require_contains(
        app_theme,
        rf'version: "{re.escape(release)}"',
        "AppChangelog latest version",
    )
    require_contains(
        root / "CHANGELOG.md",
        rf"`v{re.escape(release)}`",
        "visible version label entry",
    )
    assert_journey_checks_version_badge(root / "tests/e2e/journeys/basic_playback.json")


def main() -> int:
    try:
        validate()
    except AssertionError as exc:
        print(f"release version contract failed: {exc}", file=sys.stderr)
        return 1

    print("release version contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
