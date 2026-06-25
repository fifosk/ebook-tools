import SwiftUI

#if canImport(UIKit)
import UIKit
#endif

// MARK: - Video Player Header View

struct VideoPlayerHeaderView<SearchPill: View, SleepTimerPill: View>: View {
    let metadata: VideoPlaybackMetadata
    let isCollapsed: Bool
    let headerTopInset: CGFloat
    let headerScaleValue: Double
    let currentTime: Double
    let duration: Double
    let segmentOptions: [VideoSegmentOption]
    let selectedSegmentID: String?
    let jobProgressLabel: String?
    let jobRemainingLabel: String?
    let tracks: [VideoSubtitleTrack]
    let selectedTrack: VideoSubtitleTrack?
    let playbackRate: Double
    let playbackRateOptions: [Double]
    let bookmarks: [PlaybackBookmarkEntry]
    let isPlaying: Bool
    let searchPill: SearchPill?
    let sleepTimerPill: SleepTimerPill?
    let showBookmarkRibbonPill: Bool

    // Callbacks
    let onToggleHeaderCollapsed: () -> Void
    let onShowSubtitleSettings: () -> Void
    let onPlaybackRateChange: (Double) -> Void
    let onAddBookmark: (() -> Void)?
    let onJumpToBookmark: (PlaybackBookmarkEntry) -> Void
    let onRemoveBookmark: (PlaybackBookmarkEntry) -> Void
    let onUserInteraction: () -> Void
    let onDismiss: () -> Void

    init(
        metadata: VideoPlaybackMetadata,
        isCollapsed: Bool,
        headerTopInset: CGFloat,
        headerScaleValue: Double,
        currentTime: Double,
        duration: Double,
        segmentOptions: [VideoSegmentOption],
        selectedSegmentID: String?,
        jobProgressLabel: String?,
        jobRemainingLabel: String?,
        tracks: [VideoSubtitleTrack],
        selectedTrack: VideoSubtitleTrack?,
        playbackRate: Double,
        playbackRateOptions: [Double],
        bookmarks: [PlaybackBookmarkEntry],
        isPlaying: Bool,
        searchPill: SearchPill? = nil,
        sleepTimerPill: SleepTimerPill? = nil,
        showBookmarkRibbonPill: Bool = false,
        onToggleHeaderCollapsed: @escaping () -> Void,
        onShowSubtitleSettings: @escaping () -> Void,
        onPlaybackRateChange: @escaping (Double) -> Void,
        onAddBookmark: (() -> Void)?,
        onJumpToBookmark: @escaping (PlaybackBookmarkEntry) -> Void,
        onRemoveBookmark: @escaping (PlaybackBookmarkEntry) -> Void,
        onUserInteraction: @escaping () -> Void,
        onDismiss: @escaping () -> Void
    ) {
        self.metadata = metadata
        self.isCollapsed = isCollapsed
        self.headerTopInset = headerTopInset
        self.headerScaleValue = headerScaleValue
        self.currentTime = currentTime
        self.duration = duration
        self.segmentOptions = segmentOptions
        self.selectedSegmentID = selectedSegmentID
        self.jobProgressLabel = jobProgressLabel
        self.jobRemainingLabel = jobRemainingLabel
        self.tracks = tracks
        self.selectedTrack = selectedTrack
        self.playbackRate = playbackRate
        self.playbackRateOptions = playbackRateOptions
        self.bookmarks = bookmarks
        self.isPlaying = isPlaying
        self.searchPill = searchPill
        self.sleepTimerPill = sleepTimerPill
        self.showBookmarkRibbonPill = showBookmarkRibbonPill
        self.onToggleHeaderCollapsed = onToggleHeaderCollapsed
        self.onShowSubtitleSettings = onShowSubtitleSettings
        self.onPlaybackRateChange = onPlaybackRateChange
        self.onAddBookmark = onAddBookmark
        self.onJumpToBookmark = onJumpToBookmark
        self.onRemoveBookmark = onRemoveBookmark
        self.onUserInteraction = onUserInteraction
        self.onDismiss = onDismiss
    }

    var body: some View {
        #if os(tvOS)
        EmptyView() // tvOS uses infoHeaderOverlay separately
        #else
        topBarContent
        #endif
    }

    #if !os(tvOS)
    @ViewBuilder
    private var topBarContent: some View {
        let timelineLabel = videoTimelineLabel
        let segmentLabel = segmentHeaderLabel
        let shouldShowHeaderInfo = !isCollapsed

        if isCollapsed {
            // When collapsed, show only a minimal timeline pill without the full header bar
            collapsedHeaderPill(timelineLabel: timelineLabel)
        } else {
            Group {
                if isPad {
                    padLayout(
                        timelineLabel: timelineLabel,
                        segmentLabel: segmentLabel,
                        shouldShowHeaderInfo: shouldShowHeaderInfo
                    )
                } else {
                    phoneLayout(
                        timelineLabel: timelineLabel,
                        segmentLabel: segmentLabel,
                        shouldShowHeaderInfo: shouldShowHeaderInfo
                    )
                }
            }
            .background(
                VideoPlayerOverlayStyles.headerBackgroundGradient,
                in: RoundedRectangle(cornerRadius: VideoPlayerOverlayStyles.headerBackgroundCornerRadius)
            )
            .overlay(
                RoundedRectangle(cornerRadius: VideoPlayerOverlayStyles.headerBackgroundCornerRadius)
                    .stroke(Color.white.opacity(0.12), lineWidth: 1)
            )
        }
    }

    @ViewBuilder
    private func collapsedHeaderPill(timelineLabel: String?) -> some View {
        if let timelineLabel {
            CollapsedVideoHeaderPill(
                timelineLabel: timelineLabel,
                font: infoIndicatorFont,
                headerTopInset: headerTopInset,
                onTap: onToggleHeaderCollapsed
            )
        }
    }

    @ViewBuilder
    private func padLayout(
        timelineLabel: String?,
        segmentLabel: String?,
        shouldShowHeaderInfo: Bool
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 12) {
                VideoPlayerHeaderDismissButton(onDismiss: onDismiss)
                Spacer(minLength: 12)
                controlsRow
            }
            HStack(alignment: .top, spacing: 12) {
                if shouldShowHeaderInfo {
                    infoHeaderContent
                }
                Spacer(minLength: 12)
                VideoPlayerHeaderTimelineStack(
                    timelineLabel: timelineLabel,
                    segmentLabel: segmentLabel,
                    shouldShowHeaderInfo: shouldShowHeaderInfo,
                    font: infoIndicatorFont,
                    onToggleHeaderCollapsed: onToggleHeaderCollapsed
                )
            }
            if shouldShowHeaderInfo {
                summaryTickerView
            }
        }
        .padding(.top, 10 + iPadHeaderOffset + headerTopInset)
        .padding(.horizontal, 12)
    }

    @ViewBuilder
    private func phoneLayout(
        timelineLabel: String?,
        segmentLabel: String?,
        shouldShowHeaderInfo: Bool
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 12) {
                VideoPlayerHeaderDismissButton(onDismiss: onDismiss)
                if shouldShowHeaderInfo {
                    infoHeaderContent
                }
                Spacer(minLength: 12)
                if timelineLabel != nil || hasOptions {
                    VStack(alignment: .trailing, spacing: 6) {
                        VideoPlayerHeaderTimelineStack(
                            timelineLabel: timelineLabel,
                            segmentLabel: segmentLabel,
                            shouldShowHeaderInfo: shouldShowHeaderInfo,
                            font: infoIndicatorFont,
                            onToggleHeaderCollapsed: onToggleHeaderCollapsed
                        )
                        controlsRow
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

    private var infoHeaderContent: some View {
        VideoPlayerHeaderInfoView(
            metadata: metadata,
            headerScale: infoHeaderScale,
            coverWidth: infoCoverWidth,
            coverHeight: infoCoverHeight,
            titleFont: infoTitleFont,
            metaFont: infoMetaFont
        )
    }

    private var controlsRow: some View {
        VideoPlayerHeaderControlsRow(
            searchPill: searchPill,
            sleepTimerPill: sleepTimerPill,
            showBookmarkRibbonPill: showBookmarkRibbonPill,
            canShowBookmarks: canShowBookmarks,
            hasOptions: hasOptions,
            subtitleLabel: hasTracks ? selectedTrackLabel : "Options",
            isPad: isPad,
            bookmarks: bookmarks,
            playbackRate: playbackRate,
            playbackRateOptions: playbackRateOptions,
            onShowSubtitleSettings: onShowSubtitleSettings,
            onPlaybackRateChange: onPlaybackRateChange,
            onAddBookmark: onAddBookmark,
            onJumpToBookmark: onJumpToBookmark,
            onRemoveBookmark: onRemoveBookmark,
            onUserInteraction: onUserInteraction
        )
    }

    @ViewBuilder
    private var summaryTickerView: some View {
        if !isCollapsed,
           !isPlaying,
           let summary = metadata.summary?.nonEmptyValue {
            SummaryTickerPill(text: summary, isTV: false)
        }
    }
    #endif

    // MARK: - Computed Properties

    private var videoTimelineLabel: String? {
        guard duration.isFinite, duration > 0, currentTime.isFinite else { return nil }
        let played = min(max(currentTime, 0), duration)
        let remaining = max(duration - played, 0)
        let base = "\(VideoPlayerTimeFormatter.formatDuration(played)) / \(VideoPlayerTimeFormatter.formatDuration(remaining)) remaining"
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

    private var hasTracks: Bool {
        !tracks.isEmpty
    }

    private var hasSegmentOptions: Bool {
        segmentOptions.count > 1
    }

    private var hasOptions: Bool {
        hasTracks || hasSegmentOptions
    }

    private var canShowBookmarks: Bool {
        onAddBookmark != nil
    }

    private var selectedTrackLabel: String {
        if let selectedTrack {
            return VideoPlayerTrackLabelFormatter.trimmedLabel(
                selectedTrack.label,
                isTV: false,
                isPhone: isPhone
            )
        }
        return "Subtitles Off"
    }

    // MARK: - Fonts & Metrics

    private var infoHeaderScale: CGFloat {
        #if os(iOS)
        let base: CGFloat = isPad ? 2.0 : 1.0
        return base * CGFloat(headerScaleValue)
        #else
        return 1.0
        #endif
    }

    private var infoCoverWidth: CGFloat {
        VideoPlayerOverlayMetrics.coverWidth(isTV: false) * infoHeaderScale
    }

    private var infoCoverHeight: CGFloat {
        VideoPlayerOverlayMetrics.coverHeight(isTV: false) * infoHeaderScale
    }

    private var infoTitleFont: Font {
        VideoPlayerHeaderFonts.titleFont(isTV: false, isPad: isPad, scale: infoHeaderScale)
    }

    private var infoMetaFont: Font {
        VideoPlayerHeaderFonts.metaFont(isTV: false, isPad: isPad, scale: infoHeaderScale)
    }

    private var infoIndicatorFont: Font {
        VideoPlayerHeaderFonts.indicatorFont(isTV: false, isPad: isPad, scale: infoHeaderScale)
    }

    private var iPadHeaderOffset: CGFloat {
        #if os(iOS)
        return isPad ? UIScreen.main.bounds.height * 0.06 : 0
        #else
        return 0
        #endif
    }

    private var isPad: Bool {
        VideoPlayerPlatform.isPad
    }

    private var isPhone: Bool {
        VideoPlayerPlatform.isPhone
    }
}
