from scripts.run_changed_tests import select_targets


def test_select_targets_for_apple_surface_changes() -> None:
    assert select_targets(["ios/InteractiveReader/InteractiveReader/App/RootView.swift"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(
        [
            "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerViewModel+Sequence.swift"
        ]
    ) == [
        "test-apple-playback-state-swift",
        "test-apple-contracts",
    ]
    assert select_targets(["scripts/check_apple_reader_navigation_contract.sh"]) == [
        "test-apple-playback-state-swift",
        "test-apple-contracts",
    ]
    assert select_targets(["tests/test_apple_playback_state_helpers_contract.py"]) == [
        "test-apple-playback-state-swift",
        "test-apple-contracts",
    ]
    assert select_targets(["tests/scripts/test_check_apple_e2e_config.py"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(["scripts/check_apple_e2e_config.py"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(["tests/e2e/journeys/music_bed_sync.json"]) == [
        "test-apple-contracts",
        "check-web-e2e-journeys",
    ]
    assert select_targets(["tests/e2e/journey_runner.py"]) == [
        "check-web-e2e-journeys",
    ]
    assert select_targets(["scripts/check_web_e2e_journeys.py"]) == [
        "check-web-e2e-journeys",
    ]
    assert select_targets(["tests/scripts/test_check_web_e2e_journeys.py"]) == [
        "check-web-e2e-journeys",
    ]
    assert select_targets(["scripts/ios_e2e_report.py"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(["tests/scripts/test_ios_e2e_report.py"]) == [
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
    assert select_targets(["scripts/check_apple_shared_pipeline_helper.sh"]) == [
        "test-apple-contracts",
        "apple-pipeline-orchestration-dry-runs",
    ]
    assert select_targets(["scripts/check_apple_shared_pipeline_manifest.py"]) == [
        "test-apple-contracts",
        "apple-pipeline-orchestration-dry-runs",
    ]
    assert select_targets(["tests/test_apple_shared_pipeline_contract.py"]) == [
        "test-apple-contracts",
        "apple-pipeline-orchestration-dry-runs",
        "test-makefile-contract",
    ]
    assert select_targets(["tests/scripts/test_check_apple_shared_pipeline_manifest.py"]) == [
        "test-apple-contracts",
        "apple-pipeline-orchestration-dry-runs",
    ]
    assert select_targets(["docs/deployment.md"]) == ["test-apple-contracts"]
    assert select_targets(["docs/frontend-sync.md"]) == ["test-apple-contracts"]
    assert select_targets(["docs/testing.md"]) == [
        "test-apple-contracts",
        "test-makefile-contract",
    ]
    assert select_targets(["docs/plans/cross-surface-parity-and-optimization.md"]) == [
        "test-apple-contracts",
        "test-makefile-contract",
    ]


def test_select_targets_for_apple_swiftui_surfaces_builds_local_simulators() -> None:
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView+HeaderOverlay.swift"]
    ) == [
        "test-apple-playback-state-swift",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
        "test-apple-contracts",
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Features/Playback/VideoPlayerView+Layout.swift"]
    ) == [
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
        "test-apple-contracts",
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
        "test-web-library-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/components/player-panel/usePlayerPanelTextActivation.ts"]) == [
        "test-web-playback-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/components/__tests__/usePlayerPanelTextActivation.test.tsx"]) == [
        "test-web-playback-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/lib/playback/sequencePlan.ts"]) == [
        "test-web-playback-focused",
        "test-web-full",
        "build-web-production",
    ]


def test_select_targets_covers_focused_web_feature_slices() -> None:
    assert select_targets(["web/src/components/LoginForm.tsx"]) == [
        "test-web-auth-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/components/admin/UserManagementPanel.tsx"]) == [
        "test-web-admin-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/components/sidebar/sidebarUtils.ts"]) == [
        "test-web-sidebar-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/pages/CreateBookPage.tsx"]) == [
        "test-web-create-book-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/components/book-narration/BookNarrationForm.tsx"]) == [
        "test-web-create-intake-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/api/client/creationTemplates.ts"]) == [
        "test-web-creation-templates-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/components/JobProgress.tsx"]) == [
        "test-web-job-progress-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/pages/VideoDubbingPage.tsx"]) == [
        "test-web-video-dubbing-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/pages/subtitle-tool/useSubtitleSubmit.ts"]) == [
        "test-web-subtitle-tool-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/utils/appViewDeepLink.ts"]) == [
        "test-web-app-view-deeplink-focused",
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
    ) == ["test-backend-playback-state", "test-webapi", "test-services"]


def test_select_targets_covers_apple_runtime_backend_slices() -> None:
    assert select_targets(["modules/webapi/routers/reading_beds.py"]) == [
        "test-backend-reading-beds",
        "test-webapi",
    ]
    assert select_targets(["modules/webapi/schemas/reading_beds.py"]) == [
        "test-backend-reading-beds",
        "test-webapi",
    ]
    assert select_targets(["modules/notifications/notification_service.py"]) == [
        "test-backend-notifications",
    ]
    assert select_targets(["modules/webapi/routes/notification_routes.py"]) == [
        "test-backend-notifications",
        "test-webapi",
    ]
    assert select_targets(["modules/webapi/routers/bookmarks.py"]) == [
        "test-backend-playback-state",
        "test-webapi",
    ]
    assert select_targets(["modules/services/bookmark_service.py"]) == [
        "test-backend-playback-state",
        "test-services",
    ]
    assert select_targets(["modules/webapi/routes/media/lookup_cache.py"]) == [
        "test-backend-playback-state",
        "test-webapi",
    ]
    assert select_targets(["modules/webapi/routers/exports.py"]) == [
        "test-backend-offline-export",
        "test-webapi",
    ]
    assert select_targets(["modules/services/export_service.py"]) == [
        "test-backend-offline-export",
        "test-services",
    ]


def test_select_targets_covers_acquisition_discovery_layer() -> None:
    assert select_targets(["docs/plans/discovery-acquisition-layer.md"]) == [
        "test-backend-pipeline-sources",
        "test-backend-acquisition"
    ]
    assert select_targets(["modules/services/source_discovery.py"]) == [
        "test-backend-pipeline-sources",
        "test-backend-acquisition",
        "test-services",
    ]
    assert select_targets(["tests/modules/services/test_source_discovery.py"]) == [
        "test-backend-pipeline-sources",
        "test-backend-acquisition",
        "test-services",
    ]
    assert select_targets(["modules/services/acquisition/discovery.py"]) == [
        "test-backend-pipeline-sources",
        "test-backend-acquisition",
        "test-services",
    ]
    assert select_targets(["modules/webapi/routers/acquisition.py"]) == [
        "test-backend-pipeline-sources",
        "test-backend-acquisition",
        "test-webapi",
    ]
    assert select_targets(["modules/webapi/schemas/acquisition.py"]) == [
        "test-backend-pipeline-sources",
        "test-backend-acquisition",
        "test-webapi",
    ]
    assert select_targets(["tests/modules/webapi/test_acquisition_routes.py"]) == [
        "test-backend-pipeline-sources",
        "test-backend-acquisition",
        "test-webapi",
    ]


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
