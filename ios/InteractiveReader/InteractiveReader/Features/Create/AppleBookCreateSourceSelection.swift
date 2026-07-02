import Foundation

private enum AppleBookCreateSourceSelectionConstants {
    static let subtitleJobSourceFormats: Set<String> = ["ass", "srt", "vtt"]
    static let subtitleJobPreferredDefaultFormats: Set<String> = ["srt", "vtt"]
    static let youtubePlayableSubtitleFormats: Set<String> = ["ass", "srt", "vtt", "sub"]

    static let sourceModifiedDateFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    static let sourceModifiedDateFormatterWithFractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()
}

private func normalizedSourceText(_ value: String) -> String {
    value.trimmingCharacters(in: .whitespacesAndNewlines)
}

extension AppleBookCreatePresentation {
    static func pipelineEbookEntries(from files: PipelineFileBrowserResponse?) -> [PipelineFileEntry] {
        sortedPipelineEbookEntries(files?.ebooks.filter { isPipelineEbookEntry($0) } ?? [])
    }

    static func preferredPipelineEbook(from files: PipelineFileBrowserResponse?) -> PipelineFileEntry? {
        let ebooks = pipelineEbookEntries(from: files)
        guard !ebooks.isEmpty else {
            return nil
        }
        return ebooks.first
    }

    static func selectedPipelineEbook(
        sourcePath: String,
        files: PipelineFileBrowserResponse?
    ) -> PipelineFileEntry? {
        let trimmedPath = normalizedSourceText(sourcePath)
        guard !trimmedPath.isEmpty else {
            return nil
        }
        return pipelineEbookEntries(from: files).first { $0.path == trimmedPath }
    }

    private static func isPipelineEbookEntry(_ entry: PipelineFileEntry) -> Bool {
        let type = normalizedSourceText(entry.type).lowercased()
        guard type != "directory" else {
            return false
        }
        let path = normalizedSourceText(entry.path).lowercased()
        guard !path.isEmpty else {
            return false
        }
        let name = normalizedSourceText(entry.name).lowercased()
        if isEpubCandidate(name: name, path: path) {
            return true
        }
        return type == "file"
    }

    private static func isEpubCandidate(name: String, path: String) -> Bool {
        name.hasSuffix(".epub") || path.hasSuffix(".epub")
    }

    private static func sortedPipelineEbookEntries(_ entries: [PipelineFileEntry]) -> [PipelineFileEntry] {
        entries.sorted { left, right in
            let leftDate = parseSourceModifiedDate(left.modifiedAt)
            let rightDate = parseSourceModifiedDate(right.modifiedAt)
            if leftDate != rightDate {
                return leftDate > rightDate
            }
            return left.path.localizedStandardCompare(right.path) == .orderedAscending
        }
    }

    static func pipelineEbookPickerLabel(_ entry: PipelineFileEntry) -> String {
        let details = pickerMetadataParts(
            sizeBytes: entry.sizeBytes,
            modifiedAt: entry.modifiedAt
        )
        let title = normalizedSourceText(entry.name).isEmpty
            ? normalizedSourceText(entry.path)
            : entry.name
        let context = pickerPathContext(path: entry.path, title: title)
        let titleParts = [title, context].compactMap { value -> String? in
            let normalized = normalizedSourceText(value ?? "")
            return normalized.isEmpty ? nil : normalized
        }
        let labelTitle = titleParts.joined(separator: " · ")
        return details.isEmpty ? labelTitle : "\(labelTitle) · \(details.joined(separator: " · "))"
    }

    static func pipelineEbookDetailLabel(_ entry: PipelineFileEntry) -> String {
        var details = [String]()
        let path = normalizedSourceText(entry.path)
        if !path.isEmpty {
            details.append(path)
        }
        details.append(contentsOf: pickerMetadataParts(sizeBytes: entry.sizeBytes, modifiedAt: entry.modifiedAt))
        return details.joined(separator: " · ")
    }

    private static func pickerPathContext(path: String, title: String) -> String? {
        let normalizedPath = normalizedSourceText(path).replacingOccurrences(of: "\\", with: "/")
        guard !normalizedPath.isEmpty else {
            return nil
        }
        let normalizedTitle = normalizedSourceText(title)
        if normalizedPath == normalizedTitle {
            return nil
        }
        guard let slashIndex = normalizedPath.lastIndex(of: "/") else {
            return nil
        }
        let directory = String(normalizedPath[..<slashIndex])
        return directory.isEmpty ? nil : directory
    }

    static func subtitleJobSources(from response: SubtitleSourceListResponse?) -> [SubtitleSourceEntry] {
        response?.sources.filter {
            AppleBookCreateSourceSelectionConstants.subtitleJobSourceFormats.contains(normalizedSourceText($0.format).lowercased())
        } ?? []
    }

    static func preferredSubtitleSource(from response: SubtitleSourceListResponse?) -> SubtitleSourceEntry? {
        let candidates = subtitleJobSources(from: response)
        let preferred = candidates.filter {
            AppleBookCreateSourceSelectionConstants.subtitleJobPreferredDefaultFormats
                .contains(normalizedSourceText($0.format).lowercased())
        }
        let pool = preferred.isEmpty ? candidates : preferred
        return pool.sorted { left, right in
            let leftDate = parseSourceModifiedDate(left.modifiedAt)
            let rightDate = parseSourceModifiedDate(right.modifiedAt)
            if leftDate != rightDate {
                return leftDate > rightDate
            }
            return left.path.localizedStandardCompare(right.path) == .orderedAscending
        }.first
    }

    static func narrateSourceDefaults(
        selectedLocalFile: Bool,
        didEditSourcePath: Bool,
        sourcePath: String,
        sourceBaseOutput: String,
        didEditBaseOutput: Bool,
        files: PipelineFileBrowserResponse?
    ) -> AppleNarrateSourceDefaults? {
        guard
            !selectedLocalFile,
            !didEditSourcePath,
            normalizedSourceText(sourcePath).isEmpty,
            let entry = preferredPipelineEbook(from: files)
        else {
            return nil
        }

        let baseOutput = normalizedSourceText(sourceBaseOutput).isEmpty && !didEditBaseOutput
            ? deriveBaseOutputName(entry.name)
            : nil
        return AppleNarrateSourceDefaults(path: entry.path, baseOutput: baseOutput)
    }

    static func subtitleSourceDefaults(
        selectedLocalFile: Bool,
        didEditSourcePath: Bool,
        sourcePath: String,
        sources: SubtitleSourceListResponse?
    ) -> AppleSubtitleSourceDefaults? {
        guard
            !selectedLocalFile,
            !didEditSourcePath,
            normalizedSourceText(sourcePath).isEmpty,
            let entry = preferredSubtitleSource(from: sources)
        else {
            return nil
        }

        return AppleSubtitleSourceDefaults(path: entry.path, metadataLookupSourceName: entry.name)
    }

    static func playableYoutubeSubtitles(for video: YoutubeNasVideoEntry?) -> [YoutubeNasSubtitleEntry] {
        video?.subtitles.filter {
            AppleBookCreateSourceSelectionConstants.youtubePlayableSubtitleFormats.contains(normalizedSourceText($0.format).lowercased())
        } ?? []
    }

    static func preferredYoutubeSubtitle(for video: YoutubeNasVideoEntry?) -> YoutubeNasSubtitleEntry? {
        let candidates = playableYoutubeSubtitles(for: video)
        guard !candidates.isEmpty else {
            return nil
        }
        return candidates.first { subtitle in
            normalizedSourceText(subtitle.language ?? "").lowercased().hasPrefix("en")
        } ?? candidates[0]
    }

    static func extractableYoutubeInlineSubtitleStreams(
        from streams: [YoutubeInlineSubtitleStream]
    ) -> [YoutubeInlineSubtitleStream] {
        streams.filter(\.canExtract)
    }

    static func defaultYoutubeInlineSubtitleLanguages(
        from streams: [YoutubeInlineSubtitleStream]
    ) -> [String] {
        let extractable = extractableYoutubeInlineSubtitleStreams(from: streams)
        guard !extractable.isEmpty else {
            return []
        }
        if let english = extractable.first(where: { stream in
            normalizedSourceText(stream.language ?? "").lowercased().hasPrefix("en")
        })?.language?.nonEmptyValue {
            return [english]
        }
        if extractable.count == 1, let language = extractable[0].language?.nonEmptyValue {
            return [language]
        }
        return []
    }

    static func normalizedYoutubeInlineSubtitleLanguages(_ value: String) -> [String] {
        value
            .split { character in
                character == "," || character == "\n" || character == "\t"
            }
            .map { normalizedSourceText(String($0)) }
            .filter { !$0.isEmpty }
            .reduce(into: [String]()) { result, language in
                if !result.contains(where: { $0.caseInsensitiveCompare(language) == .orderedSame }) {
                    result.append(language)
                }
            }
    }

    static func youtubeInlineSubtitleStreamLabel(_ stream: YoutubeInlineSubtitleStream) -> String {
        let language = normalizedSourceText(stream.language ?? "")
        let codec = normalizedSourceText(stream.codec ?? "")
        let title = normalizedSourceText(stream.title ?? "")
        let details = [language, codec, title]
            .filter { !$0.isEmpty }
            .joined(separator: " · ")
        let prefix = stream.canExtract ? "Text" : "Image"
        return details.isEmpty
            ? "\(prefix) subtitle stream \(stream.index)"
            : "\(prefix) subtitle stream \(stream.index) · \(details)"
    }

    static func youtubeSubtitleExtractionStatus(
        extractedCount: Int,
        videoFilename: String
    ) -> String {
        guard extractedCount > 0 else {
            return "No subtitle streams found to extract."
        }
        let noun = extractedCount == 1 ? "track" : "tracks"
        return "Extracted \(extractedCount) subtitle \(noun) from \(videoFilename)."
    }

    static func preferredYoutubeSelection(from library: YoutubeNasLibraryResponse?) -> AppleYoutubeSourceSelection? {
        let videos = sortedYoutubeVideosForDefaultSelection(library?.videos ?? [])
        guard !videos.isEmpty else {
            return nil
        }
        let video = videos.first { !playableYoutubeSubtitles(for: $0).isEmpty } ?? videos[0]
        return AppleYoutubeSourceSelection(video: video, subtitle: preferredYoutubeSubtitle(for: video))
    }

    static func youtubeSelection(
        from library: YoutubeNasLibraryResponse?,
        storedVideoPath: String?,
        storedSubtitlePath: String?
    ) -> AppleYoutubeSourceSelection? {
        guard let videos = library?.videos, !videos.isEmpty else {
            return nil
        }

        let requestedVideoPath = storedVideoPath?.nonEmptyValue
        let selectedVideo = videos.first { $0.path == requestedVideoPath }
            ?? preferredYoutubeSelection(from: library)?.video
            ?? videos[0]
        let subtitleCandidates = playableYoutubeSubtitles(for: selectedVideo)
        let requestedSubtitlePath = storedSubtitlePath?.nonEmptyValue
        let storedSubtitle = requestedVideoPath == selectedVideo.path
            ? subtitleCandidates.first { $0.path == requestedSubtitlePath }
            : nil
        let subtitle = storedSubtitle ?? preferredYoutubeSubtitle(for: selectedVideo)

        return AppleYoutubeSourceSelection(video: selectedVideo, subtitle: subtitle)
    }

    static func youtubeSourceDefaults(
        library: YoutubeNasLibraryResponse?,
        currentStorageScope: String,
        nextStorageScope: String,
        didEditVideoPath: Bool,
        currentVideoPath: String,
        didEditSubtitlePath: Bool,
        currentSubtitlePath: String,
        storedVideoPath: String?,
        storedSubtitlePath: String?
    ) -> AppleYoutubeSourceDefaults? {
        guard let selection = youtubeSelection(
            from: library,
            storedVideoPath: storedVideoPath,
            storedSubtitlePath: storedSubtitlePath
        ) else {
            return nil
        }

        let scopeChanged = currentStorageScope != nextStorageScope
        let videoPath = !didEditVideoPath && (normalizedSourceText(currentVideoPath).isEmpty || scopeChanged)
            ? selection.video.path
            : nil
        let subtitlePath = !didEditSubtitlePath && (normalizedSourceText(currentSubtitlePath).isEmpty || scopeChanged)
            ? selection.subtitle?.path ?? ""
            : nil
        return AppleYoutubeSourceDefaults(
            nextStorageScope: nextStorageScope,
            videoPath: videoPath,
            subtitlePath: subtitlePath
        )
    }

    static func youtubeSubtitleLanguage(
        from library: YoutubeNasLibraryResponse?,
        videoPath: String,
        subtitlePath: String
    ) -> String? {
        let normalizedVideoPath = normalizedSourceText(videoPath)
        let normalizedSubtitlePath = normalizedSourceText(subtitlePath)
        guard !normalizedVideoPath.isEmpty, !normalizedSubtitlePath.isEmpty else {
            return nil
        }
        guard let video = library?.videos.first(where: { $0.path == normalizedVideoPath }) else {
            return nil
        }
        return playableYoutubeSubtitles(for: video)
            .first { $0.path == normalizedSubtitlePath }?
            .language?
            .nonEmptyValue
    }

    static func youtubeLibraryCacheKey(baseKey: String, baseDir: String) -> String {
        let normalizedBaseDir = normalizedSourceText(baseDir)
        guard !normalizedBaseDir.isEmpty else {
            return baseKey
        }
        return "\(baseKey)|youtubeBaseDir=\(normalizedBaseDir)"
    }

    static func subtitleShowOriginalPreferenceKey(baseKey: String) -> String {
        "ebookTools.appleCreate.subtitles.showOriginal.\(baseKey)"
    }

    private static func sortedYoutubeVideosForDefaultSelection(
        _ videos: [YoutubeNasVideoEntry]
    ) -> [YoutubeNasVideoEntry] {
        videos.sorted { left, right in
            let leftDate = parseSourceModifiedDate(left.modifiedAt)
            let rightDate = parseSourceModifiedDate(right.modifiedAt)
            if leftDate != rightDate {
                return leftDate > rightDate
            }
            return left.path.localizedStandardCompare(right.path) == .orderedAscending
        }
    }

    private static func pickerMetadataParts(sizeBytes: Int?, modifiedAt: String?) -> [String] {
        [
            formatPickerSize(sizeBytes),
            formatPickerModifiedDate(modifiedAt)
        ].compactMap(\.self)
    }

    private static func formatPickerSize(_ bytes: Int?) -> String? {
        guard let bytes, bytes > 0 else { return nil }
        let units: [(threshold: Double, label: String)] = [
            (1_073_741_824, "GB"),
            (1_048_576, "MB"),
            (1_024, "KB"),
        ]
        guard let unit = units.first(where: { Double(bytes) >= $0.threshold }) else {
            return "\(bytes) B"
        }
        let value = Double(bytes) / unit.threshold
        let precision = value >= 10 ? "%.0f %@" : "%.1f %@"
        return String(
            format: precision,
            locale: Locale(identifier: "en_US_POSIX"),
            value,
            unit.label
        )
    }

    private static func formatPickerModifiedDate(_ value: String?) -> String? {
        guard let value = value?.nonEmptyValue else { return nil }
        let date = parseSourceModifiedDate(value)
        if date != .distantPast {
            return String(value.prefix(10))
        }
        let prefix = value.prefix(10)
        return prefix.isEmpty ? nil : String(prefix)
    }

    private static func parseSourceModifiedDate(_ value: String?) -> Date {
        guard let value = value?.nonEmptyValue else { return .distantPast }
        return AppleBookCreateSourceSelectionConstants.sourceModifiedDateFormatterWithFractional.date(from: value)
            ?? AppleBookCreateSourceSelectionConstants.sourceModifiedDateFormatter.date(from: value)
            ?? .distantPast
    }
}
