import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

#if os(tvOS)
struct TVLanguageFlagButtonStyle: ButtonStyle {
    @Environment(\.isFocused) var isFocused

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.95 : (isFocused ? 1.1 : 1.0))
            .brightness(isFocused ? 0.15 : 0)
            .animation(.easeInOut(duration: 0.15), value: isFocused)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}
#endif

struct PlayerLanguageFlagRow: View {
    let flags: [LanguageFlagEntry]
    let modelLabel: String?
    let isTV: Bool
    let sizeScale: CGFloat
    let activeRoles: Set<LanguageFlagRole>
    let availableRoles: Set<LanguageFlagRole>
    let onToggleRole: ((LanguageFlagRole) -> Void)?
    let showConnector: Bool

    init(
        flags: [LanguageFlagEntry],
        modelLabel: String?,
        isTV: Bool,
        sizeScale: CGFloat = 1.0,
        activeRoles: Set<LanguageFlagRole> = [],
        availableRoles: Set<LanguageFlagRole> = [.original, .translation],
        onToggleRole: ((LanguageFlagRole) -> Void)? = nil,
        showConnector: Bool = true
    ) {
        self.flags = flags
        self.modelLabel = modelLabel
        self.isTV = isTV
        self.sizeScale = sizeScale
        self.activeRoles = activeRoles
        self.availableRoles = availableRoles
        self.onToggleRole = onToggleRole
        self.showConnector = showConnector
    }

    var body: some View {
        HStack(spacing: badgeSpacing) {
            ForEach(Array(orderedFlags.enumerated()), id: \.element.id) { index, flag in
                PlayerLanguageFlagRowItem(
                    flag: flag,
                    isTV: isTV,
                    sizeScale: sizeScale,
                    showsLabel: shouldShowLabel,
                    isActive: isActive(role: flag.role),
                    isAvailable: availableRoles.contains(flag.role),
                    showsConnector: showConnector && index < orderedFlags.count - 1,
                    connectorLabel: connectorLabel,
                    onToggleRole: onToggleRole
                )
            }
            if let modelBadgeLabel {
                LanguageModelBadge(label: modelBadgeLabel, isTV: isTV, sizeScale: sizeScale)
            }
        }
    }

    private var badgeSpacing: CGFloat {
        (isTV ? 6 : 4) * sizeScale
    }

    private func isActive(role: LanguageFlagRole) -> Bool {
        guard !activeRoles.isEmpty else { return true }
        return activeRoles.contains(role)
    }

    private var orderedFlags: [LanguageFlagEntry] {
        let original = flags.first(where: { $0.role == .original })
        let translation = flags.first(where: { $0.role == .translation })
        if let original, let translation {
            return [original, translation]
        }
        return flags
    }

    private var connectorLabel: String {
        "to"
    }

    private var modelBadgeLabel: String? {
        guard let modelLabel = modelLabel?.trimmingCharacters(in: .whitespacesAndNewlines),
              !modelLabel.isEmpty else {
            return nil
        }
        return "using [\(modelLabel)]"
    }

    private var shouldShowLabel: Bool {
        true
    }
}

private struct PlayerLanguageFlagRowItem: View {
    let flag: LanguageFlagEntry
    let isTV: Bool
    let sizeScale: CGFloat
    let showsLabel: Bool
    let isActive: Bool
    let isAvailable: Bool
    let showsConnector: Bool
    let connectorLabel: String
    let onToggleRole: ((LanguageFlagRole) -> Void)?

    var body: some View {
        flagControl
        if showsConnector {
            LanguageConnectorBadge(label: connectorLabel, isTV: isTV, sizeScale: sizeScale)
        }
    }

    @ViewBuilder
    private var flagControl: some View {
        if onToggleRole != nil, isAvailable {
            Button(action: handleToggleRole) {
                flagBadge
            }
            #if os(tvOS)
            .buttonStyle(TVLanguageFlagButtonStyle())
            #else
            .buttonStyle(.plain)
            #endif
        } else {
            flagBadge
        }
    }

    private var flagBadge: some View {
        LanguageFlagBadge(
            entry: flag,
            isTV: isTV,
            showsLabel: showsLabel,
            sizeScale: sizeScale,
            isActive: isActive
        )
        .opacity(flagOpacity)
    }

    private var flagOpacity: Double {
        guard isAvailable else { return 0.3 }
        return isActive ? 1.0 : 0.55
    }

    private func handleToggleRole() {
        onToggleRole?(flag.role)
    }
}

struct JobTypeGlyphBadge: View {
    let glyph: JobTypeGlyph

    var body: some View {
        Group {
            if glyph.variant == .youtube {
                YoutubeGlyphMark(width: youtubeWidth, height: youtubeHeight)
            } else if glyph.variant == .tv {
                TubeTVGlyphMark(width: tubeTvWidth, height: tubeTvHeight, color: .primary)
            } else {
                Text(glyph.icon)
                    .font(glyphFont)
            }
        }
        .frame(minWidth: 28, alignment: .center)
        .accessibilityLabel(glyph.label)
    }

    private var youtubeHeight: CGFloat {
        glyphPointSize * 0.7
    }

    private var youtubeWidth: CGFloat {
        youtubeHeight * 1.6
    }

    private var tubeTvHeight: CGFloat {
        glyphPointSize * 0.7
    }

    private var tubeTvWidth: CGFloat {
        tubeTvHeight * 1.3
    }

    private var glyphPointSize: CGFloat {
        #if os(iOS) || os(tvOS)
        return UIFont.preferredFont(forTextStyle: .caption1).pointSize * 2.0
        #else
        return 28
        #endif
    }

    private var glyphFont: Font {
        .system(size: glyphPointSize)
    }
}

struct LanguageFlagPairView: View {
    let flags: [LanguageFlagEntry]

    var body: some View {
        let ordered = orderedFlags
        if let first = ordered.first {
            HStack(spacing: 6) {
                Text(first.emoji)
                    .font(flagFont)
                if let second = ordered.dropFirst().first {
                    Text("-")
                        .font(connectorFont)
                        .foregroundStyle(.secondary)
                    Text(second.emoji)
                        .font(flagFont)
                }
            }
            .accessibilityLabel(accessibilityLabel(for: ordered))
        }
    }

    private var orderedFlags: [LanguageFlagEntry] {
        let original = flags.first(where: { $0.role == .original })
        let translation = flags.first(where: { $0.role == .translation })
        if let original, let translation {
            return [original, translation]
        }
        return flags
    }

    private func accessibilityLabel(for flags: [LanguageFlagEntry]) -> String {
        guard let first = flags.first else { return "Languages" }
        if let second = flags.dropFirst().first {
            return "\(first.label) to \(second.label)"
        }
        return first.label
    }

    private var flagFont: Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: .caption1).pointSize
        return .system(size: base * 2.0)
        #else
        return .system(size: 28)
        #endif
    }

    private var connectorFont: Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: .caption1).pointSize
        return .system(size: base)
        #else
        return .system(size: 14)
        #endif
    }
}

private struct LanguageFlagBadge: View {
    let entry: LanguageFlagEntry
    let isTV: Bool
    let showsLabel: Bool
    let sizeScale: CGFloat
    var isActive: Bool = true

    var body: some View {
        HStack(spacing: labelSpacing) {
            Text(entry.emoji)
                .font(emojiFont)
                .saturation(isActive ? 1.0 : 0.3)
            if showsLabel {
                Text(entry.shortLabel.isEmpty ? entry.label : entry.shortLabel)
                    .font(labelFont)
                    .foregroundStyle(Color.white.opacity(isActive ? 0.85 : 0.4))
            }
        }
        .padding(.horizontal, labelPaddingHorizontal)
        .padding(.vertical, labelPaddingVertical)
        .background(PlayerHeaderPillBackground(isActive: isActive, isProminent: true))
        .opacity(isActive ? 1.0 : 0.6)
        .accessibilityLabel(entry.accessibilityLabel)
    }

    private var labelSpacing: CGFloat {
        (showsLabel ? 4 : 0) * sizeScale
    }

    private var labelPaddingHorizontal: CGFloat {
        (showsLabel ? 6 : 5) * sizeScale
    }

    private var labelPaddingVertical: CGFloat {
        3 * sizeScale
    }

    private var labelFont: Font {
        #if os(tvOS)
        return scaledFont(style: .caption1, weight: .semibold)
        #else
        return scaledFont(style: .caption2, weight: .semibold)
        #endif
    }

    private var emojiFont: Font {
        scaledFont(style: .caption1, weight: .semibold)
    }

    private func scaledFont(style: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * sizeScale, weight: weight)
        #else
        return .system(size: 12 * sizeScale, weight: weight)
        #endif
    }
}

private struct LanguageConnectorBadge: View {
    let label: String
    let isTV: Bool
    let sizeScale: CGFloat

    var body: some View {
        Text(label)
            .font(labelFont)
            .foregroundStyle(Color.white.opacity(0.7))
            .lineLimit(1)
            .minimumScaleFactor(0.7)
            .padding(.horizontal, 6 * sizeScale)
            .padding(.vertical, 2 * sizeScale)
            .background(PlayerHeaderPillBackground(isActive: false))
            .accessibilityLabel(label)
    }

    private var labelFont: Font {
        #if os(tvOS)
        return scaledFont(style: .caption1, weight: .semibold)
        #else
        return scaledFont(style: .caption2, weight: .semibold)
        #endif
    }

    private func scaledFont(style: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * sizeScale, weight: weight)
        #else
        return .system(size: 12 * sizeScale, weight: weight)
        #endif
    }
}

private struct LanguageModelBadge: View {
    let label: String
    let isTV: Bool
    let sizeScale: CGFloat

    var body: some View {
        Text(label)
            .font(labelFont)
            .foregroundStyle(Color.white.opacity(0.7))
            .lineLimit(1)
            .minimumScaleFactor(0.7)
            .padding(.horizontal, 8 * sizeScale)
            .padding(.vertical, 3 * sizeScale)
            .background(PlayerHeaderPillBackground(isActive: false))
            .accessibilityLabel(label)
    }

    private var labelFont: Font {
        #if os(tvOS)
        return scaledFont(style: .caption1, weight: .semibold)
        #else
        return scaledFont(style: .caption2, weight: .semibold)
        #endif
    }

    private func scaledFont(style: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let base = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: base * sizeScale, weight: weight)
        #else
        return .system(size: 12 * sizeScale, weight: weight)
        #endif
    }
}
