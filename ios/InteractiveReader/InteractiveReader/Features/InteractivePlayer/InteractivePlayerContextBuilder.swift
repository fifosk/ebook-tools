import Foundation

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
            range = "Sentences \(start)-\(end)"
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
            let filtered = tokens.filter { !$0.isEmpty }
            if !filtered.isEmpty {
                return filtered
            }
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
