import SwiftUI

// MARK: - Search Functionality for Video Player

extension VideoPlayerView {
    func handleSearchResult(_ result: MediaSearchResult) {
        guard let seekTime = searchViewModel.calculateSeekTime(from: result) else {
            return
        }

        // Seek to the calculated time
        coordinator.seek(to: seekTime)

        // Update scrubber value
        scrubberValue = seekTime

        // Dismiss search overlay
        searchViewModel.dismiss()

        // Keep controls hidden on tvOS to maximize screen real estate
    }

    func performVideoSearch() {
        guard let config = appState.configuration else { return }
        let client = APIClient(configuration: config)
        searchViewModel.search(jobId: resolvedBookmarkJobId, using: client)
    }

    func performDebouncedVideoSearch() {
        guard let config = appState.configuration else { return }
        let client = APIClient(configuration: config)
        searchViewModel.debouncedSearch(jobId: resolvedBookmarkJobId, using: client)
    }

    func toggleVideoSearchOverlay() {
        setVideoSearchOverlayVisible(!searchViewModel.isExpanded)
        if searchViewModel.isExpanded {
            controlsHideTask?.cancel()
        }
    }

    func dismissVideoSearchOverlay() {
        setVideoSearchOverlayVisible(false)
        scheduleControlsAutoHide()
    }

    func handleVideoSearchQueryChange() {
        performDebouncedVideoSearch()
    }

    func handleVideoSearchSubmit() {
        performVideoSearch()
    }

    func handleVideoSearchSelection(_ result: MediaSearchResult) {
        handleSearchResult(result)
    }

    private func setVideoSearchOverlayVisible(_ isVisible: Bool) {
        withAnimation(.easeOut(duration: 0.2)) {
            searchViewModel.isExpanded = isVisible
        }
    }
}

// MARK: - Search UI Components for Video Player

extension VideoPlayerView {
    private var isTV: Bool {
        VideoPlayerPlatform.isTV
    }

    @ViewBuilder
    var videoSearchPillView: some View {
        MediaSearchPillView(
            isExpanded: $searchViewModel.isExpanded,
            resultCount: searchViewModel.resultCount,
            isSearching: searchViewModel.isSearching,
            isTV: isTV,
            sizeScale: videoHeaderScaleValue,
            onTap: toggleVideoSearchOverlay
        )
    }

    @ViewBuilder
    var videoSearchOverlayView: some View {
        MediaSearchOverlayView(
            isPresented: $searchViewModel.isExpanded,
            query: $searchViewModel.query,
            state: $searchViewModel.state,
            jobId: resolvedBookmarkJobId,
            isTV: isTV,
            sizeScale: videoHeaderScaleValue,
            actionType: .seekToTime,
            onSearch: { _ in handleVideoSearchSubmit() },
            onSelect: handleVideoSearchSelection
        )
        .onChange(of: searchViewModel.query) { _, _ in handleVideoSearchQueryChange() }
    }

    @ViewBuilder
    var videoSearchOverlayContainer: some View {
        if searchViewModel.isExpanded {
            ZStack {
                // Background dismissal area
                Color.black.opacity(0.3)
                    #if !os(tvOS)
                    .onTapGesture(perform: dismissVideoSearchOverlay)
                    #endif

                // Search content
                VStack {
                    HStack {
                        Spacer()
                        videoSearchOverlayView
                            .padding(.top, headerTopPadding + 60)
                            .padding(.trailing, 12)
                    }
                    Spacer()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            #if os(tvOS)
            .focusScope(searchFocusNamespace)
            .onExitCommand(perform: dismissVideoSearchOverlay)
            #endif
            .zIndex(100)
        }
    }

    private var headerTopPadding: CGFloat {
        #if os(tvOS)
        return 40
        #else
        return 10
        #endif
    }

    var videoHeaderScaleValue: CGFloat {
        #if os(tvOS)
        return 1.0
        #else
        return VideoPlayerPlatform.isPad ? 1.5 : 1.0
        #endif
    }
}
