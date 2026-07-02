.PHONY: test test-fast test-audio test-translation test-webapi test-apple test-services \
       test-pipeline test-cli test-auth test-library test-render test-media \
       test-config test-metadata test-changed test-makefile-contract \
       test-backend-auth-session \
       test-backend-library-search-source-isbn test-backend-admin-system-status \
       test-backend-pipeline-jobs \
       test-backend-runtime-descriptor \
       test-backend-create-book test-backend-creation-templates \
       test-backend-pipeline-sources test-backend-acquisition \
       test-backend-audio-routes \
       test-backend-reading-beds \
       test-backend-notifications \
       test-backend-subtitle-router \
       test-backend-playback-state \
       test-backend-playback-media \
       test-backend-offline-export \
       test-backend-youtube-dubbing-service \
       test-web-auth-focused \
       test-web-admin-focused test-web-sidebar-focused \
       test-web-create-book-focused test-web-create-intake-focused \
       test-web-creation-templates-focused \
       test-web-library-focused test-web-job-progress-focused \
       test-web-playback-focused test-web-video-dubbing-focused \
       test-web-subtitle-tool-focused test-web-app-view-deeplink-focused \
       test-web-full build-web-production check-web-export-player-bundle \
       test-release-version check-web-e2e-journeys check-apple-e2e-journeys \
       generate-language-catalogs check-language-catalogs test-apple-language-catalogs \
       test-apple-playback-state-swift \
       test-apple-create-readiness-contract test-apple-local-surface-contract \
       test-apple-contracts \
       build-apple-macos-ipad-style apple-macos-ipad-destination \
       build-apple-macos-ipad-style-dry-run apple-devices apple-device-host-readiness apple-device-update \
       apple-device-preflight apple-device-launch-console apple-device-pull-playback-log apple-device-pull-and-verify-playback-transport-log apple-device-pull-and-verify-playback-transport-pause-resume-log apple-device-pull-and-verify-playback-resume-offset-log apple-device-verify-playback-transport-log apple-device-verify-playback-transport-pause-resume-log apple-device-verify-playback-resume-offset-log apple-device-verify-music-bed-launch-log apple-device-verify-music-bed-guarded-play-log apple-device-verify-music-bed-pause-resume-log apple-device-signed-build-only apple-device-deploy-dry-run \
       apple-device-full-entitlement-plan apple-device-full-entitlement-build \
       apple-device-full-entitlement-install apple-device-full-entitlement-fallback-install \
       apple-device-full-entitlement-stable-install \
       build-apple-iphone-simulator build-apple-ipad-simulator \
       build-apple-ios-simulators build-apple-ios-uitests \
       build-apple-tvos-simulator build-apple-tvos-uitests \
       build-apple-office-ipad-surfaces verify-apple-office-ipad-surfaces \
       build-apple-local-surfaces verify-apple-local-surfaces \
       verify-apple-cross-surface-checkpoint \
       apple-local-checkpoint-bundle \
       apple-pipeline-contracts apple-pipeline-backend apple-pipeline-backend-tests \
       apple-runtime-fast-forward apple-runtime-ssh-check apple-runtime-xcode-readiness apple-pipeline-source-sync apple-pipeline-web-checks \
       apple-pipeline-simulator-smoke apple-pipeline-simulator-smoke-dry-run apple-pipeline-simulator-smokes-dry-run \
       apple-pipeline-owned-journeys-list apple-pipeline-owned-journeys apple-pipeline-owned-journey apple-pipeline-owned-journey-dry-run \
       apple-pipeline-owned-journeys-dry-run apple-pipeline-ipad-create-readiness \
       apple-pipeline-ipad-create-readiness-dry-run apple-pipeline-tvos-create-readiness \
       apple-pipeline-tvos-create-readiness-dry-run apple-pipeline-orchestration-dry-runs \
       verify-apple-shared-pipeline verify-apple-living-room-candidate verify-apple-dogfood-pipeline verify-apple-golden-pipeline \
       test-e2e test-e2e-headless test-e2e-web test-e2e-web-headless \
       test-e2e-ios test-e2e-iphone test-e2e-ipad test-e2e-tvos \
       test-e2e-iphone-create-readiness test-e2e-ipad-create-readiness \
       test-e2e-tvos-create-readiness test-e2e-ipad-music-bed-sync-dry-run test-e2e-ipad-music-bed-sync test-e2e-tvos-music-bed-sync-dry-run test-e2e-tvos-music-bed-sync test-e2e-apple-create-readiness \
       test-e2e-all test-e2e-apple-parallel \
       docker-build-backend docker-build-frontend docker-build \
       docker-up docker-down docker-logs docker-status \
       monitoring-up monitoring-down monitoring-logs monitoring-status \
       test-observability \
       k8s-build k8s-import-images k8s-deploy k8s-status k8s-logs k8s-teardown k8s-lint \
       argocd-install argocd-app argocd-ui argocd-password argocd-teardown

SHELL := /bin/bash
PYTHON ?= $(shell for candidate in .venv/bin/python python3.13 python3.12 python3.11 python3.10 python3; do \
	if { [ -x "$$candidate" ] || command -v "$$candidate" >/dev/null 2>&1; } \
		&& "$$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then \
		echo "$$candidate"; exit 0; \
	fi; \
done; echo python3)
APPLE_PIPELINE_ROOT ?= /Users/fifo/Projects/home/apple-device-app-pipeline
APPLE_PIPELINE_APP ?= ebook-tools
APPLE_PIPELINE_PYTHON ?= python3
APPLE_PIPELINE_SMOKE_PROFILE ?= ipados
APPLE_PIPELINE_SMOKE_PROFILES ?= ios ipados tvos tvos-cinema
APPLE_PIPELINE_JOURNEY_PROFILE ?= ipados
APPLE_PIPELINE_JOURNEY_PROFILES ?= apple-e2e-journeys iphone ipados tvos iphone-create ipados-create tvos-create ipados-music-bed-sync tvos-music-bed-sync runtime-xcode-readiness ios-uitests-build tvos-uitests-build macos-ipad-style-dry-run macos-ipad-style
MAC_STUDIO_SSH_TARGET ?= fifo@192.168.1.9
MAC_STUDIO_REPO_PATH ?= /Users/fifo/Projects/home/ebook-tools
MAC_STUDIO_BRANCH ?= main
MAC_STUDIO_CONNECT_TIMEOUT ?= 5
APPLE_DEVICE_PROFILE ?= ipad
APPLE_DEVICE_SIGNED_ARTIFACT_PATH ?= test-results/DerivedData-device-full-entitlements/Build/Products/Debug-iphoneos/InteractiveReader.app
APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT ?= 10
APPLE_DEVICE_LAUNCH_PRESERVE_RUNNING ?= 0
APPLE_DEVICE_LAUNCH_PRESERVE_RUNNING_FLAG = $(if $(filter 1 YES yes true TRUE,$(APPLE_DEVICE_LAUNCH_PRESERVE_RUNNING)),--preserve-running-app)
APPLE_DEVICE_PLAYBACK_LOG ?=
APPLE_PLAYBACK_TRANSPORT_LOG_MODE ?= pause-release
APPLE_MUSIC_BED_LAUNCH_LOG_MODE ?= startup
CHECKPOINT_BASE ?= origin/$(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)
CHECKPOINT_OUTPUT_DIR ?= test-results/git-checkpoints

# ── Full suite ───────────────────────────────────────────────────────────
test:
	$(PYTHON) -m pytest

# ── Skip slow / integration tests ───────────────────────────────────────
test-fast:
	$(PYTHON) -m pytest -m "not slow and not integration"

test-changed:
	$(PYTHON) scripts/run_changed_tests.py

test-makefile-contract:
	$(PYTHON) -m pytest -q tests/test_makefile_pytest_contract.py tests/test_apple_shared_pipeline_contract.py tests/test_web_video_dubbing_pipeline_contract.py tests/scripts/test_run_changed_tests.py tests/scripts/test_check_web_e2e_journeys.py tests/scripts/test_run_xcodebuild_e2e.py tests/scripts/test_write_git_checkpoint_bundle.py

# ── Domain markers ───────────────────────────────────────────────────────
test-audio:
	$(PYTHON) -m pytest -m audio

test-translation:
	$(PYTHON) -m pytest -m translation

test-webapi:
	$(PYTHON) -m pytest -m webapi

test-apple:
	$(PYTHON) -m pytest -m apple

test-backend-auth-session:
	$(PYTHON) -m pytest tests/modules/webapi/test_auth_routes.py

test-backend-library-search-source-isbn:
	$(PYTHON) -m pytest \
		tests/modules/webapi/test_library_items_route.py \
		tests/modules/webapi/test_library_isbn_routes.py \
		tests/modules/webapi/test_search_routes.py \
		tests/modules/webapi/test_metadata_lookup_routes.py \
		tests/modules/webapi/test_book_metadata_token_safe_routes.py \
		tests/test_library_source_and_isbn_metadata.py

test-backend-admin-system-status:
	$(PYTHON) -m pytest \
		tests/modules/webapi/test_system_routes.py \
		tests/modules/webapi/test_job_action_routes.py

test-backend-pipeline-jobs:
	$(PYTHON) -m pytest \
		tests/modules/webapi/test_dashboard_access_control.py \
		tests/modules/services/test_job_manager_access_control.py \
		tests/modules/services/test_job_manager_transitions.py

test-backend-runtime-descriptor:
	$(PYTHON) -m pytest \
		tests/modules/webapi/test_system_routes.py::test_runtime_descriptor_helper_returns_pipeline_contract \
		tests/modules/webapi/test_system_routes.py::test_runtime_descriptor_api_paths_match_fastapi_routes \
		tests/modules/webapi/test_system_routes.py::test_runtime_descriptor_returns_fresh_public_lists \
		tests/modules/webapi/test_system_routes.py::test_runtime_descriptor_guard_flags_secret_like_keys \
		tests/modules/webapi/test_system_routes.py::test_runtime_descriptor_uses_prevalidated_static_template \
		tests/modules/webapi/test_system_routes.py::test_public_runtime_descriptor_returns_non_secret_contract \
		tests/test_apple_runtime_descriptor_contract.py::test_runtime_descriptor_advertises_apple_pipeline_contract

test-backend-create-book:
	$(PYTHON) -m pytest tests/test_create_book.py

test-backend-creation-templates:
	$(PYTHON) -m pytest tests/modules/webapi/test_creation_template_routes.py

test-backend-pipeline-sources:
	$(PYTHON) -m pytest \
		tests/modules/services/test_source_discovery.py \
		tests/test_create_book.py::test_pipeline_ebook_listing_can_limit_newest_entries \
		tests/test_create_book.py::test_pipeline_file_picker_records_safe_timing \
		tests/test_create_book.py::test_pipeline_file_picker_accepts_bounded_picker_limit \
		tests/test_create_book.py::test_pipeline_file_picker_rejects_invalid_picker_limit \
		tests/test_create_book.py::test_pipeline_content_index_uses_selected_epub \
		tests/test_create_book.py::test_pipeline_content_index_returns_422_when_epub_cannot_be_read \
		tests/test_create_book.py::test_pipeline_content_index_records_validation_outcomes \
		tests/test_create_book.py::test_delete_pipeline_ebook_is_idempotent_for_missing_in_scope_file \
		tests/test_create_book.py::test_delete_pipeline_ebook_rejects_missing_file_outside_books_root \
		tests/test_create_book.py::test_delete_pipeline_ebook_uses_generic_error_when_unlink_fails \
		tests/test_create_book.py::test_upload_pipeline_ebook_persists_file_in_books_root \
		tests/test_create_book.py::test_upload_cover_file_uses_generic_error_when_decode_fails

test-backend-acquisition:
	$(PYTHON) -m pytest \
		tests/modules/services/test_acquisition_providers.py \
		tests/modules/webapi/test_acquisition_routes.py

test-backend-audio-routes:
	$(PYTHON) -m pytest tests/modules/webapi/test_audio_routes.py

test-backend-reading-beds:
	$(PYTHON) -m pytest tests/modules/webapi/test_reading_bed_routes.py

test-backend-notifications:
	$(PYTHON) -m pytest tests/modules/webapi/test_notification_routes.py tests/modules/test_notification_service.py

test-backend-subtitle-router:
	$(PYTHON) -m pytest \
		tests/webapi/test_subtitles_router.py \
		tests/modules/webapi/test_subtitle_metadata_token_safe_routes.py \
		tests/modules/services/test_metadata_service_token_safe_logs.py

test-backend-playback-state:
	$(PYTHON) -m pytest \
		tests/modules/webapi/test_assistant_routes.py \
		tests/modules/webapi/test_resume_routes.py \
		tests/modules/webapi/test_bookmark_routes.py \
		tests/modules/webapi/test_lookup_cache_routes.py \
		tests/modules/test_resume_service.py

test-backend-playback-media:
	$(PYTHON) -m pytest \
		tests/modules/library/test_library_service.py \
		tests/modules/webapi/test_job_media_routes.py \
		tests/modules/webapi/test_library_media_route.py \
		tests/modules/webapi/test_library_media_file_download.py

test-backend-offline-export:
	$(PYTHON) -m pytest \
		tests/modules/webapi/test_export_routes.py \
		tests/modules/services/test_export_service.py

test-backend-youtube-dubbing-service:
	$(PYTHON) -m pytest \
		tests/modules/webapi/test_youtube_library_route.py \
		tests/modules/services/test_youtube_dubbing_subtitles.py \
		tests/modules/services/test_youtube_subtitles.py

test-web-auth-focused:
	npm --prefix web test -- --run \
		src/components/__tests__/AuthFlows.test.tsx

test-web-admin-focused:
	npm --prefix web test -- --run \
		src/components/__tests__/UserManagementPanel.test.tsx \
		src/components/__tests__/SystemPanel.test.tsx \
		src/components/__tests__/SidebarAdminLinks.test.tsx

test-web-sidebar-focused:
	npm --prefix web test -- --run \
		src/components/__tests__/Sidebar.test.tsx \
		src/components/__tests__/SidebarPlayerButton.test.tsx \
		src/components/__tests__/SidebarCreationLinks.test.tsx \
		src/components/__tests__/SidebarJobOverview.test.tsx \
		src/components/__tests__/SidebarJobRow.test.tsx \
		src/components/__tests__/sidebarUtils.test.ts

test-web-create-book-focused:
	npm --prefix web test -- --run \
		src/pages/__tests__/CreateBookPage.test.tsx \
		src/pages/__tests__/createBookPageUtils.test.ts

test-web-create-intake-focused:
	npm --prefix web test -- --run \
		src/components/__tests__/createIntakeStatusUtils.test.ts \
		src/components/__tests__/useCreateIntakeStatus.test.tsx \
		src/components/__tests__/bookNarrationDiscoveryProviders.test.ts \
		src/components/__tests__/bookNarrationImageSettings.test.ts \
		src/components/__tests__/bookNarrationTemplates.test.ts \
		src/components/__tests__/bookNarrationFormUtils.test.ts \
		src/components/__tests__/useBookNarrationChapters.test.tsx \
		src/components/__tests__/useBookNarrationFiles.test.tsx \
		src/components/__tests__/useBookNarrationFormEditing.test.tsx \
		src/components/__tests__/useBookNarrationHistory.test.tsx \
		src/components/__tests__/useBookNarrationImageDefaults.test.tsx \
		src/components/__tests__/useBookNarrationImageNodeAvailability.test.tsx \
		src/components/__tests__/useBookNarrationNormalizedState.test.tsx \
		src/components/__tests__/useBookNarrationPrefill.test.tsx \
		src/components/__tests__/useBookNarrationDiscovery.test.tsx \
		src/components/__tests__/useBookNarrationDiscoverySelection.test.tsx \
		src/components/__tests__/useBookNarrationSourceDefaults.test.tsx \
		src/components/__tests__/useBookNarrationSubmitFlow.test.tsx \
		src/components/__tests__/useBookNarrationTemplateApply.test.tsx \
		src/components/__tests__/useBookNarrationTemplateSave.test.tsx \
		src/components/__tests__/useBookNarrationVoices.test.tsx \
		src/components/__tests__/useBookNarrationWorkflowRefs.test.tsx \
		src/components/__tests__/useBookNarrationSectionState.test.tsx \
		src/utils/__tests__/voiceOptions.test.ts \
		src/components/__tests__/BookNarrationStepBar.test.tsx \
		src/components/__tests__/BookNarrationSubmitStatus.test.tsx \
		src/components/__tests__/BookNarrationFileDialog.test.tsx \
		src/components/__tests__/BookNarrationFormDialogs.test.tsx \
		src/components/__tests__/BookNarrationForm.test.tsx \
		src/pages/__tests__/VideoDubbingPage.test.tsx

test-web-creation-templates-focused:
	npm --prefix web test -- --run --threads=false \
		src/api/client/__tests__/creationTemplates.test.ts \
		src/utils/__tests__/creationTemplateSanitizer.test.ts \
		src/components/__tests__/bookNarrationTemplates.test.ts \
		src/pages/__tests__/subtitleToolUtils.test.ts \
		src/pages/__tests__/videoDubbingUtils.test.ts

test-web-library-focused:
	npm --prefix web test -- --run \
		src/api/client/__tests__/resume.test.ts \
		src/pages/__tests__/libraryPageMetadata.test.ts \
		src/components/__tests__/libraryListUtils.test.ts \
		src/components/__tests__/libraryListMediaUtils.test.ts \
		src/components/__tests__/libraryListActions.test.ts \
		src/components/__tests__/LibraryFlatTable.test.tsx \
		src/components/__tests__/LibraryItemActions.test.tsx \
		src/components/__tests__/LibraryItemMediaCells.test.tsx \
		src/components/__tests__/LibraryStatusBadge.test.tsx \
		src/components/__tests__/libraryListAttention.test.ts \
		src/components/__tests__/libraryListResume.test.ts

test-web-job-progress-focused:
	npm --prefix web test -- --run \
		src/api/client/__tests__/jobs.test.ts \
		src/components/__tests__/JobStatusBadge.test.tsx \
		src/components/__tests__/JobProgress.test.tsx \
		src/components/__tests__/jobProgressParameters.test.ts \
		src/components/__tests__/jobProgressUtils.test.ts \
		src/utils/__tests__/progressEvents.test.ts

test-web-playback-focused:
	npm --prefix web test -- --run \
		src/api/client/__tests__/media.test.ts \
		src/hooks/__tests__/liveMediaState.test.ts \
		src/hooks/__tests__/liveMediaTiming.test.ts \
		src/hooks/__tests__/useLiveMedia.test.tsx \
		src/components/__tests__/playerPanelChapterNavigation.test.ts \
		src/components/__tests__/playerPanelActiveTextSelection.test.ts \
		src/components/__tests__/playerPanelUtils.test.ts \
		src/components/__tests__/playerPanelProps.test.ts \
		src/components/__tests__/playerPanelChromeState.test.ts \
		src/components/__tests__/navigationControlsState.test.ts \
		src/components/__tests__/playerPanelDocumentState.test.ts \
		src/components/__tests__/usePlayerPanelActiveText.test.tsx \
		src/components/__tests__/usePendingChunkSelection.test.tsx \
		src/components/__tests__/usePlayerPanelTextActivation.test.tsx \
		src/components/__tests__/usePlayerPanelChapterNavigation.test.tsx \
		src/components/__tests__/usePlayerPanelMediaNavigation.test.tsx \
		src/components/__tests__/usePlayerPanelNavigationChrome.test.tsx \
		src/components/__tests__/PlayerPanelBoundaryState.test.tsx \
		src/components/__tests__/PlayerPanelContent.test.tsx \
		src/components/__tests__/PlayerPanelFrame.test.tsx \
		src/components/__tests__/PlayerPanelNavigationGroups.test.tsx \
		src/components/__tests__/PlayerPanelPrelude.test.tsx \
		src/components/__tests__/PlayerPanelSearchSlot.test.tsx \
		src/components/__tests__/PlayerPanelSentenceJumpDatalist.test.tsx \
		src/components/__tests__/SleepTimerControl.test.tsx \
		src/components/__tests__/TranscriptViewAccessibility.test.tsx \
		src/components/__tests__/TranscriptWord.test.tsx \
		src/components/__tests__/VideoPlayer.test.tsx \
		src/components/__tests__/YoutubeDubPlayer.test.tsx \
		src/components/video-subtitles/__tests__/SubtitleLinguistBubblePortal.test.tsx \
		src/components/video-subtitles/__tests__/SubtitleTrackRows.test.tsx \
		src/components/video-subtitles/__tests__/subtitleTrackOverlayUtils.test.ts \
		src/components/video-subtitles/__tests__/useAssSubtitleCues.test.tsx \
		src/components/video-subtitles/__tests__/useAssSubtitlePlaybackState.test.tsx \
		src/components/video-subtitles/__tests__/useSubtitleCueKeyboardNavigation.test.tsx \
		src/components/video-subtitles/__tests__/useSubtitleOverlayDrag.test.tsx \
		src/components/video-subtitles/__tests__/useSubtitleTokenNavigation.test.tsx \
		src/components/video-subtitles/__tests__/useSubtitleTrackSelection.test.tsx \
		src/components/interactive-text/__tests__/inlineSentenceSkip.test.ts \
		src/lib/media/__tests__/audioUrlResolver.test.ts \
		src/lib/media/__tests__/sentenceChunkIndex.test.ts \
		src/lib/playback/__tests__/seekScenarios.test.ts \
		src/lib/playback/__tests__/sequencePlan.test.ts \
		src/utils/__tests__/browserStorage.test.ts

test-web-video-dubbing-focused:
	npm --prefix web test -- --run \
		src/pages/__tests__/videoDubbingDiscovery.test.ts \
		src/pages/__tests__/videoDubbingDownloadStationUtils.test.ts \
		src/pages/__tests__/videoSourcePanelUtils.test.ts \
		src/pages/__tests__/useVideoDubbingAcquisitionProviders.test.tsx \
		src/pages/__tests__/useVideoDubbingCreationTemplate.test.tsx \
		src/pages/__tests__/useVideoDubbingDiscoveryController.test.tsx \
		src/pages/__tests__/useVideoDubbingDiscoverySearch.test.tsx \
		src/pages/__tests__/useVideoDubbingDownloadStation.test.tsx \
		src/pages/__tests__/useVideoDubbingDownloadStationCompletion.test.tsx \
		src/pages/__tests__/VideoDiscoveryPanel.test.tsx \
		src/pages/__tests__/VideoDownloadedListPanel.test.tsx \
		src/pages/__tests__/VideoDownloadStationPanel.test.tsx \
		src/pages/__tests__/useVideoDubbingJobActions.test.tsx \
		src/pages/__tests__/videoDubbingUtils.test.ts \
		src/pages/__tests__/videoDubbingVoiceOptions.test.ts \
		src/utils/__tests__/voiceOptions.test.ts \
		src/pages/__tests__/useVideoDubbingSelectionState.test.tsx \
		src/pages/__tests__/useVideoDubbingResolvedSelection.test.tsx \
		src/pages/__tests__/useVideoDubbingMetadata.test.tsx \
		src/pages/__tests__/useVideoDubbingLanguageState.test.tsx \
		src/pages/__tests__/useVideoDubbingVoiceState.test.tsx \
		src/pages/__tests__/useVideoDubbingModelState.test.tsx \
		src/pages/__tests__/useVideoDubbingOutputState.test.tsx \
		src/pages/__tests__/useVideoDubbingSubtitleExtraction.test.tsx \
		src/pages/__tests__/useVideoDubbingLibraryActions.test.tsx \
		src/pages/__tests__/useVideoDubbingLibraryState.test.tsx \
		src/pages/__tests__/useVideoDubbingSourceSelection.test.tsx \
		src/pages/__tests__/VideoDubbingFeedbackPanel.test.tsx \
		src/pages/__tests__/VideoTvMetadataPreview.test.tsx \
		src/pages/__tests__/VideoDubbingPage.test.tsx \
		src/pages/__tests__/YoutubeVideoPage.test.tsx

test-web-subtitle-tool-focused:
	npm --prefix web test -- --run \
		src/api/client/__tests__/subtitles.test.ts \
		src/pages/__tests__/subtitleToolUtils.test.ts \
		src/pages/__tests__/subtitleJobPresentation.test.ts \
		src/pages/__tests__/subtitleJobUtils.test.ts \
		src/pages/__tests__/subtitleMetadataUtils.test.ts \
		src/pages/__tests__/subtitleSourceUtils.test.ts \
		src/pages/__tests__/SubtitleToolTabContent.test.tsx \
		src/pages/__tests__/SubtitleToolStatusNotices.test.tsx \
		src/pages/__tests__/useSubtitleTvMetadata.test.tsx \
		src/pages/__tests__/useSubtitleSources.test.tsx \
		src/pages/__tests__/useSubtitleJobResults.test.tsx \
		src/pages/__tests__/useSubtitleModels.test.tsx \
		src/pages/__tests__/useSubtitleLanguageDefaults.test.tsx \
		src/pages/__tests__/useSubtitleCreationDefaults.test.tsx \
		src/pages/__tests__/useSubtitleShowOriginalPreference.test.tsx \
		src/pages/__tests__/useSubtitlePrefill.test.tsx \
		src/pages/__tests__/useSubtitleCreationTemplate.test.tsx \
		src/pages/__tests__/useSubtitleTemplateActions.test.tsx \
		src/pages/__tests__/useSubtitleLanguageState.test.tsx \
		src/pages/__tests__/useSubtitleSubmitFeedback.test.tsx \
		src/pages/__tests__/useSubtitleSourceMode.test.tsx \
		src/pages/__tests__/useSubtitleProcessingOptions.test.tsx \
		src/pages/__tests__/useSubtitleTabState.test.tsx \
		src/pages/__tests__/useSubtitleSubmitStatus.test.tsx \
		src/pages/__tests__/useSubtitleSubmit.test.tsx

test-web-app-view-deeplink-focused:
	npm --prefix web test -- --run \
		src/utils/__tests__/appViewDeepLink.test.ts \
		src/utils/__tests__/creationTemplatePayloadExtras.test.ts

test-web-full:
	npm --prefix web test -- --run

build-web-production:
	npm --prefix web run build
	$(PYTHON) -m pytest -q tests/test_web_video_dubbing_pipeline_contract.py::test_export_player_html_references_trackable_bundle

check-web-export-player-bundle:
	$(PYTHON) -m pytest -q tests/test_web_video_dubbing_pipeline_contract.py::test_export_player_html_references_trackable_bundle

test-services:
	$(PYTHON) -m pytest -m services

test-pipeline:
	$(PYTHON) -m pytest -m pipeline

test-cli:
	$(PYTHON) -m pytest -m cli

test-auth:
	$(PYTHON) -m pytest -m auth

test-library:
	$(PYTHON) -m pytest -m library

test-render:
	$(PYTHON) -m pytest -m render

test-media:
	$(PYTHON) -m pytest -m media

test-config:
	$(PYTHON) -m pytest -m config

test-metadata:
	$(PYTHON) -m pytest -m metadata

test-observability:
	$(PYTHON) -m pytest -m observability -v

generate-language-catalogs:
	$(PYTHON) scripts/generate_language_catalogs.py

check-language-catalogs:
	$(PYTHON) scripts/generate_language_catalogs.py --check

test-apple-language-catalogs:
	$(PYTHON) -m pytest -q tests/test_language_catalog_parity.py tests/scripts/test_generate_language_catalogs.py
	$(PYTHON) scripts/generate_language_catalogs.py --check

check-apple-e2e-journeys:
	$(PYTHON) scripts/check_apple_e2e_journeys.py

check-web-e2e-journeys:
	$(PYTHON) scripts/check_web_e2e_journeys.py

test-apple-create-readiness-contract:
	$(PYTHON) -m pytest -q tests/scripts/test_check_apple_create_readiness.py tests/scripts/test_check_apple_e2e_journeys.py tests/test_apple_create_readiness_journey.py tests/test_apple_e2e_env_file_contract.py
	$(MAKE) check-apple-e2e-journeys

test-apple-local-surface-contract:
	$(PYTHON) -m pytest -q tests/test_apple_ios_build_contract.py tests/test_apple_tvos_build_contract.py tests/test_apple_macos_ipad_style_contract.py tests/test_apple_local_surface_build_contract.py

test-release-version:
	$(PYTHON) -m pytest -q tests/test_release_version_contract.py
	$(PYTHON) scripts/check_release_version_contract.py

test-apple-playback-state-swift:
	bash scripts/check_apple_audio_mode_manager.sh
	bash scripts/check_apple_sentence_position_provider.sh
	bash scripts/check_apple_playback_mode_switch_integration.sh
	bash scripts/check_apple_sequence_pause_cancel.sh
	bash scripts/check_apple_transcript_display_snapshots.sh
	bash scripts/check_apple_sentence_jump_render_lock.sh
	bash scripts/check_apple_interactive_context_builder.sh
	bash scripts/check_apple_reader_navigation_contract.sh

test-apple-contracts: test-release-version
	$(PYTHON) -m pytest -q tests/test_language_catalog_parity.py tests/test_backend_dependency_contract.py tests/test_apple_create_split_layout.py tests/test_apple_create_options_fallback.py tests/test_apple_create_readiness_journey.py tests/test_apple_runtime_descriptor_contract.py tests/test_apple_offline_export_contract.py tests/test_apple_job_health_timeline_contract.py tests/test_apple_job_restart_contract.py tests/test_apple_library_metadata_edit_contract.py tests/test_apple_library_source_upload_review_contract.py tests/test_apple_library_source_diagnostics_contract.py tests/test_apple_resume_status_contract.py tests/test_apple_browse_chrome_contract.py tests/test_apple_macos_ipad_style_contract.py tests/test_apple_ios_build_contract.py tests/test_apple_narration_history_defaults_contract.py tests/test_apple_local_surface_build_contract.py tests/test_apple_audio_stream_recovery_contract.py tests/test_apple_chunk_metadata_retry_contract.py tests/test_apple_live_media_fallback_contract.py tests/test_apple_timing_token_sanitization_contract.py tests/test_apple_token_normalization_cache_contract.py tests/test_apple_sentence_image_prefetch_contract.py tests/test_apple_playback_search_bookmark_contract.py tests/test_apple_playback_state_helpers_contract.py tests/test_apple_now_playing_contract.py tests/test_apple_music_bed_pause_window_contract.py tests/test_apple_sleep_timer_contract.py tests/test_apple_notification_manager_contract.py tests/test_apple_shared_pipeline_contract.py tests/test_backend_pipeline_contract.py tests/test_apple_tvos_build_contract.py tests/test_apple_e2e_env_file_contract.py tests/test_apple_e2e_login_contract.py tests/scripts/test_generate_language_catalogs.py tests/scripts/test_write_apple_e2e_config.py tests/scripts/test_check_apple_e2e_config.py tests/scripts/test_check_apple_e2e_journeys.py tests/scripts/test_ios_e2e_report.py tests/scripts/test_check_apple_shared_pipeline_manifest.py tests/scripts/test_check_apple_music_bed_launch_log.py tests/scripts/test_check_apple_xcode_readiness.py tests/scripts/test_check_apple_create_readiness.py tests/scripts/test_apple_pull_device_playback_log.py tests/scripts/test_check_apple_playback_transport_log.py tests/scripts/test_check_poc_readiness.py tests/scripts/test_ios_profile_capability_check.py tests/scripts/test_apple_merge_entitlements.py tests/scripts/test_apple_full_entitlement_signing_plan.py
	$(PYTHON) scripts/generate_language_catalogs.py --check
	$(MAKE) check-apple-e2e-journeys
	bash scripts/check_apple_runtime_descriptor_payload.sh
	bash scripts/check_apple_creation_payloads.sh
	bash scripts/check_apple_audio_mode_manager.sh
	bash scripts/check_apple_sentence_position_provider.sh
	bash scripts/check_apple_playback_mode_switch_integration.sh
	bash scripts/check_apple_sequence_pause_cancel.sh
	bash scripts/check_apple_transcript_display_snapshots.sh
	bash scripts/check_apple_sentence_jump_render_lock.sh
	bash scripts/check_apple_interactive_context_builder.sh
	bash scripts/check_apple_reader_navigation_contract.sh
	bash scripts/check_apple_macos_ipad_style_helper.sh
	bash scripts/check_apple_device_update_helper.sh
	bash scripts/check_apple_e2e_config_writer.sh
	bash scripts/check_apple_ios_build_helper.sh
	bash scripts/check_apple_local_surface_build_helper.sh
	bash scripts/check_apple_shared_pipeline_helper.sh
	bash scripts/check_apple_tvos_build_helper.sh

build-apple-office-ipad-surfaces: build-apple-ipad-simulator build-apple-macos-ipad-style

verify-apple-office-ipad-surfaces: test-apple-contracts build-apple-office-ipad-surfaces build-apple-ios-uitests

build-apple-local-surfaces: build-apple-ios-simulators build-apple-tvos-simulator build-apple-macos-ipad-style

verify-apple-local-surfaces: test-apple-contracts build-apple-local-surfaces build-apple-ios-uitests build-apple-tvos-uitests

verify-apple-cross-surface-checkpoint: test-backend-auth-session test-backend-library-search-source-isbn test-backend-admin-system-status test-backend-pipeline-jobs test-backend-runtime-descriptor test-backend-create-book test-backend-creation-templates test-backend-pipeline-sources test-backend-acquisition test-backend-audio-routes test-backend-reading-beds test-backend-notifications test-backend-subtitle-router test-backend-playback-state test-backend-playback-media test-backend-offline-export test-backend-youtube-dubbing-service test-web-auth-focused test-web-admin-focused test-web-sidebar-focused test-web-create-book-focused test-web-create-intake-focused test-web-creation-templates-focused test-web-library-focused test-web-job-progress-focused test-web-playback-focused test-web-video-dubbing-focused test-web-subtitle-tool-focused test-web-app-view-deeplink-focused test-web-full build-web-production verify-apple-local-surfaces

apple-local-checkpoint-bundle:
	$(PYTHON) scripts/write_git_checkpoint_bundle.py --base "$(CHECKPOINT_BASE)" --output-dir "$(CHECKPOINT_OUTPUT_DIR)"

apple-pipeline-contracts:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_contract_checks.py --app "$(APPLE_PIPELINE_APP)"

apple-pipeline-backend:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/check_app_backend.py --app "$(APPLE_PIPELINE_APP)"

apple-pipeline-backend-tests:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_backend_tests.py --app "$(APPLE_PIPELINE_APP)"

apple-pipeline-source-sync:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/check_app_source_sync.py --app "$(APPLE_PIPELINE_APP)"

apple-pipeline-web-checks:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_web_checks.py --app "$(APPLE_PIPELINE_APP)"

apple-pipeline-simulator-smoke:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_simulator_smoke.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_PIPELINE_SMOKE_PROFILE)"

apple-pipeline-simulator-smoke-dry-run:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_simulator_smoke.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_PIPELINE_SMOKE_PROFILE)" --dry-run

apple-pipeline-simulator-smokes-dry-run:
	@for profile in $(APPLE_PIPELINE_SMOKE_PROFILES); do \
		$(MAKE) apple-pipeline-simulator-smoke-dry-run APPLE_PIPELINE_SMOKE_PROFILE="$$profile"; \
	done

apple-pipeline-owned-journeys-list:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_owned_journey.py --app "$(APPLE_PIPELINE_APP)" --list

apple-pipeline-owned-journeys: apple-pipeline-owned-journeys-list

apple-pipeline-owned-journey:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_owned_journey.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_PIPELINE_JOURNEY_PROFILE)" --use-remote-env

apple-pipeline-owned-journey-dry-run:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_owned_journey.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_PIPELINE_JOURNEY_PROFILE)" --dry-run

apple-pipeline-owned-journeys-dry-run:
	@for profile in $(APPLE_PIPELINE_JOURNEY_PROFILES); do \
		$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE="$$profile"; \
	done

apple-runtime-fast-forward:
	bash scripts/fast_forward_mac_studio_runtime_checkout.sh \
		--target "$(MAC_STUDIO_SSH_TARGET)" \
		--repo-path "$(MAC_STUDIO_REPO_PATH)" \
		--branch "$(MAC_STUDIO_BRANCH)" \
		--connect-timeout "$(MAC_STUDIO_CONNECT_TIMEOUT)"

apple-runtime-ssh-check:
	bash scripts/check_mac_studio_runtime_checkout.sh \
		--target "$(MAC_STUDIO_SSH_TARGET)" \
		--repo-path "$(MAC_STUDIO_REPO_PATH)" \
		--branch "$(MAC_STUDIO_BRANCH)" \
		--connect-timeout "$(MAC_STUDIO_CONNECT_TIMEOUT)" \
		--require-head "$$(git rev-parse HEAD)"

apple-runtime-xcode-readiness:
	ssh -o BatchMode=yes -o ConnectTimeout="$(MAC_STUDIO_CONNECT_TIMEOUT)" "$(MAC_STUDIO_SSH_TARGET)" 'cd "$(MAC_STUDIO_REPO_PATH)" && PYTHON_BIN="$$(if [ -x .venv/bin/python ]; then printf .venv/bin/python; elif command -v python3 >/dev/null 2>&1; then command -v python3; else command -v python; fi)" && "$$PYTHON_BIN" scripts/check_apple_xcode_readiness.py --xcodebuild "$(XCBUILD)" --profile golden-runtime'

apple-pipeline-ipad-create-readiness:
	$(MAKE) apple-pipeline-owned-journey APPLE_PIPELINE_JOURNEY_PROFILE=ipados-create

apple-pipeline-ipad-create-readiness-dry-run:
	$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE=ipados-create

apple-pipeline-tvos-create-readiness:
	$(MAKE) apple-pipeline-owned-journey APPLE_PIPELINE_JOURNEY_PROFILE=tvos-create

apple-pipeline-tvos-create-readiness-dry-run:
	$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE=tvos-create

apple-pipeline-orchestration-dry-runs: apple-pipeline-simulator-smokes-dry-run apple-pipeline-owned-journeys-list apple-pipeline-owned-journeys-dry-run

verify-apple-shared-pipeline: apple-pipeline-contracts apple-pipeline-backend apple-pipeline-backend-tests apple-pipeline-web-checks apple-pipeline-orchestration-dry-runs

verify-apple-living-room-candidate: verify-apple-shared-pipeline test-e2e-tvos-music-bed-sync

verify-apple-dogfood-pipeline: verify-apple-cross-surface-checkpoint verify-apple-shared-pipeline

verify-apple-golden-pipeline: apple-runtime-fast-forward apple-runtime-ssh-check apple-runtime-xcode-readiness apple-pipeline-source-sync verify-apple-dogfood-pipeline

apple-device-preflight:
	bash scripts/apple_unattended_device_update.sh --profile "$(APPLE_DEVICE_PROFILE)" --device "$(APPLE_DEVICE_ID)" --device-preflight-only

apple-device-launch-console:
	bash scripts/apple_unattended_device_update.sh \
		--profile "$(APPLE_DEVICE_PROFILE)" \
		--device "$(APPLE_DEVICE_ID)" \
		--launch-only \
		--launch-console-timeout "$(APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT)" $(APPLE_DEVICE_LAUNCH_PRESERVE_RUNNING_FLAG)

apple-device-pull-playback-log:
	bash scripts/apple_pull_device_playback_log.sh \
		--profile "$(APPLE_DEVICE_PROFILE)" \
		--device "$(APPLE_DEVICE_ID)" \
		$(if $(strip $(APPLE_DEVICE_PLAYBACK_LOG)),--output "$(APPLE_DEVICE_PLAYBACK_LOG)")

apple-device-pull-and-verify-playback-transport-log:
	$(MAKE) apple-device-pull-playback-log
	$(MAKE) apple-device-verify-playback-transport-log

apple-device-pull-and-verify-playback-transport-pause-resume-log:
	$(MAKE) apple-device-pull-and-verify-playback-transport-log APPLE_PLAYBACK_TRANSPORT_LOG_MODE=pause-resume

apple-device-pull-and-verify-playback-resume-offset-log:
	$(MAKE) apple-device-pull-and-verify-playback-transport-log APPLE_PLAYBACK_TRANSPORT_LOG_MODE=resume-offset

apple-device-verify-playback-transport-log:
	$(PYTHON) scripts/check_apple_playback_transport_log.py \
		--device "$(APPLE_DEVICE_ID)" \
		--mode "$(APPLE_PLAYBACK_TRANSPORT_LOG_MODE)" \
		$(if $(strip $(APPLE_DEVICE_PLAYBACK_LOG)),"$(APPLE_DEVICE_PLAYBACK_LOG)")

apple-device-verify-playback-transport-pause-resume-log:
	$(MAKE) apple-device-verify-playback-transport-log APPLE_PLAYBACK_TRANSPORT_LOG_MODE=pause-resume

apple-device-verify-playback-resume-offset-log:
	$(MAKE) apple-device-verify-playback-transport-log APPLE_PLAYBACK_TRANSPORT_LOG_MODE=resume-offset

apple-device-verify-music-bed-launch-log:
	$(PYTHON) scripts/check_apple_music_bed_launch_log.py \
		--device "$(APPLE_DEVICE_ID)" \
		--mode "$(APPLE_MUSIC_BED_LAUNCH_LOG_MODE)" \
		$(if $(strip $(APPLE_DEVICE_LAUNCH_LOG)),"$(APPLE_DEVICE_LAUNCH_LOG)")

apple-device-verify-music-bed-guarded-play-log:
	$(MAKE) apple-device-verify-music-bed-launch-log APPLE_MUSIC_BED_LAUNCH_LOG_MODE=guarded-play

apple-device-verify-music-bed-pause-resume-log:
	$(MAKE) apple-device-verify-music-bed-launch-log APPLE_MUSIC_BED_LAUNCH_LOG_MODE=pause-resume

apple-device-signed-build-only:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_device_deploy.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_DEVICE_PROFILE)" --signed-build-only

apple-device-deploy-dry-run:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_device_deploy.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_DEVICE_PROFILE)" --dry-run

apple-device-full-entitlement-plan:
	bash scripts/apple_full_entitlement_signing_plan.sh --device "$(APPLE_DEVICE_ID)" $(if $(strip $(FULL_CAPABILITY_IOS_PROFILE)),--app-profile "$(FULL_CAPABILITY_IOS_PROFILE)") $(if $(strip $(WILDCARD_IOS_EXTENSION_PROFILE)),--extension-profile "$(WILDCARD_IOS_EXTENSION_PROFILE)") $(if $(strip $(APPLE_DEVELOPMENT_IDENTITY)),--signing-identity "$(APPLE_DEVELOPMENT_IDENTITY)")

apple-device-full-entitlement-build:
	bash scripts/apple_full_entitlement_signing_plan.sh --execute --device "$(APPLE_DEVICE_ID)" $(if $(strip $(FULL_CAPABILITY_IOS_PROFILE)),--app-profile "$(FULL_CAPABILITY_IOS_PROFILE)") $(if $(strip $(WILDCARD_IOS_EXTENSION_PROFILE)),--extension-profile "$(WILDCARD_IOS_EXTENSION_PROFILE)") $(if $(strip $(APPLE_DEVELOPMENT_IDENTITY)),--signing-identity "$(APPLE_DEVELOPMENT_IDENTITY)")

apple-device-full-entitlement-install:
	bash scripts/apple_full_entitlement_signing_plan.sh --execute --install --device "$(APPLE_DEVICE_ID)" $(if $(strip $(FULL_CAPABILITY_IOS_PROFILE)),--app-profile "$(FULL_CAPABILITY_IOS_PROFILE)") $(if $(strip $(WILDCARD_IOS_EXTENSION_PROFILE)),--extension-profile "$(WILDCARD_IOS_EXTENSION_PROFILE)") $(if $(strip $(APPLE_DEVELOPMENT_IDENTITY)),--signing-identity "$(APPLE_DEVELOPMENT_IDENTITY)")

apple-device-full-entitlement-fallback-install:
	bash scripts/apple_unattended_device_update.sh \
		--profile "$(APPLE_DEVICE_PROFILE)" \
		--device "$(APPLE_DEVICE_ID)" \
		--install \
		--launch \
		--launch-console-timeout "$(APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT)" \
		--fallback-to-signed-artifact \
		--signed-artifact-path "$(APPLE_DEVICE_SIGNED_ARTIFACT_PATH)"

apple-device-full-entitlement-stable-install:
	bash scripts/apple_unattended_device_update.sh \
		--profile "$(APPLE_DEVICE_PROFILE)" \
		--device "$(APPLE_DEVICE_ID)" \
		--skip-build \
		--app-path "$(APPLE_DEVICE_SIGNED_ARTIFACT_PATH)" \
		--install \
		--launch \
		--launch-console-timeout "$(APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT)" \
		--fallback-to-signed-artifact \
		--signed-artifact-path "$(APPLE_DEVICE_SIGNED_ARTIFACT_PATH)"

build-apple-macos-ipad-style:
	bash scripts/apple_build_macos_ipad_style.sh

apple-macos-ipad-destination:
	bash scripts/apple_build_macos_ipad_style.sh --show-destination

build-apple-macos-ipad-style-dry-run:
	bash scripts/apple_build_macos_ipad_style.sh --dry-run

apple-devices:
	bash scripts/apple_unattended_device_update.sh --list

apple-device-host-readiness:
	bash scripts/apple_unattended_device_update.sh --host-readiness-only

apple-device-update:
	bash scripts/apple_unattended_device_update.sh \
		--profile "$(APPLE_DEVICE_PROFILE)" \
		--device "$(APPLE_DEVICE_ID)" \
		--install \
		$(if $(strip $(APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT)),--launch --launch-console-timeout "$(APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT)")

# ── LLM model probe (diagnostic — slow, on-demand) ────────────────────
# Probes every available LLM model for translation (EN→FR/AR/HI/ZH) and
# structured JSON-batch compliance. Records per-model quality + performance
# and writes a Markdown report. Typically 30s-3min per model; use --models to
# restrict to a subset.
#
# Examples:
#   make probe-llm-models
#   make probe-llm-models ARGS='--only-cloud --exclude-tier 90'
#   make probe-llm-models ARGS='--models ollama_cloud:mistral-large-3:675b'
probe-llm-models:
	@mkdir -p test-results
	docker exec ebook-tools-backend python3 /app/scripts/probe_llm_models.py \
		--out /app/storage/llm_probe_report.md \
		--json-out /app/storage/llm_probe_report.json \
		$(ARGS)
	@docker cp ebook-tools-backend:/app/storage/llm_probe_report.md test-results/llm_probe_report.md
	@docker cp ebook-tools-backend:/app/storage/llm_probe_report.json test-results/llm_probe_report.json
	@echo "Report: test-results/llm_probe_report.md"

# ── E2E browser tests (Playwright) ────────────────────────────────────
# Artifacts (screenshots, traces) written to test-results/ (gitignored)
E2E_ARGS = -m e2e -o "addopts=-rs" --screenshot=on --full-page-screenshot --tracing=retain-on-failure

# Legacy targets (backward compat)
test-e2e:
	$(PYTHON) -m pytest $(E2E_ARGS) --e2e-report --headed --slowmo=200

test-e2e-headless:
	$(PYTHON) -m pytest $(E2E_ARGS) --e2e-report

# Named Web targets with custom report title
test-e2e-web:
	$(PYTHON) -m pytest $(E2E_ARGS) --headed --slowmo=200 \
		--e2e-report=test-results/web-e2e-report.md \
		--e2e-report-title="Web E2E Test Report"

test-e2e-web-headless:
	$(PYTHON) -m pytest $(E2E_ARGS) \
		--e2e-report=test-results/web-e2e-report.md \
		--e2e-report-title="Web E2E Test Report"

# ── Apple E2E tests (XCUITest) ────────────────────────────────────────
XCBUILD = /Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild
XCPROJ = ios/InteractiveReader/InteractiveReader.xcodeproj
JOURNEY_SRC = tests/e2e/journeys/basic_playback.json
CREATE_READINESS_JOURNEY_SRC = tests/e2e/journeys/create_readiness.json
MUSIC_BED_SYNC_JOURNEY_SRC = tests/e2e/journeys/music_bed_sync.json
E2E_TEMP_ROOT ?= /tmp/apple-device-app-pipeline/ebook-tools
E2E_PROFILE ?= local
E2E_ENV_FILE ?= $(if $(wildcard .env),.env,$(if $(wildcard .env.local),.env.local,.env))
E2E_CONFIG_PATH ?= $(E2E_TEMP_ROOT)/$(E2E_PROFILE)/ios_e2e_config.json
E2E_JOURNEY_PATH ?= $(E2E_TEMP_ROOT)/$(E2E_PROFILE)/ios_e2e_journey.json
E2E_PLATFORM_PROFILE ?= $(E2E_PROFILE)
E2E_PLATFORM_CONFIG_PATH ?= $(E2E_TEMP_ROOT)/$(E2E_PLATFORM_PROFILE)/ios_e2e_config.json
E2E_PLATFORM_JOURNEY_PATH ?= $(E2E_TEMP_ROOT)/$(E2E_PLATFORM_PROFILE)/ios_e2e_journey.json
E2E_MUSIC_BED_SYNC_TEST ?=
E2E_START_BROWSE_SECTION ?=
E2E_ALLOW_RESTORED_SESSION ?=
E2E_FAIL_ON_SKIPPED ?=
IOS_E2E_ONLY_TESTING ?= InteractiveReaderUITests/JourneyTests/testJourney
TVOS_E2E_ONLY_TESTING ?= InteractiveReaderTVUITests/JourneyTests/testJourney
E2E_SIMCTL_LOCK ?= $(shell $(PYTHON) -c 'import tempfile; print(tempfile.gettempdir() + "/apple-device-app-pipeline-simctl.lock")')
E2E_XCODEBUILD_ATTEMPTS ?= 2

# Write config + journey to profile-scoped /tmp paths.
define WRITE_E2E_CONFIG
$(PYTHON) scripts/write_apple_e2e_config.py \
	--env-file "$(E2E_ENV_FILE)" \
	--profile "$(E2E_PROFILE)" \
	--config-path "$(E2E_CONFIG_PATH)" \
	--journey-src "$(JOURNEY_SRC)" \
	--journey-path "$(E2E_JOURNEY_PATH)" \
	--fallback-config-path "$(E2E_PLATFORM_CONFIG_PATH)" \
	--fallback-journey-path "$(E2E_PLATFORM_JOURNEY_PATH)"
endef

define CHECK_E2E_CONFIG
$(PYTHON) scripts/check_apple_e2e_config.py \
	--env-file "$(E2E_ENV_FILE)" \
	--profile "$(E2E_PROFILE)" \
	--allow-restored-session "$(E2E_ALLOW_RESTORED_SESSION)"
endef

define CHECK_XCODE_READINESS
$(PYTHON) scripts/check_apple_xcode_readiness.py \
	--xcodebuild "$(XCBUILD)" \
	--profile "$(E2E_PROFILE)"
endef

# ── iPhone E2E ───────────────────────────────────────────────────────
IPHONE_DESTINATION ?= 'platform=iOS Simulator,name=iPhone 17 Pro'
IPHONE_E2E_RESULT = $(CURDIR)/test-results/iphone-e2e.xcresult
IPHONE_DERIVED_DATA = $(CURDIR)/test-results/DerivedData-iphone
IPHONE_BUILD_DERIVED_DATA = $(CURDIR)/test-results/DerivedData-iphone-build

build-apple-iphone-simulator:
	@mkdir -p test-results
	@$(CHECK_XCODE_READINESS)
	$(XCBUILD) -quiet build \
		-project $(XCPROJ) \
		-scheme InteractiveReader \
		-configuration Debug \
		-destination $(IPHONE_DESTINATION) \
		-derivedDataPath $(IPHONE_BUILD_DERIVED_DATA)

test-e2e-iphone: E2E_PROFILE = iphone
test-e2e-iphone: E2E_PLATFORM_PROFILE = iphone
test-e2e-iphone:
	@rm -rf $(IPHONE_E2E_RESULT) $(IPHONE_DERIVED_DATA) test-results/iphone-e2e-attachments
	@$(CHECK_E2E_CONFIG)
	@$(CHECK_XCODE_READINESS)
	@$(WRITE_E2E_CONFIG)
	@status=0; set -o pipefail; \
	E2E_CONFIG_PATH="$(E2E_CONFIG_PATH)" E2E_JOURNEY_PATH="$(E2E_JOURNEY_PATH)" \
		E2E_MUSIC_BED_SYNC_TEST="$(E2E_MUSIC_BED_SYNC_TEST)" \
		E2E_START_BROWSE_SECTION="$(E2E_START_BROWSE_SECTION)" \
		E2E_ALLOW_RESTORED_SESSION="$(E2E_ALLOW_RESTORED_SESSION)" \
		E2E_SIMCTL_LOCK="$(E2E_SIMCTL_LOCK)" $(PYTHON) scripts/run_xcodebuild_e2e.py \
		--attempts "$(E2E_XCODEBUILD_ATTEMPTS)" \
		--cleanup-path "$(IPHONE_E2E_RESULT)" \
		--cleanup-path "$(IPHONE_DERIVED_DATA)" \
		--label "iPhone E2E xcodebuild" -- \
		$(PYTHON) scripts/with_simulator_lock.py -- $(XCBUILD) test \
		-project $(XCPROJ) \
		-scheme InteractiveReaderUITests \
		-destination $(IPHONE_DESTINATION) \
		-derivedDataPath $(IPHONE_DERIVED_DATA) \
		-resultBundlePath $(IPHONE_E2E_RESULT) \
		-only-testing:$(IOS_E2E_ONLY_TESTING) || status=$$?; \
	report_status=0; \
	$(PYTHON) scripts/ios_e2e_report.py \
		--xcresult $(IPHONE_E2E_RESULT) \
		--output test-results/iphone-e2e-report.md \
		--title "iPhone E2E Test Report" \
		--screenshot-prefix iphone \
		$(if $(strip $(E2E_FAIL_ON_SKIPPED)),--fail-on-skipped); report_status=$$?; \
	if [ $$status -eq 0 ] && [ $$report_status -ne 0 ]; then status=$$report_status; fi; \
	rm -f "$(E2E_CONFIG_PATH)" "$(E2E_JOURNEY_PATH)" "$(E2E_PLATFORM_CONFIG_PATH)" "$(E2E_PLATFORM_JOURNEY_PATH)"; \
	exit $$status

test-e2e-iphone-create-readiness:
	@$(PYTHON) scripts/check_apple_create_readiness.py --env-file "$(E2E_ENV_FILE)"
	@$(MAKE) test-e2e-iphone \
		JOURNEY_SRC=$(CREATE_READINESS_JOURNEY_SRC) \
		E2E_FAIL_ON_SKIPPED=1 \
		E2E_PROFILE=iphone-create

# ── iPad E2E ─────────────────────────────────────────────────────────
IPAD_DESTINATION ?= 'platform=iOS Simulator,name=iPad Pro 13-inch (M5)'
IPAD_E2E_RESULT = $(CURDIR)/test-results/ipad-e2e.xcresult
IPAD_DERIVED_DATA = $(CURDIR)/test-results/DerivedData-ipad
IPAD_BUILD_DERIVED_DATA = $(CURDIR)/test-results/DerivedData-ipad-build
IOS_UITEST_BUILD_DERIVED_DATA = $(CURDIR)/test-results/DerivedData-ios-uitests-build

build-apple-ios-simulators: build-apple-iphone-simulator build-apple-ipad-simulator

build-apple-ios-uitests:
	@mkdir -p test-results
	@$(CHECK_XCODE_READINESS)
	$(XCBUILD) -quiet build-for-testing \
		-project $(XCPROJ) \
		-scheme InteractiveReaderUITests \
		-configuration Debug \
		-destination $(IPAD_DESTINATION) \
		-derivedDataPath $(IOS_UITEST_BUILD_DERIVED_DATA)

build-apple-ipad-simulator:
	@mkdir -p test-results
	@$(CHECK_XCODE_READINESS)
	$(XCBUILD) -quiet build \
		-project $(XCPROJ) \
		-scheme InteractiveReader \
		-configuration Debug \
		-destination $(IPAD_DESTINATION) \
		-derivedDataPath $(IPAD_BUILD_DERIVED_DATA)

test-e2e-ipad: E2E_PROFILE = ipados
test-e2e-ipad: E2E_PLATFORM_PROFILE = ipados
test-e2e-ipad:
	@rm -rf $(IPAD_E2E_RESULT) $(IPAD_DERIVED_DATA) test-results/ipad-e2e-attachments
	@$(CHECK_E2E_CONFIG)
	@$(CHECK_XCODE_READINESS)
	@$(WRITE_E2E_CONFIG)
	@status=0; set -o pipefail; \
	E2E_CONFIG_PATH="$(E2E_CONFIG_PATH)" E2E_JOURNEY_PATH="$(E2E_JOURNEY_PATH)" \
		E2E_MUSIC_BED_SYNC_TEST="$(E2E_MUSIC_BED_SYNC_TEST)" \
		E2E_START_BROWSE_SECTION="$(E2E_START_BROWSE_SECTION)" \
		E2E_ALLOW_RESTORED_SESSION="$(E2E_ALLOW_RESTORED_SESSION)" \
		E2E_SIMCTL_LOCK="$(E2E_SIMCTL_LOCK)" $(PYTHON) scripts/run_xcodebuild_e2e.py \
		--attempts "$(E2E_XCODEBUILD_ATTEMPTS)" \
		--cleanup-path "$(IPAD_E2E_RESULT)" \
		--cleanup-path "$(IPAD_DERIVED_DATA)" \
		--label "iPad E2E xcodebuild" -- \
		$(PYTHON) scripts/with_simulator_lock.py -- $(XCBUILD) test \
		-project $(XCPROJ) \
		-scheme InteractiveReaderUITests \
		-destination $(IPAD_DESTINATION) \
		-derivedDataPath $(IPAD_DERIVED_DATA) \
		-resultBundlePath $(IPAD_E2E_RESULT) \
		-only-testing:$(IOS_E2E_ONLY_TESTING) || status=$$?; \
	report_status=0; \
	$(PYTHON) scripts/ios_e2e_report.py \
		--xcresult $(IPAD_E2E_RESULT) \
		--output test-results/ipad-e2e-report.md \
		--title "iPad E2E Test Report" \
		--screenshot-prefix ipad \
		$(if $(strip $(E2E_FAIL_ON_SKIPPED)),--fail-on-skipped); report_status=$$?; \
	if [ $$status -eq 0 ] && [ $$report_status -ne 0 ]; then status=$$report_status; fi; \
	rm -f "$(E2E_CONFIG_PATH)" "$(E2E_JOURNEY_PATH)" "$(E2E_PLATFORM_CONFIG_PATH)" "$(E2E_PLATFORM_JOURNEY_PATH)"; \
	exit $$status

test-e2e-ipad-create-readiness:
	@$(PYTHON) scripts/check_apple_create_readiness.py --env-file "$(E2E_ENV_FILE)"
	@$(MAKE) test-e2e-ipad \
		JOURNEY_SRC=$(CREATE_READINESS_JOURNEY_SRC) \
		E2E_FAIL_ON_SKIPPED=1 \
		E2E_PROFILE=ipados-create

test-e2e-ipad-music-bed-sync-dry-run:
	@$(MAKE) check-apple-e2e-journeys
	@$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE=ipados-music-bed-sync

test-e2e-ipad-music-bed-sync:
	@E2E_MUSIC_BED_SYNC_TEST=1 E2E_START_BROWSE_SECTION=Library E2E_ALLOW_RESTORED_SESSION=1 E2E_FAIL_ON_SKIPPED=1 $(MAKE) test-e2e-ipad \
		JOURNEY_SRC=$(MUSIC_BED_SYNC_JOURNEY_SRC) \
		E2E_PROFILE=ipados-music-bed-sync

# ── tvOS E2E ─────────────────────────────────────────────────────────
TVOS_DESTINATION ?= 'platform=tvOS Simulator,name=Apple TV 4K (3rd generation)'
TVOS_E2E_RESULT = $(CURDIR)/test-results/tvos-e2e.xcresult
TVOS_DERIVED_DATA = $(CURDIR)/test-results/DerivedData-tvos
TVOS_BUILD_DERIVED_DATA = $(CURDIR)/test-results/DerivedData-tvos-build
TVOS_UITEST_BUILD_DERIVED_DATA = $(CURDIR)/test-results/DerivedData-tvos-uitests-build

build-apple-tvos-simulator:
	@mkdir -p test-results
	@$(CHECK_XCODE_READINESS)
	$(XCBUILD) -quiet build \
		-project $(XCPROJ) \
		-scheme InteractiveReaderTV \
		-configuration Debug \
		-destination $(TVOS_DESTINATION) \
		-derivedDataPath $(TVOS_BUILD_DERIVED_DATA)

build-apple-tvos-uitests:
	@mkdir -p test-results
	@$(CHECK_XCODE_READINESS)
	$(XCBUILD) -quiet build-for-testing \
		-project $(XCPROJ) \
		-scheme InteractiveReaderTVUITests \
		-configuration Debug \
		-destination $(TVOS_DESTINATION) \
		-derivedDataPath $(TVOS_UITEST_BUILD_DERIVED_DATA)

test-e2e-tvos: E2E_PROFILE = tvos
test-e2e-tvos: E2E_PLATFORM_PROFILE = tvos
test-e2e-tvos:
	@rm -rf $(TVOS_E2E_RESULT) $(TVOS_DERIVED_DATA) test-results/tvos-e2e-attachments
	@$(CHECK_E2E_CONFIG)
	@$(CHECK_XCODE_READINESS)
	@$(WRITE_E2E_CONFIG)
	@status=0; set -o pipefail; \
	E2E_CONFIG_PATH="$(E2E_CONFIG_PATH)" E2E_JOURNEY_PATH="$(E2E_JOURNEY_PATH)" \
		E2E_MUSIC_BED_SYNC_TEST="$(E2E_MUSIC_BED_SYNC_TEST)" \
		E2E_START_BROWSE_SECTION="$(E2E_START_BROWSE_SECTION)" \
		E2E_ALLOW_RESTORED_SESSION="$(E2E_ALLOW_RESTORED_SESSION)" \
		E2E_SIMCTL_LOCK="$(E2E_SIMCTL_LOCK)" $(PYTHON) scripts/run_xcodebuild_e2e.py \
		--attempts "$(E2E_XCODEBUILD_ATTEMPTS)" \
		--cleanup-path "$(TVOS_E2E_RESULT)" \
		--cleanup-path "$(TVOS_DERIVED_DATA)" \
		--label "tvOS E2E xcodebuild" -- \
		$(PYTHON) scripts/with_simulator_lock.py -- $(XCBUILD) test \
		-project $(XCPROJ) \
		-scheme InteractiveReaderTVUITests \
		-destination $(TVOS_DESTINATION) \
		-derivedDataPath $(TVOS_DERIVED_DATA) \
		-resultBundlePath $(TVOS_E2E_RESULT) \
		-only-testing:$(TVOS_E2E_ONLY_TESTING) || status=$$?; \
	report_status=0; \
	$(PYTHON) scripts/ios_e2e_report.py \
		--xcresult $(TVOS_E2E_RESULT) \
		--output test-results/tvos-e2e-report.md \
		--title "tvOS E2E Test Report" \
		--screenshot-prefix tvos \
		$(if $(strip $(E2E_FAIL_ON_SKIPPED)),--fail-on-skipped); report_status=$$?; \
	if [ $$status -eq 0 ] && [ $$report_status -ne 0 ]; then status=$$report_status; fi; \
	rm -f "$(E2E_CONFIG_PATH)" "$(E2E_JOURNEY_PATH)" "$(E2E_PLATFORM_CONFIG_PATH)" "$(E2E_PLATFORM_JOURNEY_PATH)"; \
	exit $$status

test-e2e-tvos-create-readiness:
	@$(PYTHON) scripts/check_apple_create_readiness.py --env-file "$(E2E_ENV_FILE)"
	@$(MAKE) test-e2e-tvos \
		JOURNEY_SRC=$(CREATE_READINESS_JOURNEY_SRC) \
		E2E_FAIL_ON_SKIPPED=1 \
		E2E_PROFILE=tvos-create

test-e2e-tvos-music-bed-sync-dry-run:
	@$(MAKE) check-apple-e2e-journeys
	@$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE=tvos-music-bed-sync

test-e2e-tvos-music-bed-sync:
	@E2E_MUSIC_BED_SYNC_TEST=1 E2E_START_BROWSE_SECTION=Library E2E_ALLOW_RESTORED_SESSION=1 E2E_FAIL_ON_SKIPPED=1 $(MAKE) test-e2e-tvos \
		JOURNEY_SRC=$(MUSIC_BED_SYNC_JOURNEY_SRC) \
		E2E_PROFILE=tvos-music-bed-sync

# ── Legacy alias ─────────────────────────────────────────────────────
test-e2e-ios: test-e2e-iphone

# ── Run all platforms sequentially ────────────────────────────────────
# Sequential default. Use -k to continue on failures.
test-e2e-all:
	@$(MAKE) -k \
		test-e2e-web-headless \
		test-e2e-iphone \
		test-e2e-ipad \
		test-e2e-tvos

# ── Run Apple platforms in parallel ─────────────────────────────────
# Uses profile-scoped config, journey, result, and DerivedData paths.
test-e2e-apple-parallel:
	@$(MAKE) -j3 test-e2e-iphone test-e2e-ipad test-e2e-tvos

test-e2e-apple-create-readiness:
	@$(MAKE) test-e2e-iphone-create-readiness
	@$(MAKE) test-e2e-ipad-create-readiness
	@$(MAKE) test-e2e-tvos-create-readiness

# ── Docker ──────────────────────────────────────────────────────────
DOCKER_TAG ?= latest
BACKEND_IMAGE = ebook-tools-backend
FRONTEND_IMAGE = ebook-tools-frontend

docker-build-backend:
	docker build -t $(BACKEND_IMAGE):$(DOCKER_TAG) -f docker/backend/Dockerfile .

docker-build-frontend:
	docker build -t $(FRONTEND_IMAGE):$(DOCKER_TAG) -f docker/frontend/Dockerfile \
		--build-arg VITE_API_BASE_URL=https://api.langtools.fifosk.synology.me \
		--build-arg VITE_STORAGE_BASE_URL=https://api.langtools.fifosk.synology.me/storage/jobs \
		.

docker-build: docker-build-backend docker-build-frontend

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-status:
	@docker compose ps
	@echo ""
	@echo "Backend health:"
	@curl -sf http://localhost:8000/_health 2>/dev/null || echo "  not reachable"
	@echo ""
	@echo "Frontend:"
	@curl -sf -o /dev/null -w "  HTTP %{http_code}" http://localhost:5173/ 2>/dev/null || echo "  not reachable"
	@echo ""
	@echo "Monitoring:"
	@curl -sf http://localhost:9090/-/healthy 2>/dev/null && echo "  Prometheus: healthy" || echo "  Prometheus: not reachable"
	@curl -sf -o /dev/null -w "  Grafana: HTTP %{http_code}\n" http://localhost:3000/api/health 2>/dev/null || echo "  Grafana: not reachable"
	@echo ""

# ── Monitoring ────────────────────────────────────────────────────────────
monitoring-up:
	docker compose up -d prometheus grafana postgres-exporter

monitoring-down:
	docker compose stop prometheus grafana postgres-exporter

monitoring-logs:
	docker compose logs -f prometheus grafana postgres-exporter

monitoring-status:
	@echo "Prometheus:"
	@curl -sf http://localhost:9090/-/healthy 2>/dev/null && echo "  healthy" || echo "  not reachable"
	@echo "Grafana:"
	@curl -sf -o /dev/null -w "  HTTP %{http_code}\n" http://localhost:3000/api/health 2>/dev/null || echo "  not reachable"
	@echo "Postgres Exporter:"
	@curl -sf -o /dev/null -w "  HTTP %{http_code}\n" http://localhost:9187/metrics 2>/dev/null || echo "  not reachable"

# ── Database helpers ──────────────────────────────────────────────────────
db-shell:
	docker exec -it ebook-tools-postgres psql -U ebook_tools -d ebook_tools

db-migrate:
	docker exec ebook-tools-backend alembic upgrade head

# ── Kubernetes / Helm (POC) ──────────────────────────────────────────────
K8S_NAMESPACE ?= ebook-tools
HELM_RELEASE  ?= ebook-tools
HELM_CHART    ?= helm/ebook-tools

k8s-build: docker-build
	@echo "Images built. Import into k3s with: make k8s-import-images"

k8s-import-images:
	docker save ebook-tools-backend:latest | limactl shell k3s sudo k3s ctr images import -
	docker save ebook-tools-frontend:latest | limactl shell k3s sudo k3s ctr images import -
	@echo "Images imported into k3s."

k8s-deploy:
	helm upgrade --install $(HELM_RELEASE) $(HELM_CHART) \
		--namespace $(K8S_NAMESPACE) --create-namespace \
		--set global.imagePullPolicy=Never

k8s-status:
	@echo "=== Pods ==="
	@kubectl -n $(K8S_NAMESPACE) get pods
	@echo ""
	@echo "=== Services ==="
	@kubectl -n $(K8S_NAMESPACE) get svc
	@echo ""
	@echo "=== Ingress ==="
	@kubectl -n $(K8S_NAMESPACE) get ingress
	@echo ""
	@echo "=== PVCs ==="
	@kubectl -n $(K8S_NAMESPACE) get pvc
	@echo ""
	@echo "=== CronJobs ==="
	@kubectl -n $(K8S_NAMESPACE) get cronjobs

k8s-logs:
	kubectl -n $(K8S_NAMESPACE) logs -l app.kubernetes.io/component=backend -f --tail=100

k8s-teardown:
	helm uninstall $(HELM_RELEASE) --namespace $(K8S_NAMESPACE)

k8s-lint:
	helm lint $(HELM_CHART)
	helm template $(HELM_RELEASE) $(HELM_CHART) > /dev/null && echo "Template rendering: OK"

# ── Argo CD (optional GitOps layer) ─────────────────────────────────────
argocd-install:
	kubectl create namespace argocd 2>/dev/null || true
	kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
	@echo "Waiting for Argo CD server..."
	kubectl -n argocd wait --for=condition=available deploy/argocd-server --timeout=180s
	@echo "Argo CD installed. Run 'make argocd-password' for credentials."

argocd-app:
	kubectl apply -f helm/argocd/application.yaml
	@echo "Application registered. Open Argo CD UI with: make argocd-ui"

argocd-ui:
	@echo "Argo CD UI: https://localhost:8080 (admin / $$(make -s argocd-password))"
	kubectl -n argocd port-forward svc/argocd-server 8080:443

argocd-password:
	@kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' 2>/dev/null | base64 -d; echo

argocd-teardown:
	kubectl delete -f helm/argocd/application.yaml 2>/dev/null || true
	kubectl delete namespace argocd 2>/dev/null || true
	@echo "Argo CD removed."
