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
        readInfoValue("EBOOK_TOOLS_RELEASE_VERSION") ?? "2026.06.21.08"
    }

    static var displayLabel: String {
        "v\(release)"
    }

    static var compactDisplayLabel: String {
        let parts = release.split(separator: ".")
        guard parts.count == 4 else { return displayLabel }
        return "b\(parts[3])"
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
    let compact: Bool
    let usesDarkBackground: Bool

    init(compact: Bool = false, usesDarkBackground: Bool = true) {
        self.compact = compact
        self.usesDarkBackground = usesDarkBackground
    }

    var body: some View {
        versionText
            .frame(
                minWidth: badgeTextWidth,
                idealWidth: badgeTextWidth,
                maxWidth: badgeTextWidth,
                minHeight: badgeHeight,
                idealHeight: badgeHeight,
                maxHeight: badgeHeight,
                alignment: .center
            )
            .padding(.horizontal, compact ? 6 : 8)
            .background(badgeBackground, in: RoundedRectangle(cornerRadius: compact ? 5 : 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: compact ? 5 : 8, style: .continuous)
                    .stroke(badgeBorder, lineWidth: 1)
            )
            .frame(
                minWidth: badgeWidth,
                idealWidth: badgeWidth,
                maxWidth: badgeWidth,
                minHeight: badgeHeight,
                idealHeight: badgeHeight,
                maxHeight: badgeHeight,
                alignment: .center
            )
            .fixedSize(horizontal: true, vertical: true)
            .accessibilityLabel("Version \(AppVersion.release)")
            .accessibilityIdentifier("appVersionBadge")
    }

    private var versionText: some View {
        Text(compact ? AppVersion.compactDisplayLabel : AppVersion.displayLabel)
            .font(versionFont)
            .monospacedDigit()
            .lineLimit(1)
            .minimumScaleFactor(compact ? 1 : 0.72)
            .allowsTightening(!compact)
            .foregroundStyle(badgeForeground)
            .frame(minWidth: badgeTextWidth, idealWidth: badgeTextWidth, maxWidth: badgeTextWidth, alignment: .center)
            .fixedSize(horizontal: true, vertical: true)
            .layoutPriority(20)
            .dynamicTypeSize(...DynamicTypeSize.large)
    }

    private var badgeWidth: CGFloat {
        compact ? 72 : 164
    }

    private var badgeTextWidth: CGFloat {
        compact ? 44 : 148
    }

    private var badgeHeight: CGFloat {
        compact ? 24 : 28
    }

    private var badgeBackground: Color {
        usesDarkBackground ? Color.white.opacity(0.14) : Color.primary.opacity(0.08)
    }

    private var badgeBorder: Color {
        usesDarkBackground ? Color.white.opacity(0.12) : Color.primary.opacity(0.08)
    }

    private var badgeForeground: Color {
        usesDarkBackground ? Color.white.opacity(0.82) : .secondary
    }

    private var versionFont: Font {
        #if os(tvOS)
        return .system(size: 12, weight: .semibold)
        #else
        return .system(size: compact ? 11 : 12, weight: .semibold, design: .monospaced)
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
            version: "2026.06.21.08",
            entries: [
                AppChangelogEntry(
                    id: "wd-staging-pipeline-contract",
                    title: "WD staging pipeline aligned",
                    detail: "ebook-tools and Finance Review now share the same Mac Studio WD staging convention before backend maintenance."
                ),
                AppChangelogEntry(
                    id: "compact-version-build-token",
                    title: "iPad version chip fixed",
                    detail: "Compact browse headers now show the short daily build token while full release metadata remains visible in roomy surfaces."
                ),
                AppChangelogEntry(
                    id: "compact-version-chip-width",
                    title: "Compact version chip width",
                    detail: "Compact headers now use a shorter fixed-width chip with fixed-size monospaced text so the release cannot stack vertically in split view."
                ),
                AppChangelogEntry(
                    id: "version-layout-defensive-rows",
                    title: "Version layout hardened",
                    detail: "Version text now owns its ideal width before the pill is drawn, and changelog headers no longer squeeze full version labels beside the date."
                ),
                AppChangelogEntry(
                    id: "version-pill-owns-width",
                    title: "Version badge no longer squeezes",
                    detail: "The login badge now owns a full row and toolbar headers use a compact daily label so iPad cannot stack the version vertically."
                ),
                AppChangelogEntry(
                    id: "ipad-version-pill-layout",
                    title: "iPad version badge layout",
                    detail: "The release pill now stays on one line in crowded iPad headers instead of collapsing into vertical characters."
                ),
                AppChangelogEntry(
                    id: "apple-bundle-versioning",
                    title: "Device inventory versioning",
                    detail: "Installed device metadata now carries the daily build number so CoreDevice checks can identify the deployed app."
                ),
                AppChangelogEntry(
                    id: "release-contract-guard",
                    title: "Daily release contract guard",
                    detail: "A repo check now keeps Info plists, in-app changelog, Markdown changelog, and journey badge assertions in sync."
                ),
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
            ViewThatFits(in: .horizontal) {
                changelogTitleRow
                changelogTitleStack
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

    private var changelogTitleRow: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            changelogVersionText
            Spacer(minLength: 8)
            changelogDateText
        }
    }

    private var changelogTitleStack: some View {
        VStack(alignment: .leading, spacing: 2) {
            changelogVersionText
            changelogDateText
        }
    }

    private var changelogVersionText: some View {
        Text(AppVersion.displayLabel)
            .font(.headline)
            .monospacedDigit()
            .foregroundStyle(primaryStyle)
            .lineLimit(1)
            .minimumScaleFactor(0.9)
            .fixedSize(horizontal: true, vertical: false)
    }

    private var changelogDateText: some View {
        Text(AppChangelog.days.first?.dateLabel ?? "Latest")
            .font(.caption)
            .foregroundStyle(secondaryStyle)
            .lineLimit(1)
            .fixedSize(horizontal: true, vertical: false)
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
        #if os(tvOS)
        return usesDarkBackground ? Color.white.opacity(0.07) : Color.black.opacity(0.08)
        #else
        usesDarkBackground ? Color.white.opacity(0.07) : Color(.secondarySystemBackground)
        #endif
    }

    private var borderStyle: Color {
        #if os(tvOS)
        return usesDarkBackground ? Color.white.opacity(0.12) : Color.primary.opacity(0.16)
        #else
        usesDarkBackground ? Color.white.opacity(0.12) : Color(.separator).opacity(0.4)
        #endif
    }
}
