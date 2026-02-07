import Foundation

extension InteractivePlayerViewModel {
    func prefetchAdjacentSentencesIfNeeded(isPlaying: Bool) {
        guard let context = jobContext, let chunk = selectedChunk else { return }
        if chunkNeedsTranscriptLoad(chunk),
           !chunkMetadataLoaded.contains(chunk.id),
           !chunkMetadataLoading.contains(chunk.id) {
            Task { [weak self] in
                await self?.loadChunkMetadataIfNeeded(for: chunk.id)
            }
        }
        guard let activeNumber = activeSentenceNumber(in: chunk) else { return }
        if !isPlaying && !chunk.sentences.isEmpty {
            return
        }
        if !chunk.sentences.isEmpty {
            if lastPrefetchSentenceNumber == activeNumber {
                return
            }
            // Track direction from sentence number changes (mirrors Web directionRef)
            if let last = lastPrefetchSentenceNumber {
                if activeNumber > last {
                    prefetchDirection = .forward
                } else if activeNumber < last {
                    prefetchDirection = .backward
                }
            }
            lastPrefetchSentenceNumber = activeNumber
        }
        Task { [weak self] in
            await self?.prefetchAdjacentSentences(
                around: activeNumber,
                in: context,
                selectedChunk: chunk,
                isPlaying: isPlaying
            )
        }
    }

    private func activeSentenceNumber(in chunk: InteractiveChunk) -> Int? {
        if let active = activeSentence(at: highlightingTime) {
            return active.displayIndex ?? active.id
        }
        if let start = chunk.startSentence, start > 0 {
            return start
        }
        return nil
    }

    private func chunkNeedsTranscriptLoad(_ chunk: InteractiveChunk) -> Bool {
        guard !chunk.sentences.isEmpty else { return true }
        return !chunk.sentences.contains { sentence in
            !sentence.originalTokens.isEmpty
                || !sentence.translationTokens.isEmpty
                || !sentence.transliterationTokens.isEmpty
        }
    }

    /// Number of extra chunks to prefetch ahead when the selected chunk has only one sentence.
    /// Matches the Web's SINGLE_SENTENCE_PREFETCH_AHEAD constant.
    private static let singleSentencePrefetchAhead = 3

    private func prefetchAdjacentSentences(
        around sentenceNumber: Int,
        in context: JobContext,
        selectedChunk: InteractiveChunk,
        isPlaying: Bool
    ) async {
        guard sentenceNumber > 0 else { return }
        // Direction-aware asymmetric prefetch (mirrors Web behavior)
        let skewForward = isPlaying && prefetchDirection == .forward
        let backwardRadius = skewForward ? 1 : metadataPrefetchRadius
        let forwardRadius = skewForward ? metadataPrefetchRadius + 1 : metadataPrefetchRadius
        var targets: [InteractiveChunk] = []
        for offset in (-backwardRadius)...forwardRadius {
            let candidate = sentenceNumber + offset
            guard candidate > 0 else { continue }
            if let chunk = resolveChunk(containing: candidate, in: context) {
                targets.append(chunk)
            }
        }
        if targets.isEmpty {
            targets = prefetchFallbackChunks(from: selectedChunk, in: context, isPlaying: isPlaying)
        }

        // Single-sentence-chunk lookahead: when the selected chunk has only one sentence
        // (common in poetry or short-form content), prefetch additional chunks ahead
        // to avoid stuttering during rapid auto-advance.
        let isSingleSentence = selectedChunk.sentences.count == 1
            || (selectedChunk.startSentence != nil
                && selectedChunk.endSentence != nil
                && selectedChunk.startSentence == selectedChunk.endSentence)
        if isSingleSentence {
            var ahead = selectedChunk
            for _ in 0..<Self.singleSentencePrefetchAhead {
                guard let next = context.nextChunk(after: ahead.id) else { break }
                targets.append(next)
                ahead = next
            }
        }

        // Use Dictionary(_:uniquingKeysWith:) to handle duplicate chunk IDs gracefully
        // (multiple sentence numbers can resolve to the same chunk)
        let uniqueTargets = Dictionary(targets.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
        for chunk in uniqueTargets.values {
            await loadChunkMetadataIfNeeded(for: chunk.id)
            prefetchChunkMediaIfNeeded(for: chunk)
        }
    }

    private func prefetchFallbackChunks(
        from chunk: InteractiveChunk,
        in context: JobContext,
        isPlaying: Bool
    ) -> [InteractiveChunk] {
        let skewForward = isPlaying && prefetchDirection == .forward
        let backwardRadius = skewForward ? 1 : metadataPrefetchRadius
        let forwardRadius = skewForward ? metadataPrefetchRadius + 1 : metadataPrefetchRadius
        var targets: [InteractiveChunk] = [chunk]
        var previous = chunk
        for _ in 0..<backwardRadius {
            guard let next = context.previousChunk(before: previous.id) else { break }
            targets.append(next)
            previous = next
        }
        var forward = chunk
        for _ in 0..<forwardRadius {
            guard let next = context.nextChunk(after: forward.id) else { break }
            targets.append(next)
            forward = next
        }
        return targets
    }

    private func prefetchChunkMediaIfNeeded(for chunk: InteractiveChunk) {
        let isSequence = audioModeManager?.currentMode == .sequence
        if isSequence {
            // Sequence mode: prefetch both original and translation tracks
            prefetchAudioOption(
                chunk.audioOptions.first(where: { $0.kind == .original }),
                for: chunk
            )
            prefetchAudioOption(
                chunk.audioOptions.first(where: { $0.kind == .translation }),
                for: chunk
            )
        } else {
            // Single-track mode: prefetch only the preferred track
            prefetchAudioOption(preferredAudioOption(for: chunk), for: chunk)
        }
    }

    private func prefetchAudioOption(
        _ option: InteractiveChunk.AudioOption?,
        for chunk: InteractiveChunk
    ) {
        guard let track = option else { return }
        guard let url = track.streamURLs.first else { return }
        guard !prefetchedAudioURLs.contains(url) else { return }
        prefetchedAudioURLs.insert(url)
        Task.detached(priority: .background) {
            var request = URLRequest(url: url)
            request.timeoutInterval = 6
            request.setValue("bytes=0-2047", forHTTPHeaderField: "Range")
            _ = try? await URLSession.shared.data(for: request)
        }
    }

    private func preferredAudioOption(for chunk: InteractiveChunk) -> InteractiveChunk.AudioOption? {
        if let selectedID = selectedAudioTrackID,
           let match = chunk.audioOptions.first(where: { $0.id == selectedID }) {
            return match
        }
        if let preferred = preferredAudioKind,
           let match = chunk.audioOptions.first(where: { $0.kind == preferred }) {
            return match
        }
        return chunk.audioOptions.first
    }
}
