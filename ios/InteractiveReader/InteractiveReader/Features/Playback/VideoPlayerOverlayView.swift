import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

/// Video player overlay view using modular components.
/// Orchestrates header, subtitles, controls, and settings overlays.
struct VideoPlayerOverlayView<SearchPill: View>: View {
    // MARK: - Playback State
    let cues: [VideoSubtitleCue]
    let currentTime: Double
    let duration: Double
    let isPlaying: Bool
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

    // MARK: - TV Controls
    @Binding var showTVControls: Bool
    @Binding var scrubberValue: Double
    @Binding var isScrubbing: Bool

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
    let onSkipForward: () -> Void
    let onSkipBackward: () -> Void
    let onSeek: (Double) -> Void
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
    let onSelectSegment: ((String) -> Void)?
    let onCloseSubtitleBubble: () -> Void
    let onUserInteraction: () -> Void

    // MARK: - Private State
    @AppStorage("player.headerScale") private var headerScaleValue: Double = 1.0

    #if !os(tvOS)
    @Environment(\.dismiss) private var dismiss
    @AppStorage("video.subtitle.verticalOffset") private var subtitleVerticalOffsetValue: Double = 0
    @State private var subtitleDragTranslation: CGFloat = 0
    private var subtitleBottomPadding: CGFloat {
        VideoPlayerPlatform.isPad ? 36 : 72
    }
    #endif

    #if os(iOS)
    @State private var subtitleTokenFrames: [VideoSubtitleTokenFrame] = []
    @State private var dragSelectionAnchor: VideoSubtitleWordSelection?
    @State private var dragLookupTask: Task<Void, Never>?
    private let dragLookupDelayNanos: UInt64 = 350_000_000
    #endif

    #if os(tvOS)
    @FocusState private var focusTarget: VideoPlayerFocusTarget?
    @State private var pendingSkipTask: Task<Void, Never>?
    @State private var pendingSkipDirection: MoveCommandDirection?
    @State private var suppressControlFocus = false
    @State private var suppressFocusTask: Task<Void, Never>?
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
            showBookmarkRibbonPill: true,
            onToggleHeaderCollapsed: onToggleHeaderCollapsed,
            onShowSubtitleSettings: { showSubtitleSettings = true },
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
    private var subtitleStack: some View {
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
                    .onMoveCommand { direction in
                        handleBubbleMoveCommand(direction)
                    }
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
            .onChange(of: isPlaying) { _, playing in
                if playing { resetSubtitleSelectionDrag() }
            }
            .onDisappear { resetSubtitleSelectionDrag() }
            .onChange(of: subtitleTokenFrames) { _, newFrames in
                onSubtitleInteractionFrameChange(resolveSubtitleInteractionFrame(from: newFrames))
            }
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
            onMagnify: onSetSubtitleBubbleFont
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
            onMagnify: onSetSubtitleBubbleFont
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
                    .onTapGesture {
                        onCloseSubtitleBubble()
                        if !isPlaying { onPlayPause() }
                    }
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
            .onTapGesture { showSubtitleSettings = false }
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
}

// MARK: - iOS Gestures

#if os(iOS)
extension VideoPlayerOverlayView {
    private var subtitleDragOffset: CGSize {
        let rawHeight = subtitleVerticalOffset + subtitleDragTranslation
        let maxHeight = allowSubtitleDownwardDrag ? subtitleBottomPadding : 0
        let clampedHeight = min(rawHeight, maxHeight)
        return CGSize(width: 0, height: clampedHeight)
    }

    private var subtitleVerticalOffset: CGFloat {
        get { CGFloat(subtitleVerticalOffsetValue) }
        nonmutating set { subtitleVerticalOffsetValue = Double(newValue) }
    }

    private var subtitleDragGesture: some Gesture {
        DragGesture(minimumDistance: 10, coordinateSpace: .local)
            .onChanged { value in
                guard abs(value.translation.height) >= abs(value.translation.width) else { return }
                subtitleDragTranslation = value.translation.height
            }
            .onEnded { value in
                guard abs(value.translation.height) >= abs(value.translation.width) else {
                    subtitleDragTranslation = 0
                    return
                }
                let proposedHeight = subtitleVerticalOffset + value.translation.height
                let maxHeight = allowSubtitleDownwardDrag ? subtitleBottomPadding : 0
                subtitleVerticalOffset = min(proposedHeight, maxHeight)
                subtitleDragTranslation = 0
            }
    }

    private var subtitleSelectionDragGesture: some Gesture {
        DragGesture(minimumDistance: 8, coordinateSpace: .named(VideoSubtitleTokenCoordinateSpace.name))
            .onChanged { value in
                guard VideoPlayerPlatform.isPad else { return }
                guard !isPlaying else { return }
                if dragSelectionAnchor == nil {
                    guard let anchorToken = tokenFrameContaining(value.startLocation) else { return }
                    dragSelectionAnchor = VideoSubtitleWordSelection(
                        lineKind: anchorToken.lineKind,
                        lineIndex: anchorToken.lineIndex,
                        tokenIndex: anchorToken.tokenIndex
                    )
                }
                updateSubtitleSelectionRange(at: value.location)
            }
            .onEnded { _ in
                dragSelectionAnchor = nil
            }
    }

    private func updateSubtitleSelectionRange(at location: CGPoint) {
        guard let anchor = dragSelectionAnchor else { return }
        guard let token = nearestTokenFrame(at: location) else { return }
        let selection = VideoSubtitleWordSelection(
            lineKind: token.lineKind,
            lineIndex: token.lineIndex,
            tokenIndex: token.tokenIndex
        )
        guard anchor.lineKind == selection.lineKind,
              anchor.lineIndex == selection.lineIndex else { return }
        let range = VideoSubtitleWordSelectionRange(
            lineKind: anchor.lineKind,
            lineIndex: anchor.lineIndex,
            anchorIndex: anchor.tokenIndex,
            focusIndex: selection.tokenIndex
        )
        onUpdateSubtitleSelectionRange(range, selection)
        scheduleSubtitleDragLookup()
    }

    private func nearestTokenFrame(at location: CGPoint) -> VideoSubtitleTokenFrame? {
        let candidates: [VideoSubtitleTokenFrame]
        if let anchor = dragSelectionAnchor {
            candidates = subtitleTokenFrames.filter {
                $0.lineKind == anchor.lineKind && $0.lineIndex == anchor.lineIndex
            }
        } else {
            candidates = subtitleTokenFrames
        }
        guard !candidates.isEmpty else { return nil }
        if let exact = candidates.first(where: { $0.frame.contains(location) }) {
            return exact
        }
        let sorted = candidates.sorted { lhs, rhs in
            let lhsCenter = CGPoint(x: lhs.frame.midX, y: lhs.frame.midY)
            let rhsCenter = CGPoint(x: rhs.frame.midX, y: rhs.frame.midY)
            let lhsDistance = hypot(lhsCenter.x - location.x, lhsCenter.y - location.y)
            let rhsDistance = hypot(rhsCenter.x - location.x, rhsCenter.y - location.y)
            return lhsDistance < rhsDistance
        }
        return sorted.first
    }

    private func tokenFrameContaining(_ location: CGPoint) -> VideoSubtitleTokenFrame? {
        subtitleTokenFrames.first(where: { $0.frame.contains(location) })
    }

    private func scheduleSubtitleDragLookup() {
        dragLookupTask?.cancel()
        dragLookupTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: dragLookupDelayNanos)
            guard !Task.isCancelled else { return }
            guard !isPlaying else { return }
            onSubtitleLookup()
        }
    }

    private func resetSubtitleSelectionDrag() {
        dragSelectionAnchor = nil
        dragLookupTask?.cancel()
        dragLookupTask = nil
    }

    private func resolveSubtitleInteractionFrame(from frames: [VideoSubtitleTokenFrame]) -> CGRect {
        guard !frames.isEmpty else { return .null }
        let union = frames.reduce(CGRect.null) { result, frame in
            result.union(frame.frame)
        }
        guard !union.isNull else { return union }
        return union.insetBy(dx: -8, dy: -8)
    }
}
#endif

// MARK: - tvOS Support

#if os(tvOS)
extension VideoPlayerOverlayView {
    private var tvOverlay: some View {
        VStack(spacing: 16) {
            Spacer()
            subtitleStack
            // Use frame with zero height when hidden to collapse the space
            tvBottomBar
                .frame(height: showTVControls ? nil : 0, alignment: .top)
                .opacity(showTVControls ? 1 : 0)
                .allowsHitTesting(showTVControls)
                .clipped()
                .transaction { transaction in
                    // Disable animations for playback-driven updates to prevent flicker
                    if !showTVControls {
                        transaction.disablesAnimations = true
                    }
                }
        }
        .padding(.horizontal, 60)
        .padding(.bottom, showTVControls ? 36 : 24)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottom)
        .onPlayPauseCommand {
            // When paused and controls are hidden, tap triggers lookup on current word
            // This allows single-tap lookup without needing focus to be exactly on subtitles
            if !isPlaying && !showTVControls && subtitleBubble == nil {
                onSubtitleLookup()
            } else {
                onPlayPause()
                onUserInteraction()
            }
        }
    }

    @ViewBuilder
    private var tvInfoHeaderOverlay: some View {
        let showHeaderContent = !isHeaderCollapsed
        let timelineLabel = videoTimelineLabel
        let segmentLabel = segmentHeaderLabel

        if isHeaderCollapsed {
            // Collapsed: show only the timeline pill (like iOS)
            tvCollapsedHeaderPill(timelineLabel: timelineLabel)
        } else {
            // Expanded: show full header with background
            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .top, spacing: 12) {
                    tvInfoHeaderContent
                    Spacer(minLength: 12)
                    VStack(alignment: .trailing, spacing: 6) {
                        if let segmentLabel {
                            tvTimelinePillButton(label: segmentLabel)
                        }
                        if let timelineLabel {
                            tvTimelinePillButton(label: timelineLabel)
                        }
                    }
                    .focusSection()
                }
                tvSummaryTickerView
            }
            .padding(.top, 6)
            .padding(.horizontal, 6)
            .background(
                VideoPlayerOverlayStyles.headerBackgroundGradient,
                in: RoundedRectangle(cornerRadius: VideoPlayerOverlayStyles.headerBackgroundCornerRadius)
            )
            .overlay(
                RoundedRectangle(cornerRadius: VideoPlayerOverlayStyles.headerBackgroundCornerRadius)
                    .stroke(Color.white.opacity(0.12), lineWidth: 1)
            )
            .frame(maxWidth: .infinity, alignment: .topLeading)
            .onLongPressGesture(minimumDuration: 0.6) {
                onToggleHeaderCollapsed()
            }
        }
    }

    @ViewBuilder
    private func tvCollapsedHeaderPill(timelineLabel: String?) -> some View {
        if let timelineLabel {
            tvTimelinePillButton(label: timelineLabel)
                .frame(maxWidth: .infinity, alignment: .topTrailing)
                .padding(.top, 6)
                .padding(.trailing, 6)
                .onLongPressGesture(minimumDuration: 0.6) {
                    onToggleHeaderCollapsed()
                }
        }
    }

    private func tvTimelinePillButton(label: String) -> some View {
        Button(action: onToggleHeaderCollapsed) {
            Text(label)
                .font(.callout.weight(.semibold))
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
        .buttonStyle(TVTimelinePillButtonStyle())
        .focused($focusTarget, equals: .control(.header))
        .onMoveCommand { direction in
            guard focusTarget == .control(.header) else { return }
            switch direction {
            case .down:
                if subtitleBubble != nil {
                    focusTarget = .bubble
                } else {
                    focusTarget = .subtitles
                }
            case .left:
                // Navigate left to bookmark ribbon pill if available
                if onAddBookmark != nil {
                    focusTarget = .control(.headerBookmark)
                }
            default:
                break
            }
        }
    }

    private var tvInfoHeaderContent: some View {
        HStack(alignment: .top, spacing: 12) {
            PlayerChannelBugView(
                variant: metadata.channelVariant,
                label: metadata.channelLabel,
                sizeScale: 1.0
            )
            if hasInfoBadge {
                tvInfoBadgeView
            }
        }
    }

    private var tvInfoBadgeView: some View {
        HStack(alignment: .top, spacing: 8) {
            if metadata.artworkURL != nil || metadata.secondaryArtworkURL != nil {
                PlayerCoverStackView(
                    primaryURL: metadata.artworkURL,
                    secondaryURL: metadata.secondaryArtworkURL,
                    width: VideoPlayerOverlayMetrics.coverWidth(isTV: true),
                    height: VideoPlayerOverlayMetrics.coverHeight(isTV: true),
                    isTV: true
                )
            }
            VStack(alignment: .leading, spacing: 2) {
                if !metadata.title.isEmpty {
                    Text(metadata.title)
                        .font(.headline)
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                        .foregroundStyle(.white)
                }
                if let subtitle = metadata.subtitle, !subtitle.isEmpty {
                    Text(subtitle)
                        .font(.callout)
                        .foregroundStyle(Color.white.opacity(0.75))
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                }
                if !metadata.languageFlags.isEmpty || searchPill != nil || onAddBookmark != nil {
                    HStack(spacing: 8) {
                        if !metadata.languageFlags.isEmpty {
                            PlayerLanguageFlagRow(
                                flags: metadata.languageFlags,
                                modelLabel: metadata.translationModel,
                                isTV: true,
                                sizeScale: 1.0
                            )
                        }
                        if let searchPill {
                            searchPill
                        }
                        if onAddBookmark != nil {
                            tvBookmarkRibbonPill
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var tvSummaryTickerView: some View {
        if !isHeaderCollapsed,
           !isPlaying,
           let summary = metadata.summary?.nonEmptyValue {
            SummaryTickerPill(text: summary, isTV: true)
        }
    }

    private var tvBookmarkRibbonPill: some View {
        BookmarkRibbonPillView(
            bookmarkCount: bookmarks.count,
            isTV: true,
            sizeScale: 1.0,
            bookmarks: bookmarks,
            onAddBookmark: onAddBookmark,
            onJumpToBookmark: onJumpToBookmark,
            onRemoveBookmark: onRemoveBookmark,
            onUserInteraction: onUserInteraction,
            focusTarget: $focusTarget,
            onMoveRight: { focusTarget = .control(.header) }
        )
    }

    private var tvBottomBar: some View {
        TVPlaybackControlsBar(
            isPlaying: isPlaying,
            showTVControls: showTVControls,
            showSubtitleSettings: showSubtitleSettings,
            suppressControlFocus: suppressControlFocus,
            hasOptions: hasOptions,
            canShowBookmarks: onAddBookmark != nil,
            duration: duration,
            displayTime: displayTime,
            scrubberValue: $scrubberValue,
            focusTarget: $focusTarget,
            onPlayPause: onPlayPause,
            onSkipBackward: onSkipBackward,
            onSkipForward: onSkipForward,
            onSeek: onSeek,
            onEditingChanged: { editing in
                isScrubbing = editing
                onUserInteraction()
            },
            onUserInteraction: onUserInteraction,
            onShowSubtitleSettings: { showSubtitleSettings = true },
            bookmarkMenu: onAddBookmark != nil ? AnyView(
                VideoPlayerBookmarkMenu(
                    bookmarks: bookmarks,
                    onAddBookmark: onAddBookmark,
                    onJumpToBookmark: onJumpToBookmark,
                    onRemoveBookmark: onRemoveBookmark,
                    onUserInteraction: onUserInteraction,
                    isFocused: focusTarget == .control(.bookmark),
                    isDisabled: !controlsFocusEnabled
                )
            ) : nil,
            speedMenu: AnyView(
                VideoPlayerSpeedMenu(
                    playbackRate: playbackRate,
                    playbackRateOptions: playbackRateOptions,
                    onPlaybackRateChange: onPlaybackRateChange,
                    onUserInteraction: onUserInteraction,
                    isFocused: focusTarget == .control(.speed),
                    isDisabled: !controlsFocusEnabled
                )
            )
        )
    }

    private var displayTime: Double {
        isScrubbing ? scrubberValue : currentTime
    }

    private var controlsFocusEnabled: Bool {
        showTVControls && !showSubtitleSettings && !suppressControlFocus
    }

    // MARK: - tvOS Focus Handlers

    private func handleTVAppear() {
        if showTVControls {
            focusTarget = .control(.playPause)
        } else {
            // Keep focus on subtitles whether playing or paused, so single-tap
            // can trigger lookup immediately without first acquiring focus.
            focusTarget = .subtitles
        }
    }

    private func handleTVSettingsChange(_ isVisible: Bool) {
        if isVisible {
            focusTarget = nil
        } else if showTVControls {
            focusTarget = .control(.playPause)
        } else {
            // Keep focus on subtitles whether playing or paused for single-tap lookup.
            focusTarget = .subtitles
        }
    }

    private func handleTVControlsChange(_ isVisible: Bool) {
        if isVisible {
            focusTarget = .control(.playPause)
        } else {
            // Keep focus on subtitles whether playing or paused for single-tap lookup.
            focusTarget = .subtitles
        }
    }

    private func handleTVPlayingChange(_ playing: Bool) {
        if playing {
            // Hide controls during playback to maximize screen real estate
            showTVControls = false
            focusTarget = .subtitles
        } else if showTVControls {
            focusTarget = .control(.playPause)
        } else {
            // Keep focus on subtitles when paused so single-tap triggers lookup.
            focusTarget = .subtitles
        }
    }

    private func handleBubbleMoveCommand(_ direction: MoveCommandDirection) {
        guard focusTarget == .bubble else { return }
        switch direction {
        case .up:
            focusTarget = .control(.header)
        case .down:
            focusTarget = .subtitles
        default:
            break
        }
    }

    private func handleSubtitleMoveCommand(_ direction: MoveCommandDirection) {
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
                // During playback, ignore up swipe to keep screen real estate maximized
                return
            } else {
                let moved = onNavigateSubtitleTrack(-1)
                if moved {
                    suppressControlFocusTemporarily()
                    focusTarget = .subtitles
                } else if subtitleBubble != nil {
                    suppressControlFocus = false
                    focusTarget = .bubble
                } else {
                    suppressControlFocus = false
                    focusTarget = .control(.header)
                }
            }
        case .down:
            if isPlaying { return }
            let moved = onNavigateSubtitleTrack(1)
            if moved {
                suppressControlFocusTemporarily()
                focusTarget = .subtitles
            } else {
                suppressControlFocus = false
                if subtitleBubble != nil {
                    focusTarget = .bubble
                } else {
                    showTVControls = true
                    focusTarget = .control(.playPause)
                }
            }
        default:
            break
        }
    }

    private func handleSubtitleTap() {
        guard focusTarget != .bubble else { return }
        if isPlaying {
            onUserInteraction()
        } else {
            onSubtitleLookup()
        }
    }

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

    private func suppressControlFocusTemporarily() {
        suppressFocusTask?.cancel()
        suppressControlFocus = true
        suppressFocusTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 150_000_000)
            suppressControlFocus = false
        }
    }
}
#endif

// MARK: - Computed Properties

extension VideoPlayerOverlayView {
    private var videoTimelineLabel: String? {
        guard duration.isFinite, duration > 0, currentTime.isFinite else { return nil }
        let played = min(max(currentTime, 0), duration)
        let remaining = max(duration - played, 0)
        // Unified compact format: time / remaining
        let base = "\(VideoPlayerTimeFormatter.formatDuration(played)) / \(VideoPlayerTimeFormatter.formatDuration(remaining))"
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
                // Unified compact format: C:current/total
                chunkLabel = "C:\(index + 1)/\(segmentOptions.count)"
            } else {
                chunkLabel = "C:1/\(segmentOptions.count)"
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

    private var hasOptions: Bool {
        !tracks.isEmpty || segmentOptions.count > 1
    }

    private var hasInfoBadge: Bool {
        !metadata.title.isEmpty || (metadata.subtitle?.isEmpty == false) || metadata.artworkURL != nil
    }
}

// MARK: - tvOS Button Style

#if os(tvOS)
struct TVTimelinePillButtonStyle: ButtonStyle {
    @Environment(\.isFocused) var isFocused

    func makeBody(configuration: Configuration) -> some View {
        let scale: CGFloat = configuration.isPressed ? 0.95 : (isFocused ? 1.05 : 1.0)
        let brightness: Double = isFocused ? 0.1 : 0

        configuration.label
            .scaleEffect(scale)
            .brightness(brightness)
    }
}
#endif
