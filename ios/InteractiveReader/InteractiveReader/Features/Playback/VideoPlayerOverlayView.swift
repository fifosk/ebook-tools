import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

/// Video player overlay view using modular components.
/// Orchestrates header, subtitles, controls, and settings overlays.
struct VideoPlayerOverlayView<SearchPill: View, SleepTimerPill: View>: View {
    // MARK: - Playback State
    let cues: [VideoSubtitleCue]
    let currentTime: Double
    let duration: Double
    let isPlaying: Bool
    @Binding var scrubberValue: Double
    @Binding var isScrubbing: Bool
    let playbackRate: Double
    let playbackRateOptions: [Double]

    // MARK: - Subtitle State
    let subtitleError: String?
    let tracks: [VideoSubtitleTrack]
    @Binding var selectedTrack: VideoSubtitleTrack?
    @Binding var subtitleVisibility: SubtitleVisibility
    @Binding var showSubtitleSettings: Bool
    let subtitleFontScale: CGFloat
    let subtitleSelection: VideoSubtitleWordSelection?
    let subtitleSelectionRange: VideoSubtitleWordSelectionRange?
    let subtitleAlignment: HorizontalAlignment
    let subtitleMaxWidth: CGFloat?
    let subtitleLeadingInset: CGFloat
    let allowSubtitleDownwardDrag: Bool

    // MARK: - Linguist Bubble
    let subtitleBubble: VideoLinguistBubbleState?
    let subtitleLinguistFontScale: CGFloat
    let canIncreaseSubtitleLinguistFont: Bool
    let canDecreaseSubtitleLinguistFont: Bool
    let lookupLanguage: String
    let lookupLanguageOptions: [String]
    let llmModel: String
    let llmModelOptions: [String]

    // MARK: - Header State
    let metadata: VideoPlaybackMetadata
    let segmentOptions: [VideoSegmentOption]
    let selectedSegmentID: String?
    let jobProgressLabel: String?
    let jobRemainingLabel: String?
    let isHeaderCollapsed: Bool
    let headerTopInset: CGFloat

    // MARK: - Bookmarks
    let bookmarks: [PlaybackBookmarkEntry]

    // MARK: - Search
    let searchPill: SearchPill?

    // MARK: - Sleep Timer
    let sleepTimerPill: SleepTimerPill?

    // MARK: - TV Controls
    @Binding var showTVControls: Bool

    // MARK: - Callbacks
    let onAddBookmark: (() -> Void)?
    let onJumpToBookmark: (PlaybackBookmarkEntry) -> Void
    let onRemoveBookmark: (PlaybackBookmarkEntry) -> Void
    let onPlaybackRateChange: (Double) -> Void
    let onToggleHeaderCollapsed: () -> Void
    let onResetSubtitleFont: (() -> Void)?
    let onSetSubtitleFont: ((CGFloat) -> Void)?
    let onResetSubtitleBubbleFont: (() -> Void)?
    let onSetSubtitleBubbleFont: ((CGFloat) -> Void)?
    let onPlayPause: () -> Void
    let onSeek: (Double) -> Void
    let onSkipForward: () -> Void
    let onSkipBackward: () -> Void
    let onSkipSentence: (Int) -> Void
    let onNavigateSubtitleWord: (Int) -> Void
    let onNavigateSubtitleTrack: (Int) -> Bool
    let onSubtitleLookup: () -> Void
    let onSubtitleTokenLookup: (VideoSubtitleTokenReference) -> Void
    let onSubtitleTokenSeek: (VideoSubtitleTokenReference) -> Void
    let onUpdateSubtitleSelectionRange: (VideoSubtitleWordSelectionRange, VideoSubtitleWordSelection) -> Void
    let onSubtitleInteractionFrameChange: (CGRect) -> Void
    let onToggleTransliteration: () -> Void
    let onLookupLanguageChange: (String) -> Void
    let onLlmModelChange: (String) -> Void
    let onIncreaseSubtitleLinguistFont: () -> Void
    let onDecreaseSubtitleLinguistFont: () -> Void
    let onPlayFromNarration: (() -> Void)?
    let onReadAloud: (() -> Void)?
    let onSelectSegment: ((String) -> Void)?
    let onCloseSubtitleBubble: () -> Void
    let onUserInteraction: () -> Void

    // MARK: - Private State
    @AppStorage("player.headerScale") private var headerScaleValue: Double = 1.0

    #if !os(tvOS)
    @Environment(\.dismiss) private var dismiss
    @AppStorage("video.subtitle.verticalOffset") var subtitleVerticalOffsetValue: Double = 0
    @State var subtitleDragTranslation: CGFloat = 0
    var subtitleBottomPadding: CGFloat {
        VideoPlayerPlatform.isPad ? 36 : 72
    }
    #endif

    #if os(iOS)
    @State var subtitleTokenFrames: [VideoSubtitleTokenFrame] = []
    @State var dragSelectionAnchor: VideoSubtitleWordSelection?
    @State var dragLookupTask: Task<Void, Never>?
    let dragLookupDelayNanos: UInt64 = 350_000_000
    #endif

    #if os(tvOS)
    @FocusState var focusTarget: VideoPlayerFocusTarget?
    @State var pendingSkipTask: Task<Void, Never>?
    @State var pendingSkipDirection: MoveCommandDirection?
    @State var suppressControlFocus = false
    @State var suppressFocusTask: Task<Void, Never>?
    #endif

    // MARK: - Body

    var body: some View {
        overlayContent
    }

    // MARK: - Main Content

    private var overlayContent: some View {
        Group {
            #if os(tvOS)
            ZStack(alignment: .top) {
                tvOverlay
                // Hide header when lookup bubble is active to reduce visual clutter
                if subtitleBubble == nil {
                    tvInfoHeaderOverlay
                }
                if showSubtitleSettings {
                    subtitleSettingsOverlay
                }
            }
            #else
            ZStack {
                iosOverlay
                if showSubtitleSettings {
                    subtitleSettingsOverlay
                }
            }
            #endif
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .animation(.easeInOut(duration: 0.2), value: showSubtitleSettings)
        .coordinateSpace(name: VideoSubtitleTokenCoordinateSpace.name)
        #if os(tvOS)
        .onAppear { handleTVAppear() }
        .onChange(of: showSubtitleSettings) { _, isVisible in handleTVSettingsChange(isVisible) }
        .onChange(of: showTVControls) { _, isVisible in handleTVControlsChange(isVisible) }
        .onChange(of: isPlaying) { _, playing in handleTVPlayingChange(playing) }
        #endif
    }

    var videoScrubberRange: ClosedRange<Double>? {
        guard duration.isFinite, duration > 0 else { return nil }
        return 0...duration
    }

    var videoScrubberLabel: String {
        guard let range = videoScrubberRange else { return "" }
        let value = isScrubbing ? scrubberValue : currentTime
        let clamped = min(max(value, range.lowerBound), range.upperBound)
        let played = VideoPlayerTimeFormatter.formatDuration(clamped)
        let remaining = VideoPlayerTimeFormatter.formatDuration(max(range.upperBound - clamped, 0))
        return "\(played) / \(remaining)"
    }

    // MARK: - iOS Overlay

    #if !os(tvOS)
    private var iosOverlay: some View {
        ZStack {
            VStack {
                // Hide header when lookup bubble is active to maximize space for definition
                if subtitleBubble == nil {
                    topBar
                        .transition(.opacity)
                }
                Spacer()
                subtitleStack
            }
            .animation(.easeInOut(duration: 0.2), value: subtitleBubble != nil)
            subtitleBubbleOverlay
        }
    }

    private var topBar: some View {
        VideoPlayerHeaderView(
            metadata: metadata,
            isCollapsed: isHeaderCollapsed,
            headerTopInset: headerTopInset,
            headerScaleValue: headerScaleValue,
            currentTime: currentTime,
            duration: duration,
            segmentOptions: segmentOptions,
            selectedSegmentID: selectedSegmentID,
            jobProgressLabel: jobProgressLabel,
            jobRemainingLabel: jobRemainingLabel,
            tracks: tracks,
            selectedTrack: selectedTrack,
            playbackRate: playbackRate,
            playbackRateOptions: playbackRateOptions,
            bookmarks: bookmarks,
            isPlaying: isPlaying,
            searchPill: searchPill,
            sleepTimerPill: sleepTimerPill,
            showBookmarkRibbonPill: true,
            showTimelinePill: false,
            onToggleHeaderCollapsed: onToggleHeaderCollapsed,
            onShowSubtitleSettings: handleShowSubtitleSettings,
            onPlaybackRateChange: onPlaybackRateChange,
            onAddBookmark: onAddBookmark,
            onJumpToBookmark: onJumpToBookmark,
            onRemoveBookmark: onRemoveBookmark,
            onUserInteraction: onUserInteraction,
            onDismiss: { dismiss() }
        )
    }
    #endif

    // MARK: - Subtitle Stack (shared iOS/tvOS)

    @ViewBuilder
    var subtitleStack: some View {
        #if os(iOS)
        let shouldReportTokenFramesLocal = VideoPlayerPlatform.isPad
        let tokenFramesHandler: (([VideoSubtitleTokenFrame]) -> Void)? = shouldReportTokenFramesLocal
            ? { subtitleTokenFrames = $0 }
            : nil
        #else
        let shouldReportTokenFramesLocal = false
        let tokenFramesHandler: (([VideoSubtitleTokenFrame]) -> Void)? = nil
        #endif

        let stack = VStack(alignment: subtitleAlignment, spacing: 6) {
            if includeBubbleInSubtitleStack, let subtitleBubble {
                subtitleBubbleContent(subtitleBubble)
                    .padding(.bottom, 6)
                    #if os(tvOS)
                    .focusSection()
                    .focused($focusTarget, equals: .bubble)
                    .onMoveCommand(perform: handleBubbleMoveCommand)
                    #endif
            }
            SubtitleOverlayView(
                cues: cues,
                currentTime: currentTime,
                isPlaying: isPlaying,
                visibility: subtitleVisibility,
                fontScale: subtitleFontScale,
                selection: subtitleSelection,
                selectionRange: subtitleSelectionRange,
                lineAlignment: subtitleAlignment,
                onTokenLookup: onSubtitleTokenLookup,
                onTokenSeek: onSubtitleTokenSeek,
                onTokenFramesChange: tokenFramesHandler,
                shouldReportTokenFrames: shouldReportTokenFramesLocal,
                onResetFont: onResetSubtitleFont,
                onMagnify: onSetSubtitleFont
            )
        }

        let alignedStack = alignedSubtitleStack(stack)

        #if os(iOS)
        alignedStack
            .padding(.bottom, subtitleBottomPadding)
            .contentShape(Rectangle())
            .offset(subtitleDragOffset)
            .simultaneousGesture(subtitleDragGesture, including: .gesture)
            .simultaneousGesture(subtitleSelectionDragGesture, including: .gesture)
            .onChange(of: isPlaying) { _, playing in handleSubtitlePlaybackChange(playing) }
            .onDisappear(perform: resetSubtitleSelectionDrag)
            .onChange(of: subtitleTokenFrames) { _, newFrames in handleSubtitleTokenFramesChange(newFrames) }
        #elseif os(tvOS)
        alignedStack
            .contentShape(Rectangle())
            .focusable(!showSubtitleSettings)
            .focused($focusTarget, equals: .subtitles)
            .focusSection()
            .focusEffectDisabled()
            .onLongPressGesture(minimumDuration: 0.6) { onToggleHeaderCollapsed() }
            .onMoveCommand { direction in handleSubtitleMoveCommand(direction) }
            .onTapGesture { handleSubtitleTap() }
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

    // MARK: - Subtitle Bubble

    @ViewBuilder
    private func subtitleBubbleContent(_ subtitleBubble: VideoLinguistBubbleState) -> some View {
        #if os(tvOS)
        VideoLinguistBubbleView(
            bubble: subtitleBubble,
            fontScale: subtitleLinguistFontScale,
            canIncreaseFont: canIncreaseSubtitleLinguistFont,
            canDecreaseFont: canDecreaseSubtitleLinguistFont,
            lookupLanguage: lookupLanguage,
            isFocusEnabled: focusTarget == .bubble,
            onBubbleFocus: { focusTarget = .bubble },
            lookupLanguageOptions: lookupLanguageOptions,
            onLookupLanguageChange: onLookupLanguageChange,
            llmModel: llmModel,
            llmModelOptions: llmModelOptions,
            onLlmModelChange: onLlmModelChange,
            onIncreaseFont: onIncreaseSubtitleLinguistFont,
            onDecreaseFont: onDecreaseSubtitleLinguistFont,
            onResetFont: onResetSubtitleBubbleFont,
            onClose: onCloseSubtitleBubble,
            onMagnify: onSetSubtitleBubbleFont,
            onPlayFromNarration: onPlayFromNarration,
            onReadAloud: onReadAloud,
            onPreviousToken: { onNavigateSubtitleWord(-1) },
            onNextToken: { onNavigateSubtitleWord(1) }
        )
        #else
        VideoLinguistBubbleView(
            bubble: subtitleBubble,
            fontScale: subtitleLinguistFontScale,
            canIncreaseFont: canIncreaseSubtitleLinguistFont,
            canDecreaseFont: canDecreaseSubtitleLinguistFont,
            lookupLanguage: lookupLanguage,
            lookupLanguageOptions: lookupLanguageOptions,
            onLookupLanguageChange: onLookupLanguageChange,
            llmModel: llmModel,
            llmModelOptions: llmModelOptions,
            onLlmModelChange: onLlmModelChange,
            onIncreaseFont: onIncreaseSubtitleLinguistFont,
            onDecreaseFont: onDecreaseSubtitleLinguistFont,
            onResetFont: onResetSubtitleBubbleFont,
            onClose: onCloseSubtitleBubble,
            onMagnify: onSetSubtitleBubbleFont,
            onPlayFromNarration: onPlayFromNarration,
            onReadAloud: onReadAloud,
            onPreviousToken: { onNavigateSubtitleWord(-1) },
            onNextToken: { onNavigateSubtitleWord(1) }
        )
        #endif
    }

    @ViewBuilder
    private var subtitleBubbleOverlay: some View {
        #if os(iOS)
        if shouldOverlayBubbleOnPhone, let subtitleBubble {
            ZStack {
                Color.clear
                    .contentShape(Rectangle())
                    .onTapGesture(perform: handleSubtitleBubbleBackdropTap)
                GeometryReader { proxy in
                    subtitleBubbleContent(subtitleBubble)
                        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
                        .position(x: proxy.size.width * 0.5, y: proxy.size.height * 0.5)
                }
            }
            .ignoresSafeArea()
            .zIndex(1)
        }
        #else
        EmptyView()
        #endif
    }

    // MARK: - Subtitle Settings Panel

    @ViewBuilder
    private var subtitleSettingsOverlay: some View {
        Color.black.opacity(0.55)
            .ignoresSafeArea()
            .onTapGesture(perform: handleCloseSubtitleSettings)
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
                onClose: handleCloseSubtitleSettings
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
            onClose: handleCloseSubtitleSettings
        )
        .padding(.horizontal, 24)
        .transition(.opacity)
        #endif
    }

    // MARK: - Helpers

    @ViewBuilder
    private func alignedSubtitleStack<Content: View>(_ stack: Content) -> some View {
        if let subtitleMaxWidth {
            stack
                .frame(maxWidth: subtitleMaxWidth, alignment: subtitleFrameAlignment)
                .padding(.leading, subtitleLeadingInset)
                .frame(maxWidth: .infinity, alignment: .leading)
        } else {
            stack
        }
    }

    private var subtitleFrameAlignment: Alignment {
        switch subtitleAlignment {
        case .leading: return .leading
        case .trailing: return .trailing
        default: return .center
        }
    }

    private var includeBubbleInSubtitleStack: Bool {
        !shouldOverlayBubbleOnPhone
    }

    private var shouldOverlayBubbleOnPhone: Bool {
        VideoPlayerPlatform.isPhone
    }

    private func handleShowSubtitleSettings() {
        showSubtitleSettings = true
    }

    private func handleCloseSubtitleSettings() {
        showSubtitleSettings = false
    }

    #if os(iOS)
    private func handleSubtitlePlaybackChange(_ playing: Bool) {
        if playing {
            resetSubtitleSelectionDrag()
        }
    }

    private func handleSubtitleTokenFramesChange(_ frames: [VideoSubtitleTokenFrame]) {
        onSubtitleInteractionFrameChange(resolveSubtitleInteractionFrame(from: frames))
    }

    private func handleSubtitleBubbleBackdropTap() {
        onCloseSubtitleBubble()
        if !isPlaying {
            onPlayPause()
        }
    }
    #endif
}
