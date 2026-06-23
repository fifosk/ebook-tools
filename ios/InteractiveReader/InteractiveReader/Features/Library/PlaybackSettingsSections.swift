import SwiftUI

enum BackendRuntimeState: Equatable {
    case idle
    case checking
    case verified(service: String, version: String, createContract: BackendCreateContractState)
    case unavailable(String)

    var label: String {
        switch self {
        case .idle, .checking:
            return "Checking"
        case let .verified(service, version, _):
            let serviceLabel = service.nonEmptyValue ?? "Backend"
            let versionLabel = version.nonEmptyValue ?? "unknown"
            return "\(serviceLabel) · \(versionLabel)"
        case let .unavailable(message):
            return message
        }
    }

    var systemImage: String {
        switch self {
        case .idle, .checking:
            return "arrow.triangle.2.circlepath"
        case .verified:
            return "checkmark.seal"
        case .unavailable:
            return "exclamationmark.triangle"
        }
    }

    var createContractState: BackendCreateContractState? {
        switch self {
        case let .verified(_, _, createContract):
            return createContract
        case .idle, .checking, .unavailable:
            return nil
        }
    }
}

enum BackendCreateContractState: Equatable {
    case ready(summary: String)
    case mismatch(summary: String)
    case unavailable

    var label: String {
        switch self {
        case let .ready(summary):
            return summary
        case let .mismatch(summary):
            return "Unexpected paths: \(summary)"
        case .unavailable:
            return "Unavailable on this backend"
        }
    }

    var systemImage: String {
        switch self {
        case .ready:
            return "checkmark.circle"
        case .mismatch:
            return "exclamationmark.triangle"
        case .unavailable:
            return "exclamationmark.triangle"
        }
    }
}

struct SettingsSectionHeader: View {
    let title: String
    let usesDarkBackground: Bool

    var body: some View {
        Text(title)
            .foregroundStyle(usesDarkBackground ? .white.opacity(0.72) : .secondary)
    }
}

struct SettingsConnectionSection: View {
    let apiHostLabel: String
    let backendRuntimeState: BackendRuntimeState
    let sessionLabel: String
    let usesDarkBackground: Bool

    var body: some View {
        Section {
            SettingsInfoRow(
                title: "API Host",
                value: apiHostLabel,
                systemImage: "network",
                accessibilityIdentifier: "settingsAPIHostRow"
            )

            SettingsInfoRow(
                title: "Backend Runtime",
                value: backendRuntimeState.label,
                systemImage: backendRuntimeState.systemImage,
                accessibilityIdentifier: "settingsBackendRuntimeRow"
            )

            if let createContractState = backendRuntimeState.createContractState {
                SettingsInfoRow(
                    title: "Create Contract",
                    value: createContractState.label,
                    systemImage: createContractState.systemImage,
                    accessibilityIdentifier: "settingsCreateContractRow"
                )
            }

            SettingsInfoRow(
                title: "Session",
                value: sessionLabel,
                systemImage: "person.crop.circle.badge.checkmark",
                accessibilityIdentifier: "settingsSessionRow"
            )

            SettingsInfoRow(
                title: "Token Storage",
                value: "Keychain",
                systemImage: "key",
                accessibilityIdentifier: "settingsTokenStorageRow"
            )
        } header: {
            SettingsSectionHeader(title: "Connection", usesDarkBackground: usesDarkBackground)
        }
    }
}

struct PlaybackSettingsSection: View {
    @Binding var autoScaleEnabled: Bool
    let usesDarkBackground: Bool

    var body: some View {
        Section {
            Toggle(isOn: $autoScaleEnabled) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Auto-fit transcript")
                        .foregroundStyle(.primary)
                    Text("Scale active sentences to fit the screen on rotation or font changes.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        } header: {
            SettingsSectionHeader(title: "Playback", usesDarkBackground: usesDarkBackground)
        }
    }
}

struct AppChangelogSettingsSection: View {
    let usesDarkBackground: Bool

    var body: some View {
        Section {
            changelogSummary
                .listRowInsets(EdgeInsets(top: 8, leading: 0, bottom: 8, trailing: 0))
            #if os(iOS)
                .listRowBackground(Color.clear)
            #endif
        } header: {
            SettingsSectionHeader(title: "Daily Changelog", usesDarkBackground: usesDarkBackground)
        }
    }

    private var changelogSummary: some View {
        #if os(tvOS)
        AppChangelogSummaryView(
            showBuildMetadata: true,
            usesDarkBackground: usesDarkBackground,
            maxContentHeight: 520
        )
        #else
        AppChangelogSummaryView(
            showBuildMetadata: true,
            usesDarkBackground: usesDarkBackground,
            maxContentHeight: 420
        )
        #endif
    }
}

struct VoiceSettingsSection: View {
    let usesDarkBackground: Bool

    var body: some View {
        Section {
            if hasVoiceOverrides {
                Button(role: .destructive, action: resetVoiceSettings) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Reset Voice Settings")
                            .foregroundStyle(.red)
                        Text("Clears custom TTS voice selections for all languages.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            } else {
                VStack(alignment: .leading, spacing: 4) {
                    Text("No custom voice settings")
                        .foregroundStyle(.primary)
                    Text("Custom voices selected in MyLinguist will appear here.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        } header: {
            SettingsSectionHeader(title: "Voice", usesDarkBackground: usesDarkBackground)
        }
    }

    private var hasVoiceOverrides: Bool {
        !TtsVoicePreferencesManager.shared.allVoices().isEmpty
    }

    private func resetVoiceSettings() {
        TtsVoicePreferencesManager.shared.clearAllVoices()
    }
}

#if os(iOS)
struct NotificationSettingsSection: View {
    @ObservedObject var notificationManager: NotificationManager
    let isRequestingPermission: Bool
    let isSendingTestNotification: Bool
    let isSendingRichTestNotification: Bool
    let requestNotificationPermission: () -> Void
    let sendTestNotification: () -> Void
    let sendRichTestNotification: () -> Void
    let usesDarkBackground: Bool

    var body: some View {
        Section {
            if notificationManager.isAuthorized {
                Toggle(isOn: $notificationManager.notificationsEnabled) {
                    SettingsRowText(
                        title: "Job Notifications",
                        detail: "Receive alerts when jobs complete or fail."
                    )
                }

                SettingsActionRow(
                    title: "Send Test Notification",
                    detail: "Verify push notifications are working.",
                    systemImage: "bell.badge",
                    isLoading: isSendingTestNotification,
                    action: sendTestNotification
                )
                .disabled(isSendingTestNotification || !notificationManager.notificationsEnabled)

                SettingsActionRow(
                    title: "Send Rich Notification",
                    detail: "Test notification with cover art image.",
                    systemImage: "photo.badge.checkmark",
                    isLoading: isSendingRichTestNotification,
                    action: sendRichTestNotification
                )
                .disabled(isSendingRichTestNotification || !notificationManager.notificationsEnabled)
            } else {
                SettingsActionRow(
                    title: "Enable Notifications",
                    detail: "Get alerts when jobs complete or fail.",
                    systemImage: "bell",
                    isLoading: isRequestingPermission,
                    action: requestNotificationPermission
                )
                .disabled(isRequestingPermission)
            }
        } header: {
            SettingsSectionHeader(title: "Notifications", usesDarkBackground: usesDarkBackground)
        }
    }
}

struct SettingsActionRow: View {
    let title: String
    let detail: String
    let systemImage: String
    let isLoading: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                SettingsRowText(title: title, detail: detail)
                Spacer()
                if isLoading {
                    ProgressView()
                        .controlSize(.small)
                } else {
                    Image(systemName: systemImage)
                        .foregroundStyle(Color.accentColor)
                }
            }
        }
    }
}
#endif

struct SettingsRowText: View {
    let title: String
    let detail: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .foregroundStyle(.primary)
            Text(detail)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}

struct SettingsInfoRow: View {
    let title: String
    let value: String
    let systemImage: String
    let accessibilityIdentifier: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: systemImage)
                .foregroundStyle(.secondary)
                .frame(width: 24)
            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .foregroundStyle(.primary)
                Text(value)
                    .font(.caption)
                    .lineLimit(1)
                    .minimumScaleFactor(0.75)
                    .foregroundStyle(.secondary)
            }
            Spacer(minLength: 8)
        }
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier(accessibilityIdentifier)
    }
}
