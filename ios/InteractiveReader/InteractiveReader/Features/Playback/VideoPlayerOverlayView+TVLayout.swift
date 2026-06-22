import SwiftUI

#if os(tvOS)
extension VideoPlayerOverlayView {
    var tvOverlay: some View {
        VStack(spacing: 16) {
            Spacer()
            subtitleStack
            tvBottomBar
                .frame(height: showTVControls ? nil : 0, alignment: .top)
                .opacity(showTVControls ? 1 : 0)
                .allowsHitTesting(showTVControls)
                .clipped()
                .transaction { transaction in
                    if !showTVControls {
                        transaction.disablesAnimations = true
                    }
                }
        }
        .padding(.horizontal, 60)
        .padding(.bottom, showTVControls ? 36 : 24)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottom)
        .onPlayPauseCommand(perform: handleTVPlayPauseCommand)
    }

    @ViewBuilder
    var tvInfoHeaderOverlay: some View {
        let timelineLabel = videoTimelineLabel
        let segmentLabel = segmentHeaderLabel

        if isHeaderCollapsed {
            tvCollapsedHeaderPill(timelineLabel: timelineLabel)
        } else {
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
            .onLongPressGesture(minimumDuration: 0.6, perform: handleHeaderLongPress)
        }
    }

    @ViewBuilder
    private func tvCollapsedHeaderPill(timelineLabel: String?) -> some View {
        if let timelineLabel {
            tvTimelinePillButton(label: timelineLabel)
                .frame(maxWidth: .infinity, alignment: .topTrailing)
                .padding(.top, 6)
                .padding(.trailing, 6)
                .onLongPressGesture(minimumDuration: 0.6, perform: handleHeaderLongPress)
        }
    }

    private func tvTimelinePillButton(label: String) -> some View {
        TVTimelinePillButton(
            label: label,
            focusTarget: $focusTarget,
            onToggle: onToggleHeaderCollapsed,
            onMoveCommand: handleTimelinePillMoveCommand
        )
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
            onEditingChanged: handleTVScrubberEditingChanged,
            onUserInteraction: onUserInteraction,
            onShowSubtitleSettings: showTVSubtitleSettings,
            bookmarkMenu: VideoPlayerBookmarkMenu(
                bookmarks: bookmarks,
                onAddBookmark: onAddBookmark,
                onJumpToBookmark: onJumpToBookmark,
                onRemoveBookmark: onRemoveBookmark,
                onUserInteraction: onUserInteraction,
                isFocused: focusTarget == .control(.bookmark),
                isDisabled: !controlsFocusEnabled
            ),
            speedMenu: VideoPlayerSpeedMenu(
                playbackRate: playbackRate,
                playbackRateOptions: playbackRateOptions,
                onPlaybackRateChange: onPlaybackRateChange,
                onUserInteraction: onUserInteraction,
                isFocused: focusTarget == .control(.speed),
                isDisabled: !controlsFocusEnabled
            )
        )
    }

    var displayTime: Double {
        isScrubbing ? scrubberValue : currentTime
    }

    private var controlsFocusEnabled: Bool {
        showTVControls && !showSubtitleSettings && !suppressControlFocus
    }

    private func handleTVPlayPauseCommand() {
        if !isPlaying && !showTVControls && subtitleBubble == nil {
            onSubtitleLookup()
        } else {
            onPlayPause()
            onUserInteraction()
        }
    }

    private func handleTVScrubberEditingChanged(_ editing: Bool) {
        isScrubbing = editing
        onUserInteraction()
    }

    private func showTVSubtitleSettings() {
        showSubtitleSettings = true
    }
}
#endif
