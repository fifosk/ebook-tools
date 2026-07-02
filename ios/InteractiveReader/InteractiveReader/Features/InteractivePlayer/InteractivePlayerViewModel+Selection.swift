import Foundation
import SwiftUI
import Combine
import OSLog

private let interactiveSelectionLogger = Logger(
    subsystem: "InteractiveReader",
    category: "InteractiveSelection"
)

private let recentSingleTrackSentenceAnchorLifetime: TimeInterval = 60.0

extension InteractivePlayerViewModel {
    func prepareResumeSingleTrack(_ track: SequenceTrack?) {
        pendingResumeSingleTrack = track
        preferredSingleTrackMode = track
        durableSingleTrackPlaybackMode = track
        guard let track, let audioModeManager else { return }
        audioModeManager.setTracks(
            original: track == .original,
            translation: track == .translation
        )
        sequenceController.audioMode = audioModeManager.currentMode
    }

    func rememberAudioModePreference(
        _ mode: AudioMode,
        clearSingleTrackOnSequence: Bool = true
    ) {
        switch mode {
        case .singleTrack(let track):
            preferredSingleTrackMode = track
            durableSingleTrackPlaybackMode = track
        case .sequence:
            if clearSingleTrackOnSequence {
                preferredSingleTrackMode = nil
                durableSingleTrackPlaybackMode = nil
                loadedSingleTrackPlaybackMode = nil
                selectedTimingSingleTrackMode = nil
            }
        }
    }

    /// Check if chunk sentences have gate data needed for combined (sequence) mode
    private func sentencesHaveGateData(_ sentences: [InteractiveChunk.Sentence]) -> Bool {
        guard let first = sentences.first else { return false }
        // Gate data is required for sequence playback - check if any gate fields are populated
        return first.originalStartGate != nil || first.startGate != nil
    }

    /// Check if chunk sentences have tokens loaded (required for transcript display)
    private func sentencesHaveTokens(_ sentences: [InteractiveChunk.Sentence]) -> Bool {
        sentences.contains(where: sentenceHasRenderableTokens)
    }

    /// Check if the currently selected track requires gate data (combined mode)
    private func selectedTrackRequiresGates(for chunk: InteractiveChunk) -> Bool {
        if let audioModeManager, !audioModeManager.isSequenceMode {
            return false
        }
        guard let trackID = selectedAudioTrackID,
              let track = chunk.audioOptions.first(where: { $0.id == trackID }) else {
            return false
        }
        return track.kind == .combined
    }

    func isTranscriptReady(for chunk: InteractiveChunk) -> Bool {
        !chunk.sentences.isEmpty
            && sentencesHaveTokens(chunk.sentences)
            && (!selectedTrackRequiresGates(for: chunk) || sentencesHaveGateData(chunk.sentences))
    }

    func isSentenceReadyForDisplay(in chunk: InteractiveChunk, targetIndex: Int?) -> Bool {
        guard isTranscriptReady(for: chunk) else { return false }
        guard let targetIndex else { return true }
        guard chunk.sentences.indices.contains(targetIndex) else { return false }
        return sentenceHasRenderableTokens(chunk.sentences[targetIndex])
    }

    private func sentenceHasRenderableTokens(_ sentence: InteractiveChunk.Sentence) -> Bool {
        !sentence.originalTokens.isEmpty
            || !sentence.translationTokens.isEmpty
            || !sentence.transliterationTokens.isEmpty
    }

    /// Select a chunk for playback
    /// - Parameters:
    ///   - id: The chunk ID to select
    ///   - autoPlay: Whether to start playback automatically
    ///   - targetSentenceIndex: Optional 0-based sentence index to start from. Use -1 to mean "last sentence".
    func selectChunk(id: String, autoPlay: Bool = false, targetSentenceIndex: Int? = nil) {
        let isTargetedJump = targetSentenceIndex != nil || pendingSentenceJump?.chunkID == id || pendingTimeSeek?.chunkID == id
        if selectedChunkID == id, !isTargetedJump, !autoPlay {
            return
        }
        if isTargetedJump, audioCoordinator.isPlaybackRequested || audioCoordinator.isPlaying || autoPlay {
            audioCoordinator.pauseForDwell()
        }
        let incomingChunk = jobContext?.chunk(withID: id)
        if let incomingChunk {
            synchronizeSelectedAudioTrackForChunkHandoff(for: incomingChunk)
        }
        selectedChunkID = id
        if recentSingleTrackSentenceAnchor?.chunkID != id {
            recentSingleTrackSentenceAnchor = nil
        }
        lastPrefetchSentenceNumber = nil
        prefetchDirection = .none
        guard let chunk = incomingChunk ?? selectedChunk else {
            audioCoordinator.reset()
            selectedTimingURL = nil
            return
        }
        synchronizeSelectedAudioTrackForChunkHandoff(for: chunk)
        // If chunk has sentences with complete data, prepare audio immediately
        // For combined mode, we need gate data - if missing, load metadata first
        // Also require tokens to be loaded for proper transcript display
        let hasGates = sentencesHaveGateData(chunk.sentences)
        let hasTokens = sentencesHaveTokens(chunk.sentences)
        let needsGates = selectedTrackRequiresGates(for: chunk)
        rememberSingleTrackBatchStartAnchorIfNeeded(
            for: chunk,
            targetSentenceIndex: targetSentenceIndex,
            autoPlay: autoPlay
        )
        interactiveSelectionLogger.debug(
            "Configure defaults: chunk=\(chunk.id, privacy: .private), sentences=\(chunk.sentences.count, privacy: .public), hasGates=\(hasGates, privacy: .public), hasTokens=\(hasTokens, privacy: .public), needsGates=\(needsGates, privacy: .public)"
        )
        if isTranscriptReady(for: chunk) {
            isTranscriptLoading = false
            let effectiveTargetIndex: Int? = {
                let target = SentencePositionProvider.targetSentenceIndex(
                    in: chunk,
                    explicitIndex: targetSentenceIndex,
                    pendingJump: pendingSentenceJump
                )
                guard let target else { return nil }
                if target < 0 {
                    return max(0, chunk.sentences.count - 1)
                }
                return target
            }()
            rememberSingleTrackSentenceAnchor(in: chunk, targetIndex: effectiveTargetIndex)
            prepareAudio(for: chunk, autoPlay: autoPlay, targetSentenceIndex: effectiveTargetIndex)
            attemptPendingSentenceJump(in: chunk)
            attemptPendingTimeSeek(in: chunk)
            return
        }
        // Mark transcript as loading while we fetch metadata
        isTranscriptLoading = true
        // Load metadata before starting playback to ensure transcript is ready
        Task { [weak self] in
            guard let self else { return }
            let didLoad = await self.loadChunkMetadataIfNeeded(for: chunk.id, force: true)
            // Prepare audio after metadata is loaded
            guard self.selectedChunkID == id else { return }
            // Get the UPDATED chunk after metadata loaded (may have new sentences)
            guard let updatedChunk = self.selectedChunk else { return }
            // Clear loading state now that we have the transcript
            self.isTranscriptLoading = false
            let effectiveTargetIndex: Int? = {
                let target = SentencePositionProvider.targetSentenceIndex(
                    in: updatedChunk,
                    explicitIndex: targetSentenceIndex,
                    pendingJump: self.pendingSentenceJump
                )
                guard let target else { return nil }
                if target < 0 {
                    return max(0, updatedChunk.sentences.count - 1)
                }
                return target
            }()
            self.rememberSingleTrackSentenceAnchor(in: updatedChunk, targetIndex: effectiveTargetIndex)
            self.synchronizeSelectedAudioTrackForChunkHandoff(for: updatedChunk)
            // Only start audio if transcript is now available. This prevents
            // jumps from playing audio while the view still shows the spinner.
            guard didLoad, self.isSentenceReadyForDisplay(in: updatedChunk, targetIndex: effectiveTargetIndex) else {
                return
            }
            self.prepareAudio(for: updatedChunk, autoPlay: autoPlay, targetSentenceIndex: effectiveTargetIndex)
            self.attemptPendingSentenceJump(in: updatedChunk)
            self.attemptPendingTimeSeek(in: updatedChunk)
        }
    }

    func selectAudioTrack(id: String) {
        let previousTrackID = selectedAudioTrackID
        selectedAudioTrackID = id
        guard let chunk = selectedChunk else { return }
        if let track = chunk.audioOptions.first(where: { $0.id == id }) {
            let modeWasAlreadyAligned = audioModeMatchesSelectedTrack(track)
            preferredAudioKind = track.kind
            applyAudioModePreference(for: track)
            if previousTrackID == id,
               modeWasAlreadyAligned {
                return
            }
            // If switching to combined mode and sentences lack gate data, load metadata first
            if track.kind == .combined && !sentencesHaveGateData(chunk.sentences) {
                Task { [weak self] in
                    guard let self else { return }
                    await self.loadChunkMetadataIfNeeded(for: chunk.id, force: true)
                    guard self.selectedAudioTrackID == id else { return }
                    guard let updatedChunk = self.selectedChunk else { return }
                    self.prepareAudio(for: updatedChunk, autoPlay: self.audioCoordinator.isPlaybackRequested)
                }
                return
            }
        }
        prepareAudio(for: chunk, autoPlay: audioCoordinator.isPlaybackRequested)
    }

    private func applyAudioModePreference(for track: InteractiveChunk.AudioOption) {
        switch track.kind {
        case .original:
            preferredSingleTrackMode = .original
            durableSingleTrackPlaybackMode = .original
            if let audioModeManager {
                audioModeManager.setTracks(original: true, translation: false)
                sequenceController.audioMode = audioModeManager.currentMode
            } else {
                sequenceController.audioMode = .singleTrack(.original)
            }
        case .translation:
            preferredSingleTrackMode = .translation
            durableSingleTrackPlaybackMode = .translation
            if let audioModeManager {
                audioModeManager.setTracks(original: false, translation: true)
                sequenceController.audioMode = audioModeManager.currentMode
            } else {
                sequenceController.audioMode = .singleTrack(.translation)
            }
        case .combined:
            preferredSingleTrackMode = nil
            durableSingleTrackPlaybackMode = nil
            loadedSingleTrackPlaybackMode = nil
            selectedTimingSingleTrackMode = nil
            if let audioModeManager {
                audioModeManager.enableSequenceMode()
                sequenceController.audioMode = audioModeManager.currentMode
            } else {
                sequenceController.audioMode = .sequence
            }
        case .other:
            break
        }
    }

    private func audioModeMatchesSelectedTrack(_ track: InteractiveChunk.AudioOption) -> Bool {
        switch track.kind {
        case .original:
            return concreteAudioModeTrack() == .original
        case .translation:
            return concreteAudioModeTrack() == .translation
        case .combined:
            return concreteAudioModeTrack() == nil
        case .other:
            return true
        }
    }

    private func concreteAudioModeTrack() -> SequenceTrack? {
        if let audioModeManager {
            if case .singleTrack(let track) = audioModeManager.currentMode {
                return track
            }
            return nil
        }
        if case .singleTrack(let track) = sequenceController.audioMode {
            return track
        }
        return preferredSingleTrackMode
    }

    var selectedChunk: InteractiveChunk? {
        guard let context = jobContext else { return nil }
        if let id = selectedChunkID, let chunk = context.chunk(withID: id) {
            return chunk
        }
        return context.chunks.first
    }

    var currentAudioOptions: [InteractiveChunk.AudioOption] {
        selectedChunk?.audioOptions ?? []
    }

    func chunkBinding() -> Binding<String> {
        Binding(
            get: {
                self.selectedChunkID ?? self.jobContext?.chunks.first?.id ?? ""
            },
            set: { newValue in
                self.selectChunk(id: newValue, autoPlay: self.audioCoordinator.isPlaybackRequested)
            }
        )
    }

    func audioTrackBinding(defaultID: String?) -> Binding<String> {
        Binding(
            get: {
                self.selectedAudioTrackID ?? defaultID ?? ""
            },
            set: { newValue in
                self.selectAudioTrack(id: newValue)
            }
        )
    }

    func configureDefaultSelections() {
        guard let context = jobContext else { return }
        lastPrefetchSentenceNumber = nil
        prefetchDirection = .none
        if let chunk = context.chunks.first(where: { !$0.audioOptions.isEmpty }) ?? context.chunks.first {
            selectedChunkID = chunk.id
            synchronizeSelectedAudioTrackForChunkHandoff(for: chunk)
            if let selectedAudioTrackID,
               let option = chunk.audioOptions.first(where: { $0.id == selectedAudioTrackID }) {
                preferredAudioKind = preferredAudioKindForCurrentMode(fallback: option.kind)
            } else if let option = chunk.audioOptions.first {
                selectedAudioTrackID = option.id
                preferredAudioKind = preferredAudioKindForCurrentMode(fallback: option.kind)
            } else {
                selectedAudioTrackID = nil
            }
            // If chunk has sentences with complete data, prepare audio immediately
            // For combined mode (default), we need gate data - if missing, load metadata first
            // Also require tokens to be loaded for proper transcript display
            let hasGates = sentencesHaveGateData(chunk.sentences)
            let hasTokens = sentencesHaveTokens(chunk.sentences)
            let needsGates = selectedTrackRequiresGates(for: chunk)
            interactiveSelectionLogger.debug(
                "Configure defaults: chunk=\(chunk.id, privacy: .private), sentences=\(chunk.sentences.count, privacy: .public), hasGates=\(hasGates, privacy: .public), hasTokens=\(hasTokens, privacy: .public), needsGates=\(needsGates, privacy: .public)"
            )
            if isTranscriptReady(for: chunk) {
                isTranscriptLoading = false
                prepareAudio(for: chunk, autoPlay: false)
                return
            }
            // Mark transcript as loading while we fetch metadata
            isTranscriptLoading = true
            interactiveSelectionLogger.debug("Configure defaults: loading metadata for chunk=\(chunk.id, privacy: .private)")
            // Load metadata before preparing audio to ensure transcript is ready
            let chunkId = chunk.id
            Task { [weak self] in
                guard let self else { return }
                let didLoad = await self.loadChunkMetadataIfNeeded(for: chunkId, force: true)
                guard self.selectedChunkID == chunkId else { return }
                // Get the UPDATED chunk after metadata loaded (may have new sentences)
                guard let updatedChunk = self.selectedChunk else {
                    interactiveSelectionLogger.debug("Configure defaults: no updated chunk after metadata load")
                    return
                }
                interactiveSelectionLogger.debug(
                    "Configure defaults: after metadata sentences=\(updatedChunk.sentences.count, privacy: .public)"
                )
                // Clear loading state now that we have the transcript
                self.isTranscriptLoading = false
                // Only prepare audio if transcript is now available
                guard didLoad, self.isTranscriptReady(for: updatedChunk) else {
                    interactiveSelectionLogger.debug("Configure defaults: still no sentences after metadata load")
                    return
                }
                self.synchronizeSelectedAudioTrackForChunkHandoff(for: updatedChunk)
                self.prepareAudio(for: updatedChunk, autoPlay: false)
            }
        } else {
            selectedChunkID = nil
            selectedAudioTrackID = nil
            audioCoordinator.reset()
            selectedTimingURL = nil
            preferredAudioKind = nil
            isTranscriptLoading = false
        }
    }

    func synchronizeSelectedAudioTrackWithCurrentMode(for chunk: InteractiveChunk) {
        guard let audioModeManager,
              let targetID = audioModeManager.resolvePreferredTrackID(for: chunk),
              let targetOption = chunk.audioOptions.first(where: { $0.id == targetID }) else {
            return
        }
        selectedAudioTrackID = targetID
        preferredAudioKind = preferredAudioKindForCurrentMode(
            fallback: targetOption.kind
        )
        if case .singleTrack(let track) = audioModeManager.currentMode {
            preferredSingleTrackMode = track
        }
        sequenceController.audioMode = audioModeManager.currentMode
    }

    func requestedSingleTrackMode() -> SequenceTrack? {
        if let loadedSingleTrackPlaybackMode {
            return loadedSingleTrackPlaybackMode
        }
        if let preferredSingleTrackMode {
            return preferredSingleTrackMode
        }
        if let durableSingleTrackPlaybackMode {
            return durableSingleTrackPlaybackMode
        }
        if let chunk = selectedChunk,
           let selectedTimingSingleTrack = selectedTimingSingleTrackMode(in: chunk) {
            return selectedTimingSingleTrack
        }
        if let audioModeManager,
           case .singleTrack(let track) = audioModeManager.currentMode {
            return track
        }
        if case .singleTrack(let track) = sequenceController.audioMode {
            return track
        }
        if let chunk = selectedChunk,
           let selectedAudioTrackID,
           let selectedOption = chunk.audioOptions.first(where: { $0.id == selectedAudioTrackID }) {
            switch selectedOption.kind {
            case .original:
                return .original
            case .translation:
                return .translation
            case .combined, .other:
                break
            }
        }
        switch preferredAudioKind {
        case .original:
            return .original
        case .translation:
            return .translation
        case .combined, .other, .none:
            break
        }
        if let track = loadedSingleURLTrackMode() {
            return track
        }
        return nil
    }

    private func loadedSingleURLTrackMode() -> SequenceTrack? {
        guard !sequenceController.isEnabled,
              sequenceController.plan.isEmpty,
              let chunk = selectedChunk,
              audioCoordinator.activeURLs.count == 1,
              let activeURL = audioCoordinator.activeURLs.first else {
            return nil
        }
        return singleTrackMode(forAudioURL: activeURL, in: chunk)
    }

    private func singleTrackMode(forAudioURL url: URL, in chunk: InteractiveChunk) -> SequenceTrack? {
        if chunk.audioOptions.contains(where: { $0.kind == .original && $0.streamURLs.contains(url) }) {
            return .original
        }
        if chunk.audioOptions.contains(where: { $0.kind == .translation && $0.streamURLs.contains(url) }) {
            return .translation
        }
        if let combined = chunk.audioOptions.first(where: { $0.kind == .combined }) {
            if combined.streamURLs.first == url {
                return .original
            }
            if combined.streamURLs.dropFirst().contains(url) {
                return .translation
            }
        }
        return nil
    }

    func synchronizeSelectedAudioTrackForChunkHandoff(for chunk: InteractiveChunk) {
        if let track = requestedSingleTrackMode() {
            applySingleTrackSelection(track, for: chunk)
            preferredSingleTrackMode = track
            durableSingleTrackPlaybackMode = track
            return
        }
        synchronizeSelectedAudioTrackWithCurrentMode(for: chunk)
        repairSelectedAudioTrackIfNeeded(for: chunk)
    }

    @discardableResult
    func reassertSelectedAudioTrackAfterContextRebuild() -> Bool {
        guard let chunk = selectedChunk else { return false }
        let previousTrackID = selectedAudioTrackID
        let previousPreferredKind = preferredAudioKind
        let previousAudioMode = sequenceController.audioMode

        synchronizeSelectedAudioTrackForChunkHandoff(for: chunk)

        let changed = previousTrackID != selectedAudioTrackID
            || previousPreferredKind != preferredAudioKind
            || previousAudioMode != sequenceController.audioMode
        if changed {
            interactiveSelectionLogger.debug(
                "Context rebuild reasserted audio selection chunk=\(chunk.id, privacy: .private), trackID=\(self.selectedAudioTrackID ?? "nil", privacy: .private), mode=\(self.sequenceController.audioMode.description, privacy: .public)"
            )
        }
        return changed
    }

    func reprepareSingleTrackAudioAfterContextRebuildIfNeeded(autoPlay: Bool) {
        guard let updatedChunk = selectedChunk,
              requestedSingleTrackMode() != nil else {
            return
        }
        guard let targetIndex = recentSingleTrackSentenceAnchorIndex(in: updatedChunk) else {
            return
        }
        rememberSingleTrackSentenceAnchor(in: updatedChunk, targetIndex: targetIndex)
        prepareAudio(
            for: updatedChunk,
            autoPlay: autoPlay,
            targetSentenceIndex: targetIndex
        )
    }

    func applySingleTrackSelection(_ track: SequenceTrack, for chunk: InteractiveChunk) {
        preferredSingleTrackMode = track
        durableSingleTrackPlaybackMode = track
        loadedSingleTrackPlaybackMode = track
        if let audioModeManager {
            audioModeManager.setTracks(
                original: track == .original,
                translation: track == .translation
            )
            sequenceController.audioMode = audioModeManager.currentMode
            synchronizeSelectedAudioTrackWithCurrentMode(for: chunk)
            if chunk.audioOptions.contains(where: { $0.id == selectedAudioTrackID }) {
                return
            }
        } else {
            sequenceController.audioMode = .singleTrack(track)
        }

        preferredAudioKind = track == .original ? .original : .translation
        selectedAudioTrackID = preferredSingleTrackAudioOption(for: track, in: chunk)?.id
    }

    private func preferredSingleTrackAudioOption(
        for track: SequenceTrack,
        in chunk: InteractiveChunk
    ) -> InteractiveChunk.AudioOption? {
        let dedicatedKind: InteractiveChunk.AudioOption.Kind = track == .original ? .original : .translation
        if let dedicated = chunk.audioOptions.first(where: { $0.kind == dedicatedKind }) {
            return dedicated
        }
        if let combined = chunk.audioOptions.first(where: { $0.kind == .combined }) {
            return combined
        }
        return chunk.audioOptions.first
    }

    func repairSelectedAudioTrackIfNeeded(for chunk: InteractiveChunk) {
        if chunk.audioOptions.contains(where: { $0.id == selectedAudioTrackID }) {
            return
        }
        if let track = requestedSingleTrackMode() {
            applySingleTrackSelection(track, for: chunk)
            return
        }
        let preferred = preferredAudioKind.flatMap { kind in
            chunk.audioOptions.first(where: { $0.kind == kind })
        }
        selectedAudioTrackID = preferred?.id ?? chunk.audioOptions.first?.id
    }

    private func preferredAudioKindForCurrentMode(
        fallback: InteractiveChunk.AudioOption.Kind
    ) -> InteractiveChunk.AudioOption.Kind {
        guard let audioModeManager else { return fallback }
        switch audioModeManager.currentMode {
        case .sequence:
            return fallback == .combined ? .combined : fallback
        case .singleTrack(.original):
            return .original
        case .singleTrack(.translation):
            return .translation
        }
    }

    func prepareAudio(for chunk: InteractiveChunk, autoPlay: Bool, targetSentenceIndex: Int? = nil) {
        interactiveSelectionLogger.debug(
            "Prepare audio: targetSentenceIndex=\(targetSentenceIndex ?? -1, privacy: .public), autoPlay=\(autoPlay, privacy: .public)"
        )

        reassertSingleTrackPlaybackLane(for: chunk)

        guard let mgr = audioModeManager,
              let instruction = mgr.resolveAudioInstruction(for: chunk, selectedTrackID: selectedAudioTrackID) else {
            interactiveSelectionLogger.debug("Prepare audio guard failed: no track found or no audio mode manager")
            audioCoordinator.reset()
            sequenceController.reset()
            selectedTimingURL = nil
            return
        }

        interactiveSelectionLogger.debug(
            "Prepare audio: instruction=\(String(describing: instruction), privacy: .public), mode=\(mgr.currentMode.description, privacy: .public)"
        )

        switch instruction {
        case .sequence:
            prepareSequenceAudio(for: chunk, autoPlay: autoPlay, targetSentenceIndex: targetSentenceIndex)

        case .singleOption, .singleURL:
            prepareSingleTrackAudio(
                instruction,
                for: chunk,
                autoPlay: autoPlay,
                targetSentenceIndex: targetSentenceIndex
            )
        }
    }

    /// Prepare sequence-mode audio with a target sentence resolved from explicit jumps first, then pending jumps.
    private func prepareSequenceAudio(
        for chunk: InteractiveChunk,
        autoPlay: Bool,
        targetSentenceIndex: Int?
    ) {
        loadedSingleTrackPlaybackMode = nil
        selectedTimingSingleTrackMode = nil
        let effectiveTargetIndex = resolvedSequenceTargetIndex(for: chunk, targetSentenceIndex: targetSentenceIndex)
        interactiveSelectionLogger.debug(
            "Prepare audio: taking sequence path effectiveTargetIndex=\(effectiveTargetIndex ?? -1, privacy: .public)"
        )
        configureSequencePlayback(for: chunk, autoPlay: autoPlay, targetSentenceIndex: effectiveTargetIndex)
    }

    private func resolvedSequenceTargetIndex(
        for chunk: InteractiveChunk,
        targetSentenceIndex: Int?
    ) -> Int? {
        SentencePositionProvider.targetSentenceIndex(
            in: chunk,
            explicitIndex: targetSentenceIndex,
            pendingJump: pendingSentenceJump
        )
    }

    /// Prepare a single-track audio instruction without changing the sequence-mode branch.
    private func prepareSingleTrackAudio(
        _ instruction: ResolvedAudioInstruction,
        for chunk: InteractiveChunk,
        autoPlay: Bool,
        targetSentenceIndex: Int?
    ) {
        if sequenceController.isEnabled || !sequenceController.plan.isEmpty {
            sequenceController.reset()
        }

        switch instruction {
        case .sequence:
            return

        case .singleOption(let option, _):
            // Check if already playing the same URLs (prevent unnecessary reload from SwiftUI re-renders)
            if audioCoordinator.activeURLs == option.streamURLs {
                handleSameURLPlayback(
                    autoPlay: autoPlay,
                    targetSentenceIndex: targetSentenceIndex,
                    chunk: chunk,
                    timingURL: option.timingURL ?? option.streamURLs.first
                )
                return
            }
            loadSingleTrack(
                urls: option.streamURLs,
                timingURL: option.timingURL ?? option.streamURLs.first,
                autoPlay: autoPlay,
                targetSentenceIndex: targetSentenceIndex,
                chunk: chunk
            )

        case .singleURL(let url, _):
            loadSingleTrack(
                urls: [url],
                timingURL: url,
                autoPlay: autoPlay,
                targetSentenceIndex: targetSentenceIndex,
                chunk: chunk
            )
        }
    }

    /// Handle the case where the same URLs are already loaded (prevent unnecessary reload).
    private func handleSameURLPlayback(
        autoPlay: Bool,
        targetSentenceIndex: Int?,
        chunk: InteractiveChunk,
        timingURL: URL?
    ) {
        if sequenceController.isEnabled || !sequenceController.plan.isEmpty {
            interactiveSelectionLogger.debug("Prepare audio: resetting sequence controller for same-URL single-track mode")
            sequenceController.reset()
        }
        loadedSingleTrackPlaybackMode = reassertSingleTrackPlaybackLane(for: chunk)
        selectedTimingSingleTrackMode = loadedSingleTrackPlaybackMode
        selectedTimingURL = timingURL
        if let targetIndex = targetSentenceIndex,
           targetIndex >= 0,
           targetIndex < chunk.sentences.count,
           startTimeForSentence(atIndex: targetIndex, in: chunk) != nil {
            seekSingleTrackSentenceWhenReady(
                targetIndex,
                in: chunk,
                autoPlay: autoPlay
            )
            return
        }
        if autoPlay && !audioCoordinator.isPlaying {
            audioCoordinator.play()
        }
    }

    /// Load a single track (non-sequence mode) with optional seek to target sentence.
    private func loadSingleTrack(
        urls: [URL],
        timingURL: URL?,
        autoPlay: Bool,
        targetSentenceIndex: Int?,
        chunk: InteractiveChunk
    ) {
        sequenceController.reset()
        loadedSingleTrackPlaybackMode = reassertSingleTrackPlaybackLane(for: chunk)
        selectedTimingSingleTrackMode = loadedSingleTrackPlaybackMode
        let needsSeek = targetSentenceIndex != nil && targetSentenceIndex! >= 0 && targetSentenceIndex! < chunk.sentences.count
        audioCoordinator.load(
            urls: urls,
            autoPlay: needsSeek ? false : autoPlay,
            forceNoAutoPlay: needsSeek,
            preservePlaybackRequested: needsSeek
        )
        selectedTimingURL = timingURL
        if needsSeek, let targetIndex = targetSentenceIndex {
            rememberSingleTrackSentenceAnchor(in: chunk, targetIndex: targetIndex)
            seekToSentenceAfterLoad(targetIndex, in: chunk, autoPlay: autoPlay)
        }
    }

    @discardableResult
    private func reassertSingleTrackPlaybackLane(for chunk: InteractiveChunk) -> SequenceTrack? {
        guard let track = requestedSingleTrackMode() else { return nil }
        applySingleTrackSelection(track, for: chunk)
        return track
    }

    func handlePlaybackEnded(endedURL: URL? = nil) {
        guard let chunk = selectedChunk,
              let nextChunk = jobContext?.nextChunk(after: chunk.id) else {
            // No next chunk — end of book. Stop narration audio so the reading bed
            // observes isPlaybackRequested == false and pauses.
            audioCoordinator.pause()
            return
        }
        if let endedURL,
           !playbackEndedURLBelongsToCurrentChunk(endedURL, chunk: chunk) {
            interactiveSelectionLogger.debug(
                "Ignoring stale playback-ended callback url=\(endedURL.lastPathComponent, privacy: .private), chunk=\(chunk.id, privacy: .private), selectedTrackID=\(self.selectedAudioTrackID ?? "nil", privacy: .private)"
            )
            return
        }
        let preservedSingleTrack = singleTrackModeForCompletedPlayback(
            endedURL: endedURL,
            in: chunk
        )
        if let preservedSingleTrack {
            preferredSingleTrackMode = preservedSingleTrack
            durableSingleTrackPlaybackMode = preservedSingleTrack
            loadedSingleTrackPlaybackMode = preservedSingleTrack
        }
        selectChunkPreservingAudioLane(
            nextChunk,
            autoPlay: true,
            targetSentenceIndex: 0,
            preservedSingleTrack: preservedSingleTrack
        )
    }

    private func singleTrackModeForCompletedPlayback(
        endedURL: URL?,
        in chunk: InteractiveChunk
    ) -> SequenceTrack? {
        if let track = requestedSingleTrackMode() {
            return track
        }
        guard !sequenceController.isEnabled else { return nil }
        if let selectedTimingSingleTrack = selectedTimingSingleTrackMode(in: chunk) {
            if let endedURL {
                let combinedURLs = chunk.audioOptions.first(where: { $0.kind == .combined })?.streamURLs
                    ?? [selectedTimingURL].compactMap { $0 }
                if PlaybackEndedURLPolicy.endedURL(
                    endedURL,
                    belongsToSingleTrack: selectedTimingSingleTrack,
                    in: combinedURLs
                ) {
                    return selectedTimingSingleTrack
                }
            } else {
                return selectedTimingSingleTrack
            }
        }
        guard sequenceController.plan.isEmpty else {
            return nil
        }
        let activeURLs = audioCoordinator.activeURLs
        let completedURL: URL? = {
            if let endedURL {
                if !activeURLs.isEmpty,
                   activeURLs.count != 1 || activeURLs.first != endedURL {
                    return nil
                }
                return endedURL
            }
            guard activeURLs.count == 1 else { return nil }
            return activeURLs.first ?? audioCoordinator.activeURL
        }()
        guard let completedURL else {
            return nil
        }
        if chunk.audioOptions.contains(where: { $0.kind == .original && $0.streamURLs.contains(completedURL) }) {
            return .original
        }
        if chunk.audioOptions.contains(where: { $0.kind == .translation && $0.streamURLs.contains(completedURL) }) {
            return .translation
        }
        if let combined = chunk.audioOptions.first(where: { $0.kind == .combined }) {
            if combined.streamURLs.first == completedURL {
                return .original
            }
            if combined.streamURLs.dropFirst().contains(completedURL) {
                return .translation
            }
        }
        return nil
    }

    func audioURLBelongsToSelectedLane(_ url: URL, in chunk: InteractiveChunk) -> Bool {
        guard selectedChunkID == chunk.id else { return false }
        if let selectedSingleTrack = requestedSingleTrackMode() {
            switch selectedSingleTrack {
            case .original:
                if chunk.audioOptions.contains(where: { $0.kind == .original && $0.streamURLs.contains(url) }) {
                    return true
                }
            case .translation:
                if chunk.audioOptions.contains(where: { $0.kind == .translation && $0.streamURLs.contains(url) }) {
                    return true
                }
            }
            return chunk.audioOptions.contains { option in
                guard option.kind == .combined else { return false }
                return PlaybackEndedURLPolicy.endedURL(
                    url,
                    belongsTo: option,
                    singleTrack: selectedSingleTrack
                )
            }
        }
        guard let selectedOption = selectedAudioOption(for: chunk) else { return false }
        return selectedOption.streamURLs.contains(url)
    }

    private func selectedTimingSingleTrackMode(in chunk: InteractiveChunk) -> SequenceTrack? {
        guard let selectedTimingSingleTrackMode else {
            return nil
        }
        if let selectedTimingURL,
           singleTrackMode(forAudioURL: selectedTimingURL, in: chunk) == selectedTimingSingleTrackMode {
            return selectedTimingSingleTrackMode
        }
        guard chunkSupportsSingleTrack(selectedTimingSingleTrackMode, in: chunk) else {
            return nil
        }
        return selectedTimingSingleTrackMode
    }

    private func chunkSupportsSingleTrack(_ track: SequenceTrack, in chunk: InteractiveChunk) -> Bool {
        let dedicatedKind: InteractiveChunk.AudioOption.Kind = track == .original ? .original : .translation
        if chunk.audioOptions.contains(where: { $0.kind == dedicatedKind }) {
            return true
        }
        return chunk.audioOptions.contains { option in
            option.kind == .combined && !option.streamURLs.isEmpty
        }
    }

    private func playbackEndedURLBelongsToCurrentChunk(
        _ endedURL: URL,
        chunk: InteractiveChunk
    ) -> Bool {
        if requestedSingleTrackMode() != nil {
            return audioURLBelongsToSelectedLane(endedURL, in: chunk)
        }
        if let selectedOption = selectedAudioOption(for: chunk) {
            if let selectedTimingSingleTrack = selectedTimingSingleTrackMode(in: chunk) {
                return PlaybackEndedURLPolicy.endedURL(
                    endedURL,
                    belongsTo: selectedOption,
                    singleTrack: selectedTimingSingleTrack
                )
            }
            let activeSingleTrack = singleTrackModeForCompletedPlayback(
                endedURL: nil,
                in: chunk
            )
            return PlaybackEndedURLPolicy.endedURL(
                endedURL,
                belongsTo: selectedOption,
                singleTrack: activeSingleTrack ?? requestedSingleTrackMode()
            )
        }
        return chunk.audioOptions.contains { option in
            option.streamURLs.contains(endedURL)
        }
    }

    func selectAdjacentChunk(
        from chunk: InteractiveChunk,
        forward: Bool,
        autoPlay: Bool
    ) {
        if forward {
            guard let nextChunk = jobContext?.nextChunk(after: chunk.id) else { return }
            selectChunkPreservingAudioLane(
                nextChunk,
                autoPlay: autoPlay,
                targetSentenceIndex: 0
            )
            return
        }

        guard let previousChunk = jobContext?.previousChunk(before: chunk.id) else { return }
        selectChunkPreservingAudioLane(
            previousChunk,
            autoPlay: autoPlay,
            targetSentenceIndex: -1
        )
    }

    private func selectChunkPreservingAudioLane(
        _ chunk: InteractiveChunk,
        autoPlay: Bool,
        targetSentenceIndex: Int?,
        preservedSingleTrack: SequenceTrack? = nil
    ) {
        if let track = preservedSingleTrack ?? requestedSingleTrackMode() {
            preferredSingleTrackMode = track
            applySingleTrackSelection(track, for: chunk)
            rememberSingleTrackSentenceAnchor(
                in: chunk,
                targetIndex: targetSentenceIndex
            )
        }
        selectChunk(
            id: chunk.id,
            autoPlay: autoPlay,
            targetSentenceIndex: targetSentenceIndex
        )
    }

    func jumpToSentence(_ sentenceNumber: Int, autoPlay: Bool = false) {
        guard let context = jobContext else { return }
        guard sentenceNumber > 0 else { return }
        guard let targetChunk = resolveChunk(containing: sentenceNumber, in: context) else { return }

        let requestedJump = PendingSentenceJump(
            chunkID: targetChunk.id,
            sentenceNumber: sentenceNumber,
            autoPlay: autoPlay
        )
        pendingSentenceJump = requestedJump
        if audioModeManager?.isSequenceMode == false {
            rememberSingleTrackSentenceAnchor(
                chunkID: targetChunk.id,
                sentenceNumber: sentenceNumber
            )
        }

        // Check if we're jumping within the same chunk
        let isSameChunk = selectedChunkID == targetChunk.id

        if isSameChunk {
            // Same chunk - reconfigure audio to start at target sentence
            Task { [weak self] in
                guard let self else { return }
                let initialChunk = self.selectedChunk ?? targetChunk
                let initialTargetIndex = SentencePositionProvider.sentenceIndex(
                    in: initialChunk,
                    matching: sentenceNumber
                )
                let needsRenderableMetadata = !self.isSentenceReadyForDisplay(
                    in: initialChunk,
                    targetIndex: initialTargetIndex
                )
                if needsRenderableMetadata {
                    self.isTranscriptLoading = true
                }
                let didLoad = await self.loadChunkMetadataIfNeeded(
                    for: targetChunk.id,
                    force: needsRenderableMetadata
                )
                guard self.pendingSentenceJump == requestedJump else {
                    if self.pendingSentenceJump == nil {
                        self.isTranscriptLoading = false
                    }
                    return
                }
                guard self.selectedChunkID == targetChunk.id else { return }
                guard let updatedChunk = self.selectedChunk else {
                    self.isTranscriptLoading = false
                    return
                }
                // Find the 0-based index of the target sentence
                guard let targetIndex = SentencePositionProvider.sentenceIndex(in: updatedChunk, matching: sentenceNumber) else {
                    self.isTranscriptLoading = false
                    return
                }
                self.isTranscriptLoading = false
                guard self.isSentenceReadyForDisplay(in: updatedChunk, targetIndex: targetIndex) else {
                    if didLoad {
                        interactiveSelectionLogger.debug(
                            "Jump to sentence: metadata loaded but target sentence is not renderable sentenceNumber=\(sentenceNumber, privacy: .public)"
                        )
                    }
                    return
                }
                self.prepareAudio(for: updatedChunk, autoPlay: autoPlay, targetSentenceIndex: targetIndex)
                // Clear pending jump since we're passing target index directly
                self.pendingSentenceJump = nil
            }
        } else {
            // Different chunk - selectChunk will handle loading and audio setup
            let targetIndex = SentencePositionProvider.sentenceIndex(
                in: targetChunk,
                matching: sentenceNumber
            )
            selectChunk(id: targetChunk.id, autoPlay: autoPlay, targetSentenceIndex: targetIndex)
            if audioModeManager?.isSequenceMode == false {
                rememberSingleTrackSentenceAnchor(
                    chunkID: targetChunk.id,
                    sentenceNumber: sentenceNumber
                )
            }
        }
    }

    func jumpToTime(
        _ time: Double,
        in chunk: InteractiveChunk,
        autoPlay: Bool = false,
        matchingSentenceNumber sentenceNumber: Int? = nil,
        preferredTrack: SequenceTrack? = nil
    ) {
        guard time.isFinite else { return }
        pendingTimeSeek = PendingTimeSeek(
            chunkID: chunk.id,
            time: time,
            autoPlay: autoPlay,
            sentenceNumber: sentenceNumber,
            preferredTrackRawValue: preferredTrack?.rawValue
        )
        if selectedChunkID == chunk.id {
            seekPlaybackWhenReady(
                to: time,
                in: chunk,
                autoPlay: autoPlay,
                matchingSentenceNumber: sentenceNumber,
                preferredTrack: preferredTrack
            )
            pendingTimeSeek = nil
            return
        }
        selectChunk(id: chunk.id, autoPlay: false)
    }

    func resolveChunk(containing sentenceNumber: Int, in context: JobContext) -> InteractiveChunk? {
        if let match = context.chunks.first(where: { chunk in
            SentencePositionProvider.sentenceIndex(in: chunk, matching: sentenceNumber) != nil
        }) {
            return match
        }
        return context.chunks.first(where: { chunk in
            guard let start = chunk.startSentence else { return false }
            guard let end = chunk.endSentence else {
                return sentenceNumber == start
            }
            return sentenceNumber >= start && sentenceNumber <= end
        })
    }

    func attemptPendingSentenceJump(in chunk: InteractiveChunk) {
        guard let pending = pendingSentenceJump, pending.chunkID == chunk.id else { return }

        // In sequence mode, use the sequence controller for seeking
        if isSequenceModeActive {
            // Find the target sentence index
            guard let targetSentenceIndex = SentencePositionProvider.sentenceIndex(
                in: chunk,
                matching: pending.sentenceNumber
            ) else {
                interactiveSelectionLogger.debug(
                    "Sequence jump: could not find sentence index for sentenceNumber=\(pending.sentenceNumber, privacy: .public)"
                )
                pendingSentenceJump = nil
                return
            }

            // CRITICAL: verify the sequence plan was built for THIS chunk. If the
            // selected chunk changed (e.g., adjacent chunk preload, resume to a
            // different chunk) without rebuilding the plan, seekToSentence would
            // return timings from the wrong audio file — causing audio and text
            // to play different sentences.
            let chunkOriginalURL = chunk.audioOptions.first(where: { $0.kind == .original })?.primaryURL
            if let chunkOriginalURL,
               sequenceController.originalTrackURL != chunkOriginalURL {
                interactiveSelectionLogger.debug(
                    "Sequence jump: stale plan current=\(self.sequenceController.originalTrackURL?.lastPathComponent ?? "nil", privacy: .private), needed=\(chunkOriginalURL.lastPathComponent, privacy: .private), targetSentenceIndex=\(targetSentenceIndex, privacy: .public)"
                )
                // Rebuild the plan + reload audio for the correct chunk, then the
                // seek target is computed against the fresh plan.
                prepareAudio(for: chunk, autoPlay: pending.autoPlay, targetSentenceIndex: targetSentenceIndex)
                pendingSentenceJump = nil
                return
            }

            // Check if we're already at this sentence (might have been handled by configureSequencePlayback)
            if let currentIdx = sequenceController.currentSentenceIndex, currentIdx == targetSentenceIndex {
                interactiveSelectionLogger.debug(
                    "Sequence jump: already at target sentence \(targetSentenceIndex, privacy: .public), clearing pending jump autoPlay=\(pending.autoPlay, privacy: .public)"
                )
                pendingSentenceJump = nil
                if pending.autoPlay && !audioCoordinator.isPlaying {
                    playForReaderTransport()
                }
                return
            }

            // Use seekToSentence for within-chunk jumps in sequence mode
            interactiveSelectionLogger.debug(
                "Sequence jump: within-chunk targetIndex=\(targetSentenceIndex, privacy: .public), sentenceNumber=\(pending.sentenceNumber, privacy: .public)"
            )
            pendingSentenceJump = nil

            // Capture current track BEFORE updating state
            let previousTrack = sequenceController.currentTrack

            guard let target = sequenceController.seekToSentence(
                targetSentenceIndex,
                preferredTrack: audioModeManager?.preferredTrack ?? .original
            ) else {
                interactiveSelectionLogger.debug(
                    "Sequence jump: seekToSentence returned nil for index=\(targetSentenceIndex, privacy: .public)"
                )
                return
            }

            // Mute immediately to prevent audio bleed during the transition
            audioCoordinator.setVolume(0)

            // Cancel any pending audio ready subscription from initial load
            // This prevents the old transition from completing with wrong position
            cancelPendingAudioReadySubscription()
            let token = currentTransitionToken

            // Fire pre-transition callback
            onSequenceWillTransition?()
            sequenceController.beginTransition()

            // Check if we need to switch tracks (compare target with PREVIOUS track)
            if target.track != previousTrack {
                handleSequenceTrackSwitch(
                    track: target.track,
                    seekTime: target.time,
                    shouldPlay: pending.autoPlay
                )
            } else {
                // Same track, just seek - mute during seek to prevent audio bleed
                // NOTE: We don't pause here to avoid triggering reading bed pause
                let wasPlaying = audioCoordinator.isPlaying
                audioCoordinator.setVolume(0)
                self.performWithinChunkSeekWithDriftCheck(
                    to: target.time,
                    wasPlaying: wasPlaying,
                    shouldPlay: pending.autoPlay,
                    token: token
                )
            }
            return
        }

        // Non-sequence mode: use the same guarded sentence seek path as live
        // slider/keyboard jumps so stale seek completions cannot re-anchor the
        // transcript after metadata finishes loading.
        guard let targetIndex = SentencePositionProvider.sentenceIndex(
            in: chunk,
            matching: pending.sentenceNumber
        ) else { return }
        rememberSingleTrackSentenceAnchor(chunkID: chunk.id, sentenceNumber: pending.sentenceNumber)
        pendingSentenceJump = nil
        seekSingleTrackSentenceWhenReady(targetIndex, in: chunk, autoPlay: pending.autoPlay)
    }

    func attemptPendingTimeSeek(in chunk: InteractiveChunk) {
        guard let pending = pendingTimeSeek, pending.chunkID == chunk.id else { return }
        pendingTimeSeek = nil
        seekPlaybackWhenReady(
            to: pending.time,
            in: chunk,
            autoPlay: pending.autoPlay,
            matchingSentenceNumber: pending.sentenceNumber,
            preferredTrack: pending.preferredTrackRawValue.flatMap(SequenceTrack.init(rawValue:))
        )
    }

    func seekPlaybackWhenReady(
        to time: Double,
        in chunk: InteractiveChunk,
        autoPlay: Bool,
        matchingSentenceNumber sentenceNumber: Int? = nil,
        preferredTrack: SequenceTrack? = nil
    ) {
        guard time.isFinite else { return }
        if isSequenceModeActive {
            seekSequencePlaybackWhenReady(
                to: time,
                in: chunk,
                autoPlay: autoPlay,
                matchingSentenceNumber: sentenceNumber,
                preferredTrack: preferredTrack
            )
            return
        }
        let chunkId = chunk.id
        if audioCoordinator.isReady {
            rememberSingleTrackTimeSeekAnchor(
                time: time,
                sentenceNumber: sentenceNumber,
                in: chunk
            )
            playbackTransportDebugLog(
                "[PlaybackTransport] Interactive time seek accepted sequence=false sentence=\(sentenceNumber ?? -1) time=\(String(format: "%.3f", time))"
            )
            seekPlayback(to: time, in: chunk)
            if autoPlay && !audioCoordinator.isPlaying {
                audioCoordinator.play()
            }
            return
        }

        var seenLoadingState = false
        var isFirstEmission = true
        var cancellable: AnyCancellable?
        cancellable = audioCoordinator.$isReady
            .sink { [weak self] isReady in
                guard let self else { return }
                guard let currentChunk = self.selectedChunk, currentChunk.id == chunkId else {
                    cancellable?.cancel()
                    return
                }
                if !isReady {
                    seenLoadingState = true
                    isFirstEmission = false
                    return
                }
                guard seenLoadingState || isFirstEmission else { return }
                isFirstEmission = false
                self.rememberSingleTrackTimeSeekAnchor(
                    time: time,
                    sentenceNumber: sentenceNumber,
                    in: currentChunk
                )
                playbackTransportDebugLog(
                    "[PlaybackTransport] Interactive time seek accepted sequence=false sentence=\(sentenceNumber ?? -1) time=\(String(format: "%.3f", time))"
                )
                self.seekPlayback(to: time, in: currentChunk)
                if autoPlay && !self.audioCoordinator.isPlaying {
                    self.audioCoordinator.play()
                }
                cancellable?.cancel()
            }
    }

    func seekSequencePlaybackWhenReady(
        to time: Double,
        in chunk: InteractiveChunk,
        autoPlay: Bool,
        matchingSentenceNumber sentenceNumber: Int? = nil,
        preferredTrack: SequenceTrack? = nil
    ) {
        let chunkId = chunk.id
        let targetSentenceIndex = sentenceNumber.flatMap {
            SentencePositionProvider.sentenceIndex(in: chunk, matching: $0)
        }

        func applySequenceSeek(in currentChunk: InteractiveChunk) {
            let previousTrack = sequenceController.currentTrack
            guard let target = sequenceController.seekToTime(
                time,
                sentenceIndex: targetSentenceIndex,
                preferredTrack: preferredTrack ?? sequenceController.currentTrack
            ) ?? targetSentenceIndex.flatMap({
                playbackTransportDebugLog(
                    "[PlaybackTransport] Interactive sequence time seek fallback=sentenceStart sentence=\(sentenceNumber ?? -1) time=\(String(format: "%.3f", time))"
                )
                return sequenceController.seekToSentence(
                    $0,
                    preferredTrack: audioModeManager?.preferredTrack ?? .original
                )
            }) else {
                playbackTransportDebugLog(
                    "[PlaybackTransport] Interactive sequence time seek failed sentence=\(sentenceNumber ?? -1) time=\(String(format: "%.3f", time))"
                )
                return
            }
            playbackTransportDebugLog(
                "[PlaybackTransport] Interactive sequence time seek accepted sentence=\(sentenceNumber ?? -1) time=\(String(format: "%.3f", target.time)) track=\(target.track.rawValue)"
            )
            if let sentenceNumber {
                rememberSingleTrackSentenceAnchor(chunkID: currentChunk.id, sentenceNumber: sentenceNumber)
            } else {
                rememberSingleTrackSentenceAnchor(atTime: target.time, in: currentChunk)
            }
            let targetURL = sequenceTrackURL(target.track)
            let shouldLoadTargetTrack = previousTrack != target.track
                || audioCoordinator.activeURL != targetURL
                || audioCoordinator.nowPlayingPlayer == nil
            if shouldLoadTargetTrack {
                handleSequenceTrackSwitch(
                    track: target.track,
                    seekTime: target.time,
                    shouldPlay: autoPlay
                )
                return
            }
            if !sequenceController.isTransitioning {
                onSequenceWillTransition?()
            }
            sequenceController.beginTransition()
            cancelPendingAudioReadySubscription()
            let token = currentTransitionToken
            audioCoordinator.setVolume(0)
            performWithinChunkSeekWithDriftCheck(
                to: target.time,
                wasPlaying: audioCoordinator.isPlaying,
                shouldPlay: autoPlay,
                token: token
            )
        }

        if audioCoordinator.isReady {
            applySequenceSeek(in: chunk)
            return
        }

        var seenLoadingState = false
        var isFirstEmission = true
        var cancellable: AnyCancellable?
        cancellable = audioCoordinator.$isReady
            .sink { [weak self] isReady in
                guard let self else { return }
                guard let currentChunk = self.selectedChunk, currentChunk.id == chunkId else {
                    cancellable?.cancel()
                    return
                }
                if !isReady {
                    seenLoadingState = true
                    isFirstEmission = false
                    return
                }
                guard seenLoadingState || isFirstEmission else { return }
                isFirstEmission = false
                self.seekSequencePlaybackWhenReady(
                    to: time,
                    in: currentChunk,
                    autoPlay: autoPlay,
                    matchingSentenceNumber: sentenceNumber,
                    preferredTrack: preferredTrack
                )
                cancellable?.cancel()
            }
    }

    private func sequenceTrackURL(_ track: SequenceTrack) -> URL? {
        switch track {
        case .original:
            return sequenceController.originalTrackURL
        case .translation:
            return sequenceController.translationTrackURL
        }
    }

    func rememberSingleTrackSentenceAnchor(in chunk: InteractiveChunk, targetIndex: Int?) {
        guard let targetIndex else { return }
        let sentenceNumber = singleTrackSentenceNumber(
            in: chunk,
            targetIndex: targetIndex
        )
        let resolvedTargetIndex: Int? = {
            if targetIndex >= 0 {
                return targetIndex
            }
            if !chunk.sentences.isEmpty {
                return max(0, chunk.sentences.count - 1)
            }
            return nil
        }()
        guard sentenceNumber != nil || resolvedTargetIndex != nil else { return }
        rememberSingleTrackSentenceAnchor(
            chunkID: chunk.id,
            sentenceNumber: sentenceNumber,
            targetIndex: resolvedTargetIndex
        )
    }

    private func singleTrackSentenceNumber(in chunk: InteractiveChunk, targetIndex: Int) -> Int? {
        if targetIndex >= 0,
           chunk.sentences.indices.contains(targetIndex) {
            return chunkDerivedSingleTrackSentenceNumber(in: chunk, targetIndex: targetIndex)
        }

        if targetIndex < 0 {
            if let end = chunk.endSentence {
                return end
            }
            if !chunk.sentences.isEmpty {
                return SentencePositionProvider.sentenceNumber(
                    in: chunk,
                    at: max(0, chunk.sentences.count - 1)
                )
            }
            return chunk.startSentence
        }

        guard let start = chunk.startSentence else { return nil }
        let sentenceNumber = start + targetIndex
        if let end = chunk.endSentence, sentenceNumber > end {
            return nil
        }
        return sentenceNumber
    }

    private func chunkDerivedSingleTrackSentenceNumber(
        in chunk: InteractiveChunk,
        targetIndex: Int
    ) -> Int? {
        SentencePositionProvider.sentenceNumber(
            in: chunk,
            at: targetIndex
        )
    }

    func rememberSingleTrackSentenceAnchor(chunkID: String, sentenceNumber: Int) {
        rememberSingleTrackSentenceAnchor(
            chunkID: chunkID,
            sentenceNumber: sentenceNumber,
            targetIndex: nil
        )
    }

    private func rememberSingleTrackSentenceAnchor(
        chunkID: String,
        sentenceNumber: Int?,
        targetIndex: Int?
    ) {
        recentSingleTrackSentenceAnchor = RecentSingleTrackSentenceAnchor(
            chunkID: chunkID,
            sentenceNumber: sentenceNumber,
            targetIndex: targetIndex,
            createdAt: Date()
        )
    }

    func rememberSingleTrackSentenceAnchor(atTime time: Double, in chunk: InteractiveChunk) {
        guard !isSequenceModeActive,
              let sentenceNumber = SentencePositionProvider.sentenceNumber(
                in: chunk,
                atTime: time,
                activeTimingTrack: activeTimingTrack(for: chunk)
              ) else {
            return
        }
        rememberSingleTrackSentenceAnchor(chunkID: chunk.id, sentenceNumber: sentenceNumber)
    }

    private func rememberSingleTrackTimeSeekAnchor(
        time: Double,
        sentenceNumber: Int?,
        in chunk: InteractiveChunk
    ) {
        if let sentenceNumber,
           SentencePositionProvider.sentenceIndex(in: chunk, matching: sentenceNumber) != nil {
            rememberSingleTrackSentenceAnchor(chunkID: chunk.id, sentenceNumber: sentenceNumber)
            return
        }
        rememberSingleTrackSentenceAnchor(atTime: time, in: chunk)
    }

    private func rememberSingleTrackBatchStartAnchorIfNeeded(
        for chunk: InteractiveChunk,
        targetSentenceIndex: Int?,
        autoPlay: Bool
    ) {
        guard requestedSingleTrackMode() != nil else { return }
        let inferredTargetIndex: Int? = {
            if let targetSentenceIndex {
                return targetSentenceIndex
            }
            if autoPlay || audioCoordinator.isPlaybackRequested {
                return 0
            }
            return nil
        }()
        rememberSingleTrackSentenceAnchor(in: chunk, targetIndex: inferredTargetIndex)
    }

    func recentSingleTrackSentenceAnchorNumber(in chunk: InteractiveChunk) -> Int? {
        guard requestedSingleTrackMode() != nil, !isSequenceModeActive else { return nil }
        guard let anchor = recentSingleTrackSentenceAnchor,
              anchor.chunkID == chunk.id,
              Date().timeIntervalSince(anchor.createdAt) <= recentSingleTrackSentenceAnchorLifetime else {
            recentSingleTrackSentenceAnchor = nil
            return nil
        }
        if let sentenceNumber = anchor.sentenceNumber {
            return sentenceNumber
        }
        guard let targetIndex = anchor.targetIndex,
              let sentenceNumber = SentencePositionProvider.sentenceNumber(
                in: chunk,
                at: targetIndex
              ) else {
            return nil
        }
        recentSingleTrackSentenceAnchor = RecentSingleTrackSentenceAnchor(
            chunkID: anchor.chunkID,
            sentenceNumber: sentenceNumber,
            targetIndex: targetIndex,
            createdAt: anchor.createdAt
        )
        return sentenceNumber
    }

    func clearRecentSingleTrackSentenceAnchor(chunkID: String? = nil, sentenceNumber: Int? = nil) {
        guard let anchor = recentSingleTrackSentenceAnchor else { return }
        if let chunkID, anchor.chunkID != chunkID { return }
        if let sentenceNumber, anchor.sentenceNumber != sentenceNumber { return }
        recentSingleTrackSentenceAnchor = nil
    }

    func recentSingleTrackSentenceAnchorIndex(in chunk: InteractiveChunk) -> Int? {
        if let sentenceNumber = recentSingleTrackSentenceAnchorNumber(in: chunk),
           let index = SentencePositionProvider.sentenceIndex(in: chunk, matching: sentenceNumber) {
            return index
        }
        guard requestedSingleTrackMode() != nil, !isSequenceModeActive else { return nil }
        guard let anchor = recentSingleTrackSentenceAnchor,
              anchor.chunkID == chunk.id,
              Date().timeIntervalSince(anchor.createdAt) <= recentSingleTrackSentenceAnchorLifetime,
              let targetIndex = anchor.targetIndex,
              chunk.sentences.indices.contains(targetIndex) else {
            return nil
        }
        return targetIndex
    }

    /// Perform a within-chunk seek with drift verification. Fixes audio-vs-text
    /// desync on resume: AVPlayer's seek completion can fire while the internal
    /// read head is still at an older position, so when play() resumes we can
    /// briefly hear content from before the intended sentence. We re-check the
    /// observed currentTime after the seek completion; if it's off by more than
    /// 100ms we force a second seek before resuming playback.
    private func performWithinChunkSeekWithDriftCheck(
        to seekTime: Double,
        wasPlaying: Bool,
        shouldPlay: Bool,
        token: Int
    ) {
        audioCoordinator.seek(to: seekTime) { [weak self] finished in
            guard let self else { return }
            interactiveSelectionLogger.debug("Sequence jump: within-chunk seek completed finished=\(finished, privacy: .public)")
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) { [weak self] in
                guard let self else { return }
                guard token == self.currentTransitionToken else {
                    interactiveSelectionLogger.debug(
                        "Sequence jump: ignoring stale within-chunk seek completion token=\(token, privacy: .public), current=\(self.currentTransitionToken, privacy: .public)"
                    )
                    return
                }
                let observed = self.audioCoordinator.currentTime
                let drift = abs(observed - seekTime)
                if drift > 0.1 {
                    interactiveSelectionLogger.debug(
                        "Sequence jump: within-chunk seek drift observed=\(String(format: "%.3f", observed), privacy: .public), expected=\(String(format: "%.3f", seekTime), privacy: .public), re-seeking"
                    )
                    self.audioCoordinator.seek(to: seekTime) { [weak self] _ in
                        guard let self else { return }
                        guard token == self.currentTransitionToken else { return }
                        self.finalizeWithinChunkSeek(
                            seekTime: seekTime,
                            wasPlaying: wasPlaying,
                            shouldPlay: shouldPlay
                        )
                    }
                    return
                }
                self.finalizeWithinChunkSeek(
                    seekTime: seekTime,
                    wasPlaying: wasPlaying,
                    shouldPlay: shouldPlay
                )
            }
        }
    }

    private func finalizeWithinChunkSeek(seekTime: Double, wasPlaying: Bool, shouldPlay: Bool) {
        self.sequenceController.endTransition(expectedTime: seekTime)
        self.audioCoordinator.restoreVolume()
        if (wasPlaying || shouldPlay), !self.audioCoordinator.isPlaying {
            self.audioCoordinator.play()
        }
    }

    func startTimeForSentence(_ sentenceNumber: Int, in chunk: InteractiveChunk) -> Double? {
        let activeTimingTrack = activeTimingTrack(for: chunk)
        let useCombinedPhases = useCombinedPhases(for: chunk)
        if !useCombinedPhases,
           let index = SentencePositionProvider.sentenceIndex(in: chunk, matching: sentenceNumber),
           let gate = gateStartTimeForSentence(atIndex: index, in: chunk, activeTimingTrack: activeTimingTrack) {
            return gate
        }
        let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: playbackDuration(for: chunk),
            useCombinedPhases: useCombinedPhases,
            timingVersion: chunk.timingVersion
        )
        if let timelineSentences {
            for runtime in timelineSentences {
                guard chunk.sentences.indices.contains(runtime.index) else { continue }
                if SentencePositionProvider.sentenceNumber(in: chunk, at: runtime.index) == sentenceNumber {
                    return runtime.startTime
                }
            }
        }
        if let index = SentencePositionProvider.sentenceIndex(in: chunk, matching: sentenceNumber) {
            return chunk.sentences[index].startTime
        }
        return nil
    }

    func resumePlaybackTime(_ time: Double, matches sentenceNumber: Int, in chunk: InteractiveChunk) -> Bool {
        guard time.isFinite, time >= 0 else { return false }
        var resolvedAnyTimingTrack = false
        for timingTrack in resumeValidationTimingTracks(for: chunk) {
            if let resolved = SentencePositionProvider.sentenceNumber(
                in: chunk,
                atTime: time,
                activeTimingTrack: timingTrack
            ) {
                resolvedAnyTimingTrack = true
                if resolved == sentenceNumber {
                    return true
                }
            }
        }
        if resolvedAnyTimingTrack {
            return false
        }
        guard let index = SentencePositionProvider.sentenceIndex(in: chunk, matching: sentenceNumber),
              let start = startTimeForSentence(atIndex: index, in: chunk) else {
            return false
        }
        let nextStart = chunk.sentences.indices.contains(index + 1)
            ? startTimeForSentence(atIndex: index + 1, in: chunk)
            : nil
        if let nextStart, nextStart.isFinite, nextStart > start {
            return time >= max(0, start - 0.05) && time < nextStart + 0.05
        }
        if let duration = playbackDuration(for: chunk), duration.isFinite, duration > start {
            return time >= max(0, start - 0.05) && time <= duration + 0.05
        }
        return time >= max(0, start - 0.05)
    }

    func resumeValidationTimingTracks(for chunk: InteractiveChunk) -> [TextPlayerTimingTrack] {
        let active = activeTimingTrack(for: chunk)
        guard audioModeManager?.isSequenceMode == true,
              chunk.audioOptions.contains(where: { $0.kind == .combined }) else {
            return [active]
        }
        var tracks: [TextPlayerTimingTrack] = [active]
        for candidate in [TextPlayerTimingTrack.original, .translation, .mix] where !tracks.contains(candidate) {
            tracks.append(candidate)
        }
        return tracks
    }

    /// Get start time for a sentence by its 0-based array index
    func startTimeForSentence(atIndex index: Int, in chunk: InteractiveChunk) -> Double? {
        guard chunk.sentences.indices.contains(index) else { return nil }
        let activeTimingTrack = activeTimingTrack(for: chunk)
        let useCombinedPhases = useCombinedPhases(for: chunk)
        if !useCombinedPhases,
           let gate = gateStartTimeForSentence(atIndex: index, in: chunk, activeTimingTrack: activeTimingTrack) {
            return gate
        }
        let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: playbackDuration(for: chunk),
            useCombinedPhases: useCombinedPhases,
            timingVersion: chunk.timingVersion
        )
        if let timelineSentences,
           let runtime = timelineSentences.first(where: { $0.index == index }) {
            return runtime.startTime
        }
        // Fallback to sentence's start time
        return chunk.sentences[index].startTime
    }

    func gateStartTimeForSentence(
        atIndex index: Int,
        in chunk: InteractiveChunk,
        activeTimingTrack: TextPlayerTimingTrack
    ) -> Double? {
        SentencePositionProvider.gateStartTime(
            in: chunk,
            at: index,
            activeTimingTrack: activeTimingTrack
        )
    }

    /// Helper to seek to a sentence after audio finishes loading.
    /// Observes audioCoordinator.isReady and seeks once the audio is ready.
    /// Handles both cases: audio needs to load, or audio is already loaded.
    func seekToSentenceAfterLoad(_ targetIndex: Int, in chunk: InteractiveChunk, autoPlay: Bool) {
        let chunkId = chunk.id

        // If audio is already ready, seek immediately
        if audioCoordinator.isReady {
            if startTimeForSentence(atIndex: targetIndex, in: chunk) != nil {
                interactiveSelectionLogger.debug(
                    "Single toggle: audio already ready, seeking sentenceIndex=\(targetIndex, privacy: .public)"
                )
                seekSingleTrackSentence(atIndex: targetIndex, in: chunk, autoPlay: autoPlay)
            }
            return
        }

        // Audio not ready yet - wait for it
        var seenLoadingState = false
        var isFirstEmission = true
        var cancellable: AnyCancellable?

        cancellable = audioCoordinator.$isReady
            .sink { [weak self] isReady in
                guard let self else { return }
                guard let currentChunk = self.selectedChunk, currentChunk.id == chunkId else {
                    cancellable?.cancel()
                    return
                }

                if !isReady {
                    seenLoadingState = true
                    isFirstEmission = false
                    interactiveSelectionLogger.debug("Single toggle: audio loading")
                } else if seenLoadingState || isFirstEmission {
                    // Either we saw loading->ready transition, or audio was already ready on first emit
                    isFirstEmission = false
                    if self.startTimeForSentence(atIndex: targetIndex, in: currentChunk) != nil {
                        interactiveSelectionLogger.debug(
                            "Single toggle: audio ready, seeking sentenceIndex=\(targetIndex, privacy: .public)"
                        )
                        self.seekSingleTrackSentence(atIndex: targetIndex, in: currentChunk, autoPlay: autoPlay)
                    }
                    cancellable?.cancel()
                }
            }
    }

    func seekSingleTrackSentenceWhenReady(_ targetIndex: Int, in chunk: InteractiveChunk, autoPlay: Bool) {
        let chunkId = chunk.id
        rememberSingleTrackSentenceAnchor(in: chunk, targetIndex: targetIndex)
        if audioCoordinator.isReady {
            seekSingleTrackSentence(atIndex: targetIndex, in: chunk, autoPlay: autoPlay)
            return
        }

        var seenLoadingState = false
        var isFirstEmission = true
        var cancellable: AnyCancellable?
        cancellable = audioCoordinator.$isReady
            .sink { [weak self] isReady in
                guard let self else { return }
                guard let currentChunk = self.selectedChunk, currentChunk.id == chunkId else {
                    cancellable?.cancel()
                    return
                }
                if !isReady {
                    seenLoadingState = true
                    isFirstEmission = false
                    return
                }
                guard seenLoadingState || isFirstEmission else { return }
                isFirstEmission = false
                self.seekSingleTrackSentence(atIndex: targetIndex, in: currentChunk, autoPlay: autoPlay)
                cancellable?.cancel()
            }
    }
}
