from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "apple_merge_entitlements.py"


def _write_plist(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        plistlib.dump(payload, handle)
    return path


def _read_plist(path: Path) -> dict:
    with path.open("rb") as handle:
        return plistlib.load(handle)


def test_merge_app_entitlements_expands_project_macros_and_profile_values(tmp_path: Path) -> None:
    profile = _write_plist(
        tmp_path / "app.mobileprovision",
        {
            "Entitlements": {
                "application-identifier": "3Y7288895K.com.example.InteractiveReader",
                "com.apple.developer.team-identifier": "3Y7288895K",
                "get-task-allow": True,
                "keychain-access-groups": ["3Y7288895K.*"],
            }
        },
    )
    project = _write_plist(
        tmp_path / "InteractiveReader.entitlements",
        {
            "aps-environment": "development",
            "com.apple.developer.applesignin": ["Default"],
            "com.apple.developer.icloud-container-identifiers": [
                "iCloud.com.ebook-tools.interactivereader"
            ],
            "com.apple.developer.icloud-services": ["CloudDocuments", "CloudKit"],
            "com.apple.developer.ubiquity-container-identifiers": [
                "iCloud.com.ebook-tools.interactivereader"
            ],
            "com.apple.developer.ubiquity-kvstore-identifier": (
                "$(TeamIdentifierPrefix)$(CFBundleIdentifier)"
            ),
        },
    )
    output = tmp_path / "merged-app.plist"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--profile",
            str(profile),
            "--bundle-id",
            "com.example.InteractiveReader",
            "--project-entitlements",
            str(project),
            "--output",
            str(output),
        ],
        check=True,
    )

    payload = _read_plist(output)
    assert payload["application-identifier"] == "3Y7288895K.com.example.InteractiveReader"
    assert payload["com.apple.developer.team-identifier"] == "3Y7288895K"
    assert payload["get-task-allow"] is True
    assert payload["keychain-access-groups"] == ["3Y7288895K.com.example.InteractiveReader"]
    assert payload["aps-environment"] == "development"
    assert payload["com.apple.developer.applesignin"] == ["Default"]
    assert payload["com.apple.developer.icloud-services"] == ["CloudDocuments", "CloudKit"]
    assert (
        payload["com.apple.developer.ubiquity-kvstore-identifier"]
        == "3Y7288895K.com.example.InteractiveReader"
    )


def test_merge_extension_entitlements_expands_wildcard_profile(tmp_path: Path) -> None:
    profile = _write_plist(
        tmp_path / "extension.mobileprovision",
        {
            "Entitlements": {
                "application-identifier": "3Y7288895K.*",
                "com.apple.developer.team-identifier": "3Y7288895K",
                "get-task-allow": True,
                "keychain-access-groups": ["3Y7288895K.*"],
            }
        },
    )
    output = tmp_path / "merged-extension.plist"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--profile",
            str(profile),
            "--bundle-id",
            "com.example.InteractiveReader.NotificationServiceExtension",
            "--output",
            str(output),
        ],
        check=True,
    )

    payload = _read_plist(output)
    assert (
        payload["application-identifier"]
        == "3Y7288895K.com.example.InteractiveReader.NotificationServiceExtension"
    )
    assert payload["com.apple.developer.team-identifier"] == "3Y7288895K"
    assert payload["get-task-allow"] is True
    assert payload["keychain-access-groups"] == [
        "3Y7288895K.com.example.InteractiveReader.NotificationServiceExtension"
    ]
