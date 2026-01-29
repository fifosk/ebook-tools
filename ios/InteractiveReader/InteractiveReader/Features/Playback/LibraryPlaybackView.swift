import Foundation
import SwiftUI
#if os(iOS)
import UIKit
#endif

struct LibraryPlaybackView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var offlineStore: OfflineMediaStore
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme
    #if !os(tvOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.verticalSizeClass) private var verticalSizeClass
    #endif
    let item: LibraryItem
    @Binding var autoPlayOnLoad: Bool
    let playbackMode: PlaybackStartMode

    @StateObject private var viewModel = InteractivePlayerViewModel()
    @StateObject private var nowPlaying = NowPlayingCoordinator()
    @State private var resumeManager: PlaybackResumeManager?
    @State private var sentenceIndexTracker = SentenceIndexTracker()
    @State private var showImageReel = true
    #if !os(tvOS)
    @State private var showVideoPlayer = false
    #endif
    #if os(iOS)
    @AppStorage("videoPreviewVerticalOffset") private var videoVerticalOffset: Double = 80
    @State private var dragOffset: CGFloat = 0
    #endif

    init(item: LibraryItem, autoPlayOnLoad: Binding<Bool> = .constant(true), playbackMode: PlaybackStartMode = .resume) {
        self.item = item
        self._autoPlayOnLoad = autoPlayOnLoad
        self.playbackMode = playbackMode
    }

    var body: some View {
        bodyContent
        .navigationTitle(navigationTitleText)
        #if os(iOS)
        .toolbarBackground(shouldUseInteractiveBackground ? Color.black : (usesDarkBackground ? AppTheme.lightBackground : Color.clear), for: .navigationBar)
        .toolbarBackground(.visible, for: .navigationBar)
        .toolbarColorScheme(.dark, for: .navigationBar)
        #endif
        .task(id: item.jobId) {
            @MainActor in
            await loadEntry()
        }
        .onReceive(viewModel.audioCoordinator.$currentTime) { newValue in
            updateNowPlayingPlayback(time: newValue)
        }
        .onReceive(viewModel.audioCoordinator.$isPlaying) { _ in
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        .onReceive(viewModel.audioCoordinator.$duration) { _ in
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        .onReceive(viewModel.audioCoordinator.$isReady) { _ in
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        .onDisappear {
            persistResumeOnExit()
            viewModel.audioCoordinator.reset()
            if scenePhase == .active {
                nowPlaying.clear()
            }
        }
        .onChange(of: scenePhase) { _, newPhase in
            guard newPhase != .active else { return }
            persistResumeOnExit()
        }
    }

    // Computed properties for resume manager values
    private var videoAutoPlay: Bool { resumeManager?.videoAutoPlay ?? false }
    private var videoResumeTime: Double? { resumeManager?.videoResumeTime }
    private var videoResumeActionID: UUID { resumeManager?.videoResumeActionID ?? UUID() }
    private var resumeUserId: String? { appState.resumeUserKey }

    private var navigationTitleText: String {
        shouldHideNavigationTitle ? "" : item.bookTitle
    }

    private var shouldHideNavigationTitle: Bool {
        viewModel.jobContext != nil && !isVideoPreferred
    }

    private var shouldUseInteractiveBackground: Bool {
        viewModel.jobContext != nil && !isVideoPreferred
    }

    /// Whether to use dark background (iPad in light mode, matching tvOS style)
    private var usesDarkBackground: Bool {
        #if os(iOS)
        return horizontalSizeClass != .compact && colorScheme == .light
        #else
        return false
        #endif
    }

    #if os(iOS)
    private var shouldHideInteractiveNavigation: Bool {
        shouldUseInteractiveBackground && UIDevice.current.userInterfaceIdiom == .phone
    }
    #endif

    private var standardBodyPadding: EdgeInsets {
        #if os(tvOS)
        return shouldUseInteractiveBackground
            ? EdgeInsets()
            : EdgeInsets(top: 8, leading: 16, bottom: 12, trailing: 16)
        #else
        return shouldUseInteractiveBackground
            ? EdgeInsets()
            : EdgeInsets(top: 16, leading: 16, bottom: 16, trailing: 16)
        #endif
    }

    /// Whether video preview position can be adjusted by dragging (iPhone portrait only)
    private var canDragVideoPreview: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .phone && verticalSizeClass == .regular
        #else
        return false
        #endif
    }

    /// Extra top padding for video preview on iPhone portrait mode
    private var videoTopPadding: CGFloat {
        #if os(iOS)
        guard canDragVideoPreview else { return 0 }
        return CGFloat(videoVerticalOffset) + dragOffset
        #else
        return 0
        #endif
    }

    @ViewBuilder
    private var bodyContent: some View {
        #if os(tvOS)
        if isVideoPreferred {
            tvVideoBody
        } else {
            standardBody
        }
        #else
        standardBody
        #endif
    }

    @ViewBuilder
    private var standardBody: some View {
        let base = VStack(alignment: .leading, spacing: rootSpacing) {
            if isVideoPreferred {
                header
            }

            switch viewModel.loadState {
            case .idle, .loading:
                loadingView
            case let .error(message):
                errorView(message: message)
            case .loaded:
                if isVideoPreferred, let videoURL {
                    #if os(tvOS)
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
                        .frame(maxWidth: .infinity)
                        .aspectRatio(16 / 9, contentMode: .fit)
                    #else
                    // Show empty placeholder when video player is presenting/presented
                    // This avoids showing the preview briefly before fullscreen cover
                    VStack(spacing: 0) {
                        Spacer()
                            .frame(height: max(0, videoTopPadding))
                        if showVideoPlayer {
                            Color.black
                                .frame(maxWidth: .infinity)
                                .aspectRatio(16 / 9, contentMode: .fit)
                        } else {
                            videoPreview
                                .frame(maxWidth: .infinity)
                                .aspectRatio(16 / 9, contentMode: .fit)
                        }
                        Spacer()
                    }
                    .frame(maxHeight: .infinity)
                    .contentShape(Rectangle())
                    .simultaneousGesture(videoPreviewDragGesture)
                    #endif
                } else if viewModel.jobContext != nil {
                    InteractivePlayerView(
                        viewModel: viewModel,
                        audioCoordinator: viewModel.audioCoordinator,
                        showImageReel: $showImageReel,
                        showsScrubber: showsScrubber,
                        linguistInputLanguage: linguistInputLanguage,
                        linguistLookupLanguage: linguistLookupLanguage,
                        headerInfo: interactiveHeaderInfo,
                        bookmarkUserId: resumeUserId,
                        bookmarkJobId: item.jobId,
                        bookmarkItemType: bookmarkItemType
                    )
                } else {
                    Text("No playable media found for this entry.")
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(standardBodyPadding)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background {
            if shouldUseInteractiveBackground {
                Color.black.ignoresSafeArea()
            } else if usesDarkBackground {
                AppTheme.lightBackground.ignoresSafeArea()
            }
        }
        #if !os(tvOS)
        .fullScreenCover(isPresented: $showVideoPlayer, onDismiss: {
            // When video player is dismissed, also dismiss this view to go back to menu
            dismiss()
        }) {
            if let videoURL {
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
                .ignoresSafeArea()
            } else {
                Color.black
                    .ignoresSafeArea()
            }
        }
        #endif
        #if os(iOS)
        if shouldHideInteractiveNavigation {
            base
                .overlay(alignment: .leading) {
                    EdgeSwipeBackOverlay {
                        dismiss()
                    }
                }
                .toolbar(.hidden, for: .navigationBar)
                .navigationBarBackButtonHidden(true)
        } else {
            base
        }
        #else
        base
        #endif
    }

    #if os(tvOS)
    private var tvVideoBody: some View {
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
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    Text("No playable media found for this entry.")
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
        }
        .ignoresSafeArea()
        .toolbar(.hidden, for: .navigationBar)
    }
    #endif

    #if !os(tvOS)
    private var videoPreview: some View {
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
    private var videoPreviewDragGesture: some Gesture {
        DragGesture(minimumDistance: 10)
            .onChanged { value in
                guard canDragVideoPreview else { return }
                dragOffset = value.translation.height
            }
            .onEnded { value in
                guard canDragVideoPreview else { return }
                let newOffset = videoVerticalOffset + Double(value.translation.height)
                // Clamp between 0 and 300 points
                videoVerticalOffset = min(max(newOffset, 0), 300)
                dragOffset = 0
            }
    }
    #else
    private var videoPreviewDragGesture: some Gesture {
        DragGesture().onChanged { _ in }
    }
    #endif
    #endif

    @ViewBuilder
    private var header: some View {
        #if os(tvOS)
        HStack(alignment: .top, spacing: headerSpacing) {
            headerInfo
            if showImageReel, !imageReelURLs.isEmpty {
                Spacer(minLength: 12)
                LibraryImageReel(urls: imageReelURLs, height: coverHeight)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            } else {
                Spacer()
            }
        }
        #else
        if horizontalSizeClass == .regular {
            HStack(alignment: .top, spacing: headerSpacing) {
                headerInfo
                if showImageReel, !imageReelURLs.isEmpty {
                    Spacer(minLength: 12)
                    LibraryImageReel(urls: imageReelURLs, height: coverHeight)
                        .frame(maxWidth: .infinity, alignment: .trailing)
                } else {
                    Spacer()
                }
            }
        } else {
            VStack(alignment: .leading, spacing: headerSpacing) {
                headerInfo
                if showImageReel, !imageReelURLs.isEmpty {
                    LibraryImageReel(urls: imageReelURLs, height: coverHeight)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
        #endif
    }

    private var headerInfo: some View {
        HStack(alignment: .top, spacing: headerSpacing) {
            AsyncImage(url: coverURL) { phase in
                if let image = phase.image {
                    image.resizable().scaledToFill()
                } else {
                    Color.gray.opacity(0.2)
                }
            }
            .frame(width: coverWidth, height: coverHeight)
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
            )

            VStack(alignment: .leading, spacing: headerTextSpacing) {
                Text(item.bookTitle.isEmpty ? "Untitled" : item.bookTitle)
                    .font(titleFont)
                    .lineLimit(titleLineLimit)
                    .minimumScaleFactor(0.9)
                    .truncationMode(.tail)
                Text(item.author.isEmpty ? "Unknown author" : item.author)
                    .font(authorFont)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
                    .foregroundStyle(.secondary)
                Text(itemTypeLabel)
                    .font(metaFont)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.accentColor.opacity(0.2), in: Capsule())
            }
        }
    }

    private var loadingView: some View {
        VStack(spacing: 12) {
            ProgressView()
                .tint(usesDarkBackground ? .white : nil)
            Text("Loading media…")
                .foregroundStyle(usesDarkBackground ? .white.opacity(0.7) : .secondary)
        }
        .frame(maxWidth: .infinity, minHeight: 200)
    }

    private func errorView(message: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Unable to load media", systemImage: "exclamationmark.triangle.fill")
                .foregroundStyle(.red)
            Text(message)
                .font(.callout)
                .foregroundStyle(usesDarkBackground ? .white.opacity(0.7) : .secondary)
        }
    }

    private var itemTypeLabel: String {
        switch item.itemType {
        case "video":
            return "Video"
        case "narrated_subtitle":
            return "Subtitles"
        default:
            return "Book"
        }
    }

    private var bookmarkItemType: String {
        item.itemType.nonEmptyValue ?? itemTypeLabel.lowercased()
    }

    private var showsScrubber: Bool {
        item.itemType == "video"
    }

    private var linguistInputLanguage: String {
        metadataString(for: [
            "input_language",
            "original_language",
            "source_language",
            "translation_source_language",
            "book_language"
        ]) ?? item.language
    }

    private var linguistLookupLanguage: String {
        metadataString(for: [
            "target_language",
            "translation_language",
            "target_languages",
            "book_language"
        ]) ?? metadataString(for: ["language"], maxDepth: 0) ?? item.language
    }

    private var summaryText: String? {
        if let summary = resolvedYoutubeSummary {
            return summary
        }
        if let summary = resolvedTvSummary {
            return summary
        }
        if let summary = bookSummary {
            return summary
        }
        return nil
    }

    private var interactiveHeaderInfo: InteractivePlayerHeaderInfo {
        InteractivePlayerHeaderInfo(
            title: item.bookTitle.isEmpty ? "Untitled" : item.bookTitle,
            author: item.author.isEmpty ? "Unknown author" : item.author,
            itemTypeLabel: itemTypeLabel,
            coverURL: coverURL,
            secondaryCoverURL: secondaryCoverURL,
            languageFlags: languageFlags,
            translationModel: translationModelLabel
        )
    }

    private var coverWidth: CGFloat {
        #if os(tvOS)
        return 96
        #else
        return 64
        #endif
    }

    private var coverHeight: CGFloat {
        #if os(tvOS)
        return 144
        #else
        return 96
        #endif
    }

    private var titleFont: Font {
        #if os(tvOS)
        return .title2
        #else
        return .title2
        #endif
    }

    private var authorFont: Font {
        #if os(tvOS)
        return .callout
        #else
        return .callout
        #endif
    }

    private var metaFont: Font {
        #if os(tvOS)
        return .caption2
        #else
        return .caption
        #endif
    }

    private var titleLineLimit: Int {
        #if os(tvOS)
        return 2
        #else
        return 3
        #endif
    }

    private var rootSpacing: CGFloat {
        #if os(tvOS)
        return 12
        #else
        return 16
        #endif
    }

    private var headerSpacing: CGFloat {
        #if os(tvOS)
        return 10
        #else
        return 12
        #endif
    }

    private var headerTextSpacing: CGFloat {
        #if os(tvOS)
        return 4
        #else
        return 6
        #endif
    }

    private func metadataString(for keys: [String], maxDepth: Int = 4) -> String? {
        guard let metadata = item.metadata else { return nil }
        return PlaybackMetadataHelpers.metadataString(in: metadata, keys: keys, maxDepth: maxDepth)
    }

    private func normalizedSummary(_ value: String?) -> String? {
        PlaybackMetadataHelpers.normalizedSummary(value)
    }

    private var resolvedTvMetadata: [String: JSONValue]? {
        guard let metadata = item.metadata else { return nil }
        return PlaybackMetadataHelpers.extractTvMediaMetadata(from: metadata)
    }

    private var isTvSeriesMetadata: Bool {
        PlaybackMetadataHelpers.isTvSeriesMetadata(resolvedTvMetadata)
    }

    private var resolvedYoutubeMetadata: [String: JSONValue]? {
        if let tvMetadata = resolvedTvMetadata,
           let youtube = tvMetadata["youtube"]?.objectValue {
            return youtube
        }
        guard let metadata = item.metadata else { return nil }
        return metadata["youtube"]?.objectValue
    }

    private var resolvedYoutubeSummary: String? {
        PlaybackMetadataHelpers.youtubeSummary(from: resolvedYoutubeMetadata)
    }

    private var resolvedTvSummary: String? {
        PlaybackMetadataHelpers.tvSummary(from: resolvedTvMetadata)
    }

    private var imageReelURLs: [URL] {
        guard let chunk = viewModel.selectedChunk else { return [] }
        let hasExplicitImage = chunk.sentences.contains { sentence in
            if let rawPath = sentence.imagePath, rawPath.nonEmptyValue != nil {
                return true
            }
            return false
        }
        guard hasExplicitImage else { return [] }
        var urls: [URL] = []
        var seen: Set<String> = []
        for sentence in chunk.sentences {
            guard let path = resolveSentenceImagePath(sentence: sentence, chunk: chunk) else { continue }
            guard !seen.contains(path) else { continue }
            seen.insert(path)
            if let url = viewModel.resolvePath(path) {
                urls.append(url)
            }
            if urls.count >= 7 {
                break
            }
        }
        return urls
    }

    private func resolveSentenceImagePath(sentence: InteractiveChunk.Sentence, chunk: InteractiveChunk) -> String? {
        if let rawPath = sentence.imagePath, let path = rawPath.nonEmptyValue {
            return path
        }
        guard let rangeFragment = chunk.rangeFragment?.nonEmptyValue else { return nil }
        let sentenceNumber = sentence.displayIndex ?? sentence.id
        guard sentenceNumber > 0 else { return nil }
        let padded = String(format: "%05d", sentenceNumber)
        return "media/images/\(rangeFragment)/sentence_\(padded).png"
    }

    private var coverURL: URL? {
        guard let apiBaseURL = appState.apiBaseURL else { return nil }
        let resolver = LibraryCoverResolver(apiBaseURL: apiBaseURL, accessToken: appState.authToken)
        return resolver.resolveCoverURL(for: item)
    }

    private var secondaryCoverURL: URL? {
        guard let apiBaseURL = appState.apiBaseURL else { return nil }
        let resolver = LibraryCoverResolver(apiBaseURL: apiBaseURL, accessToken: appState.authToken)
        return resolver.resolveSecondaryCoverURL(for: item)
    }

    private var languageFlags: [LanguageFlagEntry] {
        LanguageFlagResolver.resolveFlags(
            originalLanguage: linguistInputLanguage,
            translationLanguage: linguistLookupLanguage
        )
    }

    private var translationModelLabel: String? {
        metadataString(for: ["llm_model", "ollama_model"])?.nonEmptyValue
    }

    private var bookSummary: String? {
        let summary = metadataString(for: ["book_summary"], maxDepth: 4)
            ?? metadataString(for: ["summary"], maxDepth: 4)
        return normalizedSummary(summary)
    }

    private var hasInteractiveChunks: Bool {
        guard let chunks = viewModel.jobContext?.chunks else { return false }
        return chunks.contains { !$0.sentences.isEmpty || $0.startSentence != nil || $0.endSentence != nil }
    }

    private var hasVideo: Bool {
        !(viewModel.mediaResponse?.media["video"] ?? []).isEmpty
    }

    private var isVideoPreferred: Bool {
        if item.itemType == "video" {
            return true
        }
        return hasVideo && !hasInteractiveChunks
    }

    private var videoURL: URL? {
        guard let files = viewModel.mediaResponse?.media["video"] else { return nil }
        for file in files {
            if let url = viewModel.resolveMediaURL(for: file) {
                return url
            }
        }
        return nil
    }

    private var subtitleTracks: [VideoSubtitleTrack] {
        guard let files = viewModel.mediaResponse?.media["text"] else { return [] }
        var tracks: [VideoSubtitleTrack] = []
        var seen: Set<String> = []
        for file in files {
            guard let url = viewModel.resolveMediaURL(for: file) else { continue }
            let sourcePath = file.relativePath ?? file.path ?? file.name
            let format = SubtitleParser.format(for: sourcePath)
            let id = (sourcePath.nonEmptyValue ?? url.absoluteString)
            guard !seen.contains(id) else { continue }
            seen.insert(id)
            let label = subtitleTrackLabel(for: file, fallback: "Subtitle \(tracks.count + 1)")
            tracks.append(VideoSubtitleTrack(id: id, url: url, format: format, label: label))
        }
        return tracks
    }

    private func subtitleTrackLabel(for file: PipelineMediaFile, fallback: String) -> String {
        let raw = (file.name.nonEmptyValue ?? file.relativePath?.nonEmptyValue ?? file.path?.nonEmptyValue)
        let filename = raw?.split(whereSeparator: { $0 == "/" || $0 == "\\" }).last.map(String.init) ?? fallback
        if let dotIndex = filename.lastIndex(of: ".") {
            let stem = filename[..<dotIndex]
            if !stem.isEmpty {
                return String(stem)
            }
        }
        return filename
    }

    private var videoMetadata: VideoPlaybackMetadata {
        let title = item.bookTitle.isEmpty ? "Video" : item.bookTitle
        let subtitle = item.author.isEmpty ? nil : item.author
        let isYoutubeVideo = resolvedYoutubeMetadata != nil
        let isTvSeries = isTvSeriesMetadata
        let channelVariant: PlayerChannelVariant = {
            if isTvSeries {
                return .tv
            }
            if isYoutubeVideo {
                return .youtube
            }
            switch item.itemType {
            case "narrated_subtitle":
                return .subtitles
            default:
                return .video
            }
        }()
        let channelLabel = isTvSeries
            ? "TV"
            : isYoutubeVideo
                ? "YouTube"
                : (item.itemType == "narrated_subtitle" ? "Subtitles" : "Video")
        return VideoPlaybackMetadata(
            title: title,
            subtitle: subtitle,
            artist: subtitle,
            album: item.bookTitle.isEmpty ? nil : item.bookTitle,
            artworkURL: coverURL,
            secondaryArtworkURL: secondaryCoverURL,
            languageFlags: languageFlags,
            translationModel: translationModelLabel,
            summary: summaryText,
            channelVariant: channelVariant,
            channelLabel: channelLabel
        )
    }

    @MainActor
    private func loadEntry() async {
        guard let configuration = appState.configuration else { return }

        // Initialize resume manager
        let manager = PlaybackResumeManager(
            jobId: item.jobId,
            itemType: item.itemType,
            userId: appState.resumeUserKey,
            userAliases: appState.resumeUserAliases
        )
        resumeManager = manager
        manager.resetState()

        let shouldAutoPlay = autoPlayOnLoad
        autoPlayOnLoad = false
        sentenceIndexTracker.value = nil
        #if !os(tvOS)
        showVideoPlayer = false
        #endif

        let offlinePayload = await offlineStore.cachedPayload(for: item.jobId, kind: .library)
        if let offlinePayload,
           let localResolver = offlineStore.localResolver(for: .library, configuration: configuration) {
            let offlineConfig = APIClientConfiguration(
                apiBaseURL: configuration.apiBaseURL,
                storageBaseURL: offlinePayload.storageBaseURL,
                authToken: configuration.authToken,
                userID: configuration.userID,
                userRole: configuration.userRole
            )
            await viewModel.loadJob(
                jobId: item.jobId,
                configuration: offlineConfig,
                origin: .library,
                preferLiveMedia: false,
                mediaOverride: offlinePayload.media,
                timingOverride: offlinePayload.timing,
                resolverOverride: localResolver
            )
            applyOfflineReadingBeds(offlinePayload)
        } else {
            await viewModel.loadJob(jobId: item.jobId, configuration: configuration, origin: .library)
        }
        await viewModel.updateChapterIndex(from: item.metadata)
        if isVideoPreferred {
            nowPlaying.clear()
        } else {
            configureNowPlaying()
            updateNowPlayingMetadata(sentenceIndex: sentenceIndexTracker.value)
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        await manager.syncNow()
        manager.markResumeDecisionComplete()

        // Handle playback based on mode from context menu selection
        switch playbackMode {
        case .resume:
            // Auto-resume from last position if available
            if let resumeEntry = manager.resolveResumeEntry(isVideoPreferred: isVideoPreferred) {
                applyResume(resumeEntry)
                return
            }
            // No resume position, start from beginning
            if shouldAutoPlay {
                startPlaybackFromBeginning()
            }
        case .startOver:
            // Clear resume position and start from beginning
            manager.clearResumeEntry()
            if shouldAutoPlay {
                startPlaybackFromBeginning()
            }
        }
    }

    @MainActor
    private func applyOfflineReadingBeds(_ payload: OfflineMediaStore.OfflineMediaPayload) {
        viewModel.readingBedCatalog = payload.readingBeds
        viewModel.readingBedBaseURL = payload.readingBedBaseURL
        viewModel.selectReadingBed(id: viewModel.selectedReadingBedID)
    }

    private func configureNowPlaying() {
        nowPlaying.configureRemoteCommands(
            onPlay: { viewModel.audioCoordinator.play() },
            onPause: { viewModel.audioCoordinator.pause() },
            onNext: { viewModel.skipSentence(forward: true) },
            onPrevious: { viewModel.skipSentence(forward: false) },
            onSeek: { viewModel.audioCoordinator.seek(to: $0) },
            onToggle: { viewModel.audioCoordinator.togglePlayback() },
            onSkipForward: { viewModel.skipSentence(forward: true) },
            onSkipBackward: { viewModel.skipSentence(forward: false) },
            onBookmark: { addNowPlayingBookmark() }
        )
    }

    private func updateNowPlayingMetadata(sentenceIndex: Int?) {
        let totalSentences = totalSentenceCount
        let sentence = sentenceIndex.flatMap { index -> String? in
            guard index > 0 else { return nil }
            if let totalSentences, totalSentences > 0 {
                return "Sentence \(index) of \(totalSentences)"
            }
            return "Sentence \(index)"
        }
        let baseTitle = item.bookTitle.isEmpty ? "Interactive Reader" : item.bookTitle
        let title = sentence.map { "\(baseTitle) · \($0)" } ?? baseTitle
        nowPlaying.updateMetadata(
            title: title,
            artist: item.author.isEmpty ? nil : item.author,
            album: item.bookTitle.isEmpty ? nil : item.bookTitle,
            artworkURL: coverURL,
            queueIndex: sentenceIndex.map { max($0 - 1, 0) },
            queueCount: totalSentences
        )
    }

    private func updateNowPlayingPlayback(time: Double) {
        guard !isVideoPreferred else { return }
        let highlightTime = viewModel.highlightingTime
        if let resolvedIndex = resolveResumeSentenceIndex(at: highlightTime) {
            if sentenceIndexTracker.value != resolvedIndex {
                sentenceIndexTracker.value = resolvedIndex
                updateNowPlayingMetadata(sentenceIndex: resolvedIndex)
            }
            resumeManager?.recordInteractiveResume(sentenceIndex: resolvedIndex)
        }
        let playbackDuration = viewModel.selectedChunk.flatMap { viewModel.playbackDuration(for: $0) } ?? viewModel.audioCoordinator.duration
        let playbackTime = highlightTime.isFinite ? highlightTime : time
        nowPlaying.updatePlaybackState(
            isPlaying: viewModel.audioCoordinator.isPlaying,
            position: playbackTime,
            duration: playbackDuration
        )
    }

    private func addNowPlayingBookmark() {
        guard let chunk = viewModel.selectedChunk else { return }
        let jobId = item.jobId
        let userId = appState.resumeUserKey?.nonEmptyValue ?? "anonymous"
        let playbackTime = viewModel.playbackTime(for: chunk)
        let activeSentence = viewModel.activeSentence(at: viewModel.highlightingTime)
        let sentenceNumber = activeSentence?.displayIndex ?? activeSentence?.id
        let labelParts: [String] = {
            var parts: [String] = []
            if let sentenceNumber, sentenceNumber > 0 {
                parts.append("Sentence \(sentenceNumber)")
            }
            if playbackTime.isFinite {
                parts.append(formatBookmarkTime(playbackTime))
            }
            return parts
        }()
        let label = labelParts.isEmpty ? "Bookmark" : labelParts.joined(separator: " · ")
        let entry = PlaybackBookmarkEntry(
            id: UUID().uuidString,
            jobId: jobId,
            itemType: bookmarkItemType,
            kind: sentenceNumber != nil ? .sentence : .time,
            createdAt: Date().timeIntervalSince1970,
            label: label,
            playbackTime: playbackTime.isFinite ? playbackTime : nil,
            sentenceNumber: sentenceNumber,
            chunkId: chunk.id,
            segmentId: nil
        )
        guard let configuration = appState.configuration else {
            PlaybackBookmarkStore.shared.addBookmark(entry, userId: userId)
            return
        }
        Task {
            let client = APIClient(configuration: configuration)
            let payload = PlaybackBookmarkCreateRequest(
                id: entry.id,
                label: entry.label,
                kind: entry.kind,
                createdAt: entry.createdAt,
                position: entry.playbackTime,
                sentence: entry.sentenceNumber,
                mediaType: entry.kind == .sentence ? "text" : "audio",
                mediaId: nil,
                baseId: nil,
                segmentId: entry.segmentId,
                chunkId: entry.chunkId,
                itemType: entry.itemType
            )
            do {
                let response = try await client.createPlaybackBookmark(jobId: jobId, payload: payload)
                let stored = PlaybackBookmarkEntry(
                    id: response.id,
                    jobId: response.jobId,
                    itemType: response.itemType ?? entry.itemType,
                    kind: response.kind,
                    createdAt: response.createdAt,
                    label: response.label,
                    playbackTime: response.position,
                    sentenceNumber: response.sentence,
                    chunkId: response.chunkId,
                    segmentId: response.segmentId
                )
                PlaybackBookmarkStore.shared.addBookmark(stored, userId: userId)
            } catch {
                PlaybackBookmarkStore.shared.addBookmark(entry, userId: userId)
            }
        }
    }

    private func formatBookmarkTime(_ seconds: Double) -> String {
        let total = max(0, Int(seconds.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let remainingSeconds = total % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, remainingSeconds)
        }
        return String(format: "%02d:%02d", minutes, remainingSeconds)
    }

    // MARK: - Resume Actions

    private func startPlaybackFromBeginning() {
        if isVideoPreferred {
            // Always present the video player - no cover preview needed
            startVideoPlayback(at: 0, presentPlayer: true)
        } else if viewModel.jobContext != nil {
            startInteractivePlayback(at: 1)
        }
    }

    private func applyResume(_ entry: PlaybackResumeEntry) {
        resumeManager?.applyResume(entry)
        if isVideoPreferred {
            startVideoPlayback(at: entry.playbackTime ?? 0, presentPlayer: true)
        } else {
            startInteractivePlayback(at: entry.sentenceNumber)
        }
    }

    private func startInteractivePlayback(at sentence: Int?) {
        if let sentence, sentence > 0 {
            viewModel.jumpToSentence(sentence, autoPlay: true)
        }
        if !viewModel.audioCoordinator.isPlaying {
            viewModel.audioCoordinator.play()
        }
    }

    private func startVideoPlayback(at time: Double?, presentPlayer: Bool) {
        resumeManager?.prepareVideoResume(at: time)
        #if !os(tvOS)
        if presentPlayer {
            showVideoPlayer = true
        }
        #endif
    }

    #if !os(tvOS)
    private func handleVideoPreviewTap() {
        // If there's a resume entry, apply it; otherwise start from beginning
        if let manager = resumeManager,
           let resumeEntry = manager.resolveResumeEntry(isVideoPreferred: isVideoPreferred) {
            applyResume(resumeEntry)
        } else {
            startVideoPlayback(at: 0, presentPlayer: true)
        }
    }
    #endif

    private func handleVideoPlaybackProgress(time: Double, isPlaying: Bool) {
        resumeManager?.recordVideoResume(time: time, isPlaying: isPlaying)
    }

    private func resolveResumeSentenceIndex(at highlightTime: Double) -> Int? {
        guard let chunk = viewModel.selectedChunk else { return nil }
        let duration = viewModel.playbackDuration(for: chunk) ?? viewModel.audioCoordinator.duration
        return PlaybackSentenceIndexHelpers.resolveResumeSentenceIndex(
            at: highlightTime,
            chunk: chunk,
            activeSentence: viewModel.activeSentence(at: highlightTime),
            playbackDuration: duration
        )
    }

    private func persistResumeOnExit() {
        resumeManager?.persistOnExit(isVideoPreferred: isVideoPreferred, sentenceIndex: sentenceIndexTracker.value)
    }

    private var totalSentenceCount: Int? {
        guard let context = viewModel.jobContext else { return nil }
        var total = 0
        for chunk in context.chunks {
            if let start = chunk.startSentence, let end = chunk.endSentence, end >= start {
                total += end - start + 1
            } else if !chunk.sentences.isEmpty {
                total += chunk.sentences.count
            }
        }
        return total > 0 ? total : nil
    }

}

private final class SentenceIndexTracker {
    var value: Int?
}

private struct LibraryImageReel: View {
    let urls: [URL]
    let height: CGFloat

    private let spacing: CGFloat = 8
    private let maxImages = 7
    private let minImages = 1

    var body: some View {
        GeometryReader { proxy in
            let itemHeight = height
            let itemWidth = itemHeight * 0.78
            let maxVisible = max(
                minImages,
                min(maxImages, Int((proxy.size.width + spacing) / (itemWidth + spacing)))
            )
            let visible = Array(urls.prefix(maxVisible))
            HStack(spacing: spacing) {
                ForEach(visible.indices, id: \.self) { index in
                    AsyncImage(url: visible[index]) { phase in
                        if let image = phase.image {
                            image
                                .resizable()
                                .scaledToFill()
                        } else {
                            Color.gray.opacity(0.2)
                        }
                    }
                    .frame(width: itemWidth, height: itemHeight)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
                    )
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .trailing)
        }
        .frame(height: height)
    }
}
