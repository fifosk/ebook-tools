import SwiftUI

#if !os(tvOS)
struct CollapsedVideoHeaderPill: View {
    let timelineLabel: String
    let font: Font
    let headerTopInset: CGFloat
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            Text(timelineLabel)
                .font(font)
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
        .buttonStyle(.plain)
        .frame(maxWidth: .infinity, alignment: .center)
        .padding(.top, 36 + headerTopInset)
        .padding(.horizontal, 12)
    }
}

struct VideoPlayerHeaderDismissButton: View {
    let onDismiss: () -> Void

    var body: some View {
        Button(action: onDismiss) {
            Image(systemName: "xmark")
                .font(.caption.weight(.semibold))
                .padding(8)
                .background(.black.opacity(0.45), in: Circle())
                .foregroundStyle(.white)
        }
    }
}

struct VideoPlayerHeaderControlsRow<SearchPill: View>: View {
    let searchPill: SearchPill?
    let showBookmarkRibbonPill: Bool
    let canShowBookmarks: Bool
    let hasOptions: Bool
    let subtitleLabel: String
    let isPad: Bool
    let bookmarks: [PlaybackBookmarkEntry]
    let playbackRate: Double
    let playbackRateOptions: [Double]
    let onShowSubtitleSettings: () -> Void
    let onPlaybackRateChange: (Double) -> Void
    let onAddBookmark: (() -> Void)?
    let onJumpToBookmark: (PlaybackBookmarkEntry) -> Void
    let onRemoveBookmark: (PlaybackBookmarkEntry) -> Void
    let onUserInteraction: () -> Void

    var body: some View {
        HStack(spacing: 8) {
            if let searchPill {
                searchPill
            }
            if showBookmarkRibbonPill && canShowBookmarks {
                bookmarkRibbonPill
            }
            if hasOptions {
                subtitleButton
            }
            if canShowBookmarks && !showBookmarkRibbonPill {
                bookmarkMenu
            }
            speedMenu
        }
    }

    private var subtitleButton: some View {
        VideoPlayerSubtitleButton(
            labelText: subtitleLabel,
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

    private var bookmarkRibbonPill: some View {
        BookmarkRibbonPillView(
            bookmarkCount: bookmarks.count,
            isTV: false,
            sizeScale: isPad ? 1.5 : 1.0,
            bookmarks: bookmarks,
            onAddBookmark: onAddBookmark,
            onJumpToBookmark: onJumpToBookmark,
            onRemoveBookmark: onRemoveBookmark,
            onUserInteraction: onUserInteraction
        )
    }
}

struct VideoPlayerHeaderTimelineStack: View {
    let timelineLabel: String?
    let segmentLabel: String?
    let shouldShowHeaderInfo: Bool
    let font: Font
    let onToggleHeaderCollapsed: () -> Void

    var body: some View {
        VStack(alignment: .trailing, spacing: 6) {
            if shouldShowHeaderInfo {
                if let segmentLabel {
                    VideoTimelinePill(
                        label: segmentLabel,
                        font: font,
                        onTap: onToggleHeaderCollapsed
                    )
                }
                if let timelineLabel {
                    VideoTimelinePill(
                        label: timelineLabel,
                        font: font,
                        onTap: onToggleHeaderCollapsed
                    )
                }
            } else if let timelineLabel {
                VideoTimelinePill(
                    label: timelineLabel,
                    font: font,
                    onTap: onToggleHeaderCollapsed
                )
            }
        }
    }
}

struct VideoPlayerHeaderInfoView: View {
    let metadata: VideoPlaybackMetadata
    let headerScale: CGFloat
    let coverWidth: CGFloat
    let coverHeight: CGFloat
    let titleFont: Font
    let metaFont: Font

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            PlayerChannelBugView(
                variant: metadata.channelVariant,
                label: metadata.channelLabel,
                sizeScale: headerScale
            )
            if hasInfoBadge {
                infoBadgeView
            }
        }
    }

    private var hasInfoBadge: Bool {
        !metadata.title.isEmpty || (metadata.subtitle?.isEmpty == false) || metadata.artworkURL != nil
    }

    private var infoBadgeView: some View {
        HStack(alignment: .top, spacing: 8) {
            if metadata.artworkURL != nil || metadata.secondaryArtworkURL != nil {
                PlayerCoverStackView(
                    primaryURL: metadata.artworkURL,
                    secondaryURL: metadata.secondaryArtworkURL,
                    width: coverWidth,
                    height: coverHeight,
                    isTV: false
                )
            }
            VStack(alignment: .leading, spacing: 2) {
                if !metadata.title.isEmpty {
                    Text(metadata.title)
                        .font(titleFont)
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                        .foregroundStyle(.white)
                }
                if let subtitle = metadata.subtitle, !subtitle.isEmpty {
                    Text(subtitle)
                        .font(metaFont)
                        .foregroundStyle(Color.white.opacity(0.75))
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                }
                if !metadata.languageFlags.isEmpty {
                    PlayerLanguageFlagRow(
                        flags: metadata.languageFlags,
                        modelLabel: metadata.translationModel,
                        isTV: false,
                        sizeScale: headerScale
                    )
                }
            }
        }
    }
}
#endif
