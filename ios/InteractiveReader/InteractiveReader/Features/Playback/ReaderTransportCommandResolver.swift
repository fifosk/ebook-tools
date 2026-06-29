import Foundation

enum ReaderTransportCommandResolver {
    static var duplicateWindow: TimeInterval {
        #if os(tvOS)
        return 1.25
        #else
        return 0.25
        #endif
    }

    static var pauseHoldWindow: TimeInterval {
        0.75
    }

    static var brokerEchoWindow: TimeInterval {
        return 1.25
    }

    static var shouldHoldReaderResumeAfterPause: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }

    static func resolvedAction(
        for command: String,
        ownershipState: AudioOwnership,
        isReaderPlaybackRequested: Bool,
        isReaderPlaying: Bool,
        isMusicPlaying: Bool,
        isMusicPausedByReaderTransport: Bool
    ) -> String {
        if ownershipState == .appleMusicBed,
           isMusicPausedByReaderTransport,
           !isReaderPlaying {
            #if os(tvOS)
            if command == "play" || command == "pause" || command == "toggle" {
                return "play"
            }
            #else
            if command == "toggle" {
                return "play"
            }
            #endif
        }
        let shouldPause = shouldPauseForToggle(
            ownershipState: ownershipState,
            isReaderPlaybackRequested: isReaderPlaybackRequested,
            isReaderPlaying: isReaderPlaying,
            isMusicPlaying: isMusicPlaying,
            isMusicPausedByReaderTransport: isMusicPausedByReaderTransport
        )

        #if os(tvOS)
        if ownershipState == .appleMusicBed {
            if command == "pause" {
                return "pause"
            }
            if command == "play" || command == "toggle" {
                return shouldPause ? "pause" : "play"
            }
        }
        #endif

        guard command == "toggle" else { return command }
        return shouldPause ? "pause" : "play"
    }

    static func shouldReapplyDuplicateCommand(
        elapsed: TimeInterval,
        resolvedAction: String,
        previousAction: String
    ) -> Bool {
        #if os(tvOS)
        return false
        #else
        elapsed < duplicateWindow && resolvedAction == previousAction
        #endif
    }

    static func shouldRejectDuplicateCommand(
        elapsed: TimeInterval,
        resolvedAction: String,
        previousAction: String
    ) -> Bool {
        #if os(tvOS)
        return elapsed < duplicateWindow
        #else
        elapsed < duplicateWindow && resolvedAction != previousAction
        #endif
    }

    private static func shouldPauseForToggle(
        ownershipState: AudioOwnership,
        isReaderPlaybackRequested: Bool,
        isReaderPlaying: Bool,
        isMusicPlaying: Bool,
        isMusicPausedByReaderTransport: Bool
    ) -> Bool {
        isReaderPlaybackRequested ||
            isReaderPlaying ||
            (ownershipState == .appleMusicBed &&
             isMusicPlaying &&
             !isMusicPausedByReaderTransport)
    }
}

#if os(tvOS)
@MainActor
enum TVPlayPauseCommandGate {
    private static var suppressUntil: TimeInterval = 0

    static func shouldSuppressCurrentPress() -> Bool {
        let now = ProcessInfo.processInfo.systemUptime
        guard now >= suppressUntil else {
            return true
        }
        suppressUntil = now + ReaderTransportCommandResolver.duplicateWindow
        return false
    }
}
#endif
