import Foundation

enum AppleBookCreateMetadataSources {
    static func youtubeTvSourceName(subtitlePath: String, videoPath: String) -> String {
        trimmed(subtitlePath).nonEmptyValue ?? trimmed(videoPath)
    }

    static func youtubeVideoSourceName(videoPath: String) -> String {
        trimmed(videoPath)
    }

    static func subtitleSourceName(
        selectedFileName: String?,
        selectedPath: String,
        sources: [SubtitleSourceEntry]
    ) -> String {
        if let fileName = selectedFileName?.nonEmptyValue {
            return fileName
        }
        let normalizedPath = trimmed(selectedPath)
        if let entryName = sources.first(where: { $0.path == normalizedPath })?.name.nonEmptyValue {
            return entryName
        }
        guard !normalizedPath.isEmpty else {
            return ""
        }
        return URL(fileURLWithPath: normalizedPath).lastPathComponent
    }

    private static func trimmed(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
