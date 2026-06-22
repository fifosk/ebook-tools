import Foundation

enum JobRowCoverParsing {
    static func youtubeThumbnailFallback(from sources: [String?]) -> String? {
        for source in sources {
            guard let source, let id = youtubeVideoID(from: source) else { continue }
            return "https://i.ytimg.com/vi/\(id)/hqdefault.jpg"
        }
        return nil
    }

    static func normalizeCoverCandidate(_ candidate: String) -> String {
        if candidate.hasPrefix("//") {
            return "https:" + candidate
        }
        let lower = candidate.lowercased()
        if lower.hasPrefix("http://"),
           (lower.contains("youtube.com") || lower.contains("ytimg.com") || lower.contains("youtu.be")) {
            return "https://" + candidate.dropFirst("http://".count)
        }
        return candidate
    }

    static func youtubeVideoID(from value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if let url = URL(string: trimmed), let id = youtubeVideoID(from: url) {
            return id
        }
        if let id = bracketedYoutubeID(from: trimmed) {
            return id
        }
        if let id = idBeforeToken(in: trimmed, token: "_yt") {
            return id
        }
        return nil
    }

    private static func youtubeVideoID(from url: URL) -> String? {
        let host = url.host?.lowercased() ?? ""
        let pathComponents = url.path.split(separator: "/").map(String.init)
        if host.contains("youtu.be"), let first = pathComponents.first, isValidYoutubeID(first) {
            return first
        }
        if host.contains("youtube.com") {
            if url.path.contains("/watch") {
                let components = URLComponents(url: url, resolvingAgainstBaseURL: false)
                let id = components?.queryItems?.first(where: { $0.name == "v" })?.value
                if let id, isValidYoutubeID(id) {
                    return id
                }
            }
            if let shortsIndex = pathComponents.firstIndex(of: "shorts"),
               pathComponents.indices.contains(shortsIndex + 1) {
                let id = pathComponents[shortsIndex + 1]
                if isValidYoutubeID(id) {
                    return id
                }
            }
            if let embedIndex = pathComponents.firstIndex(of: "embed"),
               pathComponents.indices.contains(embedIndex + 1) {
                let id = pathComponents[embedIndex + 1]
                if isValidYoutubeID(id) {
                    return id
                }
            }
        }
        return nil
    }

    private static func bracketedYoutubeID(from value: String) -> String? {
        var searchRange = value.startIndex..<value.endIndex
        while let open = value.range(of: "[", options: [], range: searchRange)?.lowerBound {
            let afterOpen = value.index(after: open)
            guard let closeRange = value.range(of: "]", options: [], range: afterOpen..<value.endIndex) else {
                break
            }
            let candidate = String(value[afterOpen..<closeRange.lowerBound])
            let suffix = value[closeRange.upperBound...].lowercased()
            if isValidYoutubeID(candidate),
               suffix.hasPrefix("_yt") || suffix.hasPrefix(".yt") || suffix.hasPrefix("-yt") || suffix.contains("youtube") {
                return candidate
            }
            searchRange = closeRange.upperBound..<value.endIndex
        }
        return nil
    }

    private static func idBeforeToken(in value: String, token: String) -> String? {
        let lowered = value.lowercased()
        guard let range = lowered.range(of: token) else { return nil }
        let endIndex = range.lowerBound
        let prefix = value[..<endIndex]
        let validChars = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")
        var buffer = ""
        for character in prefix.reversed() {
            guard let scalar = character.unicodeScalars.first, validChars.contains(scalar) else { break }
            buffer.append(character)
            if buffer.count >= 11 {
                break
            }
        }
        let reversed = String(buffer.reversed())
        return isValidYoutubeID(reversed) ? reversed : nil
    }

    private static func isValidYoutubeID(_ value: String) -> Bool {
        guard value.count == 11 else { return false }
        let validChars = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")
        return value.unicodeScalars.allSatisfy { validChars.contains($0) }
    }
}
