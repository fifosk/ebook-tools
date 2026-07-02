import SwiftUI
import OSLog

private let interactiveTracksLogger = Logger(subsystem: "InteractiveReader", category: "InteractiveTracks")

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
            toggleTrackIfAvailable(kind)
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
        if let selection = linguistSelection, !visibleTracks.contains(selection.variantKind) {
            linguistSelection = nil
            linguistSelectionRange = nil
        }
    }

    func toggleTrackIfAvailable(_ kind: TextPlayerVariantKind) {
        guard let chunk = viewModel.selectedChunk else { return }
        let available = availableTracks(for: chunk)
        guard available.contains(kind) else { return }
        let currentSentenceIndex = captureCurrentSentenceIndex(for: chunk)
        toggleTrack(kind)
        synchronizeAudioModeWithVisibleTextTracks(
            for: chunk,
            preservingSentence: currentSentenceIndex,
            allowExpandingSingleTrackAudio: true
        )
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
        alignVisibleTracksWithCurrentAudioMode(for: chunk, expandSequenceMode: true)

        // Reconfigure playback based on new toggle state
        reconfigureAudioForCurrentToggles(preservingSentence: currentSentenceIndex)
    }

    /// Capture the current sentence index using SentencePositionProvider
    /// - Parameter chunk: The current chunk
    /// - Returns: The current sentence index, or nil if not found
    func captureCurrentSentenceIndex(for chunk: InteractiveChunk) -> Int? {
        interactiveTracksLogger.debug(
            "Capturing position: seqEnabled=\(viewModel.sequenceController.isEnabled, privacy: .public), seqSentenceIdx=\(viewModel.sequenceController.currentSentenceIndex ?? -1, privacy: .public), highlightingTime=\(viewModel.highlightingTime, privacy: .public)"
        )

        let positionProvider = SentencePositionProvider.from(
            sequenceController: viewModel.sequenceController,
            transcriptDisplayIndex: { [self] in
                let display = activeSentenceDisplay(for: chunk)
                interactiveTracksLogger.debug("Transcript display index=\(display?.index ?? -1, privacy: .public)")
                return display?.index
            },
            timeBasedIndex: { [self] in
                guard let activeSentence = viewModel.activeSentence(at: viewModel.highlightingTime) else {
                    interactiveTracksLogger.debug("Time-based index: no active sentence found")
                    return nil
                }
                let index = chunk.sentences.firstIndex { $0.id == activeSentence.id }
                interactiveTracksLogger.debug(
                    "Time-based index found sentence id=\(activeSentence.id, privacy: .public), index=\(index ?? -1, privacy: .public)"
                )
                return index
            }
        )

        let positionResult = positionProvider.currentSentenceIndex()
        if let result = positionResult {
            interactiveTracksLogger.debug(
                "Captured position via \(result.strategy.rawValue, privacy: .public): sentence \(result.index, privacy: .public)"
            )
        } else {
            interactiveTracksLogger.warning("Failed to capture position")
        }
        return positionResult?.index
    }

    /// Reconfigure audio playback based on AudioModeManager state.
    /// Called after toggling audio tracks to switch between sequence and single-track modes.
    /// - Parameter preservingSentence: The sentence index to preserve (already captured before toggle)
    func reconfigureAudioForCurrentToggles(preservingSentence currentSentenceIndex: Int? = nil) {
        guard let chunk = viewModel.selectedChunk else { return }

        interactiveTracksLogger.debug(
            "Reconfiguring: mode=\(audioModeManager.currentMode.description, privacy: .public), currentSentenceIndex=\(currentSentenceIndex ?? -1, privacy: .public), time=\(viewModel.highlightingTime, privacy: .public), seqEnabled=\(viewModel.sequenceController.isEnabled, privacy: .public)"
        )

        viewModel.rememberAudioModePreference(audioModeManager.currentMode)

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

    func synchronizeAudioModeWithVisibleTextTracks(
        for chunk: InteractiveChunk,
        preservingSentence currentSentenceIndex: Int? = nil,
        allowExpandingSingleTrackAudio: Bool = false
    ) {
        let available = Set(availableTracks(for: chunk))
        let canUseOriginal = available.contains(.original)
        let canUseTranslation = available.contains(.translation)
        guard canUseOriginal || canUseTranslation else { return }

        let wantsOriginal = canUseOriginal && visibleTracks.contains(.original)
        let wantsTranslation = canUseTranslation && visibleTracks.contains(.translation)
        guard wantsOriginal || wantsTranslation else { return }

        if !allowExpandingSingleTrackAudio,
           wantsOriginal && wantsTranslation,
           let durableSingleTrack = viewModel.requestedSingleTrackMode() {
            let desiredTextTrack: TextPlayerVariantKind = durableSingleTrack == .original ? .original : .translation
            visibleTracks = [desiredTextTrack]
            hasCustomTrackSelection = true
            viewModel.applySingleTrackSelection(durableSingleTrack, for: chunk)
            reconfigureAudioForCurrentToggles(preservingSentence: currentSentenceIndex)
            return
        }

        guard wantsOriginal != audioModeManager.isOriginalEnabled
            || wantsTranslation != audioModeManager.isTranslationEnabled else {
            return
        }

        audioModeManager.setTracks(
            original: wantsOriginal,
            translation: wantsTranslation,
            preservingPosition: currentSentenceIndex
        )
        reconfigureAudioForCurrentToggles(preservingSentence: currentSentenceIndex)
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

    func prepareAudioModeForInitialPlayback(for chunk: InteractiveChunk) {
        viewModel.audioModeManager = audioModeManager
        viewModel.rememberAudioModePreference(
            audioModeManager.currentMode,
            clearSingleTrackOnSequence: false
        )
        let prefersCustomMultiTrackSelection = shouldPreferCustomMultiTrackSelection(for: chunk)
        let appliedResumeTrack = applyPendingResumeSingleTrackIfNeeded(for: chunk)
        let restoredViewModelSingleTrack: Bool
        if appliedResumeTrack || prefersCustomMultiTrackSelection {
            restoredViewModelSingleTrack = false
        } else {
            restoredViewModelSingleTrack = restoreSingleTrackModeFromViewModelPreferenceIfNeeded(for: chunk)
        }
        if !appliedResumeTrack && !restoredViewModelSingleTrack {
            viewModel.sequenceController.audioMode = audioModeManager.currentMode
        }
        let restoredVisibleSingleTrack: Bool
        if appliedResumeTrack || restoredViewModelSingleTrack || prefersCustomMultiTrackSelection {
            restoredVisibleSingleTrack = false
        } else {
            restoredVisibleSingleTrack = restoreSingleTrackModeFromVisibleSelectionIfNeeded(for: chunk)
        }
        let preservedSingleTrack = appliedResumeTrack
            || restoredViewModelSingleTrack
            || restoredVisibleSingleTrack
            || (!prefersCustomMultiTrackSelection && preserveSingleTrackModeIfNeeded(for: chunk))
        if !preservedSingleTrack {
            applyDefaultTrackSelection(for: chunk)
            synchronizeAudioModeWithVisibleTextTracks(
                for: chunk,
                allowExpandingSingleTrackAudio: prefersCustomMultiTrackSelection
            )
        }
        viewModel.sequenceController.audioMode = audioModeManager.currentMode
        viewModel.synchronizeSelectedAudioTrackForChunkHandoff(for: chunk)
        if viewModel.selectedAudioTrackID == nil,
           let targetID = audioModeManager.resolvePreferredTrackID(for: chunk) {
            viewModel.selectedAudioTrackID = targetID
        }
    }

    func shouldPreferCustomMultiTrackSelection(for chunk: InteractiveChunk) -> Bool {
        guard hasCustomTrackSelection else { return false }
        let available = Set(availableTracks(for: chunk))
        guard available.contains(.original), available.contains(.translation) else { return false }
        return visibleTracks.contains(.original) && visibleTracks.contains(.translation)
    }

    @discardableResult
    func restoreSingleTrackModeFromViewModelPreferenceIfNeeded(for chunk: InteractiveChunk) -> Bool {
        guard let requestedTrack = viewModel.lifecycleSingleTrackRestoreMode(in: chunk) else { return false }

        let desiredTextTrack: TextPlayerVariantKind = requestedTrack == .original ? .original : .translation
        let available = Set(availableTracks(for: chunk))
        guard available.contains(desiredTextTrack) || chunkSupportsAudioTrack(requestedTrack, in: chunk) else {
            return false
        }

        visibleTracks = [desiredTextTrack]
        hasCustomTrackSelection = true
        audioModeManager.setTracks(
            original: requestedTrack == .original,
            translation: requestedTrack == .translation
        )
        viewModel.rememberAudioModePreference(audioModeManager.currentMode)
        viewModel.sequenceController.audioMode = audioModeManager.currentMode
        viewModel.applySingleTrackSelection(requestedTrack, for: chunk)
        return true
    }

    @discardableResult
    func restoreSingleTrackModeFromVisibleSelectionIfNeeded(for chunk: InteractiveChunk) -> Bool {
        guard hasCustomTrackSelection, visibleTracks.count == 1 else { return false }
        guard let onlyTrack = visibleTracks.first else { return false }
        let requestedTrack: SequenceTrack?
        switch onlyTrack {
        case .original:
            requestedTrack = .original
        case .translation:
            requestedTrack = .translation
        case .transliteration:
            requestedTrack = nil
        }
        guard let requestedTrack else { return false }

        let available = Set(availableTracks(for: chunk))
        guard available.contains(onlyTrack) || chunkSupportsAudioTrack(requestedTrack, in: chunk) else {
            return false
        }

        audioModeManager.setTracks(
            original: requestedTrack == .original,
            translation: requestedTrack == .translation
        )
        viewModel.rememberAudioModePreference(audioModeManager.currentMode)
        viewModel.sequenceController.audioMode = audioModeManager.currentMode
        viewModel.applySingleTrackSelection(requestedTrack, for: chunk)
        return true
    }

    @discardableResult
    func preserveSingleTrackModeIfNeeded(for chunk: InteractiveChunk) -> Bool {
        guard let track = viewModel.requestedSingleTrackMode() else { return false }

        let desiredTextTrack: TextPlayerVariantKind = track == .original ? .original : .translation
        let available = Set(availableTracks(for: chunk))
        guard available.contains(desiredTextTrack) || chunkSupportsAudioTrack(track, in: chunk) else { return false }

        visibleTracks = [desiredTextTrack]
        hasCustomTrackSelection = true
        viewModel.applySingleTrackSelection(track, for: chunk)
        return true
    }

    @discardableResult
    func alignVisibleTracksWithCurrentAudioMode(
        for chunk: InteractiveChunk,
        expandSequenceMode: Bool = false
    ) -> Bool {
        switch audioModeManager.currentMode {
        case .singleTrack(let track):
            let desiredTextTrack: TextPlayerVariantKind = track == .original ? .original : .translation
            let available = Set(availableTracks(for: chunk))
            guard available.contains(desiredTextTrack) || chunkSupportsAudioTrack(track, in: chunk) else {
                return false
            }
            guard visibleTracks != [desiredTextTrack] || !hasCustomTrackSelection else {
                return false
            }
            visibleTracks = [desiredTextTrack]
            hasCustomTrackSelection = true
            if let targetID = audioModeManager.resolvePreferredTrackID(for: chunk) {
                viewModel.selectedAudioTrackID = targetID
            }
            return true

        case .sequence:
            guard expandSequenceMode else { return false }
            let available = Set(availableTracks(for: chunk))
            guard !available.isEmpty, visibleTracks != available || hasCustomTrackSelection else {
                return false
            }
            visibleTracks = available
            hasCustomTrackSelection = false
            if let targetID = audioModeManager.resolvePreferredTrackID(for: chunk) {
                viewModel.selectedAudioTrackID = targetID
            }
            return true
        }
    }

    @discardableResult
    func applyPendingResumeSingleTrackIfNeeded(for chunk: InteractiveChunk) -> Bool {
        guard let resumeTrack = viewModel.pendingResumeSingleTrack else { return false }
        viewModel.pendingResumeSingleTrack = nil

        let desiredTextTrack: TextPlayerVariantKind = resumeTrack == .original ? .original : .translation
        let available = Set(availableTracks(for: chunk))
        guard available.contains(desiredTextTrack) || chunkSupportsAudioTrack(resumeTrack, in: chunk) else { return false }

        visibleTracks = [desiredTextTrack]
        hasCustomTrackSelection = true
        viewModel.applySingleTrackSelection(resumeTrack, for: chunk)
        return true
    }

    func chunkSupportsAudioTrack(_ track: SequenceTrack, in chunk: InteractiveChunk) -> Bool {
        let dedicatedKind: InteractiveChunk.AudioOption.Kind = track == .original ? .original : .translation
        if chunk.audioOptions.contains(where: { $0.kind == dedicatedKind }) {
            return true
        }
        return chunk.audioOptions.contains { option in
            guard option.kind == .combined else { return false }
            return !option.streamURLs.isEmpty
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
}
