import SwiftUI

#if canImport(UIKit)
import UIKit
#endif

private struct SubtitlePlaybackHighlight: Equatable {
    let kind: VideoSubtitleLineKind
    let lineIndex: Int
    let tokenIndex: Int
}

struct SubtitleOverlayView: View {
    let cues: [VideoSubtitleCue]
    let currentTime: Double
    let isPlaying: Bool
    let visibility: SubtitleVisibility
    let fontScale: CGFloat
    let selection: VideoSubtitleWordSelection?
    let selectionRange: VideoSubtitleWordSelectionRange?
    let lineAlignment: HorizontalAlignment
    let onTokenLookup: ((VideoSubtitleTokenReference) -> Void)?
    let onTokenSeek: ((VideoSubtitleTokenReference) -> Void)?
    let onTokenFramesChange: (([VideoSubtitleTokenFrame]) -> Void)?
    let shouldReportTokenFrames: Bool
    let onResetFont: (() -> Void)?
    let onMagnify: ((CGFloat) -> Void)?

    #if os(iOS)
    @State private var magnifyStartScale: CGFloat?
    #endif

    var body: some View {
        if let display = VideoSubtitleDisplayBuilder.build(
            cues: cues,
            time: currentTime,
            visibility: visibility
        ) {
            let playbackHighlight = playbackHighlight(in: display)
            let playbackShadowHighlight = playbackShadowHighlight(
                for: playbackHighlight,
                in: display
            )
            let shadowSelectionValue = shadowSelection(from: selection, in: display)
            let content = ZStack(alignment: .topTrailing) {
                VStack(alignment: lineAlignment, spacing: 8) {
                    ForEach(display.lines) { line in
                        SubtitleTokenLineView(
                            line: line,
                            highlightStart: display.highlightStart,
                            highlightEnd: display.highlightEnd,
                            currentTime: currentTime,
                            selection: selection,
                            selectionRange: selectionRange,
                            shadowSelection: shadowSelectionValue,
                            playbackHighlight: playbackHighlight,
                            playbackShadowHighlight: playbackShadowHighlight,
                            fontScale: clampedFontScale,
                            alignment: lineAlignment,
                            onTokenLookup: onTokenLookup,
                            onTokenSeek: onTokenSeek,
                            shouldReportTokenFrames: shouldReportTokenFrames
                        )
                    }
                }
                #if os(iOS)
                if let onResetFont {
                    Button(action: onResetFont) {
                        Image(systemName: "arrow.counterclockwise")
                            .font(.caption2.weight(.semibold))
                            .padding(6)
                            .background(.black.opacity(0.4), in: Circle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Reset subtitle size")
                }
                #endif
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(.black.opacity(0.6), in: RoundedRectangle(cornerRadius: 12))
            .padding(.bottom, 24)
            .transition(.opacity)
            .applyIf(shouldReportTokenFrames) { view in
                view.onPreferenceChange(
                    VideoSubtitleTokenFramePreferenceKey.self,
                    perform: handleTokenFramesChange
                )
            }
            Group {
                if lineAlignment == .leading {
                    HStack(spacing: 0) {
                        content
                        Spacer(minLength: 0)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                } else if lineAlignment == .trailing {
                    HStack(spacing: 0) {
                        Spacer(minLength: 0)
                        content
                    }
                    .frame(maxWidth: .infinity, alignment: .trailing)
                } else {
                    content
                        .frame(maxWidth: .infinity, alignment: .center)
                }
            }
            #if os(iOS)
            .simultaneousGesture(magnifyGesture, including: .gesture)
            #endif
        } else {
            Color.clear
                .onAppear(perform: clearTokenFrames)
        }
    }

    private var clampedFontScale: CGFloat {
        max(0.7, min(fontScale, 2.0))
    }

    private func handleTokenFramesChange(_ frames: [VideoSubtitleTokenFrame]) {
        onTokenFramesChange?(frames)
    }

    private func clearTokenFrames() {
        onTokenFramesChange?([])
    }

    private func playbackHighlight(in display: VideoSubtitleDisplay) -> SubtitlePlaybackHighlight? {
        guard isPlaying else { return nil }
        guard let line = playbackPrimaryLine(in: display) else { return nil }
        guard let tokenIndex = playbackTokenIndex(for: line, in: display) else { return nil }
        return SubtitlePlaybackHighlight(
            kind: line.kind,
            lineIndex: line.index,
            tokenIndex: tokenIndex
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

    private func playbackShadowHighlight(
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

    private func shadowSelection(
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

    #if os(iOS)
    private var magnifyGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                guard let onMagnify else { return }
                if magnifyStartScale == nil {
                    magnifyStartScale = clampedFontScale
                }
                let startScale = magnifyStartScale ?? clampedFontScale
                onMagnify(startScale * value)
            }
            .onEnded { _ in
                magnifyStartScale = nil
            }
    }
    #endif
}

private struct SubtitleTokenLineView: View {
    let line: VideoSubtitleDisplayLine
    let highlightStart: Double
    let highlightEnd: Double
    let currentTime: Double
    let selection: VideoSubtitleWordSelection?
    let selectionRange: VideoSubtitleWordSelectionRange?
    let shadowSelection: VideoSubtitleWordSelection?
    let playbackHighlight: SubtitlePlaybackHighlight?
    let playbackShadowHighlight: SubtitlePlaybackHighlight?
    let fontScale: CGFloat
    let alignment: HorizontalAlignment
    let onTokenLookup: ((VideoSubtitleTokenReference) -> Void)?
    let onTokenSeek: ((VideoSubtitleTokenReference) -> Void)?
    let shouldReportTokenFrames: Bool

    var body: some View {
        TokenFlowLayout(
            itemSpacing: tokenItemSpacing,
            lineSpacing: tokenLineSpacing,
            alignment: alignment
        ) {
            ForEach(displayTokenIndices, id: \.self) { index in
                let token = line.tokens[index]
                let isRangeSelected = selectedTokenRange?.contains(index) ?? false
                SubtitleTokenWordView(
                    text: token,
                    color: tokenColor(for: tokenState(for: index)),
                    isSelected: isSelectedToken(index) || isRangeSelected,
                    isShadowSelected: isShadowSelectedToken(index),
                    isPlaybackSelected: isPlaybackSelectedToken(index),
                    isPlaybackShadowSelected: isPlaybackShadowSelectedToken(index),
                    fontScale: fontScale,
                    horizontalPadding: tokenHorizontalPadding,
                    verticalPadding: tokenVerticalPadding,
                    cornerRadius: tokenCornerRadius,
                    onTap: {
                        onTokenSeek?(VideoSubtitleTokenReference(
                            lineKind: line.kind,
                            lineIndex: line.index,
                            tokenIndex: index,
                            token: token,
                            seekTime: tokenSeekTime(for: index)
                        ))
                    },
                    onLookup: {
                        onTokenLookup?(VideoSubtitleTokenReference(
                            lineKind: line.kind,
                            lineIndex: line.index,
                            tokenIndex: index,
                            token: token,
                            seekTime: tokenSeekTime(for: index)
                        ))
                    }
                )
                .applyIf(shouldReportTokenFrames) { view in
                    view.background(
                        GeometryReader { proxy in
                            Color.clear.preference(
                                key: VideoSubtitleTokenFramePreferenceKey.self,
                                value: [
                                    VideoSubtitleTokenFrame(
                                        lineKind: line.kind,
                                        lineIndex: line.index,
                                        tokenIndex: index,
                                        frame: proxy.frame(in: .named(VideoSubtitleTokenCoordinateSpace.name))
                                    )
                                ]
                            )
                        }
                    )
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: frameAlignment)
    }

    private var frameAlignment: Alignment {
        switch alignment {
        case .leading:
            return .leading
        case .trailing:
            return .trailing
        default:
            return .center
        }
    }

    private var tokenRevealCutoff: Double {
        let clamped = min(max(currentTime, highlightStart), highlightEnd)
        return clamped.isFinite ? clamped : highlightStart
    }

    private var revealedCount: Int {
        let epsilon = 1e-3
        let count = line.revealTimes.filter { $0 <= tokenRevealCutoff + epsilon }.count
        if tokenRevealCutoff >= highlightEnd - epsilon {
            return line.tokens.count
        }
        return min(max(count, 0), line.tokens.count)
    }

    private var displayTokenIndices: [Int] {
        Array(line.tokens.indices)
    }

    private func isSelectedToken(_ index: Int) -> Bool {
        guard let selection else { return false }
        return selection.lineKind == line.kind
            && selection.lineIndex == line.index
            && selection.tokenIndex == index
    }

    private func isShadowSelectedToken(_ index: Int) -> Bool {
        guard let shadowSelection else { return false }
        return shadowSelection.lineKind == line.kind
            && shadowSelection.lineIndex == line.index
            && shadowSelection.tokenIndex == index
    }

    private var selectedTokenRange: ClosedRange<Int>? {
        guard let selectionRange,
              selectionRange.lineKind == line.kind,
              selectionRange.lineIndex == line.index else { return nil }
        guard !line.tokens.isEmpty else { return nil }
        let maxIndex = line.tokens.count - 1
        let startIndex = max(0, min(selectionRange.startIndex, maxIndex))
        let endIndex = max(0, min(selectionRange.endIndex, maxIndex))
        guard startIndex <= endIndex else { return nil }
        return startIndex...endIndex
    }

    private func isPlaybackSelectedToken(_ index: Int) -> Bool {
        guard let playbackHighlight else { return false }
        guard line.kind == playbackHighlight.kind else { return false }
        guard line.index == playbackHighlight.lineIndex else { return false }
        return playbackHighlight.tokenIndex == index
    }

    private func isPlaybackShadowSelectedToken(_ index: Int) -> Bool {
        guard let playbackShadowHighlight else { return false }
        guard line.kind == playbackShadowHighlight.kind else { return false }
        guard line.index == playbackShadowHighlight.lineIndex else { return false }
        return playbackShadowHighlight.tokenIndex == index
    }

    private func tokenState(for index: Int) -> SubtitleTokenState {
        if let styles = line.tokenStyles, styles.indices.contains(index) {
            switch styles[index] {
            case .highlightPrior:
                return .past
            case .highlightCurrent:
                return .current
            case .base:
                return .future
            }
        }
        guard shouldHighlightLine else { return .future }
        if tokenRevealCutoff <= highlightStart {
            return .future
        }
        if tokenRevealCutoff >= highlightEnd {
            return .past
        }
        if revealedCount == 0 {
            return .future
        }
        if index < max(revealedCount - 1, 0) {
            return .past
        }
        if index == max(revealedCount - 1, 0) {
            return .current
        }
        return .future
    }

    private var shouldHighlightLine: Bool {
        line.kind == .translation || line.kind == .transliteration || line.kind == .unknown
    }

    private func tokenColor(for state: SubtitleTokenState) -> Color {
        switch state {
        case .past:
            return SubtitleOverlayTheme.progress
        case .current:
            switch line.kind {
            case .original:
                return SubtitleOverlayTheme.originalCurrent
            case .translation, .unknown:
                return SubtitleOverlayTheme.translationCurrent
            case .transliteration:
                return SubtitleOverlayTheme.transliterationCurrent
            }
        case .future:
            switch line.kind {
            case .original:
                return SubtitleOverlayTheme.original
            case .translation, .unknown:
                return SubtitleOverlayTheme.translation
            case .transliteration:
                return SubtitleOverlayTheme.transliteration
            }
        }
    }

    private func tokenSeekTime(for index: Int) -> Double? {
        guard line.revealTimes.indices.contains(index) else { return nil }
        let value = line.revealTimes[index]
        return value.isFinite ? value : nil
    }

    private var tokenItemSpacing: CGFloat {
        #if os(tvOS)
        return 10
        #else
        return 8
        #endif
    }

    private var tokenLineSpacing: CGFloat {
        #if os(tvOS)
        return 8
        #else
        return 6
        #endif
    }

    private var tokenHorizontalPadding: CGFloat {
        #if os(tvOS)
        return 4
        #else
        return 3
        #endif
    }

    private var tokenVerticalPadding: CGFloat {
        #if os(tvOS)
        return 2
        #else
        return 1
        #endif
    }

    private var tokenCornerRadius: CGFloat {
        #if os(tvOS)
        return 6
        #else
        return 4
        #endif
    }

}

private struct SubtitleTokenWordView: View {
    let text: String
    let color: Color
    let isSelected: Bool
    let isShadowSelected: Bool
    let isPlaybackSelected: Bool
    let isPlaybackShadowSelected: Bool
    let fontScale: CGFloat
    let horizontalPadding: CGFloat
    let verticalPadding: CGFloat
    let cornerRadius: CGFloat
    let onTap: () -> Void
    let onLookup: () -> Void

    var body: some View {
        let isPrimaryHighlight = isSelected || isPlaybackSelected
        let isShadowHighlight = !isPrimaryHighlight && (isShadowSelected || isPlaybackShadowSelected)
        Text(text)
            .lineLimit(1)
            .minimumScaleFactor(0.7)
            .allowsTightening(true)
            .font(tokenFont)
            .padding(.horizontal, horizontalPadding)
            .padding(.vertical, verticalPadding)
            .foregroundStyle(isPrimaryHighlight ? SubtitleOverlayTheme.selectionText : color)
            .background(
                Group {
                    if isPrimaryHighlight || isShadowHighlight {
                        RoundedRectangle(cornerRadius: cornerRadius)
                            .fill(isPrimaryHighlight ? SubtitleOverlayTheme.selectionGlow : SubtitleOverlayTheme.selectionShadow)
                    }
                }
            )
            #if !os(tvOS)
            .gesture(tokenTapGesture)
            #endif
            #if os(iOS)
            .contextMenu {
                Button("Look Up") {
                    DictionaryLookupPresenter.show(term: text)
                }
                Button("Copy") {
                    UIPasteboard.general.string = text
                }
            }
            #endif
    }

    #if !os(tvOS)
    private var tokenTapGesture: some Gesture {
        let doubleTap = TapGesture(count: 2)
            .onEnded(onLookup)
        let singleTap = TapGesture(count: 1)
            .onEnded(onTap)
        return doubleTap.exclusively(before: singleTap)
    }
    #endif

    private var tokenFont: Font {
        #if os(tvOS)
        let baseSize = UIFont.preferredFont(forTextStyle: .title2).pointSize
        return .system(size: baseSize * fontScale, weight: .semibold)
        #else
        let baseSize = UIFont.preferredFont(forTextStyle: .title3).pointSize
        return .system(size: baseSize * fontScale, weight: .semibold)
        #endif
    }
}

private enum SubtitleTokenState {
    case past
    case current
    case future
}

enum VideoSubtitleTokenStyle {
    case base
    case highlightPrior
    case highlightCurrent
}

private enum SubtitleOverlayTheme {
    static let original = Color(red: 1.0, green: 0.831, blue: 0.0)
    static let translation = Color(red: 0.204, green: 0.827, blue: 0.6)
    static let transliteration = Color(red: 0.176, green: 0.831, blue: 0.749)
    static let progress = Color(red: 1.0, green: 0.549, blue: 0.0)
    static let selectionGlow = Color(red: 1.0, green: 0.549, blue: 0.0).opacity(0.6)
    static let selectionShadow = Color(red: 1.0, green: 0.549, blue: 0.0).opacity(0.25)
    static let selectionText = Color.black
    static let originalCurrent = Color.white
    static let translationCurrent = Color(red: 0.996, green: 0.941, blue: 0.541)
    static let transliterationCurrent = Color(red: 0.996, green: 0.976, blue: 0.765)
}
