import Foundation

enum BrowseResumeStatusFormatter {
    static func hasResume(
        for jobId: String,
        availabilityByJobID: [String: PlaybackResumeAvailability]
    ) -> Bool {
        let availability = availabilityByJobID[jobId]
        return availability?.hasCloud == true || availability?.hasLocal == true
    }

    static func rowStatus(
        for jobId: String,
        availabilityByJobID: [String: PlaybackResumeAvailability]
    ) -> LibraryRowView.ResumeStatus {
        guard let availability = availabilityByJobID[jobId] else {
            return .none()
        }
        let localEntry = availability.hasLocal ? availability.localEntry : nil
        let cloudEntry = availability.hasCloud ? availability.cloudEntry : nil
        switch (localEntry, cloudEntry) {
        case let (local?, cloud?):
            return .both(label: resumeLabel(prefix: "B", entry: freshestEntry(local, cloud)))
        case let (local?, nil):
            return .local(label: resumeLabel(prefix: "L", entry: local))
        case let (nil, cloud?):
            return .cloud(label: resumeLabel(prefix: "C", entry: cloud))
        case (nil, nil):
            return .none()
        }
    }

    static func menuLabel(
        for jobId: String,
        availabilityByJobID: [String: PlaybackResumeAvailability]
    ) -> String {
        guard let availability = availabilityByJobID[jobId] else {
            return "Resume"
        }
        let entry = freshestAvailableEntry(availability)
        guard let entry else { return "Resume" }
        switch entry.kind {
        case .sentence:
            if let sentence = entry.sentenceNumber, sentence > 0 {
                return "Resume from Sentence \(sentence)"
            }
        case .time:
            if let time = entry.playbackTime, time > 0 {
                return "Resume from \(formatPlaybackTime(time))"
            }
        }
        return "Resume"
    }

    private static func resumeLabel(prefix: String, entry: PlaybackResumeEntry?) -> String {
        guard let entry else { return "\(prefix)" }
        switch entry.kind {
        case .sentence:
            if let sentence = entry.sentenceNumber, sentence > 0 {
                return "\(prefix):\(sentence)"
            }
        case .time:
            if let time = entry.playbackTime, time > 0 {
                return "\(prefix):\(formatPlaybackTime(time))"
            }
        }
        return "\(prefix)"
    }

    private static func freshestAvailableEntry(_ availability: PlaybackResumeAvailability) -> PlaybackResumeEntry? {
        let localEntry = availability.hasLocal ? availability.localEntry : nil
        let cloudEntry = availability.hasCloud ? availability.cloudEntry : nil
        switch (localEntry, cloudEntry) {
        case let (local?, cloud?):
            return freshestEntry(local, cloud)
        case let (local?, nil):
            return local
        case let (nil, cloud?):
            return cloud
        case (nil, nil):
            return nil
        }
    }

    private static func freshestEntry(
        _ first: PlaybackResumeEntry,
        _ second: PlaybackResumeEntry
    ) -> PlaybackResumeEntry {
        first.updatedAt >= second.updatedAt ? first : second
    }

    private static func formatPlaybackTime(_ time: Double) -> String {
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = time >= 3600 ? [.hour, .minute, .second] : [.minute, .second]
        formatter.zeroFormattingBehavior = .pad
        return formatter.string(from: time) ?? "0:00"
    }
}

enum BrowseResumeNotificationFilter {
    static func matches(_ notification: Notification, resumeUserId: String?) -> Bool {
        guard let resumeUserId else { return false }
        let userId = notification.userInfo?["userId"] as? String
        return userId == resumeUserId
    }
}

struct BrowseResumeSnapshot {
    let availabilityByJobID: [String: PlaybackResumeAvailability]
    let iCloudStatus: PlaybackICloudStatus
}

enum BrowseResumeSnapshotProvider {
    static func snapshot(for userId: String?) -> BrowseResumeSnapshot {
        guard let userId else {
            return BrowseResumeSnapshot(
                availabilityByJobID: [:],
                iCloudStatus: PlaybackResumeStore.shared.iCloudStatus()
            )
        }
        return BrowseResumeSnapshot(
            availabilityByJobID: PlaybackResumeStore.shared.availabilitySnapshot(for: userId),
            iCloudStatus: PlaybackResumeStore.shared.iCloudStatus()
        )
    }

    static func refreshedSnapshot(
        for userId: String?,
        aliases: [String],
        visibleItemTypesByJobID: [String: String] = [:]
    ) async -> BrowseResumeSnapshot {
        guard let userId else {
            await PlaybackResumeStore.shared.refreshCloudEntries(userId: "anonymous")
            return BrowseResumeSnapshot(
                availabilityByJobID: [:],
                iCloudStatus: PlaybackResumeStore.shared.iCloudStatus()
            )
        }
        await PlaybackResumeStore.shared.refreshCloudEntries(userId: userId, aliases: aliases)
        await PlaybackResumeStore.shared.refreshFromAPI(
            jobIds: Array(visibleItemTypesByJobID.keys),
            itemTypes: visibleItemTypesByJobID
        )
        return snapshot(for: userId)
    }
}
