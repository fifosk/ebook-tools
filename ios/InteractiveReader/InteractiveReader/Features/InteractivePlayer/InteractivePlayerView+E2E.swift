import SwiftUI

#if DEBUG
extension Notification.Name {
    static let e2eBubblePronunciationResume = Notification.Name(
        "com.interactivereader.e2e.bubblePronunciationResume"
    )
}

extension InteractivePlayerView {
    @ViewBuilder
    var e2eBubbleResumeLayer: some View {
        if ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" {
            Color.clear
                .accessibilityHidden(true)
                .allowsHitTesting(false)
                .onReceive(NotificationCenter.default.publisher(for: .e2eBubblePronunciationResume)) { _ in
                    prepareBubblePronunciationResumeForE2E()
                }
        } else {
            EmptyView()
        }
    }

    @MainActor
    func prepareBubblePronunciationResumeForE2E() {
        #if os(iOS)
        guard ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" else { return }
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
        viewModel.pauseForReaderTransport()
        musicCoordinator.simulateReadingBedPauseForE2E()
        pronunciationSpeaker.speakFallback("resume", language: "en-US")
        requestKeyboardShortcutFocus()
        #endif
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
