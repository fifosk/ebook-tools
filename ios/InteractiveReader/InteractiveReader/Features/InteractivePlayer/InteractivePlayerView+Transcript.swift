import SwiftUI

extension InteractivePlayerView {
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
                selectedSentenceID = newValue
                if chapterRange != nil {
                    viewModel.jumpToSentence(newValue, autoPlay: audioCoordinator.isPlaying)
                    return
                }
                guard let target = entries.first(where: { $0.id == newValue }) else { return }
                guard let startTime = target.startTime else { return }
                viewModel.seekPlayback(to: startTime, in: chunk)
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
                let id = sentence.displayIndex ?? sentence.id
                startTimes[id] = runtime.startTime
            }
        }
        let entries = sentences.map { sentence -> SentenceOption in
            let id = sentence.displayIndex ?? sentence.id
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
        let time = viewModel.highlightingTime
        guard time.isFinite else { return }
        guard let sentence = viewModel.activeSentence(at: time) else { return }
        let id = sentence.displayIndex ?? sentence.id
        if selectedSentenceID != id {
            selectedSentenceID = id
        }
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
            print("[TranscriptView] Building during transition: track=\(activeTimingTrack), time=\(String(format: "%.3f", playbackTime)), duration=\(durationValue.map { String(format: "%.3f", $0) } ?? "nil")")
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
        let staticDisplay = TextPlayerTimeline.buildStaticDisplay(sentences: chunk.sentences)
        return TextPlayerTimeline.selectActiveSentence(from: staticDisplay)
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

    func handleWordNavigation(_ delta: Int, in chunk: InteractiveChunk) {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        linguistSelectionRange = nil
        guard let sentence = activeSentenceDisplay(for: chunk),
              let selection = resolvedSelection(for: chunk),
              let variant = sentence.variants.first(where: { $0.kind == selection.variantKind }) else {
            return
        }
        guard !variant.tokens.isEmpty else { return }
        let direction = delta >= 0 ? 1 : -1
        let candidate = selection.tokenIndex + direction
        let tokenCount = variant.tokens.count
        let resolvedIndex = ((candidate % tokenCount) + tokenCount) % tokenCount
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: selection.variantKind,
            tokenIndex: resolvedIndex
        )
        scheduleAutoLinguistLookup(in: chunk)
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
        in chunk: InteractiveChunk
    ) {
        linguistSelectionRange = nil
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentenceIndex,
            variantKind: variantKind,
            tokenIndex: tokenIndex
        )
        linguistBubble = nil
        bubbleFocusEnabled = false
        let desiredAudioKind = audioKind(for: variantKind)
        let currentOption = viewModel.selectedAudioOption(for: chunk)

        var resolvedSeekTime = seekTime
        var shouldSwitch = false
        if let currentOption, currentOption.kind == .combined {
            let isCombinedQueue = currentOption.streamURLs.count > 1
            let useCombinedPhases = !isCombinedQueue
            let timingTrack: TextPlayerTimingTrack = useCombinedPhases ? .mix : timingTrack(for: desiredAudioKind)
            if resolvedSeekTime == nil {
                let durationKind: InteractiveChunk.AudioOption.Kind = useCombinedPhases ? .combined : desiredAudioKind
                let audioDuration = estimatedDuration(for: durationKind, in: chunk)
                resolvedSeekTime = tokenSeekTime(
                    sentenceIndex: sentenceIndex,
                    variantKind: variantKind,
                    tokenIndex: tokenIndex,
                    timingTrack: timingTrack,
                    audioDuration: audioDuration,
                    useCombinedPhases: useCombinedPhases,
                    in: chunk
                )
            }
            if isCombinedQueue, desiredAudioKind == .translation {
                let offset = estimatedDuration(for: .original, in: chunk) ?? 0
                if let value = resolvedSeekTime {
                    resolvedSeekTime = value + offset
                } else if offset > 0 {
                    resolvedSeekTime = offset
                }
            }
        } else if let targetOption = chunk.audioOptions.first(where: { $0.kind == desiredAudioKind }) {
            shouldSwitch = targetOption.id != currentOption?.id
            let useCombinedPhases = targetOption.kind == .combined && targetOption.streamURLs.count == 1
            let timingTrack: TextPlayerTimingTrack = useCombinedPhases ? .mix : timingTrack(for: desiredAudioKind)
            if resolvedSeekTime == nil || shouldSwitch {
                let audioDuration = estimatedDuration(for: desiredAudioKind, in: chunk)
                resolvedSeekTime = tokenSeekTime(
                    sentenceIndex: sentenceIndex,
                    variantKind: variantKind,
                    tokenIndex: tokenIndex,
                    timingTrack: timingTrack,
                    audioDuration: audioDuration,
                    useCombinedPhases: useCombinedPhases,
                    in: chunk
                )
            }
        }

        if shouldSwitch, let targetOption = chunk.audioOptions.first(where: { $0.kind == desiredAudioKind }) {
            viewModel.selectAudioTrack(id: targetOption.id)
        }

        if let resolvedSeekTime, resolvedSeekTime.isFinite {
            viewModel.seekPlayback(to: resolvedSeekTime, in: chunk)
            return
        }
        if let sentenceNumber, sentenceNumber > 0 {
            viewModel.jumpToSentence(sentenceNumber, autoPlay: audioCoordinator.isPlaybackRequested)
        }
    }

    private func audioKind(for variantKind: TextPlayerVariantKind) -> InteractiveChunk.AudioOption.Kind {
        switch variantKind {
        case .original:
            return .original
        case .translation, .transliteration:
            return .translation
        }
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
}
