import Foundation

extension InteractivePlayerViewModel {
    @MainActor
    func updateChapterIndex(from metadata: [String: JSONValue]?) async {
        chapterEntries = []
        guard let metadata else { return }
        let metadataRoot = extractMediaMetadata(from: metadata) ?? metadata
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

    func extractMediaMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        if let direct = objectValue(metadata["media_metadata"] ?? metadata["book_metadata"]) {
            return direct
        }
        if let result = objectValue(metadata["result"]),
           let nested = objectValue(result["media_metadata"] ?? result["book_metadata"]) {
            return nested
        }
        return nil
    }

    func parseContentIndex(from value: JSONValue) -> [ChapterNavigationEntry]? {
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

    func metadataValue(_ metadata: [String: JSONValue], keys: [String]) -> JSONValue? {
        for key in keys {
            if let value = metadata[key] {
                return value
            }
        }
        return nil
    }

    func metadataString(_ metadata: [String: JSONValue], keys: [String]) -> String? {
        for key in keys {
            if let value = metadata[key], let string = stringValue(value) {
                return string
            }
        }
        return nil
    }

    func objectValue(_ value: JSONValue?) -> [String: JSONValue]? {
        guard case let .object(object) = value else { return nil }
        return object
    }

    func arrayValue(_ value: JSONValue?) -> [JSONValue]? {
        guard case let .array(array) = value else { return nil }
        return array
    }

    func stringValue(_ value: JSONValue?) -> String? {
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

    func intValue(_ value: JSONValue?) -> Int? {
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
}
