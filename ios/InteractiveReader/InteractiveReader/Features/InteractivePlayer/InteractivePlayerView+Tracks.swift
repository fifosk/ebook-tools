import SwiftUI

extension InteractivePlayerView {
    func trackLabel(_ kind: TextPlayerVariantKind) -> String {
        switch kind {
        case .original:
            return "Original"
        case .transliteration:
            return "Transliteration"
        case .translation:
            return "Translation"
        }
    }

    func trackSummaryLabel(_ kind: TextPlayerVariantKind) -> String {
        switch kind {
        case .original:
            return "Original"
        case .transliteration:
            return "Translit"
        case .translation:
            return "Translation"
        }
    }

    func trackToggle(label: String, kind: TextPlayerVariantKind) -> some View {
        Button {
            toggleTrack(kind)
        } label: {
            if visibleTracks.contains(kind) {
                Label(label, systemImage: "checkmark")
            } else {
                Text(label)
            }
        }
    }

    func imageReelToggle() -> some View {
        let isEnabled = showImageReel?.wrappedValue ?? false
        return Button {
            if let showImageReel {
                showImageReel.wrappedValue.toggle()
            }
        } label: {
            if isEnabled {
                Label("Images", systemImage: "checkmark")
            } else {
                Text("Images")
            }
        }
    }

    func toggleTrack(_ kind: TextPlayerVariantKind) {
        withAnimation(.none) {
            if visibleTracks.contains(kind) {
                if visibleTracks.count > 1 {
                    visibleTracks.remove(kind)
                }
            } else {
                visibleTracks.insert(kind)
            }
        }
        hasCustomTrackSelection = true
    }

    func toggleTrackIfAvailable(_ kind: TextPlayerVariantKind) {
        guard let chunk = viewModel.selectedChunk else { return }
        let available = availableTracks(for: chunk)
        guard available.contains(kind) else { return }
        toggleTrack(kind)
    }

    func handleWordNavigation(_ delta: Int, in chunk: InteractiveChunk?) {
        guard let chunk else { return }
        handleWordNavigation(delta, in: chunk)
    }

    /// Toggle audio track enabled state.
    /// This controls whether original/translation audio plays during sequence mode.
    /// When both are enabled, sequence mode alternates between them.
    /// When only one is enabled, only that track plays (sequence mode is disabled).
    func toggleAudioTrack(_ kind: InteractiveChunk.AudioOption.Kind) {
        guard let chunk = viewModel.selectedChunk else { return }

        // Capture current sentence position BEFORE changing mode
        let currentSentenceIndex = captureCurrentSentenceIndex(for: chunk)

        // Toggle via the mode manager (handles the logic of not disabling both)
        audioModeManager.toggle(kind: kind, preservingPosition: currentSentenceIndex)

        // Reconfigure playback based on new toggle state
        reconfigureAudioForCurrentToggles(preservingSentence: currentSentenceIndex)
    }

    /// Capture the current sentence index using SentencePositionProvider
    /// - Parameter chunk: The current chunk
    /// - Returns: The current sentence index, or nil if not found
    func captureCurrentSentenceIndex(for chunk: InteractiveChunk) -> Int? {
        // Log state BEFORE creating provider
        print("[AudioToggle] Capturing position - seqEnabled=\(viewModel.sequenceController.isEnabled), seqSentenceIdx=\(viewModel.sequenceController.currentSentenceIndex ?? -1), highlightingTime=\(String(format: "%.3f", viewModel.highlightingTime))")

        let positionProvider = SentencePositionProvider.from(
            sequenceController: viewModel.sequenceController,
            transcriptDisplayIndex: { [self] in
                let display = activeSentenceDisplay(for: chunk)
                print("[AudioToggle] transcriptDisplayIndex called: index=\(display?.index ?? -1)")
                return display?.index
            },
            timeBasedIndex: { [self] in
                guard let activeSentence = viewModel.activeSentence(at: viewModel.highlightingTime) else {
                    print("[AudioToggle] timeBasedIndex: no activeSentence found")
                    return nil
                }
                let index = chunk.sentences.firstIndex { $0.id == activeSentence.id }
                print("[AudioToggle] timeBasedIndex: found sentence id=\(activeSentence.id), index=\(index ?? -1)")
                return index
            }
        )

        let positionResult = positionProvider.currentSentenceIndex()
        if let result = positionResult {
            print("[AudioToggle] Captured position via \(result.strategy.rawValue): sentence \(result.index)")
        } else {
            print("[AudioToggle] WARNING: Failed to capture position!")
        }
        return positionResult?.index
    }

    /// Reconfigure audio playback based on AudioModeManager state.
    /// Called after toggling audio tracks to switch between sequence and single-track modes.
    /// - Parameter preservingSentence: The sentence index to preserve (already captured before toggle)
    func reconfigureAudioForCurrentToggles(preservingSentence currentSentenceIndex: Int? = nil) {
        guard let chunk = viewModel.selectedChunk else { return }

        print("[AudioToggle] Reconfiguring: mode=\(audioModeManager.currentMode.description), currentSentenceIndex=\(currentSentenceIndex ?? -1), time=\(String(format: "%.3f", viewModel.highlightingTime)), seqEnabled=\(viewModel.sequenceController.isEnabled)")

        guard let targetID = audioModeManager.resolvePreferredTrackID(for: chunk) else { return }

        // Sync audio mode to sequence controller BEFORE calling prepareAudio
        // This ensures buildPlan() sees the correct mode
        viewModel.sequenceController.audioMode = audioModeManager.currentMode

        if viewModel.selectedAudioTrackID != targetID {
            viewModel.selectedAudioTrackID = targetID
        }
        viewModel.prepareAudio(
            for: chunk,
            autoPlay: audioCoordinator.isPlaybackRequested,
            targetSentenceIndex: currentSentenceIndex
        )
    }

    func availableTracks(for chunk: InteractiveChunk) -> [TextPlayerVariantKind] {
        var available: [TextPlayerVariantKind] = []
        if chunk.sentences.contains(where: { !$0.originalTokens.isEmpty }) {
            available.append(.original)
        }
        if chunk.sentences.contains(where: { !$0.transliterationTokens.isEmpty }) {
            available.append(.transliteration)
        }
        if chunk.sentences.contains(where: { !$0.translationTokens.isEmpty }) {
            available.append(.translation)
        }
        if available.isEmpty {
            return [.original]
        }
        return available
    }

    func hasImageReel(for chunk: InteractiveChunk) -> Bool {
        chunk.sentences.contains { sentence in
            if let rawPath = sentence.imagePath, rawPath.nonEmptyValue != nil {
                return true
            }
            return false
        }
    }

    func applyDefaultTrackSelection(for chunk: InteractiveChunk) {
        let available = Set(availableTracks(for: chunk))
        if !hasCustomTrackSelection || visibleTracks.isEmpty {
            visibleTracks = available
        }
        if let showImageReel {
            showImageReel.wrappedValue = hasImageReel(for: chunk)
        }
    }

    var trackAvailabilitySignature: String {
        guard let chunk = viewModel.selectedChunk else { return "" }
        let available = availableTracks(for: chunk)
        return available.map(\.rawValue).sorted().joined(separator: "|")
    }

    func textTrackSummary(for chunk: InteractiveChunk) -> String {
        let available = availableTracks(for: chunk)
        let visible = available.filter { visibleTracks.contains($0) }
        var parts = visible.map { trackSummaryLabel($0) }
        let canShowImages = hasImageReel(for: chunk) && showImageReel != nil
        if canShowImages, let showImageReel, showImageReel.wrappedValue {
            parts.append("Images")
        }
        let allTextSelected = visible.count == available.count
        let allSelected = allTextSelected && (!canShowImages || showImageReel?.wrappedValue == true)
        if allSelected {
            return "All"
        }
        if parts.isEmpty {
            return "Text"
        }
        if parts.count == 1 {
            return parts[0]
        }
        return parts.joined(separator: " + ")
    }

    func playbackRateLabel(_ rate: Double) -> String {
        let rounded = (rate * 100).rounded() / 100
        let formatted = String(format: rounded.truncatingRemainder(dividingBy: 1) == 0 ? "%.0f" : "%.2f", rounded)
        return "\(formatted)x"
    }

    func isCurrentRate(_ rate: Double) -> Bool {
        abs(rate - audioCoordinator.playbackRate) < 0.01
    }

    /// Determines the preferred sequence track based on current audio toggle state.
    /// This controls which track to start at when skipping to a different sentence.
    /// Delegates to AudioModeManager for consistency.
    var preferredSequenceTrack: SequenceTrack? {
        audioModeManager.preferredTrack
    }

    /// Whether sequence mode should be enabled based on audio toggle state.
    /// Sequence mode only activates when BOTH original and translation are enabled.
    /// Delegates to AudioModeManager for consistency.
    var isSequenceModeEnabledByToggles: Bool {
        audioModeManager.isSequenceMode
    }

    /// Convenience accessors for UI bindings that need to check toggle state
    var showOriginalAudio: Bool {
        audioModeManager.isOriginalEnabled
    }

    var showTranslationAudio: Bool {
        audioModeManager.isTranslationEnabled
    }

    /// DEPRECATED: This function is no longer used.
    ///
    /// Text track visibility should NOT affect audio playback in sequence/combined mode.
    /// Audio track selection is controlled separately via the audio picker in the header.
    /// The shouldSkipTrack callback was causing issues where translation audio would be
    /// skipped even when both audio track pills were active, because the callback was
    /// set once at startup and captured stale visibility state.
    ///
    /// Instead, shouldSkipTrack is now set to nil in onAppear, ensuring both tracks
    /// always play in sequence mode regardless of which text tracks are visible.
    @available(*, deprecated, message: "Text visibility no longer affects audio playback")
    func updateShouldSkipTrackCallback() {
        // No-op: kept for reference but no longer used
        print("[TrackVisibility] updateShouldSkipTrackCallback called but is deprecated - doing nothing")
    }
}
