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
                version: descriptor.version,
                createContract: Self.createContractState(from: descriptor.creation)
            )
        } catch is CancellationError {
            return
        } catch {
            backendRuntimeState = .unavailable("Descriptor unavailable")
        }
    }

    private static func createContractState(
        from creation: BackendRuntimeDescriptorResponse.CreationContract?
    ) -> BackendCreateContractState {
        guard
            let creation,
            let optionsPath = creation.bookOptionsPath.nonEmptyValue,
            let jobsPath = creation.bookJobsPath.nonEmptyValue
        else {
            return .unavailable
        }
        guard
            optionsPath == AppleCreateRuntimeContract.bookOptionsPath,
            jobsPath == AppleCreateRuntimeContract.bookJobsPath
        else {
            return .mismatch(optionsPath: optionsPath, jobsPath: jobsPath)
        }
        return .ready(optionsPath: optionsPath, jobsPath: jobsPath)
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
