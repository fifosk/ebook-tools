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
