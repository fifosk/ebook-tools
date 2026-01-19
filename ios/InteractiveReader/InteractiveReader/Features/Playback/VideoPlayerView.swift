import AVFoundation
import SwiftUI
import Foundation
#if canImport(UIKit)
import UIKit
#endif

#if canImport(MediaPlayer)
import MediaPlayer
#endif

struct VideoPlayerView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) var dismiss

    let videoURL: URL
    let subtitleTracks: [VideoSubtitleTrack]
    let metadata: VideoPlaybackMetadata
    let autoPlay: Bool
    let resumeTime: Double?
    let resumeActionID: UUID
    let nowPlaying: NowPlayingCoordinator
    let linguistInputLanguage: String
    let linguistLookupLanguage: String
    let linguistExplanationLanguage: String
    let segmentOptions: [VideoSegmentOption]
    let selectedSegmentID: String?
    let onSelectSegment: ((String) -> Void)?
    let jobProgressLabel: String?
    let jobRemainingLabel: String?
    let onPlaybackProgress: ((Double, Bool) -> Void)?
    let onPlaybackEnded: ((Double) -> Void)?
    let bookmarkUserId: String?
    let bookmarkJobId: String?
    let bookmarkItemType: String?

    @StateObject var coordinator = VideoPlayerCoordinator()
    @State var cues: [VideoSubtitleCue] = []
    @State var subtitleError: String?
    @State var selectedTrack: VideoSubtitleTrack?
    @State var subtitleCache: [String: [VideoSubtitleCue]] = [:]
    @State var subtitleTask: Task<Void, Never>?
    @State var subtitleLoadToken = UUID()
    @State var subtitleLoadingKey: String?
    @State var subtitleVisibility = SubtitleVisibility()
    @State var showSubtitleSettings = false
    @State var showTVControls = true
    @AppStorage("player.headerCollapsed") var isHeaderCollapsed = false
    @AppStorage("video.playbackRate") var playbackRateValue: Double = 1.0
    @State var scrubberValue: Double = 0
    @State var isScrubbing = false
    @State var controlsHideTask: Task<Void, Never>?
    @State var forceHideControlsOnPlay = false
    @AppStorage("video.subtitle.fontScale") var subtitleFontScaleValue: Double =
        Double(VideoPlayerView.defaultSubtitleFontScale)
    @AppStorage("video.subtitle.bubbleFontScale") var subtitleLinguistFontScaleValue: Double = 1.0
    @State var isShortcutHelpPinned = false
    @State var isShortcutHelpModifierActive = false
    @State var subtitleSelection: VideoSubtitleWordSelection?
    @State var subtitleSelectionRange: VideoSubtitleWordSelectionRange?
    @State var subtitleBubble: VideoLinguistBubbleState?
    @State var subtitleInteractionFrame: CGRect = .null
    @State var subtitleLookupTask: Task<Void, Never>?
    @State var subtitleSpeechTask: Task<Void, Never>?
    @State var subtitleAutoLookupTask: Task<Void, Never>?
    @AppStorage("video.player.verticalOffset") var videoVerticalOffsetValue: Double = 0
    @State var videoDragTranslation: CGFloat = 0
    @State var isVideoDragGestureActive = false
    @AppStorage(MyLinguistPreferences.lookupLanguageKey) var storedLookupLanguage: String = ""
    @AppStorage(MyLinguistPreferences.llmModelKey) var storedLlmModel: String =
        MyLinguistPreferences.defaultLlmModel
    @State var availableLlmModels: [String] = []
    @State var didLoadLlmModels = false
    @State var subtitleActiveCueID: UUID?
    @State var isManualSubtitleNavigation = false
    @State var pendingResumeTime: Double?
    @State var pendingBookmarkSeek: PendingVideoBookmarkSeek?
    @StateObject var pronunciationSpeaker = PronunciationSpeaker()
    @State var isTearingDown = false
    @State var bookmarks: [PlaybackBookmarkEntry] = []
    #if os(iOS)
    @State var isVideoScrubGestureActive = false
    @State var videoScrubStartTime: Double = 0
    @State var videoViewportSize: CGSize = .zero
    #endif

    let subtitleFontScaleStep: CGFloat = 0.1
    let subtitleFontScaleMin: CGFloat = 0.7
    let subtitleFontScaleMax: CGFloat = 2.0
    let subtitleLinguistFontScaleMin: CGFloat = 0.8
    let subtitleLinguistFontScaleMax: CGFloat = 1.6
    let subtitleLinguistFontScaleStep: CGFloat = 0.05
    let subtitleAutoLookupDelayNanos: UInt64 = 1_000_000_000

    static var defaultSubtitleFontScale: CGFloat {
        #if os(tvOS)
        return 0.8
        #else
        return 1.0
        #endif
    }

    static let playbackRateOptions: [Double] = stride(from: 0.5, through: 1.5, by: 0.1).map { value in
        (value * 10).rounded() / 10
    }

    static func clampPlaybackRate(_ value: Double) -> Double {
        let clamped = min(max(value, 0.5), 1.5)
        return (clamped * 10).rounded() / 10
    }

    var resolvedBookmarkUserId: String {
        bookmarkUserId?.nonEmptyValue ?? "anonymous"
    }

    var resolvedBookmarkJobId: String? {
        bookmarkJobId?.nonEmptyValue
    }

    var resolvedBookmarkItemType: String {
        bookmarkItemType?.nonEmptyValue ?? "video"
    }

    var bookmarkIdentityKey: String {
        "\(resolvedBookmarkUserId)|\(resolvedBookmarkJobId ?? "")"
    }

    var canUseBookmarks: Bool {
        resolvedBookmarkJobId != nil
    }

    var resolvedPlaybackRate: Double {
        Self.clampPlaybackRate(playbackRateValue)
    }

    var metadataUpdateKey: String {
        [
            metadata.title,
            metadata.subtitle ?? "",
            metadata.artist ?? "",
            metadata.album ?? "",
            metadata.artworkURL?.absoluteString ?? "",
            metadata.secondaryArtworkURL?.absoluteString ?? ""
        ]
        .joined(separator: "|")
    }

    init(
        videoURL: URL,
        subtitleTracks: [VideoSubtitleTrack],
        metadata: VideoPlaybackMetadata,
        autoPlay: Bool = false,
        resumeTime: Double? = nil,
        resumeActionID: UUID = UUID(),
        nowPlaying: NowPlayingCoordinator,
        linguistInputLanguage: String = "",
        linguistLookupLanguage: String = "English",
        linguistExplanationLanguage: String = "English",
        segmentOptions: [VideoSegmentOption] = [],
        selectedSegmentID: String? = nil,
        onSelectSegment: ((String) -> Void)? = nil,
        jobProgressLabel: String? = nil,
        jobRemainingLabel: String? = nil,
        onPlaybackProgress: ((Double, Bool) -> Void)? = nil,
        onPlaybackEnded: ((Double) -> Void)? = nil,
        bookmarkUserId: String? = nil,
        bookmarkJobId: String? = nil,
        bookmarkItemType: String? = nil
    ) {
        self.videoURL = videoURL
        self.subtitleTracks = subtitleTracks
        self.metadata = metadata
        self.autoPlay = autoPlay
        self.resumeTime = resumeTime
        self.resumeActionID = resumeActionID
        self.nowPlaying = nowPlaying
        self.linguistInputLanguage = linguistInputLanguage
        self.linguistLookupLanguage = linguistLookupLanguage
        self.linguistExplanationLanguage = linguistExplanationLanguage
        self.segmentOptions = segmentOptions
        self.selectedSegmentID = selectedSegmentID
        self.onSelectSegment = onSelectSegment
        self.jobProgressLabel = jobProgressLabel
        self.jobRemainingLabel = jobRemainingLabel
        self.onPlaybackProgress = onPlaybackProgress
        self.onPlaybackEnded = onPlaybackEnded
        self.bookmarkUserId = bookmarkUserId
        self.bookmarkJobId = bookmarkJobId
        self.bookmarkItemType = bookmarkItemType
    }

    var body: some View {
        ZStack {
            playerContent
        }
        #if os(iOS)
        .overlay(alignment: .leading) {
            if isPhone {
                EdgeSwipeBackOverlay {
                    dismiss()
                }
            }
        }
        #endif
        #if os(tvOS)
        .onExitCommand {
            handleExitCommand()
        }
        #endif
        .onAppear {
            isTearingDown = false
            loadLlmModelsIfNeeded()
            refreshBookmarks()
            coordinator.onPlaybackEnded = { [weak coordinator] in
                guard let coordinator else { return }
                let duration = coordinator.duration.isFinite && coordinator.duration > 0
                    ? coordinator.duration
                : coordinator.currentTime
                onPlaybackEnded?(duration)
            }
            pendingResumeTime = resumeTime
            let resolvedRate = Self.clampPlaybackRate(playbackRateValue)
            if resolvedRate != playbackRateValue {
                playbackRateValue = resolvedRate
            }
            coordinator.setPlaybackRate(resolvedRate)
            coordinator.load(url: videoURL, autoPlay: autoPlay && resumeTime == nil)
            configureNowPlaying()
            updateNowPlayingMetadata()
            updateNowPlayingPlayback()
            selectDefaultTrackIfNeeded()
            scrubberValue = 0
            isScrubbing = false
            showTVControls = true
            scheduleControlsAutoHide()
            applyPendingResumeIfPossible()
            applyPendingBookmarkIfPossible()
        }
        .onDisappear {
            coordinator.onPlaybackEnded = nil
        }
        .onChange(of: videoURL) { _, newURL in
            isTearingDown = false
            subtitleSelection = nil
            subtitleSelectionRange = nil
            subtitleCache.removeAll()
            pendingResumeTime = resumeTime
            let resolvedRate = Self.clampPlaybackRate(playbackRateValue)
            if resolvedRate != playbackRateValue {
                playbackRateValue = resolvedRate
            }
            coordinator.setPlaybackRate(resolvedRate)
            coordinator.load(url: newURL, autoPlay: autoPlay && resumeTime == nil)
            updateNowPlayingMetadata()
            updateNowPlayingPlayback()
            selectDefaultTrackIfNeeded()
            loadSubtitles()
            scrubberValue = 0
            isScrubbing = false
            showTVControls = true
            scheduleControlsAutoHide()
            applyPendingResumeIfPossible()
            applyPendingBookmarkIfPossible()
        }
        .onChange(of: resumeActionID) { _, _ in
            pendingResumeTime = resumeTime ?? 0
            applyPendingResumeIfPossible()
        }
        .onChange(of: metadataUpdateKey) { _, _ in
            updateNowPlayingMetadata()
        }
        .onChange(of: resumeTime) { _, newValue in
            if newValue != nil {
                pendingResumeTime = newValue
                applyPendingResumeIfPossible()
            }
        }
        .onChange(of: playbackRateValue) { _, newValue in
            let resolvedRate = Self.clampPlaybackRate(newValue)
            if resolvedRate != newValue {
                playbackRateValue = resolvedRate
            }
            coordinator.setPlaybackRate(resolvedRate)
        }
        .onChange(of: selectedSegmentID) { _, _ in
            applyPendingBookmarkIfPossible()
        }
        .onChange(of: bookmarkIdentityKey) { _, _ in
            refreshBookmarks()
        }
        .onReceive(NotificationCenter.default.publisher(for: PlaybackBookmarkStore.didChangeNotification)) { notification in
            guard let jobId = resolvedBookmarkJobId else { return }
            let userId = resolvedBookmarkUserId
            if let changedUser = notification.userInfo?["userId"] as? String, changedUser != userId {
                return
            }
            bookmarks = PlaybackBookmarkStore.shared.bookmarks(for: jobId, userId: userId)
        }
        .onChange(of: subtitleTracks) { _, _ in
            selectDefaultTrackIfNeeded()
            loadSubtitles()
        }
        .onChange(of: selectedTrack?.id) { _, _ in
            loadSubtitles()
        }
        .onChange(of: subtitleVisibility) { _, _ in
            if !coordinator.isPlaying {
                syncSubtitleSelectionIfNeeded(force: true)
            }
        }
        .onChange(of: showSubtitleSettings) { _, isVisible in
            #if os(tvOS)
            if isVisible {
                showTVControls = true
                controlsHideTask?.cancel()
            } else {
                scheduleControlsAutoHide()
            }
            #endif
        }
        .onChange(of: isScrubbing) { _, scrubbing in
            #if os(tvOS)
            if scrubbing {
                showTVControls = true
                controlsHideTask?.cancel()
            } else {
                scheduleControlsAutoHide()
            }
            #endif
        }
        .onReceive(coordinator.$currentTime) { _ in
            guard !isTearingDown else { return }
            updateNowPlayingPlayback()
            if !isScrubbing {
                scrubberValue = coordinator.currentTime
            }
            if !coordinator.isPlaying {
                syncSubtitleSelectionIfNeeded()
            }
            reportPlaybackProgress(time: coordinator.currentTime, isPlaying: coordinator.isPlaying)
        }
        .onReceive(coordinator.$isPlaying) { isPlaying in
            guard !isTearingDown else { return }
            updateNowPlayingPlayback()
            #if os(tvOS)
            if isPlaying {
                if forceHideControlsOnPlay {
                    forceHideControlsOnPlay = false
                    controlsHideTask?.cancel()
                    withAnimation(.easeInOut(duration: 0.2)) {
                        showTVControls = false
                    }
                } else {
                    scheduleControlsAutoHide()
                }
            } else {
                controlsHideTask?.cancel()
                showTVControls = true
            }
            #endif
            if isPlaying {
                isManualSubtitleNavigation = false
                subtitleActiveCueID = nil
                subtitleSelection = nil
                subtitleSelectionRange = nil
                closeSubtitleBubble()
            } else {
                syncSubtitleSelectionIfNeeded(force: true)
            }
            reportPlaybackProgress(time: coordinator.currentTime, isPlaying: isPlaying)
        }
        .onReceive(coordinator.$duration) { _ in
            guard !isTearingDown else { return }
            updateNowPlayingPlayback()
            if coordinator.duration.isFinite, coordinator.duration > 0 {
                scrubberValue = min(scrubberValue, coordinator.duration)
            } else {
                scrubberValue = 0
            }
            applyPendingResumeIfPossible()
            applyPendingBookmarkIfPossible()
        }
        .onDisappear {
            subtitleTask?.cancel()
            subtitleTask = nil
            showSubtitleSettings = false
            controlsHideTask?.cancel()
            controlsHideTask = nil
            isTearingDown = true
            reportPlaybackProgress(time: resolvedPlaybackTime(), isPlaying: false, force: true)
            coordinator.reset()
            nowPlaying.clear()
        }
    }
}
