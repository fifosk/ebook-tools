import SwiftUI

enum AppVersion {
    static var release: String {
        readInfoValue("EBOOK_TOOLS_RELEASE_VERSION") ?? "2026.06.22.87"
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
        ZStack {
            RoundedRectangle(cornerRadius: compact ? 5 : 8, style: .continuous)
                .fill(badgeBackground)
            RoundedRectangle(cornerRadius: compact ? 5 : 8, style: .continuous)
                .stroke(badgeBorder, lineWidth: 1)
            versionText
                .frame(width: badgeTextWidth, height: badgeHeight, alignment: .center)
        }
        .frame(width: badgeWidth, height: badgeHeight, alignment: .center)
        .clipped()
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
            .fixedSize(horizontal: true, vertical: true)
            .layoutPriority(20)
            .dynamicTypeSize(...DynamicTypeSize.large)
    }

    private var badgeWidth: CGFloat {
        compact ? 96 : 164
    }

    private var badgeTextWidth: CGFloat {
        compact ? 76 : 148
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
