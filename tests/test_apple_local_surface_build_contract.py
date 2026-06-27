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


def test_office_ipad_surface_build_gate_avoids_iphone_and_physical_devices() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    target_line = (
        "build-apple-office-ipad-surfaces: build-apple-ipad-simulator "
        "build-apple-macos-ipad-style"
    )
    assert target_line in makefile
    assert "build-apple-ipad-simulator:" in makefile
    assert "build-apple-macos-ipad-style:" in makefile

    target = makefile.split("build-apple-office-ipad-surfaces:", 1)[1].split("\n\n", 1)[0]
    assert "build-apple-iphone-simulator" not in target
    assert "build-apple-ios-simulators" not in target
    assert "apple-device-update" not in target
    assert "apple_unattended_device_update.sh" not in target
    assert "devicectl" not in target
    assert "--install" not in target


def test_local_surface_verification_gate_chains_contracts_and_builds_only() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    target_line = (
        "verify-apple-local-surfaces: test-apple-contracts "
        "build-apple-local-surfaces build-apple-ios-uitests build-apple-tvos-uitests"
    )
    assert target_line in makefile

    target = makefile.split("verify-apple-local-surfaces:", 1)[1].split("\n\n", 1)[0]
    assert "apple-device-update" not in target
    assert "apple_unattended_device_update.sh" not in target
    assert "devicectl" not in target
    assert "--install" not in target


def test_cross_surface_checkpoint_chains_web_and_apple_without_physical_devices() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    target_line = (
        "verify-apple-cross-surface-checkpoint: test-backend-auth-session "
        "test-backend-library-search-source-isbn test-backend-admin-system-status "
        "test-backend-runtime-descriptor test-backend-create-book "
        "test-backend-creation-templates test-backend-pipeline-sources "
        "test-backend-acquisition test-backend-audio-routes "
        "test-backend-reading-beds test-backend-notifications "
        "test-backend-subtitle-router test-backend-playback-state "
        "test-backend-playback-media test-backend-offline-export "
        "test-backend-youtube-dubbing-service test-web-auth-focused "
        "test-web-admin-focused test-web-sidebar-focused "
        "test-web-create-book-focused test-web-create-intake-focused "
        "test-web-creation-templates-focused test-web-library-focused "
        "test-web-job-progress-focused test-web-playback-focused "
        "test-web-video-dubbing-focused test-web-subtitle-tool-focused "
        "test-web-app-view-deeplink-focused test-web-full build-web-production "
        "verify-apple-local-surfaces"
    )
    assert target_line in makefile
    assert "test-backend-auth-session:" in makefile
    assert "test-backend-library-search-source-isbn:" in makefile
    assert "test-backend-admin-system-status:" in makefile
    assert "test-backend-runtime-descriptor:" in makefile
    assert "test-backend-create-book:" in makefile
    assert "test-backend-creation-templates:" in makefile
    assert "test-backend-pipeline-sources:" in makefile
    assert "test-backend-acquisition:" in makefile
    assert "test-backend-audio-routes:" in makefile
    assert "test-backend-reading-beds:" in makefile
    assert "test-backend-notifications:" in makefile
    assert "test-backend-subtitle-router:" in makefile
    assert "test-backend-playback-state:" in makefile
    assert "test-backend-playback-media:" in makefile
    assert "test-backend-offline-export:" in makefile
    assert "test-backend-youtube-dubbing-service:" in makefile
    assert "build-web-production:" in makefile
    assert "test-web-auth-focused:" in makefile
    assert "test-web-admin-focused:" in makefile
    assert "test-web-sidebar-focused:" in makefile
    assert "test-web-create-book-focused:" in makefile
    assert "test-web-create-intake-focused:" in makefile
    assert "test-web-creation-templates-focused:" in makefile
    assert "test-web-library-focused:" in makefile
    assert "test-web-job-progress-focused:" in makefile
    assert "test-web-playback-focused:" in makefile
    assert "test-web-video-dubbing-focused:" in makefile
    assert "test-web-subtitle-tool-focused:" in makefile
    assert "test-web-app-view-deeplink-focused:" in makefile
    assert "test-web-full:" in makefile
    assert "verify-apple-local-surfaces:" in makefile

    target = makefile.split("verify-apple-cross-surface-checkpoint:", 1)[1].split("\n\n", 1)[0]
    assert "test-backend-auth-session" in target
    assert "test-backend-library-search-source-isbn" in target
    assert "test-backend-admin-system-status" in target
    assert "test-backend-runtime-descriptor" in target
    assert "test-backend-create-book" in target
    assert "test-backend-creation-templates" in target
    assert "test-backend-pipeline-sources" in target
    assert "test-backend-acquisition" in target
    assert "test-backend-audio-routes" in target
    assert "test-backend-reading-beds" in target
    assert "test-backend-notifications" in target
    assert "test-backend-subtitle-router" in target
    assert "test-backend-playback-state" in target
    assert "test-backend-playback-media" in target
    assert "test-backend-offline-export" in target
    assert "test-backend-youtube-dubbing-service" in target
    assert "test-web-auth-focused" in target
    assert "test-web-admin-focused" in target
    assert "test-web-sidebar-focused" in target
    assert "test-web-create-book-focused" in target
    assert "test-web-create-intake-focused" in target
    assert "test-web-creation-templates-focused" in target
    assert "test-web-library-focused" in target
    assert "test-web-job-progress-focused" in target
    assert "test-web-playback-focused" in target
    assert "test-web-video-dubbing-focused" in target
    assert "test-web-subtitle-tool-focused" in target
    assert "test-web-app-view-deeplink-focused" in target
    assert "test-web-full" in target
    assert "build-web-production" in target
    assert "verify-apple-local-surfaces" in target
    assert "apple-device-update" not in target
    assert "apple_unattended_device_update.sh" not in target
    assert "devicectl" not in target
    assert "--install" not in target


def test_office_ipad_surface_verification_gate_chains_contracts_and_ipad_builds_only() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    target_line = (
        "verify-apple-office-ipad-surfaces: test-apple-contracts "
        "build-apple-office-ipad-surfaces build-apple-ios-uitests"
    )
    assert target_line in makefile

    target = makefile.split("verify-apple-office-ipad-surfaces:", 1)[1].split("\n\n", 1)[0]
    assert "build-apple-iphone-simulator" not in target
    assert "build-apple-ios-simulators" not in target
    assert "apple-device-update" not in target
    assert "apple_unattended_device_update.sh" not in target
    assert "devicectl" not in target
    assert "--install" not in target


def test_local_surface_contract_check_covers_aggregate_gate() -> None:
    contract_check = CONTRACT_CHECK.read_text(encoding="utf-8")

    assert "build-apple-local-surfaces" in contract_check
    assert "verify-apple-local-surfaces" in contract_check
    assert "verify-apple-cross-surface-checkpoint" in contract_check
    assert "build-apple-office-ipad-surfaces" in contract_check
    assert "verify-apple-office-ipad-surfaces" in contract_check
    assert "build-apple-ios-simulators" in contract_check
    assert "build-apple-ios-uitests" in contract_check
    assert "build-apple-tvos-uitests" in contract_check
    assert "build-apple-tvos-simulator" in contract_check
    assert "build-apple-macos-ipad-style" in contract_check
    assert "physical-device deployment" in contract_check


def test_docs_publish_local_surface_build_gate() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    developer_doc = DEVELOPER_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "make build-apple-local-surfaces" in docs
    assert "make verify-apple-local-surfaces" in docs
    assert "make verify-apple-cross-surface-checkpoint" in docs
    assert "make build-apple-tvos-uitests" in docs
    assert "make build-apple-office-ipad-surfaces" in docs
    assert "make verify-apple-office-ipad-surfaces" in docs
    assert "make build-apple-local-surfaces" in developer_doc
    assert "make verify-apple-local-surfaces" in developer_doc
    assert "make verify-apple-cross-surface-checkpoint" in developer_doc
    assert "make build-apple-tvos-uitests" in developer_doc
    assert "make build-apple-office-ipad-surfaces" in developer_doc
    assert "make verify-apple-office-ipad-surfaces" in developer_doc
    assert "local Apple surface build gate" in plan
    assert "local Apple verification gate" in plan
    assert "tvOS UITest build-for-testing lane" in plan
    assert "cross-surface checkpoint gate" in plan
    assert "office-iPad local build gate" in plan
    assert "office-iPad local verification gate" in plan
