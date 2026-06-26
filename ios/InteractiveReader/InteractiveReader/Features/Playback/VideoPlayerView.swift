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
    @State var showTVControls = false
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
    @State var linguistVM = MyLinguistBubbleViewModel()
    @State var subtitleInteractionFrame: CGRect = .null
    @AppStorage("video.player.verticalOffset") var videoVerticalOffsetValue: Double = 0
    @State var videoDragTranslation: CGFloat = 0
    @State var isVideoDragGestureActive = false
    @AppStorage(MyLinguistPreferences.lookupLanguageKey) var storedLookupLanguage: String = ""
    @AppStorage(MyLinguistPreferences.llmModelKey) var storedLlmModel: String =
        MyLinguistPreferences.defaultLlmModel
    @State var subtitleActiveCueID: UUID?
    @State var isManualSubtitleNavigation = false
    @State var pendingResumeTime: Double?
    @State var pendingBookmarkSeek: PendingVideoBookmarkSeek?
    @State var isTearingDown = false
    @State var bookmarks: [PlaybackBookmarkEntry] = []
    @StateObject var searchViewModel = MediaSearchViewModel()
    @StateObject var sleepTimer = SleepTimerController()
    @State var lastKeyboardShortcutDispatch: (identifier: String, timestamp: TimeInterval)?
    #if os(tvOS)
    @Namespace var searchFocusNamespace
    #endif
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
    let subtitleAutoLookupDelayNanos: UInt64 = 250_000_000

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

    // MARK: - ViewModel Bridge Properties

    /// Bridge to ViewModel's bubble state, converting to VideoLinguistBubbleState for backward compat.
    var subtitleBubble: VideoLinguistBubbleState? {
        get {
            guard let b = linguistVM.bubble else { return nil }
            var state = VideoLinguistBubbleState(query: b.query, status: b.status, answer: b.answer, model: b.model)
            state.lookupSource = b.lookupSource
            state.cachedAudioRef = b.cachedAudioRef
            state.pronunciationLanguage = b.pronunciationLanguage
            state.pronunciationVoice = b.pronunciationVoice
            return state
        }
        nonmutating set {
            if let v = newValue {
                var bubble = MyLinguistBubbleState(query: v.query, status: v.status, answer: v.answer, model: v.model)
                bubble.lookupSource = v.lookupSource
                bubble.cachedAudioRef = v.cachedAudioRef
                bubble.pronunciationLanguage = v.pronunciationLanguage
                bubble.pronunciationVoice = v.pronunciationVoice
                linguistVM.bubble = bubble
            } else {
                linguistVM.bubble = nil
            }
        }
    }

    var subtitleLookupTask: Task<Void, Never>? {
        linguistVM.lookupTask
    }

    var subtitleSpeechTask: Task<Void, Never>? {
        linguistVM.speechTask
    }

    var subtitleAutoLookupTask: Task<Void, Never>? {
        get { linguistVM.autoLookupTask }
        nonmutating set { linguistVM.autoLookupTask = newValue }
    }

    var availableLlmModels: [String] {
        get { linguistVM.availableLlmModels }
        nonmutating set { linguistVM.availableLlmModels = newValue }
    }

    var didLoadLlmModels: Bool {
        get { linguistVM.didLoadLlmModels }
        nonmutating set { linguistVM.didLoadLlmModels = newValue }
    }

    var pronunciationSpeaker: PronunciationSpeaker {
        linguistVM.pronunciationSpeaker
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
            #if os(iOS)
            if isPad {
                videoSwiftUIKeyboardShortcutLayer
            }
            #endif
        }
        .accessibilityIdentifier("videoPlayerView")
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
        .onAppear(perform: handleVideoAppear)
        .onDisappear(perform: clearPlaybackEndedHandler)
        .onChange(of: videoURL) { _, newURL in handleVideoURLChange(newURL) }
        .onChange(of: resumeActionID) { _, _ in handleResumeActionChange() }
        .onChange(of: metadataUpdateKey) { _, _ in handleMetadataChange() }
        .onChange(of: resumeTime) { _, newValue in handleResumeTimeChange(newValue) }
        .onChange(of: playbackRateValue) { _, newValue in handlePlaybackRateChange(newValue) }
        .onChange(of: selectedSegmentID) { _, _ in handleSelectedSegmentChange() }
        .onChange(of: bookmarkIdentityKey) { _, _ in handleBookmarkIdentityChange() }
        .onReceive(NotificationCenter.default.publisher(for: PlaybackBookmarkStore.didChangeNotification)) { notification in
            handleBookmarkStoreChange(notification)
        }
        #if os(iOS)
        .onReceive(NotificationCenter.default.publisher(for: .keyboardShortcutPlayPause)) { _ in
            guard isPad else { return }
            handleVideoKeyboardPlayPause()
        }
        .onReceive(NotificationCenter.default.publisher(for: .keyboardShortcutPrevious)) { _ in
            guard isPad else { return }
            handleVideoKeyboardPrevious()
        }
        .onReceive(NotificationCenter.default.publisher(for: .keyboardShortcutNext)) { _ in
            guard isPad else { return }
            handleVideoKeyboardNext()
        }
        .onReceive(NotificationCenter.default.publisher(for: .keyboardShortcutPreviousSentence)) { _ in
            guard isPad else { return }
            handleVideoKeyboardPrevious()
        }
        .onReceive(NotificationCenter.default.publisher(for: .keyboardShortcutNextSentence)) { _ in
            guard isPad else { return }
            handleVideoKeyboardNext()
        }
        .onReceive(NotificationCenter.default.publisher(for: .keyboardShortcutLookup)) { _ in
            guard isPad else { return }
            handleVideoKeyboardLookup()
        }
        .onReceive(NotificationCenter.default.publisher(for: .keyboardShortcutShowMenu)) { _ in
            guard isPad else { return }
            handleVideoKeyboardLineDown()
        }
        .onReceive(NotificationCenter.default.publisher(for: .keyboardShortcutHideMenu)) { _ in
            guard isPad else { return }
            handleVideoKeyboardLineUp()
        }
        #endif
        .onChange(of: subtitleTracks) { _, _ in handleSubtitleTracksChange() }
        .onChange(of: selectedTrack?.id) { _, _ in handleSelectedTrackChange() }
        .onChange(of: subtitleVisibility) { _, _ in handleSubtitleVisibilityChange() }
        .onChange(of: showSubtitleSettings) { _, isVisible in handleSubtitleSettingsVisibilityChange(isVisible) }
        .onChange(of: isScrubbing) { _, scrubbing in handleScrubbingChange(scrubbing) }
        .onReceive(coordinator.$currentTime) { _ in handleCurrentTimeChange() }
        .onReceive(coordinator.$isPlaying) { isPlaying in handlePlayingChange(isPlaying) }
        .onReceive(coordinator.$duration) { _ in handleDurationChange() }
        .onDisappear(perform: handleVideoDisappear)
    }
}
