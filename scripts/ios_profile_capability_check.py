#!/usr/bin/env python3
"""Check local iOS provisioning profiles against an app entitlement file."""

from __future__ import annotations

import argparse
import plistlib
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_PROFILE_DIRS = [
    Path.home() / "Library/Developer/Xcode/UserData/Provisioning Profiles",
    Path.home() / "Library/MobileDevice/Provisioning Profiles",
]


def load_plist(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return plistlib.load(handle)


def decode_mobileprovision(path: Path) -> dict[str, Any] | None:
    result = subprocess.run(
        ["security", "cms", "-D", "-i", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return plistlib.loads(result.stdout)
    except plistlib.InvalidFileException:
        return None


def bundle_suffix(application_identifier: str) -> str:
    return application_identifier.split(".", 1)[1] if "." in application_identifier else application_identifier


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
        # The profile stores the concrete team prefix; for this diagnostic, the
        # capability key matters more than the generated prefix string.
        return isinstance(actual, str) and bool(actual.strip())
    return expected == actual


def matching_profiles(bundle_id: str, profile_dirs: list[Path]) -> list[tuple[Path, dict[str, Any]]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for profile_dir in profile_dirs:
        if not profile_dir.exists():
            continue
        for profile in sorted(profile_dir.glob("*.mobileprovision")):
            payload = decode_mobileprovision(profile)
            if not payload:
                continue
            entitlements = payload.get("Entitlements") or {}
            application_identifier = str(entitlements.get("application-identifier") or "")
            if bundle_suffix(application_identifier) == bundle_id:
                matches.append((profile, payload))
    return matches


def describe_profile(payload: dict[str, Any]) -> str:
    name = payload.get("Name") or "<unnamed>"
    team = ",".join(payload.get("TeamIdentifier") or []) or "<unknown-team>"
    expiration = payload.get("ExpirationDate")
    expires = expiration.date().isoformat() if expiration else "<unknown-expiry>"
    return f"{name} team={team} expires={expires}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-id", required=True, help="Product bundle identifier to match.")
    parser.add_argument("--entitlements", required=True, type=Path, help="Path to the app entitlements plist.")
    parser.add_argument(
        "--profile-dir",
        action="append",
        type=Path,
        default=[],
        help="Directory containing .mobileprovision files. Defaults to common Xcode profile caches.",
    )
    args = parser.parse_args()

    expected_entitlements = load_plist(args.entitlements)
    expected_keys = sorted(key for key, value in expected_entitlements.items() if value not in (None, "", []))
    profile_dirs = args.profile_dir or DEFAULT_PROFILE_DIRS
    profiles = matching_profiles(args.bundle_id, profile_dirs)

    if not expected_keys:
        print(f"{args.bundle_id}: entitlement file declares no required capabilities.")
        return 0

    if not profiles:
        print(f"{args.bundle_id}: no local provisioning profile found.")
        print(f"Required entitlement keys: {', '.join(expected_keys)}")
        return 1

    any_compatible = False
    for _path, payload in profiles:
        entitlements = payload.get("Entitlements") or {}
        missing = [key for key in expected_keys if key not in entitlements]
        mismatched = [
            key
            for key in expected_keys
            if key in entitlements and not value_satisfies(expected_entitlements[key], entitlements[key])
        ]
        print(f"Profile: {describe_profile(payload)}")
        print(f"  present: {', '.join(key for key in expected_keys if key in entitlements) or 'none'}")
        if missing:
            print(f"  missing: {', '.join(missing)}")
        if mismatched:
            print(f"  mismatched values: {', '.join(mismatched)}")
        if not missing and not mismatched:
            print("  result: capability-compatible with declared entitlements")
            any_compatible = True
        else:
            print("  result: not compatible")

    return 0 if any_compatible else 1


if __name__ == "__main__":
    raise SystemExit(main())
