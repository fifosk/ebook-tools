import SwiftUI

struct PlaybackSettingsView: View {
    @EnvironmentObject private var appState: AppState

    let sectionPicker: BrowseSectionPicker?
    let backTitle: String?
    let onBack: (() -> Void)?
    let usesDarkBackground: Bool

    @AppStorage("interactive.autoScaleEnabled") private var autoScaleEnabled: Bool = true
    @StateObject private var notificationManager = NotificationManager.shared
    @State private var isRequestingPermission = false
    @State private var isSendingTestNotification = false
    @State private var isSendingRichTestNotification = false
    @State private var showTestAlert = false
    @State private var testAlertMessage = ""
    @State private var backendRuntimeState: BackendRuntimeState = .idle

    init(sectionPicker: BrowseSectionPicker? = nil, backTitle: String? = nil, onBack: (() -> Void)? = nil, usesDarkBackground: Bool = false) {
        self.sectionPicker = sectionPicker
        self.backTitle = backTitle
        self.onBack = onBack
        self.usesDarkBackground = usesDarkBackground
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let onBack, let backTitle {
                Button(action: onBack) {
                    Label("Back to \(backTitle)", systemImage: "chevron.left")
                }
                .padding(.horizontal)
            }
            if let sectionPicker {
                sectionPicker
            } else {
                Text("Settings")
                    .font(.title3)
                    .foregroundStyle(usesDarkBackground ? .white : .primary)
                    .padding(.horizontal)
            }
            List {
                SettingsConnectionSection(
                    apiHostLabel: apiHostLabel,
                    backendRuntimeState: backendRuntimeState,
                    sessionLabel: sessionLabel,
                    usesDarkBackground: usesDarkBackground
                )

                PlaybackSettingsSection(
                    autoScaleEnabled: $autoScaleEnabled,
                    usesDarkBackground: usesDarkBackground
                )

                AppChangelogSettingsSection(usesDarkBackground: usesDarkBackground)

                VoiceSettingsSection(usesDarkBackground: usesDarkBackground)

                #if os(iOS)
                NotificationSettingsSection(
                    notificationManager: notificationManager,
                    isRequestingPermission: isRequestingPermission,
                    isSendingTestNotification: isSendingTestNotification,
                    isSendingRichTestNotification: isSendingRichTestNotification,
                    requestNotificationPermission: requestNotificationPermission,
                    sendTestNotification: sendTestNotification,
                    sendRichTestNotification: sendRichTestNotification,
                    usesDarkBackground: usesDarkBackground
                )
                #endif
            }
            #if os(tvOS)
            .listStyle(.plain)
            #else
            .listStyle(.insetGrouped)
            .scrollContentBackground(usesDarkBackground ? .hidden : .automatic)
            #endif
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(usesDarkBackground ? AppTheme.lightBackground : Color.clear)
        #if os(iOS)
        .toolbarBackground(usesDarkBackground ? AppTheme.lightBackground : Color.clear, for: .navigationBar)
        .toolbarBackground(usesDarkBackground ? .visible : .automatic, for: .navigationBar)
        .toolbarColorScheme(usesDarkBackground ? .dark : nil, for: .navigationBar)
        #endif
        .task(id: apiHostLabel) {
            await refreshBackendRuntimeDescriptor()
        }
        #if os(iOS)
        .alert("Test Notification", isPresented: $showTestAlert) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(testAlertMessage)
        }
        #endif
    }

    private var apiHostLabel: String {
        guard let url = appState.apiBaseURL else { return "Not configured" }
        let scheme = url.scheme?.nonEmptyValue ?? "https"
        let host = url.host?.nonEmptyValue ?? url.absoluteString
        return "\(scheme)://\(host)"
    }

    private var sessionLabel: String {
        guard let user = appState.session?.user else { return "Not signed in" }
        if let role = user.role.nonEmptyValue {
            return "\(user.username) · \(role)"
        }
        return user.username
    }

    @MainActor
    private func refreshBackendRuntimeDescriptor() async {
        guard let apiBaseURL = appState.apiBaseURL else {
            backendRuntimeState = .unavailable("API URL missing")
            return
        }

        backendRuntimeState = .checking
        do {
            let client = APIClient(configuration: APIClientConfiguration(apiBaseURL: apiBaseURL))
            let descriptor = try await client.fetchBackendRuntimeDescriptor()
            let status = descriptor.status.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
            guard status == "ok" || status == "healthy" || status == "up" else {
                backendRuntimeState = .unavailable("Status \(descriptor.status)")
                return
            }
            backendRuntimeState = .verified(
                service: descriptor.service,
                version: descriptor.version
            )
        } catch is CancellationError {
            return
        } catch {
            backendRuntimeState = .unavailable("Descriptor unavailable")
        }
    }

    #if os(iOS)
    private func requestNotificationPermission() {
        isRequestingPermission = true
        Task {
            _ = await notificationManager.requestAuthorization()
            isRequestingPermission = false
        }
    }

    private func sendTestNotification() {
        guard let config = appState.configuration else {
            testAlertMessage = "Not signed in. Please log in first."
            showTestAlert = true
            return
        }

        isSendingTestNotification = true
        Task {
            do {
                let result = try await notificationManager.sendTestNotification(using: config)
                if result.sent > 0 {
                    testAlertMessage = "Test notification sent to \(result.sent) device(s)!"
                } else if let message = result.message {
                    testAlertMessage = message
                } else {
                    testAlertMessage = "No devices registered. Make sure notifications are enabled on this device."
                }
            } catch {
                testAlertMessage = "Failed to send: \(error.localizedDescription)"
            }
            isSendingTestNotification = false
            showTestAlert = true
        }
    }

    private func sendRichTestNotification() {
        guard let config = appState.configuration else {
            testAlertMessage = "Not signed in. Please log in first."
            showTestAlert = true
            return
        }

        isSendingRichTestNotification = true
        Task {
            do {
                let result = try await notificationManager.sendRichTestNotification(
                    using: config,
                    title: "Sample Book Title",
                    subtitle: "Sample Author Name"
                )
                if result.sent > 0 {
                    testAlertMessage = "Rich notification sent to \(result.sent) device(s)!"
                } else if let message = result.message {
                    testAlertMessage = message
                } else {
                    testAlertMessage = "No devices registered. Make sure notifications are enabled on this device."
                }
            } catch {
                testAlertMessage = "Failed to send: \(error.localizedDescription)"
            }
            isSendingRichTestNotification = false
            showTestAlert = true
        }
    }
    #endif
}

private enum BackendRuntimeState: Equatable {
    case idle
    case checking
    case verified(service: String, version: String)
    case unavailable(String)

    var label: String {
        switch self {
        case .idle, .checking:
            return "Checking"
        case let .verified(service, version):
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
}

private struct SettingsSectionHeader: View {
    let title: String
    let usesDarkBackground: Bool

    var body: some View {
        Text(title)
            .foregroundStyle(usesDarkBackground ? .white.opacity(0.72) : .secondary)
    }
}

private struct SettingsConnectionSection: View {
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

private struct PlaybackSettingsSection: View {
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

private struct AppChangelogSettingsSection: View {
    let usesDarkBackground: Bool

    var body: some View {
        Section {
            AppChangelogSummaryView(
                showBuildMetadata: true,
                usesDarkBackground: usesDarkBackground,
                maxContentHeight: 420
            )
            .listRowInsets(EdgeInsets(top: 8, leading: 0, bottom: 8, trailing: 0))
            #if os(iOS)
            .listRowBackground(Color.clear)
            #endif
        } header: {
            SettingsSectionHeader(title: "Daily Changelog", usesDarkBackground: usesDarkBackground)
        }
    }
}

private struct VoiceSettingsSection: View {
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
private struct NotificationSettingsSection: View {
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

private struct SettingsActionRow: View {
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

private struct SettingsRowText: View {
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

private struct SettingsInfoRow: View {
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
