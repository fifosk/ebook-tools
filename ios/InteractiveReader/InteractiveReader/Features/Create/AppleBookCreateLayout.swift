import SwiftUI

private enum AppleBookCreateLayoutMetrics {
    static let setupPaneMinWidth: CGFloat = 220
    static let setupPaneIdealWidth: CGFloat = 260
    static let setupPaneMaxWidth: CGFloat = 280
    static let settingsPaneMinWidth: CGFloat = 480
    static let settingsPaneIdealWidth: CGFloat = 680
}

struct AppleBookCreateList<Content: View>: View {
    let usesDarkBackground: Bool
    let accessibilityIdentifier: String
    private let content: () -> Content

    init(
        usesDarkBackground: Bool,
        accessibilityIdentifier: String,
        @ViewBuilder content: @escaping () -> Content
    ) {
        self.usesDarkBackground = usesDarkBackground
        self.accessibilityIdentifier = accessibilityIdentifier
        self.content = content
    }

    var body: some View {
        List {
            content()
        }
        #if os(tvOS)
        .listStyle(.plain)
        #else
        .listStyle(.insetGrouped)
        .scrollContentBackground(usesDarkBackground ? .hidden : .automatic)
        #endif
        .accessibilityIdentifier(accessibilityIdentifier)
    }
}

struct AppleBookCreateSettingsForm<Content: View>: View {
    let usesDarkBackground: Bool
    let accessibilityIdentifier: String
    private let content: () -> Content

    init(
        usesDarkBackground: Bool,
        accessibilityIdentifier: String,
        @ViewBuilder content: @escaping () -> Content
    ) {
        self.usesDarkBackground = usesDarkBackground
        self.accessibilityIdentifier = accessibilityIdentifier
        self.content = content
    }

    var body: some View {
        Form {
            content()
        }
        #if os(tvOS)
        .listStyle(.plain)
        #else
        .scrollContentBackground(usesDarkBackground ? .hidden : .automatic)
        #endif
        .accessibilityIdentifier(accessibilityIdentifier)
    }
}

struct AppleBookCreateRegularWidthLayout<SetupContent: View, SettingsContent: View>: View {
    let usesDarkBackground: Bool
    private let setupContent: () -> SetupContent
    private let settingsContent: () -> SettingsContent

    init(
        usesDarkBackground: Bool,
        @ViewBuilder setupContent: @escaping () -> SetupContent,
        @ViewBuilder settingsContent: @escaping () -> SettingsContent
    ) {
        self.usesDarkBackground = usesDarkBackground
        self.setupContent = setupContent
        self.settingsContent = settingsContent
    }

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            AppleBookCreateList(
                usesDarkBackground: usesDarkBackground,
                accessibilityIdentifier: "appleBookCreateSetupPane",
                content: setupContent
            )
            .frame(
                minWidth: AppleBookCreateLayoutMetrics.setupPaneMinWidth,
                idealWidth: AppleBookCreateLayoutMetrics.setupPaneIdealWidth,
                maxWidth: AppleBookCreateLayoutMetrics.setupPaneMaxWidth,
                maxHeight: .infinity
            )
            .layoutPriority(0)

            Divider()

            AppleBookCreateSettingsForm(
                usesDarkBackground: usesDarkBackground,
                accessibilityIdentifier: "appleBookCreateSettingsPane",
                content: settingsContent
            )
            .frame(
                minWidth: AppleBookCreateLayoutMetrics.settingsPaneMinWidth,
                idealWidth: AppleBookCreateLayoutMetrics.settingsPaneIdealWidth,
                maxWidth: .infinity,
                maxHeight: .infinity
            )
            .layoutPriority(2)
        }
        .accessibilityIdentifier("appleBookCreateRegularWidthLayout")
    }
}
