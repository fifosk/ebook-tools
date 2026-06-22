import SwiftUI

extension LibraryPlaybackView {
    #if os(tvOS)
    var tvVideoBody: some View {
        ZStack {
            switch viewModel.loadState {
            case .idle, .loading:
                loadingView
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            case let .error(message):
                errorView(message: message)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .loaded:
                if let videoURL {
                    libraryVideoPlayer(videoURL: videoURL)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    LibraryPlaybackUnavailableView(usesDarkBackground: true)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
        }
        .ignoresSafeArea()
        .toolbar(.hidden, for: .navigationBar)
    }
    #endif

    #if !os(tvOS)
    @ViewBuilder
    var fullscreenVideoPlayer: some View {
        if let videoURL {
            libraryVideoPlayer(videoURL: videoURL)
                .ignoresSafeArea()
        } else {
            Color.black
                .ignoresSafeArea()
        }
    }

    var videoPreview: some View {
        Button {
            handleVideoPreviewTap()
        } label: {
            ZStack {
                if let coverURL {
                    AsyncImage(url: coverURL) { phase in
                        if let image = phase.image {
                            image.resizable().scaledToFill()
                        } else {
                            Color.black.opacity(0.2)
                        }
                    }
                } else {
                    Color.black.opacity(0.2)
                }
                Color.black.opacity(0.35)
                VStack(spacing: 10) {
                    Image(systemName: "play.fill")
                        .font(.system(size: 34, weight: .semibold))
                    Text("Play Video")
                        .font(.headline)
                }
                .foregroundStyle(.white)
            }
            .clipShape(RoundedRectangle(cornerRadius: 14))
        }
        .buttonStyle(.plain)
    }

    #if os(iOS)
    var videoPreviewDragGesture: some Gesture {
        DragGesture(minimumDistance: 10)
            .onChanged(handleVideoPreviewDragChange)
            .onEnded(handleVideoPreviewDragEnd)
    }
    #else
    var videoPreviewDragGesture: some Gesture {
        DragGesture().onChanged { _ in }
    }
    #endif
    #endif

    func libraryVideoPlayer(videoURL: URL) -> VideoPlayerView {
        VideoPlayerView(
            videoURL: videoURL,
            subtitleTracks: subtitleTracks,
            metadata: videoMetadata,
            autoPlay: videoAutoPlay,
            resumeTime: videoResumeTime,
            resumeActionID: videoResumeActionID,
            nowPlaying: nowPlaying,
            linguistInputLanguage: linguistInputLanguage,
            linguistLookupLanguage: linguistLookupLanguage,
            onPlaybackProgress: handleVideoPlaybackProgress,
            bookmarkUserId: resumeUserId,
            bookmarkJobId: item.jobId,
            bookmarkItemType: bookmarkItemType
        )
    }

    #if !os(tvOS)
    func handleVideoPlayerDismiss() {
        dismiss()
    }

    #if os(iOS)
    func handleEdgeSwipeBack() {
        dismiss()
    }
    #endif

    func handleVideoPreviewTap() {
        if let manager = resumeManager,
           let resumeEntry = manager.resolveResumeEntry(isVideoPreferred: isVideoPreferred) {
            applyResume(resumeEntry)
        } else {
            startVideoPlayback(at: 0, presentPlayer: true)
        }
    }

    #if os(iOS)
    func handleVideoPreviewDragChange(_ value: DragGesture.Value) {
        guard canDragVideoPreview else { return }
        dragOffset = value.translation.height
    }

    func handleVideoPreviewDragEnd(_ value: DragGesture.Value) {
        guard canDragVideoPreview else { return }
        let newOffset = videoVerticalOffset + Double(value.translation.height)
        videoVerticalOffset = min(max(newOffset, 0), 300)
        dragOffset = 0
    }
    #endif
    #endif

    func handleVideoPlaybackProgress(time: Double, isPlaying: Bool) {
        resumeManager?.recordVideoResume(time: time, isPlaying: isPlaying)
    }
}
