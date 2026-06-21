import SwiftUI

enum AppTheme {
    static let lightBackground = Color(red: 0.06, green: 0.09, blue: 0.16)
    static let darkBackground = Color.black

    static func background(for scheme: ColorScheme) -> some View {
        #if os(tvOS)
        ZStack {
            Color(red: 0.03, green: 0.10, blue: 0.18)
            RadialGradient(
                gradient: Gradient(colors: [
                    Color(red: 56 / 255, green: 189 / 255, blue: 248 / 255).opacity(0.22),
                    .clear
                ]),
                center: UnitPoint(x: 0.18, y: 0.18),
                startRadius: 0,
                endRadius: 520
            )
            RadialGradient(
                gradient: Gradient(colors: [
                    Color(red: 59 / 255, green: 130 / 255, blue: 246 / 255).opacity(0.18),
                    .clear
                ]),
                center: UnitPoint(x: 0.82, y: 0.08),
                startRadius: 0,
                endRadius: 620
            )
        }
        #else
        scheme == .dark ? darkBackground : lightBackground
        #endif
    }
}

enum AppVersion {
    static var release: String {
        readInfoValue("EBOOK_TOOLS_RELEASE_VERSION") ?? "2026.06.21.01"
    }

    static var displayLabel: String {
        "v\(release)"
    }

    static var bundleVersion: String {
        readInfoValue("CFBundleVersion") ?? "1"
    }

    static var marketingVersion: String {
        readInfoValue("CFBundleShortVersionString") ?? "1.0"
    }

    static var branch: String {
        let candidates: [String?] = [
            readInfoValue("EBOOK_TOOLS_BRANCH"),
            ProcessInfo.processInfo.environment["EBOOK_TOOLS_BRANCH"],
        ]

        for candidate in candidates {
            let trimmed = candidate?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            guard !trimmed.isEmpty else { continue }
            guard !trimmed.hasPrefix("$(") else { continue }
            return trimmed
        }

        return "unknown"
    }

    static var buildLabel: String {
        let branchLabel = branch == "unknown" ? "branch unknown" : branch
        return "bundle \(marketingVersion) (\(bundleVersion)) · \(branchLabel)"
    }

    private static func readInfoValue(_ key: String) -> String? {
        Bundle.main.object(forInfoDictionaryKey: key) as? String
            ?? Bundle.main.infoDictionary?[key] as? String
    }
}

struct AppVersionBadge: View {
    var body: some View {
        Text(AppVersion.displayLabel)
            .font(versionFont)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(Color.white.opacity(0.08), in: Capsule())
            .foregroundStyle(.secondary)
            .accessibilityLabel("Version \(AppVersion.release)")
            .accessibilityIdentifier("appVersionBadge")
    }

    private var versionFont: Font {
        #if os(tvOS)
        return .system(size: 12, weight: .semibold)
        #else
        return .caption2
        #endif
    }
}

struct AppChangelogEntry: Identifiable, Equatable {
    let id: String
    let title: String
    let detail: String
}

struct AppChangelogDay: Identifiable, Equatable {
    let id: String
    let dateLabel: String
    let version: String
    let entries: [AppChangelogEntry]
}

enum AppChangelog {
    static let days: [AppChangelogDay] = [
        AppChangelogDay(
            id: "2026-06-21",
            dateLabel: "June 21, 2026",
            version: "2026.06.21.01",
            entries: [
                AppChangelogEntry(
                    id: "backend-runtime-settings",
                    title: "Backend runtime visible in Settings",
                    detail: "Settings now verifies the public ebook-tools API descriptor and shows the service/version without exposing tokens."
                ),
                AppChangelogEntry(
                    id: "pipeline-backend-preflight",
                    title: "Pipeline backend preflight",
                    detail: "Simulator smoke profiles now fail fast on backend health and runtime identity before Xcode builds."
                ),
                AppChangelogEntry(
                    id: "settings-connection-keychain",
                    title: "Connection and Keychain state",
                    detail: "Settings shows API host, signed-in session, and Keychain token storage for attended device review."
                ),
                AppChangelogEntry(
                    id: "apple-tv-icon-remote",
                    title: "tvOS deployment polish",
                    detail: "Apple TV icon assets and remote-driven playback journeys are covered by the shared pipeline."
                )
            ]
        )
    ]
}

struct AppChangelogSummaryView: View {
    let maxEntries: Int?
    let showBuildMetadata: Bool
    let usesDarkBackground: Bool

    init(
        maxEntries: Int? = nil,
        showBuildMetadata: Bool = true,
        usesDarkBackground: Bool = true
    ) {
        self.maxEntries = maxEntries
        self.showBuildMetadata = showBuildMetadata
        self.usesDarkBackground = usesDarkBackground
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(AppVersion.displayLabel)
                    .font(.headline)
                    .foregroundStyle(primaryStyle)
                Spacer(minLength: 8)
                Text(AppChangelog.days.first?.dateLabel ?? "Latest")
                    .font(.caption)
                    .foregroundStyle(secondaryStyle)
            }

            if showBuildMetadata {
                Text(AppVersion.buildLabel)
                    .font(.caption)
                    .foregroundStyle(secondaryStyle)
                    .lineLimit(2)
                    .minimumScaleFactor(0.8)
                    .accessibilityIdentifier("appBuildMetadataText")
            }

            ForEach(displayEntries) { entry in
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.caption)
                        .foregroundStyle(Color.green)
                        .padding(.top, 2)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(entry.title)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(primaryStyle)
                        Text(entry.detail)
                            .font(.caption)
                            .foregroundStyle(secondaryStyle)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        }
        .padding(12)
        .background(backgroundStyle, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(borderStyle, lineWidth: 1)
        )
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("appChangelogSummaryView")
    }

    private var displayEntries: [AppChangelogEntry] {
        let entries = AppChangelog.days.first?.entries ?? []
        guard let maxEntries else { return entries }
        return Array(entries.prefix(maxEntries))
    }

    private var primaryStyle: Color {
        usesDarkBackground ? .white : .primary
    }

    private var secondaryStyle: Color {
        usesDarkBackground ? .white.opacity(0.72) : .secondary
    }

    private var backgroundStyle: Color {
        usesDarkBackground ? Color.white.opacity(0.06) : Color.secondary.opacity(0.08)
    }

    private var borderStyle: Color {
        usesDarkBackground ? Color.white.opacity(0.12) : Color.secondary.opacity(0.18)
    }
}
