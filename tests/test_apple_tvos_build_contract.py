from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
CONTRACT_CHECK = ROOT / "scripts" / "check_apple_tvos_build_helper.sh"
TESTING_DOC = ROOT / "docs" / "testing.md"
PLAN_DOC = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"
LIBRARY_BROWSE_CHROME = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "LibraryBrowseChrome.swift"
)
CREATE_ROUTING = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateRouting.swift"
)


def test_tvos_simulator_build_lane_is_repo_owned_and_non_deploying() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "build-apple-tvos-simulator:" in makefile
    assert "$(XCBUILD) -quiet build" in makefile
    assert "-scheme InteractiveReaderTV" in makefile
    assert "-destination $(TVOS_DESTINATION)" in makefile
    assert "TVOS_BUILD_DERIVED_DATA" in makefile

    target = makefile.split("build-apple-tvos-simulator:", 1)[1].split("\n\n", 1)[0]
    assert "apple_unattended_device_update.sh" not in target
    assert "devicectl" not in target
    assert "--install" not in target


def test_tvos_contract_check_covers_compile_lane() -> None:
    contract_check = CONTRACT_CHECK.read_text(encoding="utf-8")

    assert "build-apple-tvos-simulator:" in contract_check
    assert "InteractiveReaderTV" in contract_check
    assert "TVOS_DESTINATION" in contract_check
    assert "physical-device deployment" in contract_check


def test_docs_publish_tvos_compile_gate() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "make build-apple-tvos-simulator" in docs
    assert "tvOS simulator compile lane" in plan


def test_tvos_native_create_is_reachable_and_uses_shared_modes() -> None:
    browse_source = LIBRARY_BROWSE_CHROME.read_text(encoding="utf-8")
    routing_source = CREATE_ROUTING.read_text(encoding="utf-8")

    assert "[.jobs, .create, .library, .settings, .search]" in browse_source
    assert "AppleCreateMode.allCases" in routing_source
    assert "isTV ? []" not in routing_source
