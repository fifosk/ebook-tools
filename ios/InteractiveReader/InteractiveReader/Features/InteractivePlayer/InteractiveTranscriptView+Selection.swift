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

    /// Find the nearest token frame within a maximum distance threshold.
    /// Used for tap-to-lookup to be more forgiving than exact hit testing.
    func nearestTokenFrameForTap(at location: CGPoint, maxDistance: CGFloat = 20) -> TextPlayerTokenFrame? {
        let candidates = tokenFrames
        guard !candidates.isEmpty else { return nil }
        if let exact = candidates.first(where: { $0.frame.contains(location) }) {
            return exact
        }

        var bestMatch: TextPlayerTokenFrame?
        var bestDistance: CGFloat = .greatestFiniteMagnitude
        for candidate in candidates {
            let center = CGPoint(x: candidate.frame.midX, y: candidate.frame.midY)
            let distance = hypot(center.x - location.x, center.y - location.y)
            if distance < bestDistance && distance <= maxDistance {
                bestDistance = distance
                bestMatch = candidate
            }
        }
        return bestMatch
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
