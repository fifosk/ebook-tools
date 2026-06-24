from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
CONTRACT_CHECK = ROOT / "scripts" / "check_apple_ios_build_helper.sh"
TESTING_DOC = ROOT / "docs" / "testing.md"
DEVELOPER_DOC = ROOT / "docs" / "developer-guide.md"
PLAN_DOC = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"


def _target_block(makefile: str, target: str) -> str:
    return makefile.split(f"{target}:", 1)[1].split("\n\n", 1)[0]


def test_ios_simulator_build_lanes_are_repo_owned_and_non_deploying() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "build-apple-iphone-simulator:" in makefile
    assert "build-apple-ipad-simulator:" in makefile
    assert "build-apple-ios-simulators: build-apple-iphone-simulator build-apple-ipad-simulator" in makefile

    for target, destination, derived_data in [
        ("build-apple-iphone-simulator", "IPHONE_DESTINATION", "IPHONE_BUILD_DERIVED_DATA"),
        ("build-apple-ipad-simulator", "IPAD_DESTINATION", "IPAD_BUILD_DERIVED_DATA"),
    ]:
        block = _target_block(makefile, target)
        assert "$(XCBUILD) -quiet build" in block
        assert "-scheme InteractiveReader" in block
        assert f"-destination $({destination})" in block
        assert f"-derivedDataPath $({derived_data})" in block
        assert "apple_unattended_device_update.sh" not in block
        assert "devicectl" not in block
        assert "--install" not in block


def test_ios_contract_check_covers_compile_lanes() -> None:
    contract_check = CONTRACT_CHECK.read_text(encoding="utf-8")

    assert "build-apple-iphone-simulator:" in contract_check
    assert "build-apple-ipad-simulator:" in contract_check
    assert "build-apple-ios-simulators" in contract_check
    assert "physical-device deployment" in contract_check


def test_docs_publish_ios_compile_gates() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    developer_doc = DEVELOPER_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "make build-apple-iphone-simulator" in docs
    assert "make build-apple-ipad-simulator" in docs
    assert "make build-apple-ios-simulators" in docs
    assert "make build-apple-ios-simulators" in developer_doc
    assert "iPhone/iPad simulator compile lanes" in plan
