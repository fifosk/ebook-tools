from scripts.run_changed_tests import select_targets


def test_select_targets_for_apple_surface_changes() -> None:
    assert select_targets(["ios/InteractiveReader/InteractiveReader/App/RootView.swift"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(["tests/scripts/test_check_apple_e2e_config.py"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(["scripts/check_apple_e2e_config.py"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(["tests/e2e/journeys/music_bed_sync.json"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(["scripts/check_mac_studio_runtime_checkout.sh"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(["scripts/fast_forward_mac_studio_runtime_checkout.sh"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(["scripts/apple_unattended_device_update.sh"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(["scripts/check_apple_device_update_helper.sh"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(["scripts/check_apple_music_bed_launch_log.py"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(["docs/deployment.md"]) == ["test-apple-contracts"]
    assert select_targets(["docs/testing.md"]) == [
        "test-apple-contracts",
        "test-makefile-contract",
    ]


def test_select_targets_for_release_metadata_changes() -> None:
    assert select_targets(["CHANGELOG.md"]) == ["test-release-version"]
    assert select_targets(["scripts/check_release_version_contract.py"]) == [
        "test-release-version"
    ]
    assert select_targets(["tests/test_release_version_contract.py"]) == [
        "test-release-version"
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Supporting/Info.plist"]
    ) == ["test-release-version", "test-apple-contracts"]
    assert select_targets(
        [
            "ios/InteractiveReader/InteractiveReader/Features/Shared/AppChangelogData.swift"
        ]
    ) == ["test-release-version", "test-apple-contracts"]


def test_select_targets_for_web_changes_runs_web_checks() -> None:
    assert select_targets(["web/src/pages/LibraryPage.tsx"]) == [
        "test-web-full",
        "build-web-production",
    ]


def test_select_targets_deduplicates_multiple_backend_domains() -> None:
    assert select_targets(
        [
            "modules/webapi/routers/library.py",
            "tests/modules/webapi/test_library_items_route.py",
            "modules/services/resume_service.py",
        ]
    ) == ["test-webapi", "test-services"]


def test_select_targets_uses_fast_suite_for_broad_config_changes() -> None:
    assert select_targets(["pyproject.toml"]) == ["test-fast"]


def test_select_targets_covers_makefile_contract_changes() -> None:
    assert select_targets([
        ".gitignore",
        "Makefile",
        "scripts/run_changed_tests.py",
        "tests/test_web_video_dubbing_pipeline_contract.py",
    ]) == [
        "test-makefile-contract"
    ]


def test_select_targets_defaults_to_fast_suite_for_unknown_or_no_paths() -> None:
    assert select_targets([]) == ["test-fast"]
    assert select_targets(["README.md"]) == ["test-fast"]
