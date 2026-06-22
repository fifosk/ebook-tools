import SwiftUI

// MARK: - iOS Subtitle Interaction

#if os(iOS)
extension VideoPlayerOverlayView {
    var subtitleDragOffset: CGSize {
        let rawHeight = subtitleVerticalOffset + subtitleDragTranslation
        let maxHeight = allowSubtitleDownwardDrag ? subtitleBottomPadding : 0
        let clampedHeight = min(rawHeight, maxHeight)
        return CGSize(width: 0, height: clampedHeight)
    }

    var subtitleVerticalOffset: CGFloat {
        get { CGFloat(subtitleVerticalOffsetValue) }
        nonmutating set { subtitleVerticalOffsetValue = Double(newValue) }
    }

    var subtitleDragGesture: some Gesture {
        DragGesture(minimumDistance: 10, coordinateSpace: .local)
            .onChanged(handleSubtitleDragChange)
            .onEnded(handleSubtitleDragEnd)
    }

    var subtitleSelectionDragGesture: some Gesture {
        DragGesture(minimumDistance: 8, coordinateSpace: .named(VideoSubtitleTokenCoordinateSpace.name))
            .onChanged(handleSubtitleSelectionDragChange)
            .onEnded(handleSubtitleSelectionDragEnd)
    }

    func handleSubtitleDragChange(_ value: DragGesture.Value) {
        guard abs(value.translation.height) >= abs(value.translation.width) else { return }
        subtitleDragTranslation = value.translation.height
    }

    func handleSubtitleDragEnd(_ value: DragGesture.Value) {
        guard abs(value.translation.height) >= abs(value.translation.width) else {
            subtitleDragTranslation = 0
            return
        }
        let proposedHeight = subtitleVerticalOffset + value.translation.height
        let maxHeight = allowSubtitleDownwardDrag ? subtitleBottomPadding : 0
        subtitleVerticalOffset = min(proposedHeight, maxHeight)
        subtitleDragTranslation = 0
    }

    func handleSubtitleSelectionDragChange(_ value: DragGesture.Value) {
        guard VideoPlayerPlatform.isPad else { return }
        guard !isPlaying else { return }
        if dragSelectionAnchor == nil {
            guard let anchorToken = tokenFrameContaining(value.startLocation) else { return }
            dragSelectionAnchor = VideoSubtitleWordSelection(
                lineKind: anchorToken.lineKind,
                lineIndex: anchorToken.lineIndex,
                tokenIndex: anchorToken.tokenIndex
            )
        }
        updateSubtitleSelectionRange(at: value.location)
    }

    func handleSubtitleSelectionDragEnd(_ value: DragGesture.Value) {
        dragSelectionAnchor = nil
    }

    func updateSubtitleSelectionRange(at location: CGPoint) {
        guard let anchor = dragSelectionAnchor else { return }
        guard let token = nearestTokenFrame(at: location) else { return }
        let selection = VideoSubtitleWordSelection(
            lineKind: token.lineKind,
            lineIndex: token.lineIndex,
            tokenIndex: token.tokenIndex
        )
        guard anchor.lineKind == selection.lineKind,
              anchor.lineIndex == selection.lineIndex else { return }
        let range = VideoSubtitleWordSelectionRange(
            lineKind: anchor.lineKind,
            lineIndex: anchor.lineIndex,
            anchorIndex: anchor.tokenIndex,
            focusIndex: selection.tokenIndex
        )
        onUpdateSubtitleSelectionRange(range, selection)
        scheduleSubtitleDragLookup()
    }

    func nearestTokenFrame(at location: CGPoint) -> VideoSubtitleTokenFrame? {
        let candidates: [VideoSubtitleTokenFrame]
        if let anchor = dragSelectionAnchor {
            candidates = subtitleTokenFrames.filter {
                $0.lineKind == anchor.lineKind && $0.lineIndex == anchor.lineIndex
            }
        } else {
            candidates = subtitleTokenFrames
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

    func tokenFrameContaining(_ location: CGPoint) -> VideoSubtitleTokenFrame? {
        subtitleTokenFrames.first(where: { $0.frame.contains(location) })
    }

    func scheduleSubtitleDragLookup() {
        dragLookupTask?.cancel()
        dragLookupTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: dragLookupDelayNanos)
            guard !Task.isCancelled else { return }
            guard !isPlaying else { return }
            onSubtitleLookup()
        }
    }

    func resetSubtitleSelectionDrag() {
        dragSelectionAnchor = nil
        dragLookupTask?.cancel()
        dragLookupTask = nil
    }

    func resolveSubtitleInteractionFrame(from frames: [VideoSubtitleTokenFrame]) -> CGRect {
        guard !frames.isEmpty else { return .null }
        let union = frames.reduce(CGRect.null) { result, frame in
            result.union(frame.frame)
        }
        guard !union.isNull else { return union }
        return union.insetBy(dx: -8, dy: -8)
    }
}
#endif

// MARK: - Computed Properties

extension VideoPlayerOverlayView {
    var videoTimelineLabel: String? {
        guard duration.isFinite, duration > 0, currentTime.isFinite else { return nil }
        let played = min(max(currentTime, 0), duration)
        let remaining = max(duration - played, 0)
        let base = "\(VideoPlayerTimeFormatter.formatDuration(played)) / \(VideoPlayerTimeFormatter.formatDuration(remaining))"
        if let jobRemainingLabel {
            return "\(base) · \(jobRemainingLabel)"
        }
        return base
    }

    var segmentHeaderLabel: String? {
        let chunkLabel: String?
        if segmentOptions.count > 1 {
            if let selectedSegmentID,
               let index = segmentOptions.firstIndex(where: { $0.id == selectedSegmentID }) {
                chunkLabel = "C:\(index + 1)/\(segmentOptions.count)"
            } else {
                chunkLabel = "C:1/\(segmentOptions.count)"
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

    var hasOptions: Bool {
        !tracks.isEmpty || segmentOptions.count > 1
    }

    var hasInfoBadge: Bool {
        !metadata.title.isEmpty || (metadata.subtitle?.isEmpty == false) || metadata.artworkURL != nil
    }
}
