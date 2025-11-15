import Foundation
import SwiftUI

@MainActor
final class InteractivePlayerViewModel: ObservableObject {
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

    @Published private(set) var loadState: LoadState = .idle
    @Published private(set) var jobContext: JobContext?
    @Published private(set) var selectedChunkID: String?
    @Published private(set) var selectedAudioTrackID: String?

    let audioCoordinator = AudioPlayerCoordinator()

    private var storageResolver: StorageResolver?

    func loadJob(jobId: String, configuration: APIClientConfiguration) async {
        let trimmedJobId = jobId.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedJobId.isEmpty else {
            loadState = .error("Enter a job identifier before loading.")
            return
        }

        loadState = .loading
        selectedChunkID = nil
        selectedAudioTrackID = nil

        do {
            let client = APIClient(configuration: configuration)
            async let mediaTask = client.fetchJobMedia(jobId: trimmedJobId)
            async let timingTask = client.fetchJobTiming(jobId: trimmedJobId)
            let (media, timing) = try await (mediaTask, timingTask)
            let resolver = try StorageResolver(apiBaseURL: configuration.apiBaseURL, override: configuration.storageBaseURL)
            let context = try JobContextBuilder.build(
                jobId: trimmedJobId,
                media: media,
                timing: timing,
                resolver: resolver
            )
            jobContext = context
            storageResolver = resolver
            configureDefaultSelections()
            loadState = .loaded
        } catch is CancellationError {
            loadState = .idle
        } catch {
            loadState = .error(error.localizedDescription)
        }
    }

    func selectChunk(id: String) {
        guard selectedChunkID != id else { return }
        selectedChunkID = id
        guard let chunk = selectedChunk else {
            audioCoordinator.reset()
            return
        }
        if !(chunk.audioOptions.contains { $0.id == selectedAudioTrackID }) {
            selectedAudioTrackID = chunk.audioOptions.first?.id
        }
        prepareAudio(for: chunk, autoPlay: false)
    }

    func selectAudioTrack(id: String) {
        guard selectedAudioTrackID != id else { return }
        selectedAudioTrackID = id
        guard let chunk = selectedChunk else { return }
        prepareAudio(for: chunk, autoPlay: false)
    }

    var selectedChunk: InteractiveChunk? {
        guard let context = jobContext else { return nil }
        if let id = selectedChunkID, let chunk = context.chunk(withID: id) {
            return chunk
        }
        return context.chunks.first
    }

    var currentAudioOptions: [InteractiveChunk.AudioOption] {
        selectedChunk?.audioOptions ?? []
    }

    var highlightingSummary: String? {
        guard let context = jobContext else { return nil }
        if let policy = context.highlightingPolicy?.capitalized, !policy.isEmpty {
            if context.hasEstimatedSegments {
                return "Highlighting policy: \(policy) (estimated segments present)"
            }
            return "Highlighting policy: \(policy)"
        }
        if context.hasEstimatedSegments {
            return "Estimated timings detected"
        }
        return nil
    }

    var chunkCountLabel: String {
        guard let context = jobContext else { return "No chunks" }
        return "Chunks: \(context.chunks.count)"
    }

    func chunkBinding() -> Binding<String> {
        Binding(
            get: {
                self.selectedChunkID ?? self.jobContext?.chunks.first?.id ?? ""
            },
            set: { newValue in
                self.selectChunk(id: newValue)
            }
        )
    }

    func audioTrackBinding(defaultID: String?) -> Binding<String> {
        Binding(
            get: {
                self.selectedAudioTrackID ?? defaultID ?? ""
            },
            set: { newValue in
                self.selectAudioTrack(id: newValue)
            }
        )
    }

    private func configureDefaultSelections() {
        guard let context = jobContext else { return }
        if let chunk = context.chunks.first(where: { !$0.audioOptions.isEmpty }) ?? context.chunks.first {
            selectedChunkID = chunk.id
            selectedAudioTrackID = chunk.audioOptions.first?.id
            prepareAudio(for: chunk, autoPlay: false)
        } else {
            selectedChunkID = nil
            selectedAudioTrackID = nil
            audioCoordinator.reset()
        }
    }

    private func prepareAudio(for chunk: InteractiveChunk, autoPlay: Bool) {
        guard let trackID = selectedAudioTrackID,
              let track = chunk.audioOptions.first(where: { $0.id == trackID }) else {
            audioCoordinator.reset()
            return
        }
        audioCoordinator.load(url: track.streamURL, autoPlay: autoPlay)
    }
}

// MARK: - Derived Models

struct JobContext {
    let jobId: String
    let highlightingPolicy: String?
    let hasEstimatedSegments: Bool
    let chunks: [InteractiveChunk]

    private let chunkIndex: [String: Int]

    init(jobId: String, highlightingPolicy: String?, hasEstimatedSegments: Bool, chunks: [InteractiveChunk]) {
        self.jobId = jobId
        self.highlightingPolicy = highlightingPolicy
        self.hasEstimatedSegments = hasEstimatedSegments
        self.chunks = chunks
        self.chunkIndex = Dictionary(uniqueKeysWithValues: chunks.enumerated().map { ($0.element.id, $0.offset) })
    }

    func chunk(withID id: String) -> InteractiveChunk? {
        guard let index = chunkIndex[id], chunks.indices.contains(index) else {
            return nil
        }
        return chunks[index]
    }
}

struct InteractiveChunk: Identifiable {
    struct Sentence: Identifiable {
        let id: Int
        let displayIndex: Int?
        let originalText: String
        let translationText: String
        let tokens: [WordTimingToken]
    }

    struct AudioOption: Identifiable {
        let id: String
        let label: String
        let streamURL: URL
        let duration: Double?
    }

    let id: String
    let label: String
    let rangeDescription: String?
    let startSentence: Int?
    let endSentence: Int?
    let sentences: [Sentence]
    let audioOptions: [AudioOption]
}

struct WordTimingToken: Identifiable {
    let id: String
    let text: String
    let sentenceIndex: Int?
    let startTime: Double
    let endTime: Double

    var displayText: String {
        text.isEmpty ? "" : text
    }

    func isActive(at time: Double, tolerance: Double = 0.02) -> Bool {
        let start = startTime - tolerance
        let end = endTime + tolerance
        return time >= start && time <= end
    }
}

// MARK: - Context Builder

enum JobContextBuilder {
    static func build(jobId: String, media: PipelineMediaResponse, timing: JobTimingResponse?, resolver: StorageResolver) throws -> JobContext {
        let tokens = timing?.tracks.translation.segments.compactMap { WordTimingToken(entry: $0) } ?? []
        let groupedTokens = Dictionary(grouping: tokens) { token -> Int in
            token.sentenceIndex ?? -1
        }
        let audioFiles = media.media["audio"] ?? []
        let chunks = media.chunks.enumerated().map { index, chunk in
            buildChunk(
                chunk,
                index: index,
                jobId: jobId,
                groupedTokens: groupedTokens,
                resolver: resolver,
                audioFiles: audioFiles
            )
        }
        return JobContext(
            jobId: jobId,
            highlightingPolicy: timing?.highlightingPolicy,
            hasEstimatedSegments: timing?.hasEstimatedSegments ?? false,
            chunks: chunks
        )
    }

    private static func buildChunk(
        _ chunk: PipelineMediaChunk,
        index: Int,
        jobId: String,
        groupedTokens: [Int: [WordTimingToken]],
        resolver: StorageResolver,
        audioFiles: [PipelineMediaFile]
    ) -> InteractiveChunk {
        let chunkID = chunk.chunkID ?? "chunk-\(index)"
        let label = chunkID
        let sentences = buildSentences(for: chunk, groupedTokens: groupedTokens)
        let audioOptions = buildAudioOptions(
            for: chunk,
            chunkID: chunkID,
            jobId: jobId,
            resolver: resolver,
            fallbackFiles: audioFiles
        )
        let range: String?
        if let start = chunk.startSentence, let end = chunk.endSentence {
            range = "Sentences \(start)–\(end)"
        } else {
            range = nil
        }
        return InteractiveChunk(
            id: chunkID,
            label: label,
            rangeDescription: range,
            startSentence: chunk.startSentence,
            endSentence: chunk.endSentence,
            sentences: sentences,
            audioOptions: audioOptions
        )
    }

    private static func buildSentences(
        for chunk: PipelineMediaChunk,
        groupedTokens: [Int: [WordTimingToken]]
    ) -> [InteractiveChunk.Sentence] {
        if !chunk.sentences.isEmpty {
            return chunk.sentences.enumerated().map { offset, sentence in
                let explicitIndex = sentence.sentenceNumber
                let derivedIndex = chunk.startSentence.map { $0 + offset }
                let sentenceIndex = explicitIndex ?? derivedIndex ?? offset
                let tokens = groupedTokens[sentenceIndex] ?? []
                return InteractiveChunk.Sentence(
                    id: sentenceIndex,
                    displayIndex: explicitIndex ?? derivedIndex,
                    originalText: sentence.original.text,
                    translationText: sentence.translation?.text ?? sentence.original.text,
                    tokens: tokens
                )
            }
        }

        guard let start = chunk.startSentence, let end = chunk.endSentence else {
            return []
        }

        return (start...end).map { sentenceIndex in
            let tokens = groupedTokens[sentenceIndex] ?? []
            let text = tokens.map { $0.displayText }.joined(separator: " ").trimmingCharacters(in: .whitespaces)
            return InteractiveChunk.Sentence(
                id: sentenceIndex,
                displayIndex: sentenceIndex,
                originalText: text,
                translationText: text,
                tokens: tokens
            )
        }
    }

    private static func buildAudioOptions(
        for chunk: PipelineMediaChunk,
        chunkID: String,
        jobId: String,
        resolver: StorageResolver,
        fallbackFiles: [PipelineMediaFile]
    ) -> [InteractiveChunk.AudioOption] {
        var options: [InteractiveChunk.AudioOption] = []
        for (key, metadata) in chunk.audioTracks {
            guard let url = resolveAudioURL(jobId: jobId, track: metadata, resolver: resolver) else { continue }
            let option = InteractiveChunk.AudioOption(
                id: "\(chunkID)|\(key)",
                label: displayName(for: key),
                streamURL: url,
                duration: metadata.duration
            )
            options.append(option)
        }

        if options.isEmpty {
            let matches = fallbackFiles.filter { $0.chunkID == chunk.chunkID || $0.chunkID == chunkID }
            for file in matches {
                guard let url = resolveFileURL(jobId: jobId, file: file, resolver: resolver) else { continue }
                let option = InteractiveChunk.AudioOption(
                    id: "\(chunkID)|file|\(file.name)",
                    label: file.name,
                    streamURL: url,
                    duration: nil
                )
                options.append(option)
            }
        }

        return options.sorted(by: { $0.label < $1.label })
    }

    private static func resolveAudioURL(jobId: String, track: AudioTrackMetadata, resolver: StorageResolver) -> URL? {
        if let urlString = track.url, let url = URL(string: urlString) {
            return url
        }
        if let path = track.path {
            return resolver.url(jobId: jobId, filePath: path)
        }
        return nil
    }

    private static func resolveFileURL(jobId: String, file: PipelineMediaFile, resolver: StorageResolver) -> URL? {
        if let urlString = file.url, let url = URL(string: urlString) {
            return url
        }
        if let relative = file.relativePath {
            return resolver.url(jobId: jobId, filePath: relative)
        }
        if let path = file.path {
            return resolver.url(jobId: jobId, filePath: path)
        }
        return nil
    }

    private static func displayName(for key: String) -> String {
        switch key.lowercased() {
        case "orig_trans":
            return "Original + translation"
        case "translation", "trans":
            return "Translation"
        case "orig", "original":
            return "Original"
        default:
            return key.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }
}

extension WordTimingToken {
    init?(entry: JobTimingEntry) {
        guard let start = entry.t0 ?? entry.start ?? entry.begin ?? entry.time,
              let endValue = entry.t1 ?? entry.end ?? entry.stop ?? entry.time else {
            return nil
        }
        let textValue = entry.text?.nonEmptyValue ?? entry.token?.nonEmptyValue ?? ""
        let sentenceIndex = entry.sentenceIdx ?? entry.sentenceIdMixed ?? Int(entry.sentenceID ?? "")
        let identifier = entry.rawID ?? UUID().uuidString
        self.init(
            id: identifier,
            text: textValue,
            sentenceIndex: sentenceIndex,
            startTime: min(start, endValue),
            endTime: max(endValue, start)
        )
    }
}
