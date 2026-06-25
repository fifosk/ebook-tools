#!/usr/bin/env python3
"""Find a compatible local Apple provisioning profile."""

from __future__ import annotations

import argparse
import datetime as dt
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_PROFILE_DIRS = [
    Path.home() / "Library/Developer/Xcode/UserData/Provisioning Profiles",
    Path.home() / "Library/MobileDevice/Provisioning Profiles",
]


def load_plist(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("rb") as handle:
            payload = plistlib.load(handle)
        return payload if isinstance(payload, dict) else None
    except Exception:
        result = subprocess.run(
            ["security", "cms", "-D", "-i", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            return None
        try:
            payload = plistlib.loads(result.stdout)
        except plistlib.InvalidFileException:
            return None
        return payload if isinstance(payload, dict) else None


def load_required_plist(path: Path) -> dict[str, Any]:
    payload = load_plist(path)
    if payload is None:
        raise ValueError(f"{path} did not contain a readable plist")
    return payload


def bundle_suffix(application_identifier: str) -> str:
    return application_identifier.split(".", 1)[1] if "." in application_identifier else application_identifier


def profile_bundle_suffix(payload: dict[str, Any]) -> str:
    entitlements = payload.get("Entitlements") or {}
    application_identifier = str(entitlements.get("application-identifier") or "")
    return bundle_suffix(application_identifier)


def profile_matches_bundle(payload: dict[str, Any], bundle_id: str) -> bool:
    suffix = profile_bundle_suffix(payload)
    if suffix == bundle_id:
        return True
    if suffix == "*":
        return True
    if suffix.endswith(".*"):
        return bundle_id.startswith(suffix[:-1])
    return False


def profile_matches_platform(payload: dict[str, Any], platform: str | None) -> bool:
    if not platform:
        return True
    platforms = [str(item).lower() for item in payload.get("Platform") or []]
    return platform.lower() in platforms


def value_satisfies(expected: Any, actual: Any) -> bool:
    if expected in (None, "", []):
        return True
    if actual == "*":
        return True
    if isinstance(expected, list):
        if actual == "*":
            return True
        if not isinstance(actual, list):
            return False
        return set(str(item) for item in expected).issubset(str(item) for item in actual)
    if isinstance(expected, str) and "$(TeamIdentifierPrefix)" in expected:
        return isinstance(actual, str) and bool(actual.strip())
    return expected == actual


def profile_is_current(payload: dict[str, Any], now: dt.datetime) -> bool:
    expiration = payload.get("ExpirationDate")
    if not isinstance(expiration, dt.datetime):
        return True
    if expiration.tzinfo is not None:
        now = now.replace(tzinfo=expiration.tzinfo)
    return expiration > now


def compatibility_errors(
    payload: dict[str, Any],
    *,
    bundle_id: str,
    platform: str | None,
    expected_entitlements: dict[str, Any],
    now: dt.datetime,
) -> list[str]:
    errors: list[str] = []
    if not profile_matches_platform(payload, platform):
        errors.append("platform")
    if not profile_matches_bundle(payload, bundle_id):
        errors.append("bundle")
    if not profile_is_current(payload, now):
        errors.append("expired")

    profile_entitlements = payload.get("Entitlements") or {}
    expected_keys = sorted(
        key for key, value in expected_entitlements.items() if value not in (None, "", [])
    )
    missing = [key for key in expected_keys if key not in profile_entitlements]
    mismatched = [
        key
        for key in expected_keys
        if key in profile_entitlements
        and not value_satisfies(expected_entitlements[key], profile_entitlements[key])
    ]
    errors.extend(f"missing:{key}" for key in missing)
    errors.extend(f"mismatch:{key}" for key in mismatched)
    return errors


def profile_rank(path: Path, payload: dict[str, Any], bundle_id: str) -> tuple[int, dt.datetime, str]:
    suffix = profile_bundle_suffix(payload)
    if suffix == bundle_id:
        specificity = 3
    elif suffix != "*" and suffix.endswith(".*"):
        specificity = 2
    else:
        specificity = 1
    expiration = payload.get("ExpirationDate")
    if not isinstance(expiration, dt.datetime):
        expiration = dt.datetime.min
    return (specificity, expiration, str(path))


def find_profile(
    *,
    bundle_id: str,
    platform: str | None,
    expected_entitlements: dict[str, Any],
    profile_dirs: list[Path],
) -> Path | None:
    now = dt.datetime.now()
    candidates: list[tuple[tuple[int, dt.datetime, str], Path]] = []
    for profile_dir in profile_dirs:
        if not profile_dir.exists():
            continue
        for profile in sorted(profile_dir.glob("*.mobileprovision")):
            payload = load_plist(profile)
            if not payload:
                continue
            if compatibility_errors(
                payload,
                bundle_id=bundle_id,
                platform=platform,
                expected_entitlements=expected_entitlements,
                now=now,
            ):
                continue
            candidates.append((profile_rank(profile, payload, bundle_id), profile))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-id", required=True)
    parser.add_argument("--platform", default="iOS")
    parser.add_argument("--entitlements", type=Path)
    parser.add_argument(
        "--profile-dir",
        action="append",
        type=Path,
        default=[],
        help="Directory containing .mobileprovision files. Defaults to common Xcode profile caches.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    platform = args.platform.strip() or None
    try:
        expected_entitlements = load_required_plist(args.entitlements) if args.entitlements else {}
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    profile = find_profile(
        bundle_id=args.bundle_id,
        platform=platform,
        expected_entitlements=expected_entitlements,
        profile_dirs=args.profile_dir or DEFAULT_PROFILE_DIRS,
    )
    if profile is None:
        platform_label = f" platform={platform}" if platform else ""
        entitlement_label = f" entitlements={args.entitlements}" if args.entitlements else ""
        print(
            f"No compatible provisioning profile found for {args.bundle_id}"
            f"{platform_label}{entitlement_label}.",
            file=sys.stderr,
        )
        return 1
    print(profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
