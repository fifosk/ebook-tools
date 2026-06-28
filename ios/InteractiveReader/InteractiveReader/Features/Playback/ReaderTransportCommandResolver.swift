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
        12.0
    }

    static func resolvedAction(
        for command: String,
        ownershipState: AudioOwnership,
        isReaderPlaybackRequested: Bool,
        isReaderPlaying: Bool,
        isMusicPlaying: Bool,
        isMusicPausedByReaderTransport: Bool
    ) -> String {
        let shouldPause = shouldPauseForToggle(
            ownershipState: ownershipState,
            isReaderPlaybackRequested: isReaderPlaybackRequested,
            isReaderPlaying: isReaderPlaying,
            isMusicPlaying: isMusicPlaying,
            isMusicPausedByReaderTransport: isMusicPausedByReaderTransport
        )

        #if os(tvOS)
        if ownershipState == .appleMusicBed,
           command == "play" || command == "pause" || command == "toggle" {
            return shouldPause ? "pause" : "play"
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
        elapsed < duplicateWindow && resolvedAction == previousAction
    }

    static func shouldRejectDuplicateCommand(
        elapsed: TimeInterval,
        resolvedAction: String,
        previousAction: String
    ) -> Bool {
        elapsed < duplicateWindow && resolvedAction != previousAction
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
