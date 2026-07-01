import SwiftUI
import OSLog

private let interactiveTranscriptLogger = Logger(subsystem: "InteractiveReader", category: "InteractiveTranscript")

extension InteractivePlayerView {
    func prepareExplicitSentenceJump(to sentenceNumber: Int, chunkID: String? = nil) {
        clearHeaderSentenceProgressDraft()
        selectedSentenceID = sentenceNumber
        pendingExplicitSentenceJumpID = sentenceNumber
        pendingExplicitSentenceJumpChunkID = chunkID
        pendingExplicitSentenceJumpStartedAt = Date()
        frozenTranscriptSentences = nil
        frozenPlaybackPrimaryKind = nil
    }

    func sentenceBinding(
        entries: [SentenceOption],
        chunk: InteractiveChunk,
        chapterRange: SentenceRange?
    ) -> Binding<Int> {
        Binding(
            get: {
                if let selected = selectedSentenceID,
                   entries.contains(where: { $0.id == selected }) {
                    return selected
                }
                return entries.first?.id ?? 0
            },
            set: { newValue in
                prepareExplicitSentenceJump(to: newValue)
                viewModel.jumpToSentence(newValue, autoPlay: audioCoordinator.isPlaybackRequested)
            }
        )
    }

    func sentenceEntries(for chunk: InteractiveChunk, chapterRange: SentenceRange?) -> [SentenceOption] {
        if let chapterRange {
            guard chapterRange.end >= chapterRange.start else { return [] }
            return (chapterRange.start...chapterRange.end).map { sentenceIndex in
                SentenceOption(id: sentenceIndex, label: "\(sentenceIndex)", startTime: nil)
            }
        }
        let sentences = chunk.sentences
        if sentences.isEmpty {
            if let start = chunk.startSentence, let end = chunk.endSentence, start <= end {
                return (start...end).map { SentenceOption(id: $0, label: "\($0)", startTime: nil) }
            }
            return []
        }
        var startTimes: [Int: Double] = [:]
        let activeTimingTrack = viewModel.activeTimingTrack(for: chunk)
        let useCombinedPhases = viewModel.useCombinedPhases(for: chunk)
        let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: viewModel.playbackDuration(for: chunk),
            useCombinedPhases: useCombinedPhases,
            timingVersion: chunk.timingVersion
        )
        if let timelineSentences {
            for runtime in timelineSentences {
                guard sentences.indices.contains(runtime.index) else { continue }
                let sentence = sentences[runtime.index]
                let id = SentencePositionProvider.sentenceNumber(in: chunk, at: runtime.index)
                    ?? SentencePositionProvider.sentenceNumber(for: sentence)
                startTimes[id] = runtime.startTime
            }
        }
        let entries = sentences.enumerated().map { index, sentence -> SentenceOption in
            let id = SentencePositionProvider.sentenceNumber(in: chunk, at: index)
                ?? SentencePositionProvider.sentenceNumber(for: sentence)
            let label = "\(id)"
            return SentenceOption(
                id: id,
                label: label,
                startTime: startTimes[id] ?? sentence.startTime
            )
        }
        return entries.sorted { $0.id < $1.id }
    }

    func syncSelectedSentence(for chunk: InteractiveChunk) {
        guard !isMenuVisible else { return }
        guard linguistSelection == nil else { return }
        let time = viewModel.highlightingTime
        guard time.isFinite else { return }
        if let pending = pendingExplicitSentenceJumpID,
           pendingExplicitSentenceJumpApplies(to: chunk) {
            if pendingExplicitSentenceJumpReachedLivePlayback(in: chunk) {
                pendingExplicitSentenceJumpID = nil
                pendingExplicitSentenceJumpChunkID = nil
                pendingExplicitSentenceJumpStartedAt = nil
            } else if !pendingExplicitSentenceJumpIsExpired {
                selectedSentenceID = pending
                return
            } else {
                pendingExplicitSentenceJumpID = nil
                pendingExplicitSentenceJumpChunkID = nil
                pendingExplicitSentenceJumpStartedAt = nil
            }
        }
        if let anchor = viewModel.recentSingleTrackSentenceAnchorNumber(in: chunk),
           explicitSentenceJumpReachedLivePlayback(anchor, chunkID: chunk.id, in: chunk) {
            viewModel.clearRecentSingleTrackSentenceAnchor(chunkID: chunk.id, sentenceNumber: anchor)
        } else if let anchor = viewModel.recentSingleTrackSentenceAnchorNumber(in: chunk) {
            selectedSentenceID = anchor
            return
        }
        guard currentChunkAudioIsActive(for: chunk) else { return }
        guard let sentence = viewModel.activeSentence(at: time) else { return }
        guard let index = chunk.sentences.firstIndex(where: { $0.id == sentence.id && $0.displayIndex == sentence.displayIndex }) else {
            return
        }
        let id = SentencePositionProvider.sentenceNumber(in: chunk, at: index)
            ?? SentencePositionProvider.sentenceNumber(for: sentence)
        if let pending = pendingExplicitSentenceJumpID {
            if id == pending || pendingExplicitSentenceJumpIsExpired {
                pendingExplicitSentenceJumpID = nil
                pendingExplicitSentenceJumpChunkID = nil
                pendingExplicitSentenceJumpStartedAt = nil
            } else {
                selectedSentenceID = pending
                return
            }
        }
        if selectedSentenceID != id {
            selectedSentenceID = id
        }
    }

    func handleSentenceSkip(_ delta: Int, in chunk: InteractiveChunk) {
        let explicitAnchorSentenceID = pendingExplicitSentenceJumpID.flatMap { pending in
            pendingExplicitSentenceJumpIsExpired ? nil : pending
        } ?? viewModel.recentSingleTrackSentenceAnchorNumber(in: chunk)
            ?? selectedSentenceID
        clearHeaderSentenceProgressDraft()
        guard delta != 0 else { return }

        if viewModel.isSequenceModeActive {
            viewModel.skipSentence(
                forward: delta > 0,
                preferredTrack: preferredSequenceTrack,
                anchorSentenceNumber: explicitAnchorSentenceID
            )
            return
        }

        if let explicitAnchorSentenceID,
           jumpByOneSentenceFromExplicitAnchor(
               explicitAnchorSentenceID,
               delta: delta,
               in: chunk
           ) {
            return
        }

        guard !chunk.sentences.isEmpty else {
            viewModel.skipSentence(
                forward: delta > 0,
                preferredTrack: preferredSequenceTrack,
                anchorSentenceNumber: explicitAnchorSentenceID
            )
            return
        }

        guard let currentIndex = stableSentenceIndexForNavigation(
            in: chunk,
            preferredSentenceNumber: explicitAnchorSentenceID
        ) else {
            viewModel.skipSentence(
                forward: delta > 0,
                preferredTrack: preferredSequenceTrack,
                anchorSentenceNumber: explicitAnchorSentenceID
            )
            return
        }

        let targetIndex = currentIndex + (delta > 0 ? 1 : -1)
        guard chunk.sentences.indices.contains(targetIndex) else {
            viewModel.skipSentence(
                forward: delta > 0,
                preferredTrack: preferredSequenceTrack,
                anchorSentenceNumber: explicitAnchorSentenceID
            )
            return
        }

        guard let targetNumber = SentencePositionProvider.sentenceNumber(in: chunk, at: targetIndex) else {
            return
        }
        prepareExplicitSentenceJump(to: targetNumber)
        viewModel.jumpToSentence(targetNumber, autoPlay: audioCoordinator.isPlaybackRequested)
        requestKeyboardShortcutFocus()
    }

    private func jumpByOneSentenceFromExplicitAnchor(
        _ anchorSentenceNumber: Int,
        delta: Int,
        in chunk: InteractiveChunk
    ) -> Bool {
        guard delta != 0 else { return false }
        let step = delta > 0 ? 1 : -1
        guard let anchorIndex = SentencePositionProvider.sentenceIndex(
            in: chunk,
            matching: anchorSentenceNumber
        ) else {
            return false
        }
        let targetIndex = anchorIndex + step
        guard chunk.sentences.indices.contains(targetIndex),
              let targetNumber = SentencePositionProvider.sentenceNumber(
                in: chunk,
                at: targetIndex
              ) else {
            return false
        }
        if let range = headerSentenceProgressRange(for: chunk) {
            guard Double(targetNumber) >= range.lowerBound,
                  Double(targetNumber) <= range.upperBound else {
                return false
            }
        }
        prepareExplicitSentenceJump(to: targetNumber)
        viewModel.jumpToSentence(targetNumber, autoPlay: audioCoordinator.isPlaybackRequested)
        requestKeyboardShortcutFocus()
        return true
    }

    func stableSentenceIndexForNavigation(in chunk: InteractiveChunk) -> Int? {
        stableSentenceIndexForNavigation(in: chunk, preferredSentenceNumber: nil)
    }

    func stableSentenceIndexForNavigation(
        in chunk: InteractiveChunk,
        preferredSentenceNumber: Int?
    ) -> Int? {
        if let preferredSentenceNumber,
           let preferredIndex = SentencePositionProvider.sentenceIndex(in: chunk, matching: preferredSentenceNumber) {
            return preferredIndex
        }
        if let selection = linguistSelection,
           chunk.sentences.indices.contains(selection.sentenceIndex) {
            return selection.sentenceIndex
        }
        if let selectedSentenceID,
           let selectedIndex = SentencePositionProvider.sentenceIndex(in: chunk, matching: selectedSentenceID) {
            return selectedIndex
        }
        if audioCoordinator.isPlaying,
           let active = activeSentenceDisplay(for: chunk),
           chunk.sentences.indices.contains(active.index) {
            return active.index
        }
        if let active = activeSentenceDisplay(for: chunk),
           chunk.sentences.indices.contains(active.index) {
            return active.index
        }
        return captureCurrentSentenceIndex(for: chunk)
    }

    func transcriptSentences(for chunk: InteractiveChunk) -> [TextPlayerSentenceDisplay] {
        let isTransitioning = viewModel.isSequenceTransitioning
        let playbackTime = viewModel.highlightingTime
        let activeTimingTrack = viewModel.activeTimingTrack(for: chunk)
        let useCombinedPhases = viewModel.useCombinedPhases(for: chunk)
        let playbackDuration = viewModel.playbackDuration(for: chunk) ?? audioCoordinator.duration
        let timelineDuration = viewModel.timelineDuration(for: chunk)
        let durationValue: Double? = {
            if useCombinedPhases {
                return timelineDuration
            }
            if let timelineDuration {
                return timelineDuration
            }
            return playbackDuration > 0 ? playbackDuration : nil
        }()

        // Debug logging for sequence transitions
        if isTransitioning {
            interactiveTranscriptLogger.debug(
                "Building during transition: track=\(String(describing: activeTimingTrack), privacy: .public), time=\(playbackTime, privacy: .public), duration=\(durationValue ?? -1, privacy: .public)"
            )
        }

        if let pendingDisplay = pendingExplicitSentenceJumpDisplay(
            for: chunk,
            primaryTrack: activeTimingTrack
        ) {
            return [pendingDisplay]
        }
        if let anchorDisplay = recentSingleTrackAnchorDisplay(
            for: chunk,
            primaryTrack: activeTimingTrack
        ) {
            return [anchorDisplay]
        }

        if let activeSentence = TextPlayerTimeline.buildActiveSentenceDisplay(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack,
            chunkTime: playbackTime,
            audioDuration: durationValue,
            useCombinedPhases: useCombinedPhases
        ) {
            return [activeSentence]
        }
        if let selectedSentenceID,
           let selectedIndex = SentencePositionProvider.sentenceIndex(
               in: chunk,
               matching: selectedSentenceID
           ),
           let display = TextPlayerTimeline.buildInitialDisplay(
               sentences: chunk.sentences,
               activeIndex: selectedIndex,
               primaryTrack: activeTimingTrack
           ) {
            return [display]
        }
        let staticDisplay = TextPlayerTimeline.buildStaticDisplay(sentences: chunk.sentences)
        return TextPlayerTimeline.selectActiveSentence(from: staticDisplay)
    }

    var pendingExplicitSentenceJumpIsExpired: Bool {
        InteractiveSentenceJumpRenderLock.isExpired(
            startedAt: pendingExplicitSentenceJumpStartedAt
        )
    }

    private func pendingExplicitSentenceJumpDisplay(
        for chunk: InteractiveChunk,
        primaryTrack: TextPlayerTimingTrack
    ) -> TextPlayerSentenceDisplay? {
        guard let pending = pendingExplicitSentenceJumpID else { return nil }
        guard pendingExplicitSentenceJumpApplies(to: chunk) else { return nil }
        guard !pendingExplicitSentenceJumpIsExpired else { return nil }
        if explicitSentenceJumpReachedLivePlayback(pending, chunkID: pendingExplicitSentenceJumpChunkID, in: chunk) {
            return nil
        }
        return explicitSentenceJumpDisplay(
            sentenceNumber: pending,
            in: chunk,
            primaryTrack: primaryTrack
        )
    }

    private func recentSingleTrackAnchorDisplay(
        for chunk: InteractiveChunk,
        primaryTrack: TextPlayerTimingTrack
    ) -> TextPlayerSentenceDisplay? {
        guard pendingExplicitSentenceJumpID == nil else { return nil }
        guard let anchor = viewModel.recentSingleTrackSentenceAnchorNumber(in: chunk) else {
            return nil
        }
        guard !explicitSentenceJumpReachedLivePlayback(anchor, chunkID: chunk.id, in: chunk) else {
            viewModel.clearRecentSingleTrackSentenceAnchor(chunkID: chunk.id, sentenceNumber: anchor)
            return nil
        }
        return explicitSentenceJumpDisplay(
            sentenceNumber: anchor,
            in: chunk,
            primaryTrack: primaryTrack
        )
    }

    private func explicitSentenceJumpDisplay(
        sentenceNumber: Int,
        in chunk: InteractiveChunk,
        primaryTrack: TextPlayerTimingTrack
    ) -> TextPlayerSentenceDisplay? {
        guard let selectedIndex = SentencePositionProvider.sentenceIndex(
            in: chunk,
            matching: sentenceNumber
        ) else { return nil }
        return TextPlayerTimeline.buildInitialDisplay(
            sentences: chunk.sentences,
            activeIndex: selectedIndex,
            primaryTrack: primaryTrack
        )
    }

    private func pendingExplicitSentenceJumpApplies(to chunk: InteractiveChunk) -> Bool {
        InteractiveSentenceJumpRenderLock.applies(
            pendingChunkID: pendingExplicitSentenceJumpChunkID,
            to: chunk
        )
    }

    private func pendingExplicitSentenceJumpReachedLivePlayback(in chunk: InteractiveChunk) -> Bool {
        explicitSentenceJumpReachedLivePlayback(
            pendingExplicitSentenceJumpID,
            chunkID: pendingExplicitSentenceJumpChunkID,
            in: chunk
        )
    }

    private func explicitSentenceJumpReachedLivePlayback(
        _ sentenceNumber: Int?,
        chunkID: String?,
        in chunk: InteractiveChunk
    ) -> Bool {
        InteractiveSentenceJumpRenderLock.reachedLivePlayback(
            pendingSentenceNumber: sentenceNumber,
            pendingChunkID: chunkID,
            in: chunk,
            highlightingTime: viewModel.highlightingTime,
            currentChunkAudioIsActive: currentChunkAudioIsActive(for: chunk),
            startTimeForSentence: { sentenceNumber, chunk in
                viewModel.startTimeForSentence(sentenceNumber, in: chunk)
            }
        )
    }

    private func currentChunkAudioIsActive(for chunk: InteractiveChunk) -> Bool {
        guard viewModel.selectedChunkID == chunk.id else { return false }
        guard let activeURL = audioCoordinator.activeURL else { return false }
        return chunk.audioOptions.contains { option in
            option.streamURLs.contains(activeURL)
        }
    }


    func activeSentenceDisplay(for chunk: InteractiveChunk) -> TextPlayerSentenceDisplay? {
        let sentences = frozenTranscriptSentences ?? transcriptSentences(for: chunk)
        return sentences.first
    }

    func preferredNavigationKind(for chunk: InteractiveChunk) -> TextPlayerVariantKind {
        switch viewModel.activeTimingTrack(for: chunk) {
        case .original:
            return .original
        case .translation, .mix:
            return .translation
        }
    }

    func preferredNavigationVariant(
        for sentence: TextPlayerSentenceDisplay,
        chunk: InteractiveChunk
    ) -> TextPlayerVariantDisplay? {
        let visibleVariants = sentence.variants.filter { variant in
            visibleTracks.contains(variant.kind) && !variant.tokens.isEmpty
        }
        if visibleVariants.isEmpty {
            return sentence.variants.first(where: { !$0.tokens.isEmpty })
        }
        let preferredKind = preferredNavigationKind(for: chunk)
        if let preferred = visibleVariants.first(where: { $0.kind == preferredKind }) {
            return preferred
        }
        if let translation = visibleVariants.first(where: { $0.kind == .translation }) {
            return translation
        }
        if let original = visibleVariants.first(where: { $0.kind == .original }) {
            return original
        }
        if let transliteration = visibleVariants.first(where: { $0.kind == .transliteration }) {
            return transliteration
        }
        return visibleVariants.first
    }

    func resolvedSelection(for chunk: InteractiveChunk) -> TextPlayerWordSelection? {
        guard let sentence = activeSentenceDisplay(for: chunk) else { return nil }
        return resolvedSelection(in: sentence, chunk: chunk)
    }

    func resolvedSelection(
        in sentence: TextPlayerSentenceDisplay,
        chunk: InteractiveChunk
    ) -> TextPlayerWordSelection? {
        if let selection = linguistSelection,
           selection.sentenceIndex == sentence.index,
           let variant = sentence.variants.first(where: { $0.kind == selection.variantKind }),
           visibleTracks.contains(variant.kind),
           variant.tokens.indices.contains(selection.tokenIndex) {
            return selection
        }
        guard let variant = preferredNavigationVariant(for: sentence, chunk: chunk),
              !variant.tokens.isEmpty else {
            return nil
        }
        let fallbackIndex = variant.currentIndex ?? 0
        let clampedIndex = max(0, min(fallbackIndex, variant.tokens.count - 1))
        return TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: variant.kind,
            tokenIndex: clampedIndex
        )
    }

    func wordNavigationSentenceDisplay(for chunk: InteractiveChunk) -> TextPlayerSentenceDisplay? {
        guard let selection = linguistSelection else {
            return activeSentenceDisplay(for: chunk)
        }
        if let active = activeSentenceDisplay(for: chunk), active.index == selection.sentenceIndex {
            return active
        }
        guard chunk.sentences.indices.contains(selection.sentenceIndex) else {
            return activeSentenceDisplay(for: chunk)
        }
        let primaryTrack: TextPlayerTimingTrack = selection.variantKind == .original ? .original : .translation
        return TextPlayerTimeline.buildInitialDisplay(
            sentences: chunk.sentences,
            activeIndex: selection.sentenceIndex,
            primaryTrack: primaryTrack
        ) ?? activeSentenceDisplay(for: chunk)
    }

    func syncPausedSelection(for chunk: InteractiveChunk) {
        guard !audioCoordinator.isPlaying else { return }
        guard linguistSelection == nil else { return }
        guard let sentence = activeSentenceDisplay(for: chunk) else { return }
        let availableVariants = sentence.variants.filter { variant in
            visibleTracks.contains(variant.kind) && !variant.tokens.isEmpty
        }
        let targetVariant = availableVariants.first(where: { $0.kind == .translation })
            ?? availableVariants.first
            ?? sentence.variants.first(where: { !$0.tokens.isEmpty })
        guard let targetVariant else { return }
        let tokenIndex = activeTokenIndex(for: targetVariant)
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: targetVariant.kind,
            tokenIndex: tokenIndex
        )
    }

    private func activeTokenIndex(for variant: TextPlayerVariantDisplay) -> Int {
        guard !variant.tokens.isEmpty else { return 0 }
        let rawIndex: Int
        if let currentIndex = variant.currentIndex {
            rawIndex = currentIndex
        } else if variant.revealedCount > 0 {
            rawIndex = variant.revealedCount - 1
        } else {
            rawIndex = 0
        }
        return max(0, min(rawIndex, variant.tokens.count - 1))
    }

    @discardableResult
    func handleWordNavigation(_ delta: Int, in chunk: InteractiveChunk) -> Bool {
        keyboardShortcutDebugLog(
            "[KeyboardShortcut] Interactive wordNav requested delta=\(delta) " +
            "playing=\(audioCoordinator.isPlaying) " +
            "chunk=\(chunk.id)"
        )
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        linguistSelectionRange = nil
        guard let sentence = wordNavigationSentenceDisplay(for: chunk),
              let selection = resolvedSelection(in: sentence, chunk: chunk),
              let variant = sentence.variants.first(where: { $0.kind == selection.variantKind }) else {
            keyboardShortcutDebugLog("[KeyboardShortcut] Interactive wordNav unresolved selection")
            return false
        }
        guard !variant.tokens.isEmpty else {
            keyboardShortcutDebugLog("[KeyboardShortcut] Interactive wordNav empty tokens")
            return false
        }
        let direction = delta >= 0 ? 1 : -1
        let tokenCount = variant.tokens.count
        guard let resolvedIndex = wrappedLookupTokenIndex(
            in: variant.tokens,
            startingAt: selection.tokenIndex + direction,
            direction: direction
        ) else {
            keyboardShortcutDebugLog("[KeyboardShortcut] Interactive wordNav no lookup token")
            return false
        }
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: selection.variantKind,
            tokenIndex: resolvedIndex
        )
        #if DEBUG
        if ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1",
           linguistBubble != nil {
            InteractivePlayerE2EState.recordBubbleWordNavigation(
                direction: direction,
                sentenceIndex: sentence.index,
                variant: selection.variantKind,
                tokenIndex: resolvedIndex
            )
        }
        #endif
        if chunk.sentences.indices.contains(sentence.index) {
            selectedSentenceID = SentencePositionProvider.sentenceNumber(in: chunk, at: sentence.index)
        }
        keyboardShortcutDebugLog(
            "[KeyboardShortcut] Interactive wordNav selected sentence=\(sentence.index) " +
            "variant=\(String(describing: selection.variantKind)) " +
            "token=\(resolvedIndex)/\(tokenCount)"
        )
        if linguistBubble != nil {
            linguistVM.autoLookupTask?.cancel()
            handleLinguistLookupForCurrentSelection(in: chunk)
        } else {
            scheduleAutoLinguistLookup(in: chunk)
        }
        requestKeyboardShortcutFocus()
        return true
    }

    func handleWordRangeSelection(_ delta: Int, in chunk: InteractiveChunk) {
        guard !audioCoordinator.isPlaying else { return }
        guard let sentence = activeSentenceDisplay(for: chunk),
              let selection = resolvedSelection(for: chunk),
              let variant = sentence.variants.first(where: { $0.kind == selection.variantKind }) else {
            return
        }
        guard !variant.tokens.isEmpty else { return }
        let direction = delta >= 0 ? 1 : -1
        let tokenCount = variant.tokens.count
        let anchorIndex: Int
        let focusIndex: Int
        if let range = linguistSelectionRange,
           range.sentenceIndex == sentence.index,
           range.variantKind == selection.variantKind {
            anchorIndex = range.anchorIndex
            focusIndex = range.focusIndex
        } else {
            anchorIndex = selection.tokenIndex
            focusIndex = selection.tokenIndex
        }
        let nextIndex = max(0, min(focusIndex + direction, tokenCount - 1))
        linguistSelectionRange = TextPlayerWordSelectionRange(
            sentenceIndex: sentence.index,
            variantKind: selection.variantKind,
            anchorIndex: anchorIndex,
            focusIndex: nextIndex
        )
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: selection.variantKind,
            tokenIndex: nextIndex
        )
    }

    @discardableResult
    func handleTrackNavigation(_ delta: Int, in chunk: InteractiveChunk) -> Bool {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        linguistSelectionRange = nil
        guard let sentence = activeSentenceDisplay(for: chunk) else { return false }
        let variants = sentence.variants.filter { variant in
            visibleTracks.contains(variant.kind) && !variant.tokens.isEmpty
        }
        guard !variants.isEmpty else { return false }
        let currentSelection = resolvedSelection(for: chunk)
        let currentIndex: Int = {
            if let currentSelection,
               let index = variants.firstIndex(where: { $0.kind == currentSelection.variantKind }) {
                return index
            }
            let preferredKind = preferredNavigationKind(for: chunk)
            if let preferredIndex = variants.firstIndex(where: { $0.kind == preferredKind }) {
                return preferredIndex
            }
            return 0
        }()
        let nextIndex = currentIndex + delta
        guard variants.indices.contains(nextIndex) else { return false }
        let targetVariant = variants[nextIndex]
        let fallbackIndex = targetVariant.currentIndex ?? 0
        let preferredTokenIndex = currentSelection?.tokenIndex ?? fallbackIndex
        let clampedIndex = max(0, min(preferredTokenIndex, max(0, targetVariant.tokens.count - 1)))
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: targetVariant.kind,
            tokenIndex: clampedIndex
        )
        scheduleAutoLinguistLookup(in: chunk)
        return true
    }

    func handleTokenSeek(
        sentenceIndex: Int,
        sentenceNumber: Int?,
        variantKind: TextPlayerVariantKind,
        tokenIndex: Int,
        seekTime: Double?,
        shouldPlay: Bool,
        in chunk: InteractiveChunk
    ) {
        clearHeaderSentenceProgressDraft()
        let resolvedSentenceIndex = resolvedLocalSentenceIndex(
            for: sentenceIndex,
            sentenceNumber: sentenceNumber,
            in: chunk
        ) ?? sentenceIndex
        linguistSelectionRange = nil
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: resolvedSentenceIndex,
            variantKind: variantKind,
            tokenIndex: tokenIndex
        )
        linguistBubble = nil
        bubbleFocusEnabled = false
        let desiredAudioKind = audioKind(for: variantKind)
        let currentOption = viewModel.selectedAudioOption(for: chunk)

        if viewModel.isSequenceModeActive {
            let sequenceTrack: SequenceTrack = desiredAudioKind == .original ? .original : .translation
            if let target = viewModel.sequenceController.findSentenceTarget(
                resolvedSentenceIndex,
                preferredTrack: sequenceTrack
            ) {
                let sequenceTimingTrack: TextPlayerTimingTrack = target.track == .original ? .original : .translation
                let sequenceAudioKind: InteractiveChunk.AudioOption.Kind = target.track == .original ? .original : .translation
                let sequenceSeekTime = tokenSeekTime(
                    sentenceIndex: resolvedSentenceIndex,
                    variantKind: variantKind,
                    tokenIndex: tokenIndex,
                    timingTrack: sequenceTimingTrack,
                    audioDuration: estimatedDuration(for: sequenceAudioKind, in: chunk),
                    useCombinedPhases: false,
                    in: chunk
                )
                let targetTime = sequenceSeekTime ?? target.time
                viewModel.seekSequencePlayback(
                    segmentIndex: target.segmentIndex,
                    track: target.track,
                    time: targetTime,
                    autoPlay: shouldPlay
                )
                return
            }
        }

        var resolvedSeekTime = seekTime
        var shouldSwitch = false
        if let currentOption, currentOption.kind == .combined {
            let isCombinedQueue = currentOption.streamURLs.count > 1
            let isSingleTrackMode: Bool = {
                if case .singleTrack = audioModeManager.currentMode {
                    return true
                }
                return false
            }()
            let didSyncAudioMode = isCombinedQueue && isSingleTrackMode
                ? syncAudioModeForTokenSeek(
                    to: desiredAudioKind,
                    preservingSentenceIndex: resolvedSentenceIndex
                )
                : false
            let useCombinedPhases = !isCombinedQueue
            let timingTrack: TextPlayerTimingTrack = useCombinedPhases ? .mix : timingTrack(for: desiredAudioKind)
            if resolvedSeekTime == nil || didSyncAudioMode {
                let durationKind: InteractiveChunk.AudioOption.Kind = useCombinedPhases ? .combined : desiredAudioKind
                let audioDuration = estimatedDuration(for: durationKind, in: chunk)
                resolvedSeekTime = tokenSeekTime(
                    sentenceIndex: resolvedSentenceIndex,
                    variantKind: variantKind,
                    tokenIndex: tokenIndex,
                    timingTrack: timingTrack,
                    audioDuration: audioDuration,
                    useCombinedPhases: useCombinedPhases,
                    in: chunk
                )
            }
            if didSyncAudioMode {
                viewModel.prepareAudio(for: chunk, autoPlay: audioCoordinator.isPlaybackRequested)
            }
            if isCombinedQueue, !isSingleTrackMode, desiredAudioKind == .translation {
                let offset = estimatedDuration(for: .original, in: chunk) ?? 0
                if let value = resolvedSeekTime {
                    resolvedSeekTime = value + offset
                } else if offset > 0 {
                    resolvedSeekTime = offset
                }
            }
        } else if let targetOption = chunk.audioOptions.first(where: { $0.kind == desiredAudioKind }) {
            shouldSwitch = targetOption.id != currentOption?.id
            let didSyncAudioMode = syncAudioModeForTokenSeek(
                to: desiredAudioKind,
                preservingSentenceIndex: resolvedSentenceIndex
            )
            let useCombinedPhases = targetOption.kind == .combined && targetOption.streamURLs.count == 1
            let timingTrack: TextPlayerTimingTrack = useCombinedPhases ? .mix : timingTrack(for: desiredAudioKind)
            if resolvedSeekTime == nil || shouldSwitch || didSyncAudioMode {
                let audioDuration = estimatedDuration(for: desiredAudioKind, in: chunk)
                resolvedSeekTime = tokenSeekTime(
                    sentenceIndex: resolvedSentenceIndex,
                    variantKind: variantKind,
                    tokenIndex: tokenIndex,
                    timingTrack: timingTrack,
                    audioDuration: audioDuration,
                    useCombinedPhases: useCombinedPhases,
                    in: chunk
                )
            }
            if didSyncAudioMode && !shouldSwitch {
                viewModel.prepareAudio(for: chunk, autoPlay: audioCoordinator.isPlaybackRequested)
            }
        }

        if shouldSwitch, let targetOption = chunk.audioOptions.first(where: { $0.kind == desiredAudioKind }) {
            viewModel.selectAudioTrack(id: targetOption.id)
        }

        if let resolvedSeekTime, resolvedSeekTime.isFinite {
            viewModel.seekPlaybackWhenReady(to: resolvedSeekTime, in: chunk, autoPlay: shouldPlay)
            if !shouldPlay, audioCoordinator.isPlaying {
                audioCoordinator.pause()
            }
            return
        }
        if let sentenceNumber, sentenceNumber > 0 {
            viewModel.jumpToSentence(sentenceNumber, autoPlay: shouldPlay)
        }
    }

    private func resolvedLocalSentenceIndex(
        for sentenceIndex: Int,
        sentenceNumber: Int?,
        in chunk: InteractiveChunk
    ) -> Int? {
        if chunk.sentences.indices.contains(sentenceIndex) {
            return sentenceIndex
        }
        if let sentenceNumber,
           let index = SentencePositionProvider.sentenceIndex(in: chunk, matching: sentenceNumber) {
            return index
        }
        if let index = chunk.sentences.firstIndex(where: { sentence in
            sentence.id == sentenceIndex || sentence.displayIndex == sentenceIndex
        }) {
            return index
        }
        return nil
    }

    private func resolveTokenText(
        sentenceIndex: Int,
        variantKind: TextPlayerVariantKind,
        tokenIndex: Int,
        in chunk: InteractiveChunk
    ) -> String? {
        guard let sentence = chunk.sentences.first(where: { $0.id == sentenceIndex }) else { return nil }
        let tokens: [String]
        switch variantKind {
        case .original:
            tokens = sentence.originalTokens
        case .translation:
            tokens = sentence.translationTokens
        case .transliteration:
            tokens = sentence.transliterationTokens
        }
        guard tokens.indices.contains(tokenIndex) else { return nil }
        return tokens[tokenIndex]
    }

    private func audioKind(for variantKind: TextPlayerVariantKind) -> InteractiveChunk.AudioOption.Kind {
        switch variantKind {
        case .original:
            return .original
        case .translation, .transliteration:
            return .translation
        }
    }

    @discardableResult
    private func syncAudioModeForTokenSeek(
        to desiredAudioKind: InteractiveChunk.AudioOption.Kind,
        preservingSentenceIndex sentenceIndex: Int
    ) -> Bool {
        let desiredTrack: SequenceTrack
        switch desiredAudioKind {
        case .original:
            desiredTrack = .original
        case .translation:
            desiredTrack = .translation
        case .combined, .other:
            return false
        }

        let previousMode = audioModeManager.currentMode
        audioModeManager.setTracks(
            original: desiredTrack == .original,
            translation: desiredTrack == .translation,
            preservingPosition: sentenceIndex
        )
        viewModel.rememberAudioModePreference(audioModeManager.currentMode)
        viewModel.sequenceController.audioMode = audioModeManager.currentMode
        return previousMode != audioModeManager.currentMode
    }

    private func timingTrack(for audioKind: InteractiveChunk.AudioOption.Kind) -> TextPlayerTimingTrack {
        switch audioKind {
        case .original:
            return .original
        case .translation, .combined, .other:
            return .translation
        }
    }

    private func estimatedDuration(
        for kind: InteractiveChunk.AudioOption.Kind,
        in chunk: InteractiveChunk
    ) -> Double? {
        if let duration = viewModel.durationForOption(kind: kind, in: chunk), duration > 0 {
            return duration
        }
        if let duration = viewModel.combinedTrackDuration(kind: kind, in: chunk), duration > 0 {
            return duration
        }
        if let duration = viewModel.fallbackDuration(for: chunk, kind: kind), duration > 0 {
            return duration
        }
        return nil
    }

    private func tokenSeekTime(
        sentenceIndex: Int,
        variantKind: TextPlayerVariantKind,
        tokenIndex: Int,
        timingTrack: TextPlayerTimingTrack,
        audioDuration: Double?,
        useCombinedPhases: Bool,
        in chunk: InteractiveChunk
    ) -> Double? {
        guard let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: chunk.sentences,
            activeTimingTrack: timingTrack,
            audioDuration: audioDuration,
            useCombinedPhases: useCombinedPhases,
            timingVersion: chunk.timingVersion
        ),
        let runtime = timelineSentences.first(where: { $0.index == sentenceIndex }) else {
            return nil
        }
        guard let variantRuntime = runtime.variants[variantKind] else {
            return runtime.startTime
        }
        let revealTimes = variantRuntime.revealTimes
        guard !revealTimes.isEmpty else {
            return runtime.startTime
        }
        let clampedIndex = max(0, min(tokenIndex, revealTimes.count - 1))
        let value = revealTimes[clampedIndex]
        return value.isFinite ? value : runtime.startTime
    }

    private func wrappedLookupTokenIndex(
        in tokens: [String],
        startingAt index: Int,
        direction: Int
    ) -> Int? {
        guard !tokens.isEmpty else { return nil }
        let step = direction >= 0 ? 1 : -1
        var candidate = index
        while tokens.indices.contains(candidate) {
            if sanitizeLookupQuery(tokens[candidate]) != nil {
                return candidate
            }
            candidate += step
        }
        candidate = direction >= 0 ? 0 : tokens.count - 1
        while tokens.indices.contains(candidate) {
            if sanitizeLookupQuery(tokens[candidate]) != nil {
                return candidate
            }
            candidate += step
        }
        return nil
    }
}
