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
        return url.appendingPathComponent(trimmedPath, isDirectory: false)
    }

    private static func makeDefaultBaseURL(from apiBaseURL: URL) -> URL? {
        let url = apiBaseURL
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
}
