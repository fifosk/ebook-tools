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

    @Published private(set) var loadState: LoadState = .idle
    @Published private(set) var jobId: String?
    @Published private(set) var jobContext: JobContext?
    @Published private(set) var selectedChunkID: String?
    @Published private(set) var selectedAudioTrackID: String?
    @Published private(set) var selectedTimingURL: URL?
    @Published private(set) var mediaResponse: PipelineMediaResponse?
    @Published private(set) var timingResponse: JobTimingResponse?

    let audioCoordinator = AudioPlayerCoordinator()

    private var mediaResolver: MediaURLResolver?
    private var preferredAudioKind: InteractiveChunk.AudioOption.Kind?

    init() {
        audioCoordinator.onPlaybackEnded = { [weak self] in
            self?.handlePlaybackEnded()
        }
    }

    func loadJob(jobId: String, configuration: APIClientConfiguration, origin: MediaOrigin = .job) async {
        let trimmedJobId = jobId.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedJobId.isEmpty else {
            loadState = .error("Enter a job identifier before loading.")
            return
        }

        loadState = .loading
        self.jobId = trimmedJobId
        selectedChunkID = nil
        selectedAudioTrackID = nil
        selectedTimingURL = nil
        preferredAudioKind = nil
        jobContext = nil
        mediaResponse = nil
        timingResponse = nil
        mediaResolver = nil
        audioCoordinator.reset()

        do {
            let client = APIClient(configuration: configuration)
            async let mediaTask: PipelineMediaResponse = {
                switch origin {
                case .library:
                    return try await client.fetchLibraryMedia(jobId: trimmedJobId)
                case .job:
                    return try await client.fetchJobMedia(jobId: trimmedJobId)
                }
            }()
            async let timingTask = client.fetchJobTiming(jobId: trimmedJobId)
            let (media, timing) = try await (mediaTask, timingTask)
            let resolver: MediaURLResolver
            switch origin {
            case .library:
                resolver = MediaURLResolver(
                    origin: .library(apiBaseURL: configuration.apiBaseURL, accessToken: configuration.authToken)
                )
            case .job:
                let storageResolver = try StorageResolver(
                    apiBaseURL: configuration.apiBaseURL,
                    override: configuration.storageBaseURL
                )
                resolver = MediaURLResolver(
                    origin: .storage(
                        apiBaseURL: configuration.apiBaseURL,
                        resolver: storageResolver,
                        accessToken: configuration.authToken
                    )
                )
            }
            let context = try JobContextBuilder.build(
                jobId: trimmedJobId,
                media: media,
                timing: timing,
                resolver: resolver
            )
            jobContext = context
            mediaResolver = resolver
            mediaResponse = media
            timingResponse = timing
            configureDefaultSelections()
            loadState = .loaded
        } catch is CancellationError {
            loadState = .idle
        } catch {
            loadState = .error(error.localizedDescription)
        }
    }

    func selectChunk(id: String, autoPlay: Bool = false) {
        guard selectedChunkID != id else { return }
        selectedChunkID = id
        guard let chunk = selectedChunk else {
            audioCoordinator.reset()
            selectedTimingURL = nil
            return
        }
        if !(chunk.audioOptions.contains { $0.id == selectedAudioTrackID }) {
            let preferred = preferredAudioKind.flatMap { kind in
                chunk.audioOptions.first(where: { $0.kind == kind })
            }
            selectedAudioTrackID = preferred?.id ?? chunk.audioOptions.first?.id
        }
        prepareAudio(for: chunk, autoPlay: autoPlay)
    }

    func selectAudioTrack(id: String) {
        guard selectedAudioTrackID != id else { return }
        selectedAudioTrackID = id
        guard let chunk = selectedChunk else { return }
        if let track = chunk.audioOptions.first(where: { $0.id == id }) {
            preferredAudioKind = track.kind
        }
        prepareAudio(for: chunk, autoPlay: audioCoordinator.isPlaying)
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

    var highlightingTime: Double {
        guard let timingURL = selectedTimingURL else {
            return audioCoordinator.currentTime
        }
        guard let activeURL = audioCoordinator.activeURL, activeURL == timingURL else {
            return .nan
        }
        return audioCoordinator.currentTime
    }

    func resolveMediaURL(for file: PipelineMediaFile) -> URL? {
        guard let jobId, let mediaResolver else { return nil }
        return mediaResolver.resolveFileURL(jobId: jobId, file: file)
    }

    func resolvePath(_ path: String) -> URL? {
        guard let jobId, let mediaResolver else { return nil }
        return mediaResolver.resolvePath(jobId: jobId, relativePath: path)
    }

    func activeSentence(at time: Double) -> InteractiveChunk.Sentence? {
        guard time.isFinite else { return nil }
        guard let chunk = selectedChunk else { return nil }
        if let match = chunk.sentences.first(where: { $0.contains(time: time) }) {
            return match
        }
        let sorted = chunk.sentences
            .compactMap { sentence -> (InteractiveChunk.Sentence, Double)? in
                guard let start = sentence.startTime else { return nil }
                return (sentence, start)
            }
            .sorted { $0.1 < $1.1 }
        return sorted.last(where: { $0.1 <= time })?.0
    }

    func skipSentence(forward: Bool) {
        guard let chunk = selectedChunk else { return }
        let entries = chunk.sentences.compactMap { sentence -> (InteractiveChunk.Sentence, Double)? in
            guard let start = sentence.startTime else { return nil }
            return (sentence, start)
        }
        if entries.isEmpty {
            return
        }
        let sorted = entries.sorted { $0.1 < $1.1 }
        let currentTime = highlightingTime
        guard currentTime.isFinite else { return }
        let epsilon = 0.05

        if forward {
            if let next = sorted.first(where: { $0.1 > currentTime + epsilon }) {
                audioCoordinator.seek(to: next.1)
                return
            }
            if let nextChunk = jobContext?.nextChunk(after: chunk.id) {
                selectChunk(id: nextChunk.id, autoPlay: audioCoordinator.isPlaying)
            }
        } else {
            if let previous = sorted.last(where: { $0.1 < currentTime - epsilon }) {
                audioCoordinator.seek(to: previous.1)
                return
            }
            if let previousChunk = jobContext?.previousChunk(before: chunk.id) {
                selectChunk(id: previousChunk.id, autoPlay: audioCoordinator.isPlaying)
            }
        }
    }

    func chunkBinding() -> Binding<String> {
        Binding(
            get: {
                self.selectedChunkID ?? self.jobContext?.chunks.first?.id ?? ""
            },
            set: { newValue in
                self.selectChunk(id: newValue, autoPlay: self.audioCoordinator.isPlaying)
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
            if let option = chunk.audioOptions.first {
                selectedAudioTrackID = option.id
                preferredAudioKind = option.kind
            } else {
                selectedAudioTrackID = nil
            }
            prepareAudio(for: chunk, autoPlay: false)
        } else {
            selectedChunkID = nil
            selectedAudioTrackID = nil
            audioCoordinator.reset()
            selectedTimingURL = nil
            preferredAudioKind = nil
        }
    }

    private func prepareAudio(for chunk: InteractiveChunk, autoPlay: Bool) {
        guard let trackID = selectedAudioTrackID,
              let track = chunk.audioOptions.first(where: { $0.id == trackID }) else {
            audioCoordinator.reset()
            selectedTimingURL = nil
            return
        }
        audioCoordinator.load(urls: track.streamURLs, autoPlay: autoPlay)
        selectedTimingURL = track.timingURL ?? track.streamURLs.first
    }

    private func handlePlaybackEnded() {
        guard let chunk = selectedChunk,
              let nextChunk = jobContext?.nextChunk(after: chunk.id) else {
            return
        }
        selectChunk(id: nextChunk.id, autoPlay: true)
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

    func nextChunk(after id: String) -> InteractiveChunk? {
        guard let index = chunkIndex[id] else { return nil }
        let nextIndex = index + 1
        guard chunks.indices.contains(nextIndex) else { return nil }
        return chunks[nextIndex]
    }

    func previousChunk(before id: String) -> InteractiveChunk? {
        guard let index = chunkIndex[id] else { return nil }
        let previousIndex = index - 1
        guard chunks.indices.contains(previousIndex) else { return nil }
        return chunks[previousIndex]
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
        enum Kind: String {
            case combined
            case translation
            case original
            case other
        }

        let id: String
        let label: String
        let kind: Kind
        let streamURLs: [URL]
        let timingURL: URL?
        let duration: Double?

        var primaryURL: URL {
            streamURLs[0]
        }
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
        guard time.isFinite else { return false }
        let start = startTime - tolerance
        let end = endTime + tolerance
        return time >= start && time <= end
    }
}

// MARK: - Context Builder

enum JobContextBuilder {
    static func build(jobId: String, media: PipelineMediaResponse, timing: JobTimingResponse?, resolver: MediaURLResolver) throws -> JobContext {
        let tokens = timing?.tracks.translation.segments.compactMap { WordTimingToken(entry: $0) } ?? []
        let groupedTokens = Dictionary(grouping: tokens) { token -> Int in
            token.sentenceIndex ?? -1
        }
        let globalAudioFiles = media.media["audio"] ?? []
        let chunks = media.chunks.enumerated().map { index, chunk in
            buildChunk(
                chunk,
                index: index,
                jobId: jobId,
                groupedTokens: groupedTokens,
                resolver: resolver,
                audioFiles: globalAudioFiles
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
        resolver: MediaURLResolver,
        audioFiles: [PipelineMediaFile]
    ) -> InteractiveChunk {
        let chunkID = chunk.chunkID ?? "chunk-\(index)"
        let label = chunkID
        let sentences = buildSentences(for: chunk, groupedTokens: groupedTokens)
        let chunkAudioFiles = filterAudioFiles(from: chunk.files)
        let audioOptions = buildAudioOptions(
            for: chunk,
            chunkID: chunkID,
            jobId: jobId,
            resolver: resolver,
            chunkFiles: chunkAudioFiles,
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
        resolver: MediaURLResolver,
        chunkFiles: [PipelineMediaFile],
        fallbackFiles: [PipelineMediaFile]
    ) -> [InteractiveChunk.AudioOption] {
        var optionsByKind: [InteractiveChunk.AudioOption.Kind: InteractiveChunk.AudioOption] = [:]
        var otherOptions: [InteractiveChunk.AudioOption] = []
        var otherURLKeys: Set<String> = []

        func registerOption(
            kind: InteractiveChunk.AudioOption.Kind,
            id: String,
            label: String,
            urls: [URL],
            timingURL: URL?,
            duration: Double?
        ) {
            guard let primaryURL = urls.first else { return }
            if kind == .other {
                let key = dedupedURLKey(for: primaryURL)
                guard !otherURLKeys.contains(key) else { return }
                otherURLKeys.insert(key)
                otherOptions.append(
                    InteractiveChunk.AudioOption(
                        id: id,
                        label: label,
                        kind: kind,
                        streamURLs: urls,
                        timingURL: timingURL,
                        duration: duration
                    )
                )
                return
            }
            guard optionsByKind[kind] == nil else { return }
            optionsByKind[kind] = InteractiveChunk.AudioOption(
                id: id,
                label: label,
                kind: kind,
                streamURLs: urls,
                timingURL: timingURL,
                duration: duration
            )
        }

        for (key, metadata) in chunk.audioTracks {
            guard let url = resolveAudioURL(jobId: jobId, track: metadata, resolver: resolver) else { continue }
            let kind = audioKind(for: key)
            registerOption(
                kind: kind,
                id: "\(chunkID)|\(key)",
                label: displayName(for: key),
                urls: [url],
                timingURL: url,
                duration: metadata.duration
            )
        }

        for file in chunkFiles {
            guard let url = resolveFileURL(jobId: jobId, file: file, resolver: resolver) else { continue }
            let kind = audioKind(for: file)
            registerOption(
                kind: kind,
                id: "\(chunkID)|file|\(file.name)",
                label: labelForAudioFile(file),
                urls: [url],
                timingURL: url,
                duration: nil
            )
        }

        let matches = matchingAudioFiles(for: chunk, fallbackFiles: fallbackFiles)
        for file in matches {
            guard let url = resolveFileURL(jobId: jobId, file: file, resolver: resolver) else { continue }
            let kind = audioKind(for: file)
            registerOption(
                kind: kind,
                id: "\(chunkID)|fallback|\(file.name)",
                label: labelForAudioFile(file),
                urls: [url],
                timingURL: url,
                duration: nil
            )
        }

        if optionsByKind.isEmpty && otherOptions.isEmpty {
            for file in filterAudioFiles(from: fallbackFiles) {
                guard let url = resolveFileURL(jobId: jobId, file: file, resolver: resolver) else { continue }
                let kind = audioKind(for: file)
                registerOption(
                    kind: kind,
                    id: "\(chunkID)|global|\(file.name)",
                    label: labelForAudioFile(file),
                    urls: [url],
                    timingURL: url,
                    duration: nil
                )
            }
        }

        if optionsByKind[.combined] == nil {
            if let original = optionsByKind[.original], let translation = optionsByKind[.translation] {
                let combinedDuration: Double?
                if let originalDuration = original.duration, let translationDuration = translation.duration {
                    combinedDuration = originalDuration + translationDuration
                } else {
                    combinedDuration = translation.duration ?? original.duration
                }
                optionsByKind[.combined] = InteractiveChunk.AudioOption(
                    id: "\(chunkID)|combined",
                    label: "Original + Translation",
                    kind: .combined,
                    streamURLs: [original.primaryURL, translation.primaryURL],
                    timingURL: translation.primaryURL,
                    duration: combinedDuration
                )
            }
        }

        var ordered: [InteractiveChunk.AudioOption] = []
        if let combined = optionsByKind[.combined] {
            ordered.append(combined)
        }
        if let translation = optionsByKind[.translation] {
            ordered.append(translation)
        }
        if let original = optionsByKind[.original] {
            ordered.append(original)
        }
        if !otherOptions.isEmpty {
            ordered.append(contentsOf: otherOptions.sorted(by: { $0.label < $1.label }))
        }
        return ordered
    }

    private static func matchingAudioFiles(
        for chunk: PipelineMediaChunk,
        fallbackFiles: [PipelineMediaFile]
    ) -> [PipelineMediaFile] {
        let audioFallbacks = filterAudioFiles(from: fallbackFiles)
        guard !audioFallbacks.isEmpty else { return [] }
        let matches = audioFallbacks.filter { file in
            if let chunkID = chunk.chunkID, let fileChunkID = file.chunkID, fileChunkID == chunkID {
                return true
            }
            if let rangeFragment = chunk.rangeFragment, let fileRange = file.rangeFragment, fileRange == rangeFragment {
                return true
            }
            if let start = chunk.startSentence, let end = chunk.endSentence,
               let fileStart = file.startSentence, let fileEnd = file.endSentence,
               start == fileStart, end == fileEnd {
                return true
            }
            let name = (file.relativePath ?? file.path ?? file.name).lowercased()
            if let rangeFragment = chunk.rangeFragment?.lowercased(), !rangeFragment.isEmpty, name.contains(rangeFragment) {
                return true
            }
            return false
        }
        return matches
    }

    private static func filterAudioFiles(from files: [PipelineMediaFile]) -> [PipelineMediaFile] {
        files.filter { isAudioFile($0) }
    }

    private static func isAudioFile(_ file: PipelineMediaFile) -> Bool {
        if let typeValue = file.type?.lowercased(), typeValue == "audio" {
            return true
        }
        let name = (file.relativePath ?? file.path ?? file.name).lowercased()
        let suffix = (name as NSString).pathExtension
        let audioExtensions: Set<String> = ["mp3", "m4a", "wav", "aac", "flac", "ogg", "opus", "m4b"]
        return audioExtensions.contains(suffix)
    }

    private static func labelForAudioFile(_ file: PipelineMediaFile) -> String {
        let rawName = file.relativePath ?? file.path ?? file.name
        let lowercased = rawName.lowercased()
        if lowercased.contains("orig_trans") || lowercased.contains("mix") {
            return "Original + Translation"
        }
        if lowercased.contains("_translation") || lowercased.contains("-translation") {
            return "Translation"
        }
        if lowercased.contains("_trans") || lowercased.contains("-trans") {
            return "Translation"
        }
        if lowercased.contains("_orig") || lowercased.contains("-orig") {
            return "Original"
        }
        if lowercased.contains("_original") || lowercased.contains("-original") {
            return "Original"
        }
        return file.name
    }

    private static func audioKind(for key: String) -> InteractiveChunk.AudioOption.Kind {
        let normalized = key.lowercased()
        if normalized == "orig_trans" || normalized == "mix" {
            return .combined
        }
        if normalized == "translation" || normalized == "trans" {
            return .translation
        }
        if normalized == "orig" || normalized == "original" {
            return .original
        }
        return .other
    }

    private static func audioKind(for file: PipelineMediaFile) -> InteractiveChunk.AudioOption.Kind {
        let rawName = (file.relativePath ?? file.path ?? file.name).lowercased()
        if rawName.contains("orig_trans") || rawName.contains("mix") {
            return .combined
        }
        if rawName.contains("_original") || rawName.contains("-original") || rawName.contains("_orig") || rawName.contains("-orig") {
            return .original
        }
        if rawName.contains("_translation") || rawName.contains("-translation") || rawName.contains("_trans") || rawName.contains("-trans") {
            return .translation
        }
        return .other
    }

    private static func dedupedURLKey(for url: URL) -> String {
        guard var components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
            return url.absoluteString
        }
        if let items = components.queryItems, !items.isEmpty {
            components.queryItems = items.filter { $0.name != "access_token" }
        }
        return components.url?.absoluteString ?? url.absoluteString
    }

    private static func resolveAudioURL(jobId: String, track: AudioTrackMetadata, resolver: MediaURLResolver) -> URL? {
        resolver.resolveAudioURL(jobId: jobId, track: track)
    }

    private static func resolveFileURL(jobId: String, file: PipelineMediaFile, resolver: MediaURLResolver) -> URL? {
        resolver.resolveFileURL(jobId: jobId, file: file)
    }

    private static func displayName(for key: String) -> String {
        switch key.lowercased() {
        case "orig_trans", "mix":
            return "Original + Translation"
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

extension InteractiveChunk.Sentence {
    var startTime: Double? {
        guard !tokens.isEmpty else { return nil }
        return tokens.map(\.startTime).min()
    }

    var endTime: Double? {
        guard !tokens.isEmpty else { return nil }
        return tokens.map(\.endTime).max()
    }

    func contains(time: Double) -> Bool {
        guard let start = startTime, let end = endTime else { return false }
        return time >= start && time <= end
    }
}
