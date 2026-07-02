from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SYNC_DOC = ROOT / "docs" / "frontend-sync.md"
PARITY_PLAN_DOC = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"
MAKEFILE = ROOT / "Makefile"
XCODE_PROJECT = ROOT / "ios" / "InteractiveReader" / "InteractiveReader.xcodeproj" / "project.pbxproj"
AUDIO_MODE_CHECK = ROOT / "scripts" / "check_apple_audio_mode_manager.sh"
AUDIO_MODE_SWIFT_CHECK = ROOT / "scripts" / "tests" / "check_audio_mode_manager.swift"
SENTENCE_PROVIDER_CHECK = ROOT / "scripts" / "check_apple_sentence_position_provider.sh"
SENTENCE_PROVIDER_SWIFT_CHECK = ROOT / "scripts" / "tests" / "check_sentence_position_provider.swift"
MODE_SWITCH_CHECK = ROOT / "scripts" / "check_apple_playback_mode_switch_integration.sh"
MODE_SWITCH_SWIFT_CHECK = ROOT / "scripts" / "tests" / "check_playback_mode_switch_integration.swift"
SEQUENCE_PAUSE_CHECK = ROOT / "scripts" / "check_apple_sequence_pause_cancel.sh"
SEQUENCE_PAUSE_SWIFT_CHECK = ROOT / "scripts" / "tests" / "check_sequence_pause_cancel.swift"
TRANSCRIPT_SNAPSHOT_CHECK = ROOT / "scripts" / "check_apple_transcript_display_snapshots.sh"
TRANSCRIPT_SNAPSHOT_SWIFT_CHECK = ROOT / "scripts" / "tests" / "check_transcript_display_snapshots.swift"
SENTENCE_JUMP_LOCK_CHECK = ROOT / "scripts" / "check_apple_sentence_jump_render_lock.sh"
SENTENCE_JUMP_LOCK_SWIFT_CHECK = ROOT / "scripts" / "tests" / "check_sentence_jump_render_lock.swift"
INTERACTIVE_CONTEXT_BUILDER_CHECK = ROOT / "scripts" / "check_apple_interactive_context_builder.sh"
INTERACTIVE_CONTEXT_BUILDER_SWIFT_CHECK = ROOT / "scripts" / "tests" / "check_interactive_context_builder.swift"
INTERACTIVE = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
)


def _source(name: str) -> str:
    return (INTERACTIVE / name).read_text(encoding="utf-8")


def _function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : index]
    raise AssertionError(f"Could not find body for {signature}")


def _brace_object_body(source: str, start: int) -> str:
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : index]
    raise AssertionError("Could not find pbx object body")


def _pbx_object_body(source: str, object_id: str) -> str:
    pattern = re.compile(rf"\n\t\t'?{re.escape(object_id)}'?(?: /\* [^*]+ \*/)? = \{{")
    match = pattern.search(source)
    if match is None:
        raise AssertionError(f"Could not find pbx object {object_id}")
    return _brace_object_body(source, match.start())


def _pbx_native_target_body(source: str, target_name: str) -> str:
    for match in re.finditer(r"\n\t\t(?:'?[A-Z0-9]+'?(?: /\* [^*]+ \*/)?) = \{", source):
        body = _brace_object_body(source, match.start())
        if "isa = PBXNativeTarget;" in body and f"name = {target_name};" in body:
            return body
    raise AssertionError(f"Could not find PBXNativeTarget {target_name}")


def _pbx_source_phase_body_for_target(source: str, target_name: str) -> str:
    target_body = _pbx_native_target_body(source, target_name)
    build_phases_match = re.search(r"buildPhases = \((.*?)\);", target_body, flags=re.S)
    assert build_phases_match is not None
    build_phase_ids = []
    for line in build_phases_match.group(1).splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        build_phase_ids.append(stripped.split()[0].strip("',"))

    for build_phase_id in build_phase_ids:
        build_phase_body = _pbx_object_body(source, build_phase_id)
        if "isa = PBXSourcesBuildPhase;" in build_phase_body:
            return build_phase_body
    raise AssertionError(f"Could not find sources build phase for {target_name}")


def test_sentence_position_provider_swift_check_is_wired_into_apple_contracts() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    check_script = SENTENCE_PROVIDER_CHECK.read_text(encoding="utf-8")
    swift_check = SENTENCE_PROVIDER_SWIFT_CHECK.read_text(encoding="utf-8")

    assert "test-apple-playback-state-swift:" in makefile
    assert "bash scripts/check_apple_sentence_position_provider.sh" in makefile
    assert str(SENTENCE_PROVIDER_SWIFT_CHECK.relative_to(ROOT)) in check_script
    assert "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/SentencePositionProvider.swift" in check_script
    assert "SequencePlaybackController" in swift_check
    assert "strategy: .sequenceController" in swift_check
    assert "strategy: .transcriptDisplay" in swift_check
    assert "strategy: .timeBased" in swift_check
    assert "Provider should return nil when every strategy is unavailable" in swift_check


def test_audio_mode_manager_swift_check_is_wired_into_apple_contracts() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    check_script = AUDIO_MODE_CHECK.read_text(encoding="utf-8")
    swift_check = AUDIO_MODE_SWIFT_CHECK.read_text(encoding="utf-8")

    assert "test-apple-playback-state-swift:" in makefile
    assert "bash scripts/check_apple_audio_mode_manager.sh" in makefile
    assert str(AUDIO_MODE_SWIFT_CHECK.relative_to(ROOT)) in check_script
    assert "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/AudioModeManager.swift" in check_script
    assert "manager.toggle(.original, preservingPosition: 4)" in swift_check
    assert "manager.setTracks(original: false, translation: false, preservingPosition: 6)" in swift_check
    assert "manager.toggle(kind: .combined, preservingPosition: 9)" in swift_check
    assert "resolveAudioInstruction(for: chunk, selectedTrackID: \"combined\")" in swift_check
    assert "resolveTimingTrack(" in swift_check


def test_shared_playback_mode_sources_are_compiled_into_ios_and_tvos_targets() -> None:
    project = XCODE_PROJECT.read_text(encoding="utf-8")

    for target_name in ("InteractiveReader", "InteractiveReaderTV"):
        sources = _pbx_source_phase_body_for_target(project, target_name)
        assert "AudioModeManager.swift in Sources" in sources
        assert "InteractivePlayerView+Tracks.swift in Sources" in sources


def test_mode_switch_integration_check_is_wired_into_apple_contracts() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    check_script = MODE_SWITCH_CHECK.read_text(encoding="utf-8")
    swift_check = MODE_SWITCH_SWIFT_CHECK.read_text(encoding="utf-8")

    assert "test-apple-playback-state-swift:" in makefile
    assert "bash scripts/check_apple_playback_mode_switch_integration.sh" in makefile
    assert str(MODE_SWITCH_SWIFT_CHECK.relative_to(ROOT)) in check_script
    assert "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/AudioModeManager.swift" in check_script
    assert "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/SentencePositionProvider.swift" in check_script
    assert "manager.toggle(.original, preservingPosition: sequenceProvider.index)" in swift_check
    assert "manager.toggle(.translation, preservingPosition: transcriptProvider.index)" in swift_check
    assert "SentencePositionProvider.targetSentenceIndex(" in swift_check
    assert "manager.toggle(kind: .combined, preservingPosition: timeProvider.index)" in swift_check
    assert "Sequence-controller position should be preserved" in swift_check
    assert "private func usesCombinedQueue(" in swift_check
    assert "if let audioModeManager, !audioModeManager.isSequenceMode" in swift_check
    assert "Translation-only mode should not add combined queue offsets" in swift_check
    assert "Original-only mode should not add combined queue offsets" in swift_check
    assert "Sequence mode should keep combined queue timing enabled" in swift_check
    assert "singleTrackNavigationTarget(" in swift_check
    assert "Translation-only next sentence at a chunk boundary should advance to the next displayed batch, not skip a batch" in swift_check
    assert "Translation-only previous sentence at a chunk boundary should return to the previous displayed batch" in swift_check
    assert "Translation-only anchored next sentence should use visible sentence numbers on the active track" in swift_check
    assert "Translation-only slider anchor should beat stale end-of-chunk time so next moves one sentence, not one batch" in swift_check
    assert "prepareResumeSingleTrack(" in swift_check
    assert "applyPendingResumeSingleTrackIfNeeded(" in swift_check
    assert "Translation-only resume should restore single-track mode before seeking" in swift_check
    assert "View restore should keep translation-only visible instead of defaulting back to all tracks" in swift_check
    assert "preserveSingleTrackModeIfNeeded(" in swift_check
    assert "Cross-batch setup should preserve an existing translation-only audio mode instead of defaulting to all tracks" in swift_check
    assert "Cross-batch setup should keep the transcript aligned to the translation-only audio track" in swift_check
    assert "Unloaded next-batch setup should preserve translation-only mode when text tracks temporarily fall back to original" in swift_check
    assert "synchronizeSelectedAudioTrackWithCurrentMode(" in swift_check
    assert "Chunk handoff should switch the selected audio option before immediate playback can load the next batch" in swift_check
    assert "Chunk handoff should record translation-only as the durable lane before batch autoplay starts" in swift_check
    assert "Combined-only chunk handoff should extract the translation stream before rendering follows the wrong track" in swift_check
    assert "Combined-only chunk handoff should keep a durable translation-only lane even when the selected option remains combined" in swift_check
    assert "PlaybackEndedURLPolicy.endedURL(" in swift_check
    assert "Combined-only translation playback should reject hidden original EOF callbacks" in swift_check
    assert "Combined-only translation playback should accept translation EOF callbacks" in swift_check
    assert "Combined-only original playback should accept original EOF callbacks" in swift_check
    assert "Active translation-only URL should reject stale hidden original EOF before the next batch can reset to combined" in swift_check
    assert "Active translation-only URL should accept its own EOF for batch handoff" in swift_check
    assert "Single-track EOF handoff should preserve translation from the active URL when the ended callback lost its URL" in swift_check
    assert "Missing EOF URL should not guess a lane from a multi-file active queue" in swift_check
    assert "Prepare audio should reapply translation-only selection before resolving a stale batch option" in swift_check
    assert "Loaded translation-only lane should beat stale preferred state at batch EOF" in swift_check
    assert "requestedSingleTrackMode(" in swift_check
    assert "End-of-batch handoff should preserve translation-only selection even if the view manager bridge is unavailable" in swift_check
    assert "Bridgeless end-of-batch handoff should select translation audio instead of falling back to combined" in swift_check
    assert "Single-track sequence-controller mode should stop stale combined selections from rendering as sequence after a batch handoff" in swift_check
    assert "rememberSingleTrackBatchStartAnchorIfNeeded(" in swift_check
    assert "Natural translation-only batch advance should anchor the placeholder batch start before audio autoplay can reset rendering" in swift_check
    assert "Targeted translation-only batch selection should derive a visible sentence anchor from placeholder range metadata" in swift_check
    assert "Translation-only resume anchor should be consumed after live playback reaches the target sentence" in swift_check
    assert "Consumed translation-only resume anchor must not pull the first post-resume sentence back out of sync" in swift_check
    assert "shouldPrefetchSequenceAudio(" in swift_check
    assert "Remembered translation-only lane should stop next-batch prefetch from warming sequence audio after manager reset" in swift_check
    assert "preferredPrefetchAudioOption(" in swift_check
    assert "Remembered translation-only lane should make next-batch prefetch choose translation audio" in swift_check
    assert "prefetchAudioURL(" in swift_check
    assert "Combined-only translation prefetch should warm the translation stream instead of the hidden original stream" in swift_check
    assert "allowExpandingSingleTrackAudio" in swift_check
    assert "Passive hydrated-batch sync should not expand a remembered translation-only lane back to combined" in swift_check
    assert "Translation-only render anchors must not release on a hidden original stream from the selected combined option" in swift_check
    assert "Translation-only render anchors must reject a stale dedicated original option after the batch selection refreshes" in swift_check
    assert "Translation-only render anchors should still accept the translation stream after the selected option refreshes to original" in swift_check
    assert "Explicit text-track toggle should still be able to expand translation-only playback to combined" in swift_check
    frontend_sync = FRONTEND_SYNC_DOC.read_text(encoding="utf-8")
    assert "Once live\n  playback reaches the anchored sentence, the anchor must be consumed/cleared" in frontend_sync
    assert "first following translated sentence is rendered from live audio time" in frontend_sync
    assert "chunk/batch setup must preserve that single-track mode" in frontend_sync
    assert "based on playable audio options too, not only currently hydrated visible text\n  tracks" in frontend_sync
    assert "Passive hydrated-batch text/audio sync must not expand a remembered single-track lane" in frontend_sync
    assert "Natural end-of-batch single-track advances should\n  establish a fresh next-batch anchor" in frontend_sync
    assert "reapply the active single-track audio option before\n  selecting the next chunk" in frontend_sync
    assert "pass an explicit sentence-0 target" in frontend_sync
    sequence_source = (INTERACTIVE / "InteractivePlayerViewModel+Sequence.swift").read_text(encoding="utf-8")
    sequence_active_body = sequence_source.split("var isSequenceModeActive: Bool", 1)[1].split("\n}", 1)[0]
    assert "guard audioModeManager?.isSequenceMode != false else" in sequence_active_body


def test_single_track_batch_end_ignores_stale_audio_item_callbacks() -> None:
    audio_coordinator = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Services"
        / "AudioPlayerCoordinator.swift"
    ).read_text(encoding="utf-8")
    view_model = _source("InteractivePlayerViewModel.swift")
    selection = _source("InteractivePlayerViewModel+Selection.swift")
    audio_mode_manager = _source("AudioModeManager.swift")

    assert "var onPlaybackEndedWithURL: ((URL?) -> Void)?" in audio_coordinator
    end_observer_body = _function_body(audio_coordinator, "private func installEndObserver(for player: AVPlayer)")
    assert "let endedURL = self.itemURLMap[identifier]" in end_observer_body
    assert "if let handler = self.onPlaybackEndedWithURL" in end_observer_body
    assert "handler(endedURL)" in end_observer_body
    assert "self.onPlaybackEnded?()" in end_observer_body

    assert "audioCoordinator.onPlaybackEndedWithURL = { [weak self] endedURL in" in view_model
    assert "self?.handlePlaybackEnded(endedURL: endedURL)" in view_model

    ended_body = _function_body(selection, "func handlePlaybackEnded(endedURL: URL? = nil)")
    assert "playbackEndedURLBelongsToCurrentChunk(endedURL, chunk: chunk)" in ended_body
    assert "Ignoring stale playback-ended callback" in ended_body
    assert ended_body.index("playbackEndedURLBelongsToCurrentChunk(endedURL, chunk: chunk)") < ended_body.index(
        "let preservedSingleTrack = singleTrackModeForCompletedPlayback("
    )
    assert "selectChunkPreservingAudioLane(" in ended_body

    belongs_body = _function_body(
        selection,
        "private func playbackEndedURLBelongsToCurrentChunk(\n        _ endedURL: URL,\n        chunk: InteractiveChunk\n    ) -> Bool",
    )
    assert "if requestedSingleTrackMode() != nil" in belongs_body
    assert "return audioURLBelongsToSelectedLane(endedURL, in: chunk)" in belongs_body
    assert "if let selectedOption = selectedAudioOption(for: chunk)" in belongs_body
    assert "let activeSingleTrack = singleTrackModeForCompletedPlayback(" in belongs_body
    assert "endedURL: nil" in belongs_body
    assert "PlaybackEndedURLPolicy.endedURL(" in belongs_body
    assert "belongsTo: selectedOption" in belongs_body
    assert "singleTrack: activeSingleTrack ?? requestedSingleTrackMode()" in belongs_body
    assert "return chunk.audioOptions.contains" in belongs_body

    lane_body = _function_body(selection, "func audioURLBelongsToSelectedLane(_ url: URL, in chunk: InteractiveChunk) -> Bool")
    assert "guard selectedChunkID == chunk.id else { return false }" in lane_body
    assert "if let selectedSingleTrack = requestedSingleTrackMode()" in lane_body
    assert "kind == .translation && $0.streamURLs.contains(url)" in lane_body
    assert "PlaybackEndedURLPolicy.endedURL(" in lane_body

    policy_body = _function_body(audio_mode_manager, "enum PlaybackEndedURLPolicy")
    assert "static func endedURL(" in policy_body
    assert "guard option.kind == .combined, let singleTrack else" in policy_body
    assert "return option.streamURLs.contains(endedURL)" in policy_body
    assert "belongsToSingleTrack track: SequenceTrack" in policy_body
    assert "case .original:" in policy_body
    assert "return streamURLs.first == endedURL" in policy_body
    assert "case .translation:" in policy_body
    assert "return streamURLs.dropFirst().contains(endedURL)" in policy_body


def test_sequence_pause_cancel_swift_check_is_wired_into_apple_contracts() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    check_script = SEQUENCE_PAUSE_CHECK.read_text(encoding="utf-8")
    swift_check = SEQUENCE_PAUSE_SWIFT_CHECK.read_text(encoding="utf-8")

    assert "test-apple-playback-state-swift:" in makefile
    assert "bash scripts/check_apple_sequence_pause_cancel.sh" in makefile
    assert makefile.count("bash scripts/check_apple_sequence_pause_cancel.sh") >= 2
    assert str(SEQUENCE_PAUSE_SWIFT_CHECK.relative_to(ROOT)) in check_script
    assert "ios/InteractiveReader/InteractiveReader/Services/SequencePlaybackController.swift" in check_script
    assert "controller.boundaryReached()" in swift_check
    assert "controller.cancelPendingAutomaticAdvanceForPause()" in swift_check
    assert "Cancelled dwell should not advance after its timer fires" in swift_check
    assert "Pause cancellation should clear an in-flight transition" in swift_check
    assert "runSingleTrackPlanInitialLaneCheck()" in swift_check
    assert "Translation-only plan should point at the first translation segment" in swift_check


def test_transcript_display_snapshot_check_is_wired_into_apple_contracts() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    check_script = TRANSCRIPT_SNAPSHOT_CHECK.read_text(encoding="utf-8")
    swift_check = TRANSCRIPT_SNAPSHOT_SWIFT_CHECK.read_text(encoding="utf-8")

    assert "test-apple-playback-state-swift:" in makefile
    assert "bash scripts/check_apple_transcript_display_snapshots.sh" in makefile
    assert str(TRANSCRIPT_SNAPSHOT_SWIFT_CHECK.relative_to(ROOT)) in check_script
    assert "TextPlayerTimeline+DisplayBuilders.swift" in check_script
    assert "TextPlayerTimeline+Helpers.swift" in check_script
    assert "TextPlayerTimeline.buildStaticDisplay" in swift_check
    assert "TextPlayerTimeline.buildInitialDisplay" in swift_check
    assert "TextPlayerTimeline.buildTrackSwitchDisplay" in swift_check
    assert "TextPlayerTimeline.buildDwellDisplay" in swift_check
    assert "TextPlayerTimeline.buildSettlingDisplay" in swift_check
    assert "translationStartOnlyGateSentences" in swift_check
    assert "Start-only translation gates should still resolve active rendering in audio time" in swift_check
    assert "Translation-only rendering should stay on the sought sentence when jobs provide start gates without end gates" in swift_check
    assert "stretchedTranslationSentences" in swift_check
    assert "Translation-only word highlighting should use the timeline runtime" in swift_check
    active_display = _source("TextPlayerTimeline+ActiveDisplay.swift")
    active_sentence_body = _function_body(
        active_display,
        "static func buildActiveSentenceDisplay(\n        sentences: [InteractiveChunk.Sentence],\n        activeTimingTrack: TextPlayerTimingTrack,\n        chunkTime: Double,\n        audioDuration: Double?,\n        useCombinedPhases: Bool\n    ) -> TextPlayerSentenceDisplay?",
    )
    assert "buildTimelineSentences(" in active_sentence_body
    assert "buildActiveSentenceDisplay(\n               timelineSentences: timelineSentences" in active_sentence_body
    assert "Empty static display should remain empty" in swift_check


def test_sentence_jump_render_lock_check_is_wired_into_apple_contracts() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    check_script = SENTENCE_JUMP_LOCK_CHECK.read_text(encoding="utf-8")
    swift_check = SENTENCE_JUMP_LOCK_SWIFT_CHECK.read_text(encoding="utf-8")
    helper_source = _source("InteractiveSentenceJumpRenderLock.swift")
    transcript_source = _source("InteractivePlayerView+Transcript.swift")
    project = XCODE_PROJECT.read_text(encoding="utf-8")

    assert "test-apple-playback-state-swift:" in makefile
    assert "bash scripts/check_apple_sentence_jump_render_lock.sh" in makefile
    assert makefile.count("bash scripts/check_apple_sentence_jump_render_lock.sh") >= 2
    assert str(SENTENCE_JUMP_LOCK_SWIFT_CHECK.relative_to(ROOT)) in check_script
    assert "InteractiveSentenceJumpRenderLock.swift" in check_script
    assert "SentencePositionProvider.swift" in check_script
    assert "Stale audio from another chunk must not unlock a translation-only slider jump" in swift_check
    assert "The next visible sentence window must not unlock the previous slider target" in swift_check
    assert "pendingChunkID == chunk.id" in helper_source
    assert "currentChunkAudioIsActive" in helper_source
    assert "SentencePositionProvider.sentenceIndex" in helper_source
    assert "SentencePositionProvider.sentenceNumber" in helper_source
    assert "InteractiveSentenceJumpRenderLock.reachedLivePlayback" in transcript_source
    for target_name in ("InteractiveReader", "InteractiveReaderTV"):
        sources = _pbx_source_phase_body_for_target(project, target_name)
        assert "InteractiveSentenceJumpRenderLock.swift in Sources" in sources


def test_active_sentence_resolution_honors_partial_sentence_gates() -> None:
    helpers = _source("TextPlayerTimeline+Helpers.swift")
    body = _function_body(
        helpers,
        "static func resolveActiveSentenceResolution(\n        sentences: [InteractiveChunk.Sentence],\n        activeTimingTrack: TextPlayerTimingTrack,\n        chunkTime: Double,\n        audioDuration: Double?,\n        useCombinedPhases: Bool\n    ) -> ActiveSentenceResolution?",
    )

    assert "sentences.contains" in body
    assert "hasAnyAbsoluteOriginalTiming" in body
    assert "hasAnyAbsoluteTranslationTiming" in body
    assert "sentences.allSatisfy" not in body
    assert "let useAbsoluteOriginalTiming = isOriginalTrack" in body
    assert "let useAbsoluteTranslationTiming = !isOriginalTrack" in body
    assert "offset = endTime" in body


def test_interactive_context_builder_check_is_wired_into_apple_contracts() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    check_script = INTERACTIVE_CONTEXT_BUILDER_CHECK.read_text(encoding="utf-8")
    swift_check = INTERACTIVE_CONTEXT_BUILDER_SWIFT_CHECK.read_text(encoding="utf-8")

    assert "test-apple-playback-state-swift:" in makefile
    assert "bash scripts/check_apple_interactive_context_builder.sh" in makefile
    assert str(INTERACTIVE_CONTEXT_BUILDER_SWIFT_CHECK.relative_to(ROOT)) in check_script
    assert "InteractivePlayerContextBuilder.swift" in check_script
    assert "PipelineMediaApiModels.swift" in check_script
    assert "TextPlayerTimeline+ActiveDisplay.swift" in check_script
    assert "\"startSentence\": 2180" in swift_check
    assert "{\"sentenceIdx\": 0" in swift_check
    assert "{\"sentenceIdx\": 1" in swift_check
    assert "First global sentence should bind chunk-local translation tokens" in swift_check
    assert "Second timeline row should preserve display sentence" in swift_check
    assert "decodeOutOfOrderChunksFixture" in swift_check
    assert "\"chunk_2210\", \"chunk_2220\", \"chunk_2230\"" in swift_check
    assert "Next chunk after sentence 2219 should be the 2220 batch" in swift_check
    assert "Previous chunk before 2230 should be the 2220 batch" in swift_check


def test_audio_mode_manager_owns_toggle_state_and_preserves_position() -> None:
    source = _source("AudioModeManager.swift")
    tracks = _source("InteractivePlayerView+Tracks.swift")
    audio_management = _source("InteractivePlayerView+AudioManagement.swift")

    assert "@MainActor\nfinal class AudioModeManager: ObservableObject" in source
    assert "@Published private(set) var isOriginalEnabled: Bool" in source
    assert "@Published private(set) var isTranslationEnabled: Bool" in source
    assert "@Published private(set) var currentMode: AudioMode" in source
    assert "var onModeChange: ((AudioMode, Int?) -> Void)?" in source

    init_body = _function_body(source, "init()")
    assert "self.isOriginalEnabled = true" in init_body
    assert "self.isTranslationEnabled = true" in init_body
    assert "self.currentMode = .sequence" in init_body

    normalized_body = _function_body(
        source,
        "private static func normalizedTrackState(original: Bool, translation: Bool) -> (original: Bool, translation: Bool)",
    )
    assert "guard original || translation else { return (true, true) }" in normalized_body

    apply_body = _function_body(
        source,
        "private func applyTrackState(\n        original: Bool,\n        translation: Bool,\n        preservingPosition currentSentenceIndex: Int?,\n        reason: String\n    )",
    )
    assert "let normalized = Self.normalizedTrackState" in apply_body
    assert "let newMode = Self.computeMode" in apply_body
    assert "currentMode = newMode" in apply_body
    assert "onModeChange?(newMode, currentSentenceIndex)" in apply_body
    assert apply_body.index("if normalized.original && !isOriginalEnabled") < apply_body.index(
        "if !normalized.original && isOriginalEnabled"
    )

    toggle_body = _function_body(source, "func toggle(_ track: SequenceTrack, preservingPosition currentSentenceIndex: Int? = nil)")
    assert "if nextOriginal && !nextTranslation" in toggle_body
    assert "if nextTranslation && !nextOriginal" in toggle_body
    assert "preservingPosition: currentSentenceIndex" in toggle_body

    assert "let currentSentenceIndex = captureCurrentSentenceIndex(for: chunk)" in tracks
    assert "audioModeManager.toggle(kind: kind, preservingPosition: currentSentenceIndex)" in tracks
    assert "reconfigureAudioForCurrentToggles(preservingSentence: currentSentenceIndex)" in tracks

    assert "let currentSentenceIndex = captureCurrentSentenceIndex(for: chunk)" in audio_management
    header_toggle_body = _function_body(
        audio_management,
        "func toggleHeaderAudioRole(\n        _ role: LanguageFlagRole,\n        for chunk: InteractiveChunk,\n        availableRoles: Set<LanguageFlagRole>\n    )",
    )
    assert "let activeRoles = activeAudioRoles(for: chunk, availableRoles: availableRoles)" in header_toggle_body
    assert "let shouldSelectRoleOnly = activeRoles != [role]" in header_toggle_body
    assert "audioModeManager.setTracks(" in header_toggle_body
    assert "audioModeManager.toggle(" not in header_toggle_body


def test_audio_mode_manager_resolves_tracks_and_timing_from_current_mode() -> None:
    source = _source("AudioModeManager.swift")
    selection = _source("InteractivePlayerViewModel+Selection.swift")
    playback = _source("InteractivePlayerViewModel+Playback.swift")

    assert "enum ResolvedAudioInstruction: CustomStringConvertible" in source
    assert "case sequence(combinedOption: InteractiveChunk.AudioOption)" in source
    assert "case singleOption(option: InteractiveChunk.AudioOption, timingTrack: TextPlayerTimingTrack)" in source
    assert "case singleURL(url: URL, timingTrack: TextPlayerTimingTrack)" in source

    instruction_body = _function_body(
        source,
        "func resolveAudioInstruction(\n        for chunk: InteractiveChunk,\n        selectedTrackID: String?\n    ) -> ResolvedAudioInstruction?",
    )
    assert "case .sequence:" in instruction_body
    assert "track.kind == .combined" in instruction_body
    assert "return .sequence(combinedOption: track)" in instruction_body
    assert "chunk.audioOptions.first(where: { $0.kind == .combined })" in instruction_body
    assert "return .sequence(combinedOption: combinedOption)" in instruction_body
    assert "case .singleTrack(let enabledTrack):" in instruction_body
    assert "return resolveSingleFromCombined" in instruction_body
    assert "track.kind == audioOptionKind(for: enabledTrack)" in instruction_body
    assert "if let matchingOption = option(for: enabledTrack, in: chunk)" in instruction_body
    assert "timingTrackForSequenceTrack(enabledTrack)" in instruction_body

    preferred_body = _function_body(source, "func resolvePreferredTrackID(for chunk: InteractiveChunk) -> String?")
    assert re.search(r"case \.sequence:\s+return \(combinedOption \?\? originalOption \?\? translationOption\)\?\.id", preferred_body)
    assert re.search(r"case \.singleTrack\(\.original\):\s+return \(originalOption \?\? combinedOption \?\? translationOption\)\?\.id", preferred_body)
    assert re.search(r"case \.singleTrack\(\.translation\):\s+return \(translationOption \?\? combinedOption \?\? originalOption\)\?\.id", preferred_body)

    timing_body = _function_body(
        source,
        "func resolveTimingTrack(\n        for chunk: InteractiveChunk,\n        selectedTrackID: String?,\n        sequenceTrack: SequenceTrack,\n        sequenceEnabled: Bool,\n        activeURL: URL?\n    ) -> TextPlayerTimingTrack",
    )
    assert "if sequenceEnabled" in timing_body
    assert "if case .singleTrack(let enabledTrack) = currentMode" in timing_body
    assert (
        timing_body.index("if case .singleTrack(let enabledTrack) = currentMode")
        < timing_body.index("if sequenceEnabled")
    )
    single_track_body = timing_body[
        timing_body.index("if case .singleTrack(let enabledTrack) = currentMode"):
        timing_body.index("// Both toggles enabled")
    ]
    assert "matchURLToTimingTrack" not in single_track_body
    assert "case .original: return .original" in single_track_body
    assert "case .translation: return .translation" in single_track_body
    assert "return track.streamURLs.count == 1 ? .mix : .original" in timing_body

    assert "mgr.resolveAudioInstruction(for: chunk, selectedTrackID: selectedAudioTrackID)" in selection
    assert "prepareSequenceAudio(for: chunk, autoPlay: autoPlay, targetSentenceIndex: targetSentenceIndex)" in selection
    assert "prepareSingleTrackAudio(\n                instruction" in selection
    assert "private func prepareSequenceAudio(" in selection
    assert "private func prepareSingleTrackAudio(" in selection
    assert "reassertSingleTrackPlaybackLane(for: chunk)" in selection
    assert "resolvedSequenceTargetIndex(for: chunk, targetSentenceIndex: targetSentenceIndex)" in selection
    combined_queue_body = _function_body(playback, "func usesCombinedQueue(for chunk: InteractiveChunk) -> Bool")
    assert "if isSequenceModeActive" in combined_queue_body
    assert "if requestedSingleTrackMode() != nil" in combined_queue_body
    assert "return false" in combined_queue_body
    assert "track.kind == .combined && track.streamURLs.count > 1" in combined_queue_body
    active_timing_body = _function_body(playback, "func activeTimingTrack(for chunk: InteractiveChunk) -> TextPlayerTimingTrack")
    assert "if let track = requestedSingleTrackMode()" in active_timing_body
    assert active_timing_body.index("if let track = requestedSingleTrackMode()") < active_timing_body.index(
        "if let mgr = audioModeManager"
    )
    selected_option_body = _function_body(playback, "func selectedAudioOption(for chunk: InteractiveChunk) -> InteractiveChunk.AudioOption?")
    assert "if let track = requestedSingleTrackMode()" in selected_option_body
    assert "chunk.audioOptions.first(where: { $0.kind == kind })" in selected_option_body
    assert "?? chunk.audioOptions.first(where: { $0.kind == .combined })" in selected_option_body
    prefetch = _source("InteractivePlayerViewModel+Prefetch.swift")
    prefetch_chunk_body = _function_body(prefetch, "private func prefetchChunkMediaIfNeeded(for chunk: InteractiveChunk)")
    assert "let isSequence = requestedSingleTrackMode() == nil" in prefetch_chunk_body
    prefetch_url_body = _function_body(prefetch, "private func prefetchURL(for option: InteractiveChunk.AudioOption) -> URL?")
    assert "let requestedTrack = requestedSingleTrackMode()" in prefetch_url_body
    assert "return option.streamURLs[1]" in prefetch_url_body
    preferred_prefetch_body = _function_body(prefetch, "private func preferredAudioOption(for chunk: InteractiveChunk) -> InteractiveChunk.AudioOption?")
    assert "if let selected = selectedAudioOption(for: chunk)" in preferred_prefetch_body
    assert "mgr.currentMode.description" in selection
    sync_body = _function_body(selection, "func synchronizeSelectedAudioTrackWithCurrentMode(for chunk: InteractiveChunk)")
    assert "if case .singleTrack(let track) = audioModeManager.currentMode" in sync_body
    assert "preferredSingleTrackMode = track" in sync_body
    assert "if let mgr = audioModeManager" in playback
    assert "return mgr.resolveTimingTrack(" in playback

    transcript_ready_body = _function_body(
        selection,
        "private func selectedTrackRequiresGates(for chunk: InteractiveChunk) -> Bool",
    )
    assert "if let audioModeManager, !audioModeManager.isSequenceMode" in transcript_ready_body
    assert "return false" in transcript_ready_body


def test_sentence_position_provider_priority_and_player_integration() -> None:
    provider = _source("SentencePositionProvider.swift")
    tracks = _source("InteractivePlayerView+Tracks.swift")
    audio_management = _source("InteractivePlayerView+AudioManagement.swift")

    assert "@MainActor\nstruct SentencePositionProvider" in provider
    assert "let sequenceController: SequencePlaybackController" in provider
    assert "let transcriptDisplayIndex: () -> Int?" in provider
    assert "let timeBasedIndex: () -> Int?" in provider
    assert 'case sequenceController = "sequenceController"' in provider
    assert 'case transcriptDisplay = "transcriptDisplay"' in provider
    assert 'case timeBased = "timeBased"' in provider

    body = _function_body(provider, "func currentSentenceIndex() -> Result?")
    sequence_index = body.index("if sequenceController.isEnabled")
    transcript_index = body.index("if let displayIndex = transcriptDisplayIndex()")
    time_index = body.index("if let timeIndex = timeBasedIndex()")
    assert sequence_index < transcript_index < time_index
    assert "return Result(index: seqIndex, strategy: .sequenceController)" in body
    assert "return Result(index: displayIndex, strategy: .transcriptDisplay)" in body
    assert "return Result(index: timeIndex, strategy: .timeBased)" in body
    assert "return nil" in body

    assert "static func from(" in provider
    assert "static func sentenceNumber(for sentence: InteractiveChunk.Sentence) -> Int" in provider
    assert "static func sentenceNumber(\n        in chunk: InteractiveChunk,\n        at index: Int" in provider
    assert "static func sentenceIndex(in chunk: InteractiveChunk, matching sentenceNumber: Int) -> Int?" in provider
    assert "let derivedIndex = sentenceNumber - startSentence" in provider
    assert "static func pendingSentenceIndex(in chunk: InteractiveChunk, pendingJump: PendingSentenceJump?) -> Int?" in provider
    assert "static func targetSentenceIndex(" in provider
    assert "SentencePositionProvider.from(" in tracks
    assert "sequenceController: viewModel.sequenceController" in tracks
    assert "activeSentenceDisplay(for: chunk)" in tracks
    assert "viewModel.activeSentence(at: viewModel.highlightingTime)" in tracks
    assert "return positionResult?.index" in tracks
    assert "captureCurrentSentenceIndex(for: chunk)" in audio_management
    selection = _source("InteractivePlayerViewModel+Selection.swift")
    assert "SentencePositionProvider.targetSentenceIndex(" in selection
    assert "SentencePositionProvider.sentenceIndex(in: updatedChunk, matching: sentenceNumber)" in selection
    assert "SentencePositionProvider.sentenceIndex(in: chunk, matching: sentenceNumber) != nil" in selection
    assert "SentencePositionProvider.sentenceNumber(in: chunk, at: runtime.index) == sentenceNumber" in selection


def test_single_track_rendering_ignores_stale_sequence_state() -> None:
    playback = _source("InteractivePlayerViewModel+Playback.swift")
    sequence = _source("InteractivePlayerViewModel+Sequence.swift")
    content = _source("InteractivePlayerView+InteractiveContent.swift")

    highlighting_body = _function_body(playback, "var highlightingTime: Double")
    assert "if isSequenceModeActive && sequenceController.isTransitioning" in highlighting_body
    assert "if isSequenceModeActive, let expected = sequenceController.expectedPosition" in highlighting_body

    sequence_update_body = _function_body(
        sequence,
        "func updateSequencePlayback(currentTime: Double, isPlaying: Bool)",
    )
    assert "guard isSequenceModeActive, isPlaying else { return }" in sequence_update_body
    assert "guard sequenceController.isEnabled, isPlaying else { return }" not in sequence_update_body

    assert "let sequenceRenderGuardsActive = viewModel.isSequenceModeActive" in content
    assert "let isTransitioning = sequenceRenderGuardsActive && viewModel.isSequenceTransitioning" in content
    assert "let isSameSentenceTrackSwitch = sequenceRenderGuardsActive && viewModel.sequenceController.isSameSentenceTrackSwitch" in content
    assert "let isDwelling = sequenceRenderGuardsActive && viewModel.sequenceController.isDwelling" in content
    assert "let currentSentenceIdx = sequenceRenderGuardsActive ? viewModel.sequenceController.currentSentenceIndex : nil" in content
    assert "let expectedPosition = sequenceRenderGuardsActive ? viewModel.sequenceController.expectedPosition : nil" in content


def test_sentence_jump_supersession_and_ready_seek_contract() -> None:
    models = _source("InteractivePlayerModels.swift")
    playback = _source("InteractivePlayerViewModel+Playback.swift")
    selection = _source("InteractivePlayerViewModel+Selection.swift")

    assert "struct PendingSentenceJump: Equatable" in models
    assert "let autoPlay: Bool" in models

    jump_body = _function_body(selection, "func jumpToSentence(_ sentenceNumber: Int, autoPlay: Bool = false)")
    assert "let requestedJump = PendingSentenceJump(" in jump_body
    assert "autoPlay: autoPlay" in jump_body
    assert "pendingSentenceJump = requestedJump" in jump_body
    assert "guard self.pendingSentenceJump == requestedJump else" in jump_body
    assert "if self.pendingSentenceJump == nil" in jump_body
    assert "let targetIndex = SentencePositionProvider.sentenceIndex(" in jump_body
    assert "selectChunk(id: targetChunk.id, autoPlay: autoPlay, targetSentenceIndex: targetIndex)" in jump_body
    assert jump_body.index("guard self.pendingSentenceJump == requestedJump else") < jump_body.index(
        "self.prepareAudio(for: updatedChunk, autoPlay: autoPlay, targetSentenceIndex: targetIndex)"
    )

    same_url_body = _function_body(
        selection,
        "private func handleSameURLPlayback(\n        autoPlay: Bool,\n        targetSentenceIndex: Int?,\n        chunk: InteractiveChunk,\n        timingURL: URL?\n    )",
    )
    assert "reassertSingleTrackPlaybackLane(for: chunk)" in same_url_body
    assert "selectedTimingURL = timingURL" in same_url_body
    assert "seekSingleTrackSentenceWhenReady(" in same_url_body
    assert "seekPlayback(to: startTime, in: chunk)" not in same_url_body
    assert same_url_body.index("reassertSingleTrackPlaybackLane(for: chunk)") < same_url_body.index(
        "seekSingleTrackSentenceWhenReady("
    )
    assert same_url_body.index("selectedTimingURL = timingURL") < same_url_body.index(
        "seekSingleTrackSentenceWhenReady("
    )
    assert same_url_body.index("seekSingleTrackSentenceWhenReady(") < same_url_body.index(
        "if autoPlay && !audioCoordinator.isPlaying"
    )
    single_track_seek_body = _function_body(
        playback,
        "func seekSingleTrackSentence(",
    )
    assert "completion: ((Bool) -> Void)? = nil" in playback
    assert "seekPlayback(to: targetTime, in: chunk) { [weak self] _ in" in single_track_seek_body
    assert "cancelPendingAudioReadySubscription()" in single_track_seek_body
    assert "let token = currentTransitionToken" in single_track_seek_body
    assert "token == self.currentTransitionToken" in single_track_seek_body
    assert "finalizeSingleTrackSentenceSeek(" in single_track_seek_body
    finalize_seek_body = _function_body(
        playback,
        "private func finalizeSingleTrackSentenceSeek(",
    )
    assert "rememberSingleTrackSentenceAnchor(in: chunk, targetIndex: targetIndex)" in finalize_seek_body

    pending_jump_body = _function_body(selection, "func attemptPendingSentenceJump(in chunk: InteractiveChunk)")
    assert "if pending.autoPlay && !audioCoordinator.isPlaying" in pending_jump_body
    assert "playForReaderTransport()" in pending_jump_body
    assert "shouldPlay: pending.autoPlay" in pending_jump_body
    assert "seekSingleTrackSentenceWhenReady(targetIndex, in: chunk, autoPlay: pending.autoPlay)" in pending_jump_body
    assert "seekPlaybackWhenReady(to: startTime, in: chunk, autoPlay: pending.autoPlay)" not in pending_jump_body


def test_token_tap_sequence_seek_preserves_same_sentence_track_switch() -> None:
    controller = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Services"
        / "SequencePlaybackController.swift"
    ).read_text(encoding="utf-8")
    playback = _source("InteractivePlayerViewModel+Playback.swift")
    transcript = _source("InteractivePlayerView+Transcript.swift")
    token_view = _source("TextPlayerTokenWordView.swift")

    assert "func commitTokenSeekTarget(_ target: (segmentIndex: Int, track: SequenceTrack, time: Double))" in controller
    commit_body = _function_body(
        controller,
        "func commitTokenSeekTarget(_ target: (segmentIndex: Int, track: SequenceTrack, time: Double))",
    )
    assert "let previousTrack = currentTrack" in commit_body
    assert "let previousSentenceIndex = currentSegment?.sentenceIndex" in commit_body
    assert "plan[target.segmentIndex].sentenceIndex" in commit_body
    assert "isSameSentenceTrackSwitch = previousTrack != target.track && previousSentenceIndex == targetSentenceIndex" in commit_body
    assert "currentSegmentIndex = target.segmentIndex" in commit_body
    assert "currentTrack = target.track" in commit_body

    seek_body = _function_body(
        playback,
        "func seekSequencePlayback(\n        segmentIndex: Int,\n        track: SequenceTrack,\n        time: Double,\n        autoPlay: Bool\n    )",
    )
    assert "sequenceController.commitTokenSeekTarget(target)" in seek_body
    assert "handleSequenceTrackSwitch(track: track, seekTime: time, shouldPlay: autoPlay)" in seek_body
    assert "cancelPendingAudioReadySubscription()" in seek_body
    assert "let token = currentTransitionToken" in seek_body
    assert "audioCoordinator.seek(to: time)" in seek_body
    assert "guard token == self.currentTransitionToken else" in seek_body
    assert "finalizeSameTrackTokenSeek(at: time, autoPlay: autoPlay)" in seek_body
    assert "self.audioCoordinator.seek(to: time)" in seek_body

    token_seek_body = _function_body(
        transcript,
        "func handleTokenSeek(\n        sentenceIndex: Int,\n        sentenceNumber: Int?,\n        variantKind: TextPlayerVariantKind,\n        tokenIndex: Int,\n        seekTime: Double?,\n        shouldPlay: Bool,\n        in chunk: InteractiveChunk\n    )",
    )
    assert "let sequenceTrack: SequenceTrack = desiredAudioKind == .original ? .original : .translation" in token_seek_body
    assert "let resolvedSentenceIndex = resolvedLocalSentenceIndex(" in token_seek_body
    assert "findSentenceTarget(" in token_seek_body
    assert "preferredTrack: sequenceTrack" in token_seek_body
    assert "findSentenceTarget(\n                resolvedSentenceIndex" in token_seek_body
    assert "let sequenceTimingTrack: TextPlayerTimingTrack = target.track == .original ? .original : .translation" in token_seek_body
    assert "let sequenceAudioKind: InteractiveChunk.AudioOption.Kind = target.track == .original ? .original : .translation" in token_seek_body
    assert "autoPlay: shouldPlay" in token_seek_body
    assert "syncAudioModeForTokenSeek(" in token_seek_body
    assert "let targetTime = sequenceSeekTime ?? target.time" in token_seek_body
    assert "segmentIndex: target.segmentIndex" in token_seek_body
    assert "track: target.track" in token_seek_body
    assert "sequenceSeekTime ?? resolvedSeekTime" not in token_seek_body

    assert "onTap?(false)" in token_view
    assert "onLookup?()" in token_view
    assert ".onEnded { onTap?(true) }" in token_view


def test_reader_transport_pause_cancels_pending_sequence_handoffs() -> None:
    controller = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Services"
        / "SequencePlaybackController.swift"
    ).read_text(encoding="utf-8")
    sequence = _source("InteractivePlayerViewModel+Sequence.swift")

    cancel_body = _function_body(controller, "func cancelPendingAutomaticAdvanceForPause()")
    assert "dwellWorkItem?.cancel()" in cancel_body
    assert "dwellWorkItem = nil" in cancel_body
    assert "case .dwelling, .transitioning, .validating:" in cancel_body
    assert "phase = .playing" in cancel_body
    assert "onTimeStabilized?()" in cancel_body
    assert "onCleanupAudioEffects?()" in cancel_body

    pause_body = _function_body(sequence, "func pauseForReaderTransport()")
    assert pause_body.index("cancelPendingAudioReadySubscription()") < pause_body.index(
        "sequenceController.cancelPendingAutomaticAdvanceForPause()"
    )
    assert pause_body.index("sequenceController.cancelPendingAutomaticAdvanceForPause()") < pause_body.index(
        "audioCoordinator.pause()"
    )

    play_body = _function_body(sequence, "func playForReaderTransport()")
    assert "audioCoordinator.nowPlayingPlayer == nil" in play_body
    assert "let chunk = selectedChunk" in play_body
    assert "prepareAudio(for: chunk, autoPlay: true)" in play_body
    assert play_body.index("audioCoordinator.clearAudioMix()") < play_body.index("audioCoordinator.restoreVolume()")
    assert play_body.index("audioCoordinator.restoreVolume()") < play_body.index("audioCoordinator.play()")
    assert "audioCoordinator.play()" in play_body
    assert "!audioCoordinator.isPlaybackRequested" in play_body
    audible_body = _function_body(sequence, "var isNarrationAudibleForReaderTransport: Bool")
    assert "audioCoordinator.isPlaybackRequested" in audible_body
    assert "audioCoordinator.isPlaying" in audible_body
    assert "audioCoordinator.volume > 0.001" in audible_body
    assert "!isSequenceTransitioning" in audible_body


def test_single_track_auto_advance_uses_targeted_next_chunk_seek() -> None:
    selection = _source("InteractivePlayerViewModel+Selection.swift")

    ended_body = _function_body(selection, "func handlePlaybackEnded(endedURL: URL? = nil)")
    assert "let nextChunk = jobContext?.nextChunk(after: chunk.id)" in ended_body
    assert "let preservedSingleTrack = singleTrackModeForCompletedPlayback(" in ended_body
    assert "playbackEndedURLBelongsToCurrentChunk(endedURL, chunk: chunk)" in ended_body
    assert ended_body.index("playbackEndedURLBelongsToCurrentChunk(endedURL, chunk: chunk)") < ended_body.index(
        "let preservedSingleTrack = singleTrackModeForCompletedPlayback("
    )
    assert "selectChunkPreservingAudioLane(" in ended_body
    assert "nextChunk," in ended_body
    assert "autoPlay: true" in ended_body
    assert "targetSentenceIndex: 0" in ended_body
    assert "preservedSingleTrack: preservedSingleTrack" in ended_body
    assert "selectChunk(id: nextChunk.id, autoPlay: true)" not in ended_body

    completed_lane_body = _function_body(selection, "private func singleTrackModeForCompletedPlayback(")
    assert "if let track = requestedSingleTrackMode()" in completed_lane_body
    assert "guard !sequenceController.isEnabled else { return nil }" in completed_lane_body
    assert "guard sequenceController.plan.isEmpty else" in completed_lane_body
    assert "let completedURL: URL?" in completed_lane_body
    assert "activeURLs.count != 1 || activeURLs.first != endedURL" in completed_lane_body
    assert "guard activeURLs.count == 1 else { return nil }" in completed_lane_body
    assert "kind == .original && $0.streamURLs.contains(completedURL)" in completed_lane_body
    assert "kind == .translation && $0.streamURLs.contains(completedURL)" in completed_lane_body
    assert "combined.streamURLs.dropFirst().contains(completedURL)" in completed_lane_body

    requested_body = _function_body(selection, "func requestedSingleTrackMode() -> SequenceTrack?")
    assert "loadedSingleURLTrackMode()" in requested_body
    assert "loadedSingleTrackPlaybackMode" in requested_body
    assert "durableSingleTrackPlaybackMode" in requested_body
    assert "selectedTimingSingleTrackMode(in: chunk)" in requested_body
    assert requested_body.index("if let loadedSingleTrackPlaybackMode") < requested_body.index("if let preferredSingleTrackMode")
    assert requested_body.index("if let preferredSingleTrackMode") < requested_body.index(
        "if let durableSingleTrackPlaybackMode"
    )
    assert requested_body.index("if let durableSingleTrackPlaybackMode") < requested_body.index(
        "selectedTimingSingleTrackMode(in: chunk)"
    )
    assert requested_body.index("if let loadedSingleTrackPlaybackMode") < requested_body.index("if let audioModeManager")
    lifecycle_restore_body = _function_body(
        selection,
        "func lifecycleSingleTrackRestoreMode(in chunk: InteractiveChunk? = nil) -> SequenceTrack?",
    )
    assert "loadedSingleTrackPlaybackMode" in lifecycle_restore_body
    assert "preferredSingleTrackMode" in lifecycle_restore_body
    assert "durableSingleTrackPlaybackMode" in lifecycle_restore_body
    assert "selectedTimingSingleTrackMode(in: chunk)" in lifecycle_restore_body
    assert lifecycle_restore_body.index("if let loadedSingleTrackPlaybackMode") < lifecycle_restore_body.index(
        "if let preferredSingleTrackMode"
    )
    assert lifecycle_restore_body.index("if let preferredSingleTrackMode") < lifecycle_restore_body.index(
        "if let durableSingleTrackPlaybackMode"
    )
    assert lifecycle_restore_body.index("if let durableSingleTrackPlaybackMode") < lifecycle_restore_body.index(
        "selectedTimingSingleTrackMode(in: chunk)"
    )
    assert lifecycle_restore_body.index("sequenceController.audioMode") < lifecycle_restore_body.index(
        "audioModeManager.currentMode"
    )
    selected_timing_body = _function_body(
        selection,
        "private func selectedTimingSingleTrackMode(in chunk: InteractiveChunk) -> SequenceTrack?",
    )
    assert "!sequenceController.isEnabled" not in selected_timing_body
    assert "singleTrackMode(forAudioURL: selectedTimingURL, in: chunk) == selectedTimingSingleTrackMode" in selected_timing_body
    assert "chunkSupportsSingleTrack(selectedTimingSingleTrackMode, in: chunk)" in selected_timing_body
    loaded_url_body = _function_body(selection, "private func loadedSingleURLTrackMode() -> SequenceTrack?")
    assert "guard !sequenceController.isEnabled" in loaded_url_body
    assert "sequenceController.plan.isEmpty" in loaded_url_body
    assert "audioCoordinator.activeURLs.count == 1" in loaded_url_body
    assert "singleTrackMode(forAudioURL: activeURL, in: chunk)" in loaded_url_body

    assert "preservedSingleTrack: SequenceTrack? = nil" in selection
    handoff_body = _function_body(selection, "private func selectChunkPreservingAudioLane(")
    assert "if let track = preservedSingleTrack ?? requestedSingleTrackMode()" in handoff_body
    assert "durableSingleTrackPlaybackMode = preservedSingleTrack" in ended_body
    assert "applySingleTrackSelection(track, for: chunk)" in handoff_body
    assert "rememberSingleTrackSentenceAnchor(" in handoff_body
    assert "targetIndex: targetSentenceIndex" in handoff_body
    assert handoff_body.index("applySingleTrackSelection(track, for: chunk)") < handoff_body.index(
        "selectChunk("
    )
    assert "id: chunk.id" in handoff_body
    assert "autoPlay: autoPlay" in handoff_body
    assert "targetSentenceIndex: targetSentenceIndex" in handoff_body

    adjacent_body = _function_body(selection, "func selectAdjacentChunk(")
    assert "selectChunkPreservingAudioLane(" in adjacent_body
    assert "targetSentenceIndex: 0" in adjacent_body
    assert "targetSentenceIndex: -1" in adjacent_body

    playback = _source("InteractivePlayerViewModel+Playback.swift")
    assert playback.count("selectAdjacentChunk(") >= 5
    assert "selectChunk(id: nextChunk.id, autoPlay: audioCoordinator.isPlaybackRequested" not in playback
    assert "selectChunk(id: previousChunk.id, autoPlay: audioCoordinator.isPlaybackRequested" not in playback


def test_audio_coordinator_preserves_reader_intent_through_url_ended_handoff() -> None:
    coordinator = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Services"
        / "AudioPlayerCoordinator.swift"
    ).read_text(encoding="utf-8")

    load_body = _function_body(coordinator, "func load(urls: [URL]")
    same_url_branch = load_body[load_body.index("if activeURLs == sanitized {") : load_body.index("streamFailureRetryCountByURL = [:]")]
    assert "isPlaybackRequested = preservePlaybackRequested ? wasPlaybackRequested : shouldAutoPlay" in same_url_branch
    assert "if activeURL == nil {\n                    activeURL = sanitized.first\n                }" in same_url_branch
    assert same_url_branch.index("isPlaybackRequested = preservePlaybackRequested ? wasPlaybackRequested : shouldAutoPlay") < same_url_branch.index(
        "if shouldAutoPlay"
    )

    end_body = _function_body(coordinator, "private func installEndObserver(for player: AVPlayer)")
    assert "if let handler = self.onPlaybackEndedWithURL" in end_body
    handler_branch = end_body[
        end_body.index("if let handler = self.onPlaybackEndedWithURL") : end_body.index("} else {", end_body.index("if let handler = self.onPlaybackEndedWithURL"))
    ]
    assert "self.isPlaybackRequested = false" not in handler_branch
    assert "AudioPlaybackRegistry.shared.endPlayback(for: self)" not in handler_branch
    assert "self.setIdleTimerDisabled(false)" not in handler_branch
    assert "handler(endedURL)" in handler_branch
    assert "self.isPlaybackRequested = false" in end_body
    assert "self.onPlaybackEnded?()" in end_body


def test_tvos_sequence_boundaries_leave_headroom_for_output_buffers() -> None:
    controller = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Services"
        / "SequencePlaybackController.swift"
    ).read_text(encoding="utf-8")

    headroom_body = _function_body(controller, "private var boundaryHeadroom: Double")
    assert "#if os(tvOS)" in headroom_body
    assert "return 0.18" in headroom_body
    assert "return 0.05" in headroom_body
    assert "private let fadeOutDuration: Double = 0.20" in controller
    install_body = _function_body(controller, "private func installBoundaryForCurrentSegment()")
    assert "segment.end - boundaryHeadroom" in install_body
    assert "segment.end - fadeOutDuration" in install_body
    assert "onInstallBoundary?(boundaryTime)" in install_body
    assert "onApplySegmentFade?(fadeStart, segment.end)" in install_body


def test_token_tap_syncs_audio_mode_before_non_sequence_track_seek() -> None:
    transcript = _source("InteractivePlayerView+Transcript.swift")

    helper_body = _function_body(
        transcript,
        "private func syncAudioModeForTokenSeek(\n        to desiredAudioKind: InteractiveChunk.AudioOption.Kind,\n        preservingSentenceIndex sentenceIndex: Int\n    ) -> Bool",
    )
    assert "case .original:" in helper_body
    assert "case .translation:" in helper_body
    assert "audioModeManager.setTracks(" in helper_body
    assert "original: desiredTrack == .original" in helper_body
    assert "translation: desiredTrack == .translation" in helper_body
    assert "viewModel.sequenceController.audioMode = audioModeManager.currentMode" in helper_body
    assert "return previousMode != audioModeManager.currentMode" in helper_body

    token_seek_body = _function_body(
        transcript,
        "func handleTokenSeek(\n        sentenceIndex: Int,\n        sentenceNumber: Int?,\n        variantKind: TextPlayerVariantKind,\n        tokenIndex: Int,\n        seekTime: Double?,\n        shouldPlay: Bool,\n        in chunk: InteractiveChunk\n    )",
    )
    assert "let didSyncAudioMode = syncAudioModeForTokenSeek(" in token_seek_body
    assert "resolvedSeekTime == nil || shouldSwitch || didSyncAudioMode" in token_seek_body
    assert "if didSyncAudioMode && !shouldSwitch" in token_seek_body
    assert "viewModel.prepareAudio(for: chunk, autoPlay: audioCoordinator.isPlaybackRequested)" in token_seek_body


def test_visible_text_track_toggles_sync_audio_mode() -> None:
    tracks = _source("InteractivePlayerView+Tracks.swift")
    menu_controls = _source("InteractivePlayerView+MenuControls.swift")

    track_toggle_body = _function_body(
        tracks,
        "func trackToggle(label: String, kind: TextPlayerVariantKind) -> some View",
    )
    assert "toggleTrackIfAvailable(kind)" in track_toggle_body
    assert "toggleTrack(kind)" not in track_toggle_body

    toggle_body = _function_body(
        tracks,
        "func toggleTrackIfAvailable(_ kind: TextPlayerVariantKind)",
    )
    assert "let currentSentenceIndex = captureCurrentSentenceIndex(for: chunk)" in toggle_body
    assert "toggleTrack(kind)" in toggle_body
    assert "synchronizeAudioModeWithVisibleTextTracks(" in toggle_body
    assert "allowExpandingSingleTrackAudio: true" in toggle_body

    sync_body = _function_body(
        tracks,
        "func synchronizeAudioModeWithVisibleTextTracks(\n        for chunk: InteractiveChunk,\n        preservingSentence currentSentenceIndex: Int? = nil,\n        allowExpandingSingleTrackAudio: Bool = false\n    )",
    )
    assert "let wantsOriginal = canUseOriginal && visibleTracks.contains(.original)" in sync_body
    assert "let wantsTranslation = canUseTranslation && visibleTracks.contains(.translation)" in sync_body
    assert "!allowExpandingSingleTrackAudio" in sync_body
    assert "viewModel.requestedSingleTrackMode()" in sync_body
    assert "visibleTracks = [desiredTextTrack]" in sync_body
    assert "hasCustomTrackSelection = true" in sync_body
    assert "viewModel.applySingleTrackSelection(durableSingleTrack, for: chunk)" in sync_body
    assert "audioModeManager.setTracks(" in sync_body
    assert "original: wantsOriginal" in sync_body
    assert "translation: wantsTranslation" in sync_body
    assert "reconfigureAudioForCurrentToggles(preservingSentence: currentSentenceIndex)" in sync_body

    generic_toggle_body = _function_body(
        tracks,
        "func toggleTrack(_ kind: TextPlayerVariantKind)",
    )
    assert "if let selection = linguistSelection, !visibleTracks.contains(selection.variantKind)" in generic_toggle_body
    assert "linguistSelection = nil" in generic_toggle_body
    assert "linguistSelectionRange = nil" in generic_toggle_body
    assert "trackToggle(label: trackLabel(kind), kind: kind)" in menu_controls

    initial_playback_body = _function_body(
        tracks,
        "func prepareAudioModeForInitialPlayback(for chunk: InteractiveChunk)",
    )
    assert "viewModel.audioModeManager = audioModeManager" in initial_playback_body
    assert "viewModel.sequenceController.audioMode = audioModeManager.currentMode" in initial_playback_body
    assert "let appliedResumeTrack = applyPendingResumeSingleTrackIfNeeded(for: chunk)" in initial_playback_body
    assert "let prefersCustomMultiTrackSelection = shouldPreferCustomMultiTrackSelection(for: chunk)" in initial_playback_body
    assert "preserveSingleTrackModeIfNeeded(for: chunk)" in initial_playback_body
    assert "restoreSingleTrackModeFromViewModelPreferenceIfNeeded(for: chunk)" in initial_playback_body
    assert "if appliedResumeTrack || prefersCustomMultiTrackSelection" in initial_playback_body
    assert "restoredViewModelSingleTrack = false" in initial_playback_body
    assert "allowExpandingSingleTrackAudio: prefersCustomMultiTrackSelection" in initial_playback_body
    assert "if !preservedSingleTrack" in initial_playback_body
    assert "viewModel.synchronizeSelectedAudioTrackForChunkHandoff(for: chunk)" in initial_playback_body
    assert initial_playback_body.index("viewModel.audioModeManager = audioModeManager") < initial_playback_body.index(
        "let appliedResumeTrack = applyPendingResumeSingleTrackIfNeeded(for: chunk)"
    )
    assert initial_playback_body.index("applyPendingResumeSingleTrackIfNeeded") < initial_playback_body.index(
        "applyDefaultTrackSelection(for: chunk)"
    )
    assert initial_playback_body.index("preserveSingleTrackModeIfNeeded") < initial_playback_body.index(
        "applyDefaultTrackSelection(for: chunk)"
    )
    assert initial_playback_body.index(
        "viewModel.synchronizeSelectedAudioTrackForChunkHandoff(for: chunk)"
    ) < initial_playback_body.index("if viewModel.selectedAudioTrackID == nil")

    custom_multi_body = _function_body(
        tracks,
        "func shouldPreferCustomMultiTrackSelection(for chunk: InteractiveChunk) -> Bool",
    )
    assert "guard hasCustomTrackSelection else { return false }" in custom_multi_body
    assert "available.contains(.original), available.contains(.translation)" in custom_multi_body
    assert "visibleTracks.contains(.original) && visibleTracks.contains(.translation)" in custom_multi_body

    preserve_body = _function_body(
        tracks,
        "func preserveSingleTrackModeIfNeeded(for chunk: InteractiveChunk) -> Bool",
    )
    assert "guard let track = viewModel.requestedSingleTrackMode() else { return false }" in preserve_body
    assert "available.contains(desiredTextTrack) || chunkSupportsAudioTrack(track, in: chunk)" in preserve_body
    assert "visibleTracks = [desiredTextTrack]" in preserve_body
    assert "hasCustomTrackSelection = true" in preserve_body
    assert "viewModel.applySingleTrackSelection(track, for: chunk)" in preserve_body
    assert "viewModel.selectedAudioTrackID = targetID" not in preserve_body

    restore_body = _function_body(
        tracks,
        "func restoreSingleTrackModeFromViewModelPreferenceIfNeeded(for chunk: InteractiveChunk) -> Bool",
    )
    assert "viewModel.lifecycleSingleTrackRestoreMode(in: chunk)" in restore_body
    assert "viewModel.preferredSingleTrackMode" not in restore_body
    assert "case .singleTrack(let sequenceTrack) = viewModel.sequenceController.audioMode" not in restore_body
    assert "audioModeManager.setTracks(" in restore_body
    assert "viewModel.applySingleTrackSelection(requestedTrack, for: chunk)" in restore_body

    resume_track_body = _function_body(
        tracks,
        "func applyPendingResumeSingleTrackIfNeeded(for chunk: InteractiveChunk) -> Bool",
    )
    assert "guard let resumeTrack = viewModel.pendingResumeSingleTrack else { return false }" in resume_track_body
    assert "viewModel.pendingResumeSingleTrack = nil" in resume_track_body
    assert "available.contains(desiredTextTrack) || chunkSupportsAudioTrack(resumeTrack, in: chunk)" in resume_track_body
    assert "visibleTracks = [desiredTextTrack]" in resume_track_body
    assert "hasCustomTrackSelection = true" in resume_track_body
    assert "viewModel.applySingleTrackSelection(resumeTrack, for: chunk)" in resume_track_body
    assert "viewModel.selectedAudioTrackID = targetID" not in resume_track_body

    audio_support_body = _function_body(
        tracks,
        "func chunkSupportsAudioTrack(_ track: SequenceTrack, in chunk: InteractiveChunk) -> Bool",
    )
    assert "let dedicatedKind: InteractiveChunk.AudioOption.Kind = track == .original ? .original : .translation" in audio_support_body
    assert "option.kind == .combined" in audio_support_body
    assert "return !option.streamURLs.isEmpty" in audio_support_body

    selection = _source("InteractivePlayerViewModel+Selection.swift")
    select_chunk_body = _function_body(
        selection,
        "func selectChunk(id: String, autoPlay: Bool = false, targetSentenceIndex: Int? = nil)",
    )
    assert "if selectedChunkID == id, !isTargetedJump, !autoPlay" in select_chunk_body
    assert "guard selectedChunkID != id else { return }" not in select_chunk_body
    assert "synchronizeSelectedAudioTrackForChunkHandoff(for: chunk)" in select_chunk_body
    assert "self.synchronizeSelectedAudioTrackForChunkHandoff(for: updatedChunk)" in select_chunk_body
    assert select_chunk_body.index("synchronizeSelectedAudioTrackForChunkHandoff(for: chunk)") < select_chunk_body.index(
        "prepareAudio(for: chunk"
    )
    assert select_chunk_body.index("self.synchronizeSelectedAudioTrackForChunkHandoff(for: updatedChunk)") < select_chunk_body.index(
        "self.prepareAudio(for: updatedChunk"
    )
    resolve_chunk_body = _function_body(
        selection,
        "func resolveChunk(containing sentenceNumber: Int, in context: JobContext) -> InteractiveChunk?",
    )
    assert "guard let start = chunk.startSentence else { return false }" in resolve_chunk_body
    assert "guard let end = chunk.endSentence else" in resolve_chunk_body
    assert "return sentenceNumber == start" in resolve_chunk_body

    requested_body = _function_body(selection, "func requestedSingleTrackMode() -> SequenceTrack?")
    assert requested_body.index("if let loadedSingleTrackPlaybackMode") < requested_body.index("if let preferredSingleTrackMode")
    assert "case .singleTrack(let track) = audioModeManager.currentMode" in requested_body
    assert "case .singleTrack(let track) = sequenceController.audioMode" in requested_body
    assert requested_body.index("audioModeManager.currentMode") < requested_body.index("sequenceController.audioMode")
    assert "let selectedOption = chunk.audioOptions.first(where: { $0.id == selectedAudioTrackID })" in requested_body
    assert "case .translation:" in requested_body

    reassert_body = _function_body(
        selection,
        "private func reassertSingleTrackPlaybackLane(for chunk: InteractiveChunk) -> SequenceTrack?",
    )
    assert "guard let track = requestedSingleTrackMode() else { return nil }" in reassert_body
    assert "applySingleTrackSelection(track, for: chunk)" in reassert_body
    assert "return track" in reassert_body

    reprepare_body = _function_body(
        selection,
        "func reprepareSingleTrackAudioAfterContextRebuildIfNeeded(autoPlay: Bool)",
    )
    assert "guard let updatedChunk = selectedChunk" in reprepare_body
    assert "let track = requestedSingleTrackMode()" in reprepare_body
    assert "applySingleTrackSelection(track, for: updatedChunk)" in reprepare_body
    assert "let targetIndex = recentSingleTrackSentenceAnchorIndex(in: updatedChunk)" in reprepare_body
    assert "guard let targetIndex = recentSingleTrackSentenceAnchorIndex(in: updatedChunk)" not in reprepare_body
    assert "if let targetIndex" in reprepare_body
    assert "rememberSingleTrackSentenceAnchor(in: updatedChunk, targetIndex: targetIndex)" in reprepare_body
    assert "prepareAudio(" in reprepare_body
    assert "targetSentenceIndex: targetIndex" in reprepare_body

    handoff_body = _function_body(
        selection,
        "func synchronizeSelectedAudioTrackForChunkHandoff(for chunk: InteractiveChunk)",
    )
    assert "if let track = requestedSingleTrackMode()" in handoff_body
    assert "applySingleTrackSelection(track, for: chunk)" in handoff_body
    assert handoff_body.index("applySingleTrackSelection(track, for: chunk)") < handoff_body.index(
        "synchronizeSelectedAudioTrackWithCurrentMode(for: chunk)"
    )
    loading = _source("InteractivePlayerViewModel+Loading.swift")
    refresh_body = _function_body(loading, "func refreshLiveMedia() async")
    assert "reassertSelectedAudioTrackAfterContextRebuild()" in refresh_body
    assert "reprepareSingleTrackAudioAfterContextRebuildIfNeeded(" in refresh_body
    retry_body = _function_body(loading, "func retrySelectedChunkMetadataLoad(autoPlay: Bool = false)")
    assert "self.synchronizeSelectedAudioTrackForChunkHandoff(for: updatedChunk)" in retry_body
    assert "let targetIndex = self.recentSingleTrackSentenceAnchorIndex(in: updatedChunk)" in retry_body
    assert "self.prepareAudio(for: updatedChunk, autoPlay: autoPlay, targetSentenceIndex: targetIndex)" in retry_body

    sync_selected_audio_body = _function_body(
        selection,
        "func synchronizeSelectedAudioTrackWithCurrentMode(for chunk: InteractiveChunk)",
    )
    assert "audioModeManager.resolvePreferredTrackID(for: chunk)" in sync_selected_audio_body
    assert "selectedAudioTrackID = targetID" in sync_selected_audio_body
    assert "preferredAudioKind = preferredAudioKindForCurrentMode(" in sync_selected_audio_body
    assert "sequenceController.audioMode = audioModeManager.currentMode" in sync_selected_audio_body


def test_passive_audio_mode_observation_keeps_single_track_lane() -> None:
    selection = _source("InteractivePlayerViewModel+Selection.swift")
    lifecycle = _source("InteractivePlayerView+LifecycleObservers.swift")
    tracks = _source("InteractivePlayerView+Tracks.swift")
    menu_controls = _source("InteractivePlayerView+MenuControls.swift")

    remember_body = _function_body(
        selection,
        "func rememberAudioModePreference(",
    )
    assert "clearSingleTrackOnSequence: Bool = true" in selection
    assert "case .singleTrack(let track):" in remember_body
    assert "preferredSingleTrackMode = track" in remember_body
    assert "durableSingleTrackPlaybackMode = track" in remember_body
    assert "case .sequence:" in remember_body
    assert "if clearSingleTrackOnSequence" in remember_body
    assert "preferredSingleTrackMode = nil" in remember_body
    assert "durableSingleTrackPlaybackMode = nil" in remember_body

    audio_mode_change_body = _function_body(lifecycle, "private func handleAudioModeChange(_ newMode: AudioMode)")
    assert "viewModel.rememberAudioModePreference(newMode, clearSingleTrackOnSequence: false)" in audio_mode_change_body

    reconfigure_body = _function_body(
        tracks,
        "func reconfigureAudioForCurrentToggles(preservingSentence currentSentenceIndex: Int? = nil)",
    )
    assert "viewModel.rememberAudioModePreference(audioModeManager.currentMode)" in reconfigure_body

    select_audio_body = _function_body(
        menu_controls,
        "func selectAudioTrack(_ option: InteractiveChunk.AudioOption)",
    )
    assert "case .combined:" in select_audio_body
    assert "audioModeManager.enableSequenceMode(preservingPosition: currentSentenceIndex)" in select_audio_body
    assert "reconfigureAudioForCurrentToggles(preservingSentence: currentSentenceIndex)" in select_audio_body


def test_audio_menu_selection_syncs_audio_mode() -> None:
    menu_controls = _source("InteractivePlayerView+MenuControls.swift")

    select_audio_body = _function_body(
        menu_controls,
        "func selectAudioTrack(_ option: InteractiveChunk.AudioOption)",
    )
    assert "let currentSentenceIndex = captureCurrentSentenceIndex(for: chunk)" in select_audio_body
    assert "case .combined:" in select_audio_body
    assert "audioModeManager.enableSequenceMode(preservingPosition: currentSentenceIndex)" in select_audio_body
    assert "case .original:" in select_audio_body
    assert "original: true" in select_audio_body
    assert "translation: false" in select_audio_body
    assert "case .translation:" in select_audio_body
    assert "original: false" in select_audio_body
    assert "translation: true" in select_audio_body
    assert select_audio_body.count("reconfigureAudioForCurrentToggles(preservingSentence: currentSentenceIndex)") >= 3
    assert "case .other:" in select_audio_body
    assert "viewModel.selectAudioTrack(id: option.id)" in select_audio_body


def test_apple_music_manual_pause_blocks_auto_resume_during_sentence_switch() -> None:
    music = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Services"
        / "MusicKitCoordinator.swift"
    ).read_text(encoding="utf-8")
    view_model = _source("InteractivePlayerViewModel.swift")
    selection = _source("InteractivePlayerViewModel+Selection.swift")
    playback = _source("InteractivePlayerViewModel+Playback.swift")
    sequence = _source("InteractivePlayerViewModel+Sequence.swift")
    reading_bed = _source("InteractivePlayerView+ReadingBed.swift")
    lifecycle = _source("InteractivePlayerView+LifecycleObservers.swift")
    job_view = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Playback"
        / "JobPlaybackView.swift"
    ).read_text(encoding="utf-8")
    job_now_playing = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Playback"
        / "JobPlaybackView+NowPlaying.swift"
    ).read_text(encoding="utf-8")
    job_loading = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Playback"
        / "JobPlaybackView+Loading.swift"
    ).read_text(encoding="utf-8")
    library_view = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Playback"
        / "LibraryPlaybackView.swift"
    ).read_text(encoding="utf-8")
    library_now_playing = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Playback"
        / "LibraryPlaybackView+NowPlaying.swift"
    ).read_text(encoding="utf-8")
    library_loading = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Playback"
        / "LibraryPlaybackView+Loading.swift"
    ).read_text(encoding="utf-8")
    frontend_sync = FRONTEND_SYNC_DOC.read_text(encoding="utf-8")
    parity_plan = PARITY_PLAN_DOC.read_text(encoding="utf-8")
    overlay = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Music"
        / "MusicControlOverlayView.swift"
    ).read_text(encoding="utf-8")

    assert "@Published private(set) var isManuallyPaused = false" in music
    assert "@Published private(set) var isPausedByReaderTransport = false" in music
    assert "@Published private(set) var hasAutoResumeIntent = false" in music
    assert "private var shouldIgnoreNextNonPlayingStatus = false" in music
    assert "private var observedNonPlayingTask: Task<Void, Never>?" in music
    assert "private var playbackSurfaceReassertionTask: Task<Void, Never>?" in music
    assert "private var observedPlayingAsReadingBed = false" in music
    assert "private var lastReadingBedRecoveryAttempt = Date.distantPast" in music
    assert "private let readingBedRecoveryInterval: TimeInterval = 3" in music
    assert "private var hasRestoredQueueForAutoResume = false" in music
    assert "private var hasPersistedAppleMusicSelection" in music
    assert "(!isManuallyPaused || isPausedByReaderTransport)" in music
    assert "(hasAutoResumeIntent || isPausedByReaderTransport)" in music
    assert 'static let appleMusicMixInitializedKey = "player.appleMusicMixInitialized"' in music
    assert 'static let lastAppleMusicKindKey = "player.appleMusic.lastKind"' in music
    assert 'static let lastAppleMusicIDKey = "player.appleMusic.lastID"' in music
    assert 'static let lastAppleMusicTitleKey = "player.appleMusic.lastTitle"' in music
    assert "static let defaultAppleMusicMix: Double = 0.60" in music
    assert "case appleMusicBed" in music
    assert "var isBackgroundMode: Bool { ownershipState == .appleMusic || ownershipState == .appleMusicBed }" in music
    assert "func ensureLastSelectionLoadedForReadingBed() async" in music
    assert "await restoreLastAppleMusicSelectionToQueue()" in music
    assert "private func persistLastAppleMusicSelection(" in music
    assert "private func restoreLastAppleMusicSelectionToQueue() async" in music
    assert "MusicCatalogResourceRequest<Song>(matching: \\.id, equalTo: itemID)" in music
    assert "MusicCatalogResourceRequest<Station>(matching: \\.id, equalTo: itemID)" in music
    assert "persistLastAppleMusicSelection(\n                kind: .songs" in music
    assert "persistLastAppleMusicSelection(\n                kind: .stations" in music

    pause_body = _function_body(music, "func pause(userInitiated: Bool = true)")
    assert "cancelPlaybackSurfaceReassertions()" in pause_body
    assert "if userInitiated" in pause_body
    assert "isManuallyPaused = true" in pause_body
    assert "isPausedByReaderTransport = false" in pause_body
    assert "hasAutoResumeIntent = false" in pause_body
    assert "shouldIgnoreNextNonPlayingStatus = true" in pause_body
    assert "ApplicationMusicPlayer.shared.pause()" in pause_body

    reader_pause_body = _function_body(music, "func pauseReadingBedForReaderTransport()")
    assert "simulateReadingBedPauseForE2E()" in reader_pause_body
    assert 'adoptPauseAsReaderTransport(reason: "readerTransportPause", source: "reader transport")' in reader_pause_body
    adopt_pause_body = _function_body(music, "private func adoptPauseAsReaderTransport(reason: String, source: String)")
    assert "cancelPlaybackSurfaceReassertions()" in adopt_pause_body
    assert "isManuallyPaused = true" in adopt_pause_body
    assert "isPausedByReaderTransport = true" in adopt_pause_body
    assert "hasAutoResumeIntent = false" in adopt_pause_body
    assert "observedPlayingAsReadingBed = false" in adopt_pause_body
    assert "isPlaying = false" in adopt_pause_body
    assert "readerTransportPauseAdoptionRevision &+= 1" in adopt_pause_body
    assert "markPlaybackSurfaceDidChange(reason: reason)" in adopt_pause_body

    reader_resume_body = _function_body(music, "func resumeReadingBedForReaderTransport()")
    assert "simulateReadingBedPlayForE2E()" in reader_resume_body
    assert "isManuallyPaused = false" in reader_resume_body
    assert "isPausedByReaderTransport = false" in reader_resume_body
    assert "hasAutoResumeIntent = true" in reader_resume_body
    assert "let resumeBarrier = readerTransportResumeBarrier" in reader_resume_body
    assert "resume(userInitiated: false, expectedReaderTransportBarrier: resumeBarrier)" in reader_resume_body

    resume_body = _function_body(music, "func resume(userInitiated: Bool = true,")
    assert "expectedReaderTransportBarrier: Int? = nil" in music
    assert "isExpectedReaderTransportResumeCurrent(expectedReaderTransportBarrier)" in resume_body
    assert "isManuallyPaused = false" in resume_body
    assert "isPausedByReaderTransport = false" in resume_body
    assert "guard canAutoResumeReadingBed else { return }" in resume_body
    assert "self.hasAutoResumeIntent = true" in resume_body
    assert "if !userInitiated," in resume_body
    assert 'self.settleAlreadyPlayingReadingBedForAutoResume(reason: "resumeAlreadyPlaying")' in resume_body
    assert resume_body.index("settleAlreadyPlayingReadingBedForAutoResume") < resume_body.index(
        "try await player.play()"
    )
    assert "if player.state.playbackStatus == .playing, self.isBackgroundMode" in resume_body
    assert "self.isPlaying = true" in resume_body
    assert "self.observedPlayingAsReadingBed = true" in resume_body
    already_playing_body = _function_body(
        music,
        "func settleAlreadyPlayingReadingBedForAutoResume(reason: String)",
    )
    assert "isReadingBedAlreadyPlayingForAutoResume" in already_playing_body
    assert "!isPausedByReaderTransport" in already_playing_body
    assert "!isReaderTransportPauseGuardActive" in already_playing_body
    assert "cancelObservedNonPlayingPause()" in already_playing_body
    assert "hasAutoResumeIntent = true" in already_playing_body
    assert "isPlaying = true" in already_playing_body
    assert "observedPlayingAsReadingBed = true" in already_playing_body
    assert "e2eMusicBedAlreadyPlayingResumeSkipCount += 1" in already_playing_body
    assert 'logger.debug("Apple Music auto-resume skipped because bed is already playing")' in already_playing_body
    already_playing_probe_body = _function_body(
        music,
        "private var isReadingBedAlreadyPlayingForAutoResume: Bool",
    )
    assert "isE2EMusicBedSyncTest, isPlaying, isBackgroundMode" in already_playing_probe_body
    assert "ApplicationMusicPlayer.shared.state.playbackStatus == .playing && isBackgroundMode" in already_playing_probe_body

    stop_body = _function_body(music, "func stop()")
    assert "cancelPlaybackSurfaceReassertions()" in stop_body
    assert "shouldIgnoreNextNonPlayingStatus = true" in stop_body
    assert "hasAutoResumeIntent = false" in stop_body
    assert "observedPlayingAsReadingBed = false" in stop_body

    deactivate_body = _function_body(music, "func deactivateAsReadingBed() async")
    assert "cancelPlaybackSurfaceReassertions()" in deactivate_body
    assert "shouldIgnoreNextNonPlayingStatus = true" in deactivate_body
    assert "hasAutoResumeIntent = false" in deactivate_body

    activate_body = _function_body(music, "func activateAsReadingBed() async")
    assert "cancelObservedNonPlayingPause()" in activate_body
    assert "observedPlayingAsReadingBed = false" in activate_body
    assert "if player.state.playbackStatus == .playing" in activate_body
    assert "observedPlayingAsReadingBed = true" in activate_body

    observed_pause_body = _function_body(music, "private func handleObservedNonPlayingStatus(")
    assert "if shouldIgnoreNextNonPlayingStatus" in observed_pause_body
    assert "shouldAdoptIgnoredObservedNonPlayingAsReaderPause" in observed_pause_body
    assert "Apple Music ignored non-playing converted to reader transport pause during tvOS reading bed" in observed_pause_body
    assert "shouldIgnoreNextNonPlayingStatus = false" in observed_pause_body
    assert "guard isBackgroundMode else { return }" in observed_pause_body
    assert "guard shouldTreatObservedNonPlayingAsReaderPause else" in observed_pause_body
    assert "shouldAdoptObservedNonPlayingImmediately" in observed_pause_body
    assert "observedNonPlayingImmediate" not in observed_pause_body
    assert observed_pause_body.index("deferObservedNonPlayingDuringActiveReadingBed") < observed_pause_body.index(
        "guard shouldTreatObservedNonPlayingAsReaderPause else"
    )
    assert observed_pause_body.index("guard shouldTreatObservedNonPlayingAsReaderPause else") < observed_pause_body.index(
        "shouldAdoptObservedNonPlayingImmediately"
    )
    assert observed_pause_body.index("shouldAdoptObservedNonPlayingImmediately") < observed_pause_body.index(
        "observedNonPlayingTask = Task"
    )
    assert "readerActive=" in observed_pause_body
    assert "guard=\\(" in observed_pause_body
    assert "autoResume=" in observed_pause_body
    assert "observed non-playing confirmation ignored after state changed" in observed_pause_body
    assert "Apple Music observed non-playing ignored observedAsBed=false" in observed_pause_body
    assert "guard observedPlayingAsReadingBed else" not in observed_pause_body
    assert "guard observedPlayingAsReadingBed || isPlaying else { return }" not in observed_pause_body
    assert "guard currentSongTitle != nil else { return }" not in observed_pause_body
    assert "observedNonPlayingTask?.cancel()" in observed_pause_body
    assert "observedNonPlayingTask = Task" in observed_pause_body
    assert "Task.sleep(nanoseconds: 600_000_000)" in observed_pause_body
    assert "ApplicationMusicPlayer.shared.state.playbackStatus != .playing" in observed_pause_body
    assert 'adoptPauseAsReaderTransport(reason: "observedNonPlaying", source: "observed non-playing")' in observed_pause_body
    ignored_observed_pause_body = _function_body(
        music,
        "private var shouldAdoptIgnoredObservedNonPlayingAsReaderPause",
    )
    assert "#if os(tvOS)" in ignored_observed_pause_body
    assert "ownershipState == .appleMusicBed" in ignored_observed_pause_body
    assert "isReaderNarrationActiveForMusicBed" in ignored_observed_pause_body
    assert "!isReaderNarrationActiveForMusicBed" not in ignored_observed_pause_body
    assert "!isManuallyPaused" in ignored_observed_pause_body
    assert "!isPausedByReaderTransport" in ignored_observed_pause_body
    immediate_observed_pause_body = _function_body(
        music,
        "private var shouldAdoptObservedNonPlayingImmediately",
    )
    assert "#if os(tvOS)" in immediate_observed_pause_body
    assert "ownershipState == .appleMusicBed" in immediate_observed_pause_body
    assert "shouldTreatObservedNonPlayingAsReaderPause" in immediate_observed_pause_body
    assert "!shouldDeferObservedNonPlayingDuringActiveReadingBed" not in immediate_observed_pause_body
    assert "isReaderNarrationActiveForMusicBed" in immediate_observed_pause_body
    assert "!isReaderNarrationActiveForMusicBed" in immediate_observed_pause_body
    assert "!hasAutoResumeIntent" not in immediate_observed_pause_body
    assert "isManuallyPaused" not in immediate_observed_pause_body
    assert "isPausedByReaderTransport" in immediate_observed_pause_body
    assert "!isPausedByReaderTransport" not in immediate_observed_pause_body
    assert "return false" in immediate_observed_pause_body
    assert "isManuallyPaused = true" in adopt_pause_body
    assert "isPausedByReaderTransport = true" in adopt_pause_body
    assert "hasAutoResumeIntent = false" in adopt_pause_body
    assert "observedPlayingAsReadingBed = false" in adopt_pause_body
    assert "if statusChanged && status != .playing" in music
    assert "handleObservedNonPlayingStatus()" in music
    assert "shouldDeferObservedNonPlayingDuringActiveReadingBed" in music
    assert "Apple Music observed transient non-playing deferred during active reading bed" in music
    deferred_body = _function_body(
        music,
        "private var shouldDeferObservedNonPlayingDuringActiveReadingBed: Bool",
    )
    assert "#if os(tvOS)" in deferred_body
    assert "guard !shouldAdoptObservedNonPlayingImmediately else { return false }" in deferred_body
    assert "ownershipState == .appleMusicBed" in deferred_body
    assert "isReaderNarrationActiveForMusicBed" in deferred_body
    assert "observedPlayingAsReadingBed || hasAutoResumeIntent" not in deferred_body
    assert "!isPausedByReaderTransport" in deferred_body
    assert "!isReaderTransportPauseGuardActive" not in deferred_body
    assert "handleObservedNonPlayingStatus(allowE2E: true)" in music
    assert "if statusChanged && status == .playing" in music
    observe_body = _function_body(music, "private func observePlaybackState()")
    assert "if status == .playing, self?.isBackgroundMode == true" in observe_body
    assert "self?.observedPlayingAsReadingBed = true" in observe_body
    assert "self?.shouldIgnoreNextNonPlayingStatus = false" in observe_body
    assert "Apple Music observed reader transport resume from system playback" in observe_body
    assert "self?.isManuallyPaused = false" in observe_body
    assert "self?.isPausedByReaderTransport = false" in observe_body
    assert 'self?.markPlaybackSurfaceDidChange(reason: "observedReaderTransportResume")' in observe_body
    treat_observed_pause_body = _function_body(music, "private var shouldTreatObservedNonPlayingAsReaderPause")
    assert "observedPlayingAsReadingBed" in treat_observed_pause_body
    assert "#if os(tvOS)" not in treat_observed_pause_body
    assert "ownershipState == .appleMusicBed" not in treat_observed_pause_body
    assert "isReaderNarrationActiveForMusicBed" not in treat_observed_pause_body
    assert "hasAutoResumeIntent" in treat_observed_pause_body
    assert "isPausedByReaderTransport" in treat_observed_pause_body

    reassert_cancel_body = _function_body(music, "private func cancelPlaybackSurfaceReassertions()")
    assert "playbackSurfaceReassertionTask?.cancel()" in reassert_cancel_body
    assert "playbackSurfaceReassertionTask = nil" in reassert_cancel_body

    clear_hold_body = _function_body(music, "private func clearReaderTransportPauseHold()")
    assert "readerTransportPauseConfirmationTask?.cancel()" in clear_hold_body
    assert "readerTransportPauseConfirmationTask = nil" in clear_hold_body

    reader_resume_body = _function_body(music, "func resumeReadingBedForReaderTransport()")
    assert "clearReaderTransportPauseHold()" in reader_resume_body
    assert "shouldIgnoreNextNonPlayingStatus = false" in reader_resume_body

    reassert_guard_body = _function_body(music, "private var shouldReassertPlaybackSurface")
    assert "isBackgroundMode" in reassert_guard_body
    assert "!isManuallyPaused" in reassert_guard_body
    assert "(isPlaying || hasAutoResumeIntent)" in reassert_guard_body

    reassert_body = _function_body(music, "private func schedulePlaybackSurfaceReassertions(reason: String)")
    assert "cancelPlaybackSurfaceReassertions()" in reassert_body
    assert "playbackSurfaceReassertionTask = Task" in reassert_body
    assert "guard !Task.isCancelled else { return }" in reassert_body
    assert "guard self.shouldReassertPlaybackSurface else { return }" in reassert_body
    assert "self.playbackSurfaceReassertionTask = nil" in reassert_body

    reconcile_body = _function_body(music, "func reconcileReadingBedSystemPlayback()")
    assert "guard isBackgroundMode else { return }" in reconcile_body
    assert "ApplicationMusicPlayer.shared.state.playbackStatus == .playing" in reconcile_body
    assert "observedPlayingAsReadingBed = true" in reconcile_body
    assert "cancelObservedNonPlayingPause()" in reconcile_body
    assert "handleObservedNonPlayingStatus()" in reconcile_body

    recovery_body = _function_body(music, "func recoverReadingBedForActiveNarration(reason: String)")
    assert "guard ownershipState == .appleMusicBed else { return }" in recovery_body
    assert "guard !isPlaying, !isManuallyPaused, !isPausedByReaderTransport else { return }" in recovery_body
    assert "hasAutoResumeIntent = true" in recovery_body
    assert "if isE2EMusicBedSyncTest" in recovery_body
    assert "simulateReadingBedPlayForE2E()" in recovery_body
    assert "guard canAutoResumeReadingBed else { return }" in recovery_body
    assert recovery_body.index("simulateReadingBedPlayForE2E()") < recovery_body.index(
        "guard canAutoResumeReadingBed else { return }"
    )
    assert "now.timeIntervalSince(lastReadingBedRecoveryAttempt) >= readingBedRecoveryInterval" in recovery_body
    assert "lastReadingBedRecoveryAttempt = now" in recovery_body
    assert "resume(userInitiated: false)" in recovery_body

    apple_body = _function_body(reading_bed, "private func handleAppleMusicPlaybackChange(isPlaying: Bool)")
    auto_resume_body = _function_body(reading_bed, "private var shouldAutoResumeAppleMusicReadingBed")
    sentence_transition_body = _function_body(reading_bed, "private var isAppleMusicSentenceTransition")
    assert "readingBedEnabled" in auto_resume_body
    assert "audioCoordinator.isPlaybackRequested" in auto_resume_body
    assert "audioCoordinator.isPlaying" not in auto_resume_body
    assert "!musicCoordinator.isPausedByReaderTransport" in auto_resume_body
    assert "!musicCoordinator.isReaderTransportPauseGuardActive" in auto_resume_body
    assert "musicCoordinator.canAutoResumeReadingBed" in auto_resume_body
    assert "#if os(tvOS)" in sentence_transition_body
    assert "return false" in sentence_transition_body
    assert "viewModel.isSequenceTransitioning" in sentence_transition_body
    assert "audioCoordinator.isPlaybackRequested" in sentence_transition_body
    assert "!audioCoordinator.isPlaying" in sentence_transition_body
    can_resume_body = _function_body(music, "var canAutoResumeReadingBed")
    assert "hasQueuedMusicForAutoResume" in can_resume_body
    queue_body = _function_body(music, "private var hasQueuedMusicForAutoResume")
    assert "ApplicationMusicPlayer.shared.queue.currentEntry != nil" in queue_body
    assert "hasRestoredQueueForAutoResume" in queue_body
    assert "hasPersistedAppleMusicSelection" in queue_body
    ensure_body = _function_body(music, "func ensureLastSelectionLoadedForReadingBed() async")
    assert "currentSongTitle != nil || ApplicationMusicPlayer.shared.queue.currentEntry != nil" not in ensure_body
    assert "ApplicationMusicPlayer.shared.queue.currentEntry != nil" in ensure_body
    assert "ApplicationMusicPlayer.shared.queue.currentEntry != nil || hasRestoredQueueForAutoResume" not in ensure_body
    assert "await restoreLastAppleMusicSelectionToQueue()" in ensure_body
    prepare_body = _function_body(music, "func prepareForNarrationMix()")
    assert "guard hasQueuedMusicForAutoResume else { return }" in prepare_body
    assert "shouldIgnoreNextNonPlayingStatus = true" not in prepare_body
    deferred_resume_body = _function_body(music, "func prepareDeferredReadingBedResumeForReaderTransport()")
    assert "guard ownershipState == .appleMusicBed else { return }" in deferred_resume_body
    assert "clearReaderTransportPauseHold()" in deferred_resume_body
    assert "cancelObservedNonPlayingPause()" in deferred_resume_body
    assert "shouldIgnoreNextNonPlayingStatus = false" in deferred_resume_body
    assert "isManuallyPaused = false" in deferred_resume_body
    assert "isPausedByReaderTransport = false" in deferred_resume_body
    assert "hasAutoResumeIntent = true" in deferred_resume_body
    assert 'updateMusicPlaybackSurfaceSuppression(reason: "readerTransportDeferredResume")' in deferred_resume_body
    restore_body = _function_body(music, "private func restoreLastAppleMusicSelectionToQueue() async")
    assert "hasRestoredQueueForAutoResume = true" in restore_body
    assert "Apple Music restored reading bed queue persistedSelection=true" in restore_body
    assert "hasRestoredQueueForAutoResume = false" in stop_body
    assert "guard ownershipState == .appleMusic else { return }" not in prepare_body
    assert "if isPlaying || audioCoordinator.isPlaybackRequested" in apple_body
    assert "musicCoordinator.isPausedByReaderTransport || musicCoordinator.isReaderTransportPauseGuardActive" in apple_body
    assert "musicCoordinator.pauseReadingBedForReaderTransport()" in apple_body
    assert apple_body.index("musicCoordinator.pauseReadingBedForReaderTransport()") < apple_body.index(
        "if isPlaying || audioCoordinator.isPlaybackRequested"
    )
    assert "if isAppleMusicSentenceTransition" in apple_body
    assert 'reason: "interactiveSentenceTransitionAlreadyPlaying"' in apple_body
    assert apple_body.index("if isAppleMusicSentenceTransition") < apple_body.index(
        "if isPlaying || audioCoordinator.isPlaybackRequested"
    )
    assert apple_body.index("interactiveSentenceTransitionAlreadyPlaying") < apple_body.index(
        "await musicCoordinator.ensureLastSelectionLoadedForReadingBed()"
    )
    assert "await musicCoordinator.ensureLastSelectionLoadedForReadingBed()" in apple_body
    assert "shouldAutoResumeAppleMusicReadingBed" in apple_body
    assert 'musicCoordinator.settleAlreadyPlayingReadingBedForAutoResume(reason: "interactivePlaybackChangeAlreadyPlaying")' in apple_body
    assert 'musicCoordinator.settleAlreadyPlayingReadingBedForAutoResume(reason: "interactivePlaybackChangeTaskAlreadyPlaying")' in apple_body
    assert apple_body.index("interactivePlaybackChangeAlreadyPlaying") < apple_body.index(
        "await musicCoordinator.ensureLastSelectionLoadedForReadingBed()"
    )
    assert apple_body.index("interactivePlaybackChangeTaskAlreadyPlaying") < apple_body.index(
        "musicCoordinator.resume(userInitiated: false)"
    )
    assert "musicCoordinator.resume(userInitiated: false)" in apple_body
    assert "musicCoordinator.currentSongTitle != nil" not in apple_body
    audio = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Services"
        / "AudioPlayerCoordinator.swift"
    ).read_text(encoding="utf-8")
    assert "var mode: AVAudioSession.Mode" in audio
    assert "mixing ? .default : .spokenAudio" in audio
    assert "duckOthers: Bool = false" in audio
    assert "return duckOthers ? [.mixWithOthers, .duckOthers] : [.mixWithOthers]" in audio
    assert "must require `audioCoordinator.isPlaybackRequested`" in frontend_sync
    assert "plus MusicKit auto-resume intent" in frontend_sync
    assert "neutral playback session while mixing" in frontend_sync
    assert "MPNowPlayingSession" in frontend_sync
    assert "session info and\n  command centers" in frontend_sync
    assert "active=true canBecomeActive=true" in frontend_sync
    assert "does not require `audioCoordinator.isPlaying`" in frontend_sync
    assert "does not restart Apple Music unless the reader is actively playing" not in frontend_sync
    assert "narration playback still being requested" in parity_plan
    assert "no longer waits for `audioCoordinator.isPlaying`" in parity_plan
    assert "Low Apple Music mix values request" in parity_plan
    assert "MPNowPlayingSession" in parity_plan
    assert "active=true canBecomeActive=true" in parity_plan
    assert "both requested and\n  actively playing" not in parity_plan

    assert "var isAppleMusicOwningLockScreen: Bool" in job_view
    assert "musicOwnership.ownershipState == .appleMusic" in job_view
    assert "guard !isAppleMusicOwningLockScreen else { return }" in job_now_playing
    assert "if isVideoPreferred || isAppleMusicOwningLockScreen" in job_loading
    assert "var isAppleMusicOwningLockScreen: Bool" in library_view
    assert "musicOwnership.ownershipState == .appleMusic" in library_view
    assert "guard !isAppleMusicOwningLockScreen else { return }" in library_now_playing
    assert "if isVideoPreferred || isAppleMusicOwningLockScreen" in library_loading

    configure_body = _function_body(reading_bed, "func configureReadingBed()")
    assert "guard readingBedEnabled else" in configure_body
    assert configure_body.index("prepareAppleMusicMixDefaultIfNeeded()") < configure_body.index("guard readingBedEnabled else")
    assert "audioCoordinator.configureAudioSessionForMixing(false)" in configure_body
    assert "audioCoordinator.setTargetVolume(1.0)" in configure_body
    assert "await musicCoordinator.ensureLastSelectionLoadedForReadingBed()" in configure_body
    assert configure_body.index("await musicCoordinator.ensureLastSelectionLoadedForReadingBed()") < configure_body.index(
        "await musicCoordinator.activateAsReadingBed()"
    )

    switch_body = _function_body(reading_bed, "func switchToAppleMusic()")
    assert "guard readingBedEnabled else" in switch_body
    assert switch_body.index("prepareAppleMusicMixDefaultIfNeeded()") < switch_body.index("guard readingBedEnabled else")
    assert "audioCoordinator.configureAudioSessionForMixing(false)" in switch_body
    assert "audioCoordinator.setTargetVolume(1.0)" in switch_body
    assert "shouldAutoResumeAppleMusicReadingBed" in switch_body
    assert "await musicCoordinator.ensureLastSelectionLoadedForReadingBed()" in switch_body
    assert switch_body.index("await musicCoordinator.ensureLastSelectionLoadedForReadingBed()") < switch_body.index(
        "musicCoordinator.prepareForNarrationMix()"
    )
    assert "musicCoordinator.resume(userInitiated: false)" in switch_body

    apple_mix_body = _function_body(reading_bed, "func prepareAppleMusicMixDefaultIfNeeded()")
    assert "guard !didInitializeAppleMusicMix else { return }" in apple_mix_body
    assert "didInitializeAppleMusicMix = true" in apple_mix_body
    assert "guard musicVolume <= MusicPreferences.defaultMusicVolume else { return }" in apple_mix_body
    assert "musicVolume = MusicPreferences.defaultAppleMusicMix" in apple_mix_body

    apply_mix_body = _function_body(reading_bed, "func applyMixVolume(_ mix: Double)")
    assert "audioCoordinator.setTargetVolume(narrationVolume)" in apply_mix_body
    assert "if !useAppleMusicForBed" in apply_mix_body
    assert "configureAppleMusicAudioSession(for: mix)" in apply_mix_body
    assert "low mixes request system ducking" in apply_mix_body
    assert "readingBedCoordinator.setVolume(bedVolume)" in apply_mix_body

    toggle_body = _function_body(reading_bed, "func handleReadingBedToggleWithAppleMusic(enabled: Bool)")
    assert "shouldAutoResumeAppleMusicReadingBed" in toggle_body
    assert "await musicCoordinator.ensureLastSelectionLoadedForReadingBed()" in toggle_body
    assert "musicCoordinator.resume(userInitiated: false)" in toggle_body
    assert "musicCoordinator.resume()" not in toggle_body
    assert "musicCoordinator.currentSongTitle != nil" not in toggle_body

    disappear_body = _function_body(lifecycle, "private func handlePlayerDisappear()")
    assert "if shouldKeepAppleMusicReadingBedOnDisappear" in disappear_body
    assert "musicCoordinator.prepareForNarrationMix()" in disappear_body
    assert "applyMixVolume(musicVolume)" in disappear_body
    assert "musicCoordinator.pause(userInitiated: false)" in disappear_body
    assert "musicCoordinator.deactivateAsReadingBed()" in disappear_body
    assert disappear_body.index("musicCoordinator.prepareForNarrationMix()") < disappear_body.index(
        "musicCoordinator.pause(userInitiated: false)"
    )
    disappear_keep_body = _function_body(lifecycle, "private var shouldKeepAppleMusicReadingBedOnDisappear")
    assert "useAppleMusicForBed" in disappear_keep_body
    assert "readingBedEnabled" in disappear_keep_body
    assert "musicCoordinator.isAuthorized" in disappear_keep_body
    assert "audioCoordinator.isPlaybackRequested" in disappear_keep_body
    assert "audioCoordinator.isPlaying" not in disappear_keep_body
    assert "keep\n  playing under active reader navigation handoffs" in frontend_sync
    assert "short-circuit automatic resume before scheduling a\n  MusicKit task" in frontend_sync
    assert "autoResumeAlreadyPlaying=N" in frontend_sync
    assert "asserts\n  the counter reaches at least 1" in frontend_sync
    assert "without asking\n  MusicKit to `play()` again" in frontend_sync
    assert "Apple Music is an optional background bed, not narration audio" in frontend_sync
    assert "low mix values request `.duckOthers`" in frontend_sync
    assert "Music bed-forward default" in frontend_sync
    assert "Device evidence should include `Reader NowPlaying session" in frontend_sync
    assert "scene-phase changes" in frontend_sync
    assert "make test-e2e-ipad-music-bed-sync" in frontend_sync
    assert "make test-e2e-tvos-music-bed-sync" in frontend_sync
    assert "debug-only MyLinguist pronunciation setup" in frontend_sync
    assert "requires both sentence audio and the Apple Music bed" in frontend_sync
    assert "Active reader navigation handoffs also keep\n  Apple Music alive" in parity_plan
    built_in_recovery_body = _function_body(lifecycle, "private func handleReadingBedPlaybackChange(_ isPlaying: Bool)")
    assert "guard !useAppleMusicForBed else { return }" in built_in_recovery_body
    assert built_in_recovery_body.index("guard !useAppleMusicForBed else { return }") < built_in_recovery_body.index(
        "updateReadingBedPlayback()"
    )

    overlay_toggle_body = _function_body(overlay, "private func togglePlayback()")
    assert "musicCoordinator.pause()" in overlay_toggle_body
    assert "musicCoordinator.resume()" in overlay_toggle_body

    assert "func handleSequenceTrackSwitch(track: SequenceTrack, seekTime: Double, shouldPlay: Bool)" in sequence
    assert "requiresPlaybackRequest: Bool = false" in sequence
    assert "if shouldPlay && (!requiresPlaybackRequest || self.audioCoordinator.isPlaybackRequested)" in sequence
    assert "requiresPlaybackRequest: shouldPlay" in sequence
    assert "shouldPlay: self.audioCoordinator.isPlaybackRequested" in view_model
    assert "let shouldResume = self.audioCoordinator.isPlaybackRequested" in view_model
    assert "if shouldResume {" in view_model
    assert "self.audioCoordinator.recordStickySequenceResumeForE2E()" in view_model
    assert "self.audioCoordinator.recordStickySequenceResumeForE2E()" in sequence
    assert "shouldPlay: pending.autoPlay" in selection
    assert "shouldPlay: audioCoordinator.isPlaybackRequested" in playback
    assert "if wasPlaying,\n                       self.audioCoordinator.isPlaybackRequested,\n                       !self.audioCoordinator.isPlaying" in playback
    assert "if (wasPlaying || shouldPlay), !self.audioCoordinator.isPlaying" in selection


def test_token_tap_syncs_combined_single_track_before_seek() -> None:
    transcript = _source("InteractivePlayerView+Transcript.swift")

    token_seek_body = _function_body(
        transcript,
        "func handleTokenSeek(\n        sentenceIndex: Int,\n        sentenceNumber: Int?,\n        variantKind: TextPlayerVariantKind,\n        tokenIndex: Int,\n        seekTime: Double?,\n        shouldPlay: Bool,\n        in chunk: InteractiveChunk\n    )",
    )

    assert "if viewModel.isSequenceModeActive" in token_seek_body
    assert token_seek_body.index("if viewModel.isSequenceModeActive") < token_seek_body.index(
        "var resolvedSeekTime = seekTime"
    )
    assert "if case .singleTrack = audioModeManager.currentMode" in token_seek_body
    assert "let didSyncAudioMode = isCombinedQueue && isSingleTrackMode" in token_seek_body
    assert "syncAudioModeForTokenSeek(\n                    to: desiredAudioKind" in token_seek_body
    assert "if didSyncAudioMode {\n                viewModel.prepareAudio(for: chunk, autoPlay: audioCoordinator.isPlaybackRequested)\n            }" in token_seek_body
    assert "if resolvedSeekTime == nil || didSyncAudioMode" in token_seek_body
    assert "if isCombinedQueue, !isSingleTrackMode, desiredAudioKind == .translation" in token_seek_body

    local_index_body = _function_body(
        transcript,
        "private func resolvedLocalSentenceIndex(\n        for sentenceIndex: Int,\n        sentenceNumber: Int?,\n        in chunk: InteractiveChunk\n    ) -> Int?",
    )
    assert "chunk.sentences.indices.contains(sentenceIndex)" in local_index_body
    assert "SentencePositionProvider.sentenceIndex(in: chunk, matching: sentenceNumber)" in local_index_body
    assert "sentence.id == sentenceIndex || sentence.displayIndex == sentenceIndex" in local_index_body
