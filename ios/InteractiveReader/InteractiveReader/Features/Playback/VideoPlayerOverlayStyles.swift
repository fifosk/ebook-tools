import SwiftUI

#if canImport(UIKit)
import UIKit
#endif

// MARK: - Header Background Style

enum VideoPlayerOverlayStyles {
    static var headerBackgroundGradient: LinearGradient {
        LinearGradient(
            colors: [
                Color(white: 0.18).opacity(0.7),
                Color(white: 0.12).opacity(0.45),
                Color(white: 0.08).opacity(0.2)
            ],
            startPoint: .top,
            endPoint: .bottom
        )
    }

    static var headerBackgroundCornerRadius: CGFloat {
        #if os(tvOS)
        return 18
        #else
        return 14
        #endif
    }

    static var controlButtonBackground: Color {
        .black.opacity(0.45)
    }

    static var controlButtonCornerRadius: CGFloat {
        8
    }
}

// MARK: - Info Header Metrics
// Note: PlayerInfoMetrics is defined in PlayerChannelBugView.swift
// These are additional overlay-specific metrics

enum VideoPlayerOverlayMetrics {
    static func coverWidth(isTV: Bool) -> CGFloat {
        isTV ? 60 : 36
    }

    static func coverHeight(isTV: Bool) -> CGFloat {
        isTV ? 60 : 36
    }
}

// MARK: - Header Fonts

enum VideoPlayerHeaderFonts {
    static func titleFont(isTV: Bool, isPad: Bool, scale: CGFloat) -> Font {
        #if os(tvOS)
        return .headline
        #else
        if isPad {
            return scaledFont(style: .subheadline, weight: .semibold, scale: scale)
        }
        return .subheadline.weight(.semibold)
        #endif
    }

    static func metaFont(isTV: Bool, isPad: Bool, scale: CGFloat) -> Font {
        #if os(tvOS)
        return .callout
        #else
        if isPad {
            return scaledFont(style: .caption1, weight: .regular, scale: scale)
        }
        return .caption
        #endif
    }

    static func indicatorFont(isTV: Bool, isPad: Bool, scale: CGFloat) -> Font {
        #if os(tvOS)
        return .callout.weight(.semibold)
        #else
        if isPad {
            return scaledFont(style: .caption1, weight: .semibold, scale: scale)
        }
        return .caption.weight(.semibold)
        #endif
    }

    #if os(iOS) || os(tvOS)
    private static func scaledFont(style: UIFont.TextStyle, weight: Font.Weight, scale: CGFloat) -> Font {
        let baseSize = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: baseSize * scale, weight: weight)
    }
    #else
    private static func scaledFont(style: Any, weight: Font.Weight, scale: CGFloat) -> Font {
        return .system(size: 16 * scale, weight: weight)
    }
    #endif
}

// MARK: - Timeline Pill View

struct VideoTimelinePill: View {
    let label: String
    let font: Font

    var body: some View {
        Text(label)
            .font(font)
            .foregroundStyle(Color.white.opacity(0.75))
            .lineLimit(1)
            .truncationMode(.tail)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(
                Capsule()
                    .fill(Color.black.opacity(0.5))
                    .overlay(
                        Capsule().stroke(Color.white.opacity(0.18), lineWidth: 1)
                    )
            )
    }
}

// MARK: - Header Toggle Button

struct VideoPlayerHeaderToggleButton: View {
    let isCollapsed: Bool
    let onToggle: () -> Void

    var body: some View {
        Button(action: onToggle) {
            Image(systemName: isCollapsed ? "chevron.down" : "chevron.up")
                .font(.caption.weight(.semibold))
                .padding(6)
                .background(.black.opacity(0.45), in: Circle())
                .foregroundStyle(.white)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(isCollapsed ? "Show info header" : "Hide info header")
    }
}

// MARK: - Subtitle Options Button

struct VideoPlayerSubtitleButton: View {
    let labelText: String
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            Label(labelText, systemImage: "captions.bubble")
                .labelStyle(.titleAndIcon)
                .font(.caption)
                .lineLimit(1)
                .truncationMode(.tail)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(.black.opacity(0.45), in: RoundedRectangle(cornerRadius: 8))
                .foregroundStyle(.white)
        }
    }
}

// MARK: - Time Formatting

enum VideoPlayerTimeFormatter {
    static func formatDuration(_ value: Double) -> String {
        let total = max(0, Int(value.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let seconds = total % 60
        return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
    }

    static func formatCompact(_ seconds: Double) -> String {
        guard seconds.isFinite else { return "--:--" }
        let total = max(0, Int(seconds.rounded()))
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let remainingSeconds = total % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, remainingSeconds)
        }
        return String(format: "%02d:%02d", minutes, remainingSeconds)
    }
}

// MARK: - Track Label Formatter

enum VideoPlayerTrackLabelFormatter {
    static func trimmedLabel(_ label: String, isTV: Bool, isPhone: Bool) -> String {
        var trimmed = label.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return "Subtitles Off" }

        // Remove path prefix
        if let separator = trimmed.lastIndex(where: { $0 == "/" || $0 == "\\" }) {
            trimmed = String(trimmed[trimmed.index(after: separator)...])
        }

        // Remove extension
        if let dot = trimmed.lastIndex(of: "."),
           dot > trimmed.startIndex,
           trimmed.distance(from: dot, to: trimmed.endIndex) <= 6 {
            trimmed = String(trimmed[..<dot])
        }

        // Truncate to limit
        let limit = isTV ? 32 : (isPhone ? 18 : 26)
        if trimmed.count > limit {
            trimmed = String(trimmed.prefix(max(limit - 3, 0))) + "..."
        }

        return trimmed
    }
}
