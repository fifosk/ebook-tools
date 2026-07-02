#!/usr/bin/env python3
"""Validate ebook-tools app-owned Apple pipeline manifest handoffs."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = REPO_ROOT / "Makefile"
_RUNTIME_DESCRIPTOR_PATH = REPO_ROOT / "modules" / "webapi" / "runtime_descriptor.py"
_RUNTIME_DESCRIPTOR_SPEC = importlib.util.spec_from_file_location(
    "ebook_tools_runtime_descriptor",
    _RUNTIME_DESCRIPTOR_PATH,
)
if _RUNTIME_DESCRIPTOR_SPEC is None or _RUNTIME_DESCRIPTOR_SPEC.loader is None:
    raise RuntimeError(f"Unable to load runtime descriptor from {_RUNTIME_DESCRIPTOR_PATH}")
_runtime_descriptor = importlib.util.module_from_spec(_RUNTIME_DESCRIPTOR_SPEC)
_RUNTIME_DESCRIPTOR_SPEC.loader.exec_module(_runtime_descriptor)
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
REQUIRED_CREDENTIAL_FREE_APP_OWNED_JOURNEYS = (
    "apple-e2e-journeys",
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
REQUIRED_RELEASE_PLIST = "ios/InteractiveReader/InteractiveReader/Supporting/Info.plist"
REQUIRED_RELEASE_VERSION_KEY = "EBOOK_TOOLS_RELEASE_VERSION"
REQUIRED_RELEASE_VERSION_PREFIX = "v"
EXPECTED_SIMULATOR_PROFILE_CONTRACTS = {
    "ios": {
        "platform": "ios",
        "target": "InteractiveReader",
        "productName": "InteractiveReader",
        "bundleId": "com.example.InteractiveReader",
        "simulator": "iPhone 17 Pro",
        "simulatorRuntimeVersion": "26.5",
        "buildRootSuffix": "ebook-tools/build-sim-ios",
    },
    "ipados": {
        "platform": "ipados",
        "target": "InteractiveReader",
        "productName": "InteractiveReader",
        "bundleId": "com.example.InteractiveReader",
        "simulator": "iPad Pro 13-inch (M5)",
        "simulatorRuntimeVersion": "26.5",
        "buildRootSuffix": "ebook-tools/build-sim-ipados",
    },
    "tvos": {
        "platform": "tvos",
        "target": "InteractiveReaderTV",
        "productName": "InteractiveReaderTV",
        "bundleId": "com.example.InteractiveReader.tvos",
        "simulator": "Apple TV 4K (3rd generation)",
        "simulatorRuntimeVersion": "26.5",
        "buildRootSuffix": "ebook-tools/build-sim-tvos",
    },
    "tvos-cinema": {
        "platform": "tvos",
        "target": "InteractiveReaderTV",
        "productName": "InteractiveReaderTV",
        "bundleId": "com.example.InteractiveReader.tvos",
        "simulator": "Apple TV 4K (2nd generation)",
        "simulatorRuntimeVersion": "26.4",
        "buildRootSuffix": "ebook-tools/build-sim-tvos-cinema",
    },
}
EXPECTED_DEVICE_PROFILE_CONTRACTS = {
    "iphone": {
        "device": "Fifo iPhone",
        "platform": "ios",
        "target": "InteractiveReader",
        "productName": "InteractiveReader",
        "bundleId": "com.example.InteractiveReader",
        "deviceSdk": "iphoneos",
        "configuration": "Debug",
        "simulatorSmokeProfile": "ios",
        "buildRootSuffix": "ebook-tools/build-device-iphoneos",
        "embeddedBundleIds": ["com.example.InteractiveReader.NotificationServiceExtension"],
        "requiredCapabilities": list(REQUIRED_IOS_DEVICE_CAPABILITIES),
    },
    "ipad": {
        "device": "Fifo Ipad Pro",
        "platform": "ipados",
        "target": "InteractiveReader",
        "productName": "InteractiveReader",
        "bundleId": "com.example.InteractiveReader",
        "deviceSdk": "iphoneos",
        "configuration": "Debug",
        "simulatorSmokeProfile": "ipados",
        "buildRootSuffix": "ebook-tools/build-device-ipados",
        "embeddedBundleIds": ["com.example.InteractiveReader.NotificationServiceExtension"],
        "requiredCapabilities": list(REQUIRED_IOS_DEVICE_CAPABILITIES),
    },
    "appletv": {
        "device": "Living Room",
        "platform": "tvos",
        "target": "InteractiveReaderTV",
        "productName": "InteractiveReaderTV",
        "bundleId": "com.example.InteractiveReader.tvos",
        "deviceSdk": "appletvos",
        "configuration": "Debug",
        "simulatorSmokeProfile": "tvos",
        "buildRootSuffix": "ebook-tools/build-device-appletvos",
    },
    "cinema": {
        "device": "Cinema",
        "platform": "tvos",
        "target": "InteractiveReaderTV",
        "productName": "InteractiveReaderTV",
        "bundleId": "com.example.InteractiveReader.tvos",
        "deviceSdk": "appletvos",
        "configuration": "Debug",
        "simulatorSmokeProfile": "tvos-cinema",
        "buildRootSuffix": "ebook-tools/build-device-cinema-appletvos",
    },
}
REQUIRED_API_ENVIRONMENT = list(_runtime_descriptor.API_BASE_URL_ENVIRONMENT)
REQUIRED_CREDENTIAL_ENVIRONMENT = list(_runtime_descriptor.CREDENTIAL_ENVIRONMENT)
REQUIRED_REMOTE_ENVIRONMENT_ALLOWLIST = [
    *REQUIRED_CREDENTIAL_ENVIRONMENT,
    "E2E_API_BASE_URL",
]
REQUIRED_REMOTE_ENVIRONMENT_FILE = ".env"
REQUIRED_XCUITEST_CONFIG_FILE = (
    "/tmp/apple-device-app-pipeline/ebook-tools/{profile}/ios_e2e_config.json"
)
REQUIRED_XCUITEST_JOURNEY_FILE = (
    "/tmp/apple-device-app-pipeline/ebook-tools/{profile}/ios_e2e_journey.json"
)
REQUIRED_APP_LOCK_BYPASS = "none"
REQUIRED_BACKEND_HEALTH_PATH = "/_health"
REQUIRED_BACKEND_RUNTIME_PATH = "/api/system/runtime"
REQUIRED_BACKEND_CHECKS = (REQUIRED_BACKEND_HEALTH_PATH, REQUIRED_BACKEND_RUNTIME_PATH)
REQUIRED_BACKEND_CHECK_BASE_ENV = "INTERACTIVE_READER_API_BASE_URL"
REQUIRED_BACKEND_CHECK_TIMEOUT_SECONDS = 30
REQUIRED_SIM_ENV = "INTERACTIVE_READER_API_BASE_URL"
REQUIRED_REMOTE_STAGING_ROOT = "/Volumes/WD-1TB/Data/staging/ebook-tools"
REQUIRED_REMOTE_DISPOSABLE_ROOT = (
    "/Users/fifo/Library/Developer/XcodeBuildArtifacts/ebook-tools"
)
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
REQUIRED_BACKEND_GENERATED_PATHS = (".pytest_cache",)
REQUIRED_BACKEND_GENERATED_DIRECTORY_NAMES = ("__pycache__",)
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
REQUIRED_WEB_GENERATED_PATHS = ("web/dist", "web/export-dist")
REQUIRED_APPLE_CONTRACT_TARGETS = (
    "test-apple-language-catalogs",
    "test-apple-create-readiness-contract",
    "test-apple-local-surface-contract",
    "test-apple-playback-state-swift",
    "test-apple-contracts",
)
REQUIRED_BACKEND_RUNTIME_EXPECTED = {
    **{
        f"auth.{key}": value
        for key, value in _runtime_descriptor.AUTH_DESCRIPTOR.items()
    },
    **{
        f"clientConfig.{key}": list(value) if isinstance(value, tuple) else value
        for key, value in _runtime_descriptor.CLIENT_CONFIG_DESCRIPTOR.items()
    },
    **{
        f"applePipeline.{key}": list(value) if isinstance(value, tuple) else value
        for key, value in _runtime_descriptor.APPLE_PIPELINE_DESCRIPTOR.items()
    },
    **{
        f"pipelineJobs.{key}": value
        for key, value in _runtime_descriptor.PIPELINE_JOBS_DESCRIPTOR.items()
    },
    **{
        f"pipelineMedia.{key}": value
        for key, value in _runtime_descriptor.PIPELINE_MEDIA_DESCRIPTOR.items()
    },
    **{
        f"libraryActions.{key}": value
        for key, value in _runtime_descriptor.LIBRARY_ACTIONS_DESCRIPTOR.items()
    },
    **{
        f"playbackState.{key}": value
        for key, value in _runtime_descriptor.PLAYBACK_STATE_DESCRIPTOR.items()
    },
    **{
        f"offlineExports.{key}": list(value) if isinstance(value, tuple) else value
        for key, value in _runtime_descriptor.OFFLINE_EXPORTS_DESCRIPTOR.items()
    },
    **{
        f"creation.{key}": value
        for key, value in _runtime_descriptor.CREATION_DESCRIPTOR.items()
    },
    **{
        f"acquisition.{key}": list(value) if isinstance(value, tuple) else value
        for key, value in _runtime_descriptor.ACQUISITION_DESCRIPTOR.items()
    },
    **{
        f"linguist.{key}": value
        for key, value in _runtime_descriptor.LINGUIST_DESCRIPTOR.items()
    },
    **{
        f"notifications.{key}": value
        for key, value in _runtime_descriptor.NOTIFICATIONS_DESCRIPTOR.items()
    },
}


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
    errors.extend(_validate_simulator_contract(contract))
    errors.extend(_validate_release_contract(payload))
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
        _validate_generated_artifact_section(
            payload,
            section_name="backendTestChecks",
            required_paths=REQUIRED_BACKEND_GENERATED_PATHS,
            required_directory_names=REQUIRED_BACKEND_GENERATED_DIRECTORY_NAMES,
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
        _validate_generated_artifact_section(
            payload,
            section_name="webChecks",
            required_paths=REQUIRED_WEB_GENERATED_PATHS,
            required_directory_names=(),
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
    errors.extend(_validate_backend_runtime_expected(payload))
    errors.extend(_validate_operational_contracts(payload))
    errors.extend(_validate_known_gates(payload))
    return errors


def _validate_release_contract(payload: dict[str, Any]) -> list[str]:
    release = payload.get("release")
    if not isinstance(release, dict):
        return ["release must be an object"]
    errors: list[str] = []
    expected_values = {
        "plist": REQUIRED_RELEASE_PLIST,
        "versionKey": REQUIRED_RELEASE_VERSION_KEY,
        "versionPrefix": REQUIRED_RELEASE_VERSION_PREFIX,
    }
    for field, expected_value in expected_values.items():
        actual_value = release.get(field)
        if actual_value != expected_value:
            errors.append(f"release.{field}={actual_value!r} expected {expected_value!r}")
    return errors


def _validate_simulator_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_values = {
        "configEnvironment": REQUIRED_API_ENVIRONMENT,
        "credentialEnvironment": REQUIRED_CREDENTIAL_ENVIRONMENT,
        "remoteEnvironmentAllowlist": REQUIRED_REMOTE_ENVIRONMENT_ALLOWLIST,
        "appLaunchEnvironment": REQUIRED_API_ENVIRONMENT,
    }
    for field, expected_value in expected_values.items():
        actual_value = contract.get(field)
        if actual_value != expected_value:
            errors.append(
                f"simulatorContract.{field}={actual_value!r} expected {expected_value!r}"
            )

    expected_scalars = {
        "remoteEnvironmentFile": REQUIRED_REMOTE_ENVIRONMENT_FILE,
        "xcuitestConfigFile": REQUIRED_XCUITEST_CONFIG_FILE,
        "xcuitestJourneyFile": REQUIRED_XCUITEST_JOURNEY_FILE,
        "appLockBypass": REQUIRED_APP_LOCK_BYPASS,
    }
    for field, expected_value in expected_scalars.items():
        actual_value = contract.get(field)
        if actual_value != expected_value:
            errors.append(
                f"simulatorContract.{field}={actual_value!r} expected {expected_value!r}"
            )
    return errors


def _validate_backend_runtime_expected(payload: dict[str, Any]) -> list[str]:
    backend = payload.get("backend")
    if not isinstance(backend, dict):
        return ["backend must be an object"]
    runtime_expected = backend.get("runtimeExpected")
    if not isinstance(runtime_expected, dict):
        return ["backend.runtimeExpected must be an object"]

    errors: list[str] = []
    for key, expected_value in REQUIRED_BACKEND_RUNTIME_EXPECTED.items():
        actual_value = runtime_expected.get(key)
        if actual_value != expected_value:
            errors.append(
                f"backend.runtimeExpected.{key}={actual_value!r} expected {expected_value!r}"
            )
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
    missing_credential_free = [
        profile
        for profile in REQUIRED_CREDENTIAL_FREE_APP_OWNED_JOURNEYS
        if profile not in credential_free
    ]
    if missing_credential_free:
        errors.append(
            "credentialFreeAppOwnedJourneys missing profiles: "
            + ", ".join(missing_credential_free)
        )
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


def _validate_generated_artifact_section(
    payload: dict[str, Any],
    *,
    section_name: str,
    required_paths: tuple[str, ...],
    required_directory_names: tuple[str, ...],
) -> list[str]:
    section = payload.get(section_name)
    if not isinstance(section, dict):
        return []

    errors: list[str] = []
    generated_paths = section.get("generatedPaths")
    if not isinstance(generated_paths, list) or not all(
        isinstance(path, str) for path in generated_paths
    ):
        errors.append(f"{section_name}.generatedPaths must be a string list")
    else:
        missing_paths = [path for path in required_paths if path not in generated_paths]
        if missing_paths:
            errors.append(
                f"{section_name}.generatedPaths missing: {', '.join(missing_paths)}"
            )

    if required_directory_names:
        generated_directory_names = section.get("generatedDirectoryNames")
        if not isinstance(generated_directory_names, list) or not all(
            isinstance(name, str) for name in generated_directory_names
        ):
            errors.append(
                f"{section_name}.generatedDirectoryNames must be a string list"
            )
        else:
            missing_names = [
                name
                for name in required_directory_names
                if name not in generated_directory_names
            ]
            if missing_names:
                errors.append(
                    f"{section_name}.generatedDirectoryNames missing: "
                    + ", ".join(missing_names)
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
        expected_contract = EXPECTED_SIMULATOR_PROFILE_CONTRACTS.get(profile, {})
        errors.extend(
            _validate_profile_contract(
                details,
                prefix=f"profiles.{profile}",
                expected_contract=expected_contract,
            )
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
        expected_contract = EXPECTED_DEVICE_PROFILE_CONTRACTS.get(profile, {})
        errors.extend(
            _validate_profile_contract(
                details,
                prefix=f"deviceProfiles.{profile}",
                expected_contract=expected_contract,
            )
        )
    return errors


def _validate_profile_contract(
    details: dict[str, Any],
    *,
    prefix: str,
    expected_contract: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    for field, expected_value in expected_contract.items():
        if field == "buildRootSuffix":
            build_root = details.get("buildRoot")
            if not isinstance(build_root, str) or not build_root.endswith(
                f"/{expected_value}"
            ):
                errors.append(
                    f"{prefix}.buildRoot={build_root!r} must end with /{expected_value}"
                )
            continue
        actual_value = details.get(field)
        if actual_value != expected_value:
            errors.append(f"{prefix}.{field}={actual_value!r} expected {expected_value!r}")
    return errors


def _validate_operational_contracts(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    backend = payload.get("backend")
    if not isinstance(backend, dict):
        errors.append("backend must be an object")
        backend = {}

    for field, expected_value in (
        ("healthPath", REQUIRED_BACKEND_HEALTH_PATH),
        ("runtimePath", REQUIRED_BACKEND_RUNTIME_PATH),
    ):
        actual_value = backend.get(field)
        if actual_value != expected_value:
            errors.append(f"backend.{field}={actual_value!r} expected {expected_value!r}")

    backend_checks = payload.get("backendChecks")
    if backend_checks != list(REQUIRED_BACKEND_CHECKS):
        errors.append(
            f"backendChecks={backend_checks!r} expected {list(REQUIRED_BACKEND_CHECKS)!r}"
        )

    backend_check_base_env = payload.get("backendCheckBaseEnv")
    if backend_check_base_env != REQUIRED_BACKEND_CHECK_BASE_ENV:
        errors.append(
            "backendCheckBaseEnv="
            f"{backend_check_base_env!r} expected {REQUIRED_BACKEND_CHECK_BASE_ENV!r}"
        )

    backend_timeout = payload.get("backendCheckTimeoutSeconds")
    if backend_timeout != REQUIRED_BACKEND_CHECK_TIMEOUT_SECONDS:
        errors.append(
            "backendCheckTimeoutSeconds="
            f"{backend_timeout!r} expected {REQUIRED_BACKEND_CHECK_TIMEOUT_SECONDS!r}"
        )

    runtime_storage = payload.get("runtimeStorage")
    if not isinstance(runtime_storage, dict):
        return errors + ["runtimeStorage must be an object"]

    remote_staging_root = runtime_storage.get("remoteStagingRoot")
    if remote_staging_root != REQUIRED_REMOTE_STAGING_ROOT:
        errors.append(
            "runtimeStorage.remoteStagingRoot="
            f"{remote_staging_root!r} expected {REQUIRED_REMOTE_STAGING_ROOT!r}"
        )

    reusable_roots = runtime_storage.get("reusableArtifactRoots")
    if not isinstance(reusable_roots, list) or not any(
        isinstance(root, dict) and root.get("path") == REQUIRED_REMOTE_STAGING_ROOT
        for root in reusable_roots
    ):
        errors.append(
            "runtimeStorage.reusableArtifactRoots must include "
            f"{REQUIRED_REMOTE_STAGING_ROOT}"
        )

    disposable_roots = runtime_storage.get("remoteDisposableRoots")
    if (
        not isinstance(disposable_roots, list)
        or REQUIRED_REMOTE_DISPOSABLE_ROOT not in disposable_roots
    ):
        errors.append(
            "runtimeStorage.remoteDisposableRoots must include "
            f"{REQUIRED_REMOTE_DISPOSABLE_ROOT}"
        )

    text_fields = {
        "cleanupPolicy": "Keep reusable WD staging",
        "localVolumePolicy": "runtime-only",
        "dockerBuildPolicy": "Docker cache",
    }
    for field, expected_phrase in text_fields.items():
        value = runtime_storage.get(field)
        if not isinstance(value, str) or expected_phrase not in value:
            errors.append(
                f"runtimeStorage.{field} must mention {expected_phrase!r}"
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
