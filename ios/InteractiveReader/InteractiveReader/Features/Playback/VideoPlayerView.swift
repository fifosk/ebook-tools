import AVKit
import AVFoundation
import SwiftUI
import Foundation
#if canImport(UIKit)
import UIKit
#endif

#if canImport(MediaPlayer)
import MediaPlayer
#endif

struct VideoPlaybackMetadata {
    let title: String
    let subtitle: String?
    let artist: String?
    let album: String?
    let artworkURL: URL?
    let secondaryArtworkURL: URL?
    let languageFlags: [LanguageFlagEntry]
    let channelVariant: PlayerChannelVariant
    let channelLabel: String
}

struct VideoSegmentOption: Identifiable, Hashable {
    let id: String
    let label: String
}

struct VideoPlayerView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) private var dismiss

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

    @StateObject private var coordinator = VideoPlayerCoordinator()
    @State private var cues: [VideoSubtitleCue] = []
    @State private var subtitleError: String?
    @State private var selectedTrack: VideoSubtitleTrack?
    @State private var subtitleCache: [String: [VideoSubtitleCue]] = [:]
    @State private var subtitleTask: Task<Void, Never>?
    @State private var subtitleLoadToken = UUID()
    @State private var subtitleVisibility = SubtitleVisibility()
    @State private var showSubtitleSettings = false
    @State private var showTVControls = true
    @State private var isHeaderCollapsed = false
    @State private var scrubberValue: Double = 0
    @State private var isScrubbing = false
    @State private var controlsHideTask: Task<Void, Never>?
    @AppStorage("video.subtitle.fontScale") private var subtitleFontScaleValue: Double =
        Double(VideoPlayerView.defaultSubtitleFontScale)
    @AppStorage("video.subtitle.bubbleFontScale") private var subtitleLinguistFontScaleValue: Double = 1.0
    @State private var isShortcutHelpPinned = false
    @State private var isShortcutHelpModifierActive = false
    @State private var subtitleSelection: VideoSubtitleWordSelection?
    @State private var subtitleBubble: VideoLinguistBubbleState?
    @State private var subtitleLookupTask: Task<Void, Never>?
    @State private var subtitleSpeechTask: Task<Void, Never>?
    @State private var subtitleActiveCueID: UUID?
    @State private var isManualSubtitleNavigation = false
    @State private var pendingResumeTime: Double?
    @StateObject private var pronunciationSpeaker = VideoPronunciationSpeaker()
    @State private var isTearingDown = false
    #if os(iOS)
    @State private var isVideoScrubGestureActive = false
    @State private var videoScrubStartTime: Double = 0
    @State private var videoViewportSize: CGSize = .zero
    #endif

    private let subtitleFontScaleStep: CGFloat = 0.1
    private let subtitleFontScaleMin: CGFloat = 0.7
    private let subtitleFontScaleMax: CGFloat = 2.0
    private let subtitleLinguistFontScaleMin: CGFloat = 0.8
    private let subtitleLinguistFontScaleMax: CGFloat = 1.6
    private let subtitleLinguistFontScaleStep: CGFloat = 0.05

    private static var defaultSubtitleFontScale: CGFloat {
        #if os(tvOS)
        return 0.8
        #else
        return 1.0
        #endif
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
        onPlaybackEnded: ((Double) -> Void)? = nil
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
    }

    var body: some View {
        ZStack {
            if let player = coordinator.playerInstance() {
                VideoPlayerControllerView(
                    player: player,
                    onShowControls: handleUserInteraction
                )
                #if os(iOS)
                .background(videoViewportReader)
                .simultaneousGesture(videoTapGesture, including: .gesture)
                .simultaneousGesture(videoScrubGesture, including: .gesture)
                #endif
                #if os(tvOS)
                .focusable(false)
                .allowsHitTesting(false)
                #endif
                VideoPlayerOverlayView(
                    cues: cues,
                    currentTime: coordinator.currentTime,
                    duration: coordinator.duration,
                    subtitleError: subtitleError,
                    tracks: orderedTracks,
                    selectedTrack: $selectedTrack,
                    subtitleVisibility: $subtitleVisibility,
                    showSubtitleSettings: $showSubtitleSettings,
                    showTVControls: $showTVControls,
                    scrubberValue: $scrubberValue,
                    isScrubbing: $isScrubbing,
                    metadata: metadata,
                    segmentOptions: segmentOptions,
                    selectedSegmentID: selectedSegmentID,
                    jobProgressLabel: jobProgressLabel,
                    jobRemainingLabel: jobRemainingLabel,
                    subtitleFontScale: subtitleFontScale,
                    isPlaying: coordinator.isPlaying,
                    subtitleSelection: subtitleSelection,
                    subtitleBubble: subtitleBubble,
                    subtitleLinguistFontScale: subtitleLinguistFontScale,
                    canIncreaseSubtitleLinguistFont: canIncreaseSubtitleLinguistFont,
                    canDecreaseSubtitleLinguistFont: canDecreaseSubtitleLinguistFont,
                    isHeaderCollapsed: isHeaderCollapsed,
                    onToggleHeaderCollapsed: toggleHeaderCollapsed,
                    onResetSubtitleFont: {
                        resetSubtitleFontScale()
                    },
                    onSetSubtitleFont: { value in
                        setSubtitleFontScale(value)
                    },
                    onResetSubtitleBubbleFont: {
                        resetSubtitleLinguistFontScale()
                    },
                    onSetSubtitleBubbleFont: { value in
                        setSubtitleLinguistFontScale(value)
                    },
                    onPlayPause: {
                        handleUserInteraction()
                        coordinator.togglePlayback()
                    },
                    onSkipForward: {
                        handleUserInteraction()
                        coordinator.skip(by: 15)
                    },
                    onSkipBackward: {
                        handleUserInteraction()
                        coordinator.skip(by: -15)
                    },
                    onSeek: { time in
                        handleUserInteraction()
                        coordinator.seek(to: time)
                    },
                    onSkipSentence: { delta in
                        handleSentenceSkip(delta)
                    },
                    onNavigateSubtitleWord: { delta in
                        handleSubtitleWordNavigation(delta)
                    },
                    onNavigateSubtitleTrack: { delta in
                        handleSubtitleTrackNavigation(delta)
                    },
                    onSubtitleLookup: {
                        handleSubtitleLookup()
                    },
                    onSubtitleTokenLookup: { token in
                        handleSubtitleTokenLookup(token)
                    },
                    onSubtitleTokenSeek: { token in
                        handleSubtitleTokenSeek(token)
                    },
                    onIncreaseSubtitleLinguistFont: {
                        adjustSubtitleLinguistFontScale(by: subtitleLinguistFontScaleStep)
                    },
                    onDecreaseSubtitleLinguistFont: {
                        adjustSubtitleLinguistFontScale(by: -subtitleLinguistFontScaleStep)
                    },
                    onSelectSegment: { id in
                        showSubtitleSettings = false
                        onSelectSegment?(id)
                    },
                    onCloseSubtitleBubble: {
                        closeSubtitleBubble()
                    },
                    onUserInteraction: handleUserInteraction
                )
                #if os(iOS)
                if isPad {
                    VideoKeyboardCommandHandler(
                        onPlayPause: { coordinator.togglePlayback() },
                        onSkipBackward: {
                            if coordinator.isPlaying {
                                handleSentenceSkip(-1)
                            } else {
                                handleSubtitleWordNavigation(-1)
                            }
                        },
                        onSkipForward: {
                            if coordinator.isPlaying {
                                handleSentenceSkip(1)
                            } else {
                                handleSubtitleWordNavigation(1)
                            }
                        },
                        onNavigateLineUp: { _ = handleSubtitleTrackNavigation(-1) },
                        onNavigateLineDown: { _ = handleSubtitleTrackNavigation(1) },
                        onIncreaseFont: { adjustSubtitleFontScale(by: subtitleFontScaleStep) },
                        onDecreaseFont: { adjustSubtitleFontScale(by: -subtitleFontScaleStep) },
                        onToggleOriginal: { toggleSubtitleVisibility(.original) },
                        onToggleTransliteration: { toggleSubtitleVisibility(.transliteration) },
                        onToggleTranslation: { toggleSubtitleVisibility(.translation) },
                        onToggleShortcutHelp: { toggleShortcutHelp() },
                        onOptionKeyDown: { showShortcutHelpModifier() },
                        onOptionKeyUp: { hideShortcutHelpModifier() }
                    )
                    .frame(width: 0, height: 0)
                    .accessibilityHidden(true)
                }
                if isPad, isShortcutHelpVisible {
                    VideoShortcutHelpOverlayView(onDismiss: { dismissShortcutHelp() })
                        .transition(.opacity)
                        .zIndex(4)
                }
                #endif
            } else {
                ProgressView("Preparing video…")
            }
        }
        #if os(tvOS)
        .onExitCommand {
            handleExitCommand()
        }
        #endif
        .onAppear {
            isTearingDown = false
            coordinator.onPlaybackEnded = { [weak coordinator] in
                guard let coordinator else { return }
                let duration = coordinator.duration.isFinite && coordinator.duration > 0
                    ? coordinator.duration
                : coordinator.currentTime
                onPlaybackEnded?(duration)
            }
            pendingResumeTime = resumeTime
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
        }
        .onDisappear {
            coordinator.onPlaybackEnded = nil
        }
        .onChange(of: videoURL) { _, newURL in
            isTearingDown = false
            subtitleSelection = nil
            subtitleCache.removeAll()
            pendingResumeTime = resumeTime
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
        }
        .onChange(of: resumeActionID) { _, _ in
            pendingResumeTime = resumeTime ?? 0
            applyPendingResumeIfPossible()
        }
        .onChange(of: resumeTime) { _, newValue in
            if newValue != nil {
                pendingResumeTime = newValue
                applyPendingResumeIfPossible()
            }
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
                scheduleControlsAutoHide()
            } else {
                controlsHideTask?.cancel()
                showTVControls = true
            }
            #endif
            if isPlaying {
                isManualSubtitleNavigation = false
                subtitleActiveCueID = nil
                subtitleSelection = nil
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

    private var orderedTracks: [VideoSubtitleTrack] {
        subtitleTracks.sorted { lhs, rhs in
            if lhs.format.priority == rhs.format.priority {
                return lhs.label.localizedCaseInsensitiveCompare(rhs.label) == .orderedAscending
            }
            return lhs.format.priority < rhs.format.priority
        }
    }

    private func selectDefaultTrackIfNeeded() {
        guard let current = selectedTrack else {
            selectedTrack = orderedTracks.first
            return
        }
        if let replacement = orderedTracks.first(where: { $0.id == current.id }) {
            if replacement.url != current.url {
                selectedTrack = replacement
                loadSubtitles()
            }
            return
        }
        if let labelMatch = orderedTracks.first(where: {
            $0.format == current.format && $0.label.localizedCaseInsensitiveCompare(current.label) == .orderedSame
        }) {
            selectedTrack = labelMatch
            return
        }
        selectedTrack = orderedTracks.first
    }

    private func loadSubtitles() {
        subtitleTask?.cancel()
        subtitleError = nil
        subtitleSelection = nil
        subtitleActiveCueID = nil
        isManualSubtitleNavigation = false
        closeSubtitleBubble()
        guard let track = selectedTrack else {
            cues = []
            subtitleError = nil
            return
        }
        if let cached = subtitleCache[track.id] {
            cues = cached
            subtitleError = nil
            return
        }
        cues = []
        let loadToken = UUID()
        subtitleLoadToken = loadToken
        subtitleTask = Task {
            do {
                var request = URLRequest(url: track.url)
                request.cachePolicy = .reloadIgnoringLocalCacheData
                let (data, _) = try await URLSession.shared.data(for: request)
                let content = String(data: data, encoding: .utf8) ?? ""
                let parsed = SubtitleParser.parse(from: content, format: track.format)
                await MainActor.run {
                    guard subtitleLoadToken == loadToken else { return }
                    subtitleCache[track.id] = parsed
                    cues = parsed
                    subtitleError = nil
                    if !coordinator.isPlaying {
                        syncSubtitleSelectionIfNeeded(force: true)
                    }
                }
            } catch {
                await MainActor.run {
                    guard subtitleLoadToken == loadToken else { return }
                    subtitleError = "Unable to load subtitles"
                }
            }
        }
    }

    private func configureNowPlaying() {
        nowPlaying.configureRemoteCommands(
            onPlay: { coordinator.play() },
            onPause: { coordinator.pause() },
            onNext: nil,
            onPrevious: nil,
            onSeek: { coordinator.seek(to: $0) },
            onToggle: { coordinator.togglePlayback() },
            onSkipForward: { coordinator.skip(by: 15) },
            onSkipBackward: { coordinator.skip(by: -15) },
            skipIntervalSeconds: 15
        )
    }

    private func updateNowPlayingMetadata() {
        nowPlaying.updateMetadata(
            title: metadata.title,
            artist: metadata.artist,
            album: metadata.album,
            artworkURL: metadata.artworkURL,
            mediaType: .video
        )
    }

    private func updateNowPlayingPlayback() {
        nowPlaying.updatePlaybackState(
            isPlaying: coordinator.isPlaying,
            position: coordinator.currentTime,
            duration: coordinator.duration
        )
    }

    private func applyPendingResumeIfPossible() {
        guard let pendingResumeTime else { return }
        guard let player = coordinator.playerInstance() else { return }
        let isReady = player.currentItem?.status == .readyToPlay
        guard isReady || coordinator.duration > 0 else { return }
        let clamped = max(0, pendingResumeTime)
        coordinator.seek(to: clamped)
        if autoPlay {
            coordinator.play()
        }
        self.pendingResumeTime = nil
    }

    private func handleUserInteraction() {
        #if os(tvOS)
        showTVControls = true
        scheduleControlsAutoHide()
        #endif
    }

    private func toggleHeaderCollapsed() {
        #if os(iOS)
        withAnimation(.easeInOut(duration: 0.2)) {
            isHeaderCollapsed.toggle()
        }
        #endif
    }

    #if os(tvOS)
    private func handleExitCommand() {
        if subtitleBubble != nil {
            closeSubtitleBubble()
            return
        }
        if showSubtitleSettings {
            showSubtitleSettings = false
            return
        }
        if !coordinator.isPlaying {
            if !showTVControls {
                reportPlaybackProgress(time: resolvedPlaybackTime(), isPlaying: coordinator.isPlaying)
                dismiss()
                return
            }
            coordinator.play()
            withAnimation(.easeInOut(duration: 0.2)) {
                showTVControls = false
            }
            return
        }
        reportPlaybackProgress(time: resolvedPlaybackTime(), isPlaying: coordinator.isPlaying)
        dismiss()
    }
    #endif

    private func reportPlaybackProgress(time: Double, isPlaying: Bool, force: Bool = false) {
        guard let onPlaybackProgress else { return }
        if isTearingDown && !force { return }
        if Thread.isMainThread {
            onPlaybackProgress(time, isPlaying)
        } else {
            DispatchQueue.main.async {
                onPlaybackProgress(time, isPlaying)
            }
        }
    }

    private func resolvedPlaybackTime() -> Double {
        if let player = coordinator.playerInstance() {
            let seconds = player.currentTime().seconds
            if seconds.isFinite {
                return max(0, seconds)
            }
        }
        return coordinator.currentTime
    }

    private func scheduleControlsAutoHide() {
        #if os(tvOS)
        controlsHideTask?.cancel()
        guard shouldAutoHideControls else { return }
        controlsHideTask = Task {
            try? await Task.sleep(nanoseconds: 8_000_000_000)
            await MainActor.run {
                if shouldAutoHideControls {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        showTVControls = false
                    }
                }
            }
        }
        #endif
    }

    #if os(iOS)
    private var videoTapGesture: some Gesture {
        TapGesture()
            .onEnded {
                coordinator.togglePlayback()
            }
    }

    private var videoScrubGesture: some Gesture {
        DragGesture(minimumDistance: 12, coordinateSpace: .local)
            .onChanged { value in
                guard !showSubtitleSettings else { return }
                guard abs(value.translation.width) >= abs(value.translation.height) else { return }
                beginVideoScrubGestureIfNeeded()
                let duration = coordinator.duration
                guard duration > 0 else { return }
                let width = max(videoScrubWidth, 1)
                let delta = Double(value.translation.width / width) * duration
                let target = min(max(videoScrubStartTime + delta, 0), duration)
                scrubberValue = target
                coordinator.seek(to: target)
            }
            .onEnded { _ in
                endVideoScrubGesture()
            }
    }

    private var videoViewportReader: some View {
        GeometryReader { proxy in
            Color.clear
                .onAppear {
                    videoViewportSize = proxy.size
                }
                .onChange(of: proxy.size) { _, newValue in
                    videoViewportSize = newValue
                }
        }
        .allowsHitTesting(false)
    }

    private var videoScrubWidth: CGFloat {
        if videoViewportSize.width > 0 {
            return videoViewportSize.width
        }
        return UIScreen.main.bounds.width
    }

    private func beginVideoScrubGestureIfNeeded() {
        guard !isVideoScrubGestureActive else { return }
        isVideoScrubGestureActive = true
        isScrubbing = true
        videoScrubStartTime = coordinator.currentTime
        scrubberValue = coordinator.currentTime
    }

    private func endVideoScrubGesture() {
        guard isVideoScrubGestureActive else { return }
        isVideoScrubGestureActive = false
        isScrubbing = false
        coordinator.seek(to: scrubberValue)
    }
    #endif

    private var shouldAutoHideControls: Bool {
        guard let player = coordinator.playerInstance() else { return false }
        let isActive = player.timeControlStatus == .playing || player.rate > 0
        return isActive && !showSubtitleSettings && !isScrubbing
    }

    private var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    private var isShortcutHelpVisible: Bool {
        isShortcutHelpPinned || isShortcutHelpModifierActive
    }

    private func adjustSubtitleFontScale(by delta: CGFloat) {
        setSubtitleFontScale(subtitleFontScale + delta)
    }

    private var canIncreaseSubtitleLinguistFont: Bool {
        subtitleLinguistFontScale + subtitleLinguistFontScaleStep <= subtitleLinguistFontScaleMax
    }

    private var canDecreaseSubtitleLinguistFont: Bool {
        subtitleLinguistFontScale - subtitleLinguistFontScaleStep >= subtitleLinguistFontScaleMin
    }

    private func adjustSubtitleLinguistFontScale(by delta: CGFloat) {
        setSubtitleLinguistFontScale(subtitleLinguistFontScale + delta)
    }

    private func setSubtitleFontScale(_ value: CGFloat) {
        let updated = min(max(value, subtitleFontScaleMin), subtitleFontScaleMax)
        if updated != subtitleFontScale {
            subtitleFontScale = updated
        }
    }

    private func resetSubtitleFontScale() {
        setSubtitleFontScale(VideoPlayerView.defaultSubtitleFontScale)
    }

    private func setSubtitleLinguistFontScale(_ value: CGFloat) {
        let updated = min(max(value, subtitleLinguistFontScaleMin), subtitleLinguistFontScaleMax)
        if updated != subtitleLinguistFontScale {
            subtitleLinguistFontScale = updated
        }
    }

    private func resetSubtitleLinguistFontScale() {
        setSubtitleLinguistFontScale(1.0)
    }

    private func currentSubtitleDisplay() -> VideoSubtitleDisplay? {
        VideoSubtitleDisplayBuilder.build(cues: cues, time: coordinator.currentTime, visibility: subtitleVisibility)
    }

    private func syncSubtitleSelectionIfNeeded(force: Bool = false) {
        guard !coordinator.isPlaying else { return }
        guard let display = currentSubtitleDisplay() else {
            subtitleSelection = nil
            subtitleActiveCueID = nil
            return
        }
        if isManualSubtitleNavigation && !force {
            if subtitleActiveCueID == display.cue.id {
                return
            }
            isManualSubtitleNavigation = false
        }
        if force || subtitleActiveCueID != display.cue.id {
            subtitleActiveCueID = display.cue.id
            subtitleSelection = defaultSubtitleSelection(in: display)
            return
        }
        if let normalized = normalizedSelection(from: subtitleSelection, in: display),
           normalized != subtitleSelection {
            subtitleSelection = normalized
            return
        }
        if subtitleSelection == nil {
            subtitleSelection = defaultSubtitleSelection(in: display)
        }
    }

    private func normalizedSelection(
        from selection: VideoSubtitleWordSelection?,
        in display: VideoSubtitleDisplay
    ) -> VideoSubtitleWordSelection? {
        guard let selection else { return nil }
        let line = lineForSelection(selection, in: display)
        guard let line, !line.tokens.isEmpty else { return nil }
        let tokenIndex = min(max(selection.tokenIndex, 0), line.tokens.count - 1)
        return VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: tokenIndex
        )
    }

    private func defaultSubtitleSelection(in display: VideoSubtitleDisplay) -> VideoSubtitleWordSelection? {
        guard let line = display.lines.first, !line.tokens.isEmpty else { return nil }
        let tokenIndex = currentTokenIndex(
            for: line,
            cueStart: display.highlightStart,
            cueEnd: display.highlightEnd,
            time: coordinator.currentTime
        )
        let resolved = nearestLookupTokenIndex(in: line.tokens, startingAt: tokenIndex) ?? tokenIndex
        return VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: resolved
        )
    }

    private func currentTokenIndex(
        for line: VideoSubtitleDisplayLine,
        cueStart: Double,
        cueEnd: Double,
        time: Double
    ) -> Int {
        guard !line.tokens.isEmpty else { return 0 }
        let clamped = min(max(time, cueStart), cueEnd)
        let epsilon = 1e-3
        if clamped >= cueEnd - epsilon {
            return line.tokens.count - 1
        }
        let revealed = line.revealTimes.filter { $0 <= clamped + epsilon }.count
        if revealed > 0 {
            return min(revealed - 1, line.tokens.count - 1)
        }
        if clamped >= cueStart - epsilon {
            return 0
        }
        return 0
    }

    private func lineForSelection(
        _ selection: VideoSubtitleWordSelection,
        in display: VideoSubtitleDisplay
    ) -> VideoSubtitleDisplayLine? {
        if display.lines.indices.contains(selection.lineIndex) {
            let line = display.lines[selection.lineIndex]
            if line.kind == selection.lineKind {
                return line
            }
        }
        if let line = display.lines.first(where: { $0.kind == selection.lineKind }) {
            return line
        }
        if display.lines.indices.contains(selection.lineIndex) {
            return display.lines[selection.lineIndex]
        }
        return nil
    }

    private func handleSubtitleWordNavigation(_ delta: Int) {
        guard !coordinator.isPlaying else { return }
        guard let display = currentSubtitleDisplay() else { return }
        let selection = normalizedSelection(from: subtitleSelection, in: display)
            ?? defaultSubtitleSelection(in: display)
        guard let selection, let line = lineForSelection(selection, in: display) else { return }
        let direction = delta >= 0 ? 1 : -1
        let startIndex = selection.tokenIndex + direction
        guard let nextIndex = nextLookupTokenIndex(
            in: line.tokens,
            startingAt: startIndex,
            direction: direction
        ) else { return }
        isManualSubtitleNavigation = true
        subtitleSelection = VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: nextIndex
        )
    }

    private func handleSubtitleTrackNavigation(_ delta: Int) -> Bool {
        guard !coordinator.isPlaying else { return false }
        guard let display = currentSubtitleDisplay() else { return false }
        guard !display.lines.isEmpty else { return false }
        let selection = normalizedSelection(from: subtitleSelection, in: display)
            ?? defaultSubtitleSelection(in: display)
        let currentIndex = selection?.lineIndex ?? 0
        let nextIndex = max(0, min(currentIndex + delta, display.lines.count - 1))
        guard display.lines.indices.contains(nextIndex) else { return false }
        let moved = selection?.lineIndex != nextIndex
        let line = display.lines[nextIndex]
        let tokenIndex = currentTokenIndex(
            for: line,
            cueStart: display.highlightStart,
            cueEnd: display.highlightEnd,
            time: coordinator.currentTime
        )
        let resolvedIndex = nearestLookupTokenIndex(in: line.tokens, startingAt: tokenIndex) ?? tokenIndex
        isManualSubtitleNavigation = true
        subtitleSelection = VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: resolvedIndex
        )
        return moved
    }

    private func handleSentenceSkip(_ delta: Int) {
        let groups = subtitleSentenceGroups()
        if groups.isEmpty {
            coordinator.skip(by: delta < 0 ? -15 : 15)
            return
        }
        let time = coordinator.currentTime
        let epsilon = 1e-3
        let currentIndex = groups.firstIndex { time >= $0.start - epsilon && time <= $0.end + epsilon }
            ?? groups.lastIndex { time >= $0.start - epsilon }
            ?? 0
        let nextIndex = max(0, min(currentIndex + (delta < 0 ? -1 : 1), groups.count - 1))
        coordinator.seek(to: groups[nextIndex].start)
    }

    private func subtitleSentenceGroups() -> [SubtitleSentenceGroup] {
        guard !cues.isEmpty else { return [] }
        let sorted = cues.sorted { lhs, rhs in
            if lhs.start == rhs.start {
                return lhs.end < rhs.end
            }
            return lhs.start < rhs.start
        }
        var groups: [SubtitleSentenceGroup] = []
        let maxGap = 0.06
        for cue in sorted {
            guard !cue.text.isEmpty else { continue }
            if let last = groups.last {
                let gap = cue.start - last.end
                if cue.text == last.text && gap <= maxGap {
                    groups[groups.count - 1] = SubtitleSentenceGroup(
                        start: last.start,
                        end: max(last.end, cue.end),
                        text: last.text
                    )
                    continue
                }
            }
            groups.append(SubtitleSentenceGroup(start: cue.start, end: cue.end, text: cue.text))
        }
        return groups
    }

    private func handleSubtitleLookup() {
        if coordinator.isPlaying {
            coordinator.pause()
        }
        guard let display = currentSubtitleDisplay() else { return }
        let selection = normalizedSelection(from: subtitleSelection, in: display)
            ?? defaultSubtitleSelection(in: display)
        guard let selection, let line = lineForSelection(selection, in: display) else { return }
        guard line.tokens.indices.contains(selection.tokenIndex) else { return }
        let rawToken = line.tokens[selection.tokenIndex]
        guard let query = sanitizeLookupQuery(rawToken) else { return }
        isManualSubtitleNavigation = true
        subtitleSelection = selection
        startSubtitleLookup(query: query, lineKind: line.kind)
    }

    private struct SubtitleSentenceGroup {
        let start: Double
        let end: Double
        let text: String
    }

    private func handleSubtitleTokenLookup(_ token: VideoSubtitleTokenReference) {
        if coordinator.isPlaying {
            coordinator.pause()
        }
        isManualSubtitleNavigation = true
        subtitleSelection = VideoSubtitleWordSelection(
            lineKind: token.lineKind,
            lineIndex: token.lineIndex,
            tokenIndex: token.tokenIndex
        )
        guard let query = sanitizeLookupQuery(token.token) else { return }
        startSubtitleLookup(query: query, lineKind: token.lineKind)
    }

    private func handleSubtitleTokenSeek(_ token: VideoSubtitleTokenReference) {
        isManualSubtitleNavigation = true
        subtitleSelection = VideoSubtitleWordSelection(
            lineKind: token.lineKind,
            lineIndex: token.lineIndex,
            tokenIndex: token.tokenIndex
        )
        if let seekTime = token.seekTime, seekTime.isFinite {
            coordinator.seek(to: seekTime)
            return
        }
        guard let display = currentSubtitleDisplay() else { return }
        guard display.cue.start.isFinite else { return }
        coordinator.seek(to: display.cue.start)
    }

    private func startSubtitleLookup(query: String, lineKind: VideoSubtitleLineKind) {
        subtitleLookupTask?.cancel()
        subtitleBubble = VideoLinguistBubbleState(query: query, status: .loading, answer: nil, model: nil)
        let originalLanguage = linguistInputLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let translationLanguage = linguistLookupLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let explanationLanguage = linguistExplanationLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let inputLanguage = lookupInputLanguage(
            for: lineKind,
            originalLanguage: originalLanguage,
            translationLanguage: translationLanguage
        )
        let pronunciationLanguage = inputLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let resolvedPronunciationLanguage = pronunciationLanguage.isEmpty ? nil : pronunciationLanguage
        let fallbackLanguage = resolveSpeechLanguage(resolvedPronunciationLanguage ?? "")
        startSubtitlePronunciation(
            text: query,
            apiLanguage: resolvedPronunciationLanguage,
            fallbackLanguage: fallbackLanguage
        )
        subtitleLookupTask = Task { @MainActor in
            guard let configuration = appState.configuration else {
                subtitleBubble = VideoLinguistBubbleState(
                    query: query,
                    status: .error("Lookup is not configured."),
                    answer: nil,
                    model: nil
                )
                return
            }
            do {
                let client = APIClient(configuration: configuration)
                let response = try await client.assistantLookup(
                    query: query,
                    inputLanguage: inputLanguage,
                    lookupLanguage: explanationLanguage.isEmpty ? "English" : explanationLanguage
                )
                subtitleBubble = VideoLinguistBubbleState(
                    query: query,
                    status: .ready,
                    answer: response.answer,
                    model: response.model
                )
            } catch {
                guard !Task.isCancelled else { return }
                subtitleBubble = VideoLinguistBubbleState(
                    query: query,
                    status: .error(error.localizedDescription),
                    answer: nil,
                    model: nil
                )
            }
        }
    }

    private func closeSubtitleBubble() {
        subtitleLookupTask?.cancel()
        subtitleLookupTask = nil
        subtitleSpeechTask?.cancel()
        subtitleSpeechTask = nil
        subtitleBubble = nil
        pronunciationSpeaker.stop()
    }

    private func startSubtitlePronunciation(text: String, apiLanguage: String?, fallbackLanguage: String?) {
        subtitleSpeechTask?.cancel()
        pronunciationSpeaker.stop()
        subtitleSpeechTask = Task { @MainActor in
            guard let configuration = appState.configuration else {
                if let fallbackLanguage {
                    pronunciationSpeaker.speakFallback(text, language: fallbackLanguage)
                }
                return
            }
            do {
                let client = APIClient(configuration: configuration)
                let data = try await client.synthesizeAudio(text: text, language: apiLanguage)
                guard !Task.isCancelled else { return }
                pronunciationSpeaker.playAudio(data)
            } catch {
                guard !Task.isCancelled else { return }
                if let fallbackLanguage {
                    pronunciationSpeaker.speakFallback(text, language: fallbackLanguage)
                }
            }
        }
    }

    private func lookupInputLanguage(
        for lineKind: VideoSubtitleLineKind,
        originalLanguage: String,
        translationLanguage: String
    ) -> String {
        let resolvedOriginal = originalLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        let resolvedTranslation = translationLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
        switch lineKind {
        case .translation, .unknown:
            return resolvedTranslation.isEmpty ? resolvedOriginal : resolvedTranslation
        case .original, .transliteration:
            return resolvedOriginal.isEmpty ? resolvedTranslation : resolvedOriginal
        }
    }

    private func sanitizeLookupQuery(_ value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        let stripped = trimmed.trimmingCharacters(in: .punctuationCharacters.union(.symbols))
        let normalized = stripped.trimmingCharacters(in: .whitespacesAndNewlines)
        return normalized.isEmpty ? nil : normalized
    }

    private func nearestLookupTokenIndex(in tokens: [String], startingAt index: Int) -> Int? {
        guard !tokens.isEmpty else { return nil }
        let clamped = max(0, min(index, tokens.count - 1))
        if sanitizeLookupQuery(tokens[clamped]) != nil {
            return clamped
        }
        if tokens.count == 1 {
            return nil
        }
        for offset in 1..<tokens.count {
            let forward = clamped + offset
            if forward < tokens.count, sanitizeLookupQuery(tokens[forward]) != nil {
                return forward
            }
            let backward = clamped - offset
            if backward >= 0, sanitizeLookupQuery(tokens[backward]) != nil {
                return backward
            }
        }
        return nil
    }

    private func nextLookupTokenIndex(
        in tokens: [String],
        startingAt index: Int,
        direction: Int
    ) -> Int? {
        guard !tokens.isEmpty else { return nil }
        let step = direction >= 0 ? 1 : -1
        var idx = index
        while idx >= 0 && idx < tokens.count {
            if sanitizeLookupQuery(tokens[idx]) != nil {
                return idx
            }
            idx += step
        }
        return nil
    }

    private func resolveSpeechLanguage(_ value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let normalized = trimmed.replacingOccurrences(of: "_", with: "-")
        if normalized.contains("-") || normalized.count <= 3 {
            return normalized
        }
        switch normalized.lowercased() {
        case "english":
            return "en-US"
        case "japanese":
            return "ja-JP"
        case "spanish":
            return "es-ES"
        case "french":
            return "fr-FR"
        case "german":
            return "de-DE"
        case "italian":
            return "it-IT"
        case "portuguese":
            return "pt-PT"
        case "chinese":
            return "zh-CN"
        case "korean":
            return "ko-KR"
        case "russian":
            return "ru-RU"
        case "arabic":
            return "ar-SA"
        case "hindi":
            return "hi-IN"
        default:
            return nil
        }
    }

    private func toggleSubtitleVisibility(_ kind: VideoSubtitleLineKind) {
        switch kind {
        case .original:
            subtitleVisibility.showOriginal.toggle()
        case .transliteration:
            subtitleVisibility.showTransliteration.toggle()
        case .translation:
            subtitleVisibility.showTranslation.toggle()
        case .unknown:
            subtitleVisibility.showTranslation.toggle()
        }
    }

    private func toggleShortcutHelp() {
        isShortcutHelpPinned.toggle()
    }

    private func showShortcutHelpModifier() {
        isShortcutHelpModifierActive = true
    }

    private func hideShortcutHelpModifier() {
        isShortcutHelpModifierActive = false
    }

    private func dismissShortcutHelp() {
        isShortcutHelpPinned = false
    }

    private var subtitleFontScale: CGFloat {
        get { CGFloat(subtitleFontScaleValue) }
        nonmutating set { subtitleFontScaleValue = Double(newValue) }
    }

    private var subtitleLinguistFontScale: CGFloat {
        get { CGFloat(subtitleLinguistFontScaleValue) }
        nonmutating set { subtitleLinguistFontScaleValue = Double(newValue) }
    }
}

private struct VideoPlayerOverlayView: View {
    let cues: [VideoSubtitleCue]
    let currentTime: Double
    let duration: Double
    let subtitleError: String?
    let tracks: [VideoSubtitleTrack]
    @Binding var selectedTrack: VideoSubtitleTrack?
    @Binding var subtitleVisibility: SubtitleVisibility
    @Binding var showSubtitleSettings: Bool
    @Binding var showTVControls: Bool
    @Binding var scrubberValue: Double
    @Binding var isScrubbing: Bool
    let metadata: VideoPlaybackMetadata
    let segmentOptions: [VideoSegmentOption]
    let selectedSegmentID: String?
    let jobProgressLabel: String?
    let jobRemainingLabel: String?
    let subtitleFontScale: CGFloat
    let isPlaying: Bool
    let subtitleSelection: VideoSubtitleWordSelection?
    let subtitleBubble: VideoLinguistBubbleState?
    let subtitleLinguistFontScale: CGFloat
    let canIncreaseSubtitleLinguistFont: Bool
    let canDecreaseSubtitleLinguistFont: Bool
    let isHeaderCollapsed: Bool
    let onToggleHeaderCollapsed: () -> Void
    let onResetSubtitleFont: (() -> Void)?
    let onSetSubtitleFont: ((CGFloat) -> Void)?
    let onResetSubtitleBubbleFont: (() -> Void)?
    let onSetSubtitleBubbleFont: ((CGFloat) -> Void)?
    let onPlayPause: () -> Void
    let onSkipForward: () -> Void
    let onSkipBackward: () -> Void
    let onSeek: (Double) -> Void
    let onSkipSentence: (Int) -> Void
    let onNavigateSubtitleWord: (Int) -> Void
    let onNavigateSubtitleTrack: (Int) -> Bool
    let onSubtitleLookup: () -> Void
    let onSubtitleTokenLookup: (VideoSubtitleTokenReference) -> Void
    let onSubtitleTokenSeek: (VideoSubtitleTokenReference) -> Void
    let onIncreaseSubtitleLinguistFont: () -> Void
    let onDecreaseSubtitleLinguistFont: () -> Void
    let onSelectSegment: ((String) -> Void)?
    let onCloseSubtitleBubble: () -> Void
    let onUserInteraction: () -> Void
    #if !os(tvOS)
    @Environment(\.dismiss) private var dismiss
    @AppStorage("video.subtitle.verticalOffset") private var subtitleVerticalOffsetValue: Double = 0
    @State private var subtitleDragTranslation: CGFloat = 0
    private let subtitleBottomPadding: CGFloat = 72
    #endif
    #if os(tvOS)
    @FocusState private var focusTarget: VideoPlayerFocusTarget?
    @State private var pendingSkipTask: Task<Void, Never>?
    @State private var pendingSkipDirection: MoveCommandDirection?
    #endif
    var body: some View {
        overlayContent
    }

    private var overlayContent: some View {
        ZStack {
            #if os(tvOS)
            tvOverlay
            #else
            iosOverlay
            #endif
            #if os(tvOS)
            infoHeaderOverlay
            #endif
            if showSubtitleSettings {
                subtitleSettingsOverlay
            }
        }
        .animation(.easeInOut(duration: 0.2), value: showSubtitleSettings)
        #if os(tvOS)
        .onAppear {
            if showTVControls {
                focusTarget = .control(.playPause)
            } else if isPlaying {
                focusTarget = .subtitles
            } else {
                focusTarget = nil
            }
        }
        .onChange(of: showSubtitleSettings) { _, isVisible in
            if isVisible {
                focusTarget = nil
            } else if showTVControls {
                focusTarget = .control(.playPause)
            } else if isPlaying {
                focusTarget = .subtitles
            } else {
                focusTarget = nil
            }
        }
        .onChange(of: showTVControls) { _, isVisible in
            if isVisible {
                focusTarget = .control(.playPause)
            } else if isPlaying {
                focusTarget = .subtitles
            } else {
                focusTarget = nil
            }
        }
        .onChange(of: isPlaying) { _, playing in
            if playing {
                focusTarget = showTVControls ? .control(.playPause) : .subtitles
            } else if showTVControls {
                focusTarget = .control(.playPause)
            } else {
                focusTarget = nil
            }
        }
        #endif
    }

    private var iosOverlay: some View {
        VStack {
            topBar
            Spacer()
            subtitleStack
        }
    }

    #if os(tvOS)
    @ViewBuilder
    private var tvOverlay: some View {
        if showTVControls {
            VStack(spacing: 16) {
                Spacer()
                subtitleStack
                tvBottomBar
            }
            .padding(.horizontal, 60)
            .padding(.bottom, 36)
            .onPlayPauseCommand {
                onPlayPause()
                onUserInteraction()
            }
        } else {
            VStack(spacing: 16) {
                Spacer()
                subtitleStack
            }
            .padding(.horizontal, 60)
            .padding(.bottom, 36)
            .onPlayPauseCommand {
                onPlayPause()
                onUserInteraction()
            }
        }
    }
    #endif

    @ViewBuilder
    private var subtitleStack: some View {
        let stack = VStack(spacing: 6) {
            if let subtitleBubble {
                VideoLinguistBubbleView(
                    bubble: subtitleBubble,
                    fontScale: subtitleLinguistFontScale,
                    canIncreaseFont: canIncreaseSubtitleLinguistFont,
                    canDecreaseFont: canDecreaseSubtitleLinguistFont,
                    onIncreaseFont: onIncreaseSubtitleLinguistFont,
                    onDecreaseFont: onDecreaseSubtitleLinguistFont,
                    onResetFont: onResetSubtitleBubbleFont,
                    onClose: onCloseSubtitleBubble,
                    onMagnify: onSetSubtitleBubbleFont
                )
                .padding(.bottom, 6)
            }
            SubtitleOverlayView(
                cues: cues,
                currentTime: currentTime,
                visibility: subtitleVisibility,
                fontScale: subtitleFontScale,
                selection: subtitleSelection,
                onTokenLookup: onSubtitleTokenLookup,
                onTokenSeek: onSubtitleTokenSeek,
                onResetFont: onResetSubtitleFont,
                onMagnify: onSetSubtitleFont
            )
            .padding(.horizontal)
        }
        #if os(iOS)
        stack
            .padding(.bottom, subtitleBottomPadding)
            .contentShape(Rectangle())
            .offset(subtitleDragOffset)
            .simultaneousGesture(subtitleDragGesture, including: .gesture)
        #elseif os(tvOS)
        stack
            .contentShape(Rectangle())
            .focusable(!showSubtitleSettings)
            .focused($focusTarget, equals: .subtitles)
            .focusSection()
            .focusEffectDisabled()
            .onMoveCommand { direction in
                guard !showSubtitleSettings else { return }
                switch direction {
                case .left:
                    if isPlaying {
                        handlePlaybackDirectionalCommand(direction)
                    } else {
                        onNavigateSubtitleWord(-1)
                    }
                    focusTarget = .subtitles
                case .right:
                    if isPlaying {
                        handlePlaybackDirectionalCommand(direction)
                    } else {
                        onNavigateSubtitleWord(1)
                    }
                    focusTarget = .subtitles
                case .up:
                    if isPlaying {
                        showTVControls = true
                        focusTarget = .control(.playPause)
                    } else {
                        _ = onNavigateSubtitleTrack(-1)
                        focusTarget = .subtitles
                    }
                case .down:
                    if isPlaying {
                        return
                    }
                    let moved = onNavigateSubtitleTrack(1)
                    if moved {
                        focusTarget = .subtitles
                    } else {
                        showTVControls = true
                        focusTarget = .control(.playPause)
                    }
                default:
                    break
                }
            }
            .onTapGesture {
                if isPlaying {
                    onUserInteraction()
                } else {
                    onSubtitleLookup()
                }
            }
        #else
        stack
        #endif
        if let subtitleError, cues.isEmpty {
            Text(subtitleError)
                .font(.caption)
                .foregroundStyle(.white)
                .padding(8)
                .background(.black.opacity(0.7), in: RoundedRectangle(cornerRadius: 8))
                .padding(.bottom, 12)
                .allowsHitTesting(false)
        }
    }

    @ViewBuilder
    private var subtitleSettingsOverlay: some View {
        Color.black.opacity(0.55)
            .ignoresSafeArea()
            .onTapGesture {
                showSubtitleSettings = false
            }
        #if os(tvOS)
        VStack {
            Spacer()
            SubtitleSettingsPanel(
                tracks: tracks,
                selectedTrack: $selectedTrack,
                visibility: $subtitleVisibility,
                segmentOptions: segmentOptions,
                selectedSegmentID: selectedSegmentID,
                onSelectSegment: onSelectSegment,
                onClose: { showSubtitleSettings = false }
            )
            .frame(maxWidth: 680)
            .padding(.bottom, 36)
        }
        .padding(.horizontal, 60)
        .transition(.move(edge: .bottom).combined(with: .opacity))
        #else
        SubtitleSettingsPanel(
            tracks: tracks,
            selectedTrack: $selectedTrack,
            visibility: $subtitleVisibility,
            segmentOptions: segmentOptions,
            selectedSegmentID: selectedSegmentID,
            onSelectSegment: onSelectSegment,
            onClose: { showSubtitleSettings = false }
        )
        .padding(.horizontal, 24)
        .transition(.opacity)
        #endif
    }

    @ViewBuilder
    private var topBar: some View {
        let timelineLabel = videoTimelineLabel
        let segmentLabel = segmentHeaderLabel
        let shouldShowHeaderInfo = !isHeaderCollapsed
        if isPad {
            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .top, spacing: 12) {
                    #if !os(tvOS)
                    Button(action: { dismiss() }) {
                        Image(systemName: "xmark")
                            .font(.caption.weight(.semibold))
                            .padding(8)
                            .background(.black.opacity(0.45), in: Circle())
                            .foregroundStyle(.white)
                    }
                    #endif
                    Spacer(minLength: 12)
                    HStack(spacing: 8) {
                        if hasOptions {
                            subtitleButton
                        }
                    }
                }
                HStack(alignment: .top, spacing: 12) {
                    if shouldShowHeaderInfo {
                        infoHeaderContent
                    }
                    Spacer(minLength: 12)
                    VStack(alignment: .trailing, spacing: 6) {
                        if let segmentLabel, shouldShowHeaderInfo {
                            videoTimelineView(label: segmentLabel)
                        }
                        if let timelineLabel, shouldShowHeaderInfo {
                            videoTimelineView(label: timelineLabel)
                        }
                        headerToggleButton
                    }
                }
            }
            .padding(.top, 10 + iPadHeaderOffset)
            .padding(.horizontal, 12)
        } else {
            HStack(alignment: .top, spacing: 12) {
                #if !os(tvOS)
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark")
                        .font(.caption.weight(.semibold))
                        .padding(8)
                        .background(.black.opacity(0.45), in: Circle())
                        .foregroundStyle(.white)
                }
                #endif
                if shouldShowHeaderInfo {
                    infoHeaderContent
                }

                Spacer(minLength: 12)

                if timelineLabel != nil || hasOptions || !isTV {
                    VStack(alignment: .trailing, spacing: 6) {
                        if let segmentLabel, shouldShowHeaderInfo {
                            videoTimelineView(label: segmentLabel)
                        }
                        if let timelineLabel, shouldShowHeaderInfo {
                            videoTimelineView(label: timelineLabel)
                        }
                        #if os(tvOS)
                        tvControls
                        #else
                        HStack(spacing: 8) {
                            if hasOptions {
                                subtitleButton
                            }
                            headerToggleButton
                        }
                        #endif
                    }
                }
            }
            .padding(.top, 10)
            .padding(.horizontal, 12)
        }
    }

    private var infoHeaderContent: some View {
        HStack(alignment: .top, spacing: 12) {
            PlayerChannelBugView(variant: metadata.channelVariant, label: metadata.channelLabel)
            if hasInfoBadge {
                infoBadgeView
            }
        }
    }

    #if os(iOS)
    private var subtitleDragOffset: CGSize {
        let rawHeight = subtitleVerticalOffset + subtitleDragTranslation
        let clampedHeight = min(rawHeight, 0)
        return CGSize(width: 0, height: clampedHeight)
    }

    private var subtitleVerticalOffset: CGFloat {
        get { CGFloat(subtitleVerticalOffsetValue) }
        nonmutating set { subtitleVerticalOffsetValue = Double(newValue) }
    }

    private var subtitleDragGesture: some Gesture {
        DragGesture(minimumDistance: 10, coordinateSpace: .local)
            .onChanged { value in
                subtitleDragTranslation = value.translation.height
            }
            .onEnded { value in
                let proposedHeight = subtitleVerticalOffset + value.translation.height
                subtitleVerticalOffset = min(proposedHeight, 0)
                subtitleDragTranslation = 0
            }
    }

    #endif

    private var infoBadgeView: some View {
        HStack(alignment: .top, spacing: 8) {
            if metadata.artworkURL != nil || metadata.secondaryArtworkURL != nil {
                PlayerCoverStackView(
                    primaryURL: metadata.artworkURL,
                    secondaryURL: metadata.secondaryArtworkURL,
                    width: infoCoverWidth,
                    height: infoCoverHeight,
                    isTV: isTV
                )
            }
            VStack(alignment: .leading, spacing: 2) {
                if !metadata.title.isEmpty {
                    Text(metadata.title)
                        .font(infoTitleFont)
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                        .foregroundStyle(.white)
                }
                if let subtitle = metadata.subtitle, !subtitle.isEmpty {
                    Text(subtitle)
                        .font(infoMetaFont)
                        .foregroundStyle(Color.white.opacity(0.75))
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                }
                if !metadata.languageFlags.isEmpty {
                    PlayerLanguageFlagRow(flags: metadata.languageFlags, isTV: isTV)
                }
            }
        }
    }

    #if os(tvOS)
    private var infoHeaderOverlay: some View {
        let timelineLabel = videoTimelineLabel
        let segmentLabel = segmentHeaderLabel
        return HStack(alignment: .top, spacing: 12) {
            infoHeaderContent
            Spacer(minLength: 12)
            VStack(alignment: .trailing, spacing: 6) {
                if let segmentLabel {
                    videoTimelineView(label: segmentLabel)
                }
                if let timelineLabel {
                    videoTimelineView(label: timelineLabel)
                }
            }
        }
        .padding(.top, 6)
        .padding(.horizontal, 6)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .allowsHitTesting(false)
    }
    #endif

    private func videoTimelineView(label: String) -> some View {
        Text(label)
            .font(infoIndicatorFont)
            .foregroundStyle(Color.white.opacity(0.75))
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(
                Capsule()
                    .fill(Color.black.opacity(0.5))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(0.18), lineWidth: 1)
                    )
            )
    }

    private var videoTimelineLabel: String? {
        guard duration.isFinite, duration > 0, currentTime.isFinite else { return nil }
        let played = min(max(currentTime, 0), duration)
        let remaining = max(duration - played, 0)
        let base = "\(formatDurationLabel(played)) / \(formatDurationLabel(remaining)) remaining"
        if let jobRemainingLabel {
            return "\(base) · \(jobRemainingLabel)"
        }
        return base
    }

    private var segmentHeaderLabel: String? {
        let chunkLabel: String?
        if segmentOptions.count > 1 {
            if let selectedSegmentID,
               let index = segmentOptions.firstIndex(where: { $0.id == selectedSegmentID }) {
                chunkLabel = "Chunk \(index + 1) / \(segmentOptions.count)"
            } else {
                chunkLabel = "Chunk 1 / \(segmentOptions.count)"
            }
        } else {
            chunkLabel = nil
        }
        guard let chunkLabel else { return nil }
        if let jobProgressLabel {
            return "\(jobProgressLabel) · \(chunkLabel)"
        }
        return chunkLabel
    }

    private func formatDurationLabel(_ value: Double) -> String {
        let total = max(0, Int(value.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let seconds = total % 60
        return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
    }

    private var subtitleButton: some View {
        let labelText = hasTracks ? selectedTrackLabel : "Options"
        return Button {
            showSubtitleSettings = true
        } label: {
            Label(
                labelText,
                systemImage: "captions.bubble"
            )
            .labelStyle(.titleAndIcon)
            .font(.caption)
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(.black.opacity(0.45), in: RoundedRectangle(cornerRadius: 8))
            .foregroundStyle(.white)
        }
    }

    private var headerToggleButton: some View {
        Button(action: onToggleHeaderCollapsed) {
            Image(systemName: isHeaderCollapsed ? "chevron.down" : "chevron.up")
                .font(.caption.weight(.semibold))
                .padding(6)
                .background(.black.opacity(0.45), in: Circle())
                .foregroundStyle(.white)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(isHeaderCollapsed ? "Show info header" : "Hide info header")
    }

    #if os(tvOS)
    private var tvControls: some View {
        HStack(spacing: 14) {
            tvControlButton(
                systemName: "gobackward.15",
                isFocused: focusTarget == .control(.skipBackward),
                action: onSkipBackward
            )
                .focused($focusTarget, equals: .control(.skipBackward))
            tvControlButton(
                systemName: isPlaying ? "pause.fill" : "play.fill",
                prominent: true,
                isFocused: focusTarget == .control(.playPause),
                action: onPlayPause
            )
                .focused($focusTarget, equals: .control(.playPause))
            tvControlButton(
                systemName: "goforward.15",
                isFocused: focusTarget == .control(.skipForward),
                action: onSkipForward
            )
                .focused($focusTarget, equals: .control(.skipForward))
            if hasOptions {
                tvControlButton(
                    systemName: "captions.bubble",
                    label: "Options",
                    isFocused: focusTarget == .control(.captions)
                ) {
                    showSubtitleSettings = true
                }
                .focused($focusTarget, equals: .control(.captions))
            }
        }
        .onMoveCommand { direction in
            guard !showSubtitleSettings else { return }
            if direction == .up {
                focusTarget = .subtitles
            }
        }
    }

    private func tvControlButton(
        systemName: String,
        label: String? = nil,
        prominent: Bool = false,
        isFocused: Bool = false,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            if let label {
                Label(label, systemImage: systemName)
                    .labelStyle(.titleAndIcon)
            } else {
                Image(systemName: systemName)
            }
        }
        .font(.title3.weight(.semibold))
        .foregroundStyle(.white)
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(prominent ? Color.white.opacity(0.18) : Color.black.opacity(0.45))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isFocused ? Color.white.opacity(0.85) : Color.clear, lineWidth: 1)
        )
        .scaleEffect(isFocused ? 1.06 : 1.0)
        .shadow(color: isFocused ? Color.white.opacity(0.25) : .clear, radius: 6, x: 0, y: 0)
        .animation(.easeInOut(duration: 0.12), value: isFocused)
    }

    private var tvBottomBar: some View {
        VStack(spacing: 10) {
            HStack(alignment: .center, spacing: 18) {
                Spacer(minLength: 0)
                tvControls
                Spacer(minLength: 0)
            }
            if duration > 0 {
                HStack(spacing: 12) {
                    Text(formattedTime(displayTime))
                        .font(.caption2)
                        .foregroundStyle(.white.opacity(0.8))
                        .frame(width: 64, alignment: .leading)
                    TVScrubber(
                        value: $scrubberValue,
                        range: 0...max(duration, 1),
                        isFocusable: showTVControls,
                        onEditingChanged: { editing in
                            isScrubbing = editing
                            onUserInteraction()
                        },
                        onCommit: { newValue in
                            onSeek(newValue)
                        },
                        onUserInteraction: onUserInteraction
                    )
                    .focused($focusTarget, equals: .control(.scrubber))
                    Text(formattedTime(duration))
                        .font(.caption2)
                        .foregroundStyle(.white.opacity(0.8))
                        .frame(width: 64, alignment: .trailing)
                }
            }
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 14)
        .background(
            LinearGradient(
                colors: [Color.black.opacity(0.75), Color.black.opacity(0.35)],
                startPoint: .bottom,
                endPoint: .top
            ),
            in: RoundedRectangle(cornerRadius: 20)
        )
        .opacity(showTVControls ? 1 : 0)
        .allowsHitTesting(showTVControls)
        .animation(.easeInOut(duration: 0.2), value: showTVControls)
        .focusSection()
        .onMoveCommand { direction in
            guard !showSubtitleSettings else { return }
            if direction == .up {
                focusTarget = .subtitles
            }
        }
    }

    #if os(tvOS)
    private func handlePlaybackDirectionalCommand(_ direction: MoveCommandDirection) {
        guard direction == .left || direction == .right else { return }
        if pendingSkipTask != nil, pendingSkipDirection == direction {
            pendingSkipTask?.cancel()
            pendingSkipTask = nil
            pendingSkipDirection = nil
            beginScrubbing()
            return
        }
        pendingSkipTask?.cancel()
        pendingSkipDirection = direction
        let delta = direction == .left ? -1 : 1
        pendingSkipTask = Task {
            try? await Task.sleep(nanoseconds: 200_000_000)
            await MainActor.run {
                pendingSkipTask = nil
                pendingSkipDirection = nil
                onSkipSentence(delta)
            }
        }
    }

    private func beginScrubbing() {
        showTVControls = true
        scrubberValue = displayTime
        focusTarget = .control(.scrubber)
        onUserInteraction()
    }
    #endif

    private var displayTime: Double {
        isScrubbing ? scrubberValue : currentTime
    }

    private func formattedTime(_ seconds: Double) -> String {
        guard seconds.isFinite else { return "--:--" }
        let total = max(0, Int(seconds.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let remainingSeconds = total % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, remainingSeconds)
        }
        return String(format: "%02d:%02d", minutes, remainingSeconds)
    }
    #endif

    private var selectedTrackLabel: String {
        if let selectedTrack {
            return trimmedTrackLabel(selectedTrack.label)
        }
        return "Subtitles Off"
    }

    private func trimmedTrackLabel(_ label: String) -> String {
        var trimmed = label.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return "Subtitles Off" }
        if let separator = trimmed.lastIndex(where: { $0 == "/" || $0 == "\\" }) {
            trimmed = String(trimmed[trimmed.index(after: separator)...])
        }
        if let dot = trimmed.lastIndex(of: "."),
           dot > trimmed.startIndex,
           trimmed.distance(from: dot, to: trimmed.endIndex) <= 6 {
            trimmed = String(trimmed[..<dot])
        }
        let limit = isTV ? 32 : (isPhone ? 18 : 26)
        if trimmed.count > limit {
            trimmed = String(trimmed.prefix(max(limit - 3, 0))) + "..."
        }
        return trimmed
    }

    private var hasTracks: Bool {
        !tracks.isEmpty
    }

    private var hasSegmentOptions: Bool {
        segmentOptions.count > 1
    }

    private var hasOptions: Bool {
        hasTracks || hasSegmentOptions
    }

    private var hasInfoBadge: Bool {
        !metadata.title.isEmpty || (metadata.subtitle?.isEmpty == false) || metadata.artworkURL != nil
    }

    private var infoCoverWidth: CGFloat {
        PlayerInfoMetrics.coverWidth(isTV: isTV)
    }

    private var infoCoverHeight: CGFloat {
        PlayerInfoMetrics.coverHeight(isTV: isTV)
    }

    private var infoTitleFont: Font {
        #if os(tvOS)
        return .headline
        #else
        return .subheadline.weight(.semibold)
        #endif
    }

    private var infoMetaFont: Font {
        #if os(tvOS)
        return .callout
        #else
        return .caption
        #endif
    }

    private var infoIndicatorFont: Font {
        #if os(tvOS)
        return .callout.weight(.semibold)
        #else
        return .caption.weight(.semibold)
        #endif
    }

    private var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }

    private var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    private var isPhone: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .phone
        #else
        return false
        #endif
    }

    private var iPadHeaderOffset: CGFloat {
        #if os(iOS)
        return isPad ? UIScreen.main.bounds.height * 0.06 : 0
        #else
        return 0
        #endif
    }
}

#if os(tvOS)
private enum TVFocusTarget: Hashable {
    case playPause
    case skipBackward
    case skipForward
    case captions
    case scrubber
}

private enum VideoPlayerFocusTarget: Hashable {
    case subtitles
    case control(TVFocusTarget)
}

private struct TVScrubber: View {
    @Binding var value: Double
    let range: ClosedRange<Double>
    let isFocusable: Bool
    let onEditingChanged: (Bool) -> Void
    let onCommit: (Double) -> Void
    let onUserInteraction: () -> Void

    @FocusState private var isFocused: Bool
    @State private var commitTask: Task<Void, Never>?
    @State private var isEditing = false

    var body: some View {
        GeometryReader { proxy in
            let progress = normalizedProgress
            let width = max(proxy.size.width, 1)
            let barHeight: CGFloat = 6
            let thumbSize: CGFloat = isFocused ? 18 : 14
            let xOffset = max(0, min(width - thumbSize, width * progress - thumbSize / 2))
            ZStack(alignment: .leading) {
                Capsule()
                    .fill(Color.white.opacity(0.25))
                    .frame(height: barHeight)
                Capsule()
                    .fill(Color.white)
                    .frame(width: max(thumbSize, width * progress), height: barHeight)
                Circle()
                    .fill(Color.white)
                    .frame(width: thumbSize, height: thumbSize)
                    .offset(x: xOffset)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(height: 24)
        .focusable(isFocusable)
        .focused($isFocused)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isFocused ? Color.white.opacity(0.8) : .clear, lineWidth: 1)
        )
        .onChange(of: isFocused) { _, focused in
            onUserInteraction()
            if !focused {
                commitScrub()
            }
        }
        .onMoveCommand { direction in
            guard isFocused else { return }
            onUserInteraction()
            beginScrubbing()
            let step = stepSize
            switch direction {
            case .left:
                value = max(range.lowerBound, value - step)
            case .right:
                value = min(range.upperBound, value + step)
            default:
                break
            }
            scheduleCommit()
        }
        .onTapGesture {
            onUserInteraction()
            beginScrubbing()
            scheduleCommit()
        }
    }

    private var normalizedProgress: CGFloat {
        let span = max(range.upperBound - range.lowerBound, 1)
        let clamped = min(max(value, range.lowerBound), range.upperBound)
        return CGFloat((clamped - range.lowerBound) / span)
    }

    private var stepSize: Double {
        let span = max(range.upperBound - range.lowerBound, 1)
        return max(span / 300, 1)
    }

    private func scheduleCommit() {
        commitTask?.cancel()
        commitTask = Task {
            try? await Task.sleep(nanoseconds: 600_000_000)
            await MainActor.run {
                commitScrub()
            }
        }
    }

    private func commitScrub() {
        commitTask?.cancel()
        commitTask = nil
        if isEditing {
            onEditingChanged(false)
            isEditing = false
        }
        onCommit(value)
    }

    private func beginScrubbing() {
        guard !isEditing else { return }
        isEditing = true
        onEditingChanged(true)
    }
}
#endif

private struct SubtitleSettingsPanel: View {
    let tracks: [VideoSubtitleTrack]
    @Binding var selectedTrack: VideoSubtitleTrack?
    @Binding var visibility: SubtitleVisibility
    let segmentOptions: [VideoSegmentOption]
    let selectedSegmentID: String?
    let onSelectSegment: ((String) -> Void)?
    let onClose: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Subtitles")
                    .font(.headline)
                Spacer()
                Button("Done") {
                    onClose()
                }
                .font(.subheadline.weight(.semibold))
            }
            Divider()
                .overlay(Color.white.opacity(0.25))

            if segmentOptions.count > 1 {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Chunks")
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.7))
                    ForEach(segmentOptions) { segment in
                        Button {
                            onSelectSegment?(segment.id)
                        } label: {
                            trackRow(label: segment.label, selected: segment.id == selectedSegmentID)
                        }
                    }
                }

                Divider()
                    .overlay(Color.white.opacity(0.25))
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Tracks")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.7))
                Button {
                    selectedTrack = nil
                } label: {
                    trackRow(label: "Subtitles Off", selected: selectedTrack == nil)
                }
                if tracks.isEmpty {
                    Text("No subtitle tracks available.")
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.7))
                        .padding(.vertical, 4)
                } else {
                    ForEach(tracks) { track in
                        Button {
                            selectedTrack = track
                        } label: {
                            let label = "\(track.label) (\(track.format.label))"
                            trackRow(label: label, selected: selectedTrack?.id == track.id)
                        }
                    }
                }
            }

            Divider()
                .overlay(Color.white.opacity(0.25))

            VStack(alignment: .leading, spacing: 8) {
                Text("Lines")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.7))
                Toggle("Original", isOn: $visibility.showOriginal)
                Toggle("Translation", isOn: $visibility.showTranslation)
                Toggle("Transliteration", isOn: $visibility.showTransliteration)
            }
            .disabled(selectedTrack == nil)
        }
        .padding(16)
        .frame(maxWidth: panelMaxWidth)
        .background(.black.opacity(0.85), in: RoundedRectangle(cornerRadius: 16))
        .foregroundStyle(.white)
    }

    private func trackRow(label: String, selected: Bool) -> some View {
        HStack {
            Text(label)
                .lineLimit(1)
            Spacer()
            if selected {
                Image(systemName: "checkmark")
            }
        }
        .padding(.vertical, 4)
    }

    private var panelMaxWidth: CGFloat {
        #if os(tvOS)
        return 640
        #else
        return 480
        #endif
    }
}

private enum VideoLinguistBubbleStatus: Equatable {
    case loading
    case ready
    case error(String)
}

private struct VideoLinguistBubbleState: Equatable {
    let query: String
    let status: VideoLinguistBubbleStatus
    let answer: String?
    let model: String?
}

private struct VideoLinguistBubbleView: View {
    let bubble: VideoLinguistBubbleState
    let fontScale: CGFloat
    let canIncreaseFont: Bool
    let canDecreaseFont: Bool
    let onIncreaseFont: () -> Void
    let onDecreaseFont: () -> Void
    let onResetFont: (() -> Void)?
    let onClose: () -> Void
    let onMagnify: ((CGFloat) -> Void)?

    #if os(iOS)
    @State private var magnifyStartScale: CGFloat?
    #endif

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Text("MyLinguist")
                    .font(.headline)
                Spacer(minLength: 8)
                if let model = bubble.model, !model.isEmpty {
                    Text("Model: \(model)")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                fontSizeControls
                #if os(iOS)
                if let onResetFont {
                    Button(action: onResetFont) {
                        Image(systemName: "arrow.counterclockwise")
                            .font(.caption.weight(.semibold))
                            .padding(6)
                            .background(.black.opacity(0.3), in: Circle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Reset size")
                }
                #endif
                Button(action: onClose) {
                    Image(systemName: "xmark")
                        .font(.caption.weight(.semibold))
                        .padding(6)
                        .background(.black.opacity(0.3), in: Circle())
                }
                .buttonStyle(.plain)
            }

            Text(bubble.query)
                .font(queryFont)
                .lineLimit(2)
                .minimumScaleFactor(0.8)

            bubbleContent
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(bubbleBackground)
        .overlay(
            RoundedRectangle(cornerRadius: bubbleCornerRadius)
                .stroke(Color.white.opacity(0.12), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: bubbleCornerRadius))
        #if os(iOS)
        .simultaneousGesture(bubbleMagnifyGesture, including: .gesture)
        #endif
    }

    #if os(iOS)
    private var bubbleMagnifyGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                guard let onMagnify else { return }
                if magnifyStartScale == nil {
                    magnifyStartScale = fontScale
                }
                let startScale = magnifyStartScale ?? fontScale
                onMagnify(startScale * value)
            }
            .onEnded { _ in
                magnifyStartScale = nil
            }
    }
    #endif

    @ViewBuilder
    private var bubbleContent: some View {
        switch bubble.status {
        case .loading:
            HStack(spacing: 8) {
                ProgressView()
                    .progressViewStyle(.circular)
                Text("Looking up...")
                    .font(bodyFont)
                    .foregroundStyle(.secondary)
            }
        case let .error(message):
            Text(message)
                .font(bodyFont)
                .foregroundStyle(.red)
        case .ready:
            ScrollView {
                Text(bubble.answer ?? "")
                    .font(bodyFont)
                    .foregroundStyle(.primary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(maxHeight: bubbleMaxHeight)
        }
    }

    private var fontSizeControls: some View {
        HStack(spacing: 4) {
            Button(action: onDecreaseFont) {
                Text("A-")
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 4)
                    .background(.black.opacity(0.3), in: Capsule())
            }
            .buttonStyle(.plain)
            .disabled(!canDecreaseFont)
            Button(action: onIncreaseFont) {
                Text("A+")
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 4)
                    .background(.black.opacity(0.3), in: Capsule())
            }
            .buttonStyle(.plain)
            .disabled(!canIncreaseFont)
        }
    }

    private var queryFont: Font {
        scaledFont(textStyle: .title3, weight: .semibold)
    }

    private var bodyFont: Font {
        scaledFont(textStyle: .callout, weight: .regular)
    }

    private func scaledFont(textStyle: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let baseSize = UIFont.preferredFont(forTextStyle: textStyle).pointSize
        return .system(size: baseSize * fontScale, weight: weight)
        #else
        return .system(size: 16 * fontScale, weight: weight)
        #endif
    }

    private var bubbleBackground: Color {
        Color.black.opacity(0.75)
    }

    private var bubbleCornerRadius: CGFloat {
        #if os(tvOS)
        return 18
        #else
        return 14
        #endif
    }

    private var bubbleMaxHeight: CGFloat {
        #if os(tvOS)
        return 220
        #else
        return 180
        #endif
    }
}

#if os(iOS)
private struct VideoShortcutHelpOverlayView: View {
    let onDismiss: () -> Void

    private let sections: [ShortcutHelpSection] = [
        ShortcutHelpSection(
            title: "Playback",
            items: [
                ShortcutHelpItem(keys: "Space", action: "Play or pause"),
                ShortcutHelpItem(keys: "Left Arrow (playing)", action: "Previous sentence"),
                ShortcutHelpItem(keys: "Right Arrow (playing)", action: "Next sentence")
            ]
        ),
        ShortcutHelpSection(
            title: "Subtitles",
            items: [
                ShortcutHelpItem(keys: "Left / Right Arrow (paused)", action: "Previous or next word"),
                ShortcutHelpItem(keys: "Up / Down Arrow (paused)", action: "Switch subtitle line"),
                ShortcutHelpItem(keys: "O", action: "Toggle original line"),
                ShortcutHelpItem(keys: "I", action: "Toggle transliteration line"),
                ShortcutHelpItem(keys: "P", action: "Toggle translation line"),
                ShortcutHelpItem(keys: "+ / -", action: "Subtitle font size")
            ]
        ),
        ShortcutHelpSection(
            title: "Touch",
            items: [
                ShortcutHelpItem(keys: "Tap word", action: "Jump to word"),
                ShortcutHelpItem(keys: "Long press word", action: "System lookup"),
                ShortcutHelpItem(keys: "Drag subtitles", action: "Move subtitle position"),
                ShortcutHelpItem(keys: "Pinch subtitles", action: "Resize subtitle text"),
                ShortcutHelpItem(keys: "Pinch bubble", action: "Resize lookup bubble")
            ]
        ),
        ShortcutHelpSection(
            title: "Help",
            items: [
                ShortcutHelpItem(keys: "H", action: "Toggle this overlay"),
                ShortcutHelpItem(keys: "Option (hold)", action: "Show shortcuts overlay")
            ]
        )
    ]

    var body: some View {
        ZStack {
            Color.black.opacity(0.55)
                .ignoresSafeArea()
                .onTapGesture {
                    onDismiss()
                }
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Text("Keyboard Shortcuts")
                        .font(.title3.weight(.semibold))
                    Spacer()
                    Button(action: onDismiss) {
                        Image(systemName: "xmark")
                            .font(.caption.weight(.semibold))
                            .padding(6)
                            .background(.black.opacity(0.3), in: Circle())
                    }
                    .buttonStyle(.plain)
                }
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(sections) { section in
                            VStack(alignment: .leading, spacing: 6) {
                                Text(section.title)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                ForEach(section.items) { item in
                                    HStack(alignment: .top, spacing: 12) {
                                        Text(item.keys)
                                            .font(.callout.monospaced())
                                            .frame(width: 170, alignment: .leading)
                                        Text(item.action)
                                            .font(.callout)
                                        Spacer(minLength: 0)
                                    }
                                }
                            }
                        }
                    }
                }
                .frame(maxHeight: 320)
            }
            .padding(20)
            .frame(maxWidth: 520)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 18))
            .overlay(
                RoundedRectangle(cornerRadius: 18)
                    .stroke(Color.white.opacity(0.12), lineWidth: 1)
            )
        }
    }

    private struct ShortcutHelpSection: Identifiable {
        let id = UUID()
        let title: String
        let items: [ShortcutHelpItem]
    }

    private struct ShortcutHelpItem: Identifiable {
        let id = UUID()
        let keys: String
        let action: String
    }
}

private struct VideoKeyboardCommandHandler: UIViewControllerRepresentable {
    let onPlayPause: () -> Void
    let onSkipBackward: () -> Void
    let onSkipForward: () -> Void
    let onNavigateLineUp: () -> Void
    let onNavigateLineDown: () -> Void
    let onIncreaseFont: () -> Void
    let onDecreaseFont: () -> Void
    let onToggleOriginal: () -> Void
    let onToggleTransliteration: () -> Void
    let onToggleTranslation: () -> Void
    let onToggleShortcutHelp: () -> Void
    let onOptionKeyDown: () -> Void
    let onOptionKeyUp: () -> Void

    func makeUIViewController(context: Context) -> KeyCommandController {
        let controller = KeyCommandController()
        controller.onPlayPause = onPlayPause
        controller.onSkipBackward = onSkipBackward
        controller.onSkipForward = onSkipForward
        controller.onNavigateLineUp = onNavigateLineUp
        controller.onNavigateLineDown = onNavigateLineDown
        controller.onIncreaseFont = onIncreaseFont
        controller.onDecreaseFont = onDecreaseFont
        controller.onToggleOriginal = onToggleOriginal
        controller.onToggleTransliteration = onToggleTransliteration
        controller.onToggleTranslation = onToggleTranslation
        controller.onToggleShortcutHelp = onToggleShortcutHelp
        controller.onOptionKeyDown = onOptionKeyDown
        controller.onOptionKeyUp = onOptionKeyUp
        return controller
    }

    func updateUIViewController(_ uiViewController: KeyCommandController, context: Context) {
        uiViewController.onPlayPause = onPlayPause
        uiViewController.onSkipBackward = onSkipBackward
        uiViewController.onSkipForward = onSkipForward
        uiViewController.onNavigateLineUp = onNavigateLineUp
        uiViewController.onNavigateLineDown = onNavigateLineDown
        uiViewController.onIncreaseFont = onIncreaseFont
        uiViewController.onDecreaseFont = onDecreaseFont
        uiViewController.onToggleOriginal = onToggleOriginal
        uiViewController.onToggleTransliteration = onToggleTransliteration
        uiViewController.onToggleTranslation = onToggleTranslation
        uiViewController.onToggleShortcutHelp = onToggleShortcutHelp
        uiViewController.onOptionKeyDown = onOptionKeyDown
        uiViewController.onOptionKeyUp = onOptionKeyUp
    }

    final class KeyCommandController: UIViewController {
        var onPlayPause: (() -> Void)?
        var onSkipBackward: (() -> Void)?
        var onSkipForward: (() -> Void)?
        var onNavigateLineUp: (() -> Void)?
        var onNavigateLineDown: (() -> Void)?
        var onIncreaseFont: (() -> Void)?
        var onDecreaseFont: (() -> Void)?
        var onToggleOriginal: (() -> Void)?
        var onToggleTransliteration: (() -> Void)?
        var onToggleTranslation: (() -> Void)?
        var onToggleShortcutHelp: (() -> Void)?
        var onOptionKeyDown: (() -> Void)?
        var onOptionKeyUp: (() -> Void)?
        private var isOptionKeyDown = false

        override var canBecomeFirstResponder: Bool {
            true
        }

        override func viewDidAppear(_ animated: Bool) {
            super.viewDidAppear(animated)
            becomeFirstResponder()
        }

        override var keyCommands: [UIKeyCommand]? {
            [
                makeCommand(input: " ", action: #selector(handlePlayPause)),
                makeCommand(input: UIKeyCommand.inputLeftArrow, action: #selector(handleSkipBackward)),
                makeCommand(input: UIKeyCommand.inputRightArrow, action: #selector(handleSkipForward)),
                makeCommand(input: UIKeyCommand.inputUpArrow, action: #selector(handleLineUp)),
                makeCommand(input: UIKeyCommand.inputDownArrow, action: #selector(handleLineDown)),
                makeCommand(input: "o", action: #selector(handleToggleOriginal)),
                makeCommand(input: "o", modifiers: [.shift], action: #selector(handleToggleOriginal)),
                makeCommand(input: "i", action: #selector(handleToggleTransliteration)),
                makeCommand(input: "i", modifiers: [.shift], action: #selector(handleToggleTransliteration)),
                makeCommand(input: "p", action: #selector(handleToggleTranslation)),
                makeCommand(input: "p", modifiers: [.shift], action: #selector(handleToggleTranslation)),
                makeCommand(input: "=", action: #selector(handleIncreaseFont)),
                makeCommand(input: "=", modifiers: [.shift], action: #selector(handleIncreaseFont)),
                makeCommand(input: "+", action: #selector(handleIncreaseFont)),
                makeCommand(input: "-", action: #selector(handleDecreaseFont)),
                makeCommand(input: "h", action: #selector(handleToggleHelp)),
                makeCommand(input: "h", modifiers: [.shift], action: #selector(handleToggleHelp))
            ]
        }

        @objc private func handlePlayPause() {
            onPlayPause?()
        }

        @objc private func handleSkipBackward() {
            onSkipBackward?()
        }

        @objc private func handleSkipForward() {
            onSkipForward?()
        }

        @objc private func handleLineUp() {
            onNavigateLineUp?()
        }

        @objc private func handleLineDown() {
            onNavigateLineDown?()
        }

        @objc private func handleIncreaseFont() {
            onIncreaseFont?()
        }

        @objc private func handleDecreaseFont() {
            onDecreaseFont?()
        }

        @objc private func handleToggleOriginal() {
            onToggleOriginal?()
        }

        @objc private func handleToggleTransliteration() {
            onToggleTransliteration?()
        }

        @objc private func handleToggleTranslation() {
            onToggleTranslation?()
        }

        @objc private func handleToggleHelp() {
            onToggleShortcutHelp?()
        }

        override func pressesBegan(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            if shouldHandleOptionKey(presses), !isOptionKeyDown {
                isOptionKeyDown = true
                onOptionKeyDown?()
            }
            super.pressesBegan(presses, with: event)
        }

        override func pressesEnded(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            if shouldHandleOptionKey(presses), isOptionKeyDown {
                isOptionKeyDown = false
                onOptionKeyUp?()
            }
            super.pressesEnded(presses, with: event)
        }

        override func pressesCancelled(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
            if isOptionKeyDown {
                isOptionKeyDown = false
                onOptionKeyUp?()
            }
            super.pressesCancelled(presses, with: event)
        }

        private func makeCommand(
            input: String,
            modifiers: UIKeyModifierFlags = [],
            action: Selector
        ) -> UIKeyCommand {
            let command = UIKeyCommand(input: input, modifierFlags: modifiers, action: action)
            command.wantsPriorityOverSystemBehavior = true
            return command
        }

        private func shouldHandleOptionKey(_ presses: Set<UIPress>) -> Bool {
            for press in presses {
                guard let key = press.key else { continue }
                if key.keyCode == .keyboardLeftAlt || key.keyCode == .keyboardRightAlt {
                    return true
                }
                if key.characters.isEmpty,
                   key.charactersIgnoringModifiers.isEmpty,
                   key.modifierFlags.contains(.alternate) {
                    return true
                }
            }
            return false
        }
    }
}
#endif

private final class VideoPronunciationSpeaker: NSObject, ObservableObject, AVAudioPlayerDelegate {
    private let synthesizer = AVSpeechSynthesizer()
    private var audioPlayer: AVAudioPlayer?

    func playAudio(_ data: Data) {
        stop()
        configureAudioSession()
        do {
            let player = try AVAudioPlayer(data: data)
            player.delegate = self
            player.prepareToPlay()
            player.play()
            audioPlayer = player
        } catch {
            audioPlayer = nil
        }
    }

    func speakFallback(_ text: String, language: String?) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        stop()
        configureAudioSession()
        let utterance = AVSpeechUtterance(string: trimmed)
        if let language, let voice = AVSpeechSynthesisVoice(language: language) {
            utterance.voice = voice
        }
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        synthesizer.speak(utterance)
    }

    func stop() {
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }
        audioPlayer?.stop()
        audioPlayer = nil
    }

    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        audioPlayer = nil
    }

    private func configureAudioSession() {
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        let options: AVAudioSession.CategoryOptions = [.allowAirPlay]
        try? session.setCategory(.playback, mode: .spokenAudio, options: options)
        try? session.setActive(true)
        #endif
    }
}

private struct VideoPlayerControllerView: UIViewControllerRepresentable {
    let player: AVPlayer
    let onShowControls: () -> Void

    func makeUIViewController(context: Context) -> AVPlayerViewController {
        #if os(tvOS)
        let controller = FocusablePlayerViewController()
        #else
        let controller = AVPlayerViewController()
        #endif
        controller.player = player
        #if os(tvOS)
        controller.showsPlaybackControls = false
        #else
        controller.showsPlaybackControls = true
        #endif
        controller.videoGravity = .resizeAspect
        controller.allowsPictureInPicturePlayback = true
        #if os(iOS)
        if #available(iOS 14.2, *) {
            controller.canStartPictureInPictureAutomaticallyFromInline = true
        }
        #endif
        #if os(tvOS)
        controller.onShowControls = onShowControls
        #endif
        return controller
    }

    func updateUIViewController(_ controller: AVPlayerViewController, context: Context) {
        controller.player = player
        #if os(tvOS)
        if let controller = controller as? FocusablePlayerViewController {
            controller.onShowControls = onShowControls
        }
        #endif
    }
}

#if os(tvOS)
private final class FocusablePlayerViewController: AVPlayerViewController {
    var onShowControls: (() -> Void)?

    override func pressesBegan(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
        for press in presses {
            switch press.type {
            case .playPause, .upArrow, .downArrow, .leftArrow, .rightArrow:
                onShowControls?()
            default:
                break
            }
        }
        super.pressesBegan(presses, with: event)
    }
}
#endif
