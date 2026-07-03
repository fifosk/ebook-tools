from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "check_apple_shared_pipeline_manifest.py"
)
SPEC = importlib.util.spec_from_file_location(
    "check_apple_shared_pipeline_manifest",
    SCRIPT_PATH,
)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def _write_manifest(
    pipeline_root: Path,
    *,
    credential_environment: list[str] | None = None,
    remote_environment_allowlist: list[str] | None = None,
    app_owned_journeys: dict[str, str] | None = None,
    credential_free_journeys: list[str] | None = None,
    profiles: dict[str, object] | None = None,
    device_profiles: dict[str, object] | None = None,
    known_gates: list[str] | None = None,
    backend_test_checks: dict[str, object] | None = None,
    web_checks: dict[str, object] | None = None,
    contract_checks: dict[str, object] | None = None,
    backend_runtime_expected: dict[str, object] | None = None,
) -> Path:
    app_dir = pipeline_root / "apps"
    app_dir.mkdir(parents=True)
    path = app_dir / "ebook-tools.json"
    default_profiles = {
        profile: {
            "platform": "tvos" if profile.startswith("tvos") else profile,
            "project": "/repo/ios/InteractiveReader/InteractiveReader.xcodeproj",
            "target": "InteractiveReaderTV"
            if profile.startswith("tvos")
            else "InteractiveReader",
            "productName": "InteractiveReaderTV"
            if profile.startswith("tvos")
            else "InteractiveReader",
            "bundleId": "com.example.InteractiveReader.tvos"
            if profile.startswith("tvos")
            else "com.example.InteractiveReader",
            "buildRoot": (
                "/Users/fifo/Library/Developer/XcodeBuildArtifacts/ebook-tools/"
                f"build-sim-{profile}"
            ),
            "stageAppForInstall": False,
            "simulator": {
                "ios": "iPhone 17 Pro",
                "ipados": "iPad Pro 13-inch (M5)",
                "tvos": "Apple TV 4K (3rd generation)",
                "tvos-cinema": "Apple TV 4K (2nd generation)",
            }[profile],
            "simulatorRuntimeVersion": "26.4"
            if profile == "tvos-cinema"
            else "26.5",
            "requiredSimEnv": ["INTERACTIVE_READER_API_BASE_URL"],
        }
        for profile in ("ios", "ipados", "tvos", "tvos-cinema")
    }
    default_device_profiles = {
        "iphone": {
            "device": "Fifo iPhone",
            "platform": "ios",
            "project": "/repo/ios/InteractiveReader/InteractiveReader.xcodeproj",
            "target": "InteractiveReader",
            "productName": "InteractiveReader",
            "bundleId": "com.example.InteractiveReader",
            "deviceSdk": "iphoneos",
            "buildRoot": (
                "/Users/fifo/Library/Developer/XcodeBuildArtifacts/ebook-tools/"
                "build-device-iphoneos"
            ),
            "configuration": "Debug",
            "simulatorSmokeProfile": "ios",
            "embeddedBundleIds": [
                "com.example.InteractiveReader.NotificationServiceExtension"
            ],
            "requiredCapabilities": [
                "Push Notifications",
                "Sign In with Apple",
                "iCloud",
            ],
        },
        "ipad": {
            "device": "Fifo Ipad Pro",
            "platform": "ipados",
            "project": "/repo/ios/InteractiveReader/InteractiveReader.xcodeproj",
            "target": "InteractiveReader",
            "productName": "InteractiveReader",
            "bundleId": "com.example.InteractiveReader",
            "deviceSdk": "iphoneos",
            "buildRoot": (
                "/Users/fifo/Library/Developer/XcodeBuildArtifacts/ebook-tools/"
                "build-device-ipados"
            ),
            "configuration": "Debug",
            "simulatorSmokeProfile": "ipados",
            "embeddedBundleIds": [
                "com.example.InteractiveReader.NotificationServiceExtension"
            ],
            "requiredCapabilities": [
                "Push Notifications",
                "Sign In with Apple",
                "iCloud",
            ],
        },
        "appletv": {
            "device": "Living Room",
            "platform": "tvos",
            "project": "/repo/ios/InteractiveReader/InteractiveReader.xcodeproj",
            "target": "InteractiveReaderTV",
            "productName": "InteractiveReaderTV",
            "bundleId": "com.example.InteractiveReader.tvos",
            "deviceSdk": "appletvos",
            "buildRoot": (
                "/Users/fifo/Library/Developer/XcodeBuildArtifacts/ebook-tools/"
                "build-device-appletvos"
            ),
            "configuration": "Debug",
            "simulatorSmokeProfile": "tvos",
        },
        "cinema": {
            "device": "Cinema",
            "platform": "tvos",
            "project": "/repo/ios/InteractiveReader/InteractiveReader.xcodeproj",
            "target": "InteractiveReaderTV",
            "productName": "InteractiveReaderTV",
            "bundleId": "com.example.InteractiveReader.tvos",
            "deviceSdk": "appletvos",
            "buildRoot": (
                "/Users/fifo/Library/Developer/XcodeBuildArtifacts/ebook-tools/"
                "build-device-cinema-appletvos"
            ),
            "configuration": "Debug",
            "simulatorSmokeProfile": "tvos-cinema",
        },
    }
    payload = {
        "id": "ebook-tools",
        "release": {
            "plist": "ios/InteractiveReader/InteractiveReader/Supporting/Info.plist",
            "versionKey": "EBOOK_TOOLS_RELEASE_VERSION",
            "versionPrefix": "v",
        },
        "simulatorContract": {
            "credentialEnvironment": credential_environment
            if credential_environment is not None
            else [
                "E2E_USERNAME",
                "E2E_PASSWORD",
                "E2E_AUTH_TOKEN",
                "EBOOKTOOLS_SESSION_TOKEN",
            ],
            "remoteEnvironmentAllowlist": remote_environment_allowlist
            if remote_environment_allowlist is not None
            else [
                "E2E_USERNAME",
                "E2E_PASSWORD",
                "E2E_AUTH_TOKEN",
                "EBOOKTOOLS_SESSION_TOKEN",
                "E2E_API_BASE_URL",
            ],
            "configEnvironment": [
                "INTERACTIVE_READER_API_BASE_URL",
                "EBOOK_TOOLS_API_BASE_URL",
                "E2E_API_BASE_URL",
            ],
            "remoteEnvironmentFile": ".env",
            "appLaunchEnvironment": [
                "INTERACTIVE_READER_API_BASE_URL",
                "EBOOK_TOOLS_API_BASE_URL",
                "E2E_API_BASE_URL",
            ],
            "xcuitestConfigFile": (
                "/tmp/apple-device-app-pipeline/ebook-tools/{profile}/"
                "ios_e2e_config.json"
            ),
            "xcuitestJourneyFile": (
                "/tmp/apple-device-app-pipeline/ebook-tools/{profile}/"
                "ios_e2e_journey.json"
            ),
            "appLockBypass": "none",
        },
        "appOwnedJourneys": app_owned_journeys
        if app_owned_journeys is not None
        else {
            "apple-e2e-journeys": "make check-apple-e2e-journeys",
            "iphone": "make test-e2e-iphone",
            "ipados": "make test-e2e-ipad",
            "tvos": "make test-e2e-tvos",
            "iphone-create": "make test-e2e-iphone-create-readiness",
            "ipados-create": "make test-e2e-ipad-create-readiness",
            "tvos-create": "make test-e2e-tvos-create-readiness",
            "ipados-music-bed-sync": "make test-e2e-ipad-music-bed-sync",
            "tvos-music-bed-sync": "make test-e2e-tvos-music-bed-sync",
            "ios-uitests-build": "make build-apple-ios-uitests",
            "tvos-uitests-build": "make build-apple-tvos-uitests",
            "macos-ipad-style": "make build-apple-macos-ipad-style",
            "macos-ipad-style-dry-run": "make build-apple-macos-ipad-style-dry-run",
            "runtime-xcode-readiness": "make apple-runtime-xcode-readiness",
        },
        "credentialFreeAppOwnedJourneys": credential_free_journeys
        if credential_free_journeys is not None
        else [
            "apple-e2e-journeys",
            "ios-uitests-build",
            "tvos-uitests-build",
            "macos-ipad-style",
            "macos-ipad-style-dry-run",
            "runtime-xcode-readiness",
        ],
        "backendTestChecks": backend_test_checks
        if backend_test_checks is not None
        else {
            "commands": [
                {"name": target, "command": ["make", target]}
                for target in (
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
            ],
            "generatedPaths": [
                ".pytest_cache",
            ],
            "generatedDirectoryNames": [
                "__pycache__",
            ],
        },
        "webChecks": web_checks
        if web_checks is not None
        else {
            "commands": [
                {"name": target, "command": ["make", target]}
                for target in (
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
            ],
            "generatedPaths": [
                "web/dist",
                "web/export-dist",
            ],
        },
        "contractChecks": contract_checks
        if contract_checks is not None
        else {
            "commands": [
                {"name": target, "command": ["make", target]}
                for target in (
                    "test-apple-language-catalogs",
                    "test-apple-create-readiness-contract",
                    "test-apple-local-surface-contract",
                    "test-apple-playback-state-swift",
                    "test-apple-contracts",
                )
            ]
        },
        "backend": {
            "defaultBaseUrl": "https://api.langtools.fifosk.synology.me",
            "healthPath": "/_health",
            "runtimePath": "/api/system/runtime",
            "runtimeExpected": backend_runtime_expected
            if backend_runtime_expected is not None
            else dict(module.REQUIRED_BACKEND_RUNTIME_EXPECTED)
        },
        "backendCheckBaseEnv": "INTERACTIVE_READER_API_BASE_URL",
        "backendCheckTimeoutSeconds": 30,
        "backendChecks": [
            "/_health",
            "/api/system/runtime",
        ],
        "runtimeStorage": {
            "remoteStagingRoot": "/Volumes/WD-1TB/Data/staging/ebook-tools",
            "reusableArtifactRoots": [
                {
                    "label": "remote:wd-staging",
                    "path": "/Volumes/WD-1TB/Data/staging/ebook-tools",
                }
            ],
            "remoteDisposableRoots": [
                "/Users/fifo/Library/Developer/XcodeBuildArtifacts/ebook-tools"
            ],
            "cleanupPolicy": "Keep reusable WD staging and dependency caches.",
            "localVolumePolicy": "Mac Studio internal disk is runtime-only.",
            "dockerBuildPolicy": "Docker cache experiments use external staging.",
        },
        "profiles": profiles if profiles is not None else default_profiles,
        "deviceProfiles": device_profiles
        if device_profiles is not None
        else default_device_profiles,
        "knownGates": known_gates
        if known_gates is not None
        else [
            "Physical Apple TV deployment is attended and on-request only.",
            "Physical iPhone/iPad deployment is attended and on-request only.",
            "recursive development loops stop at simulator and build-only proof.",
            (
                "Physical device signing requires an authenticated Xcode account and "
                "provisioning profiles."
            ),
            (
                "Normal physical-device builds and non-signed skip-build installs "
                "must run scripts/check_apple_build_metadata.py so bundled "
                "branch.stamp and commit.stamp match the current checkout before "
                "CoreDevice preflight or install."
            ),
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_makefile_for_manifest(
    path: Path,
    payload: dict[str, object],
    *,
    smoke_profiles: list[str] | None = None,
    journey_profiles: list[str] | None = None,
    smoke_default: str = "ipados",
    journey_default: str = "ipados",
) -> Path:
    journeys = payload["appOwnedJourneys"]
    assert isinstance(journeys, dict)
    make_targets = {
        command.split()[1]
        for command in journeys.values()
        if isinstance(command, str) and command.startswith("make ")
    }
    make_targets.update(module.REQUIRED_BACKEND_TARGETS)
    make_targets.update(module.REQUIRED_WEB_TARGETS)
    make_targets.update(module.REQUIRED_APPLE_CONTRACT_TARGETS)
    makefile = path / "Makefile"
    makefile.write_text(
        "APPLE_PIPELINE_SMOKE_PROFILE ?= "
        + smoke_default
        + "\nAPPLE_PIPELINE_SMOKE_PROFILES ?= "
        + " ".join(smoke_profiles or payload["profiles"])
        + "\nAPPLE_PIPELINE_JOURNEY_PROFILE ?= "
        + journey_default
        + "\nAPPLE_PIPELINE_JOURNEY_PROFILES ?= "
        + " ".join(journey_profiles or journeys)
        + "\n\n"
        + "\n\n".join(f"{target}:\n\t@true" for target in sorted(make_targets)),
        encoding="utf-8",
    )
    return makefile


def test_validate_manifest_accepts_token_env_keys(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path)

    assert module.validate_manifest(path) == []


def test_validate_manifest_requires_release_contract(
    tmp_path: Path,
) -> None:
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["release"] = {
        "plist": "ios/InteractiveReader/InteractiveReader/Supporting/Info-tvOS.plist",
        "versionKey": "CFBundleVersion",
        "versionPrefix": "",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    errors = module.validate_manifest(path)

    assert (
        "release.plist='ios/InteractiveReader/InteractiveReader/Supporting/Info-tvOS.plist' "
        "expected 'ios/InteractiveReader/InteractiveReader/Supporting/Info.plist'"
    ) in errors
    assert (
        "release.versionKey='CFBundleVersion' expected 'EBOOK_TOOLS_RELEASE_VERSION'"
    ) in errors
    assert "release.versionPrefix='' expected 'v'" in errors


def test_validate_manifest_requires_simulator_contract_handoff(
    tmp_path: Path,
) -> None:
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    contract = payload["simulatorContract"]
    contract["configEnvironment"] = ["INTERACTIVE_READER_API_BASE_URL"]
    contract["credentialEnvironment"] = ["E2E_USERNAME"]
    contract["remoteEnvironmentAllowlist"] = ["E2E_USERNAME"]
    contract["appLaunchEnvironment"] = ["E2E_API_BASE_URL"]
    contract["remoteEnvironmentFile"] = ".secrets"
    contract["xcuitestConfigFile"] = "/tmp/config.json"
    contract["xcuitestJourneyFile"] = "/tmp/journey.json"
    contract["appLockBypass"] = "PFR_DISABLE_APP_LOCK=1"
    path.write_text(json.dumps(payload), encoding="utf-8")

    errors = module.validate_manifest(path)

    assert (
        "simulatorContract.configEnvironment=['INTERACTIVE_READER_API_BASE_URL'] "
        "expected ['INTERACTIVE_READER_API_BASE_URL', 'EBOOK_TOOLS_API_BASE_URL', "
        "'E2E_API_BASE_URL']"
    ) in errors
    assert (
        "simulatorContract.credentialEnvironment=['E2E_USERNAME'] "
        "expected ['E2E_USERNAME', 'E2E_PASSWORD', 'E2E_AUTH_TOKEN', "
        "'EBOOKTOOLS_SESSION_TOKEN']"
    ) in errors
    assert (
        "simulatorContract.remoteEnvironmentAllowlist=['E2E_USERNAME'] "
        "expected ['E2E_USERNAME', 'E2E_PASSWORD', 'E2E_AUTH_TOKEN', "
        "'EBOOKTOOLS_SESSION_TOKEN', 'E2E_API_BASE_URL']"
    ) in errors
    assert (
        "simulatorContract.appLaunchEnvironment=['E2E_API_BASE_URL'] "
        "expected ['INTERACTIVE_READER_API_BASE_URL', 'EBOOK_TOOLS_API_BASE_URL', "
        "'E2E_API_BASE_URL']"
    ) in errors
    assert "simulatorContract.remoteEnvironmentFile='.secrets' expected '.env'" in errors
    assert (
        "simulatorContract.xcuitestConfigFile='/tmp/config.json' "
        "expected '/tmp/apple-device-app-pipeline/ebook-tools/{profile}/"
        "ios_e2e_config.json'"
    ) in errors
    assert (
        "simulatorContract.xcuitestJourneyFile='/tmp/journey.json' "
        "expected '/tmp/apple-device-app-pipeline/ebook-tools/{profile}/"
        "ios_e2e_journey.json'"
    ) in errors
    assert (
        "simulatorContract.appLockBypass='PFR_DISABLE_APP_LOCK=1' expected 'none'"
    ) in errors


def test_validate_manifest_requires_operational_backend_and_storage_contracts(
    tmp_path: Path,
) -> None:
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["backend"]["healthPath"] = "/health"
    payload["backendChecks"] = ["/health"]
    payload["backendCheckBaseEnv"] = "EBOOK_API_BASE_URL"
    payload["backendCheckTimeoutSeconds"] = 5
    payload["runtimeStorage"] = {
        "remoteStagingRoot": "/tmp/ebook-tools",
        "reusableArtifactRoots": [],
        "remoteDisposableRoots": [],
        "cleanupPolicy": "Clean everything.",
        "localVolumePolicy": "Use local disk.",
        "dockerBuildPolicy": "Build wherever.",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    errors = module.validate_manifest(path)

    assert "backend.healthPath='/health' expected '/_health'" in errors
    assert "backendChecks=['/health'] expected ['/_health', '/api/system/runtime']" in errors
    assert (
        "backendCheckBaseEnv='EBOOK_API_BASE_URL' "
        "expected 'INTERACTIVE_READER_API_BASE_URL'"
    ) in errors
    assert "backendCheckTimeoutSeconds=5 expected 30" in errors
    assert (
        "runtimeStorage.remoteStagingRoot='/tmp/ebook-tools' "
        "expected '/Volumes/WD-1TB/Data/staging/ebook-tools'"
    ) in errors
    assert (
        "runtimeStorage.reusableArtifactRoots must include "
        "/Volumes/WD-1TB/Data/staging/ebook-tools"
    ) in errors
    assert (
        "runtimeStorage.remoteDisposableRoots must include "
        "/Users/fifo/Library/Developer/XcodeBuildArtifacts/ebook-tools"
    ) in errors
    assert "runtimeStorage.cleanupPolicy must mention 'Keep reusable WD staging'" in errors
    assert "runtimeStorage.localVolumePolicy must mention 'runtime-only'" in errors
    assert "runtimeStorage.dockerBuildPolicy must mention 'Docker cache'" in errors


def test_validate_manifest_requires_exact_simulator_and_device_profile_contracts(
    tmp_path: Path,
) -> None:
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["profiles"]["ipados"]["simulator"] = "iPad Air"
    payload["profiles"]["tvos-cinema"]["buildRoot"] = "/tmp/tvos-cinema"
    payload["deviceProfiles"]["iphone"]["embeddedBundleIds"] = []
    payload["deviceProfiles"]["ipad"]["bundleId"] = "com.example.InteractiveReader.ipad"
    payload["deviceProfiles"]["appletv"]["device"] = "Cinema"
    payload["deviceProfiles"]["appletv"]["simulatorSmokeProfile"] = "tvos-cinema"
    payload["deviceProfiles"]["cinema"]["deviceSdk"] = "iphoneos"
    payload["deviceProfiles"]["cinema"]["buildRoot"] = "/tmp/cinema"
    path.write_text(json.dumps(payload), encoding="utf-8")

    errors = module.validate_manifest(path)

    assert "profiles.ipados.simulator='iPad Air' expected 'iPad Pro 13-inch (M5)'" in errors
    assert (
        "profiles.tvos-cinema.buildRoot='/tmp/tvos-cinema' must end with "
        "/ebook-tools/build-sim-tvos-cinema"
    ) in errors
    assert (
        "deviceProfiles.iphone.embeddedBundleIds=[] expected "
        "['com.example.InteractiveReader.NotificationServiceExtension']"
    ) in errors
    assert (
        "deviceProfiles.ipad.bundleId='com.example.InteractiveReader.ipad' "
        "expected 'com.example.InteractiveReader'"
    ) in errors
    assert "deviceProfiles.appletv.device='Cinema' expected 'Living Room'" in errors
    assert (
        "deviceProfiles.appletv.simulatorSmokeProfile='tvos-cinema' expected 'tvos'"
    ) in errors
    assert "deviceProfiles.cinema.deviceSdk='iphoneos' expected 'appletvos'" in errors
    assert (
        "deviceProfiles.cinema.buildRoot='/tmp/cinema' must end with "
        "/ebook-tools/build-device-cinema-appletvos"
    ) in errors


def test_validate_manifest_requires_generated_artifact_contracts(
    tmp_path: Path,
) -> None:
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["backendTestChecks"]["generatedPaths"] = []
    del payload["backendTestChecks"]["generatedDirectoryNames"]
    payload["webChecks"]["generatedPaths"] = ["web/dist"]
    path.write_text(json.dumps(payload), encoding="utf-8")

    errors = module.validate_manifest(path)

    assert "backendTestChecks.generatedPaths missing: .pytest_cache" in errors
    assert (
        "backendTestChecks.generatedDirectoryNames must be a string list"
    ) in errors
    assert "webChecks.generatedPaths missing: web/export-dist" in errors


def test_validate_manifest_reports_missing_token_env_keys(tmp_path: Path) -> None:
    path = _write_manifest(
        tmp_path,
        credential_environment=["E2E_USERNAME", "E2E_PASSWORD"],
        remote_environment_allowlist=["E2E_USERNAME", "E2E_PASSWORD", "E2E_AUTH_TOKEN"],
    )

    errors = module.validate_manifest(path)

    assert any(
        "simulatorContract.credentialEnvironment missing token env keys" in error
        for error in errors
    )
    assert any("E2E_AUTH_TOKEN" in error for error in errors)
    assert any("EBOOKTOOLS_SESSION_TOKEN" in error for error in errors)
    assert any(
        "simulatorContract.remoteEnvironmentAllowlist missing token env keys" in error
        for error in errors
    )


def test_validate_manifest_reports_missing_app_owned_journey_contract(tmp_path: Path) -> None:
    path = _write_manifest(
        tmp_path,
        app_owned_journeys={"ipados": "npm run something"},
        credential_free_journeys=["unknown"],
    )

    errors = module.validate_manifest(path)

    assert any("appOwnedJourneys missing profiles" in error for error in errors)
    assert any(
        "appOwnedJourneys.ipados must call a repo-owned make target" in error
        for error in errors
    )
    assert any(
        "credentialFreeAppOwnedJourneys references unknown profiles" in error
        for error in errors
    )
    assert any(
        "credentialFreeAppOwnedJourneys missing profiles" in error
        for error in errors
    )
    assert any("apple-e2e-journeys" in error for error in errors)
    assert any("ios-uitests-build" in error for error in errors)


def test_validate_manifest_rejects_unknown_app_owned_journey_make_targets(tmp_path: Path) -> None:
    journeys = {
        "apple-e2e-journeys": "make check-apple-e2e-journeys",
        "iphone": "make test-e2e-iphone",
        "ipados": "make test-e2e-ipad",
        "tvos": "make test-e2e-tvos",
        "iphone-create": "make test-e2e-iphone-create-readiness",
        "ipados-create": "make test-e2e-ipad-create-readiness",
        "tvos-create": "make test-e2e-tvos-create-readiness",
        "ipados-music-bed-sync": "make test-e2e-ipad-music-bed-sync",
        "tvos-music-bed-sync": "make test-e2e-tvos-music-bed-sync",
        "ios-uitests-build": "make build-apple-ios-uitests",
        "tvos-uitests-build": "make build-apple-tvos-uitests",
        "macos-ipad-style": "make build-apple-macos-ipad-style",
        "macos-ipad-style-dry-run": "make missing-macos-ipad-style-dry-run",
        "runtime-xcode-readiness": "make apple-runtime-xcode-readiness",
    }
    path = _write_manifest(tmp_path, app_owned_journeys=journeys)

    errors = module.validate_manifest(path)

    assert (
        "appOwnedJourneys.macos-ipad-style-dry-run target is not defined in "
        "Makefile: missing-macos-ipad-style-dry-run"
    ) in errors


def test_validate_manifest_requires_backend_acquisition_runtime_expectations(
    tmp_path: Path,
) -> None:
    runtime_expected = dict(module.REQUIRED_BACKEND_RUNTIME_EXPECTED)
    del runtime_expected["creation.acquisitionProvidersPath"]
    del runtime_expected["acquisition.mediaKinds"]
    runtime_expected["creation.acquisitionAcquirePath"] = "/old/acquire"
    runtime_expected["acquisition.providerStatuses"] = ["available"]
    path = _write_manifest(tmp_path, backend_runtime_expected=runtime_expected)

    errors = module.validate_manifest(path)

    assert (
        "backend.runtimeExpected.creation.acquisitionProvidersPath=None "
        "expected '/api/acquisition/providers'"
    ) in errors
    assert (
        "backend.runtimeExpected.creation.acquisitionAcquirePath='/old/acquire' "
        "expected '/api/acquisition/acquire'"
    ) in errors
    assert (
        "backend.runtimeExpected.acquisition.mediaKinds=None expected ['book', 'video']"
    ) in errors
    assert (
        "backend.runtimeExpected.acquisition.providerStatuses=['available'] "
        "expected ['available', 'not_configured', 'planned']"
    ) in errors


def test_validate_manifest_rejects_stale_backend_runtime_expected_keys(
    tmp_path: Path,
) -> None:
    runtime_expected = dict(module.REQUIRED_BACKEND_RUNTIME_EXPECTED)
    del runtime_expected["app"]
    runtime_expected["service"] = "old-api"
    runtime_expected["creation.oldSearchPath"] = "/api/old/search"
    path = _write_manifest(tmp_path, backend_runtime_expected=runtime_expected)

    errors = module.validate_manifest(path)

    assert "backend.runtimeExpected.app=None expected 'ebook-tools'" in errors
    assert (
        "backend.runtimeExpected.service='old-api' expected 'ebook-tools-api'"
        in errors
    )
    assert (
        "backend.runtimeExpected has unknown keys: creation.oldSearchPath"
        in errors
    )


def test_validate_manifest_requires_backend_create_runtime_expectations(
    tmp_path: Path,
) -> None:
    runtime_expected = dict(module.REQUIRED_BACKEND_RUNTIME_EXPECTED)
    del runtime_expected["creation.pipelineFilesDefaultLimit"]
    runtime_expected["creation.pipelineCoverUploadPath"] = "/api/pipelines/cover"
    del runtime_expected["creation.pipelineDefaultsPath"]
    runtime_expected["creation.youtubeVideoDownloadPath"] = "/api/youtube/video"
    del runtime_expected["creation.bookMetadataPreviewPath"]
    path = _write_manifest(tmp_path, backend_runtime_expected=runtime_expected)

    errors = module.validate_manifest(path)

    assert (
        "backend.runtimeExpected.creation.pipelineFilesDefaultLimit=None "
        "expected 200"
    ) in errors
    assert (
        "backend.runtimeExpected.creation.pipelineCoverUploadPath='/api/pipelines/cover' "
        "expected '/api/pipelines/covers/upload'"
    ) in errors
    assert (
        "backend.runtimeExpected.creation.pipelineDefaultsPath=None "
        "expected '/api/pipelines/defaults'"
    ) in errors
    assert (
        "backend.runtimeExpected.creation.youtubeVideoDownloadPath='/api/youtube/video' "
        "expected '/api/subtitles/youtube/video'"
    ) in errors
    assert (
        "backend.runtimeExpected.creation.bookMetadataPreviewPath=None "
        "expected '/api/pipelines/metadata/book/lookup'"
    ) in errors


def test_validate_manifest_requires_backend_offline_export_runtime_expectations(
    tmp_path: Path,
) -> None:
    runtime_expected = dict(module.REQUIRED_BACKEND_RUNTIME_EXPECTED)
    del runtime_expected["offlineExports.createPath"]
    runtime_expected["offlineExports.playerTypes"] = ["interactive-video"]
    path = _write_manifest(tmp_path, backend_runtime_expected=runtime_expected)

    errors = module.validate_manifest(path)

    assert "backend.runtimeExpected.offlineExports.createPath=None expected '/api/exports'" in errors
    assert (
        "backend.runtimeExpected.offlineExports.playerTypes=['interactive-video'] "
        "expected ['interactive-text']"
    ) in errors


def test_validate_manifest_requires_backend_playback_state_runtime_expectations(
    tmp_path: Path,
) -> None:
    runtime_expected = dict(module.REQUIRED_BACKEND_RUNTIME_EXPECTED)
    del runtime_expected["playbackState.readingBedsPath"]
    runtime_expected["playbackState.resumeFilterQuery"] = "job"
    path = _write_manifest(tmp_path, backend_runtime_expected=runtime_expected)

    errors = module.validate_manifest(path)

    assert "backend.runtimeExpected.playbackState.readingBedsPath=None expected '/api/reading-beds'" in errors
    assert (
        "backend.runtimeExpected.playbackState.resumeFilterQuery='job' "
        "expected 'job_id'"
    ) in errors


def test_validate_manifest_requires_backend_library_action_runtime_expectations(
    tmp_path: Path,
) -> None:
    runtime_expected = dict(module.REQUIRED_BACKEND_RUNTIME_EXPECTED)
    del runtime_expected["libraryActions.removeMediaPathTemplate"]
    runtime_expected["libraryActions.reindexPath"] = "/old/reindex"
    path = _write_manifest(tmp_path, backend_runtime_expected=runtime_expected)

    errors = module.validate_manifest(path)

    assert (
        "backend.runtimeExpected.libraryActions.removeMediaPathTemplate=None "
        "expected '/api/library/remove-media/{job_id}'"
    ) in errors
    assert (
        "backend.runtimeExpected.libraryActions.reindexPath='/old/reindex' "
        "expected '/api/library/reindex'"
    ) in errors


def test_validate_manifest_requires_backend_pipeline_media_runtime_expectations(
    tmp_path: Path,
) -> None:
    runtime_expected = dict(module.REQUIRED_BACKEND_RUNTIME_EXPECTED)
    del runtime_expected["pipelineMedia.jobTimingPathTemplate"]
    runtime_expected["pipelineMedia.chunkOrdering"] = "chunk"
    path = _write_manifest(tmp_path, backend_runtime_expected=runtime_expected)

    errors = module.validate_manifest(path)

    assert (
        "backend.runtimeExpected.pipelineMedia.jobTimingPathTemplate=None "
        "expected '/api/jobs/{job_id}/timing'"
    ) in errors
    assert (
        "backend.runtimeExpected.pipelineMedia.chunkOrdering='chunk' "
        "expected 'sentenceRange'"
    ) in errors


def test_validate_manifest_requires_backend_pipeline_job_runtime_expectations(
    tmp_path: Path,
) -> None:
    runtime_expected = dict(module.REQUIRED_BACKEND_RUNTIME_EXPECTED)
    del runtime_expected["pipelineJobs.restartPathTemplate"]
    runtime_expected["pipelineJobs.cacheBusterQuery"] = "cache"
    path = _write_manifest(tmp_path, backend_runtime_expected=runtime_expected)

    errors = module.validate_manifest(path)

    assert (
        "backend.runtimeExpected.pipelineJobs.restartPathTemplate=None "
        "expected '/api/pipelines/jobs/{job_id}/restart'"
    ) in errors
    assert (
        "backend.runtimeExpected.pipelineJobs.cacheBusterQuery='cache' "
        "expected 'ts'"
    ) in errors


def test_validate_manifest_requires_backend_shared_surface_runtime_expectations(
    tmp_path: Path,
) -> None:
    runtime_expected = dict(module.REQUIRED_BACKEND_RUNTIME_EXPECTED)
    del runtime_expected["auth.logoutPath"]
    runtime_expected["clientConfig.sessionTokenStorage"] = "userdefaults"
    del runtime_expected["applePipeline.deviceProfiles"]
    runtime_expected["linguist.audioSynthesisPath"] = "/api/old-audio"
    del runtime_expected["notifications.testPath"]
    path = _write_manifest(tmp_path, backend_runtime_expected=runtime_expected)

    errors = module.validate_manifest(path)

    assert (
        "backend.runtimeExpected.auth.logoutPath=None "
        "expected '/api/auth/logout'"
    ) in errors
    assert (
        "backend.runtimeExpected.clientConfig.sessionTokenStorage='userdefaults' "
        "expected 'device-keychain'"
    ) in errors
    assert (
        "backend.runtimeExpected.applePipeline.deviceProfiles=None "
        "expected ['iphone', 'ipad', 'appletv', 'cinema']"
    ) in errors
    assert (
        "backend.runtimeExpected.linguist.audioSynthesisPath='/api/old-audio' "
        "expected '/api/audio'"
    ) in errors
    assert (
        "backend.runtimeExpected.notifications.testPath=None "
        "expected '/api/notifications/test'"
    ) in errors


def test_validate_manifest_rejects_missing_aggregate_journey_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    journeys = payload["appOwnedJourneys"]
    aggregate_profiles = [
        profile for profile in journeys if profile != "macos-ipad-style"
    ]
    make_targets = {
        command.split()[1] for command in journeys.values() if command.startswith("make ")
    }
    make_targets.update(module.REQUIRED_BACKEND_TARGETS)
    make_targets.update(module.REQUIRED_WEB_TARGETS)
    make_targets.update(module.REQUIRED_APPLE_CONTRACT_TARGETS)
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        "APPLE_PIPELINE_JOURNEY_PROFILES ?= "
        + " ".join(aggregate_profiles)
        + "\n\n"
        + "\n\n".join(f"{target}:\n\t@true" for target in sorted(make_targets)),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "MAKEFILE", makefile)

    errors = module.validate_manifest(path)

    assert (
        "APPLE_PIPELINE_JOURNEY_PROFILES missing appOwnedJourneys: "
        "macos-ipad-style"
    ) in errors


def test_validate_manifest_rejects_unknown_default_journey_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    makefile = _write_makefile_for_manifest(
        tmp_path,
        payload,
        journey_default="watchos",
    )
    monkeypatch.setattr(module, "MAKEFILE", makefile)

    errors = module.validate_manifest(path)

    assert "APPLE_PIPELINE_JOURNEY_PROFILE references unknown journey: watchos" in errors


def test_validate_manifest_rejects_default_journey_missing_from_aggregate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    journeys = payload["appOwnedJourneys"]
    journey_profiles = [
        profile for profile in journeys if profile != "ipados"
    ]
    makefile = _write_makefile_for_manifest(
        tmp_path,
        payload,
        journey_profiles=journey_profiles,
        journey_default="ipados",
    )
    monkeypatch.setattr(module, "MAKEFILE", makefile)

    errors = module.validate_manifest(path)

    assert (
        "APPLE_PIPELINE_JOURNEY_PROFILE must be included in "
        "APPLE_PIPELINE_JOURNEY_PROFILES: ipados"
    ) in errors


def test_validate_manifest_rejects_missing_aggregate_simulator_smoke_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = payload["profiles"]
    smoke_profiles = [
        profile for profile in profiles if profile != "tvos-cinema"
    ]
    journeys = payload["appOwnedJourneys"]
    make_targets = {
        command.split()[1] for command in journeys.values() if command.startswith("make ")
    }
    make_targets.update(module.REQUIRED_BACKEND_TARGETS)
    make_targets.update(module.REQUIRED_WEB_TARGETS)
    make_targets.update(module.REQUIRED_APPLE_CONTRACT_TARGETS)
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        "APPLE_PIPELINE_SMOKE_PROFILES ?= "
        + " ".join(smoke_profiles)
        + "\nAPPLE_PIPELINE_JOURNEY_PROFILES ?= "
        + " ".join(journeys)
        + "\n\n"
        + "\n\n".join(f"{target}:\n\t@true" for target in sorted(make_targets)),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "MAKEFILE", makefile)

    errors = module.validate_manifest(path)

    assert (
        "APPLE_PIPELINE_SMOKE_PROFILES missing simulator profiles: "
        "tvos-cinema"
    ) in errors


def test_validate_manifest_rejects_unknown_aggregate_simulator_smoke_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = list(payload["profiles"]) + ["visionos"]
    journeys = payload["appOwnedJourneys"]
    make_targets = {
        command.split()[1] for command in journeys.values() if command.startswith("make ")
    }
    make_targets.update(module.REQUIRED_BACKEND_TARGETS)
    make_targets.update(module.REQUIRED_WEB_TARGETS)
    make_targets.update(module.REQUIRED_APPLE_CONTRACT_TARGETS)
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        "APPLE_PIPELINE_SMOKE_PROFILES ?= "
        + " ".join(profiles)
        + "\nAPPLE_PIPELINE_JOURNEY_PROFILES ?= "
        + " ".join(journeys)
        + "\n\n"
        + "\n\n".join(f"{target}:\n\t@true" for target in sorted(make_targets)),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "MAKEFILE", makefile)

    errors = module.validate_manifest(path)

    assert (
        "APPLE_PIPELINE_SMOKE_PROFILES references unknown simulator profiles: "
        "visionos"
    ) in errors


def test_validate_manifest_rejects_unknown_default_simulator_smoke_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    makefile = _write_makefile_for_manifest(
        tmp_path,
        payload,
        smoke_default="watchos",
    )
    monkeypatch.setattr(module, "MAKEFILE", makefile)

    errors = module.validate_manifest(path)

    assert (
        "APPLE_PIPELINE_SMOKE_PROFILE references unknown simulator profile: watchos"
    ) in errors


def test_validate_manifest_rejects_default_smoke_missing_from_aggregate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = payload["profiles"]
    smoke_profiles = [
        profile for profile in profiles if profile != "ipados"
    ]
    makefile = _write_makefile_for_manifest(
        tmp_path,
        payload,
        smoke_profiles=smoke_profiles,
        smoke_default="ipados",
    )
    monkeypatch.setattr(module, "MAKEFILE", makefile)

    errors = module.validate_manifest(path)

    assert (
        "APPLE_PIPELINE_SMOKE_PROFILE must be included in "
        "APPLE_PIPELINE_SMOKE_PROFILES: ipados"
    ) in errors


def test_validate_manifest_reports_command_section_regressions(tmp_path: Path) -> None:
    path = _write_manifest(
        tmp_path,
        backend_test_checks={
            "commands": [
                {"name": "duplicate", "command": ["make", "test-backend-auth-session"]},
                {"name": "duplicate", "command": ["pytest"]},
            ]
        },
        web_checks={"commands": []},
        contract_checks={"commands": [{"name": "apple", "command": ["npm", "test"]}]},
    )

    errors = module.validate_manifest(path)

    assert any(
        "backendTestChecks.commands contains duplicate name: duplicate" in error
        for error in errors
    )
    assert any(
        "backendTestChecks.commands[1].command must be ['make', '<target>']" in error
        for error in errors
    )
    missing_backend_error = next(
        error
        for error in errors
        if error.startswith("backendTestChecks.commands missing make targets:")
    )
    assert "test-backend-runtime-descriptor" in missing_backend_error
    assert "test-backend-library-search-source-isbn" in missing_backend_error
    assert "test-backend-offline-export" in missing_backend_error
    assert any("webChecks.commands must be a non-empty list" in error for error in errors)
    assert any(
        "contractChecks.commands[0].command must be ['make', '<target>']" in error
        for error in errors
    )
    assert any(
        "contractChecks.commands missing make targets: test-apple-language-catalogs"
        in error
        for error in errors
    )


def test_validate_manifest_rejects_unknown_make_targets(tmp_path: Path) -> None:
    path = _write_manifest(
        tmp_path,
        web_checks={
            "commands": [
                {"name": "bogus", "command": ["make", "test-web-missing-focused"]},
                *[
                    {"name": target, "command": ["make", target]}
                    for target in module.REQUIRED_WEB_TARGETS
                ],
            ]
        },
    )

    errors = module.validate_manifest(path)

    assert (
        "webChecks.commands[0].command target is not defined in Makefile: "
        "test-web-missing-focused"
    ) in errors


def test_validate_manifest_reports_profile_and_gate_regressions(tmp_path: Path) -> None:
    path = _write_manifest(
        tmp_path,
        profiles={
            "ios": {
                "platform": "ios",
                "project": "/repo/project.xcodeproj",
                "target": "InteractiveReader",
                "productName": "InteractiveReader",
                "bundleId": "com.example.InteractiveReader",
                "buildRoot": "/tmp/build-sim-ios",
                "stageAppForInstall": True,
                "simulator": "iPhone 17 Pro",
                "simulatorRuntimeVersion": "26.5",
                "requiredSimEnv": [],
            }
        },
        device_profiles={
            "iphone": {
                "device": "Fifo iPhone",
                "platform": "ios",
                "project": "/repo/project.xcodeproj",
                "target": "InteractiveReader",
                "productName": "InteractiveReader",
                "bundleId": "com.example.InteractiveReader",
                "deviceSdk": "iphoneos",
                "buildRoot": "/tmp/build-device-iphoneos",
                "configuration": "Debug",
                "simulatorSmokeProfile": "missing-profile",
                "requiredCapabilities": ["iCloud"],
            }
        },
        known_gates=["No device guard text here."],
    )

    errors = module.validate_manifest(path)

    assert any(
        "profiles missing simulator profiles: ipados, tvos, tvos-cinema" in error
        for error in errors
    )
    assert any("profiles.ios.stageAppForInstall must be false" in error for error in errors)
    assert any(
        "profiles.ios.requiredSimEnv must include INTERACTIVE_READER_API_BASE_URL"
        in error
        for error in errors
    )
    assert any(
        "deviceProfiles missing physical profiles: ipad, appletv, cinema" in error
        for error in errors
    )
    assert any(
        "deviceProfiles.iphone.simulatorSmokeProfile references unknown profile "
        "missing-profile" in error
        for error in errors
    )
    assert any(
        "deviceProfiles.iphone.requiredCapabilities missing: Push Notifications, "
        "Sign In with Apple" in error
        for error in errors
    )
    assert any("knownGates missing required deployment guard" in error for error in errors)


def test_main_skips_absent_manifest_by_default(tmp_path: Path, capsys) -> None:
    result = module.main(["--pipeline-root", str(tmp_path)])

    assert result == 0
    assert "checks skipped" in capsys.readouterr().out


def test_main_can_require_manifest(tmp_path: Path, capsys) -> None:
    result = module.main(["--pipeline-root", str(tmp_path), "--require"])

    assert result == 1
    assert "manifest not found" in capsys.readouterr().err
