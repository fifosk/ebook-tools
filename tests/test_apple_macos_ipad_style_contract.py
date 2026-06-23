from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
HELPER = ROOT / "scripts" / "apple_build_macos_ipad_style.sh"
CONTRACT_CHECK = ROOT / "scripts" / "check_apple_macos_ipad_style_helper.sh"
TESTING_DOC = ROOT / "docs" / "testing.md"


def test_macos_ipad_style_make_targets_match_pipeline_profiles() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "build-apple-macos-ipad-style:" in makefile
    assert "\tbash scripts/apple_build_macos_ipad_style.sh\n" in makefile
    assert "build-apple-macos-ipad-style-dry-run:" in makefile
    assert "\tbash scripts/apple_build_macos_ipad_style.sh --dry-run\n" in makefile
    assert "apple-macos-ipad-destination:" in makefile
    assert "\tbash scripts/apple_build_macos_ipad_style.sh --show-destination\n" in makefile


def test_macos_ipad_style_helper_stays_non_deploying() -> None:
    helper = HELPER.read_text(encoding="utf-8")

    assert "Designed for iPad/iPhone" in helper
    assert "--dry-run" in helper
    assert "--show-destination" in helper
    assert "No physical device is used." in helper
    assert "xcrun devicectl" not in helper
    assert "--install" not in helper


def test_macos_ipad_style_contract_check_covers_profile_commands() -> None:
    contract_check = CONTRACT_CHECK.read_text(encoding="utf-8")

    assert "bash -n \"${HELPER}\"" in contract_check
    assert "--show-destination" in contract_check
    assert "--dry-run" in contract_check
    assert "FAKE_BUILD_OK" in contract_check


def test_testing_docs_publish_shared_pipeline_profile_names() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")

    assert "--profile macos-ipad-style-dry-run --dry-run" in docs
    assert "--profile macos-ipad-style --dry-run" in docs
    assert "make build-apple-macos-ipad-style" in docs
