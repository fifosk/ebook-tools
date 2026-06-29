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
    static var bubbleLookupCommandCount = 0
    static var bubbleLookupHadBubble = false
    static var bubbleLookupSentenceIndex = -1
    static var bubbleLookupTokenIndex = -1
    static var bubbleLookupVariant = "none"
    static var playPauseCommandCount = 0
    static var playPauseUsedOverride = false
    static var playPauseAudioPlaying = false
    static var playPauseAudioRequested = false
    static var playPauseMusicPlaying = false
    static var playPauseReaderPause = false
    static var playPauseReaderGuard = false

    static func resetBubbleWordNavigation() {
        bubbleWordNavigationCount = 0
        bubbleWordNavigationDirection = 0
        bubbleWordNavigationSentenceIndex = -1
        bubbleWordNavigationTokenIndex = -1
        bubbleWordNavigationVariant = "none"
        bubbleLookupCommandCount = 0
        bubbleLookupHadBubble = false
        bubbleLookupSentenceIndex = -1
        bubbleLookupTokenIndex = -1
        bubbleLookupVariant = "none"
        playPauseCommandCount = 0
        playPauseUsedOverride = false
        playPauseAudioPlaying = false
        playPauseAudioRequested = false
        playPauseMusicPlaying = false
        playPauseReaderPause = false
        playPauseReaderGuard = false
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

    static func recordBubbleLookupCommand(
        hadBubble: Bool,
        selection: TextPlayerWordSelection?
    ) {
        bubbleLookupCommandCount += 1
        bubbleLookupHadBubble = hadBubble
        if let selection {
            bubbleLookupSentenceIndex = selection.sentenceIndex
            bubbleLookupTokenIndex = selection.tokenIndex
            bubbleLookupVariant = String(describing: selection.variantKind)
        }
    }

    static func recordPlayPauseCommand(
        usedOverride: Bool,
        audioPlaying: Bool,
        audioRequested: Bool,
        musicPlaying: Bool,
        readerPause: Bool,
        readerGuard: Bool
    ) {
        playPauseCommandCount += 1
        playPauseUsedOverride = usedOverride
        playPauseAudioPlaying = audioPlaying
        playPauseAudioRequested = audioRequested
        playPauseMusicPlaying = musicPlaying
        playPauseReaderPause = readerPause
        playPauseReaderGuard = readerGuard
    }

    static var statusText: String {
        [
            "bubbleWordNav=\(bubbleWordNavigationCount)",
            "bubbleWordNavDirection=\(bubbleWordNavigationDirection)",
            "bubbleWordNavSentence=\(bubbleWordNavigationSentenceIndex)",
            "bubbleWordNavToken=\(bubbleWordNavigationTokenIndex)",
            "bubbleWordNavVariant=\(bubbleWordNavigationVariant)",
            "bubbleLookup=\(bubbleLookupCommandCount)",
            "bubbleLookupHadBubble=\(bubbleLookupHadBubble ? "true" : "false")",
            "bubbleLookupSentence=\(bubbleLookupSentenceIndex)",
            "bubbleLookupToken=\(bubbleLookupTokenIndex)",
            "bubbleLookupVariant=\(bubbleLookupVariant)",
            "playPauseCommands=\(playPauseCommandCount)",
            "playPauseOverride=\(playPauseUsedOverride ? "true" : "false")",
            "playPauseAudioPlaying=\(playPauseAudioPlaying ? "true" : "false")",
            "playPauseAudioRequested=\(playPauseAudioRequested ? "true" : "false")",
            "playPauseMusicPlaying=\(playPauseMusicPlaying ? "true" : "false")",
            "playPauseReaderPause=\(playPauseReaderPause ? "true" : "false")",
            "playPauseReaderGuard=\(playPauseReaderGuard ? "true" : "false")"
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
