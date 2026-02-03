import SwiftUI

struct OfflineSyncBadge: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var offlineStore: OfflineMediaStore

    let jobId: String
    let kind: OfflineMediaStore.OfflineMediaKind
    let isEligible: Bool

    @State private var showRemovePrompt = false

    var body: some View {
        #if os(tvOS)
        EmptyView()
        #else
        Menu {
            if status.isSynced {
                Button("Remove offline copy", role: .destructive) {
                    showRemovePrompt = true
                }
            } else if status.isSyncing {
                Text("Syncing...")
            } else {
                Button("Download with dictionary cache") {
                    startSync(includeLookupCache: true)
                }
                Button("Download without dictionary cache") {
                    startSync(includeLookupCache: false)
                }
            }
            if status.errorMessage != nil {
                Button("Retry download") {
                    startSync(includeLookupCache: true)
                }
            }
        } label: {
            syncLabel
        }
        .disabled(!isEligible || !offlineStore.isAvailable || appState.configuration == nil)
        .confirmationDialog("Remove offline copy?", isPresented: $showRemovePrompt) {
            Button("Remove offline copy", role: .destructive) {
                offlineStore.remove(jobId: jobId, kind: kind)
            }
        } message: {
            Text("This will delete the locally stored media from iCloud Drive.")
        }
        #endif
    }

    private var status: OfflineMediaStore.SyncStatus {
        offlineStore.status(for: jobId, kind: kind)
    }

    private var syncLabel: some View {
        let iconName: String
        if !offlineStore.isAvailable {
            iconName = "icloud.slash"
        } else if status.isSynced {
            iconName = "checkmark.circle.fill"
        } else if status.isSyncing {
            iconName = "arrow.triangle.2.circlepath"
        } else if status.errorMessage != nil {
            iconName = "exclamationmark.triangle.fill"
        } else {
            iconName = "icloud.and.arrow.down"
        }

        return ZStack {
            if let progress = status.progress {
                ProgressView(value: progress)
                    .progressViewStyle(.circular)
                Text(progressLabel(progress))
                    .font(.system(size: 9, weight: .semibold, design: .rounded))
                    .monospacedDigit()
            } else {
                Image(systemName: iconName)
                    .font(.system(size: 18, weight: .semibold))
            }
        }
        .frame(width: 28, height: 28)
        .foregroundStyle(labelColor)
        .accessibilityLabel(accessibilityLabel)
    }

    private var labelColor: Color {
        if status.isSynced {
            return .green
        }
        if status.errorMessage != nil {
            return .orange
        }
        return .secondary
    }

    private var accessibilityLabel: String {
        if !offlineStore.isAvailable {
            return "iCloud Drive unavailable"
        }
        if status.isSynced {
            return "Offline copy available"
        }
        if status.isSyncing, let progress = status.progress {
            return "Syncing offline copy \(progressLabel(progress))"
        }
        if status.isSyncing {
            return "Syncing offline copy"
        }
        if status.errorMessage != nil {
            return "Offline download failed"
        }
        return "Download for offline"
    }

    private func progressLabel(_ progress: Double) -> String {
        let clamped = min(max(progress, 0), 1)
        let percent = Int((clamped * 100).rounded())
        return "\(percent)%"
    }

    private func startSync(includeLookupCache: Bool = true) {
        guard isEligible else { return }
        guard let configuration = appState.configuration else { return }
        offlineStore.sync(jobId: jobId, kind: kind, configuration: configuration, includeLookupCache: includeLookupCache)
    }
}
