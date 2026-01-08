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
        let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: durationValue,
            useCombinedPhases: useCombinedPhases
        )
        let isVariantVisible: (TextPlayerVariantKind) -> Bool = { visibleTracks.contains($0) }
        let timelineDisplay = timelineSentences.flatMap { runtime in
            TextPlayerTimeline.buildTimelineDisplay(
                timelineSentences: runtime,
                chunkTime: playbackTime,
                audioDuration: durationValue,
                isVariantVisible: isVariantVisible
            )
        }
        let staticDisplay = TextPlayerTimeline.buildStaticDisplay(
            sentences: chunk.sentences,
            isVariantVisible: isVariantVisible
        )
        return TextPlayerTimeline.selectActiveSentence(
            from: timelineDisplay?.sentences ?? staticDisplay
        )
    }

    func activeSentenceDisplay(for chunk: InteractiveChunk) -> TextPlayerSentenceDisplay? {
        transcriptSentences(for: chunk).first
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
        let preferredKind = preferredNavigationKind(for: chunk)
        if let preferred = sentence.variants.first(where: { $0.kind == preferredKind }) {
            return preferred
        }
        if let translation = sentence.variants.first(where: { $0.kind == .translation }) {
            return translation
        }
        if let original = sentence.variants.first(where: { $0.kind == .original }) {
            return original
        }
        if let transliteration = sentence.variants.first(where: { $0.kind == .transliteration }) {
            return transliteration
        }
        return sentence.variants.first
    }

    func resolvedSelection(for chunk: InteractiveChunk) -> TextPlayerWordSelection? {
        guard let sentence = activeSentenceDisplay(for: chunk) else { return nil }
        if let selection = linguistSelection,
           selection.sentenceIndex == sentence.index,
           let variant = sentence.variants.first(where: { $0.kind == selection.variantKind }),
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

    func handleWordNavigation(_ delta: Int, in chunk: InteractiveChunk) {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        guard let sentence = activeSentenceDisplay(for: chunk),
              let selection = resolvedSelection(for: chunk),
              let variant = sentence.variants.first(where: { $0.kind == selection.variantKind }) else {
            return
        }
        let nextIndex = selection.tokenIndex + delta
        let resolvedIndex = variant.tokens.indices.contains(nextIndex) ? nextIndex : selection.tokenIndex
        linguistSelection = TextPlayerWordSelection(
            sentenceIndex: sentence.index,
            variantKind: selection.variantKind,
            tokenIndex: resolvedIndex
        )
        scheduleAutoLinguistLookup(in: chunk)
    }

    func handleTrackNavigation(_ delta: Int, in chunk: InteractiveChunk) {
        if audioCoordinator.isPlaying {
            audioCoordinator.pause()
        }
        guard let sentence = activeSentenceDisplay(for: chunk) else { return }
        let variants = sentence.variants
        guard !variants.isEmpty else { return }
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
        let nextIndex = (currentIndex + delta + variants.count) % variants.count
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
