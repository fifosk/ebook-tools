import SwiftUI

extension InteractiveTranscriptView {
    func updateSelectionRange(at location: CGPoint) {
        guard let anchor = dragSelectionAnchor else { return }
        guard let token = nearestTokenFrame(at: location) else { return }
        let selection = TextPlayerWordSelection(
            sentenceIndex: token.sentenceIndex,
            variantKind: token.variantKind,
            tokenIndex: token.tokenIndex
        )
        guard anchor.sentenceIndex == selection.sentenceIndex,
              anchor.variantKind == selection.variantKind else {
            return
        }
        let range = TextPlayerWordSelectionRange(
            sentenceIndex: anchor.sentenceIndex,
            variantKind: anchor.variantKind,
            anchorIndex: anchor.tokenIndex,
            focusIndex: selection.tokenIndex
        )
        onUpdateSelectionRange(range, selection)
        scheduleDragLookup()
    }

    func nearestTokenFrame(at location: CGPoint) -> TextPlayerTokenFrame? {
        let candidates: [TextPlayerTokenFrame]
        if let anchor = dragSelectionAnchor {
            candidates = tokenFrames.filter { frame in
                frame.sentenceIndex == anchor.sentenceIndex && frame.variantKind == anchor.variantKind
            }
        } else {
            candidates = tokenFrames
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

    func tokenFrameContaining(_ location: CGPoint) -> TextPlayerTokenFrame? {
        let candidates = tokenFrames
        guard !candidates.isEmpty else { return nil }
        if let exact = candidates.first(where: { $0.frame.contains(location) }) {
            return exact
        }
        return nil
    }

    /// Find the nearest token frame within a bounded, row-aware threshold.
    /// Used for tap-to-seek/lookup to be more forgiving than exact hit testing
    /// without jumping to tokens on adjacent lines.
    func nearestTokenFrameForTap(
        at location: CGPoint,
        horizontalTolerance: CGFloat = 9,
        verticalTolerance: CGFloat = 8
    ) -> TextPlayerTokenFrame? {
        let candidates = tokenFrames
        guard !candidates.isEmpty else { return nil }
        if let exact = candidates.first(where: { $0.frame.contains(location) }) {
            return exact
        }

        var bestMatch: TextPlayerTokenFrame?
        var bestDistance: CGFloat = .greatestFiniteMagnitude
        for candidate in candidates {
            let rowBand = candidate.frame.insetBy(dx: -horizontalTolerance, dy: -verticalTolerance)
            guard rowBand.contains(location) else { continue }
            let distance = tokenTapDistance(from: location, to: candidate.frame)
            if distance < bestDistance {
                bestDistance = distance
                bestMatch = candidate
            }
        }
        return bestMatch
    }

    func tokenTapDistance(from location: CGPoint, to frame: CGRect) -> CGFloat {
        let dx = max(frame.minX - location.x, 0, location.x - frame.maxX)
        let dy = max(frame.minY - location.y, 0, location.y - frame.maxY)
        return hypot(dx, dy)
    }

    func handleNearbyTokenTap(_ tokenFrame: TextPlayerTokenFrame, shouldPlay: Bool = true) {
        suppressPlaybackTask?.cancel()
        suppressPlaybackToggle = true
        suppressPlaybackTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 350_000_000)
            suppressPlaybackToggle = false
        }
        let wasPaused = !audioCoordinator.isPlaying
        let effectiveShouldPlay = shouldPlay && !wasPaused
        onSeekToken(
            tokenFrame.sentenceIndex,
            tokenFrame.sentenceNumber,
            tokenFrame.variantKind,
            tokenFrame.tokenIndex,
            nil,
            effectiveShouldPlay
        )
        if wasPaused, shouldPlay {
            onLookupToken(
                tokenFrame.sentenceIndex,
                tokenFrame.variantKind,
                tokenFrame.tokenIndex,
                tokenFrame.token
            )
        }
    }

    func scheduleDragLookup() {
        dragLookupTask?.cancel()
        dragLookupTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: dragLookupDelayNanos)
            guard !Task.isCancelled else { return }
            guard !audioCoordinator.isPlaying else { return }
            onLookup()
        }
    }
}
