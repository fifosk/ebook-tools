import SwiftUI

#if DEBUG
extension InteractivePlayerView {
    @ViewBuilder
    var e2eBubbleResumeLayer: some View {
        #if os(iOS)
        if ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" {
            VStack {
                HStack {
                    Spacer()
                    Button("E2E Bubble Resume Setup") {
                        prepareBubblePronunciationResumeForE2E()
                    }
                    .font(.caption2)
                    .buttonStyle(.borderedProminent)
                    .accessibilityIdentifier("e2eBubblePronunciationResumeButton")
                    .accessibilityLabel("e2eBubblePronunciationResumeButton")
                }
                Spacer()
            }
            .padding()
        }
        #else
        EmptyView()
        #endif
    }

    @MainActor
    func prepareBubblePronunciationResumeForE2E() {
        guard viewModel.selectedChunk != nil else { return }
        linguistBubble = MyLinguistBubbleState(
            query: "resume",
            status: .ready,
            answer: "E2E pronunciation resume probe",
            model: "e2e",
            lookupSource: .cache,
            pronunciationLanguage: "en-US"
        )
        pausePlaybackForLinguistLookupIfNeeded()
        pronunciationSpeaker.speakFallback("resume", language: "en-US")
        requestKeyboardShortcutFocus()
    }
}
#else
extension InteractivePlayerView {
    @ViewBuilder
    var e2eBubbleResumeLayer: some View {
        EmptyView()
    }
}
#endif
