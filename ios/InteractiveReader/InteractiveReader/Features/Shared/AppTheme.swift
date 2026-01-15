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
    static var branch: String {
        let candidates: [String?] = [
            Bundle.main.object(forInfoDictionaryKey: "EBOOK_TOOLS_BRANCH") as? String,
            Bundle.main.infoDictionary?["EBOOK_TOOLS_BRANCH"] as? String,
            ProcessInfo.processInfo.environment["EBOOK_TOOLS_BRANCH"],
            Bundle.main.infoDictionary?["CFBundleVersion"] as? String
        ]

        for candidate in candidates {
            let trimmed = candidate?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            guard !trimmed.isEmpty else { continue }
            guard !trimmed.hasPrefix("$(") else { continue }
            return trimmed
        }

        return "unknown"
    }
}

struct AppVersionBadge: View {
    private var label: String {
        "v\(AppVersion.branch)"
    }

    var body: some View {
        Text(label)
            .font(versionFont)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(Color.white.opacity(0.08), in: Capsule())
            .foregroundStyle(.secondary)
            .accessibilityLabel("Version \(AppVersion.branch)")
    }

    private var versionFont: Font {
        #if os(tvOS)
        return .system(size: 12, weight: .semibold)
        #else
        return .caption2
        #endif
    }
}
