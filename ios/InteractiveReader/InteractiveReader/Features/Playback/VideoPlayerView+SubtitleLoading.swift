import Foundation
#if canImport(CryptoKit)
import CryptoKit
#endif

extension VideoPlayerView {
    func selectDefaultTrackIfNeeded() {
        guard let current = selectedTrack else {
            selectedTrack = orderedTracks.first
            return
        }
        if let replacement = orderedTracks.first(where: { $0.id == current.id }) {
            if replacement.url != current.url {
                selectedTrack = replacement
                loadSubtitles()
            }
            return
        }
        if let labelMatch = orderedTracks.first(where: {
            $0.format == current.format && $0.label.localizedCaseInsensitiveCompare(current.label) == .orderedSame
        }) {
            selectedTrack = labelMatch
            return
        }
        selectedTrack = orderedTracks.first
    }

    func loadSubtitles() {
        guard let track = selectedTrack else {
            subtitleTask?.cancel()
            subtitleLoadingKey = nil
            cues = []
            subtitleError = nil
            return
        }
        let loadingKey = SubtitleCacheStore.shared.cacheKey(for: track)
        if subtitleLoadingKey == loadingKey, subtitleTask != nil {
            return
        }
        subtitleTask?.cancel()
        subtitleLoadingKey = loadingKey
        subtitleError = nil
        subtitleSelection = nil
        subtitleSelectionRange = nil
        subtitleActiveCueID = nil
        isManualSubtitleNavigation = false
        closeSubtitleBubble()
        let loadToken = UUID()
        subtitleLoadToken = loadToken
        subtitleTask = Task {
            defer {
                Task { @MainActor in
                    guard subtitleLoadToken == loadToken else { return }
                    subtitleTask = nil
                }
            }
            let cachedMetadata = SubtitleCacheStore.shared.cachedMetadata(for: track)
            let memoryCached = subtitleCache[loadingKey]
            let cachedEntry = memoryCached == nil
                ? await Task.detached(priority: .utility) {
                    SubtitleCacheStore.shared.cachedEntry(for: track)
                }.value
                : nil
            let cachedCues = memoryCached ?? cachedEntry?.cues
            if let cachedCues {
                await MainActor.run {
                    guard subtitleLoadToken == loadToken else { return }
                    cues = cachedCues
                    subtitleError = nil
                    subtitleCache[loadingKey] = cachedCues
                    if !coordinator.isPlaying {
                        syncSubtitleSelectionIfNeeded(force: true)
                    }
                }
            } else {
                await MainActor.run {
                    guard subtitleLoadToken == loadToken else { return }
                    cues = []
                }
            }
            do {
                let request = SubtitleCacheStore.shared.request(
                    for: track,
                    metadata: cachedMetadata
                )
                let result: SubtitleLoadResult
                if track.url.isFileURL {
                    result = try await loadLocalSubtitles(track: track)
                } else if cachedCues == nil, track.format == .srt || track.format == .vtt {
                    result = try await loadStreamingSubtitles(
                        request: request,
                        format: track.format,
                        loadToken: loadToken,
                        cachedCues: cachedCues
                    )
                } else {
                    result = try await loadRemoteSubtitles(
                        request: request,
                        format: track.format,
                        cachedCues: cachedCues
                    )
                }
                if result.usedCache {
                    await MainActor.run {
                        guard subtitleLoadToken == loadToken else { return }
                        subtitleLoadingKey = nil
                    }
                    return
                }
                await MainActor.run {
                    guard subtitleLoadToken == loadToken else { return }
                    subtitleCache[loadingKey] = result.cues
                    cues = result.cues
                    subtitleError = nil
                    subtitleLoadingKey = nil
                    if !coordinator.isPlaying {
                        syncSubtitleSelectionIfNeeded(force: true)
                    }
                }
                if !track.url.isFileURL {
                    Task.detached(priority: .utility) {
                        SubtitleCacheStore.shared.store(
                            track: track,
                            response: result.response,
                            cues: result.cues
                        )
                    }
                }
            } catch {
                if Task.isCancelled {
                    await MainActor.run {
                        guard subtitleLoadToken == loadToken else { return }
                        subtitleLoadingKey = nil
                    }
                    return
                }
                await MainActor.run {
                    guard subtitleLoadToken == loadToken else { return }
                    subtitleError = "Unable to load subtitles"
                    subtitleLoadingKey = nil
                }
            }
        }
    }

    private func loadLocalSubtitles(
        track: VideoSubtitleTrack
    ) async throws -> SubtitleLoadResult {
        let parsed = try await Task.detached(priority: .utility) { () -> [VideoSubtitleCue] in
            let data = try Data(contentsOf: track.url, options: .mappedIfSafe)
            let content = String(data: data, encoding: .utf8) ?? ""
            return SubtitleParser.parse(from: content, format: track.format)
        }.value
        return SubtitleLoadResult(cues: parsed, response: nil, usedCache: false)
    }

    private func loadRemoteSubtitles(
        request: URLRequest,
        format: SubtitleFormat,
        cachedCues: [VideoSubtitleCue]?
    ) async throws -> SubtitleLoadResult {
        let (payload, response) = try await URLSession.shared.data(for: request)
        let httpResponse = response as? HTTPURLResponse
        if let httpResponse, httpResponse.statusCode == 304 {
            if let cachedCues {
                return SubtitleLoadResult(cues: cachedCues, response: httpResponse, usedCache: true)
            }
            throw URLError(.badServerResponse)
        }
        if let httpResponse, !(200...299).contains(httpResponse.statusCode) {
            throw URLError(.badServerResponse)
        }
        let content = String(data: payload, encoding: .utf8) ?? ""
        let parsed = await Task.detached(priority: .utility) { () -> [VideoSubtitleCue] in
            SubtitleParser.parse(from: content, format: format)
        }.value
        return SubtitleLoadResult(cues: parsed, response: httpResponse, usedCache: false)
    }

    private func loadStreamingSubtitles(
        request: URLRequest,
        format: SubtitleFormat,
        loadToken: UUID,
        cachedCues: [VideoSubtitleCue]?
    ) async throws -> SubtitleLoadResult {
        let (bytes, response) = try await URLSession.shared.bytes(for: request)
        let httpResponse = response as? HTTPURLResponse
        if let httpResponse, httpResponse.statusCode == 304 {
            if let cachedCues {
                return SubtitleLoadResult(cues: cachedCues, response: httpResponse, usedCache: true)
            }
            throw URLError(.badServerResponse)
        }
        if let httpResponse, !(200...299).contains(httpResponse.statusCode) {
            throw URLError(.badServerResponse)
        }
        var parser = SubtitleParser.StreamingParser(mode: .plain)
        var parsed: [VideoSubtitleCue] = []
        var pending: [VideoSubtitleCue] = []
        var lastFlush = Date()
        var lines: [String] = []

        func flushPending(force: Bool = false) async {
            guard !pending.isEmpty else { return }
            let now = Date()
            if !force, now.timeIntervalSince(lastFlush) < 0.4, pending.count < 200 {
                return
            }
            let batch = pending
            pending.removeAll(keepingCapacity: true)
            lastFlush = now
            await MainActor.run {
                guard subtitleLoadToken == loadToken else { return }
                cues.append(contentsOf: batch)
            }
        }

        func handleLine(_ line: String) async throws {
            if Task.isCancelled {
                throw CancellationError()
            }
            lines.append(line)
            if let cue = parser.consume(line: line) {
                parsed.append(cue)
                pending.append(cue)
                if parsed.count <= 3 {
                    await flushPending(force: true)
                } else {
                    await flushPending()
                }
            }
        }

        for try await line in bytes.lines {
            if Task.isCancelled {
                throw CancellationError()
            }
            try await handleLine(line)
        }

        if let finalCue = parser.finish() {
            parsed.append(finalCue)
            pending.append(finalCue)
        }
        await flushPending(force: true)
        let fullContent = lines.joined(separator: "\n")
        let fullParsed = await Task.detached(priority: .utility) { () -> [VideoSubtitleCue] in
            SubtitleParser.parse(from: fullContent, format: format)
        }.value
        return SubtitleLoadResult(cues: fullParsed, response: httpResponse, usedCache: false)
    }
}

private struct SubtitleLoadResult {
    let cues: [VideoSubtitleCue]
    let response: HTTPURLResponse?
    let usedCache: Bool
}

private final class SubtitleCacheStore {
    static let shared = SubtitleCacheStore()

    fileprivate struct Metadata: Codable {
        let trackId: String
        let url: String
        let format: SubtitleFormat
        let etag: String?
        let lastModified: String?
        let updatedAt: TimeInterval
    }

    private let folderName = "SubtitleCache"

    func cacheKey(for track: VideoSubtitleTrack) -> String {
        let raw = "\(track.id)|\(track.url.absoluteString)"
        #if canImport(CryptoKit)
        let digest = SHA256.hash(data: Data(raw.utf8))
        return digest.map { String(format: "%02x", $0) }.joined()
        #else
        let encoded = Data(raw.utf8).base64EncodedString()
        return encoded
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "=", with: "")
        #endif
    }

    fileprivate func cachedEntry(for track: VideoSubtitleTrack) -> (metadata: Metadata, cues: [VideoSubtitleCue])? {
        guard let metadata = cachedMetadata(for: track) else { return nil }
        guard let cues = cachedCues(for: track) else { return nil }
        return (metadata, cues)
    }

    fileprivate func cachedMetadata(for track: VideoSubtitleTrack) -> Metadata? {
        guard let metaURL = metadataURL(for: track) else { return nil }
        guard let data = try? Data(contentsOf: metaURL) else { return nil }
        let decoder = JSONDecoder()
        guard let metadata = try? decoder.decode(Metadata.self, from: data) else { return nil }
        guard metadata.url == track.url.absoluteString else { return nil }
        guard metadata.format == track.format else { return nil }
        return metadata
    }

    func cachedCues(for track: VideoSubtitleTrack) -> [VideoSubtitleCue]? {
        guard let cuesURL = cuesURL(for: track) else { return nil }
        guard let data = try? Data(contentsOf: cuesURL) else { return nil }
        let decoder = JSONDecoder()
        return try? decoder.decode([VideoSubtitleCue].self, from: data)
    }

    func store(track: VideoSubtitleTrack, response: HTTPURLResponse?, cues: [VideoSubtitleCue]) {
        guard let folder = cacheFolder() else { return }
        let metadata = Metadata(
            trackId: track.id,
            url: track.url.absoluteString,
            format: track.format,
            etag: response?.value(forHTTPHeaderField: "ETag"),
            lastModified: response?.value(forHTTPHeaderField: "Last-Modified"),
            updatedAt: Date().timeIntervalSince1970
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        guard let metaData = try? encoder.encode(metadata) else { return }
        guard let cuesData = try? encoder.encode(cues) else { return }
        let metaURL = folder.appendingPathComponent("\(cacheKey(for: track)).meta.json")
        let cuesURL = folder.appendingPathComponent("\(cacheKey(for: track)).cues.json")
        try? metaData.write(to: metaURL, options: [.atomic])
        try? cuesData.write(to: cuesURL, options: [.atomic])
    }

    fileprivate func request(for track: VideoSubtitleTrack, metadata: Metadata?) -> URLRequest {
        var request = URLRequest(url: track.url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        if let etag = metadata?.etag, !etag.isEmpty {
            request.setValue(etag, forHTTPHeaderField: "If-None-Match")
        }
        if let lastModified = metadata?.lastModified, !lastModified.isEmpty {
            request.setValue(lastModified, forHTTPHeaderField: "If-Modified-Since")
        }
        return request
    }

    private func cacheFolder() -> URL? {
        let fileManager = FileManager.default
        guard let base = fileManager.urls(for: .cachesDirectory, in: .userDomainMask).first else { return nil }
        let folder = base.appendingPathComponent(folderName, isDirectory: true)
        if !fileManager.fileExists(atPath: folder.path) {
            try? fileManager.createDirectory(at: folder, withIntermediateDirectories: true)
        }
        return folder
    }

    private func metadataURL(for track: VideoSubtitleTrack) -> URL? {
        guard let folder = cacheFolder() else { return nil }
        return folder.appendingPathComponent("\(cacheKey(for: track)).meta.json")
    }

    private func cuesURL(for track: VideoSubtitleTrack) -> URL? {
        guard let folder = cacheFolder() else { return nil }
        return folder.appendingPathComponent("\(cacheKey(for: track)).cues.json")
    }
}
