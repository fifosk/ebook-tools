from __future__ import annotations

import importlib.util
import json
from pathlib import Path


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
            "platform": profile,
            "project": "/repo/ios/InteractiveReader/InteractiveReader.xcodeproj",
            "target": "InteractiveReaderTV" if profile == "tvos" else "InteractiveReader",
            "productName": "InteractiveReaderTV" if profile == "tvos" else "InteractiveReader",
            "bundleId": "com.example.InteractiveReader.tvos"
            if profile == "tvos"
            else "com.example.InteractiveReader",
            "buildRoot": f"/tmp/build-sim-{profile}",
            "stageAppForInstall": False,
            "simulator": "Apple TV 4K" if profile == "tvos" else "iPhone 17 Pro",
            "simulatorRuntimeVersion": "26.5",
            "requiredSimEnv": ["INTERACTIVE_READER_API_BASE_URL"],
        }
        for profile in ("ios", "ipados", "tvos")
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
            "runtime-xcode-readiness": "make apple-runtime-xcode-readiness",
        },
        "credentialFreeAppOwnedJourneys": credential_free_journeys
        if credential_free_journeys is not None
        else ["apple-e2e-journeys"],
        "backendTestChecks": backend_test_checks
        if backend_test_checks is not None
        else {
            "commands": [
                {"name": target, "command": ["make", target]}
                for target in (
                    "test-backend-auth-session",
                    "test-backend-runtime-descriptor",
                    "test-backend-create-book",
                    "test-backend-pipeline-sources",
                    "test-backend-acquisition",
                    "test-backend-playback-state",
                    "test-backend-playback-media",
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
                    "test-web-create-intake-focused",
                    "test-web-creation-templates-focused",
                    "test-web-library-focused",
                    "test-web-playback-focused",
                    "test-web-video-dubbing-focused",
                    "test-web-subtitle-tool-focused",
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
        "credentialFreeAppOwnedJourneys must include apple-e2e-journeys" in error
        for error in errors
    )


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
    assert any(
        "backendTestChecks.commands missing make targets: test-backend-runtime-descriptor"
        in error
        for error in errors
    )
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
        "profiles missing simulator profiles: ipados, tvos" in error
        for error in errors
    )
    assert any("profiles.ios.stageAppForInstall must be false" in error for error in errors)
    assert any(
        "profiles.ios.requiredSimEnv must include INTERACTIVE_READER_API_BASE_URL"
        in error
        for error in errors
    )
    assert any(
        "deviceProfiles missing physical profiles: ipad, appletv" in error
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
