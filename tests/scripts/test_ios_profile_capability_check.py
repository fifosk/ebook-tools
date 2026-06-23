from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ios_profile_capability_check.py"
SPEC = importlib.util.spec_from_file_location("ios_profile_capability_check", SCRIPT)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _profile(app_id: str, entitlements: dict[str, object] | None = None) -> dict[str, object]:
    return _profile_for_platform(app_id, "iOS", entitlements)


def _profile_for_platform(
    app_id: str,
    platform: str,
    entitlements: dict[str, object] | None = None,
) -> dict[str, object]:
    payload_entitlements = {"application-identifier": f"3Y7288895K.{app_id}"}
    payload_entitlements.update(entitlements or {})
    return {
        "Name": f"Profile {app_id}",
        "UUID": f"uuid-{app_id}",
        "TeamIdentifier": ["3Y7288895K"],
        "Platform": [platform],
        "Entitlements": payload_entitlements,
    }


def test_profile_matches_exact_and_wildcard_bundle_ids() -> None:
    exact = _profile("com.example.InteractiveReader")
    wildcard = _profile("*")
    prefix_wildcard = _profile("com.example.*")

    assert MODULE.profile_matches_bundle(exact, "com.example.InteractiveReader")
    assert MODULE.profile_matches_bundle(wildcard, "com.example.InteractiveReader.NotificationServiceExtension")
    assert MODULE.profile_matches_bundle(prefix_wildcard, "com.example.InteractiveReader")
    assert not MODULE.profile_matches_bundle(exact, "com.example.Other")


def test_profile_platform_filter_rejects_tvos_for_ios_profiles() -> None:
    ios = _profile_for_platform("*", "iOS")
    tvos = _profile_for_platform("*", "tvOS")

    assert MODULE.profile_matches_platform(ios, "iOS")
    assert not MODULE.profile_matches_platform(tvos, "iOS")


def test_matching_profiles_accepts_wildcard_profiles_for_embedded_bundles(
    tmp_path: Path,
    monkeypatch,
) -> None:
    exact_path = tmp_path / "exact.mobileprovision"
    wildcard_path = tmp_path / "wildcard.mobileprovision"
    unrelated_path = tmp_path / "unrelated.mobileprovision"
    for path in [exact_path, wildcard_path, unrelated_path]:
        path.write_bytes(b"placeholder")

    profiles = {
        exact_path: _profile("com.example.InteractiveReader"),
        wildcard_path: _profile("*"),
        unrelated_path: _profile_for_platform("*", "tvOS"),
    }

    monkeypatch.setattr(MODULE, "decode_mobileprovision", lambda path: profiles[path])

    matches = MODULE.matching_profiles(
        "com.example.InteractiveReader.NotificationServiceExtension",
        [tmp_path],
    )

    assert matches == [(wildcard_path, profiles[wildcard_path])]


def test_check_profiles_for_bundle_requires_declared_entitlement_values(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    profile_path = tmp_path / "reader.mobileprovision"
    profile_path.write_bytes(b"placeholder")
    profile = _profile(
        "com.example.InteractiveReader",
        {
            "aps-environment": "development",
            "com.apple.developer.applesignin": ["Default"],
        },
    )
    monkeypatch.setattr(MODULE, "decode_mobileprovision", lambda path: profile)

    ok = MODULE.check_profiles_for_bundle(
        bundle_id="com.example.InteractiveReader",
        expected_entitlements={
            "aps-environment": "development",
            "com.apple.developer.applesignin": ["Default"],
            "com.apple.developer.icloud-container-identifiers": [
                "iCloud.com.ebook-tools.interactivereader"
            ],
        },
        profile_dirs=[tmp_path],
        label="reader",
        require_entitlement_values=True,
    )

    output = capsys.readouterr().out
    assert not ok
    assert "missing: com.apple.developer.icloud-container-identifiers" in output


def test_check_profiles_for_embedded_bundle_accepts_wildcard_without_entitlements(
    tmp_path: Path,
    monkeypatch,
) -> None:
    profile_path = tmp_path / "wildcard.mobileprovision"
    profile_path.write_bytes(b"placeholder")
    monkeypatch.setattr(MODULE, "decode_mobileprovision", lambda path: _profile("*"))

    ok = MODULE.check_profiles_for_bundle(
        bundle_id="com.example.InteractiveReader.NotificationServiceExtension",
        expected_entitlements={},
        profile_dirs=[tmp_path],
        label="extension",
        require_entitlement_values=False,
    )

    assert ok
