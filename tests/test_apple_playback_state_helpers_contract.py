from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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
    assert "audioModeManager.toggle(.original, preservingPosition: currentSentenceIndex)" in audio_management
    assert "audioModeManager.toggle(.translation, preservingPosition: currentSentenceIndex)" in audio_management


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
    assert "case .singleTrack(let enabledTrack):" in instruction_body
    assert "return resolveSingleFromCombined" in instruction_body

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
    assert "matchURLToTimingTrack(activeURL: activeURL, chunk: chunk)" in timing_body
    assert "return track.streamURLs.count == 1 ? .mix : .original" in timing_body

    assert "mgr.resolveAudioInstruction(for: chunk, selectedTrackID: selectedAudioTrackID)" in selection
    assert "mgr.currentMode.description" in selection
    assert "if let mgr = audioModeManager" in playback
    assert "return mgr.resolveTimingTrack(" in playback


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
    assert "SentencePositionProvider.from(" in tracks
    assert "sequenceController: viewModel.sequenceController" in tracks
    assert "activeSentenceDisplay(for: chunk)" in tracks
    assert "viewModel.activeSentence(at: viewModel.highlightingTime)" in tracks
    assert "return positionResult?.index" in tracks
    assert "captureCurrentSentenceIndex(for: chunk)" in audio_management


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

    token_seek_body = _function_body(
        transcript,
        "func handleTokenSeek(\n        sentenceIndex: Int,\n        sentenceNumber: Int?,\n        variantKind: TextPlayerVariantKind,\n        tokenIndex: Int,\n        seekTime: Double?,\n        shouldPlay: Bool,\n        in chunk: InteractiveChunk\n    )",
    )
    assert "let sequenceTrack: SequenceTrack = desiredAudioKind == .original ? .original : .translation" in token_seek_body
    assert "track: sequenceTrack" in token_seek_body
    assert "autoPlay: shouldPlay" in token_seek_body
    assert "syncAudioModeForTokenSeek(" in token_seek_body
    assert "let targetTime = sequenceSeekTime ?? viewModel.sequenceController.plan[segmentIndex].start" in token_seek_body
    assert "sequenceSeekTime ?? resolvedSeekTime" not in token_seek_body

    assert "onTap?(false)" in token_view
    assert "onLookup?()" in token_view
    assert ".onEnded { onTap?(true) }" in token_view


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
    assert "if isCombinedQueue, !isSingleTrackMode, desiredAudioKind == .translation" in token_seek_body
