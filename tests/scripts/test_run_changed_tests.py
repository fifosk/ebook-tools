from scripts.run_changed_tests import select_targets


def test_select_targets_for_apple_surface_changes() -> None:
    assert select_targets(["ios/InteractiveReader/InteractiveReader/App/RootView.swift"]) == [
        "test-apple-contracts"
    ]


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
    assert select_targets(["Makefile", "scripts/run_changed_tests.py"]) == [
        "test-makefile-contract"
    ]


def test_select_targets_defaults_to_fast_suite_for_unknown_or_no_paths() -> None:
    assert select_targets([]) == ["test-fast"]
    assert select_targets(["README.md"]) == ["test-fast"]
