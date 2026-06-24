from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
CONTRACT_CHECK = ROOT / "scripts" / "check_apple_local_surface_build_helper.sh"
TESTING_DOC = ROOT / "docs" / "testing.md"
DEVELOPER_DOC = ROOT / "docs" / "developer-guide.md"
PLAN_DOC = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"


def test_local_surface_build_gate_chains_non_physical_apple_targets() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    target_line = (
        "build-apple-local-surfaces: build-apple-ios-simulators "
        "build-apple-tvos-simulator build-apple-macos-ipad-style"
    )
    assert target_line in makefile
    assert "build-apple-ios-simulators: build-apple-iphone-simulator build-apple-ipad-simulator" in makefile
    assert "build-apple-tvos-simulator:" in makefile
    assert "build-apple-macos-ipad-style:" in makefile

    target = makefile.split("build-apple-local-surfaces:", 1)[1].split("\n\n", 1)[0]
    assert "apple-device-update" not in target
    assert "apple_unattended_device_update.sh" not in target
    assert "devicectl" not in target
    assert "--install" not in target


def test_local_surface_contract_check_covers_aggregate_gate() -> None:
    contract_check = CONTRACT_CHECK.read_text(encoding="utf-8")

    assert "build-apple-local-surfaces" in contract_check
    assert "build-apple-ios-simulators" in contract_check
    assert "build-apple-tvos-simulator" in contract_check
    assert "build-apple-macos-ipad-style" in contract_check
    assert "physical-device deployment" in contract_check


def test_docs_publish_local_surface_build_gate() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    developer_doc = DEVELOPER_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "make build-apple-local-surfaces" in docs
    assert "make build-apple-local-surfaces" in developer_doc
    assert "local Apple surface build gate" in plan
