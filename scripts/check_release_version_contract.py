#!/usr/bin/env python3
"""Validate ebook-tools Apple release version and changelog consistency."""

from __future__ import annotations

import json
import plistlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}\.\d+$")


def read_plist_version(path: Path) -> str:
    with path.open("rb") as handle:
        payload = plistlib.load(handle)
    value = str(payload.get("EBOOK_TOOLS_RELEASE_VERSION", "")).strip()
    if not value:
        raise AssertionError(f"{path} is missing EBOOK_TOOLS_RELEASE_VERSION")
    return value


def read_plist(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return plistlib.load(handle)


def expected_marketing_version(release: str) -> str:
    year, month, day, _ = release.split(".")
    return f"{int(year)}.{int(month)}.{int(day)}"


def expected_bundle_version(release: str) -> str:
    year, month, day, build = release.split(".")
    return f"{year}{month}{day}{build}"


def assert_apple_bundle_versions(path: Path, release: str) -> None:
    payload = read_plist(path)
    expected_short = expected_marketing_version(release)
    expected_build = expected_bundle_version(release)
    actual_short = str(payload.get("CFBundleShortVersionString", "")).strip()
    actual_build = str(payload.get("CFBundleVersion", "")).strip()
    if actual_short != expected_short:
        raise AssertionError(
            f"{path} CFBundleShortVersionString={actual_short!r}, expected {expected_short!r}"
        )
    if actual_build != expected_build:
        raise AssertionError(
            f"{path} CFBundleVersion={actual_build!r}, expected {expected_build!r}"
        )


def assert_xcode_build_versions(path: Path, release: str) -> None:
    text = path.read_text(encoding="utf-8")
    expected_short = expected_marketing_version(release)
    expected_build = expected_bundle_version(release)
    stale_patterns = [
        (r"CURRENT_PROJECT_VERSION = 1;", "stale CURRENT_PROJECT_VERSION=1"),
        (r"MARKETING_VERSION = 1\.0;", "stale MARKETING_VERSION=1.0"),
    ]
    for pattern, description in stale_patterns:
        if re.search(pattern, text):
            raise AssertionError(f"{path} contains {description}")
    if f"CURRENT_PROJECT_VERSION = {expected_build};" not in text:
        raise AssertionError(
            f"{path} is missing CURRENT_PROJECT_VERSION = {expected_build};"
        )
    if f"MARKETING_VERSION = {expected_short};" not in text:
        raise AssertionError(
            f"{path} is missing MARKETING_VERSION = {expected_short};"
        )


def require_contains(path: Path, pattern: str, description: str) -> None:
    text = path.read_text(encoding="utf-8")
    if not re.search(pattern, text, re.MULTILINE):
        raise AssertionError(f"{path} is missing {description}")


def latest_changelog_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^###\s+(\d{4}\.\d{2}\.\d{2}\.\d+)\s*$", text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"{path} is missing a YYYY.MM.DD.xx version heading")
    return match.group(1)


def assert_journey_checks_version_badge(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    has_visible_assertion = False
    has_frame_assertion = False
    for step in payload.get("steps", []):
        if step.get("action") == "assert_visible" and step.get("selector") == "appVersionBadge":
            has_visible_assertion = True
        if step.get("action") == "assert_frame" and step.get("selector") == "appVersionBadge":
            has_frame_assertion = True
            if float(step.get("min_width", 0)) < 72:
                raise AssertionError(f"{path} appVersionBadge frame assertion min_width is too low")
            if float(step.get("min_aspect_ratio", 0)) < 2.0:
                raise AssertionError(f"{path} appVersionBadge frame assertion min_aspect_ratio is too low")
    if not has_visible_assertion:
        raise AssertionError(f"{path} does not assert appVersionBadge visibility")
    if not has_frame_assertion:
        raise AssertionError(f"{path} does not assert appVersionBadge frame geometry")


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
    for plist_path in [
        root / "ios/InteractiveReader/InteractiveReader/Supporting/Info.plist",
        root / "ios/InteractiveReader/InteractiveReader/Supporting/Info-tvOS.plist",
        root / "ios/InteractiveReader/NotificationServiceExtension/Info.plist",
    ]:
        assert_apple_bundle_versions(plist_path, release)
    assert_xcode_build_versions(
        root / "ios/InteractiveReader/InteractiveReader.xcodeproj/project.pbxproj",
        release,
    )

    app_version = root / "ios/InteractiveReader/InteractiveReader/Features/Shared/AppVersion.swift"
    changelog_sources = sorted(
        (root / "ios/InteractiveReader/InteractiveReader/Features/Shared").glob("AppChangelog*.swift")
    )
    require_contains(
        app_version,
        rf'readInfoValue\("EBOOK_TOOLS_RELEASE_VERSION"\) \?\? "{re.escape(release)}"',
        "AppVersion fallback release",
    )
    if not any(
        re.search(rf'version: "{re.escape(release)}"', path.read_text(encoding="utf-8"))
        for path in changelog_sources
    ):
        names = ", ".join(str(path.relative_to(root)) for path in changelog_sources)
        raise AssertionError(f"{names} are missing AppChangelog latest version")
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
