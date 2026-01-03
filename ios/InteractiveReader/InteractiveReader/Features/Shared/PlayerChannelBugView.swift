import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

enum PlayerChannelVariant {
    case book
    case subtitles
    case video
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
        coverHeight(isTV: isTV) * 0.68
    }
}

struct PlayerChannelBugView: View {
    let variant: PlayerChannelVariant
    let label: String?

    private static let hourFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH"
        return formatter
    }()

    private static let minuteFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "mm"
        return formatter
    }()

    var body: some View {
        VStack(spacing: clockSpacing) {
            ZStack {
                RoundedRectangle(cornerRadius: cornerRadius)
                    .fill(gradient)
                RoundedRectangle(cornerRadius: cornerRadius)
                    .stroke(Color.white.opacity(0.28), lineWidth: 1)
                Image(systemName: iconName)
                    .font(.system(size: iconSize, weight: .semibold))
                    .foregroundStyle(Color.white)
            }
            .frame(width: logoSize, height: logoSize)
            .shadow(color: Color.black.opacity(0.35), radius: 8, x: 0, y: 6)

            TimelineView(.periodic(from: .now, by: 1)) { context in
                let hour = Self.hourFormatter.string(from: context.date)
                let minute = Self.minuteFormatter.string(from: context.date)
                let seconds = Calendar.current.component(.second, from: context.date)
                let blink = seconds % 2 == 0
                HStack(spacing: 0) {
                    Text(hour)
                    Text(":")
                        .opacity(blink ? 1 : 0)
                    Text(minute)
                }
                .font(clockFont)
                .monospacedDigit()
                .foregroundStyle(Color.white)
                .padding(.horizontal, clockHorizontalPadding)
                .padding(.vertical, clockVerticalPadding)
                .background(
                    Capsule()
                        .fill(Color.black.opacity(0.85))
                        .overlay(Capsule().stroke(Color.white.opacity(0.2), lineWidth: 1))
                )
            }
        }
        .accessibilityLabel(label ?? "Job")
        .accessibilityHidden(true)
    }

    private var iconName: String {
        switch variant {
        case .book:
            return "book.closed"
        case .subtitles:
            return "captions.bubble"
        case .video, .youtube:
            return "play.rectangle"
        case .nas:
            return "tray.2"
        case .dub:
            return "waveform"
        case .job:
            return "briefcase"
        }
    }

    private var gradient: LinearGradient {
        let colors: [Color]
        switch variant {
        case .book:
            colors = [Color(red: 0.96, green: 0.62, blue: 0.04), Color(red: 0.98, green: 0.45, blue: 0.09)]
        case .subtitles:
            colors = [Color(red: 0.39, green: 0.40, blue: 0.95), Color(red: 0.22, green: 0.74, blue: 0.97)]
        case .video:
            colors = [Color(red: 0.13, green: 0.77, blue: 0.37), Color(red: 0.08, green: 0.72, blue: 0.65)]
        case .youtube:
            colors = [Color(red: 0.94, green: 0.27, blue: 0.27), Color(red: 0.86, green: 0.15, blue: 0.15)]
        case .nas:
            colors = [Color(red: 0.39, green: 0.46, blue: 0.55), Color(red: 0.20, green: 0.25, blue: 0.33)]
        case .dub:
            colors = [Color(red: 0.96, green: 0.25, blue: 0.37), Color(red: 0.66, green: 0.33, blue: 0.97)]
        case .job:
            colors = [Color(red: 0.58, green: 0.64, blue: 0.72), Color(red: 0.28, green: 0.33, blue: 0.41)]
        }
        return LinearGradient(colors: colors, startPoint: .topLeading, endPoint: .bottomTrailing)
    }

    private var logoSize: CGFloat {
        PlayerInfoMetrics.logoSize(isTV: isTV)
    }

    private var iconSize: CGFloat {
        PlayerInfoMetrics.iconSize(isTV: isTV)
    }

    private var cornerRadius: CGFloat {
        PlayerInfoMetrics.cornerRadius(isTV: isTV)
    }

    private var clockFont: Font {
        PlayerInfoMetrics.clockFont(isTV: isTV)
    }

    private var clockHorizontalPadding: CGFloat {
        PlayerInfoMetrics.clockHorizontalPadding(isTV: isTV)
    }

    private var clockVerticalPadding: CGFloat {
        PlayerInfoMetrics.clockVerticalPadding(isTV: isTV)
    }

    private var clockSpacing: CGFloat {
        PlayerInfoMetrics.clockSpacing(isTV: isTV)
    }

    private var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }
}
