import CloudKit
import Foundation

enum PlaybackResumeKind: String, Codable {
    case sentence
    case time
}

struct PlaybackResumeEntry: Codable, Equatable {
    let jobId: String
    let itemType: String
    let kind: PlaybackResumeKind
    let updatedAt: TimeInterval
    let sentenceNumber: Int?
    let playbackTime: Double?

    var isMeaningful: Bool {
        switch kind {
        case .sentence:
            return (sentenceNumber ?? 0) > 1
        case .time:
            return (playbackTime ?? 0) > 5
        }
    }
}

struct PlaybackResumeAvailability: Equatable {
    let localEntry: PlaybackResumeEntry?
    let cloudEntry: PlaybackResumeEntry?
    let isICloudAvailable: Bool

    var hasLocal: Bool {
        localEntry?.isMeaningful == true
    }

    var hasCloud: Bool {
        cloudEntry?.isMeaningful == true
    }
}

struct PlaybackICloudStatus: Equatable {
    let isAvailable: Bool
    let lastSyncAttempt: TimeInterval?
}

struct PlaybackICloudDebugInfo: Equatable {
    let isAvailable: Bool
    let accountStatusLabel: String
    let lastSyncAttempt: TimeInterval?
    let lastSyncSuccess: Bool?
    let recordCount: Int
    let pendingUploadCount: Int
    let pendingDeleteCount: Int
    let containerIdentifier: String?
    let bundleIdentifier: String?
    let recordType: String
    let lastError: String?
}

final class PlaybackResumeStore {
    static let shared = PlaybackResumeStore()
    static let didChangeNotification = Notification.Name("PlaybackResumeStore.didChange")

    private let localStore = UserDefaults.standard
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()
    private let containerIdentifier = "iCloud.com.ebook-tools.interactivereader"
    private let recordType = "ResumeEntry"
    private let pendingUploadPrefix = "resume.pending.upload."
    private let pendingDeletePrefix = "resume.pending.delete."
    private let syncDebounceDelay: UInt64 = 1_200_000_000
    private lazy var cloudContainer = CKContainer(identifier: containerIdentifier)
    private lazy var cloudDatabase = cloudContainer.privateCloudDatabase
    private var cloudCache: [String: PlaybackResumeEntry] = [:]
    private var lastCloudUserId: String?
    private var cloudAccountStatus: CKAccountStatus?
    private var lastCloudSyncAttempt: TimeInterval?
    private var lastCloudSyncSucceeded: Bool?
    private var lastCloudError: String?
    private var syncTask: Task<Void, Never>?
    private var queuedSyncUserId: String?
    private var syncInFlight = false

    /// API client configuration for backend resume sync.
    private var apiConfiguration: APIClientConfiguration?

    private init() {}

    /// Set the API configuration for backend resume position sync.
    func configureAPI(_ configuration: APIClientConfiguration?) {
        apiConfiguration = configuration
    }

    func entry(for jobId: String, userId: String) -> PlaybackResumeEntry? {
        let canonicalUserKey = canonicalUserId(userId)
        return cloudEntries(for: canonicalUserKey)[jobId]
    }

    func availability(for jobId: String, userId: String) -> PlaybackResumeAvailability {
        let canonicalUserKey = canonicalUserId(userId)
        let cloudEntry = cloudEntries(for: canonicalUserKey)[jobId]
        return PlaybackResumeAvailability(
            localEntry: nil,
            cloudEntry: cloudEntry,
            isICloudAvailable: isCloudAvailable
        )
    }

    func availabilitySnapshot(for userId: String) -> [String: PlaybackResumeAvailability] {
        let canonicalUserKey = canonicalUserId(userId)
        let cloudEntries = cloudEntries(for: canonicalUserKey)
        let jobIds = Set(cloudEntries.keys)
        var snapshot: [String: PlaybackResumeAvailability] = [:]
        snapshot.reserveCapacity(jobIds.count)
        for jobId in jobIds {
            snapshot[jobId] = PlaybackResumeAvailability(
                localEntry: nil,
                cloudEntry: cloudEntries[jobId],
                isICloudAvailable: isCloudAvailable
            )
        }
        return snapshot
    }

    func refreshCloudEntries(userId: String, aliases: [String] = []) async {
        let canonicalUserKey = canonicalUserId(userId)
        let aliasSet = Set(aliases.map { canonicalUserId($0) }.filter { !$0.isEmpty }).union([canonicalUserKey])
        lastCloudSyncAttempt = Date().timeIntervalSince1970
        if lastCloudUserId != canonicalUserKey {
            cloudCache = [:]
            lastCloudUserId = canonicalUserKey
        }
        await updateAccountStatus()
        let hasPending = !loadPendingUploads(for: canonicalUserKey).isEmpty || !loadPendingDeletes(for: canonicalUserKey).isEmpty
        guard isCloudAvailable else {
            lastCloudSyncSucceeded = false
            return
        }
        if hasPending {
            await runSync(userId: canonicalUserKey)
        }
        let pendingUploads = loadPendingUploads(for: canonicalUserKey)
        let pendingDeletes = loadPendingDeletes(for: canonicalUserKey)
        let shouldMarkSyncSuccess = pendingUploads.isEmpty && pendingDeletes.isEmpty
        do {
            let records = try await fetchResumeRecords(userIds: Array(aliasSet))
            var refreshed: [String: PlaybackResumeEntry] = [:]
            refreshed.reserveCapacity(records.count)
            for record in records {
                if let entry = entry(from: record, userId: canonicalUserKey) {
                    if let existing = refreshed[entry.jobId] {
                        if entry.updatedAt > existing.updatedAt {
                            refreshed[entry.jobId] = entry
                        }
                    } else {
                        refreshed[entry.jobId] = entry
                    }
                }
            }
            if !pendingUploads.isEmpty {
                for (jobId, entry) in pendingUploads {
                    if let existing = refreshed[jobId] {
                        if entry.updatedAt > existing.updatedAt {
                            refreshed[jobId] = entry
                        }
                    } else {
                        refreshed[jobId] = entry
                    }
                }
            }
            if !pendingDeletes.isEmpty {
                for jobId in pendingDeletes {
                    refreshed.removeValue(forKey: jobId)
                }
            }
            cloudCache = refreshed
            if shouldMarkSyncSuccess {
                lastCloudSyncSucceeded = true
                lastCloudError = nil
            }
        } catch {
            lastCloudSyncSucceeded = false
            lastCloudError = error.localizedDescription
        }
    }

    /// Fetch resume position for a specific job from the backend API and merge into cache.
    func refreshFromAPI(jobId: String, itemType: String) async {
        guard let config = apiConfiguration else { return }
        let client = APIClient(configuration: config)
        do {
            guard let response = try await client.fetchResumePosition(jobId: jobId) else { return }
            guard let apiEntry = response.entry else { return }
            let entry = PlaybackResumeEntry(
                jobId: apiEntry.jobId,
                itemType: itemType,
                kind: PlaybackResumeKind(rawValue: apiEntry.kind) ?? .time,
                updatedAt: apiEntry.updatedAt,
                sentenceNumber: apiEntry.sentence,
                playbackTime: apiEntry.position
            )
            guard entry.isMeaningful else { return }
            // Only apply if newer than what we already have.
            if let existing = cloudCache[jobId], existing.updatedAt >= entry.updatedAt {
                return
            }
            cloudCache[jobId] = entry
            notifyChange(userId: lastCloudUserId ?? "")
        } catch {
            // API unavailable — rely on CloudKit data only.
        }
    }

    func iCloudStatus() -> PlaybackICloudStatus {
        PlaybackICloudStatus(
            isAvailable: isCloudAvailable,
            lastSyncAttempt: lastCloudSyncAttempt
        )
    }

    func debugInfo(for userId: String?) -> PlaybackICloudDebugInfo {
        let pendingUploads = userId.map { loadPendingUploads(for: $0).count } ?? 0
        let pendingDeletes = userId.map { loadPendingDeletes(for: $0).count } ?? 0
        return PlaybackICloudDebugInfo(
            isAvailable: isCloudAvailable,
            accountStatusLabel: accountStatusLabel(cloudAccountStatus),
            lastSyncAttempt: lastCloudSyncAttempt,
            lastSyncSuccess: lastCloudSyncSucceeded,
            recordCount: cloudCache.count,
            pendingUploadCount: pendingUploads,
            pendingDeleteCount: pendingDeletes,
            containerIdentifier: cloudContainer.containerIdentifier,
            bundleIdentifier: Bundle.main.bundleIdentifier,
            recordType: recordType,
            lastError: lastCloudError
        )
    }

    func updateEntry(_ entry: PlaybackResumeEntry, userId: String) {
        let canonicalUserKey = canonicalUserId(userId)
        ensureUserContext(canonicalUserKey)
        cloudCache[entry.jobId] = entry
        queuePendingUpload(entry, userId: canonicalUserKey)
        scheduleSync(userId: canonicalUserKey)
        saveToAPI(entry)
        notifyChange(userId: canonicalUserKey)
    }

    func clearEntry(jobId: String, userId: String) {
        let canonicalUserKey = canonicalUserId(userId)
        ensureUserContext(canonicalUserKey)
        cloudCache.removeValue(forKey: jobId)
        queuePendingDelete(jobId: jobId, userId: canonicalUserKey)
        scheduleSync(userId: canonicalUserKey)
        deleteFromAPI(jobId: jobId)
        notifyChange(userId: canonicalUserKey)
    }

    func syncNow(userId: String, aliases: [String] = []) async {
        let canonicalUserKey = canonicalUserId(userId)
        syncTask?.cancel()
        syncTask = nil
        queuedSyncUserId = nil
        await runSync(userId: canonicalUserKey)
        await refreshCloudEntries(userId: canonicalUserKey, aliases: aliases)
    }

    private var isCloudAvailable: Bool {
        cloudAccountStatus == .available
    }

    private func pendingUploadStorageKey(for userId: String) -> String {
        "\(pendingUploadPrefix)\(normalizedUserKey(userId))"
    }

    private func pendingDeleteStorageKey(for userId: String) -> String {
        "\(pendingDeletePrefix)\(normalizedUserKey(userId))"
    }

    private func loadPendingUploads(for userId: String) -> [String: PlaybackResumeEntry] {
        let key = pendingUploadStorageKey(for: userId)
        guard let data = localStore.data(forKey: key) else { return [:] }
        return (try? decoder.decode([String: PlaybackResumeEntry].self, from: data)) ?? [:]
    }

    private func persistPendingUploads(_ entries: [String: PlaybackResumeEntry], for userId: String) {
        guard let data = try? encoder.encode(entries) else { return }
        localStore.set(data, forKey: pendingUploadStorageKey(for: userId))
    }

    private func loadPendingDeletes(for userId: String) -> Set<String> {
        let key = pendingDeleteStorageKey(for: userId)
        guard let data = localStore.data(forKey: key) else { return [] }
        let values = (try? decoder.decode([String].self, from: data)) ?? []
        return Set(values)
    }

    private func persistPendingDeletes(_ entries: Set<String>, for userId: String) {
        let values = Array(entries)
        guard let data = try? encoder.encode(values) else { return }
        localStore.set(data, forKey: pendingDeleteStorageKey(for: userId))
    }

    private func normalizedUserKey(_ raw: String) -> String {
        let allowed = Set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._")
        let mapped = raw.map { allowed.contains($0) ? $0 : "_" }
        let cleaned = String(mapped).trimmingCharacters(in: .whitespacesAndNewlines)
        if cleaned.count <= 48 {
            return cleaned
        }
        let index = cleaned.index(cleaned.startIndex, offsetBy: 48)
        return String(cleaned[..<index])
    }

    private func ensureUserContext(_ userId: String) {
        if lastCloudUserId != userId {
            cloudCache = [:]
            lastCloudUserId = userId
        }
    }

    private func cloudEntries(for userId: String) -> [String: PlaybackResumeEntry] {
        guard lastCloudUserId == userId else { return [:] }
        return cloudCache
    }

    private func canonicalUserId(_ raw: String) -> String {
        raw.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }

    private func updateAccountStatus() async {
        do {
            cloudAccountStatus = try await cloudContainer.accountStatus()
        } catch {
            cloudAccountStatus = nil
            lastCloudError = error.localizedDescription
        }
    }

    private func fetchResumeRecords(userIds: [String]) async throws -> [CKRecord] {
        let cleaned = userIds.filter { !$0.isEmpty }
        let predicate: NSPredicate
        if cleaned.count > 1 {
            predicate = NSPredicate(format: "userId IN %@", cleaned)
        } else if let userId = cleaned.first {
            predicate = NSPredicate(format: "userId == %@", userId)
        } else {
            predicate = NSPredicate(value: false)
        }
        let query = CKQuery(recordType: recordType, predicate: predicate)
        var records: [CKRecord] = []
        var cursor: CKQueryOperation.Cursor?
        repeat {
            let operation: CKQueryOperation
            if let cursor {
                operation = CKQueryOperation(cursor: cursor)
            } else {
                operation = CKQueryOperation(query: query)
            }
            operation.resultsLimit = 200
            let (batch, nextCursor) = try await runQuery(operation)
            records.append(contentsOf: batch)
            cursor = nextCursor
        } while cursor != nil
        return records
    }

    private func scheduleSync(userId: String) {
        queuedSyncUserId = userId
        guard syncTask == nil else { return }
        let delay = syncDebounceDelay
        syncTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: delay)
            guard let self else { return }
            guard !Task.isCancelled else { return }
            let targetUserId = self.queuedSyncUserId ?? userId
            self.queuedSyncUserId = nil
            await self.runSync(userId: targetUserId)
            self.syncTask = nil
            if let nextUserId = self.queuedSyncUserId {
                self.scheduleSync(userId: nextUserId)
            }
        }
    }

    private func runSync(userId: String) async {
        while syncInFlight {
            try? await Task.sleep(nanoseconds: 200_000_000)
        }
        syncInFlight = true
        defer { syncInFlight = false }
        await syncPendingEntries(userId: userId)
    }

    private func syncPendingEntries(userId: String) async {
        lastCloudSyncAttempt = Date().timeIntervalSince1970
        await updateAccountStatus()
        guard isCloudAvailable else {
            lastCloudSyncSucceeded = false
            return
        }
        var pendingUploads = loadPendingUploads(for: userId)
        var pendingDeletes = loadPendingDeletes(for: userId)
        var didFail = false

        if !pendingDeletes.isEmpty {
            for jobId in pendingDeletes.sorted() {
                do {
                    try await deleteCloudEntry(jobId: jobId, userId: userId)
                    pendingDeletes.remove(jobId)
                    cloudCache.removeValue(forKey: jobId)
                } catch {
                    didFail = true
                    lastCloudError = error.localizedDescription
                    break
                }
            }
        }

        if !didFail && !pendingUploads.isEmpty {
            let entries = pendingUploads.values.sorted { $0.updatedAt < $1.updatedAt }
            for entry in entries {
                do {
                    if let savedEntry = try await saveCloudEntry(entry, userId: userId) {
                        cloudCache[savedEntry.jobId] = savedEntry
                    }
                    pendingUploads.removeValue(forKey: entry.jobId)
                } catch {
                    didFail = true
                    lastCloudError = error.localizedDescription
                    break
                }
            }
        }

        persistPendingUploads(pendingUploads, for: userId)
        persistPendingDeletes(pendingDeletes, for: userId)
        if didFail {
            lastCloudSyncSucceeded = false
        } else {
            lastCloudSyncSucceeded = true
            lastCloudError = nil
        }
        notifyChange(userId: userId)
    }

    private func saveCloudEntry(_ entry: PlaybackResumeEntry, userId: String) async throws -> PlaybackResumeEntry? {
        let record = makeRecord(for: entry, userId: userId)
        let saved = try await cloudDatabase.save(record)
        return self.entry(from: saved, userId: userId)
    }

    private func deleteCloudEntry(jobId: String, userId: String) async throws {
        let recordID = CKRecord.ID(recordName: recordName(for: jobId, userId: userId))
        _ = try await cloudDatabase.deleteRecord(withID: recordID)
    }

    private func queuePendingUpload(_ entry: PlaybackResumeEntry, userId: String) {
        var pendingUploads = loadPendingUploads(for: userId)
        pendingUploads[entry.jobId] = entry
        persistPendingUploads(pendingUploads, for: userId)
        var pendingDeletes = loadPendingDeletes(for: userId)
        if pendingDeletes.contains(entry.jobId) {
            pendingDeletes.remove(entry.jobId)
            persistPendingDeletes(pendingDeletes, for: userId)
        }
    }

    private func queuePendingDelete(jobId: String, userId: String) {
        var pendingUploads = loadPendingUploads(for: userId)
        if pendingUploads.removeValue(forKey: jobId) != nil {
            persistPendingUploads(pendingUploads, for: userId)
        }
        var pendingDeletes = loadPendingDeletes(for: userId)
        pendingDeletes.insert(jobId)
        persistPendingDeletes(pendingDeletes, for: userId)
    }

    private func notifyChange(userId: String) {
        let payload: [String: String] = ["userId": userId]
        if Thread.isMainThread {
            NotificationCenter.default.post(
                name: Self.didChangeNotification,
                object: nil,
                userInfo: payload
            )
        } else {
            DispatchQueue.main.async {
                NotificationCenter.default.post(
                    name: Self.didChangeNotification,
                    object: nil,
                    userInfo: payload
                )
            }
        }
    }

    // MARK: - Backend API Sync

    private func saveToAPI(_ entry: PlaybackResumeEntry) {
        guard let config = apiConfiguration else { return }
        Task {
            let client = APIClient(configuration: config)
            let payload = ResumePositionSaveRequest(
                kind: entry.kind.rawValue,
                position: entry.playbackTime,
                sentence: entry.sentenceNumber,
                chunkId: nil,
                mediaType: entry.kind == .time ? "video" : "text",
                baseId: nil
            )
            _ = try? await client.saveResumePosition(jobId: entry.jobId, payload: payload)
        }
    }

    private func deleteFromAPI(jobId: String) {
        guard let config = apiConfiguration else { return }
        Task {
            let client = APIClient(configuration: config)
            _ = try? await client.deleteResumePosition(jobId: jobId)
        }
    }

    private func recordName(for jobId: String, userId: String) -> String {
        let userKey = normalizedUserKey(userId)
        return "resume-\(userKey)-\(jobId)"
    }

    private func makeRecord(for entry: PlaybackResumeEntry, userId: String) -> CKRecord {
        let recordID = CKRecord.ID(recordName: recordName(for: entry.jobId, userId: userId))
        let record = CKRecord(recordType: recordType, recordID: recordID)
        record["jobId"] = entry.jobId as CKRecordValue
        record["itemType"] = entry.itemType as CKRecordValue
        record["kind"] = entry.kind.rawValue as CKRecordValue
        record["updatedAt"] = Date(timeIntervalSince1970: entry.updatedAt)
        record["userId"] = userId as CKRecordValue
        if let sentence = entry.sentenceNumber {
            record["sentenceNumber"] = sentence as CKRecordValue
        }
        if let time = entry.playbackTime {
            record["playbackTime"] = time as CKRecordValue
        }
        return record
    }

    private func entry(from record: CKRecord, userId: String?) -> PlaybackResumeEntry? {
        let jobId = (record["jobId"] as? String).flatMap { $0.nonEmptyValue }
            ?? recordJobIdFallback(record, userId: userId)
        guard let jobId else { return nil }
        let itemType = (record["itemType"] as? String).flatMap { $0.nonEmptyValue } ?? "book"
        let kindRaw = (record["kind"] as? String).flatMap { $0.nonEmptyValue } ?? PlaybackResumeKind.sentence.rawValue
        let kind = PlaybackResumeKind(rawValue: kindRaw) ?? .sentence
        let updatedAt: TimeInterval = {
            if let date = record["updatedAt"] as? Date {
                return date.timeIntervalSince1970
            }
            if let modDate = record.modificationDate {
                return modDate.timeIntervalSince1970
            }
            return Date().timeIntervalSince1970
        }()
        let sentenceNumber = record["sentenceNumber"] as? Int
            ?? (record["sentenceNumber"] as? NSNumber)?.intValue
        let playbackTime = record["playbackTime"] as? Double
            ?? (record["playbackTime"] as? NSNumber)?.doubleValue
        return PlaybackResumeEntry(
            jobId: jobId,
            itemType: itemType,
            kind: kind,
            updatedAt: updatedAt,
            sentenceNumber: sentenceNumber,
            playbackTime: playbackTime
        )
    }

    private func recordJobIdFallback(_ record: CKRecord, userId: String?) -> String? {
        let recordName = record.recordID.recordName
        if let userId {
            let prefix = "resume-\(normalizedUserKey(userId))-"
            if recordName.hasPrefix(prefix) {
                let start = recordName.index(recordName.startIndex, offsetBy: prefix.count)
                return String(recordName[start...]).nonEmptyValue
            }
        }
        if recordName.hasPrefix("resume-") {
            let trimmed = recordName.replacingOccurrences(of: "resume-", with: "")
            return trimmed.nonEmptyValue
        }
        return recordName.nonEmptyValue
    }

    private func accountStatusLabel(_ status: CKAccountStatus?) -> String {
        guard let status else {
            return "unknown"
        }
        switch status {
        case .available:
            return "available"
        case .noAccount:
            return "no account"
        case .restricted:
            return "restricted"
        case .couldNotDetermine:
            return "unknown"
        default:
            return "unknown"
        }
    }

    private func runQuery(
        _ operation: CKQueryOperation
    ) async throws -> ([CKRecord], CKQueryOperation.Cursor?) {
        try await withCheckedThrowingContinuation { continuation in
            var records: [CKRecord] = []
            operation.recordMatchedBlock = { _, result in
                if case let .success(record) = result {
                    records.append(record)
                }
            }
            operation.queryResultBlock = { result in
                switch result {
                case let .success(cursor):
                    continuation.resume(returning: (records, cursor))
                case let .failure(error):
                    continuation.resume(throwing: error)
                }
            }
            cloudDatabase.add(operation)
        }
    }
}
