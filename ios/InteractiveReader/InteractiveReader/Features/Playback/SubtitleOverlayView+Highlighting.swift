import SwiftUI

struct SubtitlePlaybackHighlight: Equatable {
    let kind: VideoSubtitleLineKind
    let lineIndex: Int
    let tokenIndex: Int
}

extension SubtitleOverlayView {
    func playbackHighlight(in display: VideoSubtitleDisplay) -> SubtitlePlaybackHighlight? {
        guard isPlaying else { return nil }
        guard let line = playbackPrimaryLine(in: display) else { return nil }
        guard let tokenIndex = playbackTokenIndex(for: line, in: display) else { return nil }
        return SubtitlePlaybackHighlight(
            kind: line.kind,
            lineIndex: line.index,
            tokenIndex: tokenIndex
        )
    }

    func playbackShadowHighlight(
        for playbackHighlight: SubtitlePlaybackHighlight?,
        in display: VideoSubtitleDisplay
    ) -> SubtitlePlaybackHighlight? {
        guard let playbackHighlight else { return nil }
        let targetKind: VideoSubtitleLineKind
        switch playbackHighlight.kind {
        case .translation:
            targetKind = .transliteration
        case .transliteration:
            targetKind = .translation
        default:
            return nil
        }
        let candidates = display.lines.filter { $0.kind == targetKind && !$0.tokens.isEmpty }
        guard let targetLine = candidates.min(by: {
            abs($0.index - playbackHighlight.lineIndex) < abs($1.index - playbackHighlight.lineIndex)
        }) else {
            return nil
        }
        guard targetLine.tokens.indices.contains(playbackHighlight.tokenIndex) else { return nil }
        return SubtitlePlaybackHighlight(
            kind: targetLine.kind,
            lineIndex: targetLine.index,
            tokenIndex: playbackHighlight.tokenIndex
        )
    }

    func shadowSelection(
        from selection: VideoSubtitleWordSelection?,
        in display: VideoSubtitleDisplay
    ) -> VideoSubtitleWordSelection? {
        guard let selection else { return nil }
        let targetKind: VideoSubtitleLineKind
        switch selection.lineKind {
        case .translation:
            targetKind = .transliteration
        case .transliteration:
            targetKind = .translation
        default:
            return nil
        }
        let candidates = display.lines.filter { $0.kind == targetKind && !$0.tokens.isEmpty }
        guard let targetLine = candidates.min(by: { abs($0.index - selection.lineIndex) < abs($1.index - selection.lineIndex) })
            ?? candidates.first else {
            return nil
        }
        guard targetLine.tokens.indices.contains(selection.tokenIndex) else { return nil }
        return VideoSubtitleWordSelection(
            lineKind: targetLine.kind,
            lineIndex: targetLine.index,
            tokenIndex: selection.tokenIndex
        )
    }

    private func playbackPrimaryLine(in display: VideoSubtitleDisplay) -> VideoSubtitleDisplayLine? {
        let lines = display.lines.filter { !$0.tokens.isEmpty }
        guard !lines.isEmpty else { return nil }
        if let highlighted = lines.first(where: { $0.tokenStyles?.contains(.highlightCurrent) == true }) {
            return highlighted
        }
        if let highlighted = lines.first(where: { $0.tokenStyles?.contains(.highlightPrior) == true }) {
            return highlighted
        }
        if let translation = lines.first(where: { $0.kind == .translation }) {
            return translation
        }
        if let transliteration = lines.first(where: { $0.kind == .transliteration }) {
            return transliteration
        }
        if let original = lines.first(where: { $0.kind == .original }) {
            return original
        }
        return lines.first
    }

    private func playbackTokenIndex(
        for line: VideoSubtitleDisplayLine,
        in display: VideoSubtitleDisplay
    ) -> Int? {
        guard !line.tokens.isEmpty else { return nil }
        if let styles = line.tokenStyles {
            if let current = styles.firstIndex(where: { $0 == .highlightCurrent }) {
                return current
            }
            if let lastPrior = styles.lastIndex(where: { $0 == .highlightPrior }) {
                return lastPrior
            }
        }
        let clampedTime = min(max(currentTime, display.highlightStart), display.highlightEnd)
        let tokenRevealCutoff = clampedTime.isFinite ? clampedTime : display.highlightStart
        let epsilon = 1e-3
        if tokenRevealCutoff >= display.highlightEnd - epsilon {
            return line.tokens.count - 1
        }
        let revealedCount = line.revealTimes.filter { $0 <= tokenRevealCutoff + epsilon }.count
        if revealedCount > 0 {
            return min(revealedCount - 1, line.tokens.count - 1)
        }
        if tokenRevealCutoff >= display.highlightStart - epsilon {
            return 0
        }
        return nil
    }
}
