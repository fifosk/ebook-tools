import ast
from pathlib import Path

from scripts.run_changed_tests import select_targets


ROOT = Path(__file__).resolve().parents[2]


def _path_parts_from_ast(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name) and node.id == "ROOT":
        return []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _path_parts_from_ast(node.left) + _path_parts_from_ast(node.right)
    raise AssertionError(f"Unsupported path expression: {ast.dump(node)}")


def _runtime_descriptor_web_client_paths() -> dict[str, str]:
    source = (ROOT / "tests" / "test_apple_runtime_descriptor_contract.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    paths: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if not (target.id.startswith("WEB_") and target.id.endswith("_CLIENT")):
                continue
            path = "/".join(_path_parts_from_ast(node.value))
            if path.startswith("web/"):
                paths[target.id] = path
    return paths


def test_select_targets_for_apple_surface_changes() -> None:
    assert select_targets(["ios/InteractiveReader/InteractiveReader/App/RootView.swift"]) == [
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
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
        "test-e2e-ipad-music-bed-sync-dry-run",
        "test-e2e-tvos-music-bed-sync-dry-run",
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
    assert select_targets(["docs/developer-guide.md"]) == [
        "test-apple-contracts",
        "test-makefile-contract",
    ]
    assert select_targets(["docs/deployment.md"]) == ["test-apple-contracts"]
    assert select_targets(["docs/frontend-sync.md"]) == ["test-apple-contracts"]
    assert select_targets(["docs/interactive_reader_metadata.md"]) == [
        "test-apple-contracts"
    ]
    assert select_targets(["docs/sentence_images.md"]) == ["test-apple-contracts"]
    assert select_targets(["docs/testing.md"]) == [
        "test-apple-contracts",
        "test-makefile-contract",
    ]
    assert select_targets(["docs/plans/cross-surface-parity-and-optimization.md"]) == [
        "test-apple-contracts",
        "test-makefile-contract",
    ]


def test_select_targets_runs_music_bed_dry_runs_for_reader_transport_paths() -> None:
    music_bed_paths = [
        "ios/InteractiveReader/InteractiveReader/Features/Playback/JobPlaybackView.swift",
        "ios/InteractiveReader/InteractiveReader/Features/Playback/JobPlaybackView+NowPlaying.swift",
        "ios/InteractiveReader/InteractiveReader/Features/Playback/JobPlaybackView+Resume.swift",
        "ios/InteractiveReader/InteractiveReader/Features/Playback/LibraryPlaybackView.swift",
        "ios/InteractiveReader/InteractiveReader/Features/Playback/LibraryPlaybackView+NowPlaying.swift",
        "ios/InteractiveReader/InteractiveReader/Features/Playback/LibraryPlaybackView+Resume.swift",
        "ios/InteractiveReader/InteractiveReader/Features/Playback/LibraryPlaybackChromeViews.swift",
        "ios/InteractiveReader/InteractiveReader/Features/Playback/ReaderTransportCommandResolver.swift",
        "ios/InteractiveReader/InteractiveReaderUITests/JourneyRunner.swift",
        "ios/InteractiveReader/InteractiveReader/Services/MusicKitCoordinator.swift",
    ]

    for path in music_bed_paths:
        targets = select_targets([path])
        assert "test-e2e-ipad-music-bed-sync-dry-run" in targets, path
        assert "test-e2e-tvos-music-bed-sync-dry-run" in targets, path


def test_select_targets_for_apple_swiftui_surfaces_builds_local_simulators() -> None:
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView+HeaderOverlay.swift"]
    ) == [
        "test-apple-playback-state-swift",
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateView.swift"]
    ) == [
        "test-apple-create-readiness-contract",
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Services/APIClient+Creation.swift"]
    ) == [
        "test-apple-create-readiness-contract",
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Features/Playback/VideoPlayerView+Layout.swift"]
    ) == [
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Features/Playback/JobPlaybackView+NowPlaying.swift"]
    ) == [
        "test-apple-contracts",
        "test-e2e-ipad-music-bed-sync-dry-run",
        "test-e2e-tvos-music-bed-sync-dry-run",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Features/Playback/LibraryPlaybackChromeViews.swift"]
    ) == [
        "test-apple-contracts",
        "test-e2e-ipad-music-bed-sync-dry-run",
        "test-e2e-tvos-music-bed-sync-dry-run",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Features/Jobs/JobsView.swift"]
    ) == [
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Features/Library/LibraryView.swift"]
    ) == [
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Features/Library/PlaybackSettingsView.swift"]
    ) == [
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Services/APIClient+LibraryJobs.swift"]
    ) == [
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Services/MusicKitCoordinator.swift"]
    ) == [
        "test-apple-contracts",
        "test-e2e-ipad-music-bed-sync-dry-run",
        "test-e2e-tvos-music-bed-sync-dry-run",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Services/APIClient+Notifications.swift"]
    ) == [
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Services/SequencePlaybackController.swift"]
    ) == [
        "test-apple-playback-state-swift",
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(["ios/InteractiveReader/InteractiveReader/Models/AuthApiModels.swift"]) == [
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(["ios/InteractiveReader/InteractiveReader/Utilities/MediaURLResolver.swift"]) == [
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]
    assert select_targets(["ios/InteractiveReader/InteractiveReader/Features/Shared/AppTheme.swift"]) == [
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]


def test_select_targets_orders_contracts_before_simulator_builds() -> None:
    assert select_targets(
        ["ios/InteractiveReader/InteractiveReader/Services/APIClient+Notifications.swift"]
    ) == [
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
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
    ) == [
        "test-release-version",
        "test-apple-contracts",
    ]
    assert select_targets(
        [
            "CHANGELOG.md",
            "ios/InteractiveReader/InteractiveReader/Features/Shared/AppChangelogData.swift",
        ]
    ) == [
        "test-release-version",
        "test-apple-contracts",
    ]
    assert select_targets(
        [
            "ios/InteractiveReader/InteractiveReader/Features/Shared/AppChangelogData.swift",
            "ios/InteractiveReader/InteractiveReader/Features/Shared/AppTheme.swift",
        ]
    ) == [
        "test-release-version",
        "test-apple-contracts",
        "build-apple-ios-simulators",
        "build-apple-tvos-simulator",
    ]


def test_select_targets_for_web_changes_runs_web_checks() -> None:
    assert select_targets(["web/src/pages/LibraryPage.tsx"]) == [
        "test-web-library-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/api/client/library.ts"]) == [
        "test-web-library-focused",
        "test-apple-contracts",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/api/client/resume.ts"]) == [
        "test-web-library-focused",
        "test-apple-contracts",
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
    assert select_targets(["web/src/components/__tests__/usePendingChunkSelection.test.tsx"]) == [
        "test-web-playback-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/components/transcript/TranscriptView.tsx"]) == [
        "test-web-playback-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/components/__tests__/TranscriptViewAccessibility.test.tsx"]) == [
        "test-web-playback-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/components/interactive-text/inlineSentenceSkip.ts"]) == [
        "test-web-playback-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/lib/playback/sequencePlan.ts"]) == [
        "test-web-playback-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/api/client/media.ts"]) == [
        "test-web-playback-focused",
        "test-apple-contracts",
        "test-web-full",
        "build-web-production",
    ]


def test_runtime_descriptor_web_clients_select_apple_contracts() -> None:
    paths = _runtime_descriptor_web_client_paths()
    assert paths == {
        "WEB_ADMIN_CLIENT": "web/src/api/client/admin.ts",
        "WEB_AUTH_CLIENT": "web/src/api/client/auth.ts",
        "WEB_CREATE_BOOK_CLIENT": "web/src/api/createBook.ts",
        "WEB_CREATION_TEMPLATES_CLIENT": "web/src/api/client/creationTemplates.ts",
        "WEB_JOBS_CLIENT": "web/src/api/client/jobs.ts",
        "WEB_LIBRARY_CLIENT": "web/src/api/client/library.ts",
        "WEB_MEDIA_CLIENT": "web/src/api/client/media.ts",
        "WEB_RESUME_CLIENT": "web/src/api/client/resume.ts",
        "WEB_RUNTIME_CONTRACT_CLIENT": "web/src/api/client/runtimeContract.ts",
        "WEB_SUBTITLES_CLIENT": "web/src/api/client/subtitles.ts",
    }
    for name, path in sorted(paths.items()):
        assert "test-apple-contracts" in select_targets([path]), name


def test_select_targets_covers_focused_web_feature_slices() -> None:
    assert select_targets(["web/src/api/client/auth.ts"]) == [
        "test-web-auth-focused",
        "test-apple-contracts",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/api/client/runtimeContract.ts"]) == [
        "test-web-playback-focused",
        "test-apple-contracts",
        "test-web-auth-focused",
        "test-web-create-book-focused",
        "test-web-creation-templates-focused",
        "test-web-library-focused",
        "test-web-job-progress-focused",
        "test-web-video-dubbing-focused",
        "test-web-subtitle-tool-focused",
        "test-web-full",
        "build-web-production",
    ]
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
    assert select_targets(["web/src/api/client/admin.ts"]) == [
        "test-web-admin-focused",
        "test-apple-contracts",
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
    assert select_targets(["web/src/api/createBook.ts"]) == [
        "test-web-create-book-focused",
        "test-apple-contracts",
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
        "test-apple-contracts",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/api/dtos.ts"]) == [
        "test-web-creation-templates-focused",
        "test-apple-contracts",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/components/JobProgress.tsx"]) == [
        "test-web-job-progress-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/api/client/jobs.ts"]) == [
        "test-web-job-progress-focused",
        "test-apple-contracts",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/pages/VideoDubbingPage.tsx"]) == [
        "test-web-video-dubbing-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/api/client/subtitles.ts"]) == [
        "test-web-video-dubbing-focused",
        "test-web-subtitle-tool-focused",
        "test-apple-contracts",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/api/client/__tests__/subtitles.test.ts"]) == [
        "test-web-video-dubbing-focused",
        "test-web-subtitle-tool-focused",
        "test-apple-contracts",
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
    assert select_targets(["web/src/utils/creationTemplatePayloadExtras.ts"]) == [
        "test-web-app-view-deeplink-focused",
        "test-web-full",
        "build-web-production",
    ]
    assert select_targets(["web/src/utils/__tests__/creationTemplatePayloadExtras.test.ts"]) == [
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
    assert select_targets(["modules/webapi/runtime_descriptor.py"]) == [
        "test-backend-runtime-descriptor",
        "test-apple-contracts",
        "test-webapi",
    ]
    assert select_targets(["src/check_poc_readiness.py"]) == [
        "test-backend-runtime-descriptor",
        "test-apple-contracts",
    ]
    assert select_targets(["scripts/check_apple_create_readiness.py"]) == [
        "test-backend-runtime-descriptor",
        "test-apple-contracts",
    ]
    assert select_targets(["tests/modules/webapi/test_system_routes.py"]) == [
        "test-backend-runtime-descriptor",
        "test-webapi",
    ]
    assert select_targets(["tests/test_apple_runtime_descriptor_contract.py"]) == [
        "test-backend-runtime-descriptor",
        "test-apple-contracts",
    ]
    assert select_targets(["tests/scripts/test_check_poc_readiness.py"]) == [
        "test-backend-runtime-descriptor",
        "test-apple-contracts",
    ]
    assert select_targets(["tests/scripts/test_check_apple_create_readiness.py"]) == [
        "test-backend-runtime-descriptor",
        "test-apple-contracts",
    ]
    assert select_targets(["scripts/check_apple_runtime_descriptor_payload.sh"]) == [
        "test-backend-runtime-descriptor",
        "test-apple-contracts",
    ]
    assert select_targets(["modules/webapi/schemas/creation_templates.py"]) == [
        "test-backend-creation-templates",
        "test-apple-contracts",
        "test-webapi",
    ]
    assert select_targets(["modules/services/creation_template_service.py"]) == [
        "test-backend-creation-templates",
        "test-apple-contracts",
        "test-services",
    ]
    assert select_targets(["tests/test_apple_create_split_layout.py"]) == [
        "test-backend-creation-templates",
        "test-apple-contracts",
    ]
    assert select_targets(["modules/webapi/routes/jobs_routes.py"]) == [
        "test-backend-pipeline-jobs",
        "test-webapi",
    ]
    assert select_targets(["modules/webapi/schemas/pipeline_jobs.py"]) == [
        "test-backend-pipeline-jobs",
        "test-webapi",
    ]
    assert select_targets(["modules/services/job_manager/manager.py"]) == [
        "test-backend-pipeline-jobs",
        "test-services",
    ]
    assert select_targets(["tests/modules/webapi/test_dashboard_access_control.py"]) == [
        "test-backend-pipeline-jobs",
        "test-webapi",
    ]
    assert select_targets(["modules/webapi/routers/create_book.py"]) == [
        "test-backend-create-book",
        "test-webapi",
    ]
    assert select_targets(["modules/webapi/schemas/create_book.py"]) == [
        "test-backend-create-book",
        "test-webapi",
    ]
    assert select_targets(["tests/test_create_book.py"]) == [
        "test-backend-create-book",
        "test-backend-pipeline-sources",
    ]
    assert select_targets(["modules/webapi/routes/books_routes.py"]) == [
        "test-backend-pipeline-sources",
        "test-webapi",
    ]
    assert select_targets(["modules/webapi/schemas/pipeline_files.py"]) == [
        "test-backend-pipeline-sources",
        "test-webapi",
    ]
    assert select_targets(["modules/webapi/routers/reading_beds.py"]) == [
        "test-backend-reading-beds",
        "test-webapi",
    ]
    assert select_targets(["modules/webapi/schemas/reading_beds.py"]) == [
        "test-backend-reading-beds",
        "test-webapi",
    ]
    assert select_targets(["modules/webapi/routers/subtitles.py"]) == [
        "test-backend-subtitle-router",
        "test-webapi",
    ]
    assert select_targets(["tests/webapi/test_subtitles_router.py"]) == [
        "test-backend-subtitle-router",
    ]
    assert select_targets(["tests/modules/webapi/test_subtitle_metadata_token_safe_routes.py"]) == [
        "test-backend-subtitle-router",
        "test-webapi",
    ]
    assert select_targets(["modules/webapi/routers/subtitle_utils/youtube_routes.py"]) == [
        "test-backend-youtube-dubbing-service",
        "test-webapi",
    ]
    assert select_targets(["modules/services/youtube_dubbing/service.py"]) == [
        "test-backend-youtube-dubbing-service",
        "test-services",
    ]
    assert select_targets(["tests/modules/webapi/test_youtube_library_route.py"]) == [
        "test-backend-youtube-dubbing-service",
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
    assert select_targets(["tests/modules/services/test_export_service.py"]) == [
        "test-backend-offline-export",
        "test-services",
    ]


def test_select_targets_covers_acquisition_discovery_layer() -> None:
    assert select_targets(["docs/plans/discovery-acquisition-layer.md"]) == [
        "test-backend-pipeline-sources",
        "test-backend-acquisition",
        "test-pipeline",
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


def test_select_targets_covers_sentence_splitting_and_content_index_quality() -> None:
    assert select_targets(["modules/epub_parser.py"]) == ["test-pipeline"]
    assert select_targets(["modules/core/ingestion.py"]) == ["test-pipeline"]
    assert select_targets(["tests/test_sentence_splitting.py"]) == ["test-pipeline"]
    assert select_targets(["tests/test_epub_parser_sections.py"]) == ["test-pipeline"]
    assert select_targets(["tests/modules/core/test_ingestion_content_index_cache.py"]) == [
        "test-pipeline"
    ]
    assert select_targets(["tests/modules/core/test_pipeline_config_sentence_splitter.py"]) == [
        "test-pipeline"
    ]


def test_select_targets_uses_fast_suite_for_broad_config_changes() -> None:
    assert select_targets(["pyproject.toml"]) == ["test-fast"]


def test_select_targets_covers_makefile_contract_changes() -> None:
    assert select_targets([
        ".gitignore",
        "Makefile",
        "scripts/run_changed_tests.py",
        "scripts/write_git_checkpoint_bundle.py",
        "tests/test_web_video_dubbing_pipeline_contract.py",
        "tests/scripts/test_write_git_checkpoint_bundle.py",
    ]) == [
        "test-makefile-contract"
    ]


def test_select_targets_defaults_to_fast_suite_for_unknown_or_no_paths() -> None:
    assert select_targets([]) == ["test-fast"]
    assert select_targets(["README.md"]) == ["test-fast"]
