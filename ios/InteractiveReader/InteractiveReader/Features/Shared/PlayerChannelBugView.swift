import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

struct PlayerChannelBugView: View {
    let variant: PlayerChannelVariant
    let label: String?
    let sizeScale: CGFloat

    init(variant: PlayerChannelVariant, label: String?, sizeScale: CGFloat = 1.0) {
        self.variant = variant
        self.label = label
        self.sizeScale = sizeScale
    }

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
                if variant == .youtube {
                    youtubeLogo
                } else if variant == .tv {
                    tubeTvLogo
                } else {
                    Image(systemName: iconName)
                        .font(.system(size: iconSize, weight: .semibold))
                        .foregroundStyle(Color.white)
                }
                RoundedRectangle(cornerRadius: cornerRadius)
                    .stroke(Color.white.opacity(0.28), lineWidth: 1)
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
        case .tv:
            return "tv"
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
        case .tv:
            colors = [Color(red: 0.06, green: 0.45, blue: 0.56), Color(red: 0.02, green: 0.62, blue: 0.78)]
        case .youtube:
            colors = [Color(red: 0.06, green: 0.09, blue: 0.16), Color(red: 0.01, green: 0.02, blue: 0.09)]
        case .nas:
            colors = [Color(red: 0.39, green: 0.46, blue: 0.55), Color(red: 0.20, green: 0.25, blue: 0.33)]
        case .dub:
            colors = [Color(red: 0.96, green: 0.25, blue: 0.37), Color(red: 0.66, green: 0.33, blue: 0.97)]
        case .job:
            colors = [Color(red: 0.58, green: 0.64, blue: 0.72), Color(red: 0.28, green: 0.33, blue: 0.41)]
        }
        return LinearGradient(colors: colors, startPoint: .topLeading, endPoint: .bottomTrailing)
    }

    private var youtubeLogo: some View {
        let markWidth = logoSize * 0.8
        let markHeight = logoSize * 0.52
        return YoutubeGlyphMark(width: markWidth, height: markHeight)
    }

    private var tubeTvLogo: some View {
        let markWidth = logoSize * 0.74
        let markHeight = logoSize * 0.62
        return TubeTVGlyphMark(width: markWidth, height: markHeight, color: .white)
    }

    private var logoSize: CGFloat {
        PlayerInfoMetrics.logoSize(isTV: isTV) * sizeScale
    }

    private var iconSize: CGFloat {
        PlayerInfoMetrics.iconSize(isTV: isTV) * sizeScale
    }

    private var cornerRadius: CGFloat {
        PlayerInfoMetrics.cornerRadius(isTV: isTV) * sizeScale
    }

    private var clockFont: Font {
        #if os(iOS) || os(tvOS)
        let style: UIFont.TextStyle = isTV ? .callout : .caption2
        let baseSize = UIFont.preferredFont(forTextStyle: style).pointSize
        return .system(size: baseSize * sizeScale, weight: .bold)
        #else
        let baseSize: CGFloat = isTV ? 16 : 11
        return .system(size: baseSize * sizeScale, weight: .bold)
        #endif
    }

    private var clockHorizontalPadding: CGFloat {
        PlayerInfoMetrics.clockHorizontalPadding(isTV: isTV) * sizeScale
    }

    private var clockVerticalPadding: CGFloat {
        PlayerInfoMetrics.clockVerticalPadding(isTV: isTV) * sizeScale
    }

    private var clockSpacing: CGFloat {
        PlayerInfoMetrics.clockSpacing(isTV: isTV) * sizeScale
    }

    private var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }
}
