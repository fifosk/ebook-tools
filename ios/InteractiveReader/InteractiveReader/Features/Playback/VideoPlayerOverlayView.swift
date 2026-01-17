import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

struct VideoPlayerOverlayView: View {
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
    let bookmarks: [PlaybackBookmarkEntry]
    let onAddBookmark: (() -> Void)?
    let onJumpToBookmark: (PlaybackBookmarkEntry) -> Void
    let onRemoveBookmark: (PlaybackBookmarkEntry) -> Void
    let subtitleFontScale: CGFloat
    let isPlaying: Bool
    let subtitleSelection: VideoSubtitleWordSelection?
    let subtitleBubble: VideoLinguistBubbleState?
    let subtitleAlignment: HorizontalAlignment
    let subtitleMaxWidth: CGFloat?
    let subtitleLeadingInset: CGFloat
    let headerTopInset: CGFloat
    let allowSubtitleDownwardDrag: Bool
    let lookupLanguage: String
    let lookupLanguageOptions: [String]
    let onLookupLanguageChange: (String) -> Void
    let llmModel: String
    let llmModelOptions: [String]
    let onLlmModelChange: (String) -> Void
    let subtitleLinguistFontScale: CGFloat
    let canIncreaseSubtitleLinguistFont: Bool
    let canDecreaseSubtitleLinguistFont: Bool
    let isHeaderCollapsed: Bool
    let playbackRate: Double
    let playbackRateOptions: [Double]
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
    let onToggleTransliteration: () -> Void
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
    @State private var suppressControlFocus = false
    @State private var suppressFocusTask: Task<Void, Never>?
    #endif
    var body: some View {
        overlayContent
    }

    private var overlayContent: some View {
        Group {
            #if os(tvOS)
            ZStack(alignment: .top) {
                tvOverlay
                infoHeaderOverlay
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

    private var canShowBookmarks: Bool {
        onAddBookmark != nil
    }

    @ViewBuilder
    private var bookmarkMenu: some View {
        if canShowBookmarks {
            Menu {
                bookmarkMenuContent
            } label: {
                bookmarkMenuLabel
            }
            #if os(tvOS)
            .focused($focusTarget, equals: .control(.bookmark))
            .disabled(!controlsFocusEnabled)
            #endif
        }
    }

    @ViewBuilder
    private var speedMenu: some View {
        Menu {
            ForEach(playbackRateOptions, id: \.self) { rate in
                Button {
                    onPlaybackRateChange(rate)
                    onUserInteraction()
                } label: {
                    if isCurrentRate(rate) {
                        Label(playbackRateLabel(rate), systemImage: "checkmark")
                    } else {
                        Text(playbackRateLabel(rate))
                    }
                }
            }
        } label: {
            speedMenuLabel
        }
        #if os(tvOS)
        .focused($focusTarget, equals: .control(.speed))
        .disabled(!controlsFocusEnabled)
        #endif
    }

    @ViewBuilder
    private var bookmarkMenuContent: some View {
        Button("Add Bookmark") {
            onAddBookmark?()
            onUserInteraction()
        }
        if bookmarks.isEmpty {
            Text("No bookmarks yet.")
                .foregroundStyle(.secondary)
        } else {
            Section("Jump") {
                ForEach(bookmarks) { bookmark in
                    Button(bookmark.label) {
                        onJumpToBookmark(bookmark)
                        onUserInteraction()
                    }
                }
            }
            Section("Remove") {
                ForEach(bookmarks) { bookmark in
                    Button(role: .destructive) {
                        onRemoveBookmark(bookmark)
                        onUserInteraction()
                    } label: {
                        Text(bookmark.label)
                    }
                }
            }
        }
    }

    private var bookmarkMenuLabel: some View {
        #if os(tvOS)
        tvControlLabel(
            systemName: "bookmark",
            label: "Bookmarks",
            font: .callout.weight(.semibold),
            isFocused: focusTarget == .control(.bookmark)
        )
        #else
        Label("Bookmarks", systemImage: "bookmark")
            .labelStyle(.titleAndIcon)
            .font(.caption)
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(.black.opacity(0.45), in: RoundedRectangle(cornerRadius: 8))
            .foregroundStyle(.white)
        #endif
    }

    private var iosOverlay: some View {
        ZStack {
            VStack {
                topBar
                Spacer()
                subtitleStack
            }
            subtitleBubbleOverlay
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
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottom)
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
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottom)
            .onPlayPauseCommand {
                onPlayPause()
                onUserInteraction()
            }
        }
    }
    #endif

    @ViewBuilder
    private var subtitleStack: some View {
        let stack = VStack(alignment: subtitleAlignment, spacing: 6) {
            if includeBubbleInSubtitleStack, let subtitleBubble {
                subtitleBubbleContent(subtitleBubble)
                    .padding(.bottom, 6)
                    #if os(tvOS)
                    .focusSection()
                    .focused($focusTarget, equals: .bubble)
                    .onMoveCommand { direction in
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
                    #endif
            }
            SubtitleOverlayView(
                cues: cues,
                currentTime: currentTime,
                isPlaying: isPlaying,
                visibility: subtitleVisibility,
                fontScale: subtitleFontScale,
                selection: subtitleSelection,
                lineAlignment: subtitleAlignment,
                onTokenLookup: onSubtitleTokenLookup,
                onTokenSeek: onSubtitleTokenSeek,
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
        #elseif os(tvOS)
        alignedStack
            .contentShape(Rectangle())
            .focusable(!showSubtitleSettings)
            .focused($focusTarget, equals: .subtitles)
            .focusSection()
            .focusEffectDisabled()
            .onLongPressGesture(minimumDuration: 0.6) {
                onToggleTransliteration()
            }
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
                    if isPlaying {
                        return
                    }
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
            .onTapGesture {
                guard focusTarget != .bubble else { return }
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
    private var subtitleBubbleOverlay: some View {
        #if os(iOS)
        if shouldOverlayBubbleOnPhone, let subtitleBubble {
            ZStack {
                Color.clear
                    .contentShape(Rectangle())
                    .onTapGesture {
                        onCloseSubtitleBubble()
                        if !isPlaying {
                            onPlayPause()
                        }
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
            onBubbleFocus: {
                focusTarget = .bubble
            },
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
        Group {
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
                            if canShowBookmarks {
                                bookmarkMenu
                            }
                            speedMenu
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
                    if shouldShowHeaderInfo {
                        summaryTickerView
                    }
                }
                .padding(.top, 10 + iPadHeaderOffset + headerTopInset)
                .padding(.horizontal, 12)
            } else {
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
                                    if canShowBookmarks {
                                        bookmarkMenu
                                    }
                                    speedMenu
                                    headerToggleButton
                                }
                                #endif
                            }
                        }
                    }
                    if shouldShowHeaderInfo {
                        summaryTickerView
                    }
                }
                .padding(.top, 10 + headerTopInset)
                .padding(.horizontal, 12)
            }
        }
        .background(headerBackgroundStyle, in: RoundedRectangle(cornerRadius: headerBackgroundCornerRadius))
        .overlay(
            RoundedRectangle(cornerRadius: headerBackgroundCornerRadius)
                .stroke(Color.white.opacity(0.12), lineWidth: 1)
        )
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
                guard abs(value.translation.height) >= abs(value.translation.width) else {
                    return
                }
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
                    PlayerLanguageFlagRow(
                        flags: metadata.languageFlags,
                        modelLabel: metadata.translationModel,
                        isTV: isTV
                    )
                }
            }
        }
    }

    #if os(tvOS)
    @ViewBuilder
    private var infoHeaderOverlay: some View {
        let showHeaderContent = !isHeaderCollapsed
        if showHeaderContent || isTV {
            let timelineLabel = videoTimelineLabel
            let segmentLabel = segmentHeaderLabel
            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .top, spacing: 12) {
                    if showHeaderContent {
                        infoHeaderContent
                    }
                    Spacer(minLength: 12)
                    if showHeaderContent || isTV {
                        VStack(alignment: .trailing, spacing: 6) {
                            if showHeaderContent {
                                if let segmentLabel {
                                    videoTimelineView(label: segmentLabel)
                                }
                                if let timelineLabel {
                                    videoTimelineView(label: timelineLabel)
                                }
                            }
                            if isTV {
                                tvHeaderTogglePill
                            }
                        }
                    }
                }
                if showHeaderContent {
                    summaryTickerView
                }
            }
            .padding(.top, 6)
            .padding(.horizontal, 6)
            .background(headerBackgroundStyle, in: RoundedRectangle(cornerRadius: headerBackgroundCornerRadius))
            .overlay(
                RoundedRectangle(cornerRadius: headerBackgroundCornerRadius)
                    .stroke(Color.white.opacity(0.12), lineWidth: 1)
            )
            .frame(maxWidth: .infinity, alignment: .topLeading)
        }
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

    @ViewBuilder
    private var summaryTickerView: some View {
        if !isHeaderCollapsed,
           !isPlaying,
           let summary = metadata.summary?.nonEmptyValue {
            SummaryTickerPill(text: summary, isTV: isTV)
        }
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

    private var speedMenuLabel: some View {
        #if os(tvOS)
        tvControlLabel(
            systemName: "speedometer",
            label: "Speed",
            font: .callout.weight(.semibold),
            isFocused: focusTarget == .control(.speed)
        )
        #else
        Label("Speed", systemImage: "speedometer")
            .labelStyle(.titleAndIcon)
            .font(.caption)
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(.black.opacity(0.45), in: RoundedRectangle(cornerRadius: 8))
            .foregroundStyle(.white)
        #endif
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
    private var tvHeaderTogglePill: some View {
        TVActionButton(
            isFocusable: headerFocusEnabled,
            isFocused: focusTarget == .control(.header),
            onMoveUp: nil,
            onMoveDown: {
                showTVControls = true
                focusTarget = .control(.playPause)
            },
            action: onToggleHeaderCollapsed
        ) {
            Image(systemName: isHeaderCollapsed ? "chevron.down" : "chevron.up")
                .font(.caption.weight(.semibold))
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.black.opacity(0.6), in: Capsule())
                .foregroundStyle(.white)
        }
        .focused($focusTarget, equals: .control(.header))
        .accessibilityLabel(isHeaderCollapsed ? "Show info header" : "Hide info header")
    }
    #endif

    #if os(tvOS)
    private var controlsFocusEnabled: Bool {
        showTVControls && !showSubtitleSettings && !suppressControlFocus
    }

    private var headerFocusEnabled: Bool {
        !showSubtitleSettings
    }

    private var tvControls: some View {
        let isControlsFocusEnabled = controlsFocusEnabled
        return HStack(spacing: 14) {
            tvControlButton(
                systemName: "gobackward.15",
                isFocused: focusTarget == .control(.skipBackward),
                isFocusable: isControlsFocusEnabled,
                action: onSkipBackward
            )
                .focused($focusTarget, equals: .control(.skipBackward))
            tvControlButton(
                systemName: isPlaying ? "pause.fill" : "play.fill",
                prominent: true,
                isFocused: focusTarget == .control(.playPause),
                isFocusable: isControlsFocusEnabled,
                action: onPlayPause
            )
                .focused($focusTarget, equals: .control(.playPause))
            tvControlButton(
                systemName: "goforward.15",
                isFocused: focusTarget == .control(.skipForward),
                isFocusable: isControlsFocusEnabled,
                action: onSkipForward
            )
                .focused($focusTarget, equals: .control(.skipForward))
            if canShowBookmarks {
                bookmarkMenu
            }
            speedMenu
            if hasOptions {
                tvControlButton(
                    systemName: "captions.bubble",
                    label: "Options",
                    font: .callout.weight(.semibold),
                    isFocused: focusTarget == .control(.captions),
                    isFocusable: isControlsFocusEnabled
                ) {
                    showSubtitleSettings = true
                }
                .focused($focusTarget, equals: .control(.captions))
            }
        }
        .onMoveCommand { direction in
            guard !showSubtitleSettings else { return }
            if direction == .up {
                focusTarget = .control(.header)
            } else if direction == .down {
                focusTarget = .subtitles
            }
        }
    }

    private func tvControlButton(
        systemName: String,
        label: String? = nil,
        font: Font? = nil,
        prominent: Bool = false,
        isFocused: Bool = false,
        isFocusable: Bool = true,
        action: @escaping () -> Void
    ) -> some View {
        TVActionButton(
            isFocusable: isFocusable,
            isFocused: isFocused,
            onMoveUp: {
                focusTarget = .control(.header)
            },
            onMoveDown: {
                focusTarget = .subtitles
            },
            action: action
        ) {
            tvControlLabel(
                systemName: systemName,
                label: label,
                font: font,
                prominent: prominent,
                isFocused: isFocused
            )
        }
    }

    private func tvControlLabel(
        systemName: String,
        label: String? = nil,
        font: Font? = nil,
        prominent: Bool = false,
        isFocused: Bool = false
    ) -> some View {
        Group {
            if let label {
                Label(label, systemImage: systemName)
                    .labelStyle(.titleAndIcon)
            } else {
                Image(systemName: systemName)
            }
        }
        .font(font ?? .title3.weight(.semibold))
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
                        isFocusable: controlsFocusEnabled,
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

    private func suppressControlFocusTemporarily() {
        suppressFocusTask?.cancel()
        suppressControlFocus = true
        suppressFocusTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 150_000_000)
            suppressControlFocus = false
        }
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

    private func playbackRateLabel(_ rate: Double) -> String {
        let percent = (rate * 100).rounded()
        return "\(Int(percent))%"
    }

    private func isCurrentRate(_ rate: Double) -> Bool {
        abs(rate - playbackRate) < 0.01
    }

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

    private var headerBackgroundStyle: LinearGradient {
        LinearGradient(
            colors: [
                Color(white: 0.18).opacity(0.7),
                Color(white: 0.12).opacity(0.45),
                Color(white: 0.08).opacity(0.2)
            ],
            startPoint: .top,
            endPoint: .bottom
        )
    }

    private var headerBackgroundCornerRadius: CGFloat {
        #if os(tvOS)
        return 18
        #else
        return 14
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

    private var includeBubbleInSubtitleStack: Bool {
        !shouldOverlayBubbleOnPhone
    }

    private var shouldOverlayBubbleOnPhone: Bool {
        isPhone
    }

    private var subtitleFrameAlignment: Alignment {
        switch subtitleAlignment {
        case .leading:
            return .leading
        case .trailing:
            return .trailing
        default:
            return .center
        }
    }

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
    case bookmark
    case speed
    case captions
    case header
    case scrubber
}

private enum VideoPlayerFocusTarget: Hashable {
    case subtitles
    case bubble
    case control(TVFocusTarget)
}

private struct TVActionButton<Label: View>: View {
    let isFocusable: Bool
    let isFocused: Bool
    let onMoveUp: (() -> Void)?
    let onMoveDown: (() -> Void)?
    let action: () -> Void
    let label: () -> Label

    var body: some View {
        Button(action: action) {
            label()
        }
        .buttonStyle(.plain)
        .contentShape(Rectangle())
        .disabled(!isFocusable)
        .focusEffectDisabled()
        .onMoveCommand { direction in
            guard isFocused else { return }
            switch direction {
            case .up:
                onMoveUp?()
            case .down:
                onMoveDown?()
            default:
                break
            }
        }
    }
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
