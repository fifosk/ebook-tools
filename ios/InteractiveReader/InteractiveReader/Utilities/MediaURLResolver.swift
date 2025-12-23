import Foundation

enum MediaURLOrigin {
    case library(apiBaseURL: URL, accessToken: String?)
    case storage(apiBaseURL: URL, resolver: StorageResolver, accessToken: String?)
}

struct MediaURLResolver {
    let origin: MediaURLOrigin

    func resolveAudioURL(jobId: String, track: AudioTrackMetadata) -> URL? {
        if let urlString = track.url, let url = resolveURL(from: urlString, jobId: jobId) {
            return url
        }
        if let path = track.path {
            return resolveURL(from: path, jobId: jobId)
        }
        return nil
    }

    func resolveFileURL(jobId: String, file: PipelineMediaFile) -> URL? {
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
            case .storage:
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
                if let url = buildURL(from: apiBaseURL, path: trimmed) {
                    return appendAccessToken(url, accessToken: accessToken)
                }
            }
            let relative = extractLibraryRelativePath(from: trimmed)
                ?? (trimmed.hasPrefix("/") ? trimmed.trimmingCharacters(in: CharacterSet(charactersIn: "/")) : trimmed)
            return resolver.url(jobId: jobId, filePath: relative)
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
        if let range = normalised.range(of: "/media/") {
            return String(normalised[range.lowerBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        }
        if let range = normalised.range(of: "/metadata/") {
            return String(normalised[range.lowerBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
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
}

