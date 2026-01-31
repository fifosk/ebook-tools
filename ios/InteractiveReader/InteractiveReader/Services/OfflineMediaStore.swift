import Foundation

@MainActor
final class OfflineMediaStore: ObservableObject {
    static let sharedContainerIdentifier = "iCloud.com.ebook-tools.interactivereader"
    static let sharedRootFolderName = "OfflineMedia"
    static let sharedReadingBedsFolderName = "ReadingBeds"
    static let sharedDefaultReadingBedPath = "/assets/reading-beds/lost-in-the-pages.mp3"

    /// Storage mode for offline media
    enum StorageMode: String, Codable {
        /// Device-local storage (app's Documents directory) - no sync between devices
        case local
        /// iCloud storage - syncs between devices but may have sync delays
        case iCloud
    }

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
        let readingBeds: ReadingBedListResponse?
        let readingBedBaseURL: URL?
    }

    private struct OfflineMediaManifest: Codable {
        let jobId: String
        let kind: OfflineMediaKind
        let updatedAt: TimeInterval
        let fileCount: Int
        let totalBytes: Int64
        let mediaFile: String
        let timingFile: String?
        let readingBedsFile: String?
    }

    private struct DownloadItem {
        let relativePath: String
        let url: URL
    }

    @Published private(set) var statuses: [OfflineMediaKey: SyncStatus] = [:]

    /// Current storage mode - defaults to local for reliability
    @Published var storageMode: StorageMode = .local

    private let containerIdentifier = OfflineMediaStore.sharedContainerIdentifier
    private let rootFolderName = OfflineMediaStore.sharedRootFolderName
    private let readingBedsFolderName = OfflineMediaStore.sharedReadingBedsFolderName
    private let manifestFileName = "offline_manifest.json"
    private let mediaFileName = "media.json"
    private let timingFileName = "timing.json"
    private let readingBedsFileName = "reading_beds.json"
    private let defaultReadingBedPath = OfflineMediaStore.sharedDefaultReadingBedPath
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder
    private var syncTasks: [OfflineMediaKey: Task<Void, Never>] = [:]
    private var readingBedTask: Task<Void, Never>?

    /// UserDefaults key for persisting storage mode
    private static let storageModeKey = "OfflineMediaStorageMode"

    init() {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601
        self.encoder = encoder

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601
        self.decoder = decoder

        // Load persisted storage mode, default to local for reliability
        if let savedMode = UserDefaults.standard.string(forKey: Self.storageModeKey),
           let mode = StorageMode(rawValue: savedMode) {
            self.storageMode = mode
        } else {
            self.storageMode = .local
        }
    }

    /// Whether offline storage is available (always true for local, depends on iCloud for iCloud mode)
    var isAvailable: Bool {
        switch storageMode {
        case .local:
            return true
        case .iCloud:
            return FileManager.default.url(forUbiquityContainerIdentifier: containerIdentifier) != nil
        }
    }

    /// Whether iCloud storage is available on this device
    var isICloudAvailable: Bool {
        FileManager.default.url(forUbiquityContainerIdentifier: containerIdentifier) != nil
    }

    /// Set the storage mode and persist it
    func setStorageMode(_ mode: StorageMode) {
        storageMode = mode
        UserDefaults.standard.set(mode.rawValue, forKey: Self.storageModeKey)
        print("[OfflineStore] Storage mode set to: \(mode.rawValue)")
    }

    /// Get a description of the current storage location for debugging
    var storageLocationDescription: String {
        guard let root = rootURL() else { return "unavailable" }
        let modeLabel = storageMode == .local ? "Local" : "iCloud"
        return "\(modeLabel): \(root.path)"
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

    func cachedPayload(for jobId: String, kind: OfflineMediaKind) async -> OfflineMediaPayload? {
        let key = OfflineMediaKey(jobId: jobId, kind: kind)
        guard let baseURL = storageBaseURL(for: kind) else { return nil }
        guard let manifest = loadManifest(for: key) else { return nil }
        let itemRoot = baseURL.appendingPathComponent(jobId, isDirectory: true)
        let readingBedsFileName = readingBedsFileName
        let defaultReadingBedPath = defaultReadingBedPath
        let sharedReadingBedsRoot = readingBedsRootURL()
        return await Task.detached(priority: .utility) {
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            decoder.dateDecodingStrategy = .iso8601

            let mediaURL = itemRoot.appendingPathComponent(manifest.mediaFile)
            guard let mediaData = try? Data(contentsOf: mediaURL, options: .mappedIfSafe),
                  let media = try? decoder.decode(PipelineMediaResponse.self, from: mediaData)
            else {
                return nil
            }

            var timing: JobTimingResponse? = nil
            if let timingFile = manifest.timingFile {
                let timingURL = itemRoot.appendingPathComponent(timingFile)
                if let timingData = try? Data(contentsOf: timingURL, options: .mappedIfSafe) {
                    timing = try? decoder.decode(JobTimingResponse.self, from: timingData)
                }
            }

            var readingBeds: ReadingBedListResponse? = nil
            var readingBedBaseURL: URL? = nil
            if let sharedRoot = sharedReadingBedsRoot {
                let sharedFile = sharedRoot.appendingPathComponent(readingBedsFileName)
                if let readingBedsData = try? Data(contentsOf: sharedFile, options: .mappedIfSafe) {
                    readingBeds = try? decoder.decode(ReadingBedListResponse.self, from: readingBedsData)
                    readingBedBaseURL = sharedRoot
                }
            }
            if readingBeds == nil {
                let readingBedsFile = manifest.readingBedsFile ?? readingBedsFileName
                let readingBedsURL = itemRoot.appendingPathComponent(readingBedsFile)
                if let readingBedsData = try? Data(contentsOf: readingBedsURL, options: .mappedIfSafe) {
                    readingBeds = try? decoder.decode(ReadingBedListResponse.self, from: readingBedsData)
                    readingBedBaseURL = itemRoot
                }
            }
            if readingBedBaseURL == nil {
                if let sharedRoot = sharedReadingBedsRoot {
                    let defaultRelative = defaultReadingBedPath.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
                    let defaultURL = sharedRoot.appendingPathComponent(defaultRelative)
                    if FileManager.default.fileExists(atPath: defaultURL.path) {
                        readingBedBaseURL = sharedRoot
                    }
                }
                if readingBedBaseURL == nil {
                    readingBedBaseURL = itemRoot
                }
            }

            return OfflineMediaPayload(
                media: media,
                timing: timing,
                storageBaseURL: baseURL,
                readingBeds: readingBeds,
                readingBedBaseURL: readingBedBaseURL
            )
        }.value
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

    static func sharedReadingBedURL(for rawPath: String) -> URL? {
        guard let root = sharedReadingBedsRootURL() else { return nil }
        guard let relative = normalizeSharedReadingBedPath(rawPath) else { return nil }
        let url = root.appendingPathComponent(relative)
        guard FileManager.default.fileExists(atPath: url.path) else { return nil }
        if let values = try? url.resourceValues(forKeys: [.isUbiquitousItemKey, .ubiquitousItemDownloadingStatusKey]),
           values.isUbiquitousItem == true,
           values.ubiquitousItemDownloadingStatus != URLUbiquitousItemDownloadingStatus.current {
            try? FileManager.default.startDownloadingUbiquitousItem(at: url)
            return nil
        }
        return url
    }

    static func sharedDefaultReadingBedURL() -> URL? {
        sharedReadingBedURL(for: sharedDefaultReadingBedPath)
    }

    static func sharedReadingBedsRootURL() -> URL? {
        // Reading beds can be shared via iCloud if available, otherwise use local
        if let container = FileManager.default.url(forUbiquityContainerIdentifier: sharedContainerIdentifier) {
            let documents = container.appendingPathComponent("Documents", isDirectory: true)
            return documents
                .appendingPathComponent(sharedRootFolderName, isDirectory: true)
                .appendingPathComponent(sharedReadingBedsFolderName, isDirectory: true)
        }
        // Fallback to local Documents directory
        guard let documentsDir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else {
            return nil
        }
        return documentsDir
            .appendingPathComponent(sharedRootFolderName, isDirectory: true)
            .appendingPathComponent(sharedReadingBedsFolderName, isDirectory: true)
    }

    func syncSharedReadingBedsIfNeeded(configuration: APIClientConfiguration) {
        guard readingBedTask == nil else { return }
        guard let root = readingBedsRootURL() else { return }
        let listURL = root.appendingPathComponent(readingBedsFileName)
        let defaultRelative = defaultReadingBedPath.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let defaultURL = root.appendingPathComponent(defaultRelative)
        if FileManager.default.fileExists(atPath: listURL.path),
           FileManager.default.fileExists(atPath: defaultURL.path) {
            return
        }
        readingBedTask = Task.detached(priority: .utility) { [weak self] () async -> Void in
            guard let self else { return }
            await self.performSharedReadingBedSync(configuration: configuration)
        }
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
        switch storageMode {
        case .local:
            // Use app's local Documents directory
            guard let documentsDir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else {
                return nil
            }
            return documentsDir.appendingPathComponent(rootFolderName, isDirectory: true)
        case .iCloud:
            // Use iCloud container
            guard let container = FileManager.default.url(forUbiquityContainerIdentifier: containerIdentifier) else {
                return nil
            }
            let documents = container.appendingPathComponent("Documents", isDirectory: true)
            return documents.appendingPathComponent(rootFolderName, isDirectory: true)
        }
    }

    private func readingBedsRootURL() -> URL? {
        guard let root = rootURL() else { return nil }
        return root.appendingPathComponent(readingBedsFolderName, isDirectory: true)
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
            let readingBedsRoot = readingBedsRootURL()
            if let readingBedsRoot {
                try fileManager.createDirectory(at: readingBedsRoot, withIntermediateDirectories: true)
            }
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
            let readingBeds = try? await client.fetchReadingBeds()
            let resolver = try makeRemoteResolver(for: kind, configuration: configuration)
            let items = collectDownloadItems(media: media, jobId: jobId, resolver: resolver)
            let readingBedItems = collectReadingBedItems(
                readingBeds: readingBeds,
                apiBaseURL: configuration.apiBaseURL,
                jobId: jobId
            )
            let pendingReadingBedItems: [DownloadItem]
            if let readingBedsRoot {
                pendingReadingBedItems = readingBedItems.filter { item in
                    let destination = readingBedsRoot.appendingPathComponent(item.relativePath)
                    return !fileManager.fileExists(atPath: destination.path)
                }
            } else {
                pendingReadingBedItems = []
            }

            var completed = 0
            var totalBytes: Int64 = 0
            let totalFiles = items.count + pendingReadingBedItems.count
            if let readingBedsRoot {
                for item in pendingReadingBedItems {
                    if Task.isCancelled { throw CancellationError() }
                    let fileBytes = try await download(item: item, to: readingBedsRoot)
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
            }
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
            var readingBedsFileForManifest: String? = nil
            if let readingBeds, let readingBedsRoot {
                let readingBedsData = try encoder.encode(readingBeds)
                let readingBedsURL = readingBedsRoot.appendingPathComponent(readingBedsFileName)
                try readingBedsData.write(to: readingBedsURL, options: .atomic)
            } else if let readingBeds {
                let readingBedsURL = itemRoot.appendingPathComponent(readingBedsFileName)
                let readingBedsData = try encoder.encode(readingBeds)
                try readingBedsData.write(to: readingBedsURL, options: .atomic)
                readingBedsFileForManifest = readingBedsFileName
            }
            let manifest = OfflineMediaManifest(
                jobId: jobId,
                kind: kind,
                updatedAt: Date().timeIntervalSince1970,
                fileCount: totalFiles,
                totalBytes: totalBytes,
                mediaFile: mediaFileName,
                timingFile: timingName,
                readingBedsFile: readingBedsFileForManifest
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
                if url == nil {
                    print("[OfflineSync] WARNING: Could not resolve metadataPath: \(metadataPath)")
                }
                addItem(relativePath: metadataPath, url: url)
            }
            if let metadataURL = chunk.metadataURL?.nonEmptyValue {
                let url = resolver.resolvePath(jobId: jobId, relativePath: metadataURL)
                if url == nil {
                    print("[OfflineSync] WARNING: Could not resolve metadataURL: \(metadataURL)")
                }
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

    private func performSharedReadingBedSync(configuration: APIClientConfiguration) async {
        guard let root = readingBedsRootURL() else { return }
        let fileManager = FileManager.default
        defer {
            Task { @MainActor in
                readingBedTask = nil
            }
        }
        do {
            try fileManager.createDirectory(at: root, withIntermediateDirectories: true)
            let client = APIClient(configuration: configuration)
            let readingBeds = try? await client.fetchReadingBeds()
            let items = collectReadingBedItems(
                readingBeds: readingBeds,
                apiBaseURL: configuration.apiBaseURL,
                jobId: "shared"
            )
            for item in items {
                if Task.isCancelled { break }
                let destination = root.appendingPathComponent(item.relativePath)
                if fileManager.fileExists(atPath: destination.path) {
                    continue
                }
                _ = try await download(item: item, to: root)
            }
            if let readingBeds {
                let data = try encoder.encode(readingBeds)
                let url = root.appendingPathComponent(readingBedsFileName)
                try data.write(to: url, options: .atomic)
            }
        } catch {
            return
        }
    }

    private func collectReadingBedItems(
        readingBeds: ReadingBedListResponse?,
        apiBaseURL: URL,
        jobId: String
    ) -> [DownloadItem] {
        var paths: [String] = readingBeds?.beds.map { $0.url } ?? []
        if !paths.contains(defaultReadingBedPath) {
            paths.append(defaultReadingBedPath)
        }
        var items: [DownloadItem] = []
        var seen: Set<String> = []
        for rawPath in paths {
            guard let relativePath = normalizeReadingBedPath(rawPath, jobId: jobId) else { continue }
            guard !seen.contains(relativePath) else { continue }
            guard let url = resolveReadingBedRemoteURL(rawPath: rawPath, apiBaseURL: apiBaseURL) else { continue }
            seen.insert(relativePath)
            items.append(DownloadItem(relativePath: relativePath, url: url))
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
        if let range = path.range(of: "/assets/reading-beds/") {
            return String(path[range.lowerBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        }
        if let range = path.range(of: "/reading-beds/") {
            let suffix = String(path[range.lowerBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            return suffix.hasPrefix("assets/") ? suffix : "assets/\(suffix)"
        }
        if let range = path.range(of: "/media/") {
            return String(path[range.lowerBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        }
        if let range = path.range(of: "/metadata/") {
            return String(path[range.lowerBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        }
        let trimmedPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        if trimmedPath.hasPrefix("assets/reading-beds/") {
            return trimmedPath
        }
        if trimmedPath.hasPrefix("reading-beds/") {
            return "assets/\(trimmedPath)"
        }
        if trimmedPath.hasPrefix("media/") || trimmedPath.hasPrefix("metadata/") {
            return trimmedPath
        }
        if let fileName = trimmedPath.split(separator: "/").last {
            return "media/\(fileName)"
        }
        return nil
    }

    private func normalizeReadingBedPath(_ raw: String, jobId: String) -> String? {
        if let normalized = normalizeRelativePath(raw, jobId: jobId),
           normalized.contains("reading-beds") {
            return normalized
        }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let normalized = trimmed.replacingOccurrences(of: "\\", with: "/")
        let path = URL(string: normalized)?.path ?? normalized
        let trimmedPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard let fileName = trimmedPath.split(separator: "/").last else { return nil }
        return "assets/reading-beds/\(fileName)"
    }

    private static func normalizeSharedReadingBedPath(_ raw: String) -> String? {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
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

    private func resolveReadingBedRemoteURL(rawPath: String, apiBaseURL: URL) -> URL? {
        let trimmed = rawPath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if let url = URL(string: trimmed), url.scheme != nil {
            return url
        }
        var components = URLComponents(url: apiBaseURL, resolvingAgainstBaseURL: false) ?? URLComponents()
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
        return components.url ?? apiBaseURL.appendingPathComponent(suffix)
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
