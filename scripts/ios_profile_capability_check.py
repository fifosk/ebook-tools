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
        # The profile stores the concrete team prefix; for this diagnostic, the
        # capability key matters more than the generated prefix string.
        return isinstance(actual, str) and bool(actual.strip())
    return expected == actual


def matching_profiles(
    bundle_id: str,
    profile_dirs: list[Path],
    *,
    platform: str | None = "iOS",
) -> list[tuple[Path, dict[str, Any]]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for profile_dir in profile_dirs:
        if not profile_dir.exists():
            continue
        for profile in sorted(profile_dir.glob("*.mobileprovision")):
            payload = decode_mobileprovision(profile)
            if not payload:
                continue
            if profile_matches_bundle(payload, bundle_id) and profile_matches_platform(payload, platform):
                matches.append((profile, payload))
    return matches


def describe_profile(path: Path, payload: dict[str, Any]) -> str:
    name = payload.get("Name") or "<unnamed>"
    uuid = payload.get("UUID") or "<unknown-uuid>"
    team = ",".join(payload.get("TeamIdentifier") or []) or "<unknown-team>"
    platforms = ",".join(payload.get("Platform") or []) or "<unknown-platform>"
    expiration = payload.get("ExpirationDate")
    expires = expiration.date().isoformat() if expiration else "<unknown-expiry>"
    managed = " managed-by-xcode" if payload.get("IsXcodeManaged") else ""
    suffix = profile_bundle_suffix(payload) or "<unknown-app-id>"
    return (
        f"{name} uuid={uuid} app-id={suffix} team={team} "
        f"platforms={platforms} expires={expires}{managed} path={path}"
    )


def check_profiles_for_bundle(
    *,
    bundle_id: str,
    expected_entitlements: dict[str, Any],
    profile_dirs: list[Path],
    label: str,
    require_entitlement_values: bool,
    platform: str | None = "iOS",
) -> bool:
    expected_keys = sorted(
        key for key, value in expected_entitlements.items() if value not in (None, "", [])
    )
    profiles = matching_profiles(bundle_id, profile_dirs, platform=platform)

    if require_entitlement_values and not expected_keys:
        print(f"{label}: entitlement file declares no required capabilities.")
        return True

    if not profiles:
        platform_suffix = f" for platform {platform}" if platform else ""
        print(f"{label}: no local provisioning profile found{platform_suffix}.")
        if expected_keys:
            print(f"Required entitlement keys: {', '.join(expected_keys)}")
        return False

    any_compatible = False
    for path, payload in profiles:
        entitlements = payload.get("Entitlements") or {}
        missing = [key for key in expected_keys if key not in entitlements]
        mismatched = [
            key
            for key in expected_keys
            if key in entitlements and not value_satisfies(expected_entitlements[key], entitlements[key])
        ]
        print(f"Profile: {describe_profile(path, payload)}")
        if expected_keys:
            print(f"  present: {', '.join(key for key in expected_keys if key in entitlements) or 'none'}")
        else:
            print("  present: profile matches bundle id")
        if missing:
            print(f"  missing: {', '.join(missing)}")
        if mismatched:
            print(f"  mismatched values: {', '.join(mismatched)}")
        if not missing and not mismatched:
            suffix = profile_bundle_suffix(payload)
            if suffix != bundle_id:
                print(f"  match: wildcard profile covers {bundle_id}")
            print("  result: compatible")
            any_compatible = True
        else:
            print("  result: not compatible")

    return any_compatible


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-id", required=True, help="Product bundle identifier to match.")
    parser.add_argument("--entitlements", required=True, type=Path, help="Path to the app entitlements plist.")
    parser.add_argument(
        "--platform",
        default="iOS",
        help="Provisioning profile platform to accept, default: iOS. Pass an empty string to disable filtering.",
    )
    parser.add_argument(
        "--embedded-bundle-id",
        action="append",
        default=[],
        help=(
            "Embedded extension bundle identifier that must have a matching local profile. "
            "Repeat for multiple embedded bundles."
        ),
    )
    parser.add_argument(
        "--profile-dir",
        action="append",
        type=Path,
        default=[],
        help="Directory containing .mobileprovision files. Defaults to common Xcode profile caches.",
    )
    args = parser.parse_args()

    expected_entitlements = load_plist(args.entitlements)
    profile_dirs = args.profile_dir or DEFAULT_PROFILE_DIRS
    platform = args.platform.strip() or None
    ok = check_profiles_for_bundle(
        bundle_id=args.bundle_id,
        expected_entitlements=expected_entitlements,
        profile_dirs=profile_dirs,
        label=args.bundle_id,
        require_entitlement_values=True,
        platform=platform,
    )
    for embedded_bundle_id in args.embedded_bundle_id:
        ok = check_profiles_for_bundle(
            bundle_id=embedded_bundle_id,
            expected_entitlements={},
            profile_dirs=profile_dirs,
            label=embedded_bundle_id,
            require_entitlement_values=False,
            platform=platform,
        ) and ok

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
