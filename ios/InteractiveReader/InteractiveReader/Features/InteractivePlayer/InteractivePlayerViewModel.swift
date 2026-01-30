import Foundation
import SwiftUI
import Combine

@MainActor
final class InteractivePlayerViewModel: ObservableObject {
    enum MediaOrigin {
        case job
        case library
    }

    enum LoadState: Equatable {
        case idle
        case loading
        case loaded
        case error(String)

        var errorMessage: String? {
            if case let .error(message) = self {
                return message
            }
            return nil
        }
    }

    @Published var loadState: LoadState = .idle
    @Published var jobId: String?
    @Published var jobContext: JobContext?
    @Published var selectedChunkID: String?
    @Published var selectedAudioTrackID: String?
    @Published var selectedTimingURL: URL?
    @Published var mediaResponse: PipelineMediaResponse?
    @Published var timingResponse: JobTimingResponse?
    @Published var chapterEntries: [ChapterNavigationEntry] = []
    @Published var readingBedCatalog: ReadingBedListResponse?
    @Published var readingBedURL: URL?
    @Published var selectedReadingBedID: String?
    @Published var isTranscriptLoading: Bool = false
    /// Forwarded from sequenceController for SwiftUI observation
    @Published var isSequenceTransitioning: Bool = false
    /// The sentence index that was active BEFORE a transition started
    /// Used to maintain stable display during track switches
    @Published var preTransitionSentenceIndex: Int?
    /// Callback fired BEFORE a sequence transition begins (allows view to freeze synchronously)
    var onSequenceWillTransition: (() -> Void)?

    let audioCoordinator = AudioPlayerCoordinator()
    let sequenceController = SequencePlaybackController()

    var mediaResolver: MediaURLResolver?
    var apiBaseURL: URL?
    var authToken: String?
    var readingBedBaseURL: URL?
    var apiConfiguration: APIClientConfiguration?
    var mediaOrigin: MediaOrigin = .job
    var preferredAudioKind: InteractiveChunk.AudioOption.Kind?
    var audioDurationByURL: [URL: Double] = [:]
    var chunkMetadataLoaded: Set<String> = []
    var chunkMetadataLoading: Set<String> = []
    var chunkMetadataAttemptedAt: [String: Date] = [:]
    var lastPrefetchSentenceNumber: Int?
    var prefetchedAudioURLs: Set<URL> = []
    var pendingSentenceJump: PendingSentenceJump?
    let defaultReadingBedPath = "/assets/reading-beds/lost-in-the-pages.mp3"
    var liveUpdateTask: Task<Void, Never>?
    let liveUpdateInterval: UInt64 = 4_000_000_000
    let metadataPrefetchRadius: Int = 2
    let metadataRetryInterval: TimeInterval = 6
    private var sequenceTimeObserver: AnyCancellable?
    private var sequenceTransitionObserver: AnyCancellable?

    init() {
        // Observe time changes to update sequence playback
        // This is separate from view rendering to prevent side effects during rendering
        sequenceTimeObserver = audioCoordinator.$currentTime
            .receive(on: RunLoop.main)
            .sink { [weak self] _ in
                guard let self else { return }
                guard self.sequenceController.isEnabled else { return }
                guard self.audioCoordinator.isPlaying else { return }
                self.updateSequencePlayback(
                    currentTime: self.audioCoordinator.currentTime,
                    isPlaying: true
                )
            }

        // Forward sequenceController.isTransitioning to @Published property for SwiftUI observation
        sequenceTransitionObserver = sequenceController.$isTransitioning
            .receive(on: RunLoop.main)
            .sink { [weak self] isTransitioning in
                self?.isSequenceTransitioning = isTransitioning
                // Clear pre-transition state when transition ends
                if !isTransitioning {
                    self?.preTransitionSentenceIndex = nil
                }
            }

        audioCoordinator.onPlaybackEnded = { [weak self] in
            self?.handlePlaybackEnded()
        }

        // Set up sequence controller callbacks
        sequenceController.onTrackSwitch = { [weak self] track, time in
            Task { @MainActor [weak self] in
                self?.handleSequenceTrackSwitch(track: track, seekTime: time)
            }
        }

        sequenceController.onSequenceEnded = { [weak self] in
            Task { @MainActor [weak self] in
                self?.handlePlaybackEnded()
            }
        }

        sequenceController.onWillBeginTransition = { [weak self] in
            guard let self else { return }
            // Capture the current sentence index BEFORE the transition changes state
            // This allows the view to maintain stable display during the transition
            if let currentIndex = self.sequenceController.currentSegment?.sentenceIndex {
                print("[Sequence] onWillBeginTransition: capturing preTransitionSentenceIndex=\(currentIndex)")
                self.preTransitionSentenceIndex = currentIndex
            }
            // Forward to view layer callback synchronously (we're already on main actor)
            print("[Sequence] onWillBeginTransition: firing view callback")
            self.onSequenceWillTransition?()
        }

        sequenceController.onSeekRequest = { [weak self] time in
            Task { @MainActor [weak self] in
                guard let self else { return }
                print("[Sequence] Re-seek requested to \(String(format: "%.3f", time))")
                self.audioCoordinator.seek(to: time)
                // Small delay to let seek take effect, then end transition
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) { [weak self] in
                    guard let self else { return }
                    print("[Sequence] Re-seek completed, ending transition with expectedTime=\(String(format: "%.3f", time))")
                    self.sequenceController.endTransition(expectedTime: time)
                }
            }
        }
    }

    enum AssistantLookupError: LocalizedError {
        case missingConfiguration

        var errorDescription: String? {
            "Assistant lookup is not configured."
        }
    }

    enum PronunciationError: LocalizedError {
        case missingConfiguration

        var errorDescription: String? {
            "Pronunciation audio is not configured."
        }
    }
}
