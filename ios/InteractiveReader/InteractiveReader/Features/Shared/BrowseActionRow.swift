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
