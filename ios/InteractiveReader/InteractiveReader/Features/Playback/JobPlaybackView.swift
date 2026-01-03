import Foundation
import AVFoundation
import SwiftUI

struct JobPlaybackView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.scenePhase) private var scenePhase
    #if !os(tvOS)
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    #endif
    let job: PipelineStatusResponse

    @StateObject private var viewModel = InteractivePlayerViewModel()
    @StateObject private var nowPlaying = NowPlayingCoordinator()
    @State private var sentenceIndex: Int?
    @State private var showImageReel = true
    @State private var pendingResumeEntry: PlaybackResumeEntry?
    @State private var showResumePrompt = false
    @State private var videoResumeTime: Double?
    @State private var videoResumeActionID = UUID()
    @State private var videoAutoPlay = false
    @State private var activeVideoSegmentID: String?
    @State private var jobStatus: PipelineStatusResponse?
    @State private var subtitleTvMetadata: SubtitleTvMetadataResponse?
    @State private var youtubeVideoMetadata: YoutubeVideoMetadataResponse?
    @State private var jobRefreshTask: Task<Void, Never>?
    @State private var completedSegmentDurations: [String: Double] = [:]
    @State private var segmentDurations: [String: Double] = [:]
    @State private var segmentDurationTask: Task<Void, Never>?
    @State private var lastRecordedSentence: Int?
    @State private var lastRecordedTimeBucket: Int?
    @State private var lastVideoTime: Double = 0
    @State private var resumeDecisionPending = false
    #if !os(tvOS)
    @State private var showVideoPlayer = false
    #endif

    private let jobRefreshInterval: UInt64 = 6_000_000_000

    var body: some View {
        bodyContent
            .navigationTitle(navigationTitleText)
            .task(id: job.jobId) {
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
            .onChange(of: videoSegments.map(\.id)) { _, _ in
                refreshActiveVideoSegment()
                preloadSegmentDurations()
            }
            .onDisappear {
                persistResumeOnExit()
                segmentDurationTask?.cancel()
                segmentDurationTask = nil
                stopJobRefresh()
                viewModel.stopLiveUpdates()
                viewModel.audioCoordinator.reset()
                if scenePhase == .active {
                    nowPlaying.clear()
                }
            }
            .alert("Resume playback?", isPresented: $showResumePrompt, presenting: pendingResumeEntry) { entry in
                Button("Resume") {
                    applyResume(entry)
                }
                Button("Start Over", role: .destructive) {
                    startOver()
                }
            } message: { entry in
                Text(resumePromptMessage(for: entry))
            }
    }

    private var navigationTitleText: String {
        shouldHideNavigationTitle ? "" : jobTitle
    }

    private var shouldHideNavigationTitle: Bool {
        viewModel.jobContext != nil && !isVideoPreferred
    }

    private var shouldUseInteractiveBackground: Bool {
        viewModel.jobContext != nil && !isVideoPreferred
    }

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

    private var standardBody: some View {
        VStack(alignment: .leading, spacing: 12) {
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
                        segmentOptions: videoSegmentOptions,
                        selectedSegmentID: activeVideoSegmentID ?? videoSegments.first?.id,
                        onSelectSegment: handleVideoSegmentSelection,
                        jobProgressLabel: jobProgressLabel,
                        jobRemainingLabel: jobRemainingLabel,
                        onPlaybackProgress: handleVideoPlaybackProgress,
                        onPlaybackEnded: handleVideoSegmentEnded
                    )
                    .frame(maxWidth: .infinity)
                    .aspectRatio(16 / 9, contentMode: .fit)
                    #else
                    videoPreview
                        .frame(maxWidth: .infinity)
                        .aspectRatio(16 / 9, contentMode: .fit)
                    #endif
                } else if viewModel.jobContext != nil {
                    InteractivePlayerView(
                        viewModel: viewModel,
                        audioCoordinator: viewModel.audioCoordinator,
                        showImageReel: $showImageReel,
                        showsScrubber: false,
                        linguistInputLanguage: linguistInputLanguage,
                        linguistLookupLanguage: linguistLookupLanguage,
                        headerInfo: interactiveHeaderInfo
                    )
                } else {
                    Text("No playable media found for this job.")
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(standardBodyPadding)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background {
            if shouldUseInteractiveBackground {
                Color.black.ignoresSafeArea()
            }
        }
        #if !os(tvOS)
        .fullScreenCover(isPresented: $showVideoPlayer) {
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
                    segmentOptions: videoSegmentOptions,
                    selectedSegmentID: activeVideoSegmentID ?? videoSegments.first?.id,
                    onSelectSegment: handleVideoSegmentSelection,
                    jobProgressLabel: jobProgressLabel,
                    jobRemainingLabel: jobRemainingLabel,
                    onPlaybackProgress: handleVideoPlaybackProgress,
                    onPlaybackEnded: handleVideoSegmentEnded
                )
                .ignoresSafeArea()
            } else {
                Color.black
                    .ignoresSafeArea()
            }
        }
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
                        segmentOptions: videoSegmentOptions,
                        selectedSegmentID: activeVideoSegmentID ?? videoSegments.first?.id,
                        onSelectSegment: handleVideoSegmentSelection,
                        jobProgressLabel: jobProgressLabel,
                        jobRemainingLabel: jobRemainingLabel,
                        onPlaybackProgress: handleVideoPlaybackProgress,
                        onPlaybackEnded: handleVideoSegmentEnded
                    )
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    Text("No playable media found for this job.")
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
        }
        .ignoresSafeArea()
        .toolbar(.hidden, for: .navigationBar)
    }
    #endif

    private var loadingView: some View {
        VStack(spacing: 12) {
            ProgressView()
            Text("Loading media…")
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, minHeight: 200)
    }

    private func errorView(message: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Unable to load media", systemImage: "exclamationmark.triangle.fill")
                .foregroundStyle(.red)
            Text(message)
                .font(.callout)
        }
    }

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
    #endif

    private var hasInteractiveChunks: Bool {
        guard let chunks = viewModel.jobContext?.chunks else { return false }
        return chunks.contains { !$0.sentences.isEmpty || $0.startSentence != nil || $0.endSentence != nil }
    }

    private var hasVideo: Bool {
        guard let media = viewModel.mediaResponse?.media else { return false }
        return !resolveVideoFiles(from: media).isEmpty
    }

    private var isVideoPreferred: Bool {
        if jobVariant == .video || jobVariant == .youtube || jobVariant == .dub {
            return true
        }
        return hasVideo && !hasInteractiveChunks
    }

    private var videoSegments: [JobVideoSegment] {
        guard let mediaResponse = viewModel.mediaResponse else { return [] }
        if !mediaResponse.chunks.isEmpty {
            return buildSegments(from: mediaResponse.chunks, media: mediaResponse.media)
        }
        let media = mediaResponse.media
        let videoFiles = resolveVideoFiles(from: media)
        let subtitleFiles = resolveSubtitleFiles(from: media)
        let sortedVideos = videoFiles.enumerated().sorted { lhs, rhs in
            let left = sortKey(for: lhs.element, fallback: lhs.offset)
            let right = sortKey(for: rhs.element, fallback: rhs.offset)
            if left == right {
                return lhs.offset < rhs.offset
            }
            return left < right
        }
        let sortedSubtitles = subtitleFiles.enumerated().sorted { lhs, rhs in
            let left = sortKey(for: lhs.element, fallback: lhs.offset)
            let right = sortKey(for: rhs.element, fallback: rhs.offset)
            if left == right {
                return lhs.offset < rhs.offset
            }
            return left < right
        }
        return sortedVideos.map { entry in
            let file = entry.element
            let matched = matchSubtitleFiles(for: file, in: subtitleFiles)
            let resolvedSubtitles: [PipelineMediaFile]
            if matched.isEmpty {
                if sortedSubtitles.count == sortedVideos.count {
                    resolvedSubtitles = [sortedSubtitles[entry.offset].element]
                } else {
                    resolvedSubtitles = subtitleFiles
                }
            } else {
                resolvedSubtitles = matched
            }
            return JobVideoSegment(
                id: segmentID(for: file, chunk: nil, fallback: entry.offset),
                videoFile: file,
                subtitleFiles: resolvedSubtitles,
                chunk: nil
            )
        }
    }

    private var activeVideoSegment: JobVideoSegment? {
        guard !videoSegments.isEmpty else { return nil }
        if let activeVideoSegmentID,
           let match = videoSegments.first(where: { $0.id == activeVideoSegmentID }) {
            return match
        }
        return videoSegments.first
    }

    private var videoURL: URL? {
        guard let segment = activeVideoSegment else { return nil }
        return viewModel.resolveMediaURL(for: segment.videoFile)
    }

    private var subtitleTracks: [VideoSubtitleTrack] {
        guard let segment = activeVideoSegment else { return [] }
        return subtitleTracks(from: segment.subtitleFiles)
    }

    private var videoSegmentOptions: [VideoSegmentOption] {
        guard !videoSegments.isEmpty else { return [] }
        return videoSegments.enumerated().map { index, segment in
            VideoSegmentOption(
                id: segment.id,
                label: segmentLabel(for: segment, index: index)
            )
        }
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
        let channelLabel: String
        switch jobVariant {
        case .subtitles:
            channelLabel = "Subtitles"
        case .youtube:
            channelLabel = "YouTube"
        case .dub:
            channelLabel = "Dubbing"
        case .video:
            channelLabel = "Video"
        case .nas:
            channelLabel = "NAS"
        case .book, .job:
            channelLabel = "Video"
        }
        let title = videoTitleOverride ?? jobTitle
        let subtitle = videoSubtitleOverride ?? jobAuthor.nonEmptyValue
        return VideoPlaybackMetadata(
            title: title,
            subtitle: subtitle,
            artist: subtitle,
            album: title.nonEmptyValue,
            artworkURL: coverURL,
            secondaryArtworkURL: secondaryCoverURL,
            languageFlags: languageFlags,
            channelVariant: jobVariant,
            channelLabel: channelLabel
        )
    }

    private var videoTitleOverride: String? {
        if let youtubeTitle = resolvedYoutubeTitle {
            return youtubeTitle
        }
        if let tvTitle = resolvedTvTitle {
            return tvTitle
        }
        return nil
    }

    private var videoSubtitleOverride: String? {
        if let youtubeChannel = resolvedYoutubeChannel {
            return youtubeChannel
        }
        if let tvEpisodeLabel = resolvedTvEpisodeLabel {
            return tvEpisodeLabel
        }
        if let sourceName = subtitleTvMetadata?.sourceName?.nonEmptyValue {
            return sourceName
        }
        return nil
    }

    private var jobTitle: String {
        if let label = currentJob.jobLabel?.nonEmptyValue {
            return label
        }
        if let title = metadataString(for: ["title", "book_title", "name", "source_name"]) {
            return title
        }
        return "Job \(job.jobId)"
    }

    private var jobProgressLabel: String? {
        let statusLabel = jobStatusLabel
        if let percent = jobProgressPercent {
            return "\(statusLabel) · \(percent)%"
        }
        return statusLabel
    }

    private var jobProgressPercent: Int? {
        let chunkPercent = chunkProgressPercent
        if chunkPercent > 0 {
            return chunkPercent
        }
        if currentJob.isFinishedForDisplay {
            return 100
        }
        guard let snapshot = currentJob.latestEvent?.snapshot,
              let total = snapshot.total,
              total > 0
        else {
            return nil
        }
        let value = Int((Double(snapshot.completed) / Double(total)) * 100)
        return min(max(value, 0), 100)
    }

    private var chunkProgressPercent: Int {
        guard !videoSegments.isEmpty else { return 0 }
        guard let activeID = activeVideoSegmentID ?? videoSegments.first?.id,
              let activeIndex = videoSegments.firstIndex(where: { $0.id == activeID })
        else {
            return 0
        }
        let percent = Int((Double(activeIndex + 1) / Double(max(videoSegments.count, 1))) * 100)
        return min(max(percent, 0), 100)
    }

    private var jobRemainingLabel: String? {
        guard let remaining = jobRemainingEstimate, remaining > 0 else { return nil }
        return "Job remaining \(formatDurationLabel(remaining))"
    }

    private var jobRemainingEstimate: Double? {
        guard !videoSegments.isEmpty else { return nil }
        let durations = completedSegmentDurations.values.filter { $0.isFinite && $0 > 0 }
        guard !durations.isEmpty else { return nil }
        let average = durations.reduce(0, +) / Double(durations.count)
        let remainingCount = max(videoSegments.count - durations.count, 0)
        guard remainingCount > 0 else { return 0 }
        return average * Double(remainingCount)
    }

    private var jobStatusLabel: String {
        switch currentJob.displayStatus {
        case .pending:
            return "Pending"
        case .running:
            return "Running"
        case .pausing:
            return "Pausing"
        case .paused:
            return "Paused"
        case .completed:
            return "Completed"
        case .failed:
            return "Failed"
        case .cancelled:
            return "Cancelled"
        }
    }

    private var jobAuthor: String {
        metadataString(for: ["author", "book_author", "creator", "artist"]) ?? "Unknown author"
    }

    private var resolvedTvMetadata: [String: JSONValue]? {
        if let tvMetadata = subtitleTvMetadata?.mediaMetadata {
            return tvMetadata
        }
        guard let metadata = jobMetadata else { return nil }
        return extractTvMediaMetadata(from: metadata)
    }

    private var resolvedYoutubeMetadata: [String: JSONValue]? {
        if let youtubeMetadata = youtubeVideoMetadata?.youtubeMetadata {
            return youtubeMetadata
        }
        guard let tvMetadata = resolvedTvMetadata,
              let youtube = tvMetadata["youtube"]?.objectValue
        else {
            return nil
        }
        return youtube
    }

    private var resolvedTvTitle: String? {
        if let tvMetadata = resolvedTvMetadata,
           let show = tvMetadata["show"]?.objectValue,
           let name = show["name"]?.stringValue?.nonEmptyValue {
            return name
        }
        if let parsed = subtitleTvMetadata?.parsed?.series.nonEmptyValue {
            return parsed
        }
        if let source = subtitleTvMetadata?.sourceName?.nonEmptyValue {
            return source
        }
        return nil
    }

    private var resolvedTvEpisodeLabel: String? {
        guard let tvMetadata = resolvedTvMetadata,
              let episode = tvMetadata["episode"]?.objectValue
        else {
            return nil
        }
        let season = intValue(episode["season"])
        let number = intValue(episode["number"])
        let code: String? = {
            guard let season, let number, season > 0, number > 0 else { return nil }
            return String(format: "S%02dE%02d", season, number)
        }()
        let episodeTitle = episode["name"]?.stringValue?.nonEmptyValue
        let airdate = episode["airdate"]?.stringValue?.nonEmptyValue
        let parts = [code, episodeTitle, airdate].compactMap { $0 }
        return parts.isEmpty ? nil : parts.joined(separator: " · ")
    }

    private var resolvedYoutubeTitle: String? {
        resolvedYoutubeMetadata?["title"]?.stringValue?.nonEmptyValue
    }

    private var resolvedYoutubeChannel: String? {
        if let channel = resolvedYoutubeMetadata?["channel"]?.stringValue?.nonEmptyValue {
            return channel
        }
        return resolvedYoutubeMetadata?["uploader"]?.stringValue?.nonEmptyValue
    }

    private var jobVariant: PlayerChannelVariant {
        let type = currentJob.jobType.lowercased()
        if type.contains("youtube") {
            return .youtube
        }
        if type.contains("dub") {
            return .dub
        }
        if type.contains("subtitle") {
            return .subtitles
        }
        if type.contains("video") {
            return .video
        }
        if type.contains("nas") {
            return .nas
        }
        if type.contains("book") || type.contains("pipeline") {
            return .book
        }
        return .job
    }

    private var shouldFetchTvMetadata: Bool {
        switch jobVariant {
        case .subtitles, .youtube, .dub, .video:
            return true
        case .book, .nas, .job:
            return false
        }
    }

    private var shouldFetchYoutubeMetadata: Bool {
        switch jobVariant {
        case .youtube, .dub:
            return true
        case .book, .subtitles, .video, .nas, .job:
            return false
        }
    }

    private var itemTypeLabel: String {
        switch jobVariant {
        case .book:
            return "Book"
        case .subtitles:
            return "Subtitles"
        case .video, .youtube:
            return "Video"
        case .dub:
            return "Dubbing"
        case .nas:
            return "NAS"
        case .job:
            return "Job"
        }
    }

    private var linguistInputLanguage: String {
        metadataString(for: [
            "input_language",
            "original_language",
            "source_language",
            "translation_source_language",
            "book_language"
        ]) ?? metadataString(for: ["language"], maxDepth: 0) ?? ""
    }

    private var linguistLookupLanguage: String {
        metadataString(for: [
            "target_language",
            "translation_language",
            "target_languages",
            "book_language"
        ]) ?? metadataString(for: ["language"], maxDepth: 0) ?? ""
    }

    private var interactiveHeaderInfo: InteractivePlayerHeaderInfo {
        InteractivePlayerHeaderInfo(
            title: jobTitle,
            author: jobAuthor,
            itemTypeLabel: itemTypeLabel,
            coverURL: coverURL,
            secondaryCoverURL: secondaryCoverURL,
            languageFlags: languageFlags
        )
    }

    private var languageFlags: [LanguageFlagEntry] {
        LanguageFlagResolver.resolveFlags(
            originalLanguage: linguistInputLanguage.nonEmptyValue,
            translationLanguage: linguistLookupLanguage.nonEmptyValue
        )
    }

    private var coverURL: URL? {
        let candidates = coverCandidates()
        for candidate in candidates {
            if let url = resolveCoverCandidate(candidate) {
                return url
            }
        }
        return nil
    }

    private var secondaryCoverURL: URL? {
        guard let tvMetadata = resolvedTvMetadata else { return nil }
        let episode = resolveTvImage(from: tvMetadata, path: "episode")
        let show = resolveTvImage(from: tvMetadata, path: "show")
        let primary = episode ?? show
        guard let show, let primary, show != primary else { return nil }
        return resolveCoverCandidate(show)
    }

    private func coverCandidates() -> [String] {
        let metadata = jobMetadata
        var candidates: [String] = []
        var seen = Set<String>()

        func add(_ value: String?) {
            guard let trimmed = value?.nonEmptyValue else { return }
            guard !seen.contains(trimmed) else { return }
            seen.insert(trimmed)
            candidates.append(trimmed)
        }

        let isVideoJob = jobVariant != .book
        if isVideoJob {
            appendTvCandidates(add: add)
        }
        if let metadata {
            if let bookMetadata = extractBookMetadata(from: metadata) {
                add(bookMetadata["job_cover_asset_url"]?.stringValue)
                add(bookMetadata["job_cover_asset"]?.stringValue)
                add(bookMetadata["book_cover_file"]?.stringValue)
            }
            add(metadata["job_cover_asset_url"]?.stringValue)
            add(metadata["job_cover_asset"]?.stringValue)
            add(metadata["cover_url"]?.stringValue)
            add(metadata["cover"]?.stringValue)
        }
        if !isVideoJob {
            appendTvCandidates(add: add)
        }
        return candidates
    }

    private func resolveCoverCandidate(_ candidate: String) -> URL? {
        if let url = viewModel.resolvePath(candidate) {
            return url
        }
        if let base = appState.apiBaseURL, let url = URL(string: candidate, relativeTo: base) {
            return url
        }
        return URL(string: candidate)
    }

    private func appendTvCandidates(add: (String?) -> Void) {
        if let tvMetadata = resolvedTvMetadata {
            add(resolveTvImage(from: tvMetadata, path: "episode"))
            add(resolveTvImage(from: tvMetadata, path: "show"))
            add(resolveYoutubeThumbnailFromTvMetadata(tvMetadata))
        }
        if let youtubeMetadata = resolvedYoutubeMetadata {
            add(resolveYoutubeThumbnailFromYoutubeMetadata(youtubeMetadata))
        }
    }

    private var jobMetadata: [String: JSONValue]? {
        if let result = currentJob.result?.objectValue {
            return result
        }
        return currentJob.parameters?.objectValue
    }

    private func metadataString(for keys: [String], maxDepth: Int = 4) -> String? {
        let sources = [currentJob.result?.objectValue, currentJob.parameters?.objectValue].compactMap { $0 }
        for source in sources {
            if let found = metadataString(in: source, keys: keys, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    private func metadataString(
        in metadata: [String: JSONValue],
        keys: [String],
        maxDepth: Int
    ) -> String? {
        for key in keys {
            if let found = metadataString(in: metadata, key: key, maxDepth: maxDepth) {
                return found
            }
        }
        return nil
    }

    private func metadataString(
        in metadata: [String: JSONValue],
        key: String,
        maxDepth: Int
    ) -> String? {
        if let value = metadata[key]?.stringValue {
            return value
        }
        guard maxDepth > 0 else { return nil }
        for value in metadata.values {
            if let nested = value.objectValue {
                if let found = metadataString(in: nested, key: key, maxDepth: maxDepth - 1) {
                    return found
                }
            }
            if case let .array(items) = value {
                for entry in items {
                    if let nested = entry.objectValue,
                       let found = metadataString(in: nested, key: key, maxDepth: maxDepth - 1) {
                        return found
                    }
                }
            }
        }
        return nil
    }

    private func extractBookMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        if let direct = metadata["book_metadata"]?.objectValue {
            return direct
        }
        if let result = metadata["result"]?.objectValue,
           let nested = result["book_metadata"]?.objectValue {
            return nested
        }
        return nil
    }

    private func extractTvMediaMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        let paths: [[String]] = [
            ["result", "youtube_dub", "media_metadata"],
            ["result", "subtitle", "metadata", "media_metadata"],
            ["request", "media_metadata"],
            ["media_metadata"]
        ]
        for path in paths {
            if let value = nestedValue(metadata, path: path)?.objectValue {
                return value
            }
        }
        return nil
    }

    private func resolveTvImage(from tvMetadata: [String: JSONValue], path: String) -> String? {
        guard let section = tvMetadata[path]?.objectValue else { return nil }
        guard let imageValue = section["image"] else { return nil }
        if let direct = imageValue.stringValue {
            return direct
        }
        if let imageObject = imageValue.objectValue {
            return imageObject["medium"]?.stringValue ?? imageObject["original"]?.stringValue
        }
        return nil
    }

    private func resolveYoutubeThumbnailFromTvMetadata(_ tvMetadata: [String: JSONValue]) -> String? {
        guard let youtube = tvMetadata["youtube"]?.objectValue else { return nil }
        return youtube["thumbnail"]?.stringValue
    }

    private func resolveYoutubeThumbnailFromYoutubeMetadata(_ youtubeMetadata: [String: JSONValue]) -> String? {
        youtubeMetadata["thumbnail"]?.stringValue
    }

    private func nestedValue(_ source: [String: JSONValue], path: [String]) -> JSONValue? {
        var current: JSONValue = .object(source)
        for key in path {
            guard let object = current.objectValue, let next = object[key] else { return nil }
            current = next
        }
        return current
    }

    private func intValue(_ value: JSONValue?) -> Int? {
        guard let value else { return nil }
        switch value {
        case let .number(number) where number.isFinite:
            return Int(number)
        case .string:
            return Int(value.stringValue ?? "")
        case let .array(values):
            for entry in values {
                if let parsed = intValue(entry) {
                    return parsed
                }
            }
            return nil
        default:
            return nil
        }
    }

    @MainActor
    private func loadEntry() async {
        guard let configuration = appState.configuration else { return }
        sentenceIndex = nil
        resetResumeState()
        activeVideoSegmentID = nil
        completedSegmentDurations = [:]
        segmentDurations = [:]
        subtitleTvMetadata = nil
        youtubeVideoMetadata = nil
        jobStatus = job
        await viewModel.loadJob(
            jobId: job.jobId,
            configuration: configuration,
            origin: .job,
            preferLiveMedia: currentJob.status.isActive
        )
        await viewModel.updateChapterIndex(from: jobMetadata)
        await loadVideoMetadata()
        refreshActiveVideoSegment()
        preloadSegmentDurations()
        if isVideoPreferred {
            nowPlaying.clear()
        } else {
            configureNowPlaying()
            updateNowPlayingMetadata(sentenceIndex: sentenceIndex)
            updateNowPlayingPlayback(time: viewModel.audioCoordinator.currentTime)
        }
        if let userId = resumeUserId {
            await PlaybackResumeStore.shared.refreshCloudEntries(userId: userId)
        }
        if let resumeEntry = resolveResumeEntry() {
            pendingResumeEntry = resumeEntry
            showResumePrompt = true
            if isVideoPreferred {
                videoAutoPlay = false
            }
            return
        }
        resumeDecisionPending = false
        startPlaybackFromBeginning()
        await refreshJobStatus()
        startJobRefresh()
        if currentJob.status.isActive {
            viewModel.startLiveUpdates()
        }
    }

    @MainActor
    private func loadVideoMetadata() async {
        guard let configuration = appState.configuration else { return }
        let client = APIClient(configuration: configuration)
        if shouldFetchTvMetadata {
            do {
                subtitleTvMetadata = try await client.fetchSubtitleTvMetadata(jobId: currentJob.jobId)
            } catch {
                subtitleTvMetadata = nil
            }
        }
        if shouldFetchYoutubeMetadata {
            do {
                youtubeVideoMetadata = try await client.fetchYoutubeVideoMetadata(jobId: currentJob.jobId)
            } catch {
                youtubeVideoMetadata = nil
            }
        }
    }

    private func configureNowPlaying() {
        nowPlaying.configureRemoteCommands(
            onPlay: { viewModel.audioCoordinator.play() },
            onPause: { viewModel.audioCoordinator.pause() },
            onNext: { viewModel.skipSentence(forward: true) },
            onPrevious: { viewModel.skipSentence(forward: false) },
            onSeek: { viewModel.audioCoordinator.seek(to: $0) },
            onToggle: { viewModel.audioCoordinator.togglePlayback() },
            onSkipForward: nil,
            onSkipBackward: nil
        )
    }

    private func updateNowPlayingMetadata(sentenceIndex: Int?) {
        let title: String
        if let sentenceIndex, sentenceIndex > 0 {
            title = "\(jobTitle) · Sentence \(sentenceIndex)"
        } else {
            title = jobTitle
        }
        nowPlaying.updateMetadata(
            title: title,
            artist: jobAuthor.nonEmptyValue,
            album: jobTitle.nonEmptyValue,
            artworkURL: coverURL,
            queueIndex: sentenceIndex.map { max($0 - 1, 0) },
            queueCount: nil
        )
    }

    private func updateNowPlayingPlayback(time: Double) {
        guard !isVideoPreferred else { return }
        let highlightTime = viewModel.highlightingTime
        if let resolvedIndex = resolveResumeSentenceIndex(at: highlightTime) {
            if sentenceIndex != resolvedIndex {
                sentenceIndex = resolvedIndex
                updateNowPlayingMetadata(sentenceIndex: resolvedIndex)
            }
            recordInteractiveResume(sentenceIndex: resolvedIndex)
        } else if let sentence = viewModel.activeSentence(at: highlightTime) {
            let index = sentence.displayIndex ?? sentence.id
            if sentenceIndex != index {
                sentenceIndex = index
                updateNowPlayingMetadata(sentenceIndex: index)
            }
        }
        let playbackDuration = viewModel.selectedChunk.flatMap { viewModel.playbackDuration(for: $0) } ?? viewModel.audioCoordinator.duration
        let playbackTime = highlightTime.isFinite ? highlightTime : time
        nowPlaying.updatePlaybackState(
            isPlaying: viewModel.audioCoordinator.isPlaying,
            position: playbackTime,
            duration: playbackDuration
        )
    }

    private var resumeUserId: String? {
        appState.session?.user.username.nonEmptyValue ?? appState.lastUsername.nonEmptyValue
    }

    private var resumeItemType: String {
        currentJob.jobType.nonEmptyValue ?? itemTypeLabel.lowercased()
    }

    private func resetResumeState() {
        pendingResumeEntry = nil
        showResumePrompt = false
        videoResumeTime = nil
        videoResumeActionID = UUID()
        videoAutoPlay = false
        resumeDecisionPending = true
        lastRecordedSentence = nil
        lastRecordedTimeBucket = nil
        lastVideoTime = 0
        segmentDurationTask?.cancel()
        segmentDurationTask = nil
        #if !os(tvOS)
        showVideoPlayer = false
        #endif
    }

    private func resolveResumeEntry() -> PlaybackResumeEntry? {
        guard let userId = resumeUserId else { return nil }
        guard let entry = PlaybackResumeStore.shared.entry(for: currentJob.jobId, userId: userId) else { return nil }
        guard entry.isMeaningful else { return nil }
        if isVideoPreferred {
            return entry.kind == .time ? entry : nil
        }
        return entry.kind == .sentence ? entry : nil
    }

    private func startPlaybackFromBeginning() {
        if isVideoPreferred {
            startVideoPlayback(at: nil, presentPlayer: false)
        } else if viewModel.jobContext != nil {
            startInteractivePlayback(at: 1)
        }
    }

    private func applyResume(_ entry: PlaybackResumeEntry) {
        showResumePrompt = false
        pendingResumeEntry = nil
        resumeDecisionPending = false
        if isVideoPreferred {
            startVideoPlayback(at: entry.playbackTime, presentPlayer: true)
        } else {
            startInteractivePlayback(at: entry.sentenceNumber)
        }
    }

    private func startOver() {
        showResumePrompt = false
        pendingResumeEntry = nil
        resumeDecisionPending = false
        clearResumeEntry()
        if isVideoPreferred {
            startVideoPlayback(at: nil, presentPlayer: true)
        } else {
            startInteractivePlayback(at: 1)
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

    private func startVideoPlayback(at absoluteTime: Double?, presentPlayer: Bool) {
        videoAutoPlay = true
        if let target = resolveVideoResumeTarget(absoluteTime) {
            activeVideoSegmentID = target.segmentID
            videoResumeTime = target.localTime
        } else {
            if activeVideoSegmentID == nil {
                activeVideoSegmentID = videoSegments.first?.id
            }
            videoResumeTime = absoluteTime
        }
        videoResumeActionID = UUID()
        #if !os(tvOS)
        if presentPlayer {
            showVideoPlayer = true
        }
        #endif
    }

    #if !os(tvOS)
    private func handleVideoPreviewTap() {
        if let resumeEntry = resolveResumeEntry() {
            pendingResumeEntry = resumeEntry
            showResumePrompt = true
            videoAutoPlay = false
            return
        }
        startVideoPlayback(at: nil, presentPlayer: true)
    }
    #endif

    private func resolveVideoResumeTarget(_ absoluteTime: Double?) -> VideoResumeTarget? {
        guard let absoluteTime, absoluteTime > 0 else { return nil }
        guard !videoSegments.isEmpty else { return nil }
        if videoSegments.count == 1 {
            return VideoResumeTarget(segmentID: videoSegments[0].id, localTime: absoluteTime)
        }
        var accumulated: Double = 0
        for segment in videoSegments {
            let duration = segmentDurations[segment.id] ?? completedSegmentDurations[segment.id]
            if let duration, duration.isFinite, duration > 0 {
                let end = accumulated + duration
                if absoluteTime < end {
                    return VideoResumeTarget(segmentID: segment.id, localTime: max(0, absoluteTime - accumulated))
                }
                accumulated = end
            }
        }
        if let last = videoSegments.last {
            return VideoResumeTarget(segmentID: last.id, localTime: max(0, absoluteTime - accumulated))
        }
        return nil
    }

    private func clearResumeEntry() {
        guard let userId = resumeUserId else { return }
        PlaybackResumeStore.shared.clearEntry(jobId: currentJob.jobId, userId: userId)
    }

    private func resumePromptMessage(for entry: PlaybackResumeEntry) -> String {
        switch entry.kind {
        case .sentence:
            let sentence = entry.sentenceNumber ?? 1
            return "Continue from sentence \(sentence)."
        case .time:
            let time = entry.playbackTime ?? 0
            return "Continue from \(formatPlaybackTime(time))."
        }
    }

    private func formatPlaybackTime(_ time: Double) -> String {
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = time >= 3600 ? [.hour, .minute, .second] : [.minute, .second]
        formatter.zeroFormattingBehavior = .pad
        return formatter.string(from: time) ?? "0:00"
    }

    private var currentJob: PipelineStatusResponse {
        jobStatus ?? job
    }

    private func startJobRefresh() {
        stopJobRefresh()
        jobRefreshTask = Task {
            while !Task.isCancelled {
                await refreshJobStatus()
                try? await Task.sleep(nanoseconds: jobRefreshInterval)
            }
        }
    }

    private func stopJobRefresh() {
        jobRefreshTask?.cancel()
        jobRefreshTask = nil
    }

    @MainActor
    private func refreshJobStatus() async {
        guard let configuration = appState.configuration else { return }
        do {
            let client = APIClient(configuration: configuration)
            let status = try await client.fetchPipelineStatus(jobId: job.jobId)
            jobStatus = status
            if !status.status.isActive {
                viewModel.stopLiveUpdates()
            }
        } catch {
            return
        }
    }

    private func refreshActiveVideoSegment() {
        guard !videoSegments.isEmpty else {
            activeVideoSegmentID = nil
            return
        }
        if let activeVideoSegmentID,
           videoSegments.contains(where: { $0.id == activeVideoSegmentID }) {
            return
        }
        activeVideoSegmentID = videoSegments.first?.id
    }

    private func preloadSegmentDurations() {
        segmentDurationTask?.cancel()
        segmentDurationTask = nil
        guard isVideoPreferred else { return }
        guard !videoSegments.isEmpty else { return }
        let pending = videoSegments.compactMap { segment -> (String, URL)? in
            guard segmentDurations[segment.id] == nil else { return nil }
            guard let url = viewModel.resolveMediaURL(for: segment.videoFile) else { return nil }
            return (segment.id, url)
        }
        guard !pending.isEmpty else { return }
        segmentDurationTask = Task { @MainActor in
            for (segmentID, url) in pending {
                if Task.isCancelled { return }
                let asset = AVURLAsset(url: url)
                do {
                    let duration = try await asset.load(.duration)
                    let seconds = duration.seconds
                    if seconds.isFinite, seconds > 0 {
                        segmentDurations[segmentID] = seconds
                    }
                } catch {
                    continue
                }
            }
        }
    }

    private func handleVideoSegmentEnded(duration: Double) {
        guard !videoSegments.isEmpty else { return }
        guard let activeID = activeVideoSegmentID ?? videoSegments.first?.id else { return }
        if duration.isFinite, duration > 0 {
            completedSegmentDurations[activeID] = duration
            segmentDurations[activeID] = duration
        }
        guard let currentIndex = videoSegments.firstIndex(where: { $0.id == activeID }) else { return }
        let nextIndex = currentIndex + 1
        guard videoSegments.indices.contains(nextIndex) else { return }
        activeVideoSegmentID = videoSegments[nextIndex].id
        videoResumeTime = nil
        videoAutoPlay = true
        videoResumeActionID = UUID()
    }

    private func handleVideoSegmentSelection(_ segmentID: String) {
        guard activeVideoSegmentID != segmentID else { return }
        activeVideoSegmentID = segmentID
        videoResumeTime = nil
        videoAutoPlay = true
        videoResumeActionID = UUID()
    }

    private func handleVideoPlaybackProgress(time: Double, isPlaying: Bool) {
        let absoluteTime = absoluteVideoTime(for: activeVideoSegmentID ?? videoSegments.first?.id, segmentTime: time)
        lastVideoTime = absoluteTime
        recordVideoResume(time: absoluteTime, isPlaying: isPlaying)
    }

    private func absoluteVideoTime(for segmentID: String?, segmentTime: Double) -> Double {
        guard segmentTime.isFinite else { return 0 }
        return max(0, segmentOffset(for: segmentID) + segmentTime)
    }

    private func segmentOffset(for segmentID: String?) -> Double {
        guard let segmentID,
              let index = videoSegments.firstIndex(where: { $0.id == segmentID })
        else {
            return 0
        }
        var offset: Double = 0
        for segment in videoSegments.prefix(index) {
            if let duration = segmentDurations[segment.id] ?? completedSegmentDurations[segment.id],
               duration.isFinite,
               duration > 0
            {
                offset += duration
            }
        }
        return offset
    }

    private func recordInteractiveResume(sentenceIndex: Int) {
        guard !resumeDecisionPending else { return }
        guard let userId = resumeUserId else { return }
        guard sentenceIndex > 0 else { return }
        guard sentenceIndex != lastRecordedSentence else { return }
        lastRecordedSentence = sentenceIndex
        let entry = PlaybackResumeEntry(
            jobId: currentJob.jobId,
            itemType: resumeItemType,
            kind: .sentence,
            updatedAt: Date().timeIntervalSince1970,
            sentenceNumber: sentenceIndex,
            playbackTime: nil
        )
        PlaybackResumeStore.shared.updateEntry(entry, userId: userId)
    }

    private func recordVideoResume(time: Double, isPlaying: Bool) {
        guard !resumeDecisionPending else { return }
        guard let userId = resumeUserId else { return }
        guard time.isFinite, time >= 0 else { return }
        let bucket = Int(time / 5)
        if bucket == lastRecordedTimeBucket, isPlaying {
            return
        }
        lastRecordedTimeBucket = bucket
        let entry = PlaybackResumeEntry(
            jobId: currentJob.jobId,
            itemType: resumeItemType,
            kind: .time,
            updatedAt: Date().timeIntervalSince1970,
            sentenceNumber: nil,
            playbackTime: time
        )
        PlaybackResumeStore.shared.updateEntry(entry, userId: userId)
    }

    private func persistResumeOnExit() {
        if isVideoPreferred {
            recordVideoResume(time: lastVideoTime, isPlaying: false)
        } else if let sentenceIndex {
            recordInteractiveResume(sentenceIndex: sentenceIndex)
        }
    }

    private func resolveResumeSentenceIndex(at highlightTime: Double) -> Int? {
        guard let chunk = viewModel.selectedChunk else { return nil }
        let resolved = viewModel.activeSentence(at: highlightTime).flatMap { sentence in
            resolveSentenceNumber(for: sentence, in: chunk)
        }
        let fallback = estimateSentenceNumber(for: chunk, at: highlightTime)
        guard let resolved else { return fallback }
        guard let fallback else { return resolved }
        if resolved == fallback {
            return resolved
        }
        if shouldPreferEstimatedIndex(for: chunk, resolved: resolved, estimated: fallback, time: highlightTime) {
            return fallback
        }
        return resolved
    }

    private func resolveSentenceNumber(for sentence: InteractiveChunk.Sentence, in chunk: InteractiveChunk) -> Int? {
        if let displayIndex = sentence.displayIndex {
            return displayIndex
        }
        if let index = chunk.sentences.firstIndex(where: { $0.id == sentence.id && $0.displayIndex == sentence.displayIndex }) {
            if let start = chunk.startSentence {
                return start + index
            }
            if let first = chunk.sentences.first?.id {
                return first + index
            }
        }
        return sentence.id
    }

    private func estimateSentenceNumber(for chunk: InteractiveChunk, at time: Double) -> Int? {
        let count: Int = {
            if let start = chunk.startSentence, let end = chunk.endSentence, end >= start {
                return end - start + 1
            }
            return chunk.sentences.count
        }()
        guard count > 0 else { return nil }
        let base: Int? = {
            if let start = chunk.startSentence {
                return start
            }
            if let first = chunk.sentences.first?.displayIndex {
                return first
            }
            return chunk.sentences.first?.id
        }()
        guard let base else { return nil }
        guard count > 1 else { return base }
        let duration = viewModel.playbackDuration(for: chunk) ?? viewModel.audioCoordinator.duration
        guard duration.isFinite, duration > 0 else { return base }
        let progress = min(max(time / duration, 0), 1)
        let offset = Int((Double(count - 1) * progress).rounded(.down))
        return base + offset
    }

    private func shouldPreferEstimatedIndex(
        for chunk: InteractiveChunk,
        resolved: Int,
        estimated: Int,
        time: Double
    ) -> Bool {
        let count: Int = {
            if let start = chunk.startSentence, let end = chunk.endSentence, end >= start {
                return end - start + 1
            }
            return chunk.sentences.count
        }()
        guard count > 1 else { return false }
        let base = chunk.startSentence ?? chunk.sentences.first?.displayIndex ?? chunk.sentences.first?.id
        guard let base, resolved == base else { return false }
        let duration = viewModel.playbackDuration(for: chunk) ?? viewModel.audioCoordinator.duration
        guard duration.isFinite, duration > 0 else { return false }
        let progress = min(max(time / duration, 0), 1)
        return progress > 0.1 && estimated > resolved
    }

    private func formatDurationLabel(_ value: Double) -> String {
        let total = max(0, Int(value.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let seconds = total % 60
        return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
    }

    private func resolveSubtitleFiles(from media: [String: [PipelineMediaFile]]) -> [PipelineMediaFile] {
        var files: [PipelineMediaFile] = []
        let keys = ["text", "subtitle", "subtitles", "captions"]
        for key in keys {
            files.append(contentsOf: media[key] ?? [])
        }
        if let chunks = viewModel.mediaResponse?.chunks {
            for chunk in chunks {
                files.append(contentsOf: chunk.files.filter { isSubtitleFile($0) })
            }
        }
        return uniqueFiles(files)
    }

    private func resolveVideoFiles(from media: [String: [PipelineMediaFile]]) -> [PipelineMediaFile] {
        var files = media["video"] ?? []
        if let chunks = viewModel.mediaResponse?.chunks {
            for chunk in chunks {
                files.append(contentsOf: chunk.files.filter { isVideoFile($0) })
            }
        }
        return uniqueFiles(files)
    }

    private func uniqueFiles(_ files: [PipelineMediaFile]) -> [PipelineMediaFile] {
        var seen = Set<String>()
        var deduped: [PipelineMediaFile] = []
        for file in files {
            let signature = fileSignature(file)
            guard !seen.contains(signature) else { continue }
            seen.insert(signature)
            deduped.append(file)
        }
        return deduped
    }

    private func fileSignature(_ file: PipelineMediaFile) -> String {
        if let path = file.path?.nonEmptyValue {
            return path
        }
        if let relative = file.relativePath?.nonEmptyValue {
            return relative
        }
        if let url = file.url?.nonEmptyValue {
            return url
        }
        return file.name
    }

    private func subtitleTracks(from files: [PipelineMediaFile]) -> [VideoSubtitleTrack] {
        var tracks: [VideoSubtitleTrack] = []
        var seen: Set<String> = []
        for file in files {
            guard let url = viewModel.resolveMediaURL(for: file) else { continue }
            let sourcePath = file.relativePath ?? file.path ?? file.name
            let format = SubtitleParser.format(for: sourcePath)
            let id = subtitleTrackIdentifier(for: file, url: url, sourcePath: sourcePath)
            guard !seen.contains(id) else { continue }
            seen.insert(id)
            let label = subtitleTrackLabel(for: file, fallback: "Subtitle \(tracks.count + 1)")
            tracks.append(VideoSubtitleTrack(id: id, url: url, format: format, label: label))
        }
        return tracks
    }

    private func subtitleTrackIdentifier(for file: PipelineMediaFile, url: URL, sourcePath: String) -> String {
        let base = subtitleTrackBase(for: file, url: url, sourcePath: sourcePath)
        var suffixes: [String] = []
        if let chunkID = file.chunkID?.nonEmptyValue {
            suffixes.append("chunk=\(chunkID)")
        }
        if let range = file.rangeFragment?.nonEmptyValue {
            suffixes.append("range=\(range)")
        }
        if let start = file.startSentence {
            if let end = file.endSentence {
                suffixes.append("sent=\(start)-\(end)")
            } else {
                suffixes.append("sent=\(start)")
            }
        }
        if suffixes.isEmpty, let key = segmentKey(for: file) {
            suffixes.append("key=\(key)")
        }
        guard !suffixes.isEmpty else { return base }
        return "\(base)#\(suffixes.joined(separator: "|"))"
    }

    private func subtitleTrackBase(for file: PipelineMediaFile, url: URL, sourcePath: String) -> String {
        var base = sourcePath.nonEmptyValue ?? url.absoluteString
        let hasPathSeparator = base.contains("/") || base.contains("\\")
        if !hasPathSeparator, let urlValue = file.url?.nonEmptyValue {
            base = "\(base)#url=\(urlValue)"
        }
        return base
    }

    private func segmentLabel(for segment: JobVideoSegment, index: Int) -> String {
        let base = "Chunk \(index + 1)"
        if let chunk = segment.chunk {
            if let start = chunk.startSentence, let end = chunk.endSentence {
                return "\(base) · Sentences \(start)-\(end)"
            }
            if let start = chunk.startSentence {
                return "\(base) · Sentence \(start)"
            }
            if let range = chunk.rangeFragment?.nonEmptyValue {
                return "\(base) · \(range)"
            }
            if let chunkID = chunk.chunkID?.nonEmptyValue {
                return "\(base) · ID \(chunkID)"
            }
        }
        if let start = segment.videoFile.startSentence, let end = segment.videoFile.endSentence {
            return "\(base) · Sentences \(start)-\(end)"
        }
        if let start = segment.videoFile.startSentence {
            return "\(base) · Sentence \(start)"
        }
        if let range = segment.videoFile.rangeFragment?.nonEmptyValue {
            return "\(base) · \(range)"
        }
        if let chunkID = segment.videoFile.chunkID?.nonEmptyValue {
            return "\(base) · ID \(chunkID)"
        }
        return base
    }

    private func matchSubtitleFiles(for video: PipelineMediaFile, in subtitleFiles: [PipelineMediaFile]) -> [PipelineMediaFile] {
        if let chunkID = video.chunkID?.nonEmptyValue {
            let matches = subtitleFiles.filter { $0.chunkID == chunkID }
            if !matches.isEmpty { return matches }
        }
        if let range = video.rangeFragment?.nonEmptyValue {
            let matches = subtitleFiles.filter { $0.rangeFragment == range }
            if !matches.isEmpty { return matches }
        }
        if let start = video.startSentence, let end = video.endSentence {
            let matches = subtitleFiles.filter { file in
                guard let fileStart = file.startSentence, let fileEnd = file.endSentence else { return false }
                return fileStart <= end && fileEnd >= start
            }
            if !matches.isEmpty { return matches }
        }
        if let key = segmentKey(for: video) {
            let matches = subtitleFiles.filter { segmentKey(for: $0) == key }
            if !matches.isEmpty { return matches }
        }
        if let directoryName = fileDirectoryName(for: video) {
            let matches = subtitleFiles.filter { fileDirectoryName(for: $0) == directoryName }
            if !matches.isEmpty { return matches }
        }
        if let stem = fileStem(for: video) {
            let exactMatches = subtitleFiles.filter { fileStem(for: $0) == stem }
            if !exactMatches.isEmpty { return exactMatches }
            let fuzzyMatches = subtitleFiles.filter { file in
                guard let subtitleStem = fileStem(for: file) else { return false }
                return subtitleStem.contains(stem) || stem.contains(subtitleStem)
            }
            if !fuzzyMatches.isEmpty { return fuzzyMatches }
        }
        return []
    }

    private func sortKey(for file: PipelineMediaFile, fallback: Int) -> Int {
        if let start = file.startSentence {
            return start
        }
        if let chunkID = file.chunkID, let numeric = Int(chunkID.filter(\.isNumber)) {
            return numeric
        }
        if let stem = fileStem(for: file) {
            let digits = stem.filter(\.isNumber)
            if let numeric = Int(digits), !digits.isEmpty {
                return numeric
            }
        }
        return fallback
    }

    private func segmentID(for file: PipelineMediaFile, chunk: PipelineMediaChunk?, fallback: Int) -> String {
        file.chunkID
            ?? chunk?.chunkID
            ?? file.rangeFragment
            ?? chunk?.rangeFragment
            ?? file.name.nonEmptyValue
            ?? "video-\(fallback)"
    }

    private func buildSegments(from chunks: [PipelineMediaChunk], media: [String: [PipelineMediaFile]]) -> [JobVideoSegment] {
        let subtitleFiles = resolveSubtitleFiles(from: media)
        let sortedChunks = chunks.enumerated().sorted { lhs, rhs in
            let left = chunkSortKey(for: lhs.element, fallback: lhs.offset)
            let right = chunkSortKey(for: rhs.element, fallback: rhs.offset)
            if left == right {
                return lhs.offset < rhs.offset
            }
            return left < right
        }
        let sortedSubtitles = subtitleFiles.enumerated().sorted { lhs, rhs in
            let left = sortKey(for: lhs.element, fallback: lhs.offset)
            let right = sortKey(for: rhs.element, fallback: rhs.offset)
            if left == right {
                return lhs.offset < rhs.offset
            }
            return left < right
        }
        var segments: [JobVideoSegment] = []
        for (chunkIndex, chunkEntry) in sortedChunks.enumerated() {
            let chunk = chunkEntry.element
            let chunkVideoFiles = chunk.files.filter { isVideoFile($0) }
            guard !chunkVideoFiles.isEmpty else { continue }
            let chunkSubtitleFiles = chunk.files.filter { isSubtitleFile($0) }
            let chunkMatches = matchSubtitleFiles(for: chunk, in: subtitleFiles)
            let sortedVideos = chunkVideoFiles.enumerated().sorted { lhs, rhs in
                let left = sortKey(for: lhs.element, fallback: lhs.offset)
                let right = sortKey(for: rhs.element, fallback: rhs.offset)
                if left == right {
                    return lhs.offset < rhs.offset
                }
                return left < right
            }
            for (videoOffset, videoEntry) in sortedVideos.enumerated() {
                let videoFile = videoEntry.element
                let matched = matchSubtitleFiles(for: videoFile, in: subtitleFiles)
                let resolvedSubtitles: [PipelineMediaFile]
                if !chunkSubtitleFiles.isEmpty {
                    resolvedSubtitles = chunkSubtitleFiles
                } else if !chunkMatches.isEmpty {
                    resolvedSubtitles = chunkMatches
                } else if !matched.isEmpty {
                    resolvedSubtitles = matched
                } else if sortedSubtitles.count == sortedChunks.count,
                          sortedSubtitles.indices.contains(chunkIndex) {
                    resolvedSubtitles = [sortedSubtitles[chunkIndex].element]
                } else {
                    resolvedSubtitles = []
                }
                let fallback = chunkIndex * 100 + videoOffset
                segments.append(
                    JobVideoSegment(
                        id: segmentID(for: videoFile, chunk: chunk, fallback: fallback),
                        videoFile: videoFile,
                        subtitleFiles: resolvedSubtitles,
                        chunk: chunk
                    )
                )
            }
        }
        return segments
    }

    private func matchSubtitleFiles(for chunk: PipelineMediaChunk, in subtitleFiles: [PipelineMediaFile]) -> [PipelineMediaFile] {
        if let chunkID = chunk.chunkID?.nonEmptyValue {
            let matches = subtitleFiles.filter { $0.chunkID == chunkID }
            if !matches.isEmpty { return matches }
        }
        if let range = chunk.rangeFragment?.nonEmptyValue {
            let matches = subtitleFiles.filter { $0.rangeFragment == range }
            if !matches.isEmpty { return matches }
        }
        if let start = chunk.startSentence, let end = chunk.endSentence {
            let matches = subtitleFiles.filter { file in
                guard let fileStart = file.startSentence, let fileEnd = file.endSentence else { return false }
                return fileStart <= end && fileEnd >= start
            }
            if !matches.isEmpty { return matches }
        }
        return []
    }

    private func chunkSortKey(for chunk: PipelineMediaChunk, fallback: Int) -> Int {
        if let start = chunk.startSentence {
            return start
        }
        if let chunkID = chunk.chunkID, let numeric = Int(chunkID.filter(\.isNumber)) {
            return numeric
        }
        if let range = chunk.rangeFragment?.nonEmptyValue {
            let digits = range.filter(\.isNumber)
            if let numeric = Int(digits), !digits.isEmpty {
                return numeric
            }
        }
        return fallback
    }

    private func isVideoFile(_ file: PipelineMediaFile) -> Bool {
        let type = file.type?.lowercased() ?? ""
        if type.contains("video") { return true }
        if ["mp4", "m4v", "mov", "mkv", "webm"].contains(type) { return true }
        let path = (file.relativePath ?? file.path ?? file.name).lowercased()
        if let ext = path.split(separator: ".").last {
            return ["mp4", "m4v", "mov", "mkv", "webm"].contains(String(ext))
        }
        return false
    }

    private func isSubtitleFile(_ file: PipelineMediaFile) -> Bool {
        let type = file.type?.lowercased() ?? ""
        if type.contains("subtitle")
            || type.contains("caption")
            || type == "text"
            || type == "subtitles"
            || type == "captions"
            || type == "ass"
            || type == "vtt"
            || type == "srt"
        {
            return true
        }
        let path = file.relativePath ?? file.path ?? file.name
        let format = SubtitleParser.format(for: path)
        return format != .unknown
    }

    private func segmentKey(for file: PipelineMediaFile) -> String? {
        if let chunkID = file.chunkID?.nonEmptyValue {
            return "chunk:\(chunkID)"
        }
        if let range = file.rangeFragment?.nonEmptyValue {
            return "range:\(range)"
        }
        if let directory = fileDirectoryPath(for: file) {
            return "dir:\(directory)"
        }
        if let stem = fileStem(for: file) {
            return "stem:\(stem)"
        }
        return nil
    }

    private func fileStem(for file: PipelineMediaFile) -> String? {
        let raw = file.relativePath ?? file.path ?? file.name
        let filename = raw.split(whereSeparator: { $0 == "/" || $0 == "\\" }).last.map(String.init) ?? raw
        if let dotIndex = filename.lastIndex(of: ".") {
            let stem = filename[..<dotIndex]
            return stem.isEmpty ? nil : String(stem)
        }
        return filename.nonEmptyValue
    }

    private func fileDirectoryPath(for file: PipelineMediaFile) -> String? {
        let raw = file.relativePath ?? file.path ?? file.name
        let parts = raw.split(whereSeparator: { $0 == "/" || $0 == "\\" })
        guard parts.count > 1 else { return nil }
        return parts.dropLast().joined(separator: "/").nonEmptyValue
    }

    private func fileDirectoryName(for file: PipelineMediaFile) -> String? {
        guard let directory = fileDirectoryPath(for: file) else { return nil }
        let parts = directory.split(whereSeparator: { $0 == "/" || $0 == "\\" })
        return parts.last.map(String.init)
    }
}

private struct JobVideoSegment: Identifiable {
    let id: String
    let videoFile: PipelineMediaFile
    let subtitleFiles: [PipelineMediaFile]
    let chunk: PipelineMediaChunk?
}

private struct VideoResumeTarget {
    let segmentID: String
    let localTime: Double
}
