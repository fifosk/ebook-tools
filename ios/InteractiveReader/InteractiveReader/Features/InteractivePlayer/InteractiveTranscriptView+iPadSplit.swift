import SwiftUI
import OSLog

private let iPadSplitLogger = Logger(subsystem: "InteractiveReader", category: "iPadSplit")

// MARK: - Comparable Clamping Extension (duplicated from main file for file-private access)

private extension Comparable {
    func clamped(to range: ClosedRange<Self>) -> Self {
        min(max(self, range.lowerBound), range.upperBound)
    }
}

// MARK: - iPad Split Layout

#if os(iOS)
extension InteractiveTranscriptView {

    // MARK: Constants

    /// Minimum split ratio (tracks get at least 20% in vertical, bubble gets at least 20% in horizontal)
    var iPadMinSplitRatio: CGFloat { 0.20 }
    /// Maximum split ratio
    var iPadMaxSplitRatio: CGFloat { 0.80 }
    /// Divider thickness
    var iPadDividerThickness: CGFloat { 12 }
    /// Divider handle size
    var iPadDividerHandleWidth: CGFloat { 40 }
    var iPadDividerHandleHeight: CGFloat { 4 }

    // MARK: Split Layout

    @ViewBuilder
    func iPadSplitLayout<TrackContent: View>(
        trackView: TrackContent,
        bubble: MyLinguistBubbleState?,
        resolvedLinguistFontScale: CGFloat,
        bubbleFocusEnabled: Bool,
        availableSize: CGSize
    ) -> some View {
        let trackViewWithPlayback = trackView.contentShape(Rectangle())

        Group {
            if iPadSplitDirection == .vertical {
                iPadVerticalSplitLayout(
                    trackViewWithPlayback: trackViewWithPlayback,
                    bubble: bubble,
                    resolvedLinguistFontScale: resolvedLinguistFontScale,
                    bubbleFocusEnabled: bubbleFocusEnabled,
                    availableSize: availableSize
                )
            } else {
                iPadHorizontalSplitLayout(
                    trackViewWithPlayback: trackViewWithPlayback,
                    bubble: bubble,
                    resolvedLinguistFontScale: resolvedLinguistFontScale,
                    bubbleFocusEnabled: bubbleFocusEnabled,
                    availableSize: availableSize
                )
            }
        }
        .coordinateSpace(name: TextPlayerTokenCoordinateSpace.name)
        .onAppear {
            // Initialize previous ratio when layout appears
            previousSplitRatio = iPadSplitRatio
        }
        .onChange(of: iPadSplitRatio) { oldRatio, newRatio in
            // Dynamically adjust font scales based on split ratio changes
            // In vertical: ratio = tracks height percentage, so increasing ratio = more track space
            // In horizontal: ratio = bubble width percentage, so increasing ratio = more bubble space
            adjustFontScalesForSplitChange(
                oldRatio: oldRatio,
                newRatio: newRatio,
                isVertical: iPadSplitDirection == .vertical
            )
        }
        .onChange(of: iPadSplitDirection) { _, _ in
            // Reset previous ratio when direction changes
            previousSplitRatio = iPadSplitRatio
        }
    }

    // MARK: Font Scale Adjustment

    /// Adjust track and linguist font scales based on split ratio changes
    func adjustFontScalesForSplitChange(
        oldRatio: CGFloat,
        newRatio: CGFloat,
        isVertical: Bool
    ) {
        guard abs(newRatio - oldRatio) > 0.001 else { return }

        // Calculate how each area's size changed
        // In vertical mode:
        //   - ratio = track area percentage (0.5 means tracks get 50% of height)
        //   - track area grows when ratio increases
        //   - bubble area shrinks when ratio increases (1 - ratio)
        // In horizontal mode:
        //   - ratio = bubble area percentage (0.5 means bubble gets 50% of width)
        //   - bubble area grows when ratio increases
        //   - track area shrinks when ratio increases (1 - ratio)

        let trackRatioOld = isVertical ? oldRatio : (1 - oldRatio)
        let trackRatioNew = isVertical ? newRatio : (1 - newRatio)
        let bubbleRatioOld = isVertical ? (1 - oldRatio) : oldRatio
        let bubbleRatioNew = isVertical ? (1 - newRatio) : newRatio

        // Calculate scaling factors: how much did each area grow/shrink?
        // We want fonts to scale proportionally to fill the new space
        let trackScaleFactor = trackRatioOld > 0.001 ? trackRatioNew / trackRatioOld : 1.0
        let bubbleScaleFactor = bubbleRatioOld > 0.001 ? bubbleRatioNew / bubbleRatioOld : 1.0

        // Apply scaling to track font
        // Use square root for more gentle scaling (full linear feels too aggressive)
        let trackAdjustment = sqrt(trackScaleFactor)
        let newTrackScale = trackFontScale * trackAdjustment
        let clampedTrackScale = max(minTrackFontScale, min(maxTrackFontScale, newTrackScale))
        if abs(clampedTrackScale - trackFontScale) > 0.01 {
            onSetTrackFontScale(clampedTrackScale)
        }

        // Apply scaling to linguist font
        // linguistFontScale bounds come from the parent view
        let linguistMin: CGFloat = 0.8
        let linguistMax: CGFloat = 3.2  // iPad max from InteractivePlayerView
        let bubbleAdjustment = sqrt(bubbleScaleFactor)
        let newLinguistScale = linguistFontScale * bubbleAdjustment
        let clampedLinguistScale = max(linguistMin, min(linguistMax, newLinguistScale))
        if abs(clampedLinguistScale - linguistFontScale) > 0.01 {
            onSetLinguistFontScale(clampedLinguistScale)
        }

        previousSplitRatio = newRatio
    }

    // MARK: Vertical Split

    @ViewBuilder
    func iPadVerticalSplitLayout<TrackContent: View>(
        trackViewWithPlayback: TrackContent,
        bubble: MyLinguistBubbleState?,
        resolvedLinguistFontScale: CGFloat,
        bubbleFocusEnabled: Bool,
        availableSize: CGSize
    ) -> some View {
        let totalHeight = availableSize.height
        // Calculate exact heights for each section
        let trackHeight = max(0, totalHeight * iPadSplitRatio - iPadDividerThickness / 2)
        let bubbleHeight = max(0, totalHeight * (1 - iPadSplitRatio) - iPadDividerThickness / 2)
        logVerticalSplitLayout(
            totalHeight: totalHeight,
            trackHeight: trackHeight,
            bubbleHeight: bubbleHeight
        )

        VStack(spacing: 0) {
            // Tracks area - fixed height, clipped to bounds
            trackViewWithPlayback
                .frame(maxWidth: .infinity, alignment: .top)
                .frame(height: trackHeight)
                .clipped()
                .contentShape(Rectangle())
                .simultaneousGesture(swipeGesture, including: .all)
                .simultaneousGesture(selectionDragGesture, including: .gesture)
                .simultaneousGesture(backgroundPlaybackTapGesture, including: .all)
                .highPriorityGesture(trackMagnifyGesture, including: .all)

            // Divider
            iPadDivider(isVertical: true, availableSize: availableSize)

            // Bubble area - fixed height, clipped to bounds
            if let bubble {
                iPadBubbleContent(
                    bubble: bubble,
                    resolvedLinguistFontScale: resolvedLinguistFontScale,
                    bubbleFocusEnabled: bubbleFocusEnabled,
                    maxHeight: bubbleHeight,
                    fillWidth: true
                )
                .frame(height: bubbleHeight)
                .clipped()
            }
        }
        .frame(width: availableSize.width, height: availableSize.height)
    }

    // MARK: Horizontal Split

    @ViewBuilder
    func iPadHorizontalSplitLayout<TrackContent: View>(
        trackViewWithPlayback: TrackContent,
        bubble: MyLinguistBubbleState?,
        resolvedLinguistFontScale: CGFloat,
        bubbleFocusEnabled: Bool,
        availableSize: CGSize
    ) -> some View {
        let totalWidth = availableSize.width
        // Calculate exact widths for each section
        let bubbleWidth = max(0, totalWidth * iPadSplitRatio - iPadDividerThickness / 2)
        let trackWidth = max(0, totalWidth * (1 - iPadSplitRatio) - iPadDividerThickness / 2)
        logHorizontalSplitLayout(
            totalWidth: totalWidth,
            bubbleWidth: bubbleWidth,
            trackWidth: trackWidth
        )

        HStack(spacing: 0) {
            // Bubble area (left side, like iPhone landscape) - fixed width, clipped
            if let bubble {
                iPadBubbleContent(
                    bubble: bubble,
                    resolvedLinguistFontScale: resolvedLinguistFontScale,
                    bubbleFocusEnabled: bubbleFocusEnabled,
                    maxHeight: availableSize.height,
                    fillWidth: false
                )
                .frame(width: bubbleWidth, height: availableSize.height)
                .clipped()
            }

            // Divider
            iPadDivider(isVertical: false, availableSize: availableSize)

            // Tracks area (right side) - fixed width, clipped
            trackViewWithPlayback
                .frame(maxHeight: .infinity, alignment: .center)
                .frame(width: trackWidth)
                .clipped()
                .contentShape(Rectangle())
                .simultaneousGesture(swipeGesture, including: .all)
                .simultaneousGesture(selectionDragGesture, including: .gesture)
                .simultaneousGesture(backgroundPlaybackTapGesture, including: .all)
                .highPriorityGesture(trackMagnifyGesture, including: .all)
        }
        .padding(.leading, 24) // Extra left padding to avoid content clipping at left edge
        .frame(width: availableSize.width, height: availableSize.height)
    }

    // MARK: Divider

    @ViewBuilder
    func iPadDivider(isVertical: Bool, availableSize: CGSize) -> some View {
        let dividerColor = Color.white.opacity(isDraggingDivider ? 0.4 : 0.2)
        let handleColor = Color.white.opacity(isDraggingDivider ? 0.7 : 0.5)

        Group {
            if isVertical {
                // Horizontal divider (for vertical split)
                ZStack {
                    Rectangle()
                        .fill(dividerColor)
                        .frame(height: 1)
                    // Handle
                    RoundedRectangle(cornerRadius: iPadDividerHandleHeight / 2)
                        .fill(handleColor)
                        .frame(width: iPadDividerHandleWidth, height: iPadDividerHandleHeight)
                }
                .frame(height: iPadDividerThickness)
                .contentShape(Rectangle())
                .gesture(
                    DragGesture(minimumDistance: 1)
                        .onChanged { value in
                            if !isDraggingDivider {
                                isDraggingDivider = true
                                dividerDragStartRatio = iPadSplitRatio
                                iPadSplitLogger.debug("Divider drag started startRatio=\(dividerDragStartRatio, privacy: .public)")
                            }
                            let delta = value.translation.height / availableSize.height
                            let newRatio = (dividerDragStartRatio + delta)
                                .clamped(to: iPadMinSplitRatio...iPadMaxSplitRatio)
                            iPadSplitRatio = newRatio
                            iPadSplitLogger.debug(
                                "Divider drag delta=\(delta, privacy: .public), newRatio=\(newRatio, privacy: .public), availableHeight=\(availableSize.height, privacy: .public)"
                            )
                        }
                        .onEnded { _ in
                            isDraggingDivider = false
                            iPadSplitLogger.debug("Divider drag ended finalRatio=\(iPadSplitRatio, privacy: .public)")
                        }
                )
            } else {
                // Vertical divider (for horizontal split)
                ZStack {
                    Rectangle()
                        .fill(dividerColor)
                        .frame(width: 1)
                    // Handle
                    RoundedRectangle(cornerRadius: iPadDividerHandleHeight / 2)
                        .fill(handleColor)
                        .frame(width: iPadDividerHandleHeight, height: iPadDividerHandleWidth)
                }
                .frame(width: iPadDividerThickness)
                .contentShape(Rectangle())
                .gesture(
                    DragGesture(minimumDistance: 1)
                        .onChanged { value in
                            if !isDraggingDivider {
                                isDraggingDivider = true
                                dividerDragStartRatio = iPadSplitRatio
                            }
                            let delta = value.translation.width / availableSize.width
                            let newRatio = (dividerDragStartRatio + delta)
                                .clamped(to: iPadMinSplitRatio...iPadMaxSplitRatio)
                            iPadSplitRatio = newRatio
                        }
                        .onEnded { _ in
                            isDraggingDivider = false
                        }
                )
            }
        }
    }

    private func logVerticalSplitLayout(
        totalHeight: CGFloat,
        trackHeight: CGFloat,
        bubbleHeight: CGFloat
    ) -> some View {
        iPadSplitLogger.debug(
            "Vertical split ratio=\(iPadSplitRatio, privacy: .public), totalHeight=\(totalHeight, privacy: .public), trackHeight=\(trackHeight, privacy: .public), bubbleHeight=\(bubbleHeight, privacy: .public)"
        )
        return EmptyView()
    }

    private func logHorizontalSplitLayout(
        totalWidth: CGFloat,
        bubbleWidth: CGFloat,
        trackWidth: CGFloat
    ) -> some View {
        iPadSplitLogger.debug(
            "Horizontal split ratio=\(iPadSplitRatio, privacy: .public), totalWidth=\(totalWidth, privacy: .public), bubbleWidth=\(bubbleWidth, privacy: .public), trackWidth=\(trackWidth, privacy: .public)"
        )
        return EmptyView()
    }

    // MARK: Bubble Content

    @ViewBuilder
    func iPadBubbleContent(
        bubble: MyLinguistBubbleState,
        resolvedLinguistFontScale: CGFloat,
        bubbleFocusEnabled: Bool,
        maxHeight: CGFloat,
        fillWidth: Bool
    ) -> some View {
        ZStack(alignment: .top) {
            // Tap to dismiss area
            Color.clear
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .contentShape(Rectangle())
                .onTapGesture {
                    onCloseBubble()
                    if !audioCoordinator.isPlaying {
                        onTogglePlayback()
                    }
                }

            MyLinguistBubbleView(
                bubble: bubble,
                fontScale: resolvedLinguistFontScale,
                canIncreaseFont: canIncreaseLinguistFont,
                canDecreaseFont: canDecreaseLinguistFont,
                lookupLanguage: lookupLanguage,
                lookupLanguageOptions: lookupLanguageOptions,
                onLookupLanguageChange: onLookupLanguageChange,
                llmModel: llmModel,
                llmModelOptions: llmModelOptions,
                onLlmModelChange: onLlmModelChange,
                ttsVoice: ttsVoice,
                ttsVoiceOptions: ttsVoiceOptions,
                onTtsVoiceChange: onTtsVoiceChange,
                onIncreaseFont: onIncreaseLinguistFont,
                onDecreaseFont: onDecreaseLinguistFont,
                onClose: onCloseBubble,
                isFocusEnabled: bubbleFocusEnabled,
                focusBinding: $focusedArea,
                fillWidth: fillWidth,
                maxContentHeight: max(maxHeight - 120, 80),
                onPreviousToken: onBubblePreviousToken,
                onNextToken: onBubbleNextToken,
                onToggleLayoutDirection: onToggleLayoutDirection,
                isPinned: iPadBubblePinned,
                onTogglePin: onToggleBubblePin,
                onPlayFromNarration: onPlayFromNarration,
                keyboardNavigator: bubbleKeyboardNavigator
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
            .simultaneousGesture(bubbleMagnifyGesture, including: .all)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .contentShape(Rectangle())
        // Consume taps on bubble content
        .onTapGesture { /* consume tap */ }
        .simultaneousGesture(bubbleAreaSwipeGesture, including: .all)
        .background(GeometryReader { bubbleProxy in
            Color.clear.preference(
                key: InteractiveBubbleFrameKey.self,
                value: bubbleProxy.frame(in: .named(TextPlayerTokenCoordinateSpace.name))
            )
        })
    }
}
#endif
