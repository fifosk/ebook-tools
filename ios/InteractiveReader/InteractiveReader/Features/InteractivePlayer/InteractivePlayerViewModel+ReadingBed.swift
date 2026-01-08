import Foundation

extension InteractivePlayerViewModel {
    func selectReadingBed(id: String?) {
        let normalized = id?.nonEmptyValue
        let validID: String?
        if let normalized,
           let beds = readingBedCatalog?.beds,
           beds.contains(where: { $0.id == normalized }) {
            validID = normalized
        } else {
            validID = nil
        }
        selectedReadingBedID = validID
        readingBedURL = resolveReadingBedURL(from: readingBedCatalog, selectedID: validID)
    }

    func resolveReadingBedURL(from catalog: ReadingBedListResponse?, selectedID: String?) -> URL? {
        guard let apiBaseURL else { return nil }
        let selectedEntry = selectReadingBed(from: catalog, selectedID: selectedID)
        let rawPath = selectedEntry?.url.nonEmptyValue ?? defaultReadingBedPath
        guard let url = buildReadingBedURL(from: rawPath, baseURL: apiBaseURL) else { return nil }
        return appendAccessToken(url, token: authToken)
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
}
