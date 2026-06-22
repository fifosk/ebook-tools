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
        let cloudEntry = availability.hasCloud ? availability.cloudEntry : nil
        guard let cloudEntry else {
            return .none()
        }
        return .cloud(label: resumeLabel(prefix: "C", entry: cloudEntry))
    }

    static func menuLabel(
        for jobId: String,
        availabilityByJobID: [String: PlaybackResumeAvailability]
    ) -> String {
        guard let availability = availabilityByJobID[jobId] else {
            return "Resume"
        }
        let entry = availability.cloudEntry ?? availability.localEntry
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

    static func refreshedSnapshot(for userId: String?, aliases: [String]) async -> BrowseResumeSnapshot {
        guard let userId else {
            await PlaybackResumeStore.shared.refreshCloudEntries(userId: "anonymous")
            return BrowseResumeSnapshot(
                availabilityByJobID: [:],
                iCloudStatus: PlaybackResumeStore.shared.iCloudStatus()
            )
        }
        await PlaybackResumeStore.shared.refreshCloudEntries(userId: userId, aliases: aliases)
        return snapshot(for: userId)
    }
}
