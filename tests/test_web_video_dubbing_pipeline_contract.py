import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
TESTING_DOC = ROOT / "docs" / "testing.md"
GITIGNORE = ROOT / ".gitignore"
EXPORT_DIST = ROOT / "web" / "export-dist"
PLAN_DOC = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"
PIPELINE_MANIFEST = (
    Path("/Users/fifo/Projects/home/apple-device-app-pipeline")
    / "apps"
    / "ebook-tools.json"
)

REPO_OWNED_WEB_COMMANDS = [
    "make test-web-auth-focused",
    "make test-web-admin-focused",
    "make test-web-sidebar-focused",
    "make test-web-create-book-focused",
    "make test-web-create-intake-focused",
    "make test-web-creation-templates-focused",
    "make test-web-library-focused",
    "make test-web-job-progress-focused",
    "make test-web-playback-focused",
    "make test-web-video-dubbing-focused",
    "make test-web-subtitle-tool-focused",
    "make test-web-app-view-deeplink-focused",
    "make test-web-full",
    "make build-web-production",
]


def _target_block(makefile: str, target: str) -> str:
    return makefile.split(f"{target}:", 1)[1].split("\n\n", 1)[0]


def _pipeline_web_commands() -> list[str]:
    manifest = json.loads(PIPELINE_MANIFEST.read_text(encoding="utf-8"))
    return [
        " ".join(entry["command"])
        for entry in manifest["webChecks"]["commands"]
    ]


def test_auth_focused_web_target_covers_session_flows() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-auth-focused" in makefile
    block = _target_block(makefile, "test-web-auth-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/components/__tests__/AuthFlows.test.tsx" in block


def test_docs_publish_auth_focused_web_target() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "make test-web-auth-focused" in docs
    assert "test-web-auth-focused" in plan


def test_admin_focused_web_target_covers_admin_shell_surfaces() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-admin-focused" in makefile
    block = _target_block(makefile, "test-web-admin-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/components/__tests__/UserManagementPanel.test.tsx" in block
    assert "src/components/__tests__/SystemPanel.test.tsx" in block
    assert "src/components/__tests__/SidebarAdminLinks.test.tsx" in block


def test_docs_publish_admin_focused_web_target() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "make test-web-admin-focused" in docs
    assert "test-web-admin-focused" in plan


def test_sidebar_focused_web_target_covers_split_navigation_shell() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-sidebar-focused" in makefile
    block = _target_block(makefile, "test-web-sidebar-focused")
    assert "npm --prefix web test -- --run" in block
    for path in [
        "src/components/__tests__/Sidebar.test.tsx",
        "src/components/__tests__/SidebarPlayerButton.test.tsx",
        "src/components/__tests__/SidebarCreationLinks.test.tsx",
        "src/components/__tests__/SidebarJobOverview.test.tsx",
        "src/components/__tests__/SidebarJobRow.test.tsx",
        "src/components/__tests__/sidebarUtils.test.ts",
    ]:
        assert path in block


def test_docs_publish_sidebar_focused_web_target() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "make test-web-sidebar-focused" in docs
    assert "test-web-sidebar-focused" in plan


def test_create_book_focused_web_target_covers_create_page_tests() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-create-book-focused" in makefile
    block = _target_block(makefile, "test-web-create-book-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/pages/__tests__/CreateBookPage.test.tsx" in block
    assert "src/pages/__tests__/createBookPageUtils.test.ts" in block


def test_create_intake_focused_web_target_covers_intake_surfaces() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    form_test = (
        ROOT
        / "web"
        / "src"
        / "components"
        / "__tests__"
        / "BookNarrationForm.test.tsx"
    ).read_text(encoding="utf-8")

    assert "test-web-create-intake-focused" in makefile
    block = _target_block(makefile, "test-web-create-intake-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/components/__tests__/createIntakeStatusUtils.test.ts" in block
    assert "src/components/__tests__/bookNarrationDiscoveryProviders.test.ts" in block
    assert "src/components/__tests__/bookNarrationTemplates.test.ts" in block
    assert "src/components/__tests__/bookNarrationFormUtils.test.ts" in block
    assert "src/components/__tests__/useBookNarrationChapters.test.tsx" in block
    assert "src/components/__tests__/useBookNarrationFiles.test.tsx" in block
    assert "src/components/__tests__/useBookNarrationVoices.test.tsx" in block
    assert "src/components/__tests__/BookNarrationForm.test.tsx" in block
    assert "src/components/__tests__/BookNarrationStepBar.test.tsx" in block
    assert "src/components/__tests__/BookNarrationSubmitStatus.test.tsx" in block
    assert "src/components/__tests__/BookNarrationFileDialog.test.tsx" in block
    assert "src/pages/__tests__/VideoDubbingPage.test.tsx" in block
    assert "discoverAcquisitionCandidates" in form_test
    assert "Discover sources" in form_test
    discovery_hook = (
        ROOT
        / "web"
        / "src"
        / "components"
        / "book-narration"
        / "useBookNarrationDiscovery.ts"
    ).read_text(encoding="utf-8")
    discovery_providers = (
        ROOT
        / "web"
        / "src"
        / "components"
        / "book-narration"
        / "bookNarrationDiscoveryProviders.ts"
    ).read_text(encoding="utf-8")
    dto_source = (ROOT / "web" / "src" / "api" / "dtos.ts").read_text(encoding="utf-8")
    assert "default_provider_ids?: Partial<Record<AcquisitionMediaKind, string[]>>" in dto_source
    assert "default_eligible_media_kinds?: AcquisitionMediaKind[]" in dto_source
    assert "resolveDefaultBookDiscoveryProvider(" in discovery_hook
    assert "defaultProviderIds?.book" in discovery_providers
    assert "hasUserSelectedDiscoveryProvider.current" in discovery_hook
    assert "setDefaultProviderIds(response.default_provider_ids)" in discovery_hook
    assert "buildBookNarrationDiscoveryProviderOptions(providers, defaultProviderIds)" in discovery_hook
    assert "DEFAULT_BOOK_DISCOVERY_PROVIDER" in discovery_hook
    assert "useState<BookNarrationDiscoveryProvider>(DEFAULT_BOOK_DISCOVERY_PROVIDER)" in discovery_hook
    assert "default_eligible_media_kinds" in discovery_providers
    assert "provider === DEFAULT_BOOK_DISCOVERY_PROVIDER ? null : provider" in discovery_hook
    assert "providers.length > 0" in discovery_providers
    assert "Array.isArray(provider.discovery_media_kinds)" in discovery_providers
    assert "is unavailable on this backend. Choose another discovery source." in discovery_providers


def test_creation_templates_focused_web_target_covers_shared_payload_builders() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-creation-templates-focused" in makefile
    block = _target_block(makefile, "test-web-creation-templates-focused")
    assert "npm --prefix web test -- --run --threads=false" in block
    assert "src/api/client/__tests__/creationTemplates.test.ts" in block
    assert "src/utils/__tests__/creationTemplateSanitizer.test.ts" in block
    assert "src/components/__tests__/bookNarrationTemplates.test.ts" in block
    assert "src/pages/__tests__/subtitleToolUtils.test.ts" in block
    assert "src/pages/__tests__/videoDubbingUtils.test.ts" in block


def test_library_focused_web_target_covers_library_metadata() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-library-focused" in makefile
    block = _target_block(makefile, "test-web-library-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/api/client/__tests__/resume.test.ts" in block
    assert "src/pages/__tests__/libraryPageMetadata.test.ts" in block
    assert "src/components/__tests__/libraryListUtils.test.ts" in block
    assert "src/components/__tests__/libraryListMediaUtils.test.ts" in block
    assert "src/components/__tests__/libraryListActions.test.ts" in block
    assert "src/components/__tests__/LibraryItemActions.test.tsx" in block
    assert "src/components/__tests__/LibraryItemMediaCells.test.tsx" in block
    assert "src/components/__tests__/LibraryStatusBadge.test.tsx" in block
    assert "src/components/__tests__/libraryListAttention.test.ts" in block
    assert "src/components/__tests__/libraryListResume.test.ts" in block


def test_job_progress_focused_web_target_covers_health_timeline() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-job-progress-focused" in makefile
    block = _target_block(makefile, "test-web-job-progress-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/api/client/__tests__/jobs.test.ts" in block
    assert "src/components/__tests__/JobStatusBadge.test.tsx" in block
    assert "src/components/__tests__/JobProgress.test.tsx" in block
    assert "src/components/__tests__/jobProgressParameters.test.ts" in block
    assert "src/components/__tests__/jobProgressUtils.test.ts" in block
    assert "src/utils/__tests__/progressEvents.test.ts" in block


def test_playback_focused_web_target_covers_player_and_media_state() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-playback-focused" in makefile
    block = _target_block(makefile, "test-web-playback-focused")
    assert "npm --prefix web test -- --run" in block
    for path in [
        "src/api/client/__tests__/media.test.ts",
        "src/hooks/__tests__/liveMediaState.test.ts",
        "src/hooks/__tests__/liveMediaTiming.test.ts",
        "src/hooks/__tests__/useLiveMedia.test.tsx",
        "src/components/__tests__/playerPanelUtils.test.ts",
        "src/components/__tests__/playerPanelChromeState.test.ts",
        "src/components/__tests__/playerPanelDocumentState.test.ts",
        "src/components/__tests__/usePlayerPanelActiveText.test.tsx",
        "src/components/__tests__/usePlayerPanelMediaNavigation.test.tsx",
        "src/components/__tests__/PlayerPanelBoundaryState.test.tsx",
        "src/components/__tests__/PlayerPanelContent.test.tsx",
        "src/components/__tests__/PlayerPanelNavigationGroups.test.tsx",
        "src/components/__tests__/PlayerPanelSearchSlot.test.tsx",
        "src/components/__tests__/PlayerPanelSentenceJumpDatalist.test.tsx",
        "src/components/__tests__/SleepTimerControl.test.tsx",
        "src/components/__tests__/TranscriptWord.test.tsx",
        "src/components/__tests__/VideoPlayer.test.tsx",
        "src/components/__tests__/YoutubeDubPlayer.test.tsx",
        "src/components/video-subtitles/__tests__/SubtitleTrackRows.test.tsx",
        "src/components/video-subtitles/__tests__/subtitleTrackOverlayUtils.test.ts",
        "src/components/video-subtitles/__tests__/useAssSubtitleCues.test.tsx",
        "src/components/video-subtitles/__tests__/useAssSubtitlePlaybackState.test.tsx",
        "src/components/video-subtitles/__tests__/useSubtitleCueKeyboardNavigation.test.tsx",
        "src/components/video-subtitles/__tests__/useSubtitleTrackSelection.test.tsx",
        "src/lib/media/__tests__/audioUrlResolver.test.ts",
        "src/lib/media/__tests__/sentenceChunkIndex.test.ts",
        "src/lib/playback/__tests__/seekScenarios.test.ts",
        "src/lib/playback/__tests__/sequencePlan.test.ts",
        "src/utils/__tests__/browserStorage.test.ts",
    ]:
        assert path in block


def test_docs_publish_playback_focused_web_target() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "make test-web-playback-focused" in docs
    assert "test-web-playback-focused" in plan


def test_app_shell_uses_granular_zustand_selectors() -> None:
    production_sources = [
        ROOT / "web" / "src" / "App.tsx",
        ROOT / "web" / "src" / "hooks" / "useAppAuth.ts",
        ROOT / "web" / "src" / "hooks" / "useAppJobs.ts",
        ROOT / "web" / "src" / "hooks" / "useAppNavigation.ts",
    ]

    for path in production_sources:
        source = path.read_text(encoding="utf-8")
        assert "useJobsStore()" not in source
        assert "useUIStore()" not in source

    jobs_hook = (ROOT / "web" / "src" / "hooks" / "useAppJobs.ts").read_text(encoding="utf-8")
    navigation_hook = (
        ROOT / "web" / "src" / "hooks" / "useAppNavigation.ts"
    ).read_text(encoding="utf-8")
    auth_hook = (ROOT / "web" / "src" / "hooks" / "useAppAuth.ts").read_text(encoding="utf-8")
    app_source = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
    jobs_store = (ROOT / "web" / "src" / "stores" / "jobsStore.ts").read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "import { createWithEqualityFn } from 'zustand/traditional';" in jobs_store
    assert "createWithEqualityFn<JobsState>()" in jobs_store
    assert "import { create } from 'zustand';" not in jobs_store
    assert "useActiveJobId()" in jobs_hook
    assert "useActiveJobId()" in navigation_hook
    assert "const getJob = useJobsStore((state) => state.getJob);" in jobs_hook
    assert "const getJob = useJobsStore((state) => state.getJob);" in navigation_hook
    assert "useJobsStore((state) => state.refreshJobs)" in jobs_hook
    assert "useUIStore((state) => state.setSelectedView)" in navigation_hook
    assert "useUIStore((state) => state.authError)" in auth_hook
    assert "useUIStore((state) => state.pendingInputFile)" in app_source
    assert "const entry = getJob(jobId);" in jobs_hook
    assert "const entry = getJob(resolvedJobId);" in navigation_hook
    assert "const entry = getJob(jobId);" in navigation_hook
    assert "const entry = jobs[jobId];" not in jobs_hook
    assert "const entry = jobs[jobId];" not in navigation_hook
    assert "const entry = jobs[resolvedJobId];" not in navigation_hook
    assert "App shell Zustand subscriptions now use field/action selectors" in plan


def test_video_dubbing_focused_web_target_covers_split_hooks() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-video-dubbing-focused" in makefile
    block = _target_block(makefile, "test-web-video-dubbing-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/pages/__tests__/videoDubbingDiscovery.test.ts" in block
    assert "src/pages/__tests__/useVideoDubbingAcquisitionProviders.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingCreationTemplate.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingDiscoveryController.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingDiscoverySearch.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingDownloadStation.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingDownloadStationCompletion.test.tsx" in block
    assert "src/pages/__tests__/VideoDownloadStationPanel.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingJobActions.test.tsx" in block
    assert "src/pages/__tests__/videoDubbingUtils.test.ts" in block
    assert "src/pages/__tests__/useVideoDubbingSelectionState.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingResolvedSelection.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingMetadata.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingLanguageState.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingVoiceState.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingModelState.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingOutputState.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingSubtitleExtraction.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingLibraryActions.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingLibraryState.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingSourceSelection.test.tsx" in block
    assert "src/pages/__tests__/VideoDubbingPage.test.tsx" in block
    assert "src/pages/__tests__/YoutubeVideoPage.test.tsx" in block


def test_video_dubbing_page_uses_acquisition_discovery_for_nas_video_candidates() -> None:
    page = (ROOT / "web" / "src" / "pages" / "VideoDubbingPage.tsx").read_text(encoding="utf-8")
    source_panel = (
        ROOT / "web" / "src" / "pages" / "video-dubbing" / "VideoSourcePanel.tsx"
    ).read_text(encoding="utf-8")
    download_station_panel = (
        ROOT
        / "web"
        / "src"
        / "pages"
        / "video-dubbing"
        / "VideoDownloadStationPanel.tsx"
    ).read_text(encoding="utf-8")
    test_source = (
        ROOT / "web" / "src" / "pages" / "__tests__" / "VideoDubbingPage.test.tsx"
    ).read_text(encoding="utf-8")
    provider_hook = (
        ROOT
        / "web"
        / "src"
        / "pages"
        / "video-dubbing"
        / "useVideoDubbingAcquisitionProviders.ts"
    ).read_text(encoding="utf-8")
    download_station_hook = (
        ROOT
        / "web"
        / "src"
        / "pages"
        / "video-dubbing"
        / "useVideoDubbingDownloadStation.ts"
    ).read_text(encoding="utf-8")
    download_station_completion_hook = (
        ROOT
        / "web"
        / "src"
        / "pages"
        / "video-dubbing"
        / "useVideoDubbingDownloadStationCompletion.ts"
    ).read_text(encoding="utf-8")
    discovery_search_hook = (
        ROOT
        / "web"
        / "src"
        / "pages"
        / "video-dubbing"
        / "useVideoDubbingDiscoverySearch.ts"
    ).read_text(encoding="utf-8")
    discovery_controller_hook = (
        ROOT
        / "web"
        / "src"
        / "pages"
        / "video-dubbing"
        / "useVideoDubbingDiscoveryController.ts"
    ).read_text(encoding="utf-8")
    job_actions_hook = (
        ROOT
        / "web"
        / "src"
        / "pages"
        / "video-dubbing"
        / "useVideoDubbingJobActions.ts"
    ).read_text(encoding="utf-8")
    creation_template_hook = (
        ROOT
        / "web"
        / "src"
        / "pages"
        / "video-dubbing"
        / "useVideoDubbingCreationTemplate.ts"
    ).read_text(encoding="utf-8")
    source_selection_hook = (
        ROOT
        / "web"
        / "src"
        / "pages"
        / "video-dubbing"
        / "useVideoDubbingSourceSelection.ts"
    ).read_text(encoding="utf-8")
    selection_state_hook = (
        ROOT
        / "web"
        / "src"
        / "pages"
        / "video-dubbing"
        / "useVideoDubbingSelectionState.ts"
    ).read_text(encoding="utf-8")
    resolved_selection_hook = (
        ROOT
        / "web"
        / "src"
        / "pages"
        / "video-dubbing"
        / "useVideoDubbingResolvedSelection.ts"
    ).read_text(encoding="utf-8")
    library_actions_hook = (
        ROOT
        / "web"
        / "src"
        / "pages"
        / "video-dubbing"
        / "useVideoDubbingLibraryActions.ts"
    ).read_text(encoding="utf-8")
    discovery_helper = (
        ROOT
        / "web"
        / "src"
        / "pages"
        / "video-dubbing"
        / "videoDubbingDiscovery.ts"
    ).read_text(encoding="utf-8")

    assert "discoverAcquisitionCandidates" not in page
    assert "discoverAcquisitionCandidates" in discovery_search_hook
    assert "useVideoDubbingAcquisitionProviders" not in page
    assert "useVideoDubbingAcquisitionProviders" in discovery_controller_hook
    assert "useVideoDubbingDiscoverySearch" not in page
    assert "useVideoDubbingDiscoverySearch" in discovery_controller_hook
    assert "useVideoDubbingDiscoveryController" in page
    assert "useVideoDubbingDownloadStation" in page
    assert "useVideoDubbingDownloadStationCompletion" in page
    assert "useVideoDubbingLibraryActions" in page
    assert "handleDownloadStationCompleted" in page
    assert "refreshLibraryWithSelection" in page
    assert "const language = await refreshLibrary()" not in page
    assert "const language = await deleteVideo(video)" not in page
    assert "const language = await refreshLibrary()" in library_actions_hook
    assert "const language = await deleteVideo(video)" in library_actions_hook
    assert "ensureTargetLanguage(language)" in library_actions_hook
    assert "findDownloadStationCompletedVideo" not in page
    assert "findDownloadStationCompletedVideo" in download_station_completion_hook
    assert "resolveDownloadStationCompletedFiles" in download_station_completion_hook
    assert "useVideoDubbingJobActions" in page
    assert "useVideoDubbingCreationTemplate" in page
    assert "useVideoDubbingSourceSelection" in page
    assert "useState<Record<string, unknown> | null>" not in page
    assert "selectedVideoDiscoveryTemplateState" in selection_state_hook
    assert "clearSelectedVideoDiscoveryTemplate" in selection_state_hook
    assert "useVideoDubbingResolvedSelection" in page
    assert "filterPlayableSubtitles" not in page
    assert "filterPlayableSubtitles" in resolved_selection_hook
    assert "resolveSubtitleNotice" not in page
    assert "resolveSubtitleNotice" in resolved_selection_hook
    assert "resolveVideoDubbingMetadataSourceName" not in page
    assert "resolveVideoDubbingMetadataSourceName" in resolved_selection_hook
    assert "canExtractEmbeddedSubtitles" not in page
    assert "canExtractEmbeddedSubtitles" in resolved_selection_hook
    assert "resolveSubtitleLanguageCandidate" in resolved_selection_hook
    assert "fetchAcquisitionProviders" in provider_hook
    assert "resolveVideoDiscoveryProviderState" in provider_hook
    assert "createAcquisitionJob" not in page
    assert "fetchAcquisitionJobStatus" not in page
    assert "generateYoutubeDub" not in page
    assert "saveCreationTemplate" not in page
    assert "createAcquisitionJob" in download_station_hook
    assert "fetchAcquisitionJobStatus" in download_station_hook
    assert "onDownloadStationCompleted" in download_station_hook
    assert "generateYoutubeDub" in job_actions_hook
    assert "saveCreationTemplate" in job_actions_hook
    assert "selectedVideoDiscoveryTemplateState" in job_actions_hook
    assert "extractVideoDubbingTemplateFormState" not in page
    assert "extractVideoDubbingTemplateFormState" in creation_template_hook
    assert "pendingTemplateMetadataRef" in creation_template_hook
    assert "mediaKind: 'video'" in discovery_search_hook
    assert "useState<VideoDiscoveryProvider>(DEFAULT_VIDEO_DISCOVERY_PROVIDER)" in discovery_controller_hook
    assert "preferredVideoDiscoveryProvider" in discovery_controller_hook
    assert "hasUserSelectedVideoDiscoveryProvider" in discovery_controller_hook
    assert "DEFAULT_VIDEO_DISCOVERY_PROVIDER" in discovery_search_hook
    assert "provider:" in discovery_search_hook
    assert "? null" in discovery_search_hook
    assert "const VIDEO_DISCOVERY_PROVIDERS" in discovery_helper
    assert "Default sources" in discovery_helper
    assert "youtube_url" in discovery_helper
    assert "isYoutubeMetadataVideoDiscoveryProvider" in discovery_helper
    assert "buildDefaultVideoDiscoveryProviderOption" in discovery_helper
    assert "default_eligible_media_kinds" in discovery_helper
    assert "filterDiscoveredVideoCandidates(" in discovery_helper
    assert "defaultableVideoProviderIds([candidate.provider], providers)" in discovery_helper
    assert "isVideoDiscoveryProvider" in discovery_helper
    assert "Array.isArray(provider.discovery_media_kinds)" in discovery_helper
    assert "videoDiscoveryProviderOptions" in page
    assert "isYoutubeSearchAvailable" in page
    assert "isDownloadStationHandoffCandidate" not in page
    assert "isDownloadStationHandoffCandidate" in source_selection_hook
    assert "makeVideoDiscoveryTemplateState" not in page
    assert "makeVideoDiscoveryTemplateState" in source_selection_hook
    assert "hasProviderInventory" in discovery_helper
    assert "youtubeSearchProvider?.available ?? !hasProviderInventory" in discovery_helper
    assert "selectedVideoDiscoveryProvider?.available ?? !hasProviderInventory" in discovery_helper
    assert "is unavailable on this backend. Choose another discovery source." in discovery_helper
    assert "onSelectDiscoveryCandidate" in source_panel
    assert "VideoDownloadStationPanel" in source_panel
    assert "Download Station handoff" in download_station_panel
    assert "resolveDownloadStationCompletedFiles" in download_station_panel
    assert "Video source discovery" in source_panel
    assert "discoveryProviderOptions: VideoDiscoveryProviderOption[]" in source_panel
    assert "discoveryProviderOptions.map" in source_panel
    assert "discovers NAS video candidates" in test_source
    assert "discovers a direct YouTube URL candidate" in test_source
    assert "mockDiscoverAcquisitionCandidates" in test_source
    assert "disables YouTube discovery" in test_source
    assert "backend-registered video discovery providers" in test_source
    assert "Download Station handoff" in test_source


def test_youtube_downloader_uses_acquisition_discovery_for_search_handoff() -> None:
    page = (ROOT / "web" / "src" / "pages" / "YoutubeVideoPage.tsx").read_text(encoding="utf-8")
    test_source = (
        ROOT / "web" / "src" / "pages" / "__tests__" / "YoutubeVideoPage.test.tsx"
    ).read_text(encoding="utf-8")

    assert "discoverAcquisitionCandidates" in page
    assert "fetchAcquisitionProviders" in page
    assert "provider: 'youtube_search'" in page
    assert "isYoutubeSearchAvailable" in page
    assert "handleSelectDiscoveryCandidate" in page
    assert "setUrl(sourceUrl)" in page
    assert "fetchYoutubeSubtitleTracks" in page
    assert "searches YouTube discovery" in test_source
    assert "disables YouTube discovery" in test_source
    assert "mockDiscoverAcquisitionCandidates" in test_source


def test_docs_publish_video_dubbing_focused_web_target() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "make test-web-video-dubbing-focused" in docs
    assert "test-web-video-dubbing-focused" in plan


def test_subtitle_tool_focused_web_target_covers_split_hooks() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-subtitle-tool-focused" in makefile
    block = _target_block(makefile, "test-web-subtitle-tool-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/pages/__tests__/subtitleToolUtils.test.ts" in block
    assert "src/pages/__tests__/subtitleJobPresentation.test.ts" in block
    assert "src/pages/__tests__/subtitleJobUtils.test.ts" in block
    assert "src/pages/__tests__/subtitleMetadataUtils.test.ts" in block
    assert "src/pages/__tests__/subtitleSourceUtils.test.ts" in block
    assert "src/pages/__tests__/SubtitleToolTabContent.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleTvMetadata.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleSources.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleJobResults.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleModels.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleLanguageDefaults.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleCreationDefaults.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleShowOriginalPreference.test.tsx" in block
    assert "src/pages/__tests__/useSubtitlePrefill.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleCreationTemplate.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleTemplateActions.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleLanguageState.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleSubmitFeedback.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleSourceMode.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleProcessingOptions.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleTabState.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleSubmitStatus.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleSubmit.test.tsx" in block


def test_docs_publish_subtitle_tool_focused_web_target() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "make test-web-subtitle-tool-focused" in docs
    assert "test-web-subtitle-tool-focused" in plan


def test_app_view_deeplink_focused_web_target_covers_deeplink_utils() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-app-view-deeplink-focused" in makefile
    block = _target_block(makefile, "test-web-app-view-deeplink-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/utils/__tests__/appViewDeepLink.test.ts" in block


def test_full_web_target_runs_complete_vitest_suite() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-full" in makefile
    block = _target_block(makefile, "test-web-full")
    assert "npm --prefix web test -- --run" in block


def test_web_production_build_target_runs_export_build() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "build-web-production" in makefile
    assert "check-web-export-player-bundle:" in makefile
    block = _target_block(makefile, "build-web-production")
    assert "npm --prefix web run build" in block
    assert "$(PYTHON) -m pytest -q tests/test_web_video_dubbing_pipeline_contract.py::test_export_player_html_references_trackable_bundle" in block


def test_export_player_html_references_trackable_bundle() -> None:
    gitignore = GITIGNORE.read_text(encoding="utf-8")
    export_html = (EXPORT_DIST / "export.html").read_text(encoding="utf-8")
    script_match = re.search(r'<script[^>]+src="(?P<src>\./assets/export-[^"]+\.js)"', export_html)

    assert "!web/export-dist/assets/*.js" in gitignore
    assert "!web/export-dist/assets/*.js.map" in gitignore
    assert script_match is not None
    script_path = EXPORT_DIST / script_match.group("src").removeprefix("./")
    assert script_path.exists()


def test_docs_publish_all_repo_owned_web_pipeline_targets() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")

    for command in REPO_OWNED_WEB_COMMANDS:
        assert command in docs


def test_shared_pipeline_manifest_runs_all_repo_owned_web_checks() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    manifest_commands = _pipeline_web_commands()

    assert manifest_commands == REPO_OWNED_WEB_COMMANDS
    for command in REPO_OWNED_WEB_COMMANDS:
        _, target = command.split(" ", 1)
        assert f"{target}:" in makefile
