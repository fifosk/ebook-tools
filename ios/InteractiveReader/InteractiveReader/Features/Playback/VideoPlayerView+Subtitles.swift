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

    func currentSubtitleDisplay() -> VideoSubtitleDisplay? {
        VideoSubtitleDisplayBuilder.build(cues: cues, time: coordinator.currentTime, visibility: subtitleVisibility)
    }

    func syncSubtitleSelectionIfNeeded(force: Bool = false) {
        guard !coordinator.isPlaying else { return }
        guard let display = currentSubtitleDisplay() else {
            subtitleSelection = nil
            subtitleSelectionRange = nil
            subtitleActiveCueID = nil
            return
        }
        if isManualSubtitleNavigation && !force {
            if subtitleActiveCueID == display.cue.id {
                return
            }
            isManualSubtitleNavigation = false
        }
        if force || subtitleActiveCueID != display.cue.id {
            subtitleActiveCueID = display.cue.id
            subtitleSelection = defaultSubtitleSelection(in: display)
            subtitleSelectionRange = nil
            return
        }
        if let normalized = normalizedSelection(from: subtitleSelection, in: display),
           normalized != subtitleSelection {
            subtitleSelection = normalized
            subtitleSelectionRange = nil
            return
        }
        if subtitleSelection == nil {
            subtitleSelection = defaultSubtitleSelection(in: display)
            subtitleSelectionRange = nil
        }
    }

    func normalizedSelection(
        from selection: VideoSubtitleWordSelection?,
        in display: VideoSubtitleDisplay
    ) -> VideoSubtitleWordSelection? {
        guard let selection else { return nil }
        let line = lineForSelection(selection, in: display)
        guard let line, !line.tokens.isEmpty else { return nil }
        let tokenIndex = min(max(selection.tokenIndex, 0), line.tokens.count - 1)
        return VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: tokenIndex
        )
    }

    func defaultSubtitleSelection(in display: VideoSubtitleDisplay) -> VideoSubtitleWordSelection? {
        let preferredLine = display.lines.first(where: { $0.kind == .translation })
            ?? display.lines.first(where: { $0.kind == .unknown })
            ?? display.lines.first
        guard let line = preferredLine, !line.tokens.isEmpty else { return nil }
        let tokenIndex = currentTokenIndex(
            for: line,
            cueStart: display.highlightStart,
            cueEnd: display.highlightEnd,
            time: coordinator.currentTime
        )
        let resolved = nearestLookupTokenIndex(in: line.tokens, startingAt: tokenIndex) ?? tokenIndex
        return VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: resolved
        )
    }

    func currentTokenIndex(
        for line: VideoSubtitleDisplayLine,
        cueStart: Double,
        cueEnd: Double,
        time: Double
    ) -> Int {
        guard !line.tokens.isEmpty else { return 0 }
        if let styles = line.tokenStyles {
            if let current = styles.firstIndex(where: { $0 == .highlightCurrent }) {
                return current
            }
            if let lastPrior = styles.lastIndex(where: { $0 == .highlightPrior }) {
                return lastPrior
            }
        }
        let clamped = min(max(time, cueStart), cueEnd)
        let epsilon = 1e-3
        if clamped >= cueEnd - epsilon {
            return line.tokens.count - 1
        }
        let revealed = line.revealTimes.filter { $0 <= clamped + epsilon }.count
        if revealed > 0 {
            return min(revealed - 1, line.tokens.count - 1)
        }
        if clamped >= cueStart - epsilon {
            return 0
        }
        return 0
    }

    func lineForSelection(
        _ selection: VideoSubtitleWordSelection,
        in display: VideoSubtitleDisplay
    ) -> VideoSubtitleDisplayLine? {
        if display.lines.indices.contains(selection.lineIndex) {
            let line = display.lines[selection.lineIndex]
            if line.kind == selection.lineKind {
                return line
            }
        }
        if let line = display.lines.first(where: { $0.kind == selection.lineKind }) {
            return line
        }
        if display.lines.indices.contains(selection.lineIndex) {
            return display.lines[selection.lineIndex]
        }
        return nil
    }

    func handleSubtitleWordNavigation(_ delta: Int) {
        guard !coordinator.isPlaying else { return }
        guard let display = currentSubtitleDisplay() else { return }
        let selection = normalizedSelection(from: subtitleSelection, in: display)
            ?? defaultSubtitleSelection(in: display)
        guard let selection, let line = lineForSelection(selection, in: display) else { return }
        guard !line.tokens.isEmpty else { return }
        let direction = delta >= 0 ? 1 : -1
        let startIndex = selection.tokenIndex + direction
        guard let nextIndex = wrappedLookupTokenIndex(
            in: line.tokens,
            startingAt: startIndex,
            direction: direction
        ) else { return }
        isManualSubtitleNavigation = true
        subtitleSelectionRange = nil
        subtitleSelection = VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: nextIndex
        )
        scheduleAutoSubtitleLookup()
    }

    func handleSubtitleWordRangeSelection(_ delta: Int) {
        guard !coordinator.isPlaying else { return }
        guard let display = currentSubtitleDisplay() else { return }
        let selection = normalizedSelection(from: subtitleSelection, in: display)
            ?? defaultSubtitleSelection(in: display)
        guard let selection, let line = lineForSelection(selection, in: display) else { return }
        guard !line.tokens.isEmpty else { return }
        let direction = delta >= 0 ? 1 : -1
        let anchorIndex: Int
        let focusIndex: Int
        if let range = subtitleSelectionRange,
           range.lineKind == line.kind,
           range.lineIndex == line.index {
            anchorIndex = range.anchorIndex
            focusIndex = range.focusIndex
        } else {
            anchorIndex = selection.tokenIndex
            focusIndex = selection.tokenIndex
        }
        let nextIndex = max(0, min(focusIndex + direction, line.tokens.count - 1))
        subtitleSelectionRange = VideoSubtitleWordSelectionRange(
            lineKind: line.kind,
            lineIndex: line.index,
            anchorIndex: anchorIndex,
            focusIndex: nextIndex
        )
        subtitleSelection = VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: nextIndex
        )
        isManualSubtitleNavigation = true
    }

    func handleSubtitleTrackNavigation(_ delta: Int) -> Bool {
        guard !coordinator.isPlaying else { return false }
        guard let display = currentSubtitleDisplay() else { return false }
        guard !display.lines.isEmpty else { return false }
        let selection = normalizedSelection(from: subtitleSelection, in: display)
            ?? defaultSubtitleSelection(in: display)
        let currentLine = selection.flatMap { lineForSelection($0, in: display) } ?? display.lines[0]
        let step = delta >= 0 ? 1 : -1
        let currentIndex = display.lines.indices.contains(currentLine.index)
            ? currentLine.index
            : (display.lines.firstIndex(where: { $0.id == currentLine.id }) ?? 0)
        let nextIndex = currentIndex + step
        guard display.lines.indices.contains(nextIndex) else { return false }
        let line = display.lines[nextIndex]
        let baseTokenIndex = selection?.tokenIndex ?? currentTokenIndex(
            for: currentLine,
            cueStart: display.highlightStart,
            cueEnd: display.highlightEnd,
            time: coordinator.currentTime
        )
        let clampedIndex = max(0, min(baseTokenIndex, max(0, line.tokens.count - 1)))
        let resolvedIndex: Int = {
            guard line.tokens.indices.contains(clampedIndex) else { return clampedIndex }
            if sanitizeLookupQuery(line.tokens[clampedIndex]) != nil {
                return clampedIndex
            }
            return nearestLookupTokenIndex(in: line.tokens, startingAt: clampedIndex) ?? clampedIndex
        }()
        isManualSubtitleNavigation = true
        subtitleSelectionRange = nil
        subtitleSelection = VideoSubtitleWordSelection(
            lineKind: line.kind,
            lineIndex: line.index,
            tokenIndex: resolvedIndex
        )
        scheduleAutoSubtitleLookup()
        return true
    }

    func subtitleLineKinds(in display: VideoSubtitleDisplay) -> [VideoSubtitleLineKind] {
        var seen = Set<VideoSubtitleLineKind>()
        var ordered: [VideoSubtitleLineKind] = []
        for line in display.lines {
            if !seen.contains(line.kind) {
                seen.insert(line.kind)
                ordered.append(line.kind)
            }
        }
        return ordered
    }

    func handleSentenceSkip(_ delta: Int) {
        let groups = subtitleSentenceGroups()
        if groups.isEmpty {
            coordinator.skip(by: delta < 0 ? -15 : 15)
            return
        }
        let time = coordinator.currentTime
        let epsilon = 1e-3
        let currentIndex = groups.firstIndex { time >= $0.start - epsilon && time <= $0.end + epsilon }
            ?? groups.lastIndex { time >= $0.start - epsilon }
            ?? 0
        let nextIndex = max(0, min(currentIndex + (delta < 0 ? -1 : 1), groups.count - 1))
        let targetTime = groups[nextIndex].start

        #if os(tvOS)
        // On tvOS, mute and pause during seek to prevent audio bleed from the old position
        let wasPlaying = coordinator.isPlaying
        let player = coordinator.playerInstance()
        let savedVolume = player?.volume ?? 1.0
        player?.volume = 0
        if wasPlaying {
            coordinator.pause()
        }
        coordinator.seek(to: targetTime) { _ in
            // Restore volume after seek completes
            player?.volume = savedVolume
            if wasPlaying {
                coordinator.play()
            }
        }
        #else
        coordinator.seek(to: targetTime)
        #endif
    }

    func subtitleSentenceGroups() -> [SubtitleSentenceGroup] {
        guard !cues.isEmpty else { return [] }
        let sorted = cues.sorted { lhs, rhs in
            if lhs.start == rhs.start {
                return lhs.end < rhs.end
            }
            return lhs.start < rhs.start
        }
        var groups: [SubtitleSentenceGroup] = []
        let maxGap = 0.06
        for cue in sorted {
            guard !cue.text.isEmpty else { continue }
            if let last = groups.last {
                let gap = cue.start - last.end
                if cue.text == last.text && gap <= maxGap {
                    groups[groups.count - 1] = SubtitleSentenceGroup(
                        start: last.start,
                        end: max(last.end, cue.end),
                        text: last.text
                    )
                    continue
                }
            }
            groups.append(SubtitleSentenceGroup(start: cue.start, end: cue.end, text: cue.text))
        }
        return groups
    }

    func toggleSubtitleVisibility(_ kind: VideoSubtitleLineKind) {
        switch kind {
        case .original:
            subtitleVisibility.showOriginal.toggle()
        case .transliteration:
            subtitleVisibility.showTransliteration.toggle()
        case .translation:
            subtitleVisibility.showTranslation.toggle()
        case .unknown:
            subtitleVisibility.showTranslation.toggle()
        }
    }

    func handleTransliterationToggle() {
        guard hasTransliterationLines else { return }
        toggleSubtitleVisibility(.transliteration)
        handleUserInteraction()
    }

    var hasTransliterationLines: Bool {
        cues.contains { cue in
            cue.lines.contains { $0.kind == .transliteration }
        }
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

struct SubtitleSentenceGroup {
    let start: Double
    let end: Double
    let text: String
}
