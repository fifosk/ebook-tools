import SwiftUI

// MARK: - Search State Extension

extension InteractivePlayerView {
    func handleSearchResult(_ result: MediaSearchResult) {
        guard let targetSentence = searchViewModel.calculateTargetSentence(from: result) else {
            return
        }
        // Use jumpToSentence which handles metadata loading, sequence playback, and seeking
        viewModel.jumpToSentence(targetSentence, autoPlay: audioCoordinator.isPlaybackRequested)
        searchViewModel.dismiss()
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

    func toggleTextSearchOverlay() {
        setTextSearchOverlayVisible(!searchViewModel.isExpanded)
    }

    func dismissTextSearchOverlay() {
        setTextSearchOverlayVisible(false)
    }

    func handleTextSearchQueryChange() {
        performDebouncedSearch()
    }

    func handleTextSearchSubmit() {
        performSearch()
    }

    func handleTextSearchSelection(_ result: MediaSearchResult) {
        handleSearchResult(result)
    }

    private func setTextSearchOverlayVisible(_ isVisible: Bool) {
        withAnimation(.easeOut(duration: 0.2)) {
            searchViewModel.isExpanded = isVisible
        }
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
            sizeScale: infoPillScale,
            onTap: toggleTextSearchOverlay
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
            onSearch: { _ in handleTextSearchSubmit() },
            onSelect: handleTextSearchSelection
        )
        .onChange(of: searchViewModel.query) { _, _ in handleTextSearchQueryChange() }
    }
}
