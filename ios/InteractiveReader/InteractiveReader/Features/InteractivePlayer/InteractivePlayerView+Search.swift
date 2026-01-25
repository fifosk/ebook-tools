import SwiftUI

// MARK: - Search State Extension

extension InteractivePlayerView {
    func handleSearchResult(_ result: MediaSearchResult) {
        guard let targetSentence = searchViewModel.calculateTargetSentence(from: result) else {
            return
        }

        // Find the chunk containing this sentence
        guard let context = viewModel.jobContext else { return }

        // Look for the chunk that contains this sentence
        var targetChunk: InteractiveChunk?
        for chunk in context.chunks {
            if let start = chunk.startSentence, let end = chunk.endSentence {
                if targetSentence >= start && targetSentence <= end {
                    targetChunk = chunk
                    break
                }
            }
        }

        if let chunk = targetChunk {
            // If we need to change chunks, do so
            if chunk.id != viewModel.selectedChunkID {
                viewModel.pendingSentenceJump = PendingSentenceJump(
                    chunkID: chunk.id,
                    sentenceNumber: targetSentence
                )
                viewModel.selectedChunkID = chunk.id
            } else {
                // Same chunk, just jump to sentence
                jumpToSentence(targetSentence, in: chunk)
            }
        }

        // Dismiss search overlay
        searchViewModel.dismiss()
    }

    func jumpToSentence(_ sentenceNumber: Int, in chunk: InteractiveChunk) {
        // Find the sentence in the chunk by matching sentence id
        // Sentence.id represents the sentence number in the chunk
        if let sentence = chunk.sentences.first(where: { $0.id == sentenceNumber }) {
            selectedSentenceID = sentence.id

            // Calculate seek time based on sentence timing
            if !sentence.timeline.isEmpty {
                let seekTime = calculateSentenceStartTime(
                    sentenceId: sentenceNumber,
                    sentences: chunk.sentences
                )
                audioCoordinator.seek(to: seekTime)
            }
        } else if let sentence = chunk.sentences.first(where: { $0.id >= sentenceNumber }) {
            // Find the nearest sentence if exact match not found
            selectedSentenceID = sentence.id

            let seekTime = calculateSentenceStartTime(
                sentenceId: sentence.id,
                sentences: chunk.sentences
            )
            audioCoordinator.seek(to: seekTime)
        }
    }

    private func calculateSentenceStartTime(sentenceId: Int, sentences: [InteractiveChunk.Sentence]) -> Double {
        var time: Double = 0
        for sentence in sentences {
            if sentence.id >= sentenceId {
                break
            }
            if let duration = sentence.totalDuration {
                time += duration
            }
        }
        return time
    }

    func performSearch() {
        guard let config = appState.configuration else { return }
        let client = APIClient(configuration: config)
        searchViewModel.search(jobId: viewModel.jobId, using: client)
    }

    func performDebouncedSearch() {
        guard let config = appState.configuration else { return }
        let client = APIClient(configuration: config)
        searchViewModel.debouncedSearch(jobId: viewModel.jobId, using: client)
    }
}

// MARK: - Search UI Components for Interactive Player

extension InteractivePlayerView {
    @ViewBuilder
    var searchPillView: some View {
        MediaSearchPillView(
            isExpanded: $searchViewModel.isExpanded,
            resultCount: searchViewModel.resultCount,
            isSearching: searchViewModel.isSearching,
            isTV: isTV,
            sizeScale: infoHeaderScale,
            onTap: {
                withAnimation(.easeOut(duration: 0.2)) {
                    searchViewModel.isExpanded.toggle()
                }
            }
        )
    }

    @ViewBuilder
    var searchOverlayView: some View {
        MediaSearchOverlayView(
            isPresented: $searchViewModel.isExpanded,
            query: $searchViewModel.query,
            state: $searchViewModel.state,
            jobId: viewModel.jobId,
            isTV: isTV,
            sizeScale: infoHeaderScale,
            actionType: .jumpToSentence,
            onSearch: { _ in performSearch() },
            onSelect: { result in handleSearchResult(result) }
        )
        .onChange(of: searchViewModel.query) { _, _ in
            performDebouncedSearch()
        }
    }
}
