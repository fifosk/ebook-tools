#!/usr/bin/env python3
"""Validate ebook-tools app-owned Apple pipeline manifest handoffs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = REPO_ROOT / "Makefile"
DEFAULT_PIPELINE_ROOT = Path("/Users/fifo/Projects/home/apple-device-app-pipeline")
DEFAULT_APP_ID = "ebook-tools"
REQUIRED_TOKEN_KEYS = ("E2E_AUTH_TOKEN", "EBOOKTOOLS_SESSION_TOKEN")
REQUIRED_FIELDS = ("credentialEnvironment", "remoteEnvironmentAllowlist")
REQUIRED_APP_OWNED_JOURNEYS = (
    "apple-e2e-journeys",
    "iphone",
    "ipados",
    "tvos",
    "iphone-create",
    "ipados-create",
    "tvos-create",
    "ipados-music-bed-sync",
    "tvos-music-bed-sync",
    "ios-uitests-build",
    "tvos-uitests-build",
    "macos-ipad-style",
    "macos-ipad-style-dry-run",
    "runtime-xcode-readiness",
)
REQUIRED_SIMULATOR_PROFILES = ("ios", "ipados", "tvos", "tvos-cinema")
REQUIRED_DEVICE_PROFILES = ("iphone", "ipad", "appletv", "cinema")
REQUIRED_IOS_DEVICE_CAPABILITIES = (
    "Push Notifications",
    "Sign In with Apple",
    "iCloud",
)
REQUIRED_SIM_ENV = "INTERACTIVE_READER_API_BASE_URL"
REQUIRED_BACKEND_TARGETS = (
    "test-backend-auth-session",
    "test-backend-library-search-source-isbn",
    "test-backend-admin-system-status",
    "test-backend-pipeline-jobs",
    "test-backend-runtime-descriptor",
    "test-backend-create-book",
    "test-backend-creation-templates",
    "test-backend-pipeline-sources",
    "test-backend-acquisition",
    "test-backend-audio-routes",
    "test-backend-reading-beds",
    "test-backend-notifications",
    "test-backend-subtitle-router",
    "test-backend-playback-state",
    "test-backend-playback-media",
    "test-backend-offline-export",
    "test-backend-youtube-dubbing-service",
)
REQUIRED_WEB_TARGETS = (
    "test-web-auth-focused",
    "test-web-admin-focused",
    "test-web-sidebar-focused",
    "test-web-create-book-focused",
    "test-web-create-intake-focused",
    "test-web-creation-templates-focused",
    "test-web-library-focused",
    "test-web-job-progress-focused",
    "test-web-playback-focused",
    "test-web-video-dubbing-focused",
    "test-web-subtitle-tool-focused",
    "test-web-app-view-deeplink-focused",
    "test-web-full",
    "build-web-production",
)
REQUIRED_APPLE_CONTRACT_TARGETS = (
    "test-apple-language-catalogs",
    "test-apple-create-readiness-contract",
    "test-apple-local-surface-contract",
    "test-apple-playback-state-swift",
    "test-apple-contracts",
)


def resolve_pipeline_root(raw: str | None = None) -> Path:
    if raw:
        return Path(raw).expanduser()
    return Path(os.environ.get("APPLE_PIPELINE_ROOT", DEFAULT_PIPELINE_ROOT)).expanduser()


def manifest_path(pipeline_root: Path, app_id: str = DEFAULT_APP_ID) -> Path:
    return pipeline_root / "apps" / f"{app_id}.json"


def validate_manifest_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    make_targets = _load_make_targets()
    contract = payload.get("simulatorContract")
    if not isinstance(contract, dict):
        errors.append("simulatorContract must be an object")
        contract = {}

    for field in REQUIRED_FIELDS:
        values = contract.get(field)
        if not isinstance(values, list) or not all(
            isinstance(item, str) for item in values
        ):
            errors.append(f"simulatorContract.{field} must be a string list")
            continue
        missing = [key for key in REQUIRED_TOKEN_KEYS if key not in values]
        if missing:
            errors.append(
                f"simulatorContract.{field} missing token env keys: {', '.join(missing)}"
            )
    errors.extend(_validate_app_owned_journeys(payload, make_targets=make_targets))
    errors.extend(
        _validate_command_section(
            payload,
            section_name="backendTestChecks",
            required_targets=REQUIRED_BACKEND_TARGETS,
            make_targets=make_targets,
        )
    )
    errors.extend(
        _validate_command_section(
            payload,
            section_name="webChecks",
            required_targets=REQUIRED_WEB_TARGETS,
            make_targets=make_targets,
        )
    )
    errors.extend(
        _validate_command_section(
            payload,
            section_name="contractChecks",
            required_targets=REQUIRED_APPLE_CONTRACT_TARGETS,
            make_targets=make_targets,
        )
    )
    errors.extend(_validate_simulator_profiles(payload))
    errors.extend(_validate_device_profiles(payload))
    errors.extend(_validate_known_gates(payload))
    return errors


def _validate_app_owned_journeys(
    payload: dict[str, Any],
    *,
    make_targets: set[str],
) -> list[str]:
    errors: list[str] = []
    journeys = payload.get("appOwnedJourneys")
    if not isinstance(journeys, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in (journeys or {}).items()
    ):
        return ["appOwnedJourneys must be a string map"]

    missing = [
        profile for profile in REQUIRED_APP_OWNED_JOURNEYS if profile not in journeys
    ]
    if missing:
        errors.append(f"appOwnedJourneys missing profiles: {', '.join(missing)}")

    aggregate_profiles = _load_make_variable_words("APPLE_PIPELINE_JOURNEY_PROFILES")
    if not aggregate_profiles:
        errors.append("APPLE_PIPELINE_JOURNEY_PROFILES must list app-owned journeys")
    else:
        missing_from_make = [
            profile for profile in journeys if profile not in aggregate_profiles
        ]
        unknown_make_profiles = [
            profile for profile in aggregate_profiles if profile not in journeys
        ]
        if missing_from_make:
            errors.append(
                "APPLE_PIPELINE_JOURNEY_PROFILES missing appOwnedJourneys: "
                + ", ".join(missing_from_make)
            )
        if unknown_make_profiles:
            errors.append(
                "APPLE_PIPELINE_JOURNEY_PROFILES references unknown journeys: "
                + ", ".join(unknown_make_profiles)
            )

    default_profile = _load_make_variable_words("APPLE_PIPELINE_JOURNEY_PROFILE")
    if len(default_profile) != 1:
        errors.append("APPLE_PIPELINE_JOURNEY_PROFILE must name one app-owned journey")
    else:
        default = default_profile[0]
        if default not in journeys:
            errors.append(
                f"APPLE_PIPELINE_JOURNEY_PROFILE references unknown journey: {default}"
            )
        elif aggregate_profiles and default not in aggregate_profiles:
            errors.append(
                "APPLE_PIPELINE_JOURNEY_PROFILE must be included in "
                f"APPLE_PIPELINE_JOURNEY_PROFILES: {default}"
            )

    for profile, command in journeys.items():
        if not command.startswith("make "):
            errors.append(f"appOwnedJourneys.{profile} must call a repo-owned make target")
            continue
        command_parts = command.split()
        target = command_parts[1] if len(command_parts) >= 2 else ""
        if target not in make_targets:
            errors.append(
                f"appOwnedJourneys.{profile} target is not defined in Makefile: {target}"
            )

    credential_free = payload.get("credentialFreeAppOwnedJourneys")
    if not isinstance(credential_free, list) or not all(
        isinstance(profile, str) for profile in credential_free
    ):
        errors.append("credentialFreeAppOwnedJourneys must be a string list")
        return errors

    unknown = [profile for profile in credential_free if profile not in journeys]
    if unknown:
        errors.append(
            "credentialFreeAppOwnedJourneys references unknown profiles: "
            + ", ".join(unknown)
        )
    if "apple-e2e-journeys" not in credential_free:
        errors.append("credentialFreeAppOwnedJourneys must include apple-e2e-journeys")
    return errors


def _validate_command_section(
    payload: dict[str, Any],
    *,
    section_name: str,
    required_targets: tuple[str, ...],
    make_targets: set[str],
) -> list[str]:
    section = payload.get(section_name)
    if not isinstance(section, dict):
        return [f"{section_name} must be an object"]
    commands = section.get("commands")
    if not isinstance(commands, list) or not commands:
        return [f"{section_name}.commands must be a non-empty list"]

    errors: list[str] = []
    command_targets: list[str] = []
    command_names: set[str] = set()
    for index, entry in enumerate(commands):
        prefix = f"{section_name}.commands[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"{prefix}.name must be a non-empty string")
        elif name in command_names:
            errors.append(f"{section_name}.commands contains duplicate name: {name}")
        else:
            command_names.add(name)

        command = entry.get("command")
        if (
            not isinstance(command, list)
            or len(command) != 2
            or command[0] != "make"
            or not isinstance(command[1], str)
            or not command[1]
        ):
            errors.append(f"{prefix}.command must be ['make', '<target>']")
            continue
        command_targets.append(command[1])
        if command[1] not in make_targets:
            errors.append(
                f"{prefix}.command target is not defined in Makefile: {command[1]}"
            )

    missing = [target for target in required_targets if target not in command_targets]
    if missing:
        errors.append(
            f"{section_name}.commands missing make targets: {', '.join(missing)}"
        )
    return errors


def _load_make_targets() -> set[str]:
    try:
        source = MAKEFILE.read_text(encoding="utf-8")
    except OSError:
        return set()
    targets: set[str] = set()
    for line in source.splitlines():
        if line.startswith(("\t", " ", "#", ".")):
            continue
        match = re.match(r"^([A-Za-z0-9_.%/-]+):(?:\s|$)", line)
        if match:
            targets.add(match.group(1))
    return targets


def _load_make_variable_words(name: str) -> list[str]:
    try:
        source = MAKEFILE.read_text(encoding="utf-8")
    except OSError:
        return []
    match = re.search(
        rf"^{re.escape(name)}\s*(?:\?=|:=|=)\s*(.*(?:\\\n[^\n]*)*)",
        source,
        re.MULTILINE,
    )
    if not match:
        return []
    raw_value = match.group(1).replace("\\\n", " ")
    return raw_value.split()


def _validate_simulator_profiles(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        return ["profiles must be an object"]

    missing = [profile for profile in REQUIRED_SIMULATOR_PROFILES if profile not in profiles]
    if missing:
        errors.append(f"profiles missing simulator profiles: {', '.join(missing)}")

    aggregate_profiles = _load_make_variable_words("APPLE_PIPELINE_SMOKE_PROFILES")
    if not aggregate_profiles:
        errors.append("APPLE_PIPELINE_SMOKE_PROFILES must list simulator smoke profiles")
    else:
        missing_from_make = [
            profile for profile in profiles if profile not in aggregate_profiles
        ]
        unknown_make_profiles = [
            profile for profile in aggregate_profiles if profile not in profiles
        ]
        if missing_from_make:
            errors.append(
                "APPLE_PIPELINE_SMOKE_PROFILES missing simulator profiles: "
                + ", ".join(missing_from_make)
            )
        if unknown_make_profiles:
            errors.append(
                "APPLE_PIPELINE_SMOKE_PROFILES references unknown simulator profiles: "
                + ", ".join(unknown_make_profiles)
            )

    default_profile = _load_make_variable_words("APPLE_PIPELINE_SMOKE_PROFILE")
    if len(default_profile) != 1:
        errors.append("APPLE_PIPELINE_SMOKE_PROFILE must name one simulator smoke profile")
    else:
        default = default_profile[0]
        if default not in profiles:
            errors.append(
                f"APPLE_PIPELINE_SMOKE_PROFILE references unknown simulator profile: {default}"
            )
        elif aggregate_profiles and default not in aggregate_profiles:
            errors.append(
                "APPLE_PIPELINE_SMOKE_PROFILE must be included in "
                f"APPLE_PIPELINE_SMOKE_PROFILES: {default}"
            )

    for profile in REQUIRED_SIMULATOR_PROFILES:
        details = profiles.get(profile)
        if not isinstance(details, dict):
            continue
        for field in (
            "platform",
            "project",
            "target",
            "productName",
            "bundleId",
            "buildRoot",
            "simulator",
            "simulatorRuntimeVersion",
        ):
            if not isinstance(details.get(field), str) or not details[field]:
                errors.append(f"profiles.{profile}.{field} must be a non-empty string")
        if details.get("stageAppForInstall") is not False:
            errors.append(f"profiles.{profile}.stageAppForInstall must be false")
        required_env = details.get("requiredSimEnv")
        if not isinstance(required_env, list) or REQUIRED_SIM_ENV not in required_env:
            errors.append(
                f"profiles.{profile}.requiredSimEnv must include {REQUIRED_SIM_ENV}"
            )
    return errors


def _validate_device_profiles(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    device_profiles = payload.get("deviceProfiles")
    if not isinstance(device_profiles, dict):
        return ["deviceProfiles must be an object"]

    missing = [profile for profile in REQUIRED_DEVICE_PROFILES if profile not in device_profiles]
    if missing:
        errors.append(f"deviceProfiles missing physical profiles: {', '.join(missing)}")

    simulator_profiles = (
        payload.get("profiles") if isinstance(payload.get("profiles"), dict) else {}
    )
    for profile in REQUIRED_DEVICE_PROFILES:
        details = device_profiles.get(profile)
        if not isinstance(details, dict):
            continue
        for field in (
            "device",
            "platform",
            "project",
            "target",
            "productName",
            "bundleId",
            "deviceSdk",
            "buildRoot",
            "configuration",
            "simulatorSmokeProfile",
        ):
            if not isinstance(details.get(field), str) or not details[field]:
                errors.append(
                    f"deviceProfiles.{profile}.{field} must be a non-empty string"
                )
        smoke_profile = details.get("simulatorSmokeProfile")
        if isinstance(smoke_profile, str) and smoke_profile not in simulator_profiles:
            errors.append(
                f"deviceProfiles.{profile}.simulatorSmokeProfile references unknown profile {smoke_profile}"
            )
        if profile in {"iphone", "ipad"}:
            capabilities = details.get("requiredCapabilities")
            missing_capabilities = [
                capability
                for capability in REQUIRED_IOS_DEVICE_CAPABILITIES
                if not isinstance(capabilities, list) or capability not in capabilities
            ]
            if missing_capabilities:
                errors.append(
                    f"deviceProfiles.{profile}.requiredCapabilities missing: "
                    + ", ".join(missing_capabilities)
                )
    return errors


def _validate_known_gates(payload: dict[str, Any]) -> list[str]:
    known_gates = payload.get("knownGates")
    if not isinstance(known_gates, list) or not all(
        isinstance(item, str) for item in known_gates
    ):
        return ["knownGates must be a string list"]

    gates = "\n".join(known_gates)
    errors: list[str] = []
    for phrase in (
        "Physical Apple TV deployment is attended and on-request only",
        "Physical iPhone/iPad deployment is attended and on-request only",
        "recursive development loops stop at simulator and build-only proof",
        "authenticated Xcode account and provisioning profiles",
    ):
        if phrase not in gates:
            errors.append(f"knownGates missing required deployment guard: {phrase}")
    return errors


def validate_manifest(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"{path} is not valid JSON: {error}"]
    if not isinstance(payload, dict):
        return [f"{path} must contain a JSON object"]
    return validate_manifest_payload(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pipeline-root",
        default=None,
        help="Path to the shared apple-device-app-pipeline checkout.",
    )
    parser.add_argument(
        "--app",
        default=DEFAULT_APP_ID,
        help="Shared pipeline app manifest id.",
    )
    parser.add_argument(
        "--require",
        action="store_true",
        help="Fail instead of skipping when the shared pipeline manifest is absent.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = manifest_path(resolve_pipeline_root(args.pipeline_root), args.app)
    if not path.exists():
        message = f"apple shared pipeline manifest not found: {path}"
        if args.require:
            print(f"ERROR: {message}", file=sys.stderr)
            return 1
        print(f"apple shared pipeline manifest contract checks skipped: {message}")
        return 0

    errors = validate_manifest(path)
    if errors:
        print(
            f"apple shared pipeline manifest contract checks failed: {path}",
            file=sys.stderr,
        )
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"apple shared pipeline manifest contract checks passed: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
