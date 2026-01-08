import Foundation

enum PlaybackBookmarkKind: String, Codable {
    case time
    case sentence
}

struct PlaybackBookmarkEntry: Codable, Identifiable, Equatable {
    let id: String
    let jobId: String
    let itemType: String
    let kind: PlaybackBookmarkKind
    let createdAt: TimeInterval
    let label: String
    let playbackTime: Double?
    let sentenceNumber: Int?
    let chunkId: String?
    let segmentId: String?
}

final class PlaybackBookmarkStore {
    static let shared = PlaybackBookmarkStore()
    static let didChangeNotification = Notification.Name("PlaybackBookmarkStore.didChange")

    private let localStore = UserDefaults.standard
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()
    private let maxEntries = 300

    private init() {}

    func bookmarks(for jobId: String, userId: String) -> [PlaybackBookmarkEntry] {
        let payload = loadEntriesFromLocal(for: userId)
        return payload[jobId]?.sorted { $0.createdAt > $1.createdAt } ?? []
    }

    func addBookmark(_ entry: PlaybackBookmarkEntry, userId: String) {
        var payload = loadEntriesFromLocal(for: userId)
        var entries = payload[entry.jobId] ?? []
        if entries.contains(where: { isDuplicate($0, entry) }) {
            return
        }
        entries.append(entry)
        if entries.count > maxEntries {
            entries.sort { $0.createdAt > $1.createdAt }
            entries = Array(entries.prefix(maxEntries))
        }
        payload[entry.jobId] = entries
        persistLocalEntries(payload, for: userId)
        notifyChange(userId: userId)
    }

    func removeBookmark(id: String, jobId: String, userId: String) {
        var payload = loadEntriesFromLocal(for: userId)
        guard var entries = payload[jobId] else { return }
        entries.removeAll { $0.id == id }
        if entries.isEmpty {
            payload.removeValue(forKey: jobId)
        } else {
            payload[jobId] = entries
        }
        persistLocalEntries(payload, for: userId)
        notifyChange(userId: userId)
    }

    func replaceBookmarks(_ entries: [PlaybackBookmarkEntry], jobId: String, userId: String) {
        var payload = loadEntriesFromLocal(for: userId)
        if entries.isEmpty {
            payload.removeValue(forKey: jobId)
        } else {
            payload[jobId] = entries
        }
        persistLocalEntries(payload, for: userId)
        notifyChange(userId: userId)
    }

    private func loadEntriesFromLocal(for userId: String) -> [String: [PlaybackBookmarkEntry]] {
        let key = localKey(for: userId)
        guard let data = localStore.data(forKey: key) else {
            return [:]
        }
        do {
            return try decoder.decode([String: [PlaybackBookmarkEntry]].self, from: data)
        } catch {
            return [:]
        }
    }

    private func persistLocalEntries(_ payload: [String: [PlaybackBookmarkEntry]], for userId: String) {
        let key = localKey(for: userId)
        do {
            let data = try encoder.encode(payload)
            localStore.set(data, forKey: key)
        } catch {
            return
        }
    }

    private func localKey(for userId: String) -> String {
        "bookmark.local.\(normalizedUserKey(userId))"
    }

    private func normalizedUserKey(_ userId: String) -> String {
        userId.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }

    private func notifyChange(userId: String) {
        NotificationCenter.default.post(
            name: PlaybackBookmarkStore.didChangeNotification,
            object: nil,
            userInfo: ["userId": userId]
        )
    }

    private func isDuplicate(_ existing: PlaybackBookmarkEntry, _ incoming: PlaybackBookmarkEntry) -> Bool {
        guard existing.kind == incoming.kind else { return false }
        if existing.kind == .sentence {
            return existing.sentenceNumber != nil && existing.sentenceNumber == incoming.sentenceNumber
        }
        if existing.segmentId != incoming.segmentId {
            return false
        }
        if existing.chunkId != incoming.chunkId {
            return false
        }
        guard let time = existing.playbackTime, let incomingTime = incoming.playbackTime else {
            return false
        }
        return abs(time - incomingTime) < 0.5
    }
}
