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
            "buildRoot": f"/tmp/build-sim-{profile}",
            "stageAppForInstall": False,
            "simulator": "Apple TV 4K"
            if profile.startswith("tvos")
            else "iPhone 17 Pro",
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
            "buildRoot": "/tmp/build-device-iphoneos",
            "configuration": "Debug",
            "simulatorSmokeProfile": "ios",
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
            "buildRoot": "/tmp/build-device-ipados",
            "configuration": "Debug",
            "simulatorSmokeProfile": "ipados",
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
            "buildRoot": "/tmp/build-device-appletvos",
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
            "buildRoot": "/tmp/build-device-cinema-appletvos",
            "configuration": "Debug",
            "simulatorSmokeProfile": "tvos-cinema",
        },
    }
    payload = {
        "id": "ebook-tools",
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
            ],
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
            ]
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
            ]
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
