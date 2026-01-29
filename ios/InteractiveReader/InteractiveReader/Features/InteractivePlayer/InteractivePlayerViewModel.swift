import Foundation
import SwiftUI

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

    let audioCoordinator = AudioPlayerCoordinator()

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

    init() {
        audioCoordinator.onPlaybackEnded = { [weak self] in
            self?.handlePlaybackEnded()
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
