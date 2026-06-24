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

struct AppleBookCreateContainer<SetupContent: View, SettingsContent: View>: View {
    let sectionPicker: BrowseSectionPicker?
    let usesRegularWidthLayout: Bool
    let usesDarkBackground: Bool
    private let setupContent: () -> SetupContent
    private let settingsContent: () -> SettingsContent

    init(
        sectionPicker: BrowseSectionPicker?,
        usesRegularWidthLayout: Bool,
        usesDarkBackground: Bool,
        @ViewBuilder setupContent: @escaping () -> SetupContent,
        @ViewBuilder settingsContent: @escaping () -> SettingsContent
    ) {
        self.sectionPicker = sectionPicker
        self.usesRegularWidthLayout = usesRegularWidthLayout
        self.usesDarkBackground = usesDarkBackground
        self.setupContent = setupContent
        self.settingsContent = settingsContent
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let sectionPicker {
                sectionPicker
            }

            if usesRegularWidthLayout {
                AppleBookCreateRegularWidthLayout(
                    usesDarkBackground: usesDarkBackground,
                    setupContent: setupContent,
                    settingsContent: settingsContent
                )
            } else {
                AppleBookCreateList(
                    usesDarkBackground: usesDarkBackground,
                    accessibilityIdentifier: "appleBookCreateSingleColumnList"
                ) {
                    setupContent()
                    settingsContent()
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(usesDarkBackground ? AppTheme.lightBackground : Color.clear)
        #if os(iOS)
        .toolbarBackground(usesDarkBackground ? AppTheme.lightBackground : Color.clear, for: .navigationBar)
        .toolbarBackground(usesDarkBackground ? .visible : .automatic, for: .navigationBar)
        .toolbarColorScheme(usesDarkBackground ? .dark : nil, for: .navigationBar)
        #endif
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
