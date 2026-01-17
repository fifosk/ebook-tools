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
            useCombinedPhases: useCombinedPhases
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

    @discardableResult
    func handleTrackNavigation(_ delta: Int, in chunk: InteractiveChunk) -> Bool {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
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
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentenceIndex,
            variantKind: variantKind,
            tokenIndex: tokenIndex
        )
        linguistBubble = nil
        if let seekTime, seekTime.isFinite {
            viewModel.seekPlayback(to: seekTime, in: chunk)
            return
        }
        if let sentenceNumber, sentenceNumber > 0 {
            viewModel.jumpToSentence(sentenceNumber, autoPlay: audioCoordinator.isPlaybackRequested)
        }
    }
}
