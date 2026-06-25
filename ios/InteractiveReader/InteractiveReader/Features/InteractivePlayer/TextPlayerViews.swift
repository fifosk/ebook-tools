import SwiftUI

struct TextPlayerFrame: View {
    let sentences: [TextPlayerSentenceDisplay]
    let selection: TextPlayerWordSelection?
    let selectionRange: TextPlayerWordSelectionRange?
    let onTokenLookup: ((Int, TextPlayerVariantKind, Int, String) -> Void)?
    let onTokenSeek: ((Int, Int?, TextPlayerVariantKind, Int, Double?, Bool) -> Void)?
    let fontScale: CGFloat
    let playbackPrimaryKind: TextPlayerVariantKind?
    let visibleTracks: Set<TextPlayerVariantKind>
    let onToggleTrack: ((TextPlayerVariantKind) -> Void)?
    let onTokenFramesChange: (([TextPlayerTokenFrame]) -> Void)?
    let onTapExclusionFramesChange: (([CGRect]) -> Void)?
    let shouldReportTokenFrames: Bool
    var isLoading: Bool = false
    var loadErrorMessage: String?
    var onRetryLoad: (() -> Void)?

    var body: some View {
        VStack(spacing: 10) {
            if sentences.isEmpty {
                if isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                } else if let loadErrorMessage {
                    VStack(spacing: 10) {
                        Text(loadErrorMessage)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                        if let onRetryLoad {
                            Button("Retry") {
                                onRetryLoad()
                            }
                            .buttonStyle(.borderedProminent)
                            .accessibilityIdentifier("interactiveTranscriptRetryButton")
                        }
                    }
                    .frame(maxWidth: .infinity)
                } else {
                    Text("Waiting for transcript...")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity)
                }
            } else {
                ForEach(sentences) { sentence in
                    TextPlayerSentenceView(
                        sentence: sentence,
                        selection: selection,
                        selectionRange: selectionRange,
                        playbackPrimaryKind: playbackPrimaryKind,
                        visibleTracks: visibleTracks,
                        onToggleTrack: onToggleTrack,
                        onTokenLookup: onTokenLookup,
                        onTokenSeek: onTokenSeek,
                        fontScale: fontScale,
                        shouldReportTokenFrames: shouldReportTokenFrames
                    )
                }
            }
        }
        .padding(framePadding)
        .frame(maxWidth: .infinity)
        .background(TextPlayerTheme.frameBackground)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .onPreferenceChange(TextPlayerTokenFramePreferenceKey.self, perform: handleTokenFramesChange)
        .onPreferenceChange(TextPlayerTapExclusionPreferenceKey.self, perform: handleTapExclusionFramesChange)
    }

    private var framePadding: CGFloat {
        #if os(tvOS)
        return 20
        #else
        return 14
        #endif
    }

    private func handleTokenFramesChange(_ frames: [TextPlayerTokenFrame]) {
        onTokenFramesChange?(frames)
    }

    private func handleTapExclusionFramesChange(_ frames: [CGRect]) {
        onTapExclusionFramesChange?(frames)
    }
}

extension View {
    @ViewBuilder
    func applyIf<T: View>(_ condition: Bool, transform: (Self) -> T) -> some View {
        if condition {
            transform(self)
        } else {
            self
        }
    }
}

enum TextPlayerTheme {
    static let frameBackground = Color.black
    static let sentenceBackground = Color(red: 1.0, green: 0.878, blue: 0.521).opacity(0.04)
    static let sentenceActiveBackground = Color(red: 1.0, green: 0.647, blue: 0.0).opacity(0.16)
    static let sentenceActiveShadow = Color(red: 1.0, green: 0.549, blue: 0.0).opacity(0.18)
    static let lineLabel = Color.white.opacity(0.45)
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
