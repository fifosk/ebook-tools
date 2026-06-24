#!/usr/bin/env python3
"""Build installable iOS entitlements from a profile and project entitlements."""

from __future__ import annotations

import argparse
import plistlib
import subprocess
from pathlib import Path
from typing import Any


PROFILE_KEYS = (
    "application-identifier",
    "com.apple.developer.team-identifier",
    "get-task-allow",
    "keychain-access-groups",
)


def load_plist(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            payload = plistlib.load(handle)
    except Exception:
        decoded = subprocess.check_output(["security", "cms", "-D", "-i", str(path)])
        payload = plistlib.loads(decoded)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} did not contain a plist dictionary")
    return payload


def profile_entitlements(path: Path) -> dict[str, Any]:
    payload = load_plist(path)
    entitlements = payload.get("Entitlements")
    if not isinstance(entitlements, dict):
        raise ValueError(f"{path} does not contain Entitlements")
    return dict(entitlements)


def project_entitlements(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    payload = load_plist(path)
    return dict(payload)


def team_identifier(entitlements: dict[str, Any]) -> str:
    value = entitlements.get("com.apple.developer.team-identifier")
    if isinstance(value, str) and value:
        return value
    app_id = entitlements.get("application-identifier")
    if isinstance(app_id, str) and "." in app_id:
        return app_id.split(".", 1)[0]
    keychain_groups = entitlements.get("keychain-access-groups")
    if isinstance(keychain_groups, list) and keychain_groups:
        first = keychain_groups[0]
        if isinstance(first, str) and "." in first:
            return first.split(".", 1)[0]
    raise ValueError("Unable to determine team identifier from profile entitlements")


def expand_value(value: Any, *, team_id: str, bundle_id: str) -> Any:
    if isinstance(value, str):
        value = value.replace("$(TeamIdentifierPrefix)", f"{team_id}.")
        value = value.replace("$(AppIdentifierPrefix)", f"{team_id}.")
        value = value.replace("$(CFBundleIdentifier)", bundle_id)
        if value == f"{team_id}.*":
            return f"{team_id}.{bundle_id}"
        return value
    if isinstance(value, list):
        return [expand_value(item, team_id=team_id, bundle_id=bundle_id) for item in value]
    if isinstance(value, dict):
        return {
            key: expand_value(item, team_id=team_id, bundle_id=bundle_id)
            for key, item in value.items()
        }
    return value


def profile_value(entitlements: dict[str, Any], key: str, *, team_id: str, bundle_id: str) -> Any:
    if key == "application-identifier":
        value = entitlements.get(key) or f"{team_id}.{bundle_id}"
    elif key == "com.apple.developer.team-identifier":
        value = entitlements.get(key) or team_id
    elif key == "get-task-allow":
        value = entitlements.get(key, True)
    elif key == "keychain-access-groups":
        value = entitlements.get(key) or [f"{team_id}.{bundle_id}"]
    else:
        value = entitlements.get(key)
    return expand_value(value, team_id=team_id, bundle_id=bundle_id)


def merged_entitlements(
    *,
    profile: dict[str, Any],
    project: dict[str, Any],
    bundle_id: str,
) -> dict[str, Any]:
    team_id = team_identifier(profile)
    merged = expand_value(project, team_id=team_id, bundle_id=bundle_id)
    for key in PROFILE_KEYS:
        merged[key] = profile_value(profile, key, team_id=team_id, bundle_id=bundle_id)
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--bundle-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--project-entitlements", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile = profile_entitlements(args.profile)
    project = project_entitlements(args.project_entitlements)
    payload = merged_entitlements(
        profile=profile,
        project=project,
        bundle_id=args.bundle_id,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
