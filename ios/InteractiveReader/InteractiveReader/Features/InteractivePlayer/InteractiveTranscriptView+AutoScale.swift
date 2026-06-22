import SwiftUI

struct InteractiveAutoScaleTrackHeightKey: PreferenceKey {
    static var defaultValue: CGFloat = 0

    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = max(value, nextValue())
    }
}

// MARK: - Track Auto Scale

extension InteractiveTranscriptView {
    var sentenceSignature: String {
        sentences.map(\.id).joined(separator: "|")
    }

    func handleAutoScaleTrackHeightChange(
        _ value: CGFloat,
        shouldAutoScaleTracks: Bool,
        textHeightLimit: CGFloat
    ) {
        guard shouldAutoScaleTracks else { return }
        trackHeight = value
        lastMeasuredTrackHeight = value
        lastAvailableTrackHeight = textHeightLimit
        if effectiveTrackFontScale == 0 {
            autoScaleNeedsUpdate = true
        }
        applyAutoScaleIfNeeded()
    }

    func handleLayoutSizeChange(
        _ newSize: CGSize,
        shouldAutoScaleTracks: Bool,
        textHeightLimit: CGFloat
    ) {
        guard shouldAutoScaleTracks else { return }
        guard newSize != lastLayoutSize else { return }
        lastLayoutSize = newSize
        lastAvailableTrackHeight = textHeightLimit
        requestAutoScaleUpdate(delay: 250_000_000)
    }

    func handleTrackFontScaleChange(shouldAutoScaleTracks: Bool) {
        guard shouldAutoScaleTracks else { return }
        effectiveTrackFontScale = trackFontScale
        requestAutoScaleUpdate()
    }

    func handleVisibleTracksChange(shouldAutoScaleTracks: Bool) {
        guard shouldAutoScaleTracks else { return }
        autoScaleNeedsUpdate = true
        requestAutoScaleUpdate()
    }

    func handleSentenceSignatureChange(shouldAutoScaleTracks: Bool) {
        guard shouldAutoScaleTracks else { return }
        autoScaleNeedsUpdate = true
        requestAutoScaleUpdate()
    }

    func handleAutoScaleEnabledChange(_ enabled: Bool) {
        effectiveTrackFontScale = trackFontScale
        autoScaleTask?.cancel()
        autoScaleTask = nil
        autoScaleNeedsUpdate = enabled
        if enabled {
            requestAutoScaleUpdate()
        }
    }

    func handleBubbleChange(
        oldBubble: MyLinguistBubbleState?,
        newBubble: MyLinguistBubbleState?,
        shouldAutoScaleTracks: Bool,
        textHeightLimit: CGFloat
    ) {
        // Recalculate auto-scale when the phone bubble appears or disappears.
        guard shouldAutoScaleTracks, isPhone else { return }
        let bubbleWasOpen = oldBubble != nil
        let bubbleIsOpen = newBubble != nil
        guard bubbleWasOpen != bubbleIsOpen else { return }
        lastAvailableTrackHeight = textHeightLimit
        autoScaleNeedsUpdate = true
        requestAutoScaleUpdate(delay: 100_000_000)
    }

    private var autoScaleHeightTolerance: CGFloat {
        isPhone ? 8 : 4
    }

    private var autoScaleFloor: CGFloat {
        guard isPhone else { return minTrackFontScale }
        return max(0.75, minTrackFontScale * 0.75)
    }

    private func updateEffectiveTrackFontScale(measuredHeight: CGFloat, availableHeight: CGFloat) {
        guard !isTV else { return }
        guard measuredHeight > 0, availableHeight > 0 else {
            if effectiveTrackFontScale != trackFontScale {
                effectiveTrackFontScale = trackFontScale
            }
            return
        }
        let currentScale = effectiveTrackFontScale == 0 ? trackFontScale : effectiveTrackFontScale
        let fitHeight = max(availableHeight - autoScaleHeightTolerance, 0)
        let ratio = fitHeight / measuredHeight
        let proposed = currentScale * ratio
        let clamped = max(autoScaleFloor, min(maxTrackFontScale, proposed))
        if abs(clamped - currentScale) > 0.02 {
            effectiveTrackFontScale = clamped
        }
    }

    private func requestAutoScaleUpdate(delay: UInt64 = 120_000_000) {
        guard autoScaleEnabled, !isTV else { return }
        autoScaleNeedsUpdate = true
        autoScaleTask?.cancel()
        autoScaleTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: delay)
            applyAutoScaleIfNeeded()
        }
    }

    private func applyAutoScaleIfNeeded() {
        guard autoScaleNeedsUpdate else { return }
        guard lastMeasuredTrackHeight > 0, lastAvailableTrackHeight > 0 else { return }
        updateEffectiveTrackFontScale(
            measuredHeight: lastMeasuredTrackHeight,
            availableHeight: lastAvailableTrackHeight
        )
        autoScaleNeedsUpdate = false
    }
}
