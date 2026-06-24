import Foundation

enum AppleBookCreateStorageKeys {
    static func loadScope(apiBaseURL: URL?, userID: String?, userRole: String?) -> String {
        guard let apiBaseURL else { return "missing" }
        return [
            apiBaseURL.absoluteString,
            userID ?? "",
            userRole ?? ""
        ].joined(separator: "|")
    }

    static func youtubeSelection(baseKey: String, baseDir: String, field: String) -> String {
        _ = baseDir
        return "ebookTools.appleCreate.youtubeDub.\(field).\(baseKey)"
    }

    static func subtitleShowOriginal(baseKey: String) -> String {
        AppleBookCreatePresentation.subtitleShowOriginalPreferenceKey(baseKey: baseKey)
    }

    static func youtubeBaseDir(baseKey: String) -> String {
        "ebookTools.appleCreate.youtubeDub.baseDir.\(baseKey)"
    }

    static func youtubeLibraryLoad(baseKey: String, baseDir: String) -> String {
        AppleBookCreatePresentation.youtubeLibraryCacheKey(baseKey: baseKey, baseDir: baseDir)
    }

    static func languagePreferences(baseKey: String) -> String {
        "ebookTools.appleCreate.bookJobDefaults.v1.\(baseKey)"
    }
}
