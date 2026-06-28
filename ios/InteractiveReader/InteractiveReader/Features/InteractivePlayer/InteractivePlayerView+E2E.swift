import SwiftUI

#if DEBUG
extension Notification.Name {
    static let e2eBubblePronunciationResume = Notification.Name(
        "com.interactivereader.e2e.bubblePronunciationResume"
    )
}

@MainActor
enum InteractivePlayerE2EState {
    static var bubbleWordNavigationCount = 0
    static var bubbleWordNavigationDirection = 0
    static var bubbleWordNavigationSentenceIndex = -1
    static var bubbleWordNavigationTokenIndex = -1
    static var bubbleWordNavigationVariant = "none"

    static func resetBubbleWordNavigation() {
        bubbleWordNavigationCount = 0
        bubbleWordNavigationDirection = 0
        bubbleWordNavigationSentenceIndex = -1
        bubbleWordNavigationTokenIndex = -1
        bubbleWordNavigationVariant = "none"
    }

    static func recordBubbleWordNavigation(
        direction: Int,
        sentenceIndex: Int,
        variant: TextPlayerVariantKind,
        tokenIndex: Int
    ) {
        bubbleWordNavigationCount += 1
        bubbleWordNavigationDirection = direction
        bubbleWordNavigationSentenceIndex = sentenceIndex
        bubbleWordNavigationTokenIndex = tokenIndex
        bubbleWordNavigationVariant = String(describing: variant)
    }

    static var statusText: String {
        [
            "bubbleWordNav=\(bubbleWordNavigationCount)",
            "bubbleWordNavDirection=\(bubbleWordNavigationDirection)",
            "bubbleWordNavSentence=\(bubbleWordNavigationSentenceIndex)",
            "bubbleWordNavToken=\(bubbleWordNavigationTokenIndex)",
            "bubbleWordNavVariant=\(bubbleWordNavigationVariant)"
        ].joined(separator: " ")
    }
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
        InteractivePlayerE2EState.resetBubbleWordNavigation()
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
