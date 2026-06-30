import Foundation

enum ReaderTransportCommandResolver {
    static var duplicateWindow: TimeInterval {
        #if os(tvOS)
        return 1.5
        #else
        return 0.25
        #endif
    }

    static var pauseHoldWindow: TimeInterval {
        0.75
    }

    static var brokerEchoWindow: TimeInterval {
        #if os(tvOS)
        return 1.5
        #else
        return 1.25
        #endif
    }

    static var adoptedMusicPauseBrokerEchoWindow: TimeInterval {
        #if os(tvOS)
        return 2.25
        #else
        return brokerEchoWindow
        #endif
    }

    static var hardwarePressEchoWindow: TimeInterval {
        #if os(tvOS)
        return 0.05
        #else
        return duplicateWindow
        #endif
    }

    static var observedPauseAfterPlayEchoWindow: TimeInterval {
        #if os(tvOS)
        return duplicateWindow
        #else
        return 0
        #endif
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
           isMusicPausedByReaderTransport {
            #if os(tvOS)
            if command == "play" || command == "pause" || command == "toggle" {
                return "play"
            }
            #else
            if command == "toggle", !isReaderPlaying {
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
        return elapsed < duplicateWindow && resolvedAction == previousAction
        #else
        elapsed < duplicateWindow && resolvedAction != previousAction
        #endif
    }

    static func shouldAcceptActiveReaderDuplicatePause(
        elapsed: TimeInterval,
        resolvedAction: String,
        previousAction: String,
        isReaderPlaybackRequested: Bool,
        isReaderPlaying: Bool
    ) -> Bool {
        #if os(tvOS)
        return elapsed < duplicateWindow &&
            resolvedAction == "pause" &&
            previousAction == "pause" &&
            (isReaderPlaybackRequested || isReaderPlaying)
        #else
        return false
        #endif
    }

    static func shouldRejectUnsolicitedPlayCommand(
        ownershipState: AudioOwnership,
        previousAction: String,
        isEchoGuardActive: Bool,
        shouldRejectResumeAfterPause: Bool,
        isPauseHoldWindowActive: Bool,
        now: TimeInterval,
        localPauseHoldUntil: TimeInterval
    ) -> Bool {
        ownershipState == .appleMusicBed &&
            previousAction == "pause" &&
            (
                isEchoGuardActive ||
                shouldRejectResumeAfterPause ||
                isPauseHoldWindowActive ||
                now < localPauseHoldUntil
            )
    }

    static func shouldForceNowPlayingPause(
        ownershipState: AudioOwnership,
        isReaderPlaybackRequested: Bool,
        isReaderPlaying: Bool,
        previousAction: String,
        now: TimeInterval,
        localPauseHoldUntil: TimeInterval,
        shouldRejectResumeAfterPause: Bool,
        isPauseHoldWindowActive: Bool
    ) -> Bool {
        if ownershipState == .appleMusicBed {
            if isReaderPlaybackRequested || isReaderPlaying {
                return true
            }
            return !canResumeAfterReaderPause(
                previousAction: previousAction,
                now: now,
                localPauseHoldUntil: localPauseHoldUntil,
                shouldRejectResumeAfterPause: shouldRejectResumeAfterPause,
                isPauseHoldWindowActive: isPauseHoldWindowActive
            )
        }
        return isReaderPlaybackRequested || isReaderPlaying
    }

    static func shouldForceNowPlayingResume(
        ownershipState: AudioOwnership,
        previousAction: String,
        ignorePauseHold: Bool,
        now: TimeInterval,
        localPauseHoldUntil: TimeInterval,
        isReaderPlaybackRequested: Bool,
        isReaderPlaying: Bool,
        isMusicPausedByReaderTransport: Bool,
        isMusicPlaying: Bool
    ) -> Bool {
        guard ownershipState == .appleMusicBed else { return false }
        guard previousAction == "pause" else { return false }
        guard ignorePauseHold || now >= localPauseHoldUntil else { return false }
        if isMusicPausedByReaderTransport {
            return true
        }
        guard !isReaderPlaybackRequested, !isReaderPlaying else { return false }
        return !isMusicPlaying
    }

    static func shouldIgnoreBrokerEcho(
        canForceResume: Bool,
        elapsed: TimeInterval,
        previousAction: String,
        previousSource: String,
        shouldRejectResumeAfterPause: Bool,
        isPauseHoldWindowActive: Bool
    ) -> Bool {
        guard shouldHoldReaderResumeAfterPause else { return false }
        guard previousAction == "pause" else { return false }
        if isAdoptedMusicPauseSource(previousSource),
           elapsed < adoptedMusicPauseBrokerEchoWindow {
            return true
        }
        if elapsed < brokerEchoWindow {
            return true
        }
        guard !canForceResume else { return false }
        return shouldRejectResumeAfterPause || isPauseHoldWindowActive
    }

    private static func isAdoptedMusicPauseSource(_ source: String) -> Bool {
        source == "musicAdoption" ||
            source == "musicSurface" ||
            source == "watchdog"
    }

    static func shouldBlockResumeAfterPause(
        resolvedAction: String,
        now: TimeInterval,
        localPauseHoldUntil: TimeInterval,
        shouldRejectResumeAfterPause: Bool,
        isPauseHoldWindowActive: Bool
    ) -> Bool {
        guard shouldHoldReaderResumeAfterPause else { return false }
        guard resolvedAction == "play" else { return false }
        return now < localPauseHoldUntil ||
            shouldRejectResumeAfterPause ||
            isPauseHoldWindowActive
    }

    static func shouldReinforcePauseAfterRejectedPlay(
        ownershipState: AudioOwnership,
        resolvedAction: String,
        previousAction: String,
        now: TimeInterval,
        localPauseHoldUntil: TimeInterval,
        shouldRejectResumeAfterPause: Bool,
        isPauseHoldWindowActive: Bool,
        isPauseGuardActive: Bool
    ) -> Bool {
        guard shouldHoldReaderResumeAfterPause else { return false }
        guard resolvedAction == "play" else { return false }
        guard ownershipState == .appleMusicBed else { return false }
        let shouldAllowPostPauseResume = canResumeAfterReaderPause(
            previousAction: previousAction,
            now: now,
            localPauseHoldUntil: localPauseHoldUntil,
            shouldRejectResumeAfterPause: shouldRejectResumeAfterPause,
            isPauseHoldWindowActive: isPauseHoldWindowActive
        )
        return !shouldAllowPostPauseResume && (
            now < localPauseHoldUntil ||
                shouldRejectResumeAfterPause ||
                isPauseGuardActive
        )
    }

    static func shouldIgnoreObservedPauseAfterReaderPlay(
        previousAction: String,
        now: TimeInterval,
        lastCommandTime: TimeInterval
    ) -> Bool {
        #if os(tvOS)
        return previousAction == "play" &&
            now - lastCommandTime < observedPauseAfterPlayEchoWindow
        #else
        return false
        #endif
    }

    private static func canResumeAfterReaderPause(
        previousAction: String,
        now: TimeInterval,
        localPauseHoldUntil: TimeInterval,
        shouldRejectResumeAfterPause: Bool,
        isPauseHoldWindowActive: Bool
    ) -> Bool {
        previousAction == "pause" &&
            now >= localPauseHoldUntil &&
            !shouldRejectResumeAfterPause &&
            !isPauseHoldWindowActive
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
        suppressUntil = now + ReaderTransportCommandResolver.hardwarePressEchoWindow
        return false
    }
}
#endif
