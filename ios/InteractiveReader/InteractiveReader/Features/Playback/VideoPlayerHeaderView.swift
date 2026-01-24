import SwiftUI

#if canImport(UIKit)
import UIKit
#endif

// MARK: - Video Player Header View

struct VideoPlayerHeaderView: View {
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

    // Callbacks
    let onToggleHeaderCollapsed: () -> Void
    let onShowSubtitleSettings: () -> Void
    let onPlaybackRateChange: (Double) -> Void
    let onAddBookmark: (() -> Void)?
    let onJumpToBookmark: (PlaybackBookmarkEntry) -> Void
    let onRemoveBookmark: (PlaybackBookmarkEntry) -> Void
    let onUserInteraction: () -> Void
    let onDismiss: () -> Void

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

    @ViewBuilder
    private func padLayout(
        timelineLabel: String?,
        segmentLabel: String?,
        shouldShowHeaderInfo: Bool
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 12) {
                dismissButton
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
                        VideoTimelinePill(label: segmentLabel, font: infoIndicatorFont)
                    }
                    if let timelineLabel, shouldShowHeaderInfo {
                        VideoTimelinePill(label: timelineLabel, font: infoIndicatorFont)
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
    }

    @ViewBuilder
    private func phoneLayout(
        timelineLabel: String?,
        segmentLabel: String?,
        shouldShowHeaderInfo: Bool
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 12) {
                dismissButton
                if shouldShowHeaderInfo {
                    infoHeaderContent
                }
                Spacer(minLength: 12)
                if timelineLabel != nil || hasOptions {
                    VStack(alignment: .trailing, spacing: 6) {
                        if let segmentLabel, shouldShowHeaderInfo {
                            VideoTimelinePill(label: segmentLabel, font: infoIndicatorFont)
                        }
                        if let timelineLabel, shouldShowHeaderInfo {
                            VideoTimelinePill(label: timelineLabel, font: infoIndicatorFont)
                        }
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

    private var dismissButton: some View {
        Button(action: onDismiss) {
            Image(systemName: "xmark")
                .font(.caption.weight(.semibold))
                .padding(8)
                .background(.black.opacity(0.45), in: Circle())
                .foregroundStyle(.white)
        }
    }

    private var subtitleButton: some View {
        VideoPlayerSubtitleButton(
            labelText: hasTracks ? selectedTrackLabel : "Options",
            onTap: onShowSubtitleSettings
        )
    }

    private var bookmarkMenu: some View {
        VideoPlayerBookmarkMenu(
            bookmarks: bookmarks,
            onAddBookmark: onAddBookmark,
            onJumpToBookmark: onJumpToBookmark,
            onRemoveBookmark: onRemoveBookmark,
            onUserInteraction: onUserInteraction
        )
    }

    private var speedMenu: some View {
        VideoPlayerSpeedMenu(
            playbackRate: playbackRate,
            playbackRateOptions: playbackRateOptions,
            onPlaybackRateChange: onPlaybackRateChange,
            onUserInteraction: onUserInteraction
        )
    }

    private var headerToggleButton: some View {
        VideoPlayerHeaderToggleButton(
            isCollapsed: isCollapsed,
            onToggle: onToggleHeaderCollapsed
        )
    }

    private var infoHeaderContent: some View {
        HStack(alignment: .top, spacing: 12) {
            PlayerChannelBugView(
                variant: metadata.channelVariant,
                label: metadata.channelLabel,
                sizeScale: infoHeaderScale
            )
            if hasInfoBadge {
                infoBadgeView
            }
        }
    }

    private var infoBadgeView: some View {
        HStack(alignment: .top, spacing: 8) {
            if metadata.artworkURL != nil || metadata.secondaryArtworkURL != nil {
                PlayerCoverStackView(
                    primaryURL: metadata.artworkURL,
                    secondaryURL: metadata.secondaryArtworkURL,
                    width: infoCoverWidth,
                    height: infoCoverHeight,
                    isTV: false
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
                        isTV: false,
                        sizeScale: infoHeaderScale
                    )
                }
            }
        }
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

    private var hasInfoBadge: Bool {
        !metadata.title.isEmpty || (metadata.subtitle?.isEmpty == false) || metadata.artworkURL != nil
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
