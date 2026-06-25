from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
CONTRACT_CHECK = ROOT / "scripts" / "check_apple_tvos_build_helper.sh"
TESTING_DOC = ROOT / "docs" / "testing.md"
PLAN_DOC = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"
LIBRARY_BROWSE_CHROME = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "LibraryBrowseChrome.swift"
)
CREATE_ROUTING = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateRouting.swift"
)
CREATE_OUTPUT_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateOutputControls.swift"
)
CREATE_VALUE_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateValueControls.swift"
)
VIDEO_LINGUIST_COMPATIBILITY = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Shared"
    / "LinguistBubbleCompatibility.swift"
)
VIDEO_PLAYER_OVERLAY = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Playback"
    / "VideoPlayerOverlayView.swift"
)
VIDEO_PLAYER_LAYOUT = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Playback"
    / "VideoPlayerView+Layout.swift"
)
VIDEO_PLAYER_LINGUIST = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Playback"
    / "VideoPlayerView+Linguist.swift"
)
PRONUNCIATION_SPEAKER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Utilities"
    / "PronunciationSpeaker.swift"
)
MY_LINGUIST_VIEW_MODEL = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Shared"
    / "MyLinguistBubbleViewModel.swift"
)
LINGUIST_BUBBLE_PICKER_UI = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Shared"
    / "LinguistBubblePickerUI.swift"
)


def test_tvos_simulator_build_lane_is_repo_owned_and_non_deploying() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "build-apple-tvos-simulator:" in makefile
    assert "$(XCBUILD) -quiet build" in makefile
    assert "-scheme InteractiveReaderTV" in makefile
    assert "-destination $(TVOS_DESTINATION)" in makefile
    assert "TVOS_BUILD_DERIVED_DATA" in makefile

    target = makefile.split("build-apple-tvos-simulator:", 1)[1].split("\n\n", 1)[0]
    assert "apple_unattended_device_update.sh" not in target
    assert "devicectl" not in target
    assert "--install" not in target


def test_tvos_contract_check_covers_compile_lane() -> None:
    contract_check = CONTRACT_CHECK.read_text(encoding="utf-8")

    assert "build-apple-tvos-simulator:" in contract_check
    assert "InteractiveReaderTV" in contract_check
    assert "TVOS_DESTINATION" in contract_check
    assert "physical-device deployment" in contract_check


def test_docs_publish_tvos_compile_gate() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "make build-apple-tvos-simulator" in docs
    assert "tvOS simulator compile lane" in plan


def test_tvos_native_create_is_reachable_and_uses_shared_modes() -> None:
    browse_source = LIBRARY_BROWSE_CHROME.read_text(encoding="utf-8")
    routing_source = CREATE_ROUTING.read_text(encoding="utf-8")

    assert "[.jobs, .create, .library, .settings, .search]" in browse_source
    assert "AppleCreateMode.allCases" in routing_source
    assert "isTV ? []" not in routing_source


def test_tvos_create_exposes_media_job_tuning_controls() -> None:
    output_source = CREATE_OUTPUT_CONTROLS.read_text(encoding="utf-8")
    value_controls_source = CREATE_VALUE_CONTROLS.read_text(encoding="utf-8")

    assert "struct AppleBookCreateDiscreteDoubleValueControl: View" in value_controls_source
    assert 'accessibilityIdentifier("createSubtitleMirrorBatchesToggle")' in output_source

    for identifier in [
        "createSubtitleAssFontSizeControl",
        "createSubtitleAssEmphasisControl",
        "createSubtitleWorkerCountControl",
        "createSubtitleBatchSizeControl",
        "createSubtitleTranslationBatchSizeControl",
        "createYoutubeOriginalMixControl",
        "createYoutubeFlushSentencesControl",
        "createYoutubeTranslationBatchSizeControl",
    ]:
        assert f'accessibilityIdentifier("{identifier}")' in output_source


def test_tvos_video_lookup_can_play_cached_narration_reference() -> None:
    compatibility_source = VIDEO_LINGUIST_COMPATIBILITY.read_text(encoding="utf-8")
    overlay_source = VIDEO_PLAYER_OVERLAY.read_text(encoding="utf-8")
    layout_source = VIDEO_PLAYER_LAYOUT.read_text(encoding="utf-8")
    linguist_source = VIDEO_PLAYER_LINGUIST.read_text(encoding="utf-8")
    picker_ui_source = LINGUIST_BUBBLE_PICKER_UI.read_text(encoding="utf-8")

    assert "let onPlayFromNarration: (() -> Void)?" in compatibility_source
    assert "onPlayFromNarration: (() -> Void)? = nil" in compatibility_source
    assert "actions.onPlayFromNarration = onPlayFromNarration" in compatibility_source

    assert "let onPlayFromNarration: (() -> Void)?" in overlay_source
    assert "onPlayFromNarration: onPlayFromNarration" in overlay_source

    assert "onPlayFromNarration: handlePlayFromNarration" in layout_source

    assert "func handlePlayFromNarration()" in linguist_source
    assert "subtitleBubble?.cachedAudioRef" in linguist_source
    assert "coordinator.seek(to: seekTime)" in linguist_source
    assert "coordinator.play()" in linguist_source
    assert "return Button(action:" in picker_ui_source
    assert ".focused($focusedControl, equals: control)" in picker_ui_source
    assert ".onTapGesture" not in picker_ui_source.split("func bubbleControlItem(", 1)[1].split("\n    }", 1)[0]


def test_tvos_lookup_read_aloud_configures_audio_session_and_starts_pronunciation() -> None:
    speaker_source = PRONUNCIATION_SPEAKER.read_text(encoding="utf-8")
    view_model_source = MY_LINGUIST_VIEW_MODEL.read_text(encoding="utf-8")

    assert "#if os(iOS) || os(tvOS)" in speaker_source
    assert "@MainActor\n    func speakFallback" in speaker_source
    assert "@MainActor\n    func stop()" in speaker_source
    assert "AVAudioSession.sharedInstance()" in speaker_source
    assert "setCategory(.playback, mode: .spokenAudio" in speaker_source
    assert "try? session.setActive(true)" in speaker_source

    start_lookup = view_model_source.split("func startLookup(", 1)[1].split("lookupTask = Task", 1)[0]
    assert "startPronunciation(text: query" in start_lookup
    assert "pronunciationBackendTimeoutNanos" in view_model_source
    assert "synthesizeAudioWithTimeout" in view_model_source
    assert "Task.sleep(nanoseconds: pronunciationBackendTimeoutNanos)" in view_model_source
    assert "pronunciationSpeaker.playAudio(data)" in view_model_source
    assert "pronunciationSpeaker.speakFallback(text, language: fallbackLanguage)" in view_model_source
