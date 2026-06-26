.PHONY: test test-fast test-audio test-translation test-webapi test-apple test-services \
       test-pipeline test-cli test-auth test-library test-render test-media \
       test-config test-metadata test-changed \
       test-backend-auth-session \
       test-backend-library-search-source-isbn test-backend-admin-system-status \
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
       test-web-full build-web-production \
       generate-language-catalogs check-language-catalogs test-apple-language-catalogs \
       test-apple-create-readiness-contract test-apple-local-surface-contract \
       test-apple-contracts \
       build-apple-macos-ipad-style apple-macos-ipad-destination \
       build-apple-macos-ipad-style-dry-run apple-devices apple-device-update \
       apple-device-preflight apple-device-signed-build-only apple-device-deploy-dry-run \
       apple-device-full-entitlement-plan apple-device-full-entitlement-build \
       apple-device-full-entitlement-install apple-device-full-entitlement-fallback-install \
       apple-device-full-entitlement-stable-install \
       build-apple-iphone-simulator build-apple-ipad-simulator \
       build-apple-ios-simulators build-apple-ios-uitests build-apple-tvos-simulator \
       build-apple-office-ipad-surfaces verify-apple-office-ipad-surfaces \
       build-apple-local-surfaces verify-apple-local-surfaces \
       verify-apple-cross-surface-checkpoint \
       apple-pipeline-contracts apple-pipeline-backend apple-pipeline-backend-tests \
       apple-pipeline-source-sync apple-pipeline-web-checks \
       apple-pipeline-simulator-smoke apple-pipeline-simulator-smoke-dry-run apple-pipeline-simulator-smokes-dry-run \
       apple-pipeline-owned-journeys-list apple-pipeline-owned-journeys apple-pipeline-owned-journey apple-pipeline-owned-journey-dry-run \
       apple-pipeline-owned-journeys-dry-run apple-pipeline-ipad-create-readiness \
       apple-pipeline-ipad-create-readiness-dry-run apple-pipeline-tvos-create-readiness \
       apple-pipeline-tvos-create-readiness-dry-run apple-pipeline-orchestration-dry-runs \
       verify-apple-shared-pipeline verify-apple-dogfood-pipeline verify-apple-golden-pipeline \
       test-e2e test-e2e-headless test-e2e-web test-e2e-web-headless \
       test-e2e-ios test-e2e-iphone test-e2e-ipad test-e2e-tvos \
       test-e2e-iphone-create-readiness test-e2e-ipad-create-readiness \
       test-e2e-tvos-create-readiness test-e2e-apple-create-readiness \
       test-e2e-all test-e2e-apple-parallel \
       docker-build-backend docker-build-frontend docker-build \
       docker-up docker-down docker-logs docker-status \
       monitoring-up monitoring-down monitoring-logs monitoring-status \
       test-observability \
       k8s-build k8s-import-images k8s-deploy k8s-status k8s-logs k8s-teardown k8s-lint \
       argocd-install argocd-app argocd-ui argocd-password argocd-teardown

SHELL := /bin/bash
PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
APPLE_PIPELINE_ROOT ?= /Users/fifo/Projects/home/apple-device-app-pipeline
APPLE_PIPELINE_APP ?= ebook-tools
APPLE_PIPELINE_PYTHON ?= python3
APPLE_PIPELINE_SMOKE_PROFILE ?= ipados
APPLE_PIPELINE_SMOKE_PROFILES ?= ios ipados tvos
APPLE_PIPELINE_JOURNEY_PROFILE ?= ipados
APPLE_PIPELINE_JOURNEY_PROFILES ?= iphone ipados tvos iphone-create ipados-create tvos-create ios-uitests-build macos-ipad-style-dry-run macos-ipad-style
APPLE_DEVICE_PROFILE ?= ipad
APPLE_DEVICE_SIGNED_ARTIFACT_PATH ?= test-results/DerivedData-device-full-entitlements/Build/Products/Debug-iphoneos/InteractiveReader.app
APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT ?= 10

# ── Full suite ───────────────────────────────────────────────────────────
test:
	$(PYTHON) -m pytest

# ── Skip slow / integration tests ───────────────────────────────────────
test-fast:
	$(PYTHON) -m pytest -m "not slow and not integration"

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
		tests/modules/webapi/test_search_routes.py \
		tests/test_library_source_and_isbn_metadata.py

test-backend-admin-system-status:
	$(PYTHON) -m pytest \
		tests/modules/webapi/test_system_routes.py \
		tests/modules/webapi/test_job_action_routes.py

test-backend-runtime-descriptor:
	$(PYTHON) -m pytest \
		tests/modules/webapi/test_system_routes.py::test_runtime_descriptor_helper_returns_pipeline_contract \
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
		tests/test_create_book.py::test_pipeline_file_picker_records_safe_timing \
		tests/test_create_book.py::test_pipeline_content_index_uses_selected_epub \
		tests/test_create_book.py::test_delete_pipeline_ebook_is_idempotent_for_missing_in_scope_file \
		tests/test_create_book.py::test_delete_pipeline_ebook_rejects_missing_file_outside_books_root \
		tests/test_create_book.py::test_upload_pipeline_ebook_persists_file_in_books_root

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
	$(PYTHON) -m pytest tests/webapi/test_subtitles_router.py

test-backend-playback-state:
	$(PYTHON) -m pytest \
		tests/modules/webapi/test_resume_routes.py \
		tests/modules/webapi/test_bookmark_routes.py \
		tests/modules/webapi/test_lookup_cache_routes.py \
		tests/modules/test_resume_service.py

test-backend-playback-media:
	$(PYTHON) -m pytest \
		tests/modules/webapi/test_job_media_routes.py \
		tests/modules/webapi/test_library_media_route.py \
		tests/modules/webapi/test_library_media_file_download.py

test-backend-offline-export:
	$(PYTHON) -m pytest tests/modules/webapi/test_export_routes.py

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
		src/components/__tests__/bookNarrationDiscoveryProviders.test.ts \
		src/components/__tests__/bookNarrationFormUtils.test.ts \
		src/components/__tests__/useBookNarrationChapters.test.tsx \
		src/components/__tests__/useBookNarrationFiles.test.tsx \
		src/components/__tests__/useBookNarrationVoices.test.tsx \
		src/components/__tests__/BookNarrationStepBar.test.tsx \
		src/components/__tests__/BookNarrationSubmitStatus.test.tsx \
		src/components/__tests__/BookNarrationFileDialog.test.tsx \
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
		src/components/__tests__/LibraryItemActions.test.tsx \
		src/components/__tests__/LibraryItemMediaCells.test.tsx \
		src/components/__tests__/LibraryStatusBadge.test.tsx \
		src/components/__tests__/libraryListResume.test.ts

test-web-job-progress-focused:
	npm --prefix web test -- --run \
		src/components/__tests__/JobProgress.test.tsx \
		src/components/__tests__/jobProgressParameters.test.ts \
		src/components/__tests__/jobProgressUtils.test.ts \
		src/utils/__tests__/progressEvents.test.ts

test-web-playback-focused:
	npm --prefix web test -- --run \
		src/hooks/__tests__/liveMediaState.test.ts \
		src/hooks/__tests__/liveMediaTiming.test.ts \
		src/hooks/__tests__/useLiveMedia.test.tsx \
		src/components/__tests__/playerPanelUtils.test.ts \
		src/components/__tests__/playerPanelChromeState.test.ts \
		src/components/__tests__/playerPanelDocumentState.test.ts \
		src/components/__tests__/usePlayerPanelActiveText.test.tsx \
		src/components/__tests__/usePlayerPanelMediaNavigation.test.tsx \
		src/components/__tests__/PlayerPanelBoundaryState.test.tsx \
		src/components/__tests__/PlayerPanelContent.test.tsx \
		src/components/__tests__/PlayerPanelNavigationGroups.test.tsx \
		src/components/__tests__/PlayerPanelSearchSlot.test.tsx \
		src/components/__tests__/PlayerPanelSentenceJumpDatalist.test.tsx \
		src/components/__tests__/SleepTimerControl.test.tsx \
		src/components/__tests__/TranscriptWord.test.tsx \
		src/components/__tests__/VideoPlayer.test.tsx \
		src/components/__tests__/YoutubeDubPlayer.test.tsx \
		src/components/video-subtitles/__tests__/subtitleTrackOverlayUtils.test.ts \
		src/lib/media/__tests__/audioUrlResolver.test.ts \
		src/lib/media/__tests__/sentenceChunkIndex.test.ts \
		src/lib/playback/__tests__/sequencePlan.test.ts \
		src/utils/__tests__/browserStorage.test.ts

test-web-video-dubbing-focused:
	npm --prefix web test -- --run \
		src/pages/__tests__/videoDubbingDiscovery.test.ts \
		src/pages/__tests__/useVideoDubbingAcquisitionProviders.test.tsx \
		src/pages/__tests__/useVideoDubbingCreationTemplate.test.tsx \
		src/pages/__tests__/useVideoDubbingDiscoverySearch.test.tsx \
		src/pages/__tests__/useVideoDubbingDownloadStation.test.tsx \
		src/pages/__tests__/useVideoDubbingJobActions.test.tsx \
		src/pages/__tests__/videoDubbingUtils.test.ts \
		src/pages/__tests__/useVideoDubbingSelectionState.test.tsx \
		src/pages/__tests__/useVideoDubbingMetadata.test.tsx \
		src/pages/__tests__/useVideoDubbingLanguageState.test.tsx \
		src/pages/__tests__/useVideoDubbingVoiceState.test.tsx \
		src/pages/__tests__/useVideoDubbingModelState.test.tsx \
		src/pages/__tests__/useVideoDubbingOutputState.test.tsx \
		src/pages/__tests__/useVideoDubbingSubtitleExtraction.test.tsx \
		src/pages/__tests__/useVideoDubbingLibraryState.test.tsx \
		src/pages/__tests__/useVideoDubbingSourceSelection.test.tsx \
		src/pages/__tests__/VideoDubbingPage.test.tsx \
		src/pages/__tests__/YoutubeVideoPage.test.tsx

test-web-subtitle-tool-focused:
	npm --prefix web test -- --run \
		src/pages/__tests__/subtitleToolUtils.test.ts \
		src/pages/__tests__/subtitleJobPresentation.test.ts \
		src/pages/__tests__/subtitleJobUtils.test.ts \
		src/pages/__tests__/subtitleMetadataUtils.test.ts \
		src/pages/__tests__/subtitleSourceUtils.test.ts \
		src/pages/__tests__/useSubtitleTvMetadata.test.tsx \
		src/pages/__tests__/useSubtitleSources.test.tsx \
		src/pages/__tests__/useSubtitleJobResults.test.tsx \
		src/pages/__tests__/useSubtitleModels.test.tsx \
		src/pages/__tests__/useSubtitleLanguageDefaults.test.tsx \
		src/pages/__tests__/useSubtitleShowOriginalPreference.test.tsx \
		src/pages/__tests__/useSubtitlePrefill.test.tsx \
		src/pages/__tests__/useSubtitleLanguageState.test.tsx \
		src/pages/__tests__/useSubtitleSubmitFeedback.test.tsx \
		src/pages/__tests__/useSubtitleSourceMode.test.tsx \
		src/pages/__tests__/useSubtitleProcessingOptions.test.tsx \
		src/pages/__tests__/useSubtitleTabState.test.tsx \
		src/pages/__tests__/useSubtitleSubmitStatus.test.tsx \
		src/pages/__tests__/useSubtitleSubmit.test.tsx

test-web-app-view-deeplink-focused:
	npm --prefix web test -- --run \
		src/utils/__tests__/appViewDeepLink.test.ts

test-web-full:
	npm --prefix web test -- --run

build-web-production:
	npm --prefix web run build

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

test-apple-create-readiness-contract:
	$(PYTHON) -m pytest -q tests/scripts/test_check_apple_create_readiness.py tests/test_apple_create_readiness_journey.py tests/test_apple_e2e_env_file_contract.py

test-apple-local-surface-contract:
	$(PYTHON) -m pytest -q tests/test_apple_ios_build_contract.py tests/test_apple_tvos_build_contract.py tests/test_apple_macos_ipad_style_contract.py tests/test_apple_local_surface_build_contract.py

test-apple-contracts:
	$(PYTHON) -m pytest -q tests/test_language_catalog_parity.py tests/test_backend_dependency_contract.py tests/test_apple_create_split_layout.py tests/test_apple_create_options_fallback.py tests/test_apple_create_readiness_journey.py tests/test_apple_runtime_descriptor_contract.py tests/test_apple_offline_export_contract.py tests/test_apple_job_health_timeline_contract.py tests/test_apple_job_restart_contract.py tests/test_apple_library_metadata_edit_contract.py tests/test_apple_library_source_upload_review_contract.py tests/test_apple_library_source_diagnostics_contract.py tests/test_apple_resume_status_contract.py tests/test_apple_browse_chrome_contract.py tests/test_apple_macos_ipad_style_contract.py tests/test_apple_ios_build_contract.py tests/test_apple_narration_history_defaults_contract.py tests/test_apple_local_surface_build_contract.py tests/test_apple_audio_stream_recovery_contract.py tests/test_apple_chunk_metadata_retry_contract.py tests/test_apple_live_media_fallback_contract.py tests/test_apple_timing_token_sanitization_contract.py tests/test_apple_token_normalization_cache_contract.py tests/test_apple_sentence_image_prefetch_contract.py tests/test_apple_playback_search_bookmark_contract.py tests/test_apple_playback_state_helpers_contract.py tests/test_apple_now_playing_contract.py tests/test_apple_sleep_timer_contract.py tests/test_apple_notification_manager_contract.py tests/test_apple_shared_pipeline_contract.py tests/test_backend_pipeline_contract.py tests/test_apple_tvos_build_contract.py tests/test_apple_e2e_env_file_contract.py tests/test_apple_e2e_login_contract.py tests/scripts/test_generate_language_catalogs.py tests/scripts/test_write_apple_e2e_config.py tests/scripts/test_check_apple_create_readiness.py tests/scripts/test_check_poc_readiness.py tests/scripts/test_ios_profile_capability_check.py tests/scripts/test_apple_merge_entitlements.py tests/scripts/test_apple_full_entitlement_signing_plan.py
	$(PYTHON) scripts/generate_language_catalogs.py --check
	bash scripts/check_apple_runtime_descriptor_payload.sh
	bash scripts/check_apple_creation_payloads.sh
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

verify-apple-local-surfaces: test-apple-contracts build-apple-local-surfaces build-apple-ios-uitests

verify-apple-cross-surface-checkpoint: test-backend-auth-session test-backend-library-search-source-isbn test-backend-admin-system-status test-backend-runtime-descriptor test-backend-create-book test-backend-creation-templates test-backend-pipeline-sources test-backend-acquisition test-backend-audio-routes test-backend-reading-beds test-backend-notifications test-backend-subtitle-router test-backend-playback-state test-backend-playback-media test-backend-offline-export test-backend-youtube-dubbing-service test-web-auth-focused test-web-admin-focused test-web-sidebar-focused test-web-create-book-focused test-web-create-intake-focused test-web-creation-templates-focused test-web-library-focused test-web-job-progress-focused test-web-playback-focused test-web-video-dubbing-focused test-web-subtitle-tool-focused test-web-app-view-deeplink-focused test-web-full build-web-production verify-apple-local-surfaces

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

verify-apple-dogfood-pipeline: verify-apple-cross-surface-checkpoint verify-apple-shared-pipeline

verify-apple-golden-pipeline: apple-pipeline-source-sync verify-apple-dogfood-pipeline

apple-device-preflight:
	bash scripts/apple_unattended_device_update.sh --profile "$(APPLE_DEVICE_PROFILE)" --device "$(APPLE_DEVICE_ID)" --device-preflight-only

apple-device-signed-build-only:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_device_deploy.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_DEVICE_PROFILE)" --signed-build-only

apple-device-deploy-dry-run:
	cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_device_deploy.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_DEVICE_PROFILE)" --dry-run

apple-device-full-entitlement-plan:
	bash scripts/apple_full_entitlement_signing_plan.sh --device "$(APPLE_DEVICE_ID)" $(if $(strip $(FULL_CAPABILITY_IOS_PROFILE)),--app-profile "$(FULL_CAPABILITY_IOS_PROFILE)") $(if $(strip $(WILDCARD_IOS_EXTENSION_PROFILE)),--extension-profile "$(WILDCARD_IOS_EXTENSION_PROFILE)") --signing-identity "$(APPLE_DEVELOPMENT_IDENTITY)"

apple-device-full-entitlement-build:
	bash scripts/apple_full_entitlement_signing_plan.sh --execute --device "$(APPLE_DEVICE_ID)" $(if $(strip $(FULL_CAPABILITY_IOS_PROFILE)),--app-profile "$(FULL_CAPABILITY_IOS_PROFILE)") $(if $(strip $(WILDCARD_IOS_EXTENSION_PROFILE)),--extension-profile "$(WILDCARD_IOS_EXTENSION_PROFILE)") --signing-identity "$(APPLE_DEVELOPMENT_IDENTITY)"

apple-device-full-entitlement-install:
	bash scripts/apple_full_entitlement_signing_plan.sh --execute --install --device "$(APPLE_DEVICE_ID)" $(if $(strip $(FULL_CAPABILITY_IOS_PROFILE)),--app-profile "$(FULL_CAPABILITY_IOS_PROFILE)") $(if $(strip $(WILDCARD_IOS_EXTENSION_PROFILE)),--extension-profile "$(WILDCARD_IOS_EXTENSION_PROFILE)") --signing-identity "$(APPLE_DEVELOPMENT_IDENTITY)"

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

apple-device-update:
	bash scripts/apple_unattended_device_update.sh --install

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
E2E_TEMP_ROOT ?= /tmp/apple-device-app-pipeline/ebook-tools
E2E_PROFILE ?= local
E2E_ENV_FILE ?= $(if $(wildcard .env),.env,$(if $(wildcard .env.local),.env.local,.env))
E2E_CONFIG_PATH ?= $(E2E_TEMP_ROOT)/$(E2E_PROFILE)/ios_e2e_config.json
E2E_JOURNEY_PATH ?= $(E2E_TEMP_ROOT)/$(E2E_PROFILE)/ios_e2e_journey.json
E2E_PLATFORM_PROFILE ?= $(E2E_PROFILE)
E2E_PLATFORM_CONFIG_PATH ?= $(E2E_TEMP_ROOT)/$(E2E_PLATFORM_PROFILE)/ios_e2e_config.json
E2E_PLATFORM_JOURNEY_PATH ?= $(E2E_TEMP_ROOT)/$(E2E_PLATFORM_PROFILE)/ios_e2e_journey.json
IOS_E2E_ONLY_TESTING ?= InteractiveReaderUITests/JourneyTests/testJourney
TVOS_E2E_ONLY_TESTING ?= InteractiveReaderTVUITests/JourneyTests/testJourney
E2E_SIMCTL_LOCK ?= $(shell $(PYTHON) -c 'import tempfile; print(tempfile.gettempdir() + "/apple-device-app-pipeline-simctl.lock")')

# Write config + journey to profile-scoped /tmp paths.
define WRITE_E2E_CONFIG
$(PYTHON) scripts/write_apple_e2e_config.py \
	--env-file "$(E2E_ENV_FILE)" \
	--config-path "$(E2E_CONFIG_PATH)" \
	--journey-src "$(JOURNEY_SRC)" \
	--journey-path "$(E2E_JOURNEY_PATH)" \
	--fallback-config-path "$(E2E_PLATFORM_CONFIG_PATH)" \
	--fallback-journey-path "$(E2E_PLATFORM_JOURNEY_PATH)"
endef

# ── iPhone E2E ───────────────────────────────────────────────────────
IPHONE_DESTINATION ?= 'platform=iOS Simulator,name=iPhone 17 Pro'
IPHONE_E2E_RESULT = $(CURDIR)/test-results/iphone-e2e.xcresult
IPHONE_DERIVED_DATA = $(CURDIR)/test-results/DerivedData-iphone
IPHONE_BUILD_DERIVED_DATA = $(CURDIR)/test-results/DerivedData-iphone-build

build-apple-iphone-simulator:
	@mkdir -p test-results
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
	@$(WRITE_E2E_CONFIG)
	@status=0; set -o pipefail; \
	E2E_CONFIG_PATH="$(E2E_CONFIG_PATH)" E2E_JOURNEY_PATH="$(E2E_JOURNEY_PATH)" \
		E2E_SIMCTL_LOCK="$(E2E_SIMCTL_LOCK)" $(PYTHON) scripts/with_simulator_lock.py -- $(XCBUILD) test \
		-project $(XCPROJ) \
		-scheme InteractiveReaderUITests \
		-destination $(IPHONE_DESTINATION) \
		-derivedDataPath $(IPHONE_DERIVED_DATA) \
		-resultBundlePath $(IPHONE_E2E_RESULT) \
		-only-testing:$(IOS_E2E_ONLY_TESTING) \
		2>&1 | tail -30 || status=$$?; \
	$(PYTHON) scripts/ios_e2e_report.py \
		--xcresult $(IPHONE_E2E_RESULT) \
		--output test-results/iphone-e2e-report.md \
		--title "iPhone E2E Test Report" \
		--screenshot-prefix iphone; \
	rm -f "$(E2E_CONFIG_PATH)" "$(E2E_JOURNEY_PATH)" "$(E2E_PLATFORM_CONFIG_PATH)" "$(E2E_PLATFORM_JOURNEY_PATH)"; \
	exit $$status

test-e2e-iphone-create-readiness:
	@$(PYTHON) scripts/check_apple_create_readiness.py --env-file "$(E2E_ENV_FILE)"
	@$(MAKE) test-e2e-iphone \
		JOURNEY_SRC=$(CREATE_READINESS_JOURNEY_SRC) \
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
	$(XCBUILD) -quiet build-for-testing \
		-project $(XCPROJ) \
		-scheme InteractiveReaderUITests \
		-configuration Debug \
		-destination $(IPAD_DESTINATION) \
		-derivedDataPath $(IOS_UITEST_BUILD_DERIVED_DATA)

build-apple-ipad-simulator:
	@mkdir -p test-results
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
	@$(WRITE_E2E_CONFIG)
	@status=0; set -o pipefail; \
	E2E_CONFIG_PATH="$(E2E_CONFIG_PATH)" E2E_JOURNEY_PATH="$(E2E_JOURNEY_PATH)" \
		E2E_SIMCTL_LOCK="$(E2E_SIMCTL_LOCK)" $(PYTHON) scripts/with_simulator_lock.py -- $(XCBUILD) test \
		-project $(XCPROJ) \
		-scheme InteractiveReaderUITests \
		-destination $(IPAD_DESTINATION) \
		-derivedDataPath $(IPAD_DERIVED_DATA) \
		-resultBundlePath $(IPAD_E2E_RESULT) \
		-only-testing:$(IOS_E2E_ONLY_TESTING) \
		2>&1 | tail -30 || status=$$?; \
	$(PYTHON) scripts/ios_e2e_report.py \
		--xcresult $(IPAD_E2E_RESULT) \
		--output test-results/ipad-e2e-report.md \
		--title "iPad E2E Test Report" \
		--screenshot-prefix ipad; \
	rm -f "$(E2E_CONFIG_PATH)" "$(E2E_JOURNEY_PATH)" "$(E2E_PLATFORM_CONFIG_PATH)" "$(E2E_PLATFORM_JOURNEY_PATH)"; \
	exit $$status

test-e2e-ipad-create-readiness:
	@$(PYTHON) scripts/check_apple_create_readiness.py --env-file "$(E2E_ENV_FILE)"
	@$(MAKE) test-e2e-ipad \
		JOURNEY_SRC=$(CREATE_READINESS_JOURNEY_SRC) \
		E2E_PROFILE=ipados-create

# ── tvOS E2E ─────────────────────────────────────────────────────────
TVOS_DESTINATION ?= 'platform=tvOS Simulator,name=Apple TV 4K (3rd generation)'
TVOS_E2E_RESULT = $(CURDIR)/test-results/tvos-e2e.xcresult
TVOS_DERIVED_DATA = $(CURDIR)/test-results/DerivedData-tvos
TVOS_BUILD_DERIVED_DATA = $(CURDIR)/test-results/DerivedData-tvos-build

build-apple-tvos-simulator:
	@mkdir -p test-results
	$(XCBUILD) -quiet build \
		-project $(XCPROJ) \
		-scheme InteractiveReaderTV \
		-configuration Debug \
		-destination $(TVOS_DESTINATION) \
		-derivedDataPath $(TVOS_BUILD_DERIVED_DATA)

test-e2e-tvos: E2E_PROFILE = tvos
test-e2e-tvos: E2E_PLATFORM_PROFILE = tvos
test-e2e-tvos:
	@rm -rf $(TVOS_E2E_RESULT) $(TVOS_DERIVED_DATA) test-results/tvos-e2e-attachments
	@$(WRITE_E2E_CONFIG)
	@status=0; set -o pipefail; \
	E2E_CONFIG_PATH="$(E2E_CONFIG_PATH)" E2E_JOURNEY_PATH="$(E2E_JOURNEY_PATH)" \
		E2E_SIMCTL_LOCK="$(E2E_SIMCTL_LOCK)" $(PYTHON) scripts/with_simulator_lock.py -- $(XCBUILD) test \
		-project $(XCPROJ) \
		-scheme InteractiveReaderTVUITests \
		-destination $(TVOS_DESTINATION) \
		-derivedDataPath $(TVOS_DERIVED_DATA) \
		-resultBundlePath $(TVOS_E2E_RESULT) \
		-only-testing:$(TVOS_E2E_ONLY_TESTING) \
		2>&1 | tail -30 || status=$$?; \
	$(PYTHON) scripts/ios_e2e_report.py \
		--xcresult $(TVOS_E2E_RESULT) \
		--output test-results/tvos-e2e-report.md \
		--title "tvOS E2E Test Report" \
		--screenshot-prefix tvos; \
	rm -f "$(E2E_CONFIG_PATH)" "$(E2E_JOURNEY_PATH)" "$(E2E_PLATFORM_CONFIG_PATH)" "$(E2E_PLATFORM_JOURNEY_PATH)"; \
	exit $$status

test-e2e-tvos-create-readiness:
	@$(PYTHON) scripts/check_apple_create_readiness.py --env-file "$(E2E_ENV_FILE)"
	@$(MAKE) test-e2e-tvos \
		JOURNEY_SRC=$(CREATE_READINESS_JOURNEY_SRC) \
		E2E_PROFILE=tvos-create

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
