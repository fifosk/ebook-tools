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
    @Published private(set) var chapterEntries: [ChapterNavigationEntry] = []
    @Published private(set) var readingBedCatalog: ReadingBedListResponse?
    @Published private(set) var readingBedURL: URL?
    @Published private(set) var selectedReadingBedID: String?

    let audioCoordinator = AudioPlayerCoordinator()

    private var mediaResolver: MediaURLResolver?
    private var apiBaseURL: URL?
    private var authToken: String?
    private var apiConfiguration: APIClientConfiguration?
    private var preferredAudioKind: InteractiveChunk.AudioOption.Kind?
    private var audioDurationByURL: [URL: Double] = [:]
    private var chunkMetadataLoaded: Set<String> = []
    private var chunkMetadataLoading: Set<String> = []
    private var pendingSentenceJump: PendingSentenceJump?
    private let defaultReadingBedPath = "/assets/reading-beds/lost-in-the-pages.mp3"

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
        apiBaseURL = configuration.apiBaseURL
        authToken = configuration.authToken
        apiConfiguration = configuration
        selectedChunkID = nil
        selectedAudioTrackID = nil
        selectedTimingURL = nil
        preferredAudioKind = nil
        audioDurationByURL = [:]
        chunkMetadataLoaded = []
        chunkMetadataLoading = []
        jobContext = nil
        mediaResponse = nil
        timingResponse = nil
        chapterEntries = []
        readingBedCatalog = nil
        readingBedURL = nil
        selectedReadingBedID = nil
        mediaResolver = nil
        audioCoordinator.reset()
        pendingSentenceJump = nil

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
            async let readingBedsTask: ReadingBedListResponse? = {
                do {
                    return try await client.fetchReadingBeds()
                } catch {
                    return nil
                }
            }()
            let (media, timing) = try await (mediaTask, timingTask)
            let readingBeds = await readingBedsTask
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
            readingBedCatalog = readingBeds
            selectedReadingBedID = nil
            readingBedURL = resolveReadingBedURL(from: readingBeds, selectedID: nil)
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
        attemptPendingSentenceJump(in: chunk)
        Task { [weak self] in
            await self?.loadChunkMetadataIfNeeded(for: chunk.id)
        }
    }

    func selectAudioTrack(id: String) {
        guard selectedAudioTrackID != id else { return }
        selectedAudioTrackID = id
        guard let chunk = selectedChunk else { return }
        if let track = chunk.audioOptions.first(where: { $0.id == id }) {
            preferredAudioKind = track.kind
        }
        prepareAudio(for: chunk, autoPlay: audioCoordinator.isPlaybackRequested)
    }

    func lookupAssistant(query: String, inputLanguage: String, lookupLanguage: String) async throws -> AssistantLookupResponse {
        guard let configuration = apiConfiguration else {
            throw AssistantLookupError.missingConfiguration
        }
        let client = APIClient(configuration: configuration)
        return try await client.assistantLookup(
            query: query,
            inputLanguage: inputLanguage,
            lookupLanguage: lookupLanguage
        )
    }

    func synthesizePronunciation(text: String, language: String?) async throws -> Data {
        guard let configuration = apiConfiguration else {
            throw PronunciationError.missingConfiguration
        }
        let client = APIClient(configuration: configuration)
        return try await client.synthesizeAudio(text: text, language: language)
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
        guard let chunk = selectedChunk else {
            return audioCoordinator.currentTime
        }
        let time = usesCombinedQueue(for: chunk) ? audioCoordinator.currentTime : playbackTime(for: chunk)
        return time.isFinite ? time : audioCoordinator.currentTime
    }

    func resolveMediaURL(for file: PipelineMediaFile) -> URL? {
        guard let jobId, let mediaResolver else { return nil }
        return mediaResolver.resolveFileURL(jobId: jobId, file: file)
    }

    func resolvePath(_ path: String) -> URL? {
        guard let jobId, let mediaResolver else { return nil }
        return mediaResolver.resolvePath(jobId: jobId, relativePath: path)
    }

    func selectReadingBed(id: String?) {
        let normalized = id?.nonEmptyValue
        let validID: String?
        if let normalized,
           let beds = readingBedCatalog?.beds,
           beds.contains(where: { $0.id == normalized }) {
            validID = normalized
        } else {
            validID = nil
        }
        selectedReadingBedID = validID
        readingBedURL = resolveReadingBedURL(from: readingBedCatalog, selectedID: validID)
    }

    private func resolveReadingBedURL(from catalog: ReadingBedListResponse?, selectedID: String?) -> URL? {
        guard let apiBaseURL else { return nil }
        let selectedEntry = selectReadingBed(from: catalog, selectedID: selectedID)
        let rawPath = selectedEntry?.url.nonEmptyValue ?? defaultReadingBedPath
        guard let url = buildReadingBedURL(from: rawPath, baseURL: apiBaseURL) else { return nil }
        return appendAccessToken(url, token: authToken)
    }

    private func selectReadingBed(from catalog: ReadingBedListResponse?, selectedID: String?) -> ReadingBedEntry? {
        guard let beds = catalog?.beds, !beds.isEmpty else { return nil }
        if let selectedID,
           let match = beds.first(where: { $0.id == selectedID }) {
            return match
        }
        if let defaultId = catalog?.defaultId?.nonEmptyValue,
           let match = beds.first(where: { $0.id == defaultId }) {
            return match
        }
        if let match = beds.first(where: { $0.isDefault == true }) {
            return match
        }
        return beds.first
    }

    private func buildReadingBedURL(from rawPath: String, baseURL: URL) -> URL? {
        let trimmed = rawPath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if let url = URL(string: trimmed), url.scheme != nil {
            return url
        }
        var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) ?? URLComponents()
        let basePath = components.path
        let suffix = trimmed.hasPrefix("/") ? String(trimmed.dropFirst()) : trimmed
        let resolvedPath: String
        if basePath.isEmpty || basePath == "/" {
            resolvedPath = "/" + suffix
        } else if basePath.hasSuffix("/") {
            resolvedPath = basePath + suffix
        } else {
            resolvedPath = basePath + "/" + suffix
        }
        components.path = resolvedPath
        return components.url ?? baseURL.appendingPathComponent(suffix)
    }

    private func appendAccessToken(_ url: URL, token: String?) -> URL {
        guard let token, !token.isEmpty else { return url }
        guard var components = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return url }
        var items = components.queryItems ?? []
        if items.contains(where: { $0.name == "access_token" }) {
            return url
        }
        items.append(URLQueryItem(name: "access_token", value: token))
        components.queryItems = items
        return components.url ?? url
    }

    func recordAudioDuration(_ duration: Double, for url: URL?) {
        guard let url else { return }
        guard duration.isFinite, duration > 0 else { return }
        audioDurationByURL[url] = duration
    }

    func playbackTime(for chunk: InteractiveChunk) -> Double {
        let baseTime = audioCoordinator.currentTime
        guard let track = selectedAudioOption(for: chunk) else { return baseTime }
        if usesCombinedQueue(for: chunk) {
            return combinedQueuePlaybackTime(for: chunk)
        }
        let urls = track.streamURLs
        guard urls.count > 1,
              let activeURL = audioCoordinator.activeURL,
              let activeIndex = urls.firstIndex(of: activeURL) else {
            return baseTime
        }
        let offset = urls.prefix(activeIndex).reduce(0.0) { partial, url in
            partial + (durationForURL(url, in: chunk) ?? 0)
        }
        return offset + baseTime
    }

    func playbackDuration(for chunk: InteractiveChunk) -> Double? {
        guard let track = selectedAudioOption(for: chunk) else {
            return audioCoordinator.duration > 0 ? audioCoordinator.duration : nil
        }
        if track.streamURLs.count == 1 {
            if let activeDuration = activeTrackDuration(for: track) {
                return activeDuration
            }
            if let duration = track.duration, duration > 0 {
                return duration
            }
            if let cached = durationForURL(track.primaryURL, in: chunk), cached > 0 {
                return cached
            }
            return audioCoordinator.duration > 0 ? audioCoordinator.duration : nil
        }
        if useCombinedPhases(for: chunk) {
            let durations = track.streamURLs.map { durationForURL($0, in: chunk) }
            let summed = durations.compactMap { $0 }.reduce(0, +)
            if durations.allSatisfy({ ($0 ?? 0) > 0 }), summed > 0 {
                return summed
            }
            if let fallback = fallbackDuration(for: chunk, kind: .combined), fallback > 0 {
                return fallback
            }
            if let duration = track.duration, duration > 0 {
                return duration
            }
            return summed > 0 ? summed : nil
        }
        if let activeDuration = currentItemDuration(for: track) {
            return activeDuration
        }
        if let activeURL = audioCoordinator.activeURL,
           let activeDuration = durationForURL(activeURL, in: chunk), activeDuration > 0 {
            return activeDuration
        }
        return audioCoordinator.duration > 0 ? audioCoordinator.duration : nil
    }

    func combinedPlaybackDuration(for chunk: InteractiveChunk) -> Double? {
        guard let track = selectedAudioOption(for: chunk) else {
            return playbackDuration(for: chunk)
        }
        guard track.kind == .combined, track.streamURLs.count > 1 else {
            return playbackDuration(for: chunk)
        }
        let originalDuration = combinedTrackDuration(kind: .original, in: chunk)
        let translationDuration = combinedTrackDuration(kind: .translation, in: chunk)
        if let originalDuration, let translationDuration {
            return originalDuration + translationDuration
        }
        if let duration = track.duration, duration > 0 {
            return duration
        }
        if let originalDuration {
            return originalDuration
        }
        if let translationDuration {
            return translationDuration
        }
        let durations = track.streamURLs.map { durationForURL($0, in: chunk) }
        let total = durations.compactMap { $0 }.reduce(0, +)
        if durations.allSatisfy({ ($0 ?? 0) > 0 }), total > 0 {
            return total
        }
        if let fallback = fallbackDuration(for: chunk, kind: .combined), fallback > 0 {
            return fallback
        }
        return total > 0 ? total : nil
    }

    func combinedQueuePlaybackTime(for chunk: InteractiveChunk) -> Double {
        let baseTime = audioCoordinator.currentTime
        guard let track = selectedAudioOption(for: chunk) else { return baseTime }
        guard track.kind == .combined, track.streamURLs.count > 1 else { return baseTime }
        guard let activeURL = audioCoordinator.activeURL,
              let activeIndex = track.streamURLs.firstIndex(of: activeURL) else {
            return baseTime
        }
        guard activeIndex > 0 else { return baseTime }
        let originalDuration = combinedTrackDuration(kind: .original, in: chunk)
            ?? durationForURL(track.streamURLs.first ?? activeURL, in: chunk)
            ?? 0
        return max(0, originalDuration) + baseTime
    }

    func timelineDuration(for chunk: InteractiveChunk) -> Double? {
        guard let track = selectedAudioOption(for: chunk) else {
            return audioCoordinator.duration > 0 ? audioCoordinator.duration : nil
        }
        if track.streamURLs.count > 1 {
            if useCombinedPhases(for: chunk) {
                let durations = track.streamURLs.map { durationForURL($0, in: chunk) }
                let total = durations.compactMap { $0 }.reduce(0, +)
                if durations.allSatisfy({ ($0 ?? 0) > 0 }), total > 0 {
                    return total
                }
                if let fallback = fallbackDuration(for: chunk, kind: .combined), fallback > 0 {
                    return fallback
                }
                return total > 0 ? total : nil
            }
            if let activeDuration = currentItemDuration(for: track) {
                return activeDuration
            }
            if let activeURL = audioCoordinator.activeURL,
               let activeDuration = durationForURL(activeURL, in: chunk), activeDuration > 0 {
                return activeDuration
            }
            return audioCoordinator.duration > 0 ? audioCoordinator.duration : nil
        }
        if let activeDuration = activeTrackDuration(for: track) {
            return activeDuration
        }
        if let duration = track.duration, duration > 0 {
            return duration
        }
        if let cached = durationForURL(track.primaryURL, in: chunk), cached > 0 {
            return cached
        }
        return audioCoordinator.duration > 0 ? audioCoordinator.duration : nil
    }

    func activeTimingTrack(for chunk: InteractiveChunk) -> TextPlayerTimingTrack {
        guard let track = selectedAudioOption(for: chunk) else { return .translation }
        switch track.kind {
        case .combined:
            if track.streamURLs.count > 1 {
                if let activeURL = audioCoordinator.activeURL {
                    if activeURL == track.streamURLs.first {
                        return .original
                    }
                    return .translation
                }
                return .original
            }
            return .mix
        case .original:
            return .original
        case .translation:
            return .translation
        case .other:
            return .translation
        }
    }

    func useCombinedPhases(for chunk: InteractiveChunk) -> Bool {
        guard let track = selectedAudioOption(for: chunk) else { return false }
        return track.kind == .combined && track.streamURLs.count == 1
    }

    func usesCombinedQueue(for chunk: InteractiveChunk) -> Bool {
        guard let track = selectedAudioOption(for: chunk) else { return false }
        return track.kind == .combined && track.streamURLs.count > 1
    }

    private func selectedAudioOption(for chunk: InteractiveChunk) -> InteractiveChunk.AudioOption? {
        guard let selectedID = selectedAudioTrackID else {
            return chunk.audioOptions.first
        }
        return chunk.audioOptions.first(where: { $0.id == selectedID }) ?? chunk.audioOptions.first
    }

    private func durationForURL(_ url: URL, in chunk: InteractiveChunk) -> Double? {
        let matchingOptions = chunk.audioOptions.filter { $0.primaryURL == url }
        if let option = matchingOptions.first(where: { $0.kind != .combined }), let duration = option.duration, duration > 0 {
            return duration
        }
        if let option = matchingOptions.first, let duration = option.duration, duration > 0 {
            return duration
        }
        if let option = matchingOptions.first,
           let fallback = fallbackDuration(for: chunk, kind: option.kind),
           fallback > 0 {
            return fallback
        }
        if let cached = audioDurationByURL[url], cached > 0 {
            return cached
        }
        return nil
    }

    private func durationForOption(
        kind: InteractiveChunk.AudioOption.Kind,
        in chunk: InteractiveChunk
    ) -> Double? {
        guard let option = chunk.audioOptions.first(where: { $0.kind == kind }) else {
            return nil
        }
        if let duration = option.duration, duration > 0 {
            return duration
        }
        return nil
    }

    private func combinedTrackDuration(
        kind: InteractiveChunk.AudioOption.Kind,
        in chunk: InteractiveChunk
    ) -> Double? {
        guard let option = chunk.audioOptions.first(where: { $0.kind == kind }) else {
            return nil
        }
        if let duration = option.duration, duration > 0 {
            return duration
        }
        let total = chunk.sentences.reduce(0.0) { partial, sentence in
            let value: Double? = {
                switch kind {
                case .original:
                    return sentence.phaseDurations?.original
                case .translation:
                    return sentence.phaseDurations?.translation
                case .combined, .other:
                    return nil
                }
            }()
            guard let value, value > 0 else { return partial }
            return partial + value
        }
        if total > 0 {
            return total
        }
        if let fallback = fallbackDuration(for: chunk, kind: kind), fallback > 0 {
            return fallback
        }
        if let cached = audioDurationByURL[option.primaryURL], cached > 0 {
            return cached
        }
        return nil
    }

    private func activeTrackDuration(for track: InteractiveChunk.AudioOption) -> Double? {
        guard track.streamURLs.count == 1,
              let activeURL = audioCoordinator.activeURL,
              activeURL == track.primaryURL else {
            return nil
        }
        let duration = audioCoordinator.duration
        guard duration.isFinite, duration > 0 else { return nil }
        return duration
    }

    private func currentItemDuration(for track: InteractiveChunk.AudioOption) -> Double? {
        guard let activeURL = audioCoordinator.activeURL,
              track.streamURLs.contains(activeURL) else {
            return nil
        }
        let duration = audioCoordinator.duration
        guard duration.isFinite, duration > 0 else { return nil }
        return duration
    }

    func fallbackDuration(
        for chunk: InteractiveChunk,
        kind: InteractiveChunk.AudioOption.Kind
    ) -> Double? {
        func sumPhase(
            _ keyPath: KeyPath<ChunkSentencePhaseDurations, Double?>,
            allowTotalFallback: Bool
        ) -> Double? {
            var total = 0.0
            var hasValue = false
            for sentence in chunk.sentences {
                if let phase = sentence.phaseDurations,
                   let value = phase[keyPath: keyPath],
                   value > 0 {
                    total += value
                    hasValue = true
                    continue
                }
                if allowTotalFallback,
                   let totalDuration = sentence.totalDuration,
                   totalDuration > 0 {
                    total += totalDuration
                    hasValue = true
                }
            }
            return hasValue ? total : nil
        }

        switch kind {
        case .original:
            return sumPhase(\.original, allowTotalFallback: false)
        case .translation:
            return sumPhase(\.translation, allowTotalFallback: true)
        case .combined:
            let original = sumPhase(\.original, allowTotalFallback: false)
            let translation = sumPhase(\.translation, allowTotalFallback: true)
            if let original, let translation {
                return original + translation
            }
            return translation ?? original
        case .other:
            return nil
        }
    }

    func seekPlayback(to time: Double, in chunk: InteractiveChunk) {
        guard let track = selectedAudioOption(for: chunk) else {
            audioCoordinator.seek(to: time)
            return
        }
        let urls = track.streamURLs
        guard urls.count > 1 else {
            audioCoordinator.seek(to: time)
            return
        }
        if !usesCombinedQueue(for: chunk) {
            audioCoordinator.seek(to: time)
            return
        }
        let durations = urls.map { durationForURL($0, in: chunk) ?? 0 }
        var remaining = time
        var targetIndex = 0
        for (index, duration) in durations.enumerated() {
            if duration <= 0 {
                continue
            }
            if remaining <= duration || index == durations.count - 1 {
                targetIndex = index
                break
            }
            remaining -= duration
            targetIndex = index + 1
        }
        if targetIndex >= urls.count {
            targetIndex = urls.count - 1
        }
        let targetURL = urls[targetIndex]
        if audioCoordinator.activeURL != targetURL {
            let subset = Array(urls[targetIndex...])
            audioCoordinator.load(urls: subset, autoPlay: audioCoordinator.isPlaybackRequested)
        }
        audioCoordinator.seek(to: remaining)
    }

    func activeSentence(at time: Double) -> InteractiveChunk.Sentence? {
        guard time.isFinite else { return nil }
        guard let chunk = selectedChunk else { return nil }
        if let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack(for: chunk),
            audioDuration: playbackDuration(for: chunk),
            useCombinedPhases: useCombinedPhases(for: chunk)
        ),
        let display = TextPlayerTimeline.buildTimelineDisplay(
            timelineSentences: timelineSentences,
            chunkTime: time,
            audioDuration: playbackDuration(for: chunk),
            isVariantVisible: { _ in true }
        ),
        chunk.sentences.indices.contains(display.activeIndex) {
            return chunk.sentences[display.activeIndex]
        }
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
        let currentTime = highlightingTime.isFinite ? highlightingTime : audioCoordinator.currentTime
        guard currentTime.isFinite else { return }
        let epsilon = 0.05
        let sorted: [(Int, Double)] = {
            if let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
                sentences: chunk.sentences,
                activeTimingTrack: activeTimingTrack(for: chunk),
                audioDuration: playbackDuration(for: chunk),
                useCombinedPhases: useCombinedPhases(for: chunk)
            ) {
                return timelineSentences.map { ($0.index, $0.startTime) }.sorted { $0.1 < $1.1 }
            }
            let entries = chunk.sentences.compactMap { sentence -> (Int, Double)? in
                guard let start = sentence.startTime else { return nil }
                return (sentence.id, start)
            }
            return entries.sorted { $0.1 < $1.1 }
        }()

        if sorted.isEmpty {
            return
        }

        if forward {
            if let next = sorted.first(where: { $0.1 > currentTime + epsilon }) {
                seekPlayback(to: next.1, in: chunk)
                return
            }
            if let nextChunk = jobContext?.nextChunk(after: chunk.id) {
                selectChunk(id: nextChunk.id, autoPlay: audioCoordinator.isPlaybackRequested)
            }
        } else {
            if let previous = sorted.last(where: { $0.1 < currentTime - epsilon }) {
                seekPlayback(to: previous.1, in: chunk)
                return
            }
            if let previousChunk = jobContext?.previousChunk(before: chunk.id) {
                selectChunk(id: previousChunk.id, autoPlay: audioCoordinator.isPlaybackRequested)
            }
        }
    }

    func jumpToSentence(_ sentenceNumber: Int, autoPlay: Bool = false) {
        guard let context = jobContext else { return }
        guard sentenceNumber > 0 else { return }
        guard let targetChunk = resolveChunk(containing: sentenceNumber, in: context) else { return }
        pendingSentenceJump = PendingSentenceJump(chunkID: targetChunk.id, sentenceNumber: sentenceNumber)
        selectChunk(id: targetChunk.id, autoPlay: autoPlay)
        attemptPendingSentenceJump(in: targetChunk)
        if selectedChunkID == targetChunk.id {
            Task { [weak self] in
                await self?.loadChunkMetadataIfNeeded(for: targetChunk.id)
            }
        }
    }

    @MainActor
    func updateChapterIndex(from metadata: [String: JSONValue]?) async {
        chapterEntries = []
        guard let metadata else { return }
        let metadataRoot = extractBookMetadata(from: metadata) ?? metadata
        let inlineIndex = metadataValue(metadataRoot, keys: ["content_index", "contentIndex"])
            ?? metadataValue(metadata, keys: ["content_index", "contentIndex"])
        if let inlineIndex,
           let chapters = parseContentIndex(from: inlineIndex),
           !chapters.isEmpty {
            chapterEntries = chapters
            return
        }
        guard let jobId, let resolver = mediaResolver else { return }
        let urlCandidate = metadataString(metadataRoot, keys: ["content_index_url", "contentIndexUrl"])
            ?? metadataString(metadata, keys: ["content_index_url", "contentIndexUrl"])
        let pathCandidate = metadataString(metadataRoot, keys: ["content_index_path", "contentIndexPath"])
            ?? metadataString(metadata, keys: ["content_index_path", "contentIndexPath"])
        guard let target = urlCandidate ?? pathCandidate,
              let url = resolver.resolvePath(jobId: jobId, relativePath: target) else {
            return
        }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            guard !Task.isCancelled else { return }
            let decoder = JSONDecoder()
            let payload = try decoder.decode(JSONValue.self, from: data)
            guard let chapters = parseContentIndex(from: payload),
                  !chapters.isEmpty else {
                return
            }
            chapterEntries = chapters
        } catch {
            return
        }
    }

    func chunkBinding() -> Binding<String> {
        Binding(
            get: {
                self.selectedChunkID ?? self.jobContext?.chunks.first?.id ?? ""
            },
            set: { newValue in
                self.selectChunk(id: newValue, autoPlay: self.audioCoordinator.isPlaybackRequested)
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
            Task { [weak self] in
                await self?.loadChunkMetadataIfNeeded(for: chunk.id)
            }
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

    private func loadChunkMetadataIfNeeded(for chunkID: String) async {
        guard let jobId, let resolver = mediaResolver else { return }
        guard let currentMediaResponse = mediaResponse else { return }
        guard !chunkMetadataLoaded.contains(chunkID) else { return }
        guard !chunkMetadataLoading.contains(chunkID) else { return }

        guard let index = resolveChunkIndex(chunkID, chunks: currentMediaResponse.chunks) else { return }
        let chunk = currentMediaResponse.chunks[index]
        if !chunk.sentences.isEmpty {
            chunkMetadataLoaded.insert(chunkID)
            return
        }
        let metadataPath = chunk.metadataURL ?? chunk.metadataPath
        guard let metadataPath,
              let url = resolver.resolvePath(jobId: jobId, relativePath: metadataPath) else {
            return
        }

        chunkMetadataLoading.insert(chunkID)
        defer { chunkMetadataLoading.remove(chunkID) }

        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            let sentences: [ChunkSentenceMetadata]
            if let payload = try? decoder.decode(ChunkMetadataPayload.self, from: data) {
                sentences = payload.sentences
            } else if let payload = try? decoder.decode([ChunkSentenceMetadata].self, from: data) {
                sentences = payload
            } else {
                return
            }
            guard !sentences.isEmpty else { return }

            var updatedChunks = currentMediaResponse.chunks
            let updatedChunk = PipelineMediaChunk(
                chunkID: chunk.chunkID,
                rangeFragment: chunk.rangeFragment,
                startSentence: chunk.startSentence,
                endSentence: chunk.endSentence,
                files: chunk.files,
                sentences: sentences,
                metadataPath: chunk.metadataPath,
                metadataURL: chunk.metadataURL,
                sentenceCount: chunk.sentenceCount ?? sentences.count,
                audioTracks: chunk.audioTracks
            )
            updatedChunks[index] = updatedChunk
            let refreshedMedia = PipelineMediaResponse(
                media: currentMediaResponse.media,
                chunks: updatedChunks,
                complete: currentMediaResponse.complete
            )
            let context = try JobContextBuilder.build(
                jobId: jobId,
                media: refreshedMedia,
                timing: timingResponse,
                resolver: resolver
            )
            mediaResponse = refreshedMedia
            jobContext = context
            if let updatedChunk = context.chunk(withID: chunkID) {
                attemptPendingSentenceJump(in: updatedChunk)
            }
            chunkMetadataLoaded.insert(chunkID)
        } catch {
            return
        }
    }

    private func resolveChunkIndex(_ chunkID: String, chunks: [PipelineMediaChunk]) -> Int? {
        if let index = chunks.firstIndex(where: { $0.chunkID == chunkID }) {
            return index
        }
        if chunkID.hasPrefix("chunk-") {
            let raw = chunkID.replacingOccurrences(of: "chunk-", with: "")
            if let index = Int(raw), chunks.indices.contains(index) {
                return index
            }
        }
        return nil
    }

    private func handlePlaybackEnded() {
        guard let chunk = selectedChunk,
              let nextChunk = jobContext?.nextChunk(after: chunk.id) else {
            return
        }
        selectChunk(id: nextChunk.id, autoPlay: true)
    }

    private func resolveChunk(containing sentenceNumber: Int, in context: JobContext) -> InteractiveChunk? {
        if let match = context.chunks.first(where: { chunk in
            chunk.sentences.contains { sentence in
                let id = sentence.displayIndex ?? sentence.id
                return id == sentenceNumber
            }
        }) {
            return match
        }
        return context.chunks.first(where: { chunk in
            guard let start = chunk.startSentence, let end = chunk.endSentence else { return false }
            return sentenceNumber >= start && sentenceNumber <= end
        })
    }

    private func attemptPendingSentenceJump(in chunk: InteractiveChunk) {
        guard let pending = pendingSentenceJump, pending.chunkID == chunk.id else { return }
        guard let startTime = startTimeForSentence(pending.sentenceNumber, in: chunk) else { return }
        pendingSentenceJump = nil
        seekPlayback(to: startTime, in: chunk)
    }

    private func startTimeForSentence(_ sentenceNumber: Int, in chunk: InteractiveChunk) -> Double? {
        let activeTimingTrack = activeTimingTrack(for: chunk)
        let useCombinedPhases = useCombinedPhases(for: chunk)
        let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
            sentences: chunk.sentences,
            activeTimingTrack: activeTimingTrack,
            audioDuration: playbackDuration(for: chunk),
            useCombinedPhases: useCombinedPhases
        )
        if let timelineSentences {
            for runtime in timelineSentences {
                guard chunk.sentences.indices.contains(runtime.index) else { continue }
                let sentence = chunk.sentences[runtime.index]
                let id = sentence.displayIndex ?? sentence.id
                if id == sentenceNumber {
                    return runtime.startTime
                }
            }
        }
        if let sentence = chunk.sentences.first(where: { ( $0.displayIndex ?? $0.id ) == sentenceNumber }) {
            return sentence.startTime
        }
        return nil
    }

    private func extractBookMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        if let direct = objectValue(metadata["book_metadata"]) {
            return direct
        }
        if let result = objectValue(metadata["result"]),
           let nested = objectValue(result["book_metadata"]) {
            return nested
        }
        return nil
    }

    private func parseContentIndex(from value: JSONValue) -> [ChapterNavigationEntry]? {
        guard let object = objectValue(value),
              let chaptersValue = object["chapters"],
              let chaptersArray = arrayValue(chaptersValue) else {
            return nil
        }
        var entries: [ChapterNavigationEntry] = []
        entries.reserveCapacity(chaptersArray.count)
        for (index, entryValue) in chaptersArray.enumerated() {
            guard let entry = objectValue(entryValue) else { continue }
            let start = intValue(entry["start_sentence"])
                ?? intValue(entry["startSentence"])
                ?? intValue(entry["start"])
            guard let start, start > 0 else { continue }
            let sentenceCount = intValue(entry["sentence_count"]) ?? intValue(entry["sentenceCount"])
            var end = intValue(entry["end_sentence"])
                ?? intValue(entry["endSentence"])
                ?? intValue(entry["end"])
            if end == nil, let count = sentenceCount {
                end = start + max(count - 1, 0)
            }
            if let endValue = end, endValue < start {
                end = start
            }
            let id = stringValue(entry["id"]) ?? "chapter-\(index + 1)"
            let title = stringValue(entry["title"])
                ?? stringValue(entry["toc_label"])
                ?? stringValue(entry["tocLabel"])
                ?? stringValue(entry["name"])
                ?? "Chapter \(index + 1)"
            entries.append(
                ChapterNavigationEntry(
                    id: id,
                    title: title,
                    startSentence: start,
                    endSentence: end
                )
            )
        }
        return entries
    }

    private func metadataValue(_ metadata: [String: JSONValue], keys: [String]) -> JSONValue? {
        for key in keys {
            if let value = metadata[key] {
                return value
            }
        }
        return nil
    }

    private func metadataString(_ metadata: [String: JSONValue], keys: [String]) -> String? {
        for key in keys {
            if let value = metadata[key], let string = stringValue(value) {
                return string
            }
        }
        return nil
    }

    private func objectValue(_ value: JSONValue?) -> [String: JSONValue]? {
        guard case let .object(object) = value else { return nil }
        return object
    }

    private func arrayValue(_ value: JSONValue?) -> [JSONValue]? {
        guard case let .array(array) = value else { return nil }
        return array
    }

    private func stringValue(_ value: JSONValue?) -> String? {
        switch value {
        case let .string(raw):
            return raw.nonEmptyValue
        case let .number(raw):
            guard raw.isFinite else { return nil }
            return String(raw).nonEmptyValue
        case let .array(values):
            for value in values {
                if let string = stringValue(value) {
                    return string
                }
            }
            return nil
        default:
            return nil
        }
    }

    private func intValue(_ value: JSONValue?) -> Int? {
        switch value {
        case let .number(raw):
            guard raw.isFinite else { return nil }
            return Int(raw.rounded())
        case let .string(raw):
            let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty else { return nil }
            if let parsed = Int(trimmed) {
                return parsed
            }
            if let parsed = Double(trimmed), parsed.isFinite {
                return Int(parsed.rounded())
            }
            return nil
        default:
            return nil
        }
    }

    private enum AssistantLookupError: LocalizedError {
        case missingConfiguration

        var errorDescription: String? {
            "Assistant lookup is not configured."
        }
    }

    private enum PronunciationError: LocalizedError {
        case missingConfiguration

        var errorDescription: String? {
            "Pronunciation audio is not configured."
        }
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

struct ChapterNavigationEntry: Identifiable, Hashable {
    let id: String
    let title: String
    let startSentence: Int
    let endSentence: Int?
}

private struct PendingSentenceJump {
    let chunkID: String
    let sentenceNumber: Int
}

struct InteractiveChunk: Identifiable {
    struct Sentence: Identifiable {
        let id: Int
        let displayIndex: Int?
        let originalText: String
        let translationText: String
        let transliterationText: String?
        let originalTokens: [String]
        let translationTokens: [String]
        let transliterationTokens: [String]
        let imagePath: String?
        let timingTokens: [WordTimingToken]
        let timeline: [ChunkSentenceTimelineEvent]
        let totalDuration: Double?
        let phaseDurations: ChunkSentencePhaseDurations?
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
    let rangeFragment: String?
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
        var fallbackStart = 1
        let chunks = media.chunks.enumerated().map { index, chunk in
            let effectiveStart = chunk.startSentence
                ?? chunk.sentences.first?.sentenceNumber
                ?? fallbackStart
            let built = buildChunk(
                chunk,
                index: index,
                jobId: jobId,
                groupedTokens: groupedTokens,
                resolver: resolver,
                audioFiles: globalAudioFiles,
                fallbackStart: effectiveStart
            )
            if let end = chunk.endSentence {
                fallbackStart = end + 1
            } else if let start = chunk.startSentence, !chunk.sentences.isEmpty {
                fallbackStart = start + chunk.sentences.count
            } else if !chunk.sentences.isEmpty {
                fallbackStart = effectiveStart + chunk.sentences.count
            }
            return built
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
        audioFiles: [PipelineMediaFile],
        fallbackStart: Int
    ) -> InteractiveChunk {
        let chunkID = chunk.chunkID ?? "chunk-\(index)"
        let label = chunkID
        let sentences = buildSentences(for: chunk, groupedTokens: groupedTokens, fallbackStart: fallbackStart)
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
            rangeFragment: chunk.rangeFragment,
            rangeDescription: range,
            startSentence: chunk.startSentence,
            endSentence: chunk.endSentence,
            sentences: sentences,
            audioOptions: audioOptions
        )
    }

    private static func buildSentences(
        for chunk: PipelineMediaChunk,
        groupedTokens: [Int: [WordTimingToken]],
        fallbackStart: Int
    ) -> [InteractiveChunk.Sentence] {
        if !chunk.sentences.isEmpty {
            let baseIndex = chunk.startSentence ?? fallbackStart
            return chunk.sentences.enumerated().map { offset, sentence in
                let explicitIndex = sentence.sentenceNumber
                let derivedIndex = baseIndex + offset
                let sentenceIndex = explicitIndex ?? derivedIndex
                let timingTokens = groupedTokens[sentenceIndex] ?? []
                let originalText = sentence.original.text
                let translationText = sentence.translation?.text ?? originalText
                let transliterationText = sentence.transliteration?.text
                let originalTokens = normaliseTokens(text: originalText, tokens: sentence.original.tokens)
                let translationTokens = normaliseTokens(text: translationText, tokens: sentence.translation?.tokens)
                let transliterationTokens = normaliseTokens(text: transliterationText ?? "", tokens: sentence.transliteration?.tokens)
                return InteractiveChunk.Sentence(
                    id: sentenceIndex,
                    displayIndex: explicitIndex ?? derivedIndex,
                    originalText: originalText,
                    translationText: translationText,
                    transliterationText: transliterationText,
                    originalTokens: originalTokens,
                    translationTokens: translationTokens,
                    transliterationTokens: transliterationTokens,
                    imagePath: sentence.imagePath,
                    timingTokens: timingTokens,
                    timeline: sentence.timeline,
                    totalDuration: sentence.totalDuration,
                    phaseDurations: sentence.phaseDurations
                )
            }
        }

        guard let start = chunk.startSentence, let end = chunk.endSentence else {
            return []
        }

        return (start...end).map { sentenceIndex in
            let timingTokens = groupedTokens[sentenceIndex] ?? []
            let tokens = timingTokens.map { $0.displayText }.filter { !$0.isEmpty }
            let text = tokens.joined(separator: " ").trimmingCharacters(in: .whitespaces)
            return InteractiveChunk.Sentence(
                id: sentenceIndex,
                displayIndex: sentenceIndex,
                originalText: text,
                translationText: text,
                transliterationText: nil,
                originalTokens: tokens,
                translationTokens: tokens,
                transliterationTokens: [],
                imagePath: nil,
                timingTokens: timingTokens,
                timeline: [],
                totalDuration: nil,
                phaseDurations: nil
            )
        }
    }

    private static func normaliseTokens(text: String, tokens: [String]?) -> [String] {
        if let tokens, !tokens.isEmpty {
            return tokens.filter { !$0.isEmpty }
        }
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return [] }
        return trimmed
            .split(whereSeparator: { $0.isWhitespace })
            .map { String($0) }
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
        guard !timingTokens.isEmpty else { return nil }
        return timingTokens.map(\.startTime).min()
    }

    var endTime: Double? {
        guard !timingTokens.isEmpty else { return nil }
        return timingTokens.map(\.endTime).max()
    }

    func contains(time: Double) -> Bool {
        guard let start = startTime, let end = endTime else { return false }
        return time >= start && time <= end
    }
}
