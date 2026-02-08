import Foundation
import Combine

/// Sends periodic playback heartbeats to the backend while audio is playing.
///
/// Accumulates elapsed seconds and sends a heartbeat every `heartbeatInterval`.
/// Flushes remaining time when playback stops or the manager is stopped.
///
/// Usage (from a playback view):
///   heartbeatManager.start(
///       jobId: "job-123",
///       originalLanguage: "en",
///       translationLanguage: "ar",
///       configuration: apiConfig,
///       audioCoordinator: viewModel.audioCoordinator,
///       sequenceController: viewModel.sequenceController,
///       audioModeManager: audioModeManager
///   )
///   // later:
///   heartbeatManager.stop()
@MainActor
final class PlaybackHeartbeatManager {
    private let heartbeatInterval: TimeInterval = 30
    private let minDeltaSeconds: Double = 1

    private var jobId: String?
    private var originalLanguage: String = ""
    private var translationLanguage: String = ""
    private var configuration: APIClientConfiguration?

    private var accumulatedSeconds: Double = 0
    private var lastTickDate: Date?
    private var tickTimer: Timer?
    private var heartbeatTimer: Timer?
    private var playingCancellable: AnyCancellable?

    // Providers — closures that read current state at call time
    private var isPlayingProvider: (() -> Bool)?
    private var trackKindProvider: (() -> String)?

    func start(
        jobId: String,
        originalLanguage: String,
        translationLanguage: String,
        configuration: APIClientConfiguration?,
        audioCoordinator: AudioPlayerCoordinator,
        sequenceController: SequencePlaybackController,
        audioModeManager: AudioModeManager
    ) {
        stop()

        self.jobId = jobId
        self.originalLanguage = originalLanguage
        self.translationLanguage = translationLanguage
        self.configuration = configuration

        self.isPlayingProvider = { [weak audioCoordinator] in
            audioCoordinator?.isPlaying ?? false
        }

        self.trackKindProvider = { [weak sequenceController, weak audioModeManager] in
            guard let sc = sequenceController, let amm = audioModeManager else { return "translation" }
            if sc.isEnabled {
                return sc.currentTrack.rawValue
            }
            switch amm.currentMode {
            case .singleTrack(let track):
                return track.rawValue
            case .sequence:
                return sc.currentTrack.rawValue
            }
        }

        // Observe isPlaying changes to start/stop accumulation
        playingCancellable = audioCoordinator.$isPlaying
            .removeDuplicates()
            .receive(on: RunLoop.main)
            .sink { [weak self] isPlaying in
                if isPlaying {
                    self?.startAccumulating()
                } else {
                    self?.stopAccumulating()
                }
            }
    }

    func stop() {
        flush()
        stopAccumulating()
        playingCancellable?.cancel()
        playingCancellable = nil
        heartbeatTimer?.invalidate()
        heartbeatTimer = nil
        isPlayingProvider = nil
        trackKindProvider = nil
        jobId = nil
        configuration = nil
    }

    // MARK: - Private

    private func startAccumulating() {
        lastTickDate = Date()

        tickTimer?.invalidate()
        tickTimer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.tick()
            }
        }

        heartbeatTimer?.invalidate()
        heartbeatTimer = Timer.scheduledTimer(withTimeInterval: heartbeatInterval, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.flush()
            }
        }
    }

    private func stopAccumulating() {
        flush()
        tickTimer?.invalidate()
        tickTimer = nil
        heartbeatTimer?.invalidate()
        heartbeatTimer = nil
        lastTickDate = nil
    }

    private func tick() {
        guard isPlayingProvider?() == true else { return }
        let now = Date()
        if let last = lastTickDate {
            accumulatedSeconds += now.timeIntervalSince(last)
        }
        lastTickDate = now
    }

    private func flush() {
        // Capture any remaining time from last tick
        if let last = lastTickDate, isPlayingProvider?() == true {
            accumulatedSeconds += Date().timeIntervalSince(last)
            lastTickDate = Date()
        }

        let delta = accumulatedSeconds
        guard delta >= minDeltaSeconds,
              let jobId = jobId,
              let config = configuration,
              let trackKind = trackKindProvider?()
        else { return }

        let language = trackKind == "original" ? originalLanguage : translationLanguage
        guard !language.isEmpty else { return }

        accumulatedSeconds = 0

        Task {
            let client = APIClient(configuration: config)
            let payload = PlaybackHeartbeatPayload(
                jobId: jobId,
                language: language,
                trackKind: trackKind,
                deltaSeconds: delta.rounded()
            )
            _ = try? await client.sendPlaybackHeartbeat(payload: payload)
        }
    }
}
