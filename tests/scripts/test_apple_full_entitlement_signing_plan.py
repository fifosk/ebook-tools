from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "apple_full_entitlement_signing_plan.sh"


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("placeholder", encoding="utf-8")
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

    assert "Full-entitlement iPhone/iPad signing plan" in output
    assert "Unsigned device build:" in output
    assert "-destination  generic/platform=iOS" in output
    assert "CODE_SIGNING_ALLOWED=NO" in output
    assert f"{app_path}/embedded.mobileprovision" in output
    assert f"{appex_path}/embedded.mobileprovision" in output
    assert "Sign extension dylibs:" in output
    assert "Sign notification extension:" in output
    assert f"--entitlements  {extension_entitlements}" in output
    assert "Sign app with full entitlements:" in output
    assert f"--entitlements  {app_entitlements}" in output
    assert "Verify signed app:" in output
    assert "Final guarded install command:" in output
    assert "CONFIRM_PHYSICAL_DEVICE_UPDATE=YES" in output
    assert "apple_unattended_device_update.sh" in output
    assert "--skip-build" in output
    assert f"--app-path  {app_path}" in output
    assert "--install" in output
    assert "--launch-console-timeout  12" in output
    assert "devicectl" not in output


def test_full_entitlement_signing_plan_requires_capability_inputs(tmp_path: Path) -> None:
    app_entitlements = _touch(tmp_path / "entitlements" / "app.plist")

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
    )

    assert result.returncode == 2
    assert "FULL_CAPABILITY_IOS_PROFILE or --app-profile is required." in result.stderr


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
