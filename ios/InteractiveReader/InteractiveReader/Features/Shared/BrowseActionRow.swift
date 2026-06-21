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
        HStack(spacing: 12) {
            brandLabel
            cloudStatusIcon
            syncButton
            refreshButton
            Spacer()
            accountMenu
        }
        .padding(.horizontal)
        #if os(tvOS)
        .font(PlatformTypography.sectionHeaderFont)
        #endif
    }

    private var brandLabel: some View {
        HStack(spacing: 6) {
            Image(systemName: "globe")
                .font(.system(size: iconSize, weight: .semibold))
                .foregroundStyle(usesDarkListBackground ? .cyan : .blue)
            Text("Language Tools")
                .lineLimit(1)
                .foregroundStyle(usesDarkListBackground ? .white : .primary)
            AppVersionBadge()
        }
    }

    private var cloudStatusIcon: some View {
        Image(systemName: iCloudStatus.isAvailable ? "icloud" : "icloud.slash")
            .font(.system(size: iconSize, weight: .semibold))
            .foregroundStyle(cloudStatusColor)
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

    private var accountMenu: some View {
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
                Text(userLabel)
                    .lineLimit(1)
                    .truncationMode(.middle)
            }
        }
        .tint(usesDarkListBackground ? .white : nil)
    }
}
