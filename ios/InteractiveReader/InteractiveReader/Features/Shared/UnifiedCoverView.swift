import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - Cover Metrics

/// Unified metrics for cover display across all views
enum CoverMetrics {
    /// Standard row cover height for list views
    static func rowHeight(isTV: Bool) -> CGFloat {
        isTV ? 88 : 108
    }

    /// Width for book covers (2:3 portrait aspect ratio)
    static func bookWidth(isTV: Bool) -> CGFloat {
        rowHeight(isTV: isTV) * 2 / 3
    }

    /// Width for book covers given a specific height
    static func bookWidth(forHeight height: CGFloat) -> CGFloat {
        height * 2 / 3
    }

    /// Width for video thumbnails (16:9 landscape aspect ratio)
    static func videoWidth(isTV: Bool) -> CGFloat {
        rowHeight(isTV: isTV) * 16 / 9
    }

    /// Width for video thumbnails given a specific height
    static func videoWidth(forHeight height: CGFloat) -> CGFloat {
        height * 16 / 9
    }

    /// Width for square placeholders (generic jobs)
    static func squareWidth(isTV: Bool) -> CGFloat {
        rowHeight(isTV: isTV)
    }

    /// Corner radius for cover images
    static let cornerRadius: CGFloat = 8

    /// Border width
    static let borderWidth: CGFloat = 1

    /// Shadow radius for depth
    static let shadowRadius: CGFloat = 4

    /// Shadow offset
    static let shadowOffset: CGFloat = 2

    /// Placeholder icon size relative to cover height
    static func iconSize(height: CGFloat) -> CGFloat {
        height * 0.28
    }
}

// MARK: - Cover Aspect Ratio

/// Defines the aspect ratio type for cover images
enum CoverAspectRatio {
    case book      // 2:3 portrait (standard book covers)
    case video     // 16:9 landscape (video thumbnails)
    case square    // 1:1 (generic/NAS jobs)

    var multiplier: CGFloat {
        switch self {
        case .book: return 2.0 / 3.0
        case .video:
            // Reduce video cover width by 50% on iPhone to prevent oversized thumbnails
            #if os(iOS)
            return (16.0 / 9.0) * 0.5
            #else
            return 16.0 / 9.0
            #endif
        case .square: return 1.0
        }
    }

    func width(forHeight height: CGFloat) -> CGFloat {
        height * multiplier
    }

    /// Determines aspect ratio from PlayerChannelVariant
    static func from(variant: PlayerChannelVariant) -> CoverAspectRatio {
        switch variant {
        case .book:
            return .book
        case .video, .youtube, .tv, .dub, .subtitles:
            return .video
        case .nas, .job:
            return .square
        }
    }
}

// MARK: - Cover Style

/// Visual styling for cover display
struct CoverStyle {
    let backgroundColor: Color
    let borderColor: Color
    let iconName: String
    let iconColor: Color
    let gradient: LinearGradient?

    /// Default style for unknown content
    static let `default` = CoverStyle(
        backgroundColor: Color.gray.opacity(0.15),
        borderColor: Color.secondary.opacity(0.25),
        iconName: "doc.richtext",
        iconColor: Color.secondary,
        gradient: nil
    )

    /// Create style from PlayerChannelVariant
    static func from(variant: PlayerChannelVariant) -> CoverStyle {
        let (iconName, iconColor, gradientColors) = variantAttributes(variant)
        return CoverStyle(
            backgroundColor: iconColor.opacity(0.12),
            borderColor: iconColor.opacity(0.35),
            iconName: iconName,
            iconColor: iconColor,
            gradient: LinearGradient(
                colors: gradientColors,
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
    }

    private static func variantAttributes(_ variant: PlayerChannelVariant) -> (String, Color, [Color]) {
        switch variant {
        case .book:
            return (
                "book.closed",
                Color(red: 0.96, green: 0.62, blue: 0.04),
                [Color(red: 0.96, green: 0.62, blue: 0.04), Color(red: 0.98, green: 0.45, blue: 0.09)]
            )
        case .subtitles:
            return (
                "captions.bubble",
                Color(red: 0.34, green: 0.55, blue: 0.92),
                [Color(red: 0.39, green: 0.40, blue: 0.95), Color(red: 0.22, green: 0.74, blue: 0.97)]
            )
        case .video:
            return (
                "play.rectangle",
                Color(red: 0.16, green: 0.77, blue: 0.45),
                [Color(red: 0.13, green: 0.77, blue: 0.37), Color(red: 0.08, green: 0.72, blue: 0.65)]
            )
        case .youtube:
            return (
                "play.rectangle.fill",
                Color(red: 1.0, green: 0.0, blue: 0.0),
                [Color(red: 0.06, green: 0.09, blue: 0.16), Color(red: 0.01, green: 0.02, blue: 0.09)]
            )
        case .tv:
            return (
                "tv",
                Color(red: 0.06, green: 0.45, blue: 0.56),
                [Color(red: 0.06, green: 0.45, blue: 0.56), Color(red: 0.02, green: 0.62, blue: 0.78)]
            )
        case .nas:
            return (
                "tray.2",
                Color(red: 0.5, green: 0.55, blue: 0.63),
                [Color(red: 0.39, green: 0.46, blue: 0.55), Color(red: 0.20, green: 0.25, blue: 0.33)]
            )
        case .dub:
            return (
                "waveform",
                Color(red: 0.82, green: 0.4, blue: 0.92),
                [Color(red: 0.96, green: 0.25, blue: 0.37), Color(red: 0.66, green: 0.33, blue: 0.97)]
            )
        case .job:
            return (
                "briefcase",
                Color(red: 0.6, green: 0.65, blue: 0.7),
                [Color(red: 0.58, green: 0.64, blue: 0.72), Color(red: 0.28, green: 0.33, blue: 0.41)]
            )
        }
    }
}

// MARK: - Unified Cover View

/// A unified cover view component that provides consistent styling across all list views
struct UnifiedCoverView: View {
    let url: URL?
    let aspectRatio: CoverAspectRatio
    let style: CoverStyle
    let height: CGFloat
    let showShadow: Bool

    init(
        url: URL?,
        aspectRatio: CoverAspectRatio = .book,
        style: CoverStyle = .default,
        height: CGFloat? = nil,
        showShadow: Bool = true
    ) {
        self.url = url
        self.aspectRatio = aspectRatio
        self.style = style
        self.height = height ?? CoverMetrics.rowHeight(isTV: Self.isTV)
        self.showShadow = showShadow
    }

    /// Convenience initializer using PlayerChannelVariant
    init(
        url: URL?,
        variant: PlayerChannelVariant,
        height: CGFloat? = nil,
        showShadow: Bool = true
    ) {
        self.url = url
        self.aspectRatio = CoverAspectRatio.from(variant: variant)
        self.style = CoverStyle.from(variant: variant)
        self.height = height ?? CoverMetrics.rowHeight(isTV: Self.isTV)
        self.showShadow = showShadow
    }

    private var width: CGFloat {
        aspectRatio.width(forHeight: height)
    }

    var body: some View {
        Group {
            if let url {
                coverImage(url: url)
            } else {
                placeholderView
            }
        }
        .frame(width: width, height: height)
        .clipShape(RoundedRectangle(cornerRadius: CoverMetrics.cornerRadius))
        .overlay(borderOverlay)
        .shadow(
            color: showShadow ? Color.black.opacity(0.15) : .clear,
            radius: showShadow ? CoverMetrics.shadowRadius : 0,
            x: 0,
            y: showShadow ? CoverMetrics.shadowOffset : 0
        )
    }

    @ViewBuilder
    private func coverImage(url: URL) -> some View {
        AsyncImage(url: url) { phase in
            switch phase {
            case .success(let image):
                image
                    .resizable()
                    .scaledToFill()
            case .failure:
                placeholderView
            case .empty:
                loadingView
            @unknown default:
                loadingView
            }
        }
    }

    private var placeholderView: some View {
        ZStack {
            if let gradient = style.gradient {
                gradient
            } else {
                style.backgroundColor
            }

            Image(systemName: style.iconName)
                .font(.system(size: CoverMetrics.iconSize(height: height), weight: .semibold))
                .foregroundStyle(style.gradient != nil ? Color.white : style.iconColor)
        }
    }

    private var loadingView: some View {
        ZStack {
            style.backgroundColor
            ProgressView()
                .tint(style.iconColor)
        }
    }

    private var borderOverlay: some View {
        RoundedRectangle(cornerRadius: CoverMetrics.cornerRadius)
            .stroke(style.borderColor, lineWidth: CoverMetrics.borderWidth)
    }

    private static var isTV: Bool {
        #if os(tvOS)
        return true
        #else
        return false
        #endif
    }
}

// MARK: - Preview

#if DEBUG
struct UnifiedCoverView_Previews: PreviewProvider {
    static var previews: some View {
        VStack(spacing: 20) {
            // Book cover
            HStack {
                UnifiedCoverView(url: nil, variant: .book)
                Text("Book")
            }

            // Video thumbnail
            HStack {
                UnifiedCoverView(url: nil, variant: .video)
                Text("Video")
            }

            // YouTube
            HStack {
                UnifiedCoverView(url: nil, variant: .youtube)
                Text("YouTube")
            }

            // TV
            HStack {
                UnifiedCoverView(url: nil, variant: .tv)
                Text("TV")
            }

            // NAS
            HStack {
                UnifiedCoverView(url: nil, variant: .nas)
                Text("NAS")
            }

            // Dub
            HStack {
                UnifiedCoverView(url: nil, variant: .dub)
                Text("Dub")
            }
        }
        .padding()
    }
}
#endif
