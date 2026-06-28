from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASIC_PLAYBACK_JOURNEY = ROOT / "tests" / "e2e" / "journeys" / "basic_playback.json"
CREATE_READINESS_JOURNEY = ROOT / "tests" / "e2e" / "journeys" / "create_readiness.json"
MUSIC_BED_SYNC_JOURNEY = ROOT / "tests" / "e2e" / "journeys" / "music_bed_sync.json"
JOURNEY_RUNNER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReaderUITests"
    / "JourneyRunner.swift"
)
WEB_JOURNEY_RUNNER = ROOT / "tests" / "e2e" / "journey_runner.py"


def test_create_readiness_journey_checks_runtime_create_contract() -> None:
    journey = json.loads(CREATE_READINESS_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    settings_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "browseSectionSettingsButton"
    )
    create_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "browseSectionCreateButton"
    )
    runtime_steps = steps[settings_index:create_index]

    assert any(step.get("selector") == "settingsCreateContractRow" for step in runtime_steps)
    assert any(step.get("selector") == "settingsLibraryActionsContractRow" for step in runtime_steps)
    assert any(step.get("selector") == "settingsOfflineExportsContractRow" for step in runtime_steps)
    assert any(step.get("selector") == "settingsPlaybackStateContractRow" for step in runtime_steps)
    assert any(step.get("selector") == "settingsNotificationsContractRow" for step in runtime_steps)
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/books/options",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/books/jobs",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/pipelines/files",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/subtitles/delete-source",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/subtitles/jobs",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/subtitles/youtube/dub",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/acquisition/providers",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/acquisition/discover",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/acquisition/acquire",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/acquisition/artifacts/{artifact_id}/prepare",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/acquisition/jobs",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/acquisition/jobs/{task_id}",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/creation/templates",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/creation/templates/{template_id}",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsLibraryActionsContractRow",
        "text": "/api/library/items",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsLibraryActionsContractRow",
        "text": "/api/library/items/{job_id}/upload-source",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsLibraryActionsContractRow",
        "text": "/api/library/isbn/lookup",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsOfflineExportsContractRow",
        "text": "/api/exports",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsOfflineExportsContractRow",
        "text": "/api/exports/{export_id}/download",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsOfflineExportsContractRow",
        "text": "interactive-text",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsPlaybackStateContractRow",
        "text": "/api/bookmarks/{job_id}",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsPlaybackStateContractRow",
        "text": "/api/resume",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsPlaybackStateContractRow",
        "text": "job_id",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsNotificationsContractRow",
        "text": "/api/notifications/devices",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsNotificationsContractRow",
        "text": "/api/notifications/test",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsNotificationsContractRow",
        "text": "/api/notifications/preferences",
        "timeout": 20,
    } in runtime_steps


def test_music_bed_sync_journey_exercises_reader_music_transport_pair() -> None:
    journey = json.loads(MUSIC_BED_SYNC_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    assert journey["id"] == "music_bed_sync"
    assert {
        "action": "assert_visible",
        "selector": "e2eMusicBedPauseButton",
        "platforms": ["tvOS"],
        "timeout": 30,
        "screenshot": "music_bed_player_opened",
    } in steps
    assert {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "reader=paused",
        "platforms": ["tvOS"],
        "timeout": 15,
        "screenshot": "music_bed_pause_observed",
    } in steps
    assert {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "reader=playing",
        "platforms": ["tvOS"],
        "timeout": 55,
        "screenshot": "music_bed_play_observed",
    } in steps
    assert {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "music=playing",
        "platforms": ["tvOS"],
        "timeout": 10,
    } in steps
    assert {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "surface=reader",
        "platforms": ["tvOS"],
        "timeout": 10,
    } in steps
    assert {
        "action": "press_remote_button",
        "button": "playPause",
        "platforms": ["tvOS"],
        "screenshot": "music_bed_remote_pause_pressed",
    } in steps
    remote_pause_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("screenshot") == "music_bed_remote_pause_pressed"
    )
    assert steps[remote_pause_index + 1] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "readerTransportCommands=1",
        "platforms": ["tvOS"],
        "timeout": 10,
    }
    assert steps[remote_pause_index + 2] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "lastAction=pause",
        "platforms": ["tvOS"],
        "timeout": 10,
    }
    assert steps[remote_pause_index + 3] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "reader=paused",
        "platforms": ["tvOS"],
        "timeout": 10,
        "screenshot": "music_bed_remote_pause_observed",
    }
    assert steps[remote_pause_index + 4] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "music=paused",
        "platforms": ["tvOS"],
        "timeout": 10,
    }
    assert steps[remote_pause_index + 5] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "guard=true",
        "platforms": ["tvOS"],
        "timeout": 10,
    }
    assert steps[remote_pause_index + 6] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "surface=reader",
        "platforms": ["tvOS"],
        "timeout": 10,
    }
    assert {
        "action": "wait",
        "ms": 12500,
        "platforms": ["tvOS"],
    } in steps
    assert {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "reader=paused",
        "platforms": ["tvOS"],
        "timeout": 10,
        "screenshot": "music_bed_remote_pause_long_hold_observed",
    } in steps
    assert {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "lastAction=play",
        "platforms": ["tvOS"],
        "timeout": 10,
    } in steps
    assert {
        "action": "press_remote_button",
        "button": "playPause",
        "platforms": ["tvOS"],
        "screenshot": "music_bed_remote_play_pressed",
    } in steps
    remote_play_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("screenshot") == "music_bed_remote_play_pressed"
    )
    assert steps[remote_play_index + 1] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "readerTransportCommands=2",
        "platforms": ["tvOS"],
        "timeout": 10,
    }
    assert {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "guard=false",
        "platforms": ["tvOS"],
        "timeout": 10,
    } in steps
    assert {
        "action": "tap",
        "selector": "e2eReaderPlayCommandButton",
        "platforms": ["tvOS"],
        "screenshot": "music_bed_direct_play_command_pressed",
    } in steps
    direct_play_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("screenshot") == "music_bed_direct_play_command_pressed"
    )
    assert steps[direct_play_index + 1] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "readerTransportCommands=3",
        "platforms": ["tvOS"],
        "timeout": 10,
    }
    assert steps[direct_play_index + 2] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "lastAction=pause",
        "platforms": ["tvOS"],
        "timeout": 10,
    }
    assert steps[direct_play_index + 3] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "reader=paused",
        "platforms": ["tvOS"],
        "timeout": 10,
        "screenshot": "music_bed_direct_play_resolved_pause",
    }
    assert {
        "action": "tap",
        "selector": "e2eReaderPauseCommandButton",
        "platforms": ["tvOS"],
        "screenshot": "music_bed_direct_pause_command_pressed",
    } in steps
    direct_pause_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("screenshot") == "music_bed_direct_pause_command_pressed"
    )
    assert steps[direct_pause_index + 1] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "readerTransportCommands=4",
        "platforms": ["tvOS"],
        "timeout": 10,
    }
    assert steps[direct_pause_index + 2] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "lastAction=play",
        "platforms": ["tvOS"],
        "timeout": 10,
    }
    assert steps[direct_pause_index + 3] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "reader=playing",
        "platforms": ["tvOS"],
        "timeout": 15,
        "screenshot": "music_bed_direct_pause_resolved_play",
    }
    assert {
        "action": "press_remote_button",
        "button": "playPause",
        "count": 2,
        "interval_ms": 150,
        "platforms": ["tvOS"],
        "screenshot": "music_bed_remote_double_pause_pressed",
    } in steps
    remote_double_pause_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("screenshot") == "music_bed_remote_double_pause_pressed"
    )
    assert steps[remote_double_pause_index + 1] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "readerTransportCommands=5",
        "platforms": ["tvOS"],
        "timeout": 10,
    }
    assert steps[remote_double_pause_index + 2] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "lastAction=pause",
        "platforms": ["tvOS"],
        "timeout": 10,
    }
    assert steps[remote_double_pause_index + 3] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "reader=paused",
        "platforms": ["tvOS"],
        "timeout": 10,
        "screenshot": "music_bed_remote_double_pause_observed",
    }
    remote_final_play_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("screenshot") == "music_bed_remote_final_play_pressed"
    )
    assert steps[remote_final_play_index + 1] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "readerTransportCommands=6",
        "platforms": ["tvOS"],
        "timeout": 10,
    }
    assert steps[remote_final_play_index + 2] == {
        "action": "assert_value_contains",
        "selector": "e2eMusicBedSyncStatus",
        "text": "lastAction=play",
        "platforms": ["tvOS"],
        "timeout": 10,
    }


def test_create_readiness_journey_checks_ipad_split_pane_geometry() -> None:
    journey = json.loads(CREATE_READINESS_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    create_tab_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "browseSectionCreateButton"
    )
    generate_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "createJobTypePicker"
        and step.get("text") == "Generate"
    )
    initial_create_steps = steps[create_tab_index:generate_index]

    assert {
        "action": "assert_frame",
        "selector": "appleBookCreateSetupPane",
        "platforms": ["iPad"],
        "timeout": 15,
        "min_width": 180,
        "max_width": 340,
        "min_height": 360,
    } in initial_create_steps
    assert {
        "action": "assert_frame",
        "selector": "appleBookCreateSettingsPane",
        "platforms": ["iPad"],
        "timeout": 15,
        "min_width": 420,
        "min_height": 360,
        "screenshot": "ipad_create_split_panes",
    } in initial_create_steps


def test_journey_runner_supports_platform_scoped_steps() -> None:
    source = JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert "var platforms: [String]?" in source
    assert "guard shouldRun(step) else" in source
    assert "private func shouldRun(_ step: JourneyStep) -> Bool" in source
    assert "platform.rawValue.lowercased()" in source


def test_web_journey_runner_skips_non_web_platform_steps() -> None:
    source = WEB_JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert "if not self._should_run(step):" in source
    assert "def _should_run(self, step: dict) -> bool:" in source
    assert '{"web", "browser"}' in source


def test_basic_playback_journey_smoke_checks_tvos_create_reachability() -> None:
    journey = json.loads(BASIC_PLAYBACK_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    version_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "appVersionBadge"
        and step.get("action") == "assert_frame"
    )
    search_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "browseSectionSearchButton"
        and step.get("action") == "navigate_tab"
    )
    create_steps = steps[version_index:search_index]

    assert {
        "action": "assert_visible",
        "selector": "browseSectionCreateButton",
        "platforms": ["tvOS"],
        "timeout": 10,
    } in create_steps
    assert {
        "action": "navigate_tab",
        "tab": "Create",
        "selector": "browseSectionCreateButton",
        "platforms": ["tvOS"],
        "screenshot": "tvos_create_tab",
    } in create_steps
    assert {
        "action": "assert_visible",
        "selector": "appleBookCreateView",
        "platforms": ["tvOS"],
        "timeout": 15,
    } in create_steps
    assert {
        "action": "assert_visible",
        "selector": "createJobTypePicker",
        "platforms": ["tvOS"],
        "timeout": 15,
    } in create_steps


def test_basic_playback_journey_checks_tvos_now_playing_return_after_back() -> None:
    journey = json.loads(BASIC_PLAYBACK_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    back_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("action") == "go_back"
        and step.get("screenshot") == "returned_to_menu"
    )

    assert steps[back_index + 1] == {
        "action": "assert_visible",
        "selector": "nowPlayingReturnButton",
        "platforms": ["tvOS"],
        "timeout": 10,
        "screenshot": "tvos_now_playing_return",
    }


def test_create_readiness_journey_checks_generated_book_defaults_before_media_modes() -> None:
    journey = json.loads(CREATE_READINESS_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    generated_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "createJobTypePicker"
        and step.get("text") == "Generate"
    )
    narrate_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "createJobTypePicker"
        and step.get("text") == "Narrate EPUB"
    )
    generated_steps = steps[generated_index:narrate_index]

    assert generated_index < narrate_index
    assert {
        "action": "assert_visible",
        "selector": "createBookTopicField",
        "timeout": 15,
    } in generated_steps
    assert {
        "action": "assert_visible",
        "selector": "createBookTitleField",
        "timeout": 15,
    } in generated_steps
    assert {
        "action": "assert_non_empty_value",
        "selector": "createBookAuthorField",
        "placeholder": "Author",
        "timeout": 15,
    } in generated_steps
    assert {
        "action": "enter_text",
        "selector": "createGeneratedSourceBookTitleField",
        "text": "Inferno",
        "timeout": 15,
    } in generated_steps
    assert {
        "action": "assert_value_contains",
        "selector": "createGeneratedSourceBookAuthorField",
        "text": "Dan Brown",
        "timeout": 15,
    } in generated_steps
    assert {
        "action": "enter_text",
        "selector": "createGeneratedSourceBookGenreField",
        "text": "Conspiracy thriller",
        "timeout": 15,
    } in generated_steps
    assert any(step.get("selector") == "createBookSummaryField" for step in generated_steps)
    assert any(step.get("selector") == "createBookSentenceStepper" for step in generated_steps)
    for selector in [
        "createBookAudioModePicker",
        "createBookAudioBitratePicker",
        "createBookWrittenModePicker",
        "createBookOutputHtmlToggle",
        "createBookOutputPdfToggle",
        "createBookIllustrationsToggle",
        "createBookImageNodeAvailabilityButton",
        "createBookSentencesPerFileStepper",
        "createBookTranslationBatchSizeStepper",
        "createBookThreadCountField",
        "createBookQueueSizeField",
        "createBookJobMaxWorkersField",
    ]:
        assert any(
            step.get("action") == "assert_visible"
            and step.get("selector") == selector
            and step.get("timeout") == 15
            for step in generated_steps
        )
    assert {
        "action": "tap",
        "selector": "createBookIllustrationsToggle",
        "unless_visible": "createBookImageNodeAvailabilityButton",
        "timeout": 15,
    } in generated_steps


def test_create_readiness_journey_checks_narrate_discovery_policy_provider() -> None:
    journey = json.loads(CREATE_READINESS_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    narrate_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "createJobTypePicker"
        and step.get("text") == "Narrate EPUB"
    )
    subtitle_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "createJobTypePicker"
        and step.get("text") == "Subtitles"
    )
    narrate_steps = steps[narrate_index:subtitle_index]

    assert narrate_index < subtitle_index
    assert {
        "action": "select_option",
        "selector": "createNarrateSourceModePicker",
        "text": "Discovery",
        "platforms": ["iPhone", "iPad"],
        "timeout": 15,
    } in narrate_steps
    assert {
        "action": "assert_visible",
        "selector": "createNarrateDiscoveryPanel",
        "timeout": 15,
    } in narrate_steps
    assert {
        "action": "assert_visible",
        "selector": "createNarrateDiscoveryProviderPicker",
        "timeout": 15,
    } in narrate_steps
    assert {
        "action": "select_option",
        "selector": "createNarrateDiscoveryProviderPicker",
        "text": "Z-Library import",
        "timeout": 15,
    } in narrate_steps
    assert {
        "action": "assert_value_contains",
        "selector": "createNarrateDiscoveryMessage",
        "text": "Direct Z-Library automation is intentionally disabled",
        "timeout": 15,
        "screenshot": "narrate_discovery_attended_import",
    } in narrate_steps


def test_create_readiness_journey_checks_subtitle_job_settings_before_youtube() -> None:
    journey = json.loads(CREATE_READINESS_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    subtitle_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "createJobTypePicker"
        and step.get("text") == "Subtitles"
    )
    youtube_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "createJobTypePicker"
        and step.get("text") == "YouTube Dub"
    )
    subtitle_steps = steps[subtitle_index:youtube_index]

    assert subtitle_index < youtube_index
    assert {
        "action": "assert_non_empty_value",
        "selector": "createSubtitleSourcePathField",
        "placeholder": "Server subtitle path",
        "timeout": 25,
        "screenshot": "subtitle_defaults",
    } in subtitle_steps
    for selector in [
        "createSubtitleOutputFormatPicker",
        "createSubtitleWorkerCountStepper",
        "createSubtitleBatchSizeStepper",
        "createSubtitleTranslationProviderPicker",
    ]:
        assert any(
            step.get("action") == "assert_visible"
            and step.get("selector") == selector
            and step.get("timeout") == 15
            for step in subtitle_steps
        )


def test_create_readiness_journey_checks_youtube_job_settings() -> None:
    journey = json.loads(CREATE_READINESS_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    youtube_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "createJobTypePicker"
        and step.get("text") == "YouTube Dub"
    )
    youtube_steps = steps[youtube_index:]

    assert {
        "action": "assert_non_empty_value",
        "selector": "createYoutubeVideoPathField",
        "placeholder": "Video path",
        "timeout": 25,
    } in youtube_steps
    assert {
        "action": "assert_non_empty_value",
        "selector": "createYoutubeSubtitlePathField",
        "placeholder": "Subtitle path",
        "timeout": 25,
        "screenshot": "youtube_dub_defaults",
    } in youtube_steps
    for selector in [
        "createYoutubeTargetHeightPicker",
        "createYoutubeOriginalMixStepper",
        "createYoutubeFlushSentencesStepper",
        "createYoutubeTranslationBatchSizeStepper",
        "createYoutubeSplitBatchesToggle",
        "createYoutubePreserveAspectRatioToggle",
    ]:
        assert any(
            step.get("action") == "assert_visible"
            and step.get("selector") == selector
            and step.get("timeout") == 15
            for step in youtube_steps
        )
    assert any(
        step.get("action") == "assert_visible"
        and step.get("selector") == "createBookOpenWebCreateButton"
        and step.get("timeout") == 15
        for step in youtube_steps
    )


def test_journey_runner_supports_value_contains_assertion() -> None:
    source = JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert 'case "assert_value_contains":' in source
    assert "private func doAssertValueContains(_ step: JourneyStep)" in source
    assert "localizedCaseInsensitiveContains(expectedText)" in source


def test_journey_runners_support_tap_action() -> None:
    source = JOURNEY_RUNNER.read_text(encoding="utf-8")
    web_source = WEB_JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert "var unless_visible: String?" in source
    assert 'case "tap":' in source
    assert "private func doTap(_ step: JourneyStep)" in source
    assert "step.unless_visible?.trimmingCharacters" in source
    assert "selectElement(element)" in source
    assert "def _do_tap(self, step: dict) -> None:" in web_source
    assert "unless_visible" in web_source
    assert "def _timeout_ms(self, step: dict) -> int:" in web_source


def test_journey_runner_scrolls_before_visibility_and_text_steps() -> None:
    source = JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert "private func doAssertVisible(_ step: JourneyStep)" in source
    assert "private func doEnterText(_ step: JourneyStep)" in source
    assert "scrollElementIntoView(element, timeout: min(timeout, 4))" in source
    assert "scrollElementIntoView(element, timeout: 1)" in source
