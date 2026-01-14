import Foundation

@MainActor
final class OfflineMediaStore: ObservableObject {
    enum OfflineMediaKind: String, Codable {
        case job
        case library

        var folderName: String { rawValue }
    }

    struct OfflineMediaKey: Hashable {
        let jobId: String
        let kind: OfflineMediaKind
    }

    enum SyncState: Equatable {
        case idle
        case syncing(Double)
        case synced
        case failed(String)
    }

    struct SyncStatus: Equatable {
        let state: SyncState
        let updatedAt: Date?
        let fileCount: Int?
        let totalBytes: Int64?

        var progress: Double? {
            if case let .syncing(value) = state {
                return value
            }
            return nil
        }

        var isSynced: Bool {
            if case .synced = state {
                return true
            }
            return false
        }

        var isSyncing: Bool {
            if case .syncing = state {
                return true
            }
            return false
        }

        var errorMessage: String? {
            if case let .failed(message) = state {
                return message
            }
            return nil
        }
    }

    struct OfflineMediaPayload {
        let media: PipelineMediaResponse
        let timing: JobTimingResponse?
        let storageBaseURL: URL
    }

    private struct OfflineMediaManifest: Codable {
        let jobId: String
        let kind: OfflineMediaKind
        let updatedAt: TimeInterval
        let fileCount: Int
        let totalBytes: Int64
        let mediaFile: String
        let timingFile: String?
    }

    private struct DownloadItem {
        let relativePath: String
        let url: URL
    }

    @Published private(set) var statuses: [OfflineMediaKey: SyncStatus] = [:]

    private let containerIdentifier = "iCloud.com.ebook-tools.interactivereader"
    private let rootFolderName = "OfflineMedia"
    private let manifestFileName = "offline_manifest.json"
    private let mediaFileName = "media.json"
    private let timingFileName = "timing.json"
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder
    private var syncTasks: [OfflineMediaKey: Task<Void, Never>] = [:]

    init() {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601
        self.encoder = encoder

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601
        self.decoder = decoder
    }

    var isAvailable: Bool {
        FileManager.default.url(forUbiquityContainerIdentifier: containerIdentifier) != nil
    }

    func status(for jobId: String, kind: OfflineMediaKind) -> SyncStatus {
        let key = OfflineMediaKey(jobId: jobId, kind: kind)
        if let status = statuses[key] {
            return status
        }
        if let manifest = loadManifest(for: key) {
            return SyncStatus(
                state: .synced,
                updatedAt: Date(timeIntervalSince1970: manifest.updatedAt),
                fileCount: manifest.fileCount,
                totalBytes: manifest.totalBytes
            )
        }
        return SyncStatus(state: .idle, updatedAt: nil, fileCount: nil, totalBytes: nil)
    }

    func cachedPayload(for jobId: String, kind: OfflineMediaKind) -> OfflineMediaPayload? {
        let key = OfflineMediaKey(jobId: jobId, kind: kind)
        guard let baseURL = storageBaseURL(for: kind) else { return nil }
        guard let manifest = loadManifest(for: key) else { return nil }
        let itemRoot = baseURL.appendingPathComponent(jobId, isDirectory: true)
        let mediaURL = itemRoot.appendingPathComponent(manifest.mediaFile)
        guard let mediaData = try? Data(contentsOf: mediaURL),
              let media = try? decoder.decode(PipelineMediaResponse.self, from: mediaData)
        else {
            return nil
        }
        var timing: JobTimingResponse? = nil
        if let timingFile = manifest.timingFile {
            let timingURL = itemRoot.appendingPathComponent(timingFile)
            if let timingData = try? Data(contentsOf: timingURL) {
                timing = try? decoder.decode(JobTimingResponse.self, from: timingData)
            }
        }
        return OfflineMediaPayload(media: media, timing: timing, storageBaseURL: baseURL)
    }

    func sync(jobId: String, kind: OfflineMediaKind, configuration: APIClientConfiguration) {
        let trimmedJobId = jobId.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedJobId.isEmpty else { return }
        let key = OfflineMediaKey(jobId: trimmedJobId, kind: kind)
        guard syncTasks[key] == nil else { return }
        guard let baseURL = storageBaseURL(for: kind) else {
            statuses[key] = SyncStatus(
                state: .failed("iCloud Drive is unavailable."),
                updatedAt: Date(),
                fileCount: nil,
                totalBytes: nil
            )
            return
        }

        statuses[key] = SyncStatus(state: .syncing(0), updatedAt: Date(), fileCount: nil, totalBytes: nil)
        let task: Task<Void, Never> = Task.detached(priority: .utility) { [weak self] () async -> Void in
            guard let self else { return }
            await self.performSync(
                jobId: trimmedJobId,
                kind: kind,
                configuration: configuration,
                baseURL: baseURL
            )
        }
        syncTasks[key] = task
    }

    func remove(jobId: String, kind: OfflineMediaKind) {
        let trimmedJobId = jobId.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedJobId.isEmpty else { return }
        let key = OfflineMediaKey(jobId: trimmedJobId, kind: kind)
        syncTasks[key]?.cancel()
        syncTasks[key] = nil
        if let itemRoot = itemRoot(for: key) {
            try? FileManager.default.removeItem(at: itemRoot)
        }
        statuses[key] = SyncStatus(state: .idle, updatedAt: nil, fileCount: nil, totalBytes: nil)
    }

    func storageBaseURL(for kind: OfflineMediaKind) -> URL? {
        guard let root = rootURL() else { return nil }
        return root.appendingPathComponent(kind.folderName, isDirectory: true)
    }

    func localResolver(for kind: OfflineMediaKind, configuration: APIClientConfiguration) -> MediaURLResolver? {
        guard let baseURL = storageBaseURL(for: kind),
              let resolver = try? StorageResolver(apiBaseURL: configuration.apiBaseURL, override: baseURL)
        else {
            return nil
        }
        return MediaURLResolver(
            origin: .storage(apiBaseURL: configuration.apiBaseURL, resolver: resolver, accessToken: nil)
        )
    }

    private func rootURL() -> URL? {
        guard let container = FileManager.default.url(forUbiquityContainerIdentifier: containerIdentifier) else {
            return nil
        }
        let documents = container.appendingPathComponent("Documents", isDirectory: true)
        return documents.appendingPathComponent(rootFolderName, isDirectory: true)
    }

    private func itemRoot(for key: OfflineMediaKey) -> URL? {
        guard let base = storageBaseURL(for: key.kind) else { return nil }
        return base.appendingPathComponent(key.jobId, isDirectory: true)
    }

    private func manifestURL(for key: OfflineMediaKey) -> URL? {
        guard let root = itemRoot(for: key) else { return nil }
        return root.appendingPathComponent(manifestFileName)
    }

    private func loadManifest(for key: OfflineMediaKey) -> OfflineMediaManifest? {
        guard let url = manifestURL(for: key),
              let data = try? Data(contentsOf: url)
        else {
            return nil
        }
        return try? decoder.decode(OfflineMediaManifest.self, from: data)
    }

    private func writeManifest(_ manifest: OfflineMediaManifest, to key: OfflineMediaKey) throws {
        guard let url = manifestURL(for: key) else { return }
        let data = try encoder.encode(manifest)
        try data.write(to: url, options: .atomic)
    }

    private func performSync(
        jobId: String,
        kind: OfflineMediaKind,
        configuration: APIClientConfiguration,
        baseURL: URL
    ) async {
        let key = OfflineMediaKey(jobId: jobId, kind: kind)
        let itemRoot = baseURL.appendingPathComponent(jobId, isDirectory: true)
        let fileManager = FileManager.default
        do {
            try fileManager.createDirectory(at: itemRoot, withIntermediateDirectories: true)
            let client = APIClient(configuration: configuration)
            let mediaData: Data
            switch kind {
            case .job:
                mediaData = try await client.fetchJobMediaData(jobId: jobId)
            case .library:
                mediaData = try await client.fetchLibraryMediaData(jobId: jobId)
            }
            let media = try decoder.decode(PipelineMediaResponse.self, from: mediaData)
            let timingData = try? await client.fetchJobTimingData(jobId: jobId)
            let resolver = try makeRemoteResolver(for: kind, configuration: configuration)
            let items = collectDownloadItems(media: media, jobId: jobId, resolver: resolver)

            var completed = 0
            var totalBytes: Int64 = 0
            let totalFiles = items.count
            for item in items {
                if Task.isCancelled { throw CancellationError() }
                let fileBytes = try await download(item: item, to: itemRoot)
                totalBytes += fileBytes
                completed += 1
                let progress = totalFiles > 0 ? Double(completed) / Double(totalFiles) : 1
                await MainActor.run {
                    statuses[key] = SyncStatus(
                        state: .syncing(progress),
                        updatedAt: Date(),
                        fileCount: totalFiles,
                        totalBytes: totalBytes
                    )
                }
            }

            let mediaURL = itemRoot.appendingPathComponent(mediaFileName)
            try mediaData.write(to: mediaURL, options: .atomic)
            var timingName: String? = nil
            if let timingData {
                let timingURL = itemRoot.appendingPathComponent(timingFileName)
                try timingData.write(to: timingURL, options: .atomic)
                timingName = timingFileName
            }
            let manifest = OfflineMediaManifest(
                jobId: jobId,
                kind: kind,
                updatedAt: Date().timeIntervalSince1970,
                fileCount: totalFiles,
                totalBytes: totalBytes,
                mediaFile: mediaFileName,
                timingFile: timingName
            )
            try writeManifest(manifest, to: key)
            await MainActor.run {
                statuses[key] = SyncStatus(
                    state: .synced,
                    updatedAt: Date(),
                    fileCount: totalFiles,
                    totalBytes: totalBytes
                )
            }
        } catch {
            if error is CancellationError {
                await MainActor.run {
                    statuses[key] = SyncStatus(state: .idle, updatedAt: nil, fileCount: nil, totalBytes: nil)
                }
            } else {
                try? fileManager.removeItem(at: itemRoot)
                await MainActor.run {
                    statuses[key] = SyncStatus(
                        state: .failed(error.localizedDescription),
                        updatedAt: Date(),
                        fileCount: nil,
                        totalBytes: nil
                    )
                }
            }
        }
        await MainActor.run {
            syncTasks[key] = nil
        }
    }

    private func makeRemoteResolver(
        for kind: OfflineMediaKind,
        configuration: APIClientConfiguration
    ) throws -> MediaURLResolver {
        switch kind {
        case .job:
            let storageResolver = try StorageResolver(
                apiBaseURL: configuration.apiBaseURL,
                override: configuration.storageBaseURL
            )
            return MediaURLResolver(
                origin: .storage(
                    apiBaseURL: configuration.apiBaseURL,
                    resolver: storageResolver,
                    accessToken: configuration.authToken
                )
            )
        case .library:
            return MediaURLResolver(
                origin: .library(apiBaseURL: configuration.apiBaseURL, accessToken: configuration.authToken)
            )
        }
    }

    private func collectDownloadItems(
        media: PipelineMediaResponse,
        jobId: String,
        resolver: MediaURLResolver
    ) -> [DownloadItem] {
        var items: [DownloadItem] = []
        var seen: Set<String> = []

        func addItem(relativePath: String?, url: URL?) {
            guard let relativePath = relativePath?.nonEmptyValue else { return }
            guard let url else { return }
            let normalized = normalizeRelativePath(relativePath, jobId: jobId) ?? relativePath
            let trimmed = normalized.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            guard !trimmed.isEmpty else { return }
            guard !seen.contains(trimmed) else { return }
            seen.insert(trimmed)
            items.append(DownloadItem(relativePath: trimmed, url: url))
        }

        for files in media.media.values {
            for file in files {
                let relative = preferredRelativePath(for: file, jobId: jobId)
                let url = resolver.resolveFileURL(jobId: jobId, file: file)
                    ?? relative.flatMap { resolver.resolvePath(jobId: jobId, relativePath: $0) }
                addItem(relativePath: relative, url: url)
            }
        }

        for chunk in media.chunks {
            for file in chunk.files {
                let relative = preferredRelativePath(for: file, jobId: jobId)
                let url = resolver.resolveFileURL(jobId: jobId, file: file)
                    ?? relative.flatMap { resolver.resolvePath(jobId: jobId, relativePath: $0) }
                addItem(relativePath: relative, url: url)
            }
            if let metadataPath = chunk.metadataPath?.nonEmptyValue {
                let url = resolver.resolvePath(jobId: jobId, relativePath: metadataPath)
                addItem(relativePath: metadataPath, url: url)
            }
            if let metadataURL = chunk.metadataURL?.nonEmptyValue {
                let url = resolver.resolvePath(jobId: jobId, relativePath: metadataURL)
                addItem(relativePath: metadataURL, url: url)
            }
            for track in chunk.audioTracks.values {
                let raw = track.path?.nonEmptyValue ?? track.url?.nonEmptyValue
                guard let raw else { continue }
                let url = resolver.resolvePath(jobId: jobId, relativePath: raw)
                addItem(relativePath: raw, url: url)
            }
        }

        return items
    }

    private func preferredRelativePath(for file: PipelineMediaFile, jobId: String) -> String? {
        if let relative = file.relativePath?.nonEmptyValue {
            return relative
        }
        if let path = file.path?.nonEmptyValue {
            return normalizeRelativePath(path, jobId: jobId)
        }
        if let url = file.url?.nonEmptyValue {
            return normalizeRelativePath(url, jobId: jobId)
        }
        return nil
    }

    private func normalizeRelativePath(_ raw: String, jobId: String) -> String? {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let normalized = trimmed.replacingOccurrences(of: "\\", with: "/")
        let path = URL(string: normalized)?.path ?? normalized
        let encodedJob = jobId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? jobId
        let jobCandidates = [jobId, encodedJob]
        for candidate in jobCandidates {
            if let range = path.range(of: "/storage/jobs/\(candidate)/") {
                return String(path[range.upperBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            }
            if let range = path.range(of: "/api/library/media/\(candidate)/file/") {
                return String(path[range.upperBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            }
        }
        if let range = path.range(of: "/media/") {
            return String(path[range.lowerBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        }
        if let range = path.range(of: "/metadata/") {
            return String(path[range.lowerBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        }
        let trimmedPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        if trimmedPath.hasPrefix("media/") || trimmedPath.hasPrefix("metadata/") {
            return trimmedPath
        }
        if let fileName = trimmedPath.split(separator: "/").last {
            return "media/\(fileName)"
        }
        return nil
    }

    private func download(item: DownloadItem, to root: URL) async throws -> Int64 {
        let destination = root.appendingPathComponent(item.relativePath)
        let folder = destination.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        if FileManager.default.fileExists(atPath: destination.path) {
            return fileSize(at: destination)
        }
        if item.url.isFileURL {
            try FileManager.default.copyItem(at: item.url, to: destination)
            return fileSize(at: destination)
        }
        var request = URLRequest(url: item.url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        let (tempURL, response) = try await URLSession.shared.download(for: request)
        if let httpResponse = response as? HTTPURLResponse,
           !(200..<300).contains(httpResponse.statusCode) {
            throw APIClientError.httpError(httpResponse.statusCode, nil)
        }
        if FileManager.default.fileExists(atPath: destination.path) {
            try FileManager.default.removeItem(at: destination)
        }
        try FileManager.default.moveItem(at: tempURL, to: destination)
        return fileSize(at: destination)
    }

    private func fileSize(at url: URL) -> Int64 {
        guard let values = try? url.resourceValues(forKeys: [.fileSizeKey]),
              let size = values.fileSize else {
            return 0
        }
        return Int64(size)
    }
}
