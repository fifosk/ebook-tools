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
INTERACTIVE_PLAYER_LINGUIST = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
    / "InteractivePlayerView+Linguist.swift"
)
SPEECH_LANGUAGE_RESOLVER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Utilities"
    / "SpeechLanguageResolver.swift"
)
PRONUNCIATION_SPEAKER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Utilities"
    / "PronunciationSpeaker.swift"
)
LINGUIST_TV_HEADER_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Shared"
    / "LinguistBubbleTVHeaderControls.swift"
)
LINGUIST_HEADER_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Shared"
    / "LinguistBubbleHeaderControls.swift"
)
PLAYER_CHANNEL_MODELS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Shared"
    / "PlayerChannelModels.swift"
)
INTERACTIVE_HEADER_OVERLAY = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
    / "InteractivePlayerView+HeaderOverlay.swift"
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
LINGUIST_BUBBLE_VIEW = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Shared"
    / "LinguistBubbleView.swift"
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
    tv_header_source = LINGUIST_TV_HEADER_CONTROLS.read_text(encoding="utf-8")
    header_controls_source = LINGUIST_HEADER_CONTROLS.read_text(encoding="utf-8")
    shared_bubble_source = LINGUIST_BUBBLE_VIEW.read_text(encoding="utf-8")

    assert "let onPlayFromNarration: (() -> Void)?" in compatibility_source
    assert "onPlayFromNarration: (() -> Void)? = nil" in compatibility_source
    assert "actions.onPlayFromNarration = onPlayFromNarration" in compatibility_source
    assert "let onReadAloud: (() -> Void)?" in compatibility_source
    assert "onReadAloud: (() -> Void)? = nil" in compatibility_source
    assert "actions.onReadAloud = onReadAloud" in compatibility_source

    assert "let onPlayFromNarration: (() -> Void)?" in overlay_source
    assert "onPlayFromNarration: onPlayFromNarration" in overlay_source
    assert "let onReadAloud: (() -> Void)?" in overlay_source
    assert "onReadAloud: onReadAloud" in overlay_source

    assert "onPlayFromNarration: handlePlayFromNarration" in layout_source
    assert "onReadAloud: handleReadSubtitleLookupAloud" in layout_source

    assert "func handlePlayFromNarration()" in linguist_source
    assert "func handleReadSubtitleLookupAloud()" in linguist_source
    assert "subtitleBubble?.cachedAudioRef" in linguist_source
    assert "linguistVM.readCurrentBubbleAloud" in linguist_source
    assert "coordinator.seek(to: seekTime)" in linguist_source
    assert "coordinator.play()" in linguist_source
    assert "var tvReadAloudButton: some View" in tv_header_source
    assert "actions.onReadAloud" in tv_header_source
    assert 'Image(systemName: "speaker.wave.2.circle.fill")' in tv_header_source
    assert '.accessibilityLabel("Read lookup aloud")' in tv_header_source
    assert 'Image(systemName: "slider.horizontal.3")' in header_controls_source
    assert '.accessibilityLabel("Pronunciation voice")' in header_controls_source
    assert "return Button(action:" in picker_ui_source
    assert ".focused($focusedControl, equals: control)" in picker_ui_source
    assert ".onTapGesture" not in picker_ui_source.split("func bubbleControlItem(", 1)[1].split("\n    }", 1)[0]
    assert "var visibleHeaderControls: [BubbleHeaderControl]" in shared_bubble_source
    assert "actions.onReadAloud != nil" in shared_bubble_source
    assert "controls.append(.readAloud)" in shared_bubble_source
    assert shared_bubble_source.index("controls.append(.readAloud)") < shared_bubble_source.index("controls.append(.voice)")
    assert ".onMoveCommand(perform: handleBubbleMoveCommand)" in shared_bubble_source
    assert "moveFocusedHeaderControl(by: 1)" in shared_bubble_source


def test_tvos_lookup_read_aloud_configures_audio_session_and_starts_pronunciation() -> None:
    speaker_source = PRONUNCIATION_SPEAKER.read_text(encoding="utf-8")
    view_model_source = MY_LINGUIST_VIEW_MODEL.read_text(encoding="utf-8")
    video_linguist_source = VIDEO_PLAYER_LINGUIST.read_text(encoding="utf-8")
    interactive_linguist_source = INTERACTIVE_PLAYER_LINGUIST.read_text(encoding="utf-8")
    resolver_source = SPEECH_LANGUAGE_RESOLVER.read_text(encoding="utf-8")

    assert "#if os(iOS) || os(tvOS)" in speaker_source
    assert "@MainActor\n    func speakFallback" in speaker_source
    assert "@MainActor\n    func stop()" in speaker_source
    assert "AVAudioSession.sharedInstance()" in speaker_source
    assert "try session.setCategory(.playback, mode: .spokenAudio" in speaker_source
    assert "catch" in speaker_source
    assert "try? session.setCategory(.playback, mode: .default, options: [])" in speaker_source
    assert "try? session.setActive(true)" in speaker_source
    assert "@discardableResult" in speaker_source
    assert "func playAudio(_ data: Data) -> Bool" in speaker_source
    assert "minimumAudibleDuration" in speaker_source
    assert "player.duration.isFinite" in speaker_source
    assert "player.duration >= Self.minimumAudibleDuration" in speaker_source
    assert "player.volume = 1.0" in speaker_source
    assert "let didStart = player.play()" in speaker_source
    assert "return false" in speaker_source

    assert 'case "turkish":' in resolver_source
    assert 'return "tr-TR"' in resolver_source
    assert "let pronunciationContext = makePronunciationContext(isTranslationTrack: isTranslationTrack)" in view_model_source
    assert "pronunciationLanguage: storedPronunciationLanguage" in view_model_source
    assert "pronunciationVoice: storedPronunciationVoice" in view_model_source
    assert 'let fallbackSpeechLanguage = resolvedPronLang ?? pronLang ?? "en-US"' in view_model_source
    assert "startPronunciation(\n            text: query" in view_model_source
    assert "fallbackLanguage: pronunciationContext.fallbackLanguage" in view_model_source
    assert "pronunciationBackendTimeoutNanos" in view_model_source
    assert "synthesizeAudioWithTimeout" in view_model_source
    assert "Task.sleep(nanoseconds: pronunciationBackendTimeoutNanos)" in view_model_source
    assert "let didStart = pronunciationSpeaker.playAudio(data)" in view_model_source
    assert "guard didStart else" in view_model_source
    assert "pronunciationSpeaker.speakFallback(text, language: fallbackLanguage)" in view_model_source
    assert "@MainActor\n    func stopPronunciation()" in view_model_source
    assert "func readCurrentBubbleAloud(isTranslationTrack: Bool)" in view_model_source
    assert "storedLanguage: bubble.pronunciationLanguage" in view_model_source
    assert "storedVoice: bubble.pronunciationVoice" in view_model_source
    assert "variantKind == .translation || variantKind == .transliteration" in interactive_linguist_source
    assert "lineKind == .translation || lineKind == .transliteration || lineKind == .unknown" in video_linguist_source

    video_read = video_linguist_source.split("func handleReadSubtitleLookupAloud()", 1)[1].split(
        "\n    }",
        1,
    )[0]
    assert "coordinator.pause()" in video_read
    assert "linguistVM.readCurrentBubbleAloud" in video_read

    video_play = video_linguist_source.split("func handlePlayFromNarration()", 1)[1].split(
        "\n    }",
        1,
    )[0]
    assert "linguistVM.stopPronunciation()" in video_play

    interactive_read = interactive_linguist_source.split("func handleReadLookupAloud()", 1)[1].split(
        "\n    }",
        1,
    )[0]
    assert "audioCoordinator.pause()" in interactive_read
    assert "linguistVM.readCurrentBubbleAloud" in interactive_read

    interactive_play = interactive_linguist_source.split("func handlePlayFromNarration()", 1)[1].split(
        "\n    }",
        1,
    )[0]
    assert "linguistVM.stopPronunciation()" in interactive_play


def test_interactive_reader_header_uses_shared_apple_chrome() -> None:
    channel_models_source = PLAYER_CHANNEL_MODELS.read_text(encoding="utf-8")
    header_overlay_source = INTERACTIVE_HEADER_OVERLAY.read_text(encoding="utf-8")
    header_pills_source = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "InteractivePlayer"
        / "InteractivePlayerView+HeaderPills.swift"
    ).read_text(encoding="utf-8")

    assert "struct PlayerHeaderGlassPanelBackground: View" in channel_models_source
    assert "struct PlayerHeaderIdentityBannerBackground: View" in channel_models_source
    assert "struct PlayerHeaderPillBackground: View" in channel_models_source
    assert ".fill(.ultraThinMaterial)" in channel_models_source
    assert "PlayerHeaderGlassPanelBackground(cornerRadius: headerGlassCornerRadius)" in header_overlay_source
    assert "PlayerHeaderIdentityBannerBackground(cornerRadius: cornerRadius)" in header_overlay_source
    assert "private struct InteractivePlayerHeaderIdentityBanner: View" in header_overlay_source
    assert "let controls: AnyView" in header_overlay_source
    assert "self.controls = AnyView(controls())" in header_overlay_source
    assert "InteractivePlayerHeaderIdentityBanner(" in header_overlay_source
    assert "let usesBannerProgress = showHeaderContent && headerInfo != nil" in header_overlay_source
    assert "private func headerRowContent(" in header_overlay_source
    assert "private var bannerContent: some View" in header_overlay_source
    assert "private var headerProgressPills: some View" in header_overlay_source
    assert "private func headerProgressPill(label: String, isProminent: Bool)" in header_overlay_source
    assert "slideLabel: slideLabel" in header_overlay_source
    assert "timelineLabel: timelineLabel" in header_overlay_source
    assert "onTimelineTap: handleAudioTimelineTap" in header_overlay_source
    assert ".onTapGesture(perform: onTimelineTap)" in header_overlay_source
    assert "if isPad { return .infinity }" in header_overlay_source
    assert "if isPhonePortrait {" in header_overlay_source
    assert "private var horizontalBannerContent: some View" in header_overlay_source
    assert "private var compactBannerContent: some View" in header_overlay_source
    assert "private var titleSubtitleStack: some View" in header_overlay_source
    assert "ViewThatFits(in: .horizontal)" not in header_overlay_source
    assert "ScrollView(.horizontal, showsIndicators: false)" in header_overlay_source
    assert 'accessibilityIdentifier("interactiveReaderHeaderIdentityBanner")' in header_overlay_source
    assert 'accessibilityIdentifier("interactiveReaderHeaderCover")' in header_overlay_source
    assert "headerCoverArtworkView(info: info)" in header_overlay_source
    assert "private func headerCoverPlaceholder(info: InteractivePlayerHeaderInfo)" in header_overlay_source
    assert "private func headerMetadataPillRow(info: InteractivePlayerHeaderInfo)" in header_overlay_source
    assert "private func headerMetadataPills(itemType: String, translationModel: String?)" in header_overlay_source
    assert "headerIdentitySubtitle(for: info)" in header_overlay_source
    assert "headerMetadataPill(" in header_overlay_source
    assert "itemTypeSystemImage(for: itemType)" in header_overlay_source
    assert "PlayerCoverStackView(" in header_overlay_source
    assert "PlayerHeaderPillBackground(isActive: true, isProminent: true)" in header_overlay_source
    assert "PlayerHeaderPillBackground(isActive: isNonDefault)" in header_pills_source
