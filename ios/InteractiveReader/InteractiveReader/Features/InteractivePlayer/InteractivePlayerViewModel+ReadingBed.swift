import Foundation

extension InteractivePlayerViewModel {
    func selectReadingBed(id: String?) {
        // If no explicit ID provided, try to restore the last used one
        let normalized = id?.nonEmptyValue
            ?? UserDefaults.standard.string(forKey: MusicPreferences.lastReadingBedIDKey)?.nonEmptyValue
        let validID: String?
        if let normalized,
           let beds = readingBedCatalog?.beds,
           beds.contains(where: { $0.id == normalized }) {
            validID = normalized
        } else {
            validID = nil
        }
        selectedReadingBedID = validID
        // Persist the selection for future sessions
        if let validID {
            UserDefaults.standard.set(validID, forKey: MusicPreferences.lastReadingBedIDKey)
        }
        readingBedURL = resolveReadingBedURL(from: readingBedCatalog, selectedID: validID)
    }

    func resolveReadingBedURL(from catalog: ReadingBedListResponse?, selectedID: String?) -> URL? {
        guard let baseURL = readingBedBaseURL ?? apiBaseURL else { return nil }
        let selectedEntry = selectReadingBed(from: catalog, selectedID: selectedID)
        let rawPath = selectedEntry?.url.nonEmptyValue ?? defaultReadingBedPath
        if let sharedURL = OfflineMediaStore.sharedReadingBedURL(for: rawPath) {
            return sharedURL
        }
        if let fallback = OfflineMediaStore.sharedDefaultReadingBedURL() {
            return fallback
        }
        if baseURL.isFileURL {
            guard let relative = normalizeReadingBedPath(rawPath) else { return nil }
            let localURL = baseURL.appendingPathComponent(relative)
            if FileManager.default.fileExists(atPath: localURL.path) {
                return localURL
            }
        }
        // When readingBedBaseURL is nil (online mode), use the API file endpoint
        // instead of appending the /assets/ path to apiBaseURL (which doesn't serve static assets).
        if readingBedBaseURL == nil, let apiBase = apiBaseURL, let bedID = selectedEntry?.id ?? bedIDFromPath(rawPath) {
            let encodedBedID = AppleAPIPathComponentEncoding.encode(bedID)
            let path = ApplePlaybackStateRuntimeContract.readingBedFilePath(encodedBedID)
            guard let apiURL = buildReadingBedURL(from: path, baseURL: apiBase) else { return nil }
            return appendAccessToken(apiURL, token: authToken)
        }
        guard let url = buildReadingBedURL(from: rawPath, baseURL: baseURL) else { return nil }
        return appendAccessToken(url, token: authToken)
    }

    /// Extract a reading bed ID from a path like "/assets/reading-beds/lost-in-the-pages.mp3"
    private func bedIDFromPath(_ path: String) -> String? {
        let filename = URL(string: path)?.lastPathComponent ?? (path as NSString).lastPathComponent
        guard !filename.isEmpty else { return nil }
        // Strip extension to get the bed ID
        if let dotIndex = filename.lastIndex(of: ".") {
            let id = String(filename[filename.startIndex..<dotIndex])
            return id.isEmpty ? nil : id
        }
        return filename
    }

    func selectReadingBed(from catalog: ReadingBedListResponse?, selectedID: String?) -> ReadingBedEntry? {
        guard let beds = catalog?.beds, !beds.isEmpty else { return nil }
        if let selectedID,
           let match = beds.first(where: { $0.id == selectedID }) {
            return match
        }
        if let defaultId = catalog?.defaultId?.nonEmptyValue,
           let match = beds.first(where: { $0.id == defaultId }) {
            return match
        }
        if let match = beds.first(where: { $0.isDefault == true }) {
            return match
        }
        return beds.first
    }

    func buildReadingBedURL(from rawPath: String, baseURL: URL) -> URL? {
        let trimmed = rawPath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if let url = URL(string: trimmed), url.scheme != nil {
            return url
        }
        var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) ?? URLComponents()
        let basePath = components.path
        let suffix = trimmed.hasPrefix("/") ? String(trimmed.dropFirst()) : trimmed
        let resolvedPath: String
        if basePath.isEmpty || basePath == "/" {
            resolvedPath = "/" + suffix
        } else if basePath.hasSuffix("/") {
            resolvedPath = basePath + suffix
        } else {
            resolvedPath = basePath + "/" + suffix
        }
        components.path = resolvedPath
        return components.url ?? baseURL.appendingPathComponent(suffix)
    }

    func appendAccessToken(_ url: URL, token: String?) -> URL {
        guard !url.isFileURL else { return url }
        guard let token, !token.isEmpty else { return url }
        guard var components = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return url }
        var items = components.queryItems ?? []
        if items.contains(where: { $0.name == "access_token" }) {
            return url
        }
        items.append(URLQueryItem(name: "access_token", value: token))
        components.queryItems = items
        return components.url ?? url
    }

    private func normalizeReadingBedPath(_ rawPath: String) -> String? {
        let trimmed = rawPath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let normalized = trimmed.replacingOccurrences(of: "\\", with: "/")
        let path = URL(string: normalized)?.path ?? normalized
        if let range = path.range(of: "/assets/reading-beds/") {
            return String(path[range.lowerBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        }
        if let range = path.range(of: "/reading-beds/") {
            let suffix = String(path[range.lowerBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            return suffix.hasPrefix("assets/") ? suffix : "assets/\(suffix)"
        }
        let trimmedPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        if trimmedPath.hasPrefix("assets/reading-beds/") {
            return trimmedPath
        }
        if trimmedPath.hasPrefix("reading-beds/") {
            return "assets/\(trimmedPath)"
        }
        guard let fileName = trimmedPath.split(separator: "/").last else { return nil }
        return "assets/reading-beds/\(fileName)"
    }
}
