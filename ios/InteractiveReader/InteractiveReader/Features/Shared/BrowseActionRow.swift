import Foundation
import SwiftUI

struct BrowseActionRow: View {
    let iCloudStatus: PlaybackICloudStatus
    let resumeUserId: String?
    let isLoading: Bool
    let usesDarkListBackground: Bool
    let onRefresh: () -> Void
    let onSignOut: () -> Void
    var onSync: (() -> Void)? = nil

    private var userLabel: String {
        resumeUserId ?? "Log In"
    }

    private var statusLabel: String {
        iCloudStatus.isAvailable ? "Online" : "Offline"
    }

    private var iconSize: CGFloat {
        PlatformMetrics.listIconSize
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ViewThatFits(in: .horizontal) {
                topRow(showsUserLabel: true)
                topRow(showsUserLabel: false)
            }

            HStack(spacing: 10) {
                cloudStatusLabel
                syncButton
                refreshButton
                Spacer(minLength: 0)
            }
        }
        .padding(.horizontal)
        #if os(tvOS)
        .font(PlatformTypography.sectionHeaderFont)
        #endif
    }

    private func topRow(showsUserLabel: Bool) -> some View {
        HStack(alignment: .center, spacing: 12) {
            brandLabel
            Spacer(minLength: 12)
            accountMenu(showsUserLabel: showsUserLabel)
        }
    }

    private var brandLabel: some View {
        HStack(spacing: 8) {
            Image(systemName: "globe")
                .font(.system(size: iconSize, weight: .semibold))
                .foregroundStyle(usesDarkListBackground ? .cyan : .blue)
            VStack(alignment: .leading, spacing: 2) {
                Text("Language Tools")
                    .lineLimit(1)
                    .truncationMode(.tail)
                    .foregroundStyle(usesDarkListBackground ? .white : .primary)
                    .fixedSize(horizontal: true, vertical: false)
                    .accessibilityIdentifier("browseActionBrandLabel")
                AppVersionBadge(compact: true, usesDarkBackground: usesDarkListBackground)
            }
        }
        .fixedSize(horizontal: true, vertical: false)
        .layoutPriority(20)
    }

    private var cloudStatusLabel: some View {
        HStack(spacing: 6) {
            Image(systemName: iCloudStatus.isAvailable ? "icloud" : "icloud.slash")
                .font(.system(size: iconSize, weight: .semibold))
            Text(statusLabel)
                .font(.caption.weight(.semibold))
                .lineLimit(1)
        }
        .foregroundStyle(cloudStatusColor)
        .fixedSize(horizontal: true, vertical: false)
        .accessibilityLabel(statusLabel)
    }

    @ViewBuilder
    private var syncButton: some View {
        if let onSync {
            Button(action: onSync) {
                Image(systemName: "arrow.triangle.2.circlepath")
            }
            .disabled(resumeUserId == nil || isLoading)
            .accessibilityLabel("Sync resume positions")
            .tint(usesDarkListBackground ? .white : nil)
        }
    }

    private var cloudStatusColor: Color {
        if iCloudStatus.isAvailable {
            return usesDarkListBackground ? .cyan : .blue
        }
        return usesDarkListBackground ? .white.opacity(0.6) : .secondary
    }

    private var refreshButton: some View {
        Button(action: onRefresh) {
            Image(systemName: "arrow.clockwise")
        }
        .disabled(isLoading)
        .accessibilityLabel("Refresh")
        .tint(usesDarkListBackground ? .white : nil)
    }

    private func accountMenu(showsUserLabel: Bool) -> some View {
        Menu {
            if let onSync {
                Button(action: onSync) {
                    Label("Sync Resume Positions", systemImage: "arrow.triangle.2.circlepath")
                }
                .disabled(resumeUserId == nil || isLoading)
            }
            Button("Log Out", action: onSignOut)
        } label: {
            HStack(spacing: 6) {
                Image(systemName: "person.crop.circle")
                if showsUserLabel {
                    Text(userLabel)
                        .lineLimit(1)
                        .truncationMode(.middle)
                }
            }
        }
        .tint(usesDarkListBackground ? .white : nil)
        .accessibilityLabel(userLabel)
    }
}

struct BrowseListRowFrameCapture: View {
    let coordinateSpaceName: String

    var body: some View {
        #if os(iOS)
        GeometryReader { proxy in
            Color.clear.preference(
                key: BrowseListRowFramePreferenceKey.self,
                value: [proxy.frame(in: .named(coordinateSpaceName))]
            )
        }
        #else
        Color.clear
        #endif
    }
}

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

extension View {
    @ViewBuilder
    func browseListCollapseInteraction(
        rowFrames: Binding<[CGRect]>,
        coordinateSpaceName: String,
        onCollapse: (() -> Void)?
    ) -> some View {
        #if os(iOS)
        self
            .coordinateSpace(name: coordinateSpaceName)
            .onPreferenceChange(BrowseListRowFramePreferenceKey.self) { frames in
                rowFrames.wrappedValue = frames
            }
            .simultaneousGesture(
                DragGesture(minimumDistance: 24, coordinateSpace: .named(coordinateSpaceName))
                    .onEnded { value in
                        handleBrowseListCollapseDrag(
                            value,
                            rowFrames: rowFrames.wrappedValue,
                            onCollapse: onCollapse
                        )
                    }
            )
        #else
        self
        #endif
    }

    #if os(iOS)
    private func handleBrowseListCollapseDrag(
        _ value: DragGesture.Value,
        rowFrames: [CGRect],
        onCollapse: (() -> Void)?
    ) {
        guard let onCollapse else { return }
        let start = value.startLocation
        guard !rowFrames.contains(where: { $0.contains(start) }) else { return }
        let horizontal = value.translation.width
        let vertical = value.translation.height
        guard abs(horizontal) > abs(vertical) else { return }
        guard horizontal < -70 else { return }
        guard abs(vertical) < 50 else { return }
        onCollapse()
    }
    #endif
}

#if os(iOS)
private struct BrowseListRowFramePreferenceKey: PreferenceKey {
    static var defaultValue: [CGRect] = []

    static func reduce(value: inout [CGRect], nextValue: () -> [CGRect]) {
        value.append(contentsOf: nextValue())
    }
}
#endif
