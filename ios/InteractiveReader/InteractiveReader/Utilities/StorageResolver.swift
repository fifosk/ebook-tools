import Foundation

struct StorageResolver {
    enum ResolverError: Error {
        case invalidBaseURL
    }

    let baseURL: URL

    init(apiBaseURL: URL, override: URL? = nil) throws {
        if let override = override {
            self.baseURL = override
            return
        }
        guard let resolved = StorageResolver.makeDefaultBaseURL(from: apiBaseURL) else {
            throw ResolverError.invalidBaseURL
        }
        self.baseURL = resolved
    }

    func url(jobId: String, filePath: String) -> URL? {
        let trimmedJob = jobId.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let trimmedPath = filePath.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard !trimmedJob.isEmpty, !trimmedPath.isEmpty else {
            return nil
        }
        var url = baseURL
        url.appendPathComponent(trimmedJob, isDirectory: true)
        let components = trimmedPath
            .split(separator: "/")
            .map { String($0) }
            .filter { !$0.isEmpty }
        guard !components.isEmpty else { return nil }
        for (index, component) in components.enumerated() {
            url.appendPathComponent(component, isDirectory: index < components.count - 1)
        }
        return url
    }

    private static func makeDefaultBaseURL(from apiBaseURL: URL) -> URL? {
        let url = normalizeBaseURL(apiBaseURL)
        let path = url.path
        if path.hasSuffix("/storage/jobs") || path == "/storage/jobs" {
            return url
        }
        if path.hasSuffix("/storage") {
            return url.appendingPathComponent("jobs", isDirectory: true)
        }
        return url.appendingPathComponent("storage", isDirectory: true)
            .appendingPathComponent("jobs", isDirectory: true)
    }

    private static func normalizeBaseURL(_ apiBaseURL: URL) -> URL {
        guard var components = URLComponents(url: apiBaseURL, resolvingAgainstBaseURL: false) else {
            return apiBaseURL
        }
        if let host = components.host?.lowercased(),
           host == "langtools.fifosk.synology.me" {
            components.host = "api.langtools.fifosk.synology.me"
        }
        if components.path == "/api" || components.path == "/api/" {
            components.path = "/"
        }
        return components.url ?? apiBaseURL
    }
}
