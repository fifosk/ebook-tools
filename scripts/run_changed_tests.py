#!/usr/bin/env python3
"""Run focused test targets for the current Git changes."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]

BROAD_CHANGE_PREFIXES = (
    ".github/",
    "alembic/",
    "config/",
    "docker/",
    "helm/",
    "monitoring/",
)

BROAD_CHANGE_FILES = {
    "pyproject.toml",
    "tests/conftest.py",
    "docker-compose.yml",
}

RELEASE_METADATA_ONLY_FILES = {
    "CHANGELOG.md",
    "ios/InteractiveReader/InteractiveReader/Features/Shared/AppChangelogData.swift",
    "ios/InteractiveReader/InteractiveReader/Supporting/Info.plist",
    "ios/InteractiveReader/InteractiveReader/Supporting/Info-tvOS.plist",
    "ios/InteractiveReader/NotificationServiceExtension/Info.plist",
}

SIMULATOR_BUILD_TARGETS = {
    "build-apple-ios-simulators",
    "build-apple-tvos-simulator",
}

PATH_TARGET_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        (
            "CHANGELOG.md",
            "ios/InteractiveReader/InteractiveReader.xcodeproj/project.pbxproj",
            "ios/InteractiveReader/InteractiveReader/Features/Shared/AppChangelogData.swift",
            "ios/InteractiveReader/InteractiveReader/Features/Shared/AppVersion.swift",
            "ios/InteractiveReader/InteractiveReader/Supporting/Info.plist",
            "ios/InteractiveReader/InteractiveReader/Supporting/Info-tvOS.plist",
            "ios/InteractiveReader/NotificationServiceExtension/Info.plist",
            "scripts/check_release_version_contract.py",
            "tests/test_release_version_contract.py",
        ),
        ("test-release-version",),
    ),
    (
        (
            "tests/e2e/journeys/",
        ),
        ("test-apple-contracts", "check-web-e2e-journeys"),
    ),
    (
        (
            "tests/e2e/journey_runner.py",
            "scripts/check_web_e2e_journeys.py",
            "tests/scripts/test_check_web_e2e_journeys.py",
        ),
        ("check-web-e2e-journeys",),
    ),
    (
        (
            "scripts/check_apple_shared_pipeline_helper.sh",
            "scripts/check_apple_shared_pipeline_manifest.py",
            "tests/test_apple_shared_pipeline_contract.py",
            "tests/scripts/test_check_apple_shared_pipeline_manifest.py",
        ),
        ("test-apple-contracts", "apple-pipeline-orchestration-dry-runs"),
    ),
    (
        (
            "modules/webapi/runtime_descriptor.py",
            "tests/test_apple_runtime_descriptor_contract.py",
            "scripts/check_apple_runtime_descriptor_payload.sh",
            "scripts/tests/check_apple_runtime_descriptor_payload.swift",
        ),
        ("test-backend-runtime-descriptor", "test-apple-contracts"),
    ),
    (
        (
            "scripts/check_apple_create_readiness.py",
            "src/check_poc_readiness.py",
            "tests/scripts/test_check_apple_create_readiness.py",
            "tests/scripts/test_check_poc_readiness.py",
        ),
        ("test-backend-runtime-descriptor", "test-apple-contracts"),
    ),
    (
        (
            "tests/modules/webapi/test_system_routes.py",
        ),
        ("test-backend-runtime-descriptor",),
    ),
    (
        (
            "modules/webapi/routes/jobs_routes.py",
            "modules/webapi/schemas/pipeline_jobs.py",
            "modules/services/pipeline_service.py",
            "modules/services/job_manager/",
            "tests/modules/webapi/test_dashboard_access_control.py",
            "tests/modules/services/test_job_manager_access_control.py",
            "tests/modules/services/test_job_manager_transitions.py",
        ),
        ("test-backend-pipeline-jobs",),
    ),
    (
        (
            "modules/services/creation_template_service.py",
            "modules/webapi/routers/creation_templates.py",
            "modules/webapi/schemas/creation_templates.py",
            "tests/modules/webapi/test_creation_template_routes.py",
            "tests/test_apple_create_split_layout.py",
        ),
        ("test-backend-creation-templates", "test-apple-contracts"),
    ),
    (
        (
            "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/",
            "ios/InteractiveReader/InteractiveReader/Services/SequencePlaybackController.swift",
            "scripts/check_apple_audio_mode_manager.sh",
            "scripts/check_apple_sentence_position_provider.sh",
            "scripts/check_apple_playback_mode_switch_integration.sh",
            "scripts/check_apple_sequence_pause_cancel.sh",
            "scripts/check_apple_transcript_display_snapshots.sh",
            "scripts/check_apple_interactive_context_builder.sh",
            "scripts/check_apple_reader_navigation_contract.sh",
            "scripts/tests/check_playback_mode_switch_integration.swift",
            "scripts/tests/check_transcript_display_snapshots.swift",
            "tests/test_apple_playback_search_bookmark_contract.py",
            "tests/test_apple_playback_state_helpers_contract.py",
        ),
        ("test-apple-playback-state-swift",),
    ),
    (
        (
            "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView.swift",
            "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView+",
            "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractiveTranscriptView",
            "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/TextPlayer",
            "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/JumpControlOverlayView.swift",
            "ios/InteractiveReader/InteractiveReader/Features/Playback/",
        ),
        ("build-apple-ios-simulators", "build-apple-tvos-simulator"),
    ),
    (
        (
            "ios/InteractiveReader/InteractiveReader/Features/Create/",
            "ios/InteractiveReader/InteractiveReader/Services/APIClient+Creation.swift",
        ),
        (
            "test-apple-create-readiness-contract",
            "build-apple-ios-simulators",
            "build-apple-tvos-simulator",
        ),
    ),
    (
        (
            "ios/InteractiveReader/InteractiveReader/Features/Jobs/",
            "ios/InteractiveReader/InteractiveReader/Features/Library/",
            "ios/InteractiveReader/InteractiveReader/Services/APIClient+LibraryJobs.swift",
        ),
        ("build-apple-ios-simulators", "build-apple-tvos-simulator"),
    ),
    (
        (
            "ios/InteractiveReader/InteractiveReader/Services/",
        ),
        ("build-apple-ios-simulators", "build-apple-tvos-simulator"),
    ),
    (
        (
            "ios/InteractiveReader/InteractiveReader/App/",
            "ios/InteractiveReader/InteractiveReader/Models/",
            "ios/InteractiveReader/InteractiveReader/Utilities/",
            "ios/InteractiveReader/InteractiveReader/Features/Shared/",
        ),
        ("build-apple-ios-simulators", "build-apple-tvos-simulator"),
    ),
    (
        (
            "ios/",
            "docs/developer-guide.md",
            "docs/deployment.md",
            "docs/frontend-sync.md",
            "docs/interactive_reader_metadata.md",
            "docs/plans/cross-surface-parity-and-optimization.md",
            "docs/sentence_images.md",
            "docs/testing.md",
            "scripts/apple_full_entitlement_signing_plan.sh",
            "scripts/apple_merge_entitlements.py",
            "scripts/apple_unattended_device_update.sh",
            "scripts/check_apple_",
            "scripts/check_mac_studio_runtime_checkout.sh",
            "scripts/fast_forward_mac_studio_runtime_checkout.sh",
            "scripts/ios_e2e_report.py",
            "scripts/ios_profile_capability_check.py",
            "tests/test_apple_",
            "tests/scripts/test_apple_",
            "tests/scripts/test_check_apple_",
            "tests/scripts/test_check_poc_readiness.py",
            "tests/scripts/test_generate_language_catalogs.py",
            "tests/scripts/test_ios_e2e_report.py",
            "tests/scripts/test_ios_profile_capability_check.py",
            "tests/scripts/test_write_apple_e2e_config.py",
        ),
        ("test-apple-contracts",),
    ),
    (
        (
            "tests/e2e/journeys/music_bed_sync.json",
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
        ),
        (
            "test-e2e-ipad-music-bed-sync-dry-run",
            "test-e2e-tvos-music-bed-sync-dry-run",
        ),
    ),
    (
        (
            "docs/plans/discovery-acquisition-layer.md",
            "modules/services/source_discovery.py",
            "modules/services/acquisition/",
            "modules/webapi/routers/acquisition.py",
            "modules/webapi/schemas/acquisition.py",
            "tests/modules/services/test_source_discovery.py",
            "tests/modules/services/test_acquisition_providers.py",
            "tests/modules/webapi/test_acquisition_routes.py",
        ),
        ("test-backend-pipeline-sources", "test-backend-acquisition"),
    ),
    (
        (
            "docs/plans/discovery-acquisition-layer.md",
            "modules/epub_parser.py",
            "modules/core/ingestion.py",
            "tests/test_sentence_splitting.py",
            "tests/test_epub_parser_sections.py",
            "tests/modules/core/test_ingestion_content_index_cache.py",
            "tests/modules/core/test_pipeline_config_sentence_splitter.py",
        ),
        ("test-pipeline",),
    ),
    (
        (
            "modules/webapi/routers/reading_beds.py",
            "modules/webapi/schemas/reading_beds.py",
            "tests/modules/webapi/test_reading_bed_routes.py",
        ),
        ("test-backend-reading-beds",),
    ),
    (
        (
            "modules/notifications/",
            "modules/webapi/routes/notification_routes.py",
            "tests/modules/test_notification_service.py",
            "tests/modules/webapi/test_notification_routes.py",
        ),
        ("test-backend-notifications",),
    ),
    (
        (
            "modules/services/assistant.py",
            "modules/services/bookmark_service.py",
            "modules/services/pg_bookmark_service.py",
            "modules/services/pg_resume_service.py",
            "modules/services/resume_service.py",
            "modules/services/pipeline_phases/lookup_cache_phase.py",
            "modules/webapi/routers/assistant.py",
            "modules/webapi/routers/bookmarks.py",
            "modules/webapi/routers/resume.py",
            "modules/webapi/routes/media/lookup_cache.py",
            "modules/webapi/schemas/assistant.py",
            "modules/webapi/schemas/bookmarks.py",
            "modules/webapi/schemas/resume.py",
            "tests/modules/test_resume_service.py",
            "tests/modules/webapi/test_assistant_routes.py",
            "tests/modules/webapi/test_bookmark_routes.py",
            "tests/modules/webapi/test_lookup_cache_routes.py",
            "tests/modules/webapi/test_resume_routes.py",
        ),
        ("test-backend-playback-state",),
    ),
    (
        (
            "modules/services/export_service.py",
            "modules/webapi/routers/exports.py",
            "modules/webapi/schemas/exports.py",
            "tests/modules/services/test_export_service.py",
            "tests/modules/webapi/test_export_routes.py",
        ),
        ("test-backend-offline-export",),
    ),
    (
        (
            "web/src/components/PlayerPanel.tsx",
            "web/src/components/player-panel/",
            "web/src/components/__tests__/PlayerPanel",
            "web/src/components/__tests__/playerPanel",
            "web/src/components/__tests__/TranscriptView",
            "web/src/components/__tests__/TranscriptWord",
            "web/src/components/__tests__/usePlayerPanel",
            "web/src/components/__tests__/VideoPlayer.test.tsx",
            "web/src/components/__tests__/YoutubeDubPlayer.test.tsx",
            "web/src/components/interactive-text/",
            "web/src/components/transcript/",
            "web/src/components/video-subtitles/",
            "web/src/lib/playback/",
            "web/src/lib/media/",
        ),
        ("test-web-playback-focused",),
    ),
    (
        (
            "web/src/api/client/media.ts",
            "web/src/api/client/runtimeContract.ts",
        ),
        ("test-web-playback-focused", "test-apple-contracts"),
    ),
    (
        (
            "web/src/components/AuthProvider.tsx",
            "web/src/components/ChangePasswordForm.tsx",
            "web/src/components/LoginForm.tsx",
            "web/src/components/LoginServerStatus.tsx",
            "web/src/components/RegisterForm.tsx",
            "web/src/components/__tests__/AuthFlows.test.tsx",
            "web/src/components/app/AuthScreen.tsx",
        ),
        ("test-web-auth-focused",),
    ),
    (
        (
            "web/src/api/client/auth.ts",
            "web/src/api/client/runtimeContract.ts",
        ),
        ("test-web-auth-focused", "test-apple-contracts"),
    ),
    (
        (
            "web/src/api/client/admin.ts",
        ),
        ("test-web-admin-focused", "test-apple-contracts"),
    ),
    (
        (
            "web/src/components/admin/",
            "web/src/components/__tests__/SystemPanel.test.tsx",
            "web/src/components/__tests__/UserManagementPanel.test.tsx",
            "web/src/components/__tests__/SidebarAdminLinks.test.tsx",
        ),
        ("test-web-admin-focused",),
    ),
    (
        (
            "web/src/components/Sidebar.tsx",
            "web/src/components/sidebar/",
            "web/src/components/__tests__/Sidebar",
            "web/src/components/__tests__/sidebarUtils.test.ts",
        ),
        ("test-web-sidebar-focused",),
    ),
    (
        (
            "web/src/pages/CreateBookPage.tsx",
            "web/src/pages/__tests__/CreateBookPage.test.tsx",
            "web/src/pages/__tests__/createBookPageUtils.test.ts",
        ),
        ("test-web-create-book-focused",),
    ),
    (
        (
            "web/src/api/createBook.ts",
            "web/src/api/client/runtimeContract.ts",
        ),
        ("test-web-create-book-focused", "test-apple-contracts"),
    ),
    (
        (
            "web/src/components/book-narration/",
            "web/src/components/create-intake/",
            "web/src/components/__tests__/BookNarration",
            "web/src/components/__tests__/bookNarration",
            "web/src/components/__tests__/createIntakeStatusUtils.test.ts",
            "web/src/components/__tests__/useBookNarration",
            "web/src/pages/NewImmersiveBookPage.tsx",
        ),
        ("test-web-create-intake-focused",),
    ),
    (
        (
            "web/src/api/client/creationTemplates.ts",
            "web/src/api/client/runtimeContract.ts",
            "web/src/api/client/__tests__/creationTemplates.test.ts",
            "web/src/utils/creationTemplateSanitizer.ts",
            "web/src/utils/__tests__/creationTemplateSanitizer.test.ts",
        ),
        ("test-web-creation-templates-focused", "test-apple-contracts"),
    ),
    (
        (
            "web/src/api/dtos.ts",
        ),
        ("test-web-creation-templates-focused", "test-apple-contracts"),
    ),
    (
        (
            "web/src/components/LibraryList",
            "web/src/components/LibraryToolbar",
            "web/src/components/library-list/",
            "web/src/components/__tests__/Library",
            "web/src/components/__tests__/libraryList",
            "web/src/hooks/useLibraryMedia.ts",
            "web/src/pages/LibraryPage",
            "web/src/pages/library/",
            "web/src/pages/__tests__/libraryPageMetadata.test.ts",
            "web/src/api/client/__tests__/resume.test.ts",
        ),
        ("test-web-library-focused",),
    ),
    (
        (
            "web/src/api/client/library.ts",
        ),
        ("test-web-library-focused", "test-apple-contracts"),
    ),
    (
        (
            "web/src/api/client/resume.ts",
            "web/src/api/client/runtimeContract.ts",
        ),
        ("test-web-library-focused", "test-apple-contracts"),
    ),
    (
        (
            "web/src/components/JobProgress.tsx",
            "web/src/components/JobStatusBadge.tsx",
            "web/src/components/job-progress/",
            "web/src/components/__tests__/JobProgress.test.tsx",
            "web/src/components/__tests__/JobStatusBadge.test.tsx",
            "web/src/components/__tests__/jobProgress",
            "web/src/api/client/__tests__/jobs.test.ts",
            "web/src/utils/progressEvents.ts",
            "web/src/utils/__tests__/progressEvents.test.ts",
        ),
        ("test-web-job-progress-focused",),
    ),
    (
        (
            "web/src/api/client/jobs.ts",
            "web/src/api/client/runtimeContract.ts",
        ),
        ("test-web-job-progress-focused", "test-apple-contracts"),
    ),
    (
        (
            "web/src/pages/VideoDubbingPage",
            "web/src/pages/YoutubeVideoPage",
            "web/src/pages/video-dubbing/",
            "web/src/pages/__tests__/VideoDubbingPage.test.tsx",
            "web/src/pages/__tests__/YoutubeVideoPage.test.tsx",
            "web/src/pages/__tests__/videoDubbing",
            "web/src/pages/__tests__/useVideoDubbing",
            "web/src/pages/__tests__/VideoDownloadStationPanel.test.tsx",
        ),
        ("test-web-video-dubbing-focused",),
    ),
    (
        (
            "web/src/api/client/subtitles.ts",
            "web/src/api/client/runtimeContract.ts",
            "web/src/api/client/__tests__/subtitles.test.ts",
        ),
        (
            "test-web-video-dubbing-focused",
            "test-web-subtitle-tool-focused",
            "test-apple-contracts",
        ),
    ),
    (
        (
            "web/src/pages/SubtitleToolPage",
            "web/src/pages/subtitle-tool/",
            "web/src/pages/__tests__/SubtitleTool",
            "web/src/pages/__tests__/subtitle",
            "web/src/pages/__tests__/useSubtitle",
        ),
        ("test-web-subtitle-tool-focused",),
    ),
    (
        (
            "web/src/utils/appViewDeepLink.ts",
            "web/src/utils/__tests__/appViewDeepLink.test.ts",
            "web/src/utils/creationTemplatePayloadExtras.ts",
            "web/src/utils/__tests__/creationTemplatePayloadExtras.test.ts",
        ),
        ("test-web-app-view-deeplink-focused",),
    ),
    (("web/",), ("test-web-full", "build-web-production")),
    (("modules/webapi/", "tests/modules/webapi/"), ("test-webapi",)),
    (("modules/services/", "tests/modules/services/"), ("test-services",)),
    (("modules/audio/", "tests/modules/audio/"), ("test-audio",)),
    (("modules/translation/", "tests/modules/translation/"), ("test-translation",)),
    (("modules/library/", "tests/modules/library/"), ("test-library",)),
    (("modules/render/", "tests/render/", "tests/modules/render/"), ("test-render",)),
    (("modules/media/", "tests/modules/media/"), ("test-media",)),
    (("modules/config", "config/", "tests/modules/config", "tests/modules/config_manager/"), ("test-config",)),
    (("modules/metadata", "tests/modules/metadata", "tests/test_library_metadata"), ("test-metadata",)),
    (("modules/search/",), ("test-backend-library-search-source-isbn",)),
    ((".gitignore", "Makefile", "docs/developer-guide.md", "docs/plans/cross-surface-parity-and-optimization.md", "docs/testing.md", "PLAN.md", "AGENTS.md", "scripts/run_changed_tests.py", "scripts/write_git_checkpoint_bundle.py", "tests/test_makefile_pytest_contract.py", "tests/test_apple_shared_pipeline_contract.py", "tests/test_web_video_dubbing_pipeline_contract.py", "tests/scripts/test_run_changed_tests.py", "tests/scripts/test_write_git_checkpoint_bundle.py"), ("test-makefile-contract",)),
)


def _run_git(args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def changed_paths(base: str) -> list[str]:
    paths: set[str] = set()
    for args in (
        ["diff", "--name-only", "--diff-filter=ACMR", base, "--"],
        ["diff", "--name-only", "--diff-filter=ACMR", "--cached", "--"],
        ["ls-files", "--others", "--exclude-standard"],
    ):
        paths.update(_run_git(args))
    return sorted(paths)


def _matches(path: str, prefixes: Iterable[str]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def select_targets(paths: Iterable[str]) -> list[str]:
    normalized = sorted({path.strip().lstrip("./") for path in paths if path.strip()})
    if not normalized:
        return ["test-fast"]

    if any(path in BROAD_CHANGE_FILES or _matches(path, BROAD_CHANGE_PREFIXES) for path in normalized):
        return ["test-fast"]

    targets: list[str] = []
    for prefixes, candidate_targets in PATH_TARGET_RULES:
        if any(_matches(path, prefixes) for path in normalized):
            for target in candidate_targets:
                if target not in targets:
                    targets.append(target)

    if targets and all(path in RELEASE_METADATA_ONLY_FILES for path in normalized):
        targets = [target for target in targets if target not in SIMULATOR_BUILD_TARGETS]

    if targets:
        return _order_targets_for_feedback(targets)
    return ["test-fast"]


def _order_targets_for_feedback(targets: list[str]) -> list[str]:
    """Run non-Xcode checks before simulator builds so host issues don't hide contract failures."""
    non_simulator = [target for target in targets if target not in SIMULATOR_BUILD_TARGETS]
    simulator = [target for target in targets if target in SIMULATOR_BUILD_TARGETS]
    return non_simulator + simulator


def run_targets(targets: list[str], *, dry_run: bool) -> int:
    print("Selected test targets: " + " ".join(targets), flush=True)
    if dry_run:
        return 0
    for target in targets:
        result = subprocess.run(["make", target], cwd=REPO_ROOT)
        if result.returncode:
            return result.returncode
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default="HEAD",
        help="Git base revision for changed path detection. Defaults to HEAD.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected targets without running them.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional explicit paths to classify instead of reading Git changes.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    paths = args.paths or changed_paths(args.base)
    return run_targets(select_targets(paths), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
