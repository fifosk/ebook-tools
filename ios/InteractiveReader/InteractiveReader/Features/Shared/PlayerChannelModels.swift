import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

enum PlayerChannelVariant {
    case book
    case subtitles
    case video
    case tv
    case youtube
    case nas
    case dub
    case job
}

enum PlayerInfoMetrics {
    static func logoSize(isTV: Bool) -> CGFloat {
        isTV ? 70 : 47
    }

    static func iconSize(isTV: Bool) -> CGFloat {
        isTV ? 34 : 23
    }

    static func cornerRadius(isTV: Bool) -> CGFloat {
        isTV ? 22 : 16
    }

    static func clockSpacing(isTV: Bool) -> CGFloat {
        isTV ? 6 : 4
    }

    static func clockHorizontalPadding(isTV: Bool) -> CGFloat {
        isTV ? 10 : 7
    }

    static func clockVerticalPadding(isTV: Bool) -> CGFloat {
        isTV ? 6 : 3
    }

    static func clockFont(isTV: Bool) -> Font {
        isTV ? .callout.weight(.bold) : .caption2.weight(.bold)
    }

    static func clockLineHeight(isTV: Bool) -> CGFloat {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .callout : .caption2
        return UIFont.preferredFont(forTextStyle: style).lineHeight
        #else
        return isTV ? 20 : 12
        #endif
    }

    static func badgeHeight(isTV: Bool) -> CGFloat {
        let clockHeight = clockLineHeight(isTV: isTV) + clockVerticalPadding(isTV: isTV) * 2
        return logoSize(isTV: isTV) + clockSpacing(isTV: isTV) + clockHeight
    }

    static func coverHeight(isTV: Bool) -> CGFloat {
        badgeHeight(isTV: isTV)
    }

    static func coverWidth(isTV: Bool) -> CGFloat {
        CoverMetrics.bookWidth(forHeight: coverHeight(isTV: isTV))
    }
}

struct PlayerHeaderGlassPanelBackground: View {
    let cornerRadius: CGFloat

    var body: some View {
        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
            .fill(.ultraThinMaterial)
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .fill(Color.white.opacity(0.07))
            )
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .stroke(Color.white.opacity(0.18), lineWidth: 1)
            )
            .shadow(color: Color.black.opacity(0.25), radius: 16, x: 0, y: 10)
    }
}

struct PlayerHeaderIdentityBannerBackground: View {
    let cornerRadius: CGFloat

    var body: some View {
        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
            .fill(.thinMaterial)
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [
                                Color.white.opacity(0.12),
                                Color.white.opacity(0.04)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
            )
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .stroke(Color.white.opacity(0.18), lineWidth: 1)
            )
    }
}

struct PlayerHeaderPillBackground: View {
    let isActive: Bool
    var isProminent: Bool = false

    var body: some View {
        Capsule(style: .continuous)
            .fill(.ultraThinMaterial)
            .overlay(
                Capsule(style: .continuous)
                    .fill(Color.white.opacity(fillOpacity))
            )
            .overlay(
                Capsule(style: .continuous)
                    .stroke(Color.white.opacity(strokeOpacity), lineWidth: 1)
            )
    }

    private var fillOpacity: Double {
        if isProminent { return isActive ? 0.20 : 0.13 }
        return isActive ? 0.16 : 0.09
    }

    private var strokeOpacity: Double {
        if isProminent { return isActive ? 0.36 : 0.24 }
        return isActive ? 0.32 : 0.18
    }
}
