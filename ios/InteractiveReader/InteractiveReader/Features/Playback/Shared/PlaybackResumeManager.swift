import Foundation

/// Manages playback resume state and operations for both Job and Library playback views.
/// This consolidates duplicate resume logic that was previously in both views.
@MainActor
final class PlaybackResumeManager: ObservableObject {
    @Published var pendingResumeEntry: PlaybackResumeEntry?
    @Published var showResumePrompt = false
    @Published var videoResumeTime: Double?
    @Published var videoResumeActionID = UUID()
    @Published var videoAutoPlay = false
    @Published var resumeDecisionPending = false
    @Published var lastRecordedSentence: Int?
    @Published var lastRecordedTimeBucket: Int?
    @Published var lastVideoTime: Double = 0

    private let jobId: String
    private let itemType: String
    private let userId: String?
    private let userAliases: [String]

    init(jobId: String, itemType: String, userId: String?, userAliases: [String] = []) {
        self.jobId = jobId
        self.itemType = itemType
        self.userId = userId
        self.userAliases = userAliases
    }

    // MARK: - State Reset

    func resetState() {
        pendingResumeEntry = nil
        showResumePrompt = false
        videoResumeTime = nil
        videoResumeActionID = UUID()
        videoAutoPlay = false
        resumeDecisionPending = true
        lastRecordedSentence = nil
        lastRecordedTimeBucket = nil
        lastVideoTime = 0
    }

    // MARK: - Resume Entry Resolution

    func resolveResumeEntry(isVideoPreferred: Bool) -> PlaybackResumeEntry? {
        guard let userId else { return nil }
        guard let entry = PlaybackResumeStore.shared.entry(for: jobId, userId: userId) else { return nil }
        guard entry.isMeaningful else { return nil }
        if isVideoPreferred {
            return entry.kind == .time ? entry : nil
        }
        return entry.kind == .sentence ? entry : nil
    }

    func clearResumeEntry() {
        guard let userId else { return }
        PlaybackResumeStore.shared.clearEntry(jobId: jobId, userId: userId)
    }

    // MARK: - Resume Actions

    func applyResume(_ entry: PlaybackResumeEntry) {
        showResumePrompt = false
        pendingResumeEntry = nil
        resumeDecisionPending = false
    }

    func startOver() {
        showResumePrompt = false
        pendingResumeEntry = nil
        resumeDecisionPending = false
        clearResumeEntry()
    }

    func markResumeDecisionComplete() {
        resumeDecisionPending = false
    }

    // MARK: - Video Resume

    func prepareVideoResume(at time: Double?) {
        videoAutoPlay = true
        videoResumeTime = time
        videoResumeActionID = UUID()
    }

    // MARK: - Recording Resume State

    func recordInteractiveResume(sentenceIndex: Int, force: Bool = false) {
        guard !resumeDecisionPending else { return }
        guard let userId else { return }
        guard sentenceIndex > 0 else { return }
        if !force, sentenceIndex == lastRecordedSentence {
            return
        }
        lastRecordedSentence = sentenceIndex
        let entry = PlaybackResumeEntry(
            jobId: jobId,
            itemType: itemType,
            kind: .sentence,
            updatedAt: Date().timeIntervalSince1970,
            sentenceNumber: sentenceIndex,
            playbackTime: nil
        )
        PlaybackResumeStore.shared.updateEntry(entry, userId: userId)
    }

    @discardableResult
    func recordVideoResume(time: Double, isPlaying: Bool) -> Bool {
        guard !resumeDecisionPending else { return false }
        guard let userId else { return false }
        guard time.isFinite, time >= 0 else { return false }
        if !isPlaying, time < 1, lastVideoTime > 5 {
            return false
        }
        lastVideoTime = time
        let bucket = Int(time / 5)
        if bucket == lastRecordedTimeBucket, isPlaying {
            return true
        }
        lastRecordedTimeBucket = bucket
        let entry = PlaybackResumeEntry(
            jobId: jobId,
            itemType: itemType,
            kind: .time,
            updatedAt: Date().timeIntervalSince1970,
            sentenceNumber: nil,
            playbackTime: time
        )
        PlaybackResumeStore.shared.updateEntry(entry, userId: userId)
        return true
    }

    func persistOnExit(isVideoPreferred: Bool, sentenceIndex: Int?) {
        if isVideoPreferred {
            recordVideoResume(time: lastVideoTime, isPlaying: false)
        } else if let sentenceIndex {
            recordInteractiveResume(sentenceIndex: sentenceIndex, force: true)
        }
        if let userId {
            Task {
                await PlaybackResumeStore.shared.syncNow(userId: userId, aliases: userAliases)
            }
        }
    }

    func syncNow() async {
        guard let userId else { return }
        await PlaybackResumeStore.shared.syncNow(userId: userId, aliases: userAliases)
    }

    // MARK: - Prompt Message Formatting

    func resumePromptMessage(for entry: PlaybackResumeEntry) -> String {
        let iCloudNote = iCloudResumeNote()
        switch entry.kind {
        case .sentence:
            let sentence = entry.sentenceNumber ?? 1
            return "Continue from sentence \(sentence).\n\(iCloudNote)"
        case .time:
            let time = entry.playbackTime ?? 0
            return "Continue from \(formatPlaybackTime(time)).\n\(iCloudNote)"
        }
    }

    private func iCloudResumeNote() -> String {
        let status = PlaybackResumeStore.shared.iCloudStatus()
        guard status.isAvailable else { return "iCloud: unavailable" }
        if let lastSync = status.lastSyncAttempt {
            return "iCloud sync \(formatRelativeTime(lastSync))"
        }
        return "iCloud: connected"
    }

    private func formatRelativeTime(_ timestamp: TimeInterval) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .short
        let date = Date(timeIntervalSince1970: timestamp)
        return formatter.localizedString(for: date, relativeTo: Date())
    }

    private func formatPlaybackTime(_ time: Double) -> String {
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = time >= 3600 ? [.hour, .minute, .second] : [.minute, .second]
        formatter.zeroFormattingBehavior = .pad
        return formatter.string(from: time) ?? "0:00"
    }
}
