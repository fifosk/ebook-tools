import Foundation

enum MediaURLOrigin {
    case library(apiBaseURL: URL, accessToken: String?)
    case storage(apiBaseURL: URL, resolver: StorageResolver, accessToken: String?)
}

struct MediaURLResolver {
    let origin: MediaURLOrigin

    func resolveAudioURL(jobId: String, track: AudioTrackMetadata) -> URL? {
        print("[MediaURLResolver] resolveAudioURL: path=\(track.path ?? "nil"), url=\(track.url ?? "nil"), origin=\(originDescription)")
        switch origin {
        case .storage:
            if let path = track.path, isStorageRelativePath(path), let url = resolveURL(from: path, jobId: jobId) {
                print("[MediaURLResolver] Resolved via storage relative path: \(url)")
                return url
            }
            if let urlString = track.url, let url = resolveURL(from: urlString, jobId: jobId) {
                print("[MediaURLResolver] Resolved via url string: \(url)")
                return url
            }
            if let path = track.path, let url = resolveURL(from: path, jobId: jobId) {
                print("[MediaURLResolver] Resolved via path fallback: \(url)")
                return url
            }
            print("[MediaURLResolver] Failed to resolve audio URL")
            return nil
        case .library:
            if let urlString = track.url, let url = resolveURL(from: urlString, jobId: jobId) {
                print("[MediaURLResolver] Resolved via library url: \(url)")
                return url
            }
            if let path = track.path {
                let url = resolveURL(from: path, jobId: jobId)
                print("[MediaURLResolver] Resolved via library path: \(url?.absoluteString ?? "nil")")
                return url
            }
            print("[MediaURLResolver] Failed to resolve library audio URL")
            return nil
        }
    }

    private var originDescription: String {
        switch origin {
        case .storage(let apiBaseURL, let resolver, _):
            return "storage(api=\(apiBaseURL.absoluteString), base=\(resolver.baseURL.absoluteString))"
        case .library(let apiBaseURL, _):
            return "library(api=\(apiBaseURL.absoluteString))"
        }
    }

    func resolveFileURL(jobId: String, file: PipelineMediaFile) -> URL? {
        switch origin {
        case .storage:
            if let relative = file.relativePath, let url = resolveURL(from: relative, jobId: jobId) {
                return url
            }
            if let path = file.path, isStorageRelativePath(path), let url = resolveURL(from: path, jobId: jobId) {
                return url
            }
            if let urlString = file.url, let url = resolveURL(from: urlString, jobId: jobId) {
                return url
            }
            if let path = file.path, let url = resolveURL(from: path, jobId: jobId) {
                return url
            }
            return nil
        case .library:
            if let urlString = file.url, let url = resolveURL(from: urlString, jobId: jobId) {
                return url
            }
            if let relative = file.relativePath, let url = resolveURL(from: relative, jobId: jobId) {
                return url
            }
            if let path = file.path, let url = resolveURL(from: path, jobId: jobId) {
                return url
            }
            return nil
        }
    }

    func resolvePath(jobId: String, relativePath: String) -> URL? {
        resolveURL(from: relativePath, jobId: jobId)
    }

    private func resolveURL(from rawValue: String, jobId: String) -> URL? {
        let trimmed = rawValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }

        if let url = URL(string: trimmed), url.scheme != nil {
            switch origin {
            case let .library(apiBaseURL, accessToken):
                if let relative = extractLibraryRelativePath(from: url.path) {
                    return buildLibraryMediaURL(jobId: jobId, relativePath: relative, apiBaseURL: apiBaseURL, accessToken: accessToken)
                }
                return appendAccessToken(url, accessToken: accessToken)
            case let .storage(_, resolver, _):
                if resolver.baseURL.isFileURL,
                   let relative = extractStorageRelativePath(from: url.path, jobId: jobId)
                    ?? extractLibraryRelativePath(from: url.path),
                   let localURL = resolver.url(jobId: jobId, filePath: relative) {
                    return localURL
                }
                return applyAccessToken(to: url)
            }
        }

        switch origin {
        case let .library(apiBaseURL, accessToken):
            let url = resolveLibraryURL(jobId: jobId, rawValue: trimmed, apiBaseURL: apiBaseURL, accessToken: accessToken)
            if let url {
                return appendAccessToken(url, accessToken: accessToken)
            }
            return nil
        case let .storage(apiBaseURL, resolver, accessToken):
            if trimmed.hasPrefix("/api/") || trimmed.hasPrefix("/storage/") {
                if resolver.baseURL.isFileURL,
                   let relative = extractStorageRelativePath(from: trimmed, jobId: jobId)
                    ?? extractLibraryRelativePath(from: trimmed),
                   let localURL = resolver.url(jobId: jobId, filePath: relative) {
                    return localURL
                }
                if let url = buildURL(from: apiBaseURL, path: trimmed) {
                    return appendAccessToken(url, accessToken: accessToken)
                }
            }
            let relative = extractLibraryRelativePath(from: trimmed)
                ?? (trimmed.hasPrefix("/") ? trimmed.trimmingCharacters(in: CharacterSet(charactersIn: "/")) : trimmed)
            if let url = resolver.url(jobId: jobId, filePath: relative) {
                return appendAccessToken(url, accessToken: accessToken)
            }
            return nil
        }
    }

    private func resolveLibraryURL(jobId: String, rawValue: String, apiBaseURL: URL, accessToken: String?) -> URL? {
        if rawValue.hasPrefix("/api/library/") {
            return buildURL(from: apiBaseURL, path: rawValue)
        }
        if rawValue.hasPrefix("/storage/") || rawValue.hasPrefix("/api/") {
            if let relative = extractLibraryRelativePath(from: rawValue) {
                return buildLibraryMediaURL(jobId: jobId, relativePath: relative, apiBaseURL: apiBaseURL, accessToken: accessToken)
            }
            return buildURL(from: apiBaseURL, path: rawValue)
        }
        let encodedJobId = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let candidate = rawValue.replacingOccurrences(of: "\\", with: "/")
        if let relative = extractLibraryRelativePath(from: candidate) {
            return buildLibraryMediaURL(jobId: jobId, relativePath: relative, apiBaseURL: apiBaseURL, accessToken: accessToken)
        }
        let normalised = candidate.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        if normalised.isEmpty {
            return nil
        }
        let encodedPath = normalised
            .split(separator: "/")
            .map { $0.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? String($0) }
            .joined(separator: "/")
        let path = "/api/library/media/\(encodedJobId)/file/\(encodedPath)"
        return buildURL(from: apiBaseURL, path: path)
    }

    private func buildLibraryMediaURL(jobId: String, relativePath: String, apiBaseURL: URL, accessToken: String?) -> URL? {
        let encodedJobId = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let normalised = relativePath.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let encodedPath = normalised
            .split(separator: "/")
            .map { $0.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? String($0) }
            .joined(separator: "/")
        let path = "/api/library/media/\(encodedJobId)/file/\(encodedPath)"
        if let url = buildURL(from: apiBaseURL, path: path) {
            return appendAccessToken(url, accessToken: accessToken)
        }
        return nil
    }

    private func extractLibraryRelativePath(from rawValue: String) -> String? {
        let normalised = rawValue.replacingOccurrences(of: "\\", with: "/")
        if let range = normalised.range(of: "/api/library/media/"),
           let fileRange = normalised.range(of: "/file/", range: range.upperBound..<normalised.endIndex) {
            return String(normalised[fileRange.upperBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        }
        if let range = normalised.range(of: "/media/") {
            return String(normalised[range.lowerBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        }
        if let range = normalised.range(of: "/metadata/") {
            return String(normalised[range.lowerBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        }
        return nil
    }

    private func extractStorageRelativePath(from rawValue: String, jobId: String) -> String? {
        let normalised = rawValue.replacingOccurrences(of: "\\", with: "/")
        let encodedJob = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let candidates = [jobId, encodedJob]
        for candidate in candidates {
            if let range = normalised.range(of: "/storage/jobs/\(candidate)/") {
                return String(normalised[range.upperBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            }
        }
        return nil
    }

    private func applyAccessToken(to url: URL) -> URL {
        switch origin {
        case let .library(_, accessToken):
            return appendAccessToken(url, accessToken: accessToken)
        case let .storage(_, _, accessToken):
            return appendAccessToken(url, accessToken: accessToken)
        }
    }

    private func appendAccessToken(_ url: URL, accessToken: String?) -> URL {
        guard let token = accessToken, !token.isEmpty else {
            return url
        }
        guard let scheme = url.scheme?.lowercased(), scheme == "http" || scheme == "https" else {
            return url
        }
        guard var components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
            return url
        }
        var items = components.queryItems ?? []
        if items.contains(where: { $0.name == "access_token" }) {
            return url
        }
        items.append(URLQueryItem(name: "access_token", value: token))
        components.queryItems = items
        return components.url ?? url
    }

    private func buildURL(from base: URL, path: String) -> URL? {
        var components = URLComponents(url: base, resolvingAgainstBaseURL: false) ?? URLComponents()
        let basePath = components.path
        let suffix = path.hasPrefix("/") ? String(path.dropFirst()) : path
        let resolvedPath: String
        if basePath.isEmpty || basePath == "/" {
            resolvedPath = "/" + suffix
        } else if basePath.hasSuffix("/") {
            resolvedPath = basePath + suffix
        } else {
            resolvedPath = basePath + "/" + suffix
        }
        if isPercentEncodedPath(resolvedPath) {
            components.percentEncodedPath = resolvedPath
        } else {
            components.path = resolvedPath
        }
        return components.url
    }

    private func isPercentEncodedPath(_ value: String) -> Bool {
        var sawPercent = false
        var index = value.startIndex
        while index < value.endIndex {
            if value[index] == "%" {
                sawPercent = true
                let nextIndex = value.index(after: index)
                guard nextIndex < value.endIndex else { return false }
                let nextNextIndex = value.index(after: nextIndex)
                guard nextNextIndex < value.endIndex else { return false }
                let first = value[nextIndex]
                let second = value[nextNextIndex]
                guard isHexDigit(first), isHexDigit(second) else { return false }
                index = value.index(after: nextNextIndex)
            } else {
                index = value.index(after: index)
            }
        }
        return sawPercent
    }

    private func isHexDigit(_ value: Character) -> Bool {
        guard let scalar = value.unicodeScalars.first, value.unicodeScalars.count == 1 else {
            return false
        }
        switch scalar.value {
        case 48...57, 65...70, 97...102:
            return true
        default:
            return false
        }
    }

    private func isStorageRelativePath(_ value: String) -> Bool {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return false }
        let normalized = trimmed.replacingOccurrences(of: "\\", with: "/")
        if normalized.hasPrefix("media/") || normalized.hasPrefix("metadata/") {
            return true
        }
        if normalized.hasPrefix("/media/") || normalized.hasPrefix("/metadata/") {
            return true
        }
        if normalized.contains("/storage/") || normalized.contains("/media/") || normalized.contains("/metadata/") {
            return true
        }
        return false
    }
}

struct LibraryCoverResolver {
    let apiBaseURL: URL
    let accessToken: String?

    func resolveCoverURL(for item: LibraryItem) -> URL? {
        let resolver = MediaURLResolver(origin: .library(apiBaseURL: apiBaseURL, accessToken: accessToken))
        for candidate in coverCandidates(for: item) {
            let trimmed = candidate.trimmingCharacters(in: .whitespacesAndNewlines)
            guard trimmed.nonEmptyValue != nil else { continue }
            guard !trimmed.contains("/pipelines/") else { continue }
            if let url = resolveCandidate(trimmed, jobId: item.jobId, resolver: resolver) {
                return url
            }
        }
        return nil
    }

    func resolveSecondaryCoverURL(for item: LibraryItem) -> URL? {
        guard let metadata = item.metadata else { return nil }
        guard let tvMetadata = extractTvMediaMetadata(from: metadata) else { return nil }
        let resolver = MediaURLResolver(origin: .library(apiBaseURL: apiBaseURL, accessToken: accessToken))
        let episode = resolveTvImage(from: tvMetadata, path: "episode")
        let show = resolveTvImage(from: tvMetadata, path: "show")
        let primary = episode ?? show
        guard let show, let primary, show != primary else { return nil }
        return resolveCandidate(show, jobId: item.jobId, resolver: resolver)
    }

    private func coverCandidates(for item: LibraryItem) -> [String] {
        var candidates: [String] = []
        var seen = Set<String>()

        func addCandidate(_ value: String?) {
            guard let trimmed = value?.nonEmptyValue else { return }
            guard !seen.contains(trimmed) else { return }
            seen.insert(trimmed)
            candidates.append(trimmed)
        }

        let isVideoItem = item.itemType == "video"
        let isSubtitleItem = item.itemType == "narrated_subtitle"
        let metadata = item.metadata

        // For video items, check thumbnail first
        if isVideoItem || isSubtitleItem {
            addCandidate(searchMetadata(metadata, for: "thumbnail"))
            appendTvCandidates(from: metadata, add: addCandidate)
        }

        addCandidate(item.coverPath)

        if let metadata {
            // Check for image object with original/medium
            if let imageObj = metadata["image"]?.objectValue {
                addCandidate(imageObj["original"]?.stringValue)
                addCandidate(imageObj["medium"]?.stringValue)
            }

            if let bookMetadata = extractBookMetadata(from: metadata) {
                addCandidate(bookMetadata["job_cover_asset"]?.stringValue)
                addCandidate(bookMetadata["book_cover_file"]?.stringValue)
                addCandidate(bookMetadata["job_cover_asset_url"]?.stringValue)
            }
            addCandidate(metadata["job_cover_asset"]?.stringValue)
            addCandidate(metadata["cover_url"]?.stringValue)
            addCandidate(metadata["poster"]?.stringValue)
        }

        if !(isVideoItem || isSubtitleItem) {
            addCandidate(searchMetadata(metadata, for: "thumbnail"))
            appendTvCandidates(from: metadata, add: addCandidate)
        }

        return candidates
    }

    private func searchMetadata(_ metadata: [String: JSONValue]?, for key: String, maxDepth: Int = 6) -> String? {
        guard let metadata else { return nil }
        if let value = metadata[key]?.stringValue {
            return value
        }
        guard maxDepth > 0 else { return nil }
        for value in metadata.values {
            if let nested = value.objectValue {
                if let found = searchMetadata(nested, for: key, maxDepth: maxDepth - 1) {
                    return found
                }
            }
        }
        return nil
    }

    private func appendTvCandidates(from metadata: [String: JSONValue]?, add: (String?) -> Void) {
        guard let metadata else { return }
        guard let tvMetadata = extractTvMediaMetadata(from: metadata) else { return }
        add(resolveTvImage(from: tvMetadata, path: "episode"))
        add(resolveTvImage(from: tvMetadata, path: "show"))
        add(resolveYoutubeThumbnail(from: tvMetadata))
    }

    private func extractBookMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        if let direct = metadata["book_metadata"]?.objectValue {
            return direct
        }
        if let result = metadata["result"]?.objectValue,
           let nested = result["book_metadata"]?.objectValue {
            return nested
        }
        return nil
    }

    private func extractTvMediaMetadata(from metadata: [String: JSONValue]) -> [String: JSONValue]? {
        let paths: [[String]] = [
            ["result", "youtube_dub", "media_metadata"],
            ["result", "subtitle", "metadata", "media_metadata"],
            ["request", "media_metadata"],
            ["media_metadata"]
        ]
        for path in paths {
            if let value = nestedValue(metadata, path: path)?.objectValue {
                return value
            }
        }
        return nil
    }

    private func resolveTvImage(from tvMetadata: [String: JSONValue], path: String) -> String? {
        guard let section = tvMetadata[path]?.objectValue else { return nil }
        guard let imageValue = section["image"] else { return nil }
        if let direct = imageValue.stringValue {
            return direct
        }
        if let imageObject = imageValue.objectValue {
            return imageObject["medium"]?.stringValue ?? imageObject["original"]?.stringValue
        }
        return nil
    }

    private func resolveYoutubeThumbnail(from tvMetadata: [String: JSONValue]) -> String? {
        guard let youtube = tvMetadata["youtube"]?.objectValue else { return nil }
        return youtube["thumbnail"]?.stringValue
    }

    private func nestedValue(_ source: [String: JSONValue], path: [String]) -> JSONValue? {
        var current: JSONValue = .object(source)
        for key in path {
            guard let object = current.objectValue, let next = object[key] else { return nil }
            current = next
        }
        return current
    }

    private func resolveCandidate(_ candidate: String, jobId: String, resolver: MediaURLResolver) -> URL? {
        let normalized = normalizeCandidate(candidate)
        if let url = URL(string: normalized), url.scheme != nil {
            if shouldAppendAccessToken(for: url) {
                return resolver.resolvePath(jobId: jobId, relativePath: normalized)
            }
            return url
        }
        return resolver.resolvePath(jobId: jobId, relativePath: normalized)
    }

    private func shouldAppendAccessToken(for url: URL) -> Bool {
        guard let host = url.host?.lowercased(),
              let apiHost = apiBaseURL.host?.lowercased() else { return false }
        return host == apiHost
    }

    private func normalizeCandidate(_ candidate: String) -> String {
        let trimmed = candidate.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return trimmed }
        if trimmed.hasPrefix("//") {
            return "https:" + trimmed
        }
        let lower = trimmed.lowercased()
        if !lower.contains("://"), isYoutubeHostPath(lower) {
            return "https://" + trimmed
        }
        if let url = URL(string: trimmed),
           let scheme = url.scheme?.lowercased(),
           scheme == "http",
           shouldUpgradeToHTTPS(for: url),
           var components = URLComponents(url: url, resolvingAgainstBaseURL: false) {
            components.scheme = "https"
            return components.string ?? trimmed
        }
        return trimmed
    }

    private func shouldUpgradeToHTTPS(for url: URL) -> Bool {
        guard let host = url.host?.lowercased() else { return false }
        return isYoutubeHost(host)
    }

    private func isYoutubeHostPath(_ value: String) -> Bool {
        let host = value.split(separator: "/").first.map(String.init) ?? value
        return isYoutubeHost(host)
    }

    private func isYoutubeHost(_ host: String) -> Bool {
        let normalized = host.trimmingCharacters(in: .whitespacesAndNewlines)
        return normalized.hasSuffix("ytimg.com")
            || normalized.hasSuffix("youtube.com")
            || normalized.hasSuffix("youtu.be")
    }
}
