import Foundation

enum ReaderTransportCommandResolver {
    static var duplicateWindow: TimeInterval {
        #if os(tvOS)
        return 1.25
        #else
        return 0.25
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
        let shouldPause = shouldPauseForToggle(
            ownershipState: ownershipState,
            isReaderPlaybackRequested: isReaderPlaybackRequested,
            isReaderPlaying: isReaderPlaying,
            isMusicPlaying: isMusicPlaying,
            isMusicPausedByReaderTransport: isMusicPausedByReaderTransport
        )

        guard command == "toggle" else { return command }
        return shouldPause ? "pause" : "play"
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
