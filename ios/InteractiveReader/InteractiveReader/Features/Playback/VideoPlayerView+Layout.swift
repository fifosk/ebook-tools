import AVFoundation
import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

extension VideoPlayerView {
    @ViewBuilder
    var playerContent: some View {
        if let player = coordinator.playerInstance() {
            GeometryReader { proxy in
                let isPhonePortrait = isPhone && proxy.size.height > proxy.size.width
                let videoHeight = min(proxy.size.height, proxy.size.width * 9 / 16)
                let topPadding = isPhonePortrait ? max(proxy.safeAreaInsets.top, 12) : 0
                let verticalOffset = isPhonePortrait ? proxy.size.height * 0.1 : 0
                let leadingInset = isPhonePortrait ? max(proxy.safeAreaInsets.leading, 8) : 0
                let trailingInset = isPhonePortrait ? max(proxy.safeAreaInsets.trailing, 32) : 0
                let availableWidth = isPhonePortrait
                    ? max(proxy.size.width - leadingInset - trailingInset, 0)
                    : proxy.size.width
                let subtitleAlignment: HorizontalAlignment = isPhonePortrait ? .center : .center
                let allowSubtitleDownwardDrag = isPhone && !isPhonePortrait
                let subtitleLeadingInset: CGFloat = isPhonePortrait ? leadingInset : 0
                let subtitleMaxWidth: CGFloat? = isPhonePortrait ? availableWidth : nil
                let headerTopInset: CGFloat = isPhonePortrait ? verticalOffset : 0
                let baseOffset = topPadding + verticalOffset
                let bottomPadding = max(proxy.safeAreaInsets.bottom, 24)
                let maxTop = max(topPadding, proxy.size.height - videoHeight - bottomPadding)
                let minAdditional = topPadding - baseOffset
                let maxAdditional = maxTop - baseOffset
                let storedAdditional = CGFloat(videoVerticalOffsetValue)
                let clampedStoredAdditional = min(max(storedAdditional, minAdditional), maxAdditional)
                let dragAdditional = isVideoDragGestureActive
                    ? clampedStoredAdditional + videoDragTranslation
                    : clampedStoredAdditional
                let appliedAdditional = min(max(dragAdditional, minAdditional), maxAdditional)
                let appliedTop = baseOffset + appliedAdditional
                let videoBottom = appliedTop + videoHeight
                let videoRepositionGesture = DragGesture(minimumDistance: 12, coordinateSpace: .local)
                    .onChanged { value in
                        guard isPhonePortrait else { return }
                        guard !showSubtitleSettings else { return }
                        guard !isScrubbing else { return }
                        let horizontal = value.translation.width
                        let vertical = value.translation.height
                        guard abs(vertical) > abs(horizontal) else { return }
                        if !isVideoDragGestureActive {
                            let startY = value.startLocation.y
                            guard startY >= appliedTop - 12, startY <= videoBottom + 12 else { return }
                            isVideoDragGestureActive = true
                        }
                        if isVideoDragGestureActive {
                            videoDragTranslation = vertical
                        }
                    }
                    .onEnded { value in
                        defer {
                            videoDragTranslation = 0
                            isVideoDragGestureActive = false
                        }
                        guard isVideoDragGestureActive else { return }
                        let proposed = clampedStoredAdditional + value.translation.height
                        let clamped = min(max(proposed, minAdditional), maxAdditional)
                        videoVerticalOffsetValue = Double(clamped)
                    }
                ZStack(alignment: .top) {
                    Color.black.ignoresSafeArea()
                    playerSurface(player)
                        .frame(
                            width: availableWidth,
                            height: isPhonePortrait ? videoHeight : proxy.size.height,
                            alignment: .topLeading
                        )
                        .padding(.top, appliedTop)
                        .padding(.leading, leadingInset)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    overlayView(
                        subtitleAlignment: subtitleAlignment,
                        subtitleMaxWidth: subtitleMaxWidth,
                        subtitleLeadingInset: subtitleLeadingInset,
                        headerTopInset: headerTopInset,
                        allowSubtitleDownwardDrag: allowSubtitleDownwardDrag
                    )
                    #if os(iOS)
                        .simultaneousGesture(videoScrubGesture, including: .gesture)
                    #endif
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
                            onLookup: {
                                guard !coordinator.isPlaying else { return }
                                handleSubtitleLookup()
                            },
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
                }
                #if os(iOS)
                .contentShape(Rectangle())
                .simultaneousGesture(videoRepositionGesture, including: .gesture)
                #endif
            }
        } else {
            ProgressView("Preparing video…")
        }
    }

    @ViewBuilder
    func playerSurface(_ player: AVPlayer) -> some View {
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
    }

    func overlayView(
        subtitleAlignment: HorizontalAlignment,
        subtitleMaxWidth: CGFloat?,
        subtitleLeadingInset: CGFloat,
        headerTopInset: CGFloat,
        allowSubtitleDownwardDrag: Bool
    ) -> VideoPlayerOverlayView {
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
            bookmarks: bookmarks,
            onAddBookmark: canUseBookmarks ? addBookmark : nil,
            onJumpToBookmark: jumpToBookmark,
            onRemoveBookmark: removeBookmark,
            subtitleFontScale: subtitleFontScale,
            isPlaying: coordinator.isPlaying,
            subtitleSelection: subtitleSelection,
            subtitleBubble: subtitleBubble,
            subtitleAlignment: subtitleAlignment,
            subtitleMaxWidth: subtitleMaxWidth,
            subtitleLeadingInset: subtitleLeadingInset,
            headerTopInset: headerTopInset,
            allowSubtitleDownwardDrag: allowSubtitleDownwardDrag,
            lookupLanguage: resolvedLookupLanguage,
            lookupLanguageOptions: lookupLanguageOptions,
            onLookupLanguageChange: { storedLookupLanguage = $0 },
            llmModel: resolvedLlmModel ?? MyLinguistPreferences.defaultLlmModel,
            llmModelOptions: llmModelOptions,
            onLlmModelChange: { storedLlmModel = $0 },
            subtitleLinguistFontScale: subtitleLinguistFontScale,
            canIncreaseSubtitleLinguistFont: canIncreaseSubtitleLinguistFont,
            canDecreaseSubtitleLinguistFont: canDecreaseSubtitleLinguistFont,
            isHeaderCollapsed: isHeaderCollapsed,
            playbackRate: resolvedPlaybackRate,
            playbackRateOptions: Self.playbackRateOptions,
            onPlaybackRateChange: { rate in
                playbackRateValue = Self.clampPlaybackRate(rate)
            },
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
            onToggleTransliteration: {
                handleTransliterationToggle()
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
    }

    var orderedTracks: [VideoSubtitleTrack] {
        subtitleTracks.sorted { lhs, rhs in
            if lhs.format.priority == rhs.format.priority {
                return lhs.label.localizedCaseInsensitiveCompare(rhs.label) == .orderedAscending
            }
            return lhs.format.priority < rhs.format.priority
        }
    }

    var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    var isPhone: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .phone
        #else
        return false
        #endif
    }

    var isShortcutHelpVisible: Bool {
        isShortcutHelpPinned || isShortcutHelpModifierActive
    }
}
