from __future__ import annotations

import plistlib
import datetime as dt
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "apple_full_entitlement_signing_plan.sh"


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("placeholder", encoding="utf-8")
    return path


def _write_plist(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        plistlib.dump(payload, handle)
    return path


def _read_plist(path: Path) -> dict:
    with path.open("rb") as handle:
        return plistlib.load(handle)


def _write_executable(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_full_entitlement_signing_plan_prints_non_mutating_recipe(tmp_path: Path) -> None:
    app_profile = _touch(tmp_path / "profiles" / "app.mobileprovision")
    extension_profile = _touch(tmp_path / "profiles" / "extension.mobileprovision")
    app_entitlements = _touch(tmp_path / "entitlements" / "app.plist")
    extension_entitlements = _touch(tmp_path / "entitlements" / "extension.plist")
    derived_data = tmp_path / "DerivedData-device-full-entitlements"

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--device",
            "TEST-IPAD",
            "--app-profile",
            str(app_profile),
            "--extension-profile",
            str(extension_profile),
            "--app-entitlements",
            str(app_entitlements),
            "--extension-entitlements",
            str(extension_entitlements),
            "--signing-identity",
            "Apple Development: Test User (TEAMID)",
            "--derived-data",
            str(derived_data),
            "--configuration",
            "Release",
            "--launch-console-timeout",
            "12",
        ],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )

    output = result.stdout
    app_path = derived_data / "Build/Products/Release-iphoneos/InteractiveReader.app"
    appex_path = app_path / "PlugIns/NotificationServiceExtension.appex"
    merged_app_entitlements = derived_data / "MergedEntitlements/InteractiveReader.entitlements.plist"
    merged_extension_entitlements = (
        derived_data / "MergedEntitlements/NotificationServiceExtension.entitlements.plist"
    )

    assert "Full-entitlement iPhone/iPad signing plan" in output
    assert "Unsigned device build:" in output
    assert "-destination  generic/platform=iOS" in output
    assert "CODE_SIGNING_ALLOWED=NO" in output
    assert "Generate merged app entitlements:" in output
    assert "apple_merge_entitlements.py" in output
    assert f"--output  {merged_app_entitlements}" in output
    assert "Generate merged extension entitlements:" in output
    assert f"--project-entitlements  {extension_entitlements}" in output
    assert f"--output  {merged_extension_entitlements}" in output
    assert f"{app_path}/embedded.mobileprovision" in output
    assert f"{appex_path}/embedded.mobileprovision" in output
    assert "Sign extension dylibs:" in output
    assert "Sign notification extension:" in output
    assert f"--entitlements  {merged_extension_entitlements}" in output
    assert "Sign app with full entitlements:" in output
    assert f"--entitlements  {merged_app_entitlements}" in output
    assert "Verify signed app:" in output
    assert "Final guarded install command:" in output
    assert "CONFIRM_PHYSICAL_DEVICE_UPDATE=YES" in output
    assert "apple_unattended_device_update.sh" in output
    assert "--skip-build" in output
    assert f"--app-path  {app_path}" in output
    assert "--install" in output
    assert "--launch-console-timeout  12" in output
    assert "devicectl" not in output


def test_full_entitlement_signing_plan_auto_discovers_profiles(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profiles"
    app_profile = _write_plist(
        profile_dir / "app.mobileprovision",
        {
            "Name": "Reader full capabilities",
            "Platform": ["iOS"],
            "ExpirationDate": dt.datetime(2099, 1, 1),
            "Entitlements": {
                "application-identifier": "3Y7288895K.com.example.InteractiveReader",
                "com.apple.developer.team-identifier": "3Y7288895K",
                "aps-environment": "development",
                "com.apple.developer.applesignin": ["Default"],
                "com.apple.developer.icloud-container-identifiers": [
                    "iCloud.com.ebook-tools.interactivereader"
                ],
                "com.apple.developer.ubiquity-kvstore-identifier": (
                    "3Y7288895K.com.example.InteractiveReader"
                ),
                "get-task-allow": True,
                "keychain-access-groups": ["3Y7288895K.*"],
            },
        },
    )
    extension_profile = _write_plist(
        profile_dir / "wildcard.mobileprovision",
        {
            "Name": "Wildcard extension profile",
            "Platform": ["iOS"],
            "ExpirationDate": dt.datetime(2099, 1, 1),
            "Entitlements": {
                "application-identifier": "3Y7288895K.*",
                "com.apple.developer.team-identifier": "3Y7288895K",
                "get-task-allow": True,
                "keychain-access-groups": ["3Y7288895K.*"],
            },
        },
    )
    _write_plist(
        profile_dir / "missing-capabilities.mobileprovision",
        {
            "Name": "Old profile without capabilities",
            "Platform": ["iOS"],
            "ExpirationDate": dt.datetime(2099, 1, 1),
            "Entitlements": {
                "application-identifier": "3Y7288895K.com.example.InteractiveReader",
                "com.apple.developer.team-identifier": "3Y7288895K",
                "get-task-allow": True,
            },
        },
    )
    app_entitlements = _write_plist(
        tmp_path / "entitlements" / "app.plist",
        {
            "aps-environment": "development",
            "com.apple.developer.applesignin": ["Default"],
            "com.apple.developer.icloud-container-identifiers": [
                "iCloud.com.ebook-tools.interactivereader"
            ],
            "com.apple.developer.ubiquity-kvstore-identifier": (
                "$(TeamIdentifierPrefix)$(CFBundleIdentifier)"
            ),
        },
    )
    derived_data = tmp_path / "DerivedData-device-full-entitlements"

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--device",
            "TEST-IPAD",
            "--app-entitlements",
            str(app_entitlements),
            "--signing-identity",
            "Apple Development: Test User (TEAMID)",
            "--derived-data",
            str(derived_data),
            "--profile-dir",
            str(profile_dir),
        ],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )

    output = result.stdout
    assert f"Auto-selected app provisioning profile: {app_profile}" in output
    assert f"Auto-selected extension provisioning profile: {extension_profile}" in output
    assert f"cp  {app_profile}" in output
    assert f"cp  {extension_profile}" in output


def test_full_entitlement_signing_plan_execute_builds_and_signs_with_merged_entitlements(
    tmp_path: Path,
) -> None:
    app_profile = _write_plist(
        tmp_path / "profiles" / "app.mobileprovision",
        {
            "Entitlements": {
                "application-identifier": "3Y7288895K.com.example.InteractiveReader",
                "com.apple.developer.team-identifier": "3Y7288895K",
                "get-task-allow": True,
                "keychain-access-groups": ["3Y7288895K.*"],
            }
        },
    )
    extension_profile = _write_plist(
        tmp_path / "profiles" / "extension.mobileprovision",
        {
            "Entitlements": {
                "application-identifier": "3Y7288895K.*",
                "com.apple.developer.team-identifier": "3Y7288895K",
                "get-task-allow": True,
                "keychain-access-groups": ["3Y7288895K.*"],
            }
        },
    )
    app_entitlements = _write_plist(
        tmp_path / "entitlements" / "app.plist",
        {
            "aps-environment": "development",
            "com.apple.developer.applesignin": ["Default"],
            "com.apple.developer.icloud-container-identifiers": [
                "iCloud.com.ebook-tools.interactivereader"
            ],
            "com.apple.developer.ubiquity-kvstore-identifier": (
                "$(TeamIdentifierPrefix)$(CFBundleIdentifier)"
            ),
        },
    )
    derived_data = tmp_path / "DerivedData-device-full-entitlements"
    codesign_log = tmp_path / "codesign.log"
    fake_xcodebuild = _write_executable(
        tmp_path / "bin" / "xcodebuild",
        """#!/usr/bin/env bash
set -euo pipefail
derived=""
configuration="Debug"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -derivedDataPath)
      derived="$2"
      shift 2
      ;;
    -configuration)
      configuration="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
if [[ -z "${derived}" ]]; then
  echo "missing derived data path" >&2
  exit 2
fi
app="${derived}/Build/Products/${configuration}-iphoneos/InteractiveReader.app"
appex="${app}/PlugIns/NotificationServiceExtension.appex"
mkdir -p "${appex}"
touch "${app}/InteractiveReader.debug.dylib"
touch "${app}/__preview.dylib"
touch "${appex}/NotificationServiceExtension.debug.dylib"
touch "${appex}/__preview.dylib"
echo "fake xcodebuild created ${app}"
""",
    )
    fake_codesign = _write_executable(
        tmp_path / "bin" / "codesign",
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "${CODESIGN_LOG}"
""",
    )

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--execute",
            "--device",
            "TEST-IPAD",
            "--app-profile",
            str(app_profile),
            "--extension-profile",
            str(extension_profile),
            "--app-entitlements",
            str(app_entitlements),
            "--signing-identity",
            "Apple Development: Test User (TEAMID)",
            "--derived-data",
            str(derived_data),
            "--configuration",
            "Debug",
        ],
        check=True,
        env={
            **os.environ,
            "XCBUILD": str(fake_xcodebuild),
            "CODESIGN": str(fake_codesign),
            "CODESIGN_LOG": str(codesign_log),
        },
        stdout=subprocess.PIPE,
        text=True,
    )

    app_path = derived_data / "Build/Products/Debug-iphoneos/InteractiveReader.app"
    appex_path = app_path / "PlugIns/NotificationServiceExtension.appex"
    merged_app_entitlements = derived_data / "MergedEntitlements/InteractiveReader.entitlements.plist"
    merged_extension_entitlements = (
        derived_data / "MergedEntitlements/NotificationServiceExtension.entitlements.plist"
    )

    assert "Executing full-entitlement build/sign flow..." in result.stdout
    assert f"Built and signed app: {app_path}" in result.stdout
    assert (app_path / "embedded.mobileprovision").read_bytes() == app_profile.read_bytes()
    assert (appex_path / "embedded.mobileprovision").read_bytes() == extension_profile.read_bytes()

    merged_app = _read_plist(merged_app_entitlements)
    assert merged_app["application-identifier"] == "3Y7288895K.com.example.InteractiveReader"
    assert merged_app["com.apple.developer.icloud-container-identifiers"] == [
        "iCloud.com.ebook-tools.interactivereader"
    ]
    assert (
        merged_app["com.apple.developer.ubiquity-kvstore-identifier"]
        == "3Y7288895K.com.example.InteractiveReader"
    )
    merged_extension = _read_plist(merged_extension_entitlements)
    assert (
        merged_extension["application-identifier"]
        == "3Y7288895K.com.example.InteractiveReader.NotificationServiceExtension"
    )

    sign_log = codesign_log.read_text(encoding="utf-8")
    assert f"--entitlements {merged_extension_entitlements} {appex_path}" in sign_log
    assert f"--entitlements {merged_app_entitlements} {app_path}" in sign_log
    assert f"--verify --deep --strict --verbose=4 {app_path}" in sign_log


def test_full_entitlement_signing_plan_install_requires_execute(tmp_path: Path) -> None:
    app_profile = _touch(tmp_path / "profiles" / "app.mobileprovision")
    extension_profile = _touch(tmp_path / "profiles" / "extension.mobileprovision")
    app_entitlements = _touch(tmp_path / "entitlements" / "app.plist")

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--install",
            "--device",
            "TEST-IPAD",
            "--app-profile",
            str(app_profile),
            "--extension-profile",
            str(extension_profile),
            "--app-entitlements",
            str(app_entitlements),
            "--signing-identity",
            "Apple Development: Test User (TEAMID)",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "--install requires --execute." in result.stderr


def test_full_entitlement_signing_plan_requires_capability_inputs(tmp_path: Path) -> None:
    app_entitlements = _write_plist(
        tmp_path / "entitlements" / "app.plist",
        {"aps-environment": "development"},
    )
    empty_profile_dir = tmp_path / "empty-profile-cache"
    empty_profile_dir.mkdir()

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--device",
            "TEST-IPAD",
            "--app-entitlements",
            str(app_entitlements),
            "--signing-identity",
            "Apple Development: Test User (TEAMID)",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        env={
            **os.environ,
            "APPLE_PROVISIONING_PROFILE_DIRS": str(empty_profile_dir),
        },
    )

    assert result.returncode == 2
    assert "No compatible provisioning profile found for com.example.InteractiveReader" in result.stderr
    assert "Unable to auto-discover app provisioning profile." in result.stderr


def test_make_full_entitlement_plan_target_passes_required_inputs() -> None:
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-n",
            "apple-device-full-entitlement-plan",
            "APPLE_DEVICE_ID=TEST-IPAD",
            "FULL_CAPABILITY_IOS_PROFILE=/tmp/app.mobileprovision",
            "WILDCARD_IOS_EXTENSION_PROFILE=/tmp/extension.mobileprovision",
            "APPLE_DEVELOPMENT_IDENTITY=Apple Development: Test User (TEAMID)",
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )

    output = result.stdout
    assert "bash scripts/apple_full_entitlement_signing_plan.sh" in output
    assert '--device "TEST-IPAD"' in output
    assert '--app-profile "/tmp/app.mobileprovision"' in output
    assert '--extension-profile "/tmp/extension.mobileprovision"' in output
    assert '--signing-identity "Apple Development: Test User (TEAMID)"' in output


def test_make_full_entitlement_plan_omits_empty_profile_overrides() -> None:
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-n",
            "apple-device-full-entitlement-plan",
            "APPLE_DEVICE_ID=TEST-IPAD",
            "APPLE_DEVELOPMENT_IDENTITY=Apple Development: Test User (TEAMID)",
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )

    output = result.stdout
    assert "bash scripts/apple_full_entitlement_signing_plan.sh" in output
    assert '--device "TEST-IPAD"' in output
    assert "--app-profile" not in output
    assert "--extension-profile" not in output
    assert '--signing-identity "Apple Development: Test User (TEAMID)"' in output


def test_make_full_entitlement_execute_targets_pass_required_inputs() -> None:
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-n",
            "apple-device-full-entitlement-build",
            "apple-device-full-entitlement-install",
            "APPLE_DEVICE_ID=TEST-IPAD",
            "FULL_CAPABILITY_IOS_PROFILE=/tmp/app.mobileprovision",
            "WILDCARD_IOS_EXTENSION_PROFILE=/tmp/extension.mobileprovision",
            "APPLE_DEVELOPMENT_IDENTITY=Apple Development: Test User (TEAMID)",
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )

    output = result.stdout
    assert output.count("bash scripts/apple_full_entitlement_signing_plan.sh") == 2
    assert output.count("--execute") == 2
    assert "--install" in output
    assert '--device "TEST-IPAD"' in output
    assert '--app-profile "/tmp/app.mobileprovision"' in output
    assert '--extension-profile "/tmp/extension.mobileprovision"' in output
    assert '--signing-identity "Apple Development: Test User (TEAMID)"' in output


def test_make_full_entitlement_execute_targets_omit_empty_profile_overrides() -> None:
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-n",
            "apple-device-full-entitlement-build",
            "apple-device-full-entitlement-install",
            "APPLE_DEVICE_ID=TEST-IPAD",
            "APPLE_DEVELOPMENT_IDENTITY=Apple Development: Test User (TEAMID)",
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )

    output = result.stdout
    assert output.count("bash scripts/apple_full_entitlement_signing_plan.sh") == 2
    assert output.count("--execute") == 2
    assert "--install" in output
    assert "--app-profile" not in output
    assert "--extension-profile" not in output
    assert output.count('--signing-identity "Apple Development: Test User (TEAMID)"') == 2


def test_make_full_entitlement_fallback_install_target_passes_guarded_inputs() -> None:
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-n",
            "apple-device-full-entitlement-fallback-install",
            "APPLE_DEVICE_PROFILE=ipad",
            "APPLE_DEVICE_ID=TEST-IPAD",
            "APPLE_DEVICE_SIGNED_ARTIFACT_PATH=/tmp/InteractiveReader.app",
            "APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT=12",
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )

    output = result.stdout
    assert "bash scripts/apple_unattended_device_update.sh" in output
    assert '--profile "ipad"' in output
    assert '--device "TEST-IPAD"' in output
    assert "--install" in output
    assert "--launch" in output
    assert '--launch-console-timeout "12"' in output
    assert "--fallback-to-signed-artifact" in output
    assert '--signed-artifact-path "/tmp/InteractiveReader.app"' in output


def test_make_full_entitlement_stable_install_target_passes_guarded_inputs() -> None:
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-n",
            "apple-device-full-entitlement-stable-install",
            "APPLE_DEVICE_PROFILE=ipad",
            "APPLE_DEVICE_ID=TEST-IPAD",
            "APPLE_DEVICE_SIGNED_ARTIFACT_PATH=/tmp/InteractiveReader.app",
            "APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT=12",
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )

    output = result.stdout
    assert "bash scripts/apple_unattended_device_update.sh" in output
    assert '--profile "ipad"' in output
    assert '--device "TEST-IPAD"' in output
    assert "--skip-build" in output
    assert '--app-path "/tmp/InteractiveReader.app"' in output
    assert "--install" in output
    assert "--launch" in output
    assert '--launch-console-timeout "12"' in output
    assert "--fallback-to-signed-artifact" in output
    assert '--signed-artifact-path "/tmp/InteractiveReader.app"' in output
