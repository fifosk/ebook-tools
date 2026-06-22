import SwiftUI

#if canImport(UIKit)
import UIKit
#endif

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
