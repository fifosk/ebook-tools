import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - Styling

extension LinguistBubbleView {

    var queryFont: Font {
        #if os(tvOS)
        if configuration.autoScaleFontToFit {
            return scaledFont(textStyle: .title3, weight: .semibold, autoScale: autoScaleFontScale)
        }
        #endif
        return scaledFont(textStyle: .title3, weight: .semibold)
    }

    var bodyFont: Font {
        #if os(tvOS)
        if configuration.autoScaleFontToFit {
            return scaledFont(textStyle: .callout, weight: .regular, autoScale: autoScaleFontScale)
        }
        #endif
        return scaledFont(textStyle: .callout, weight: .regular)
    }

    var bubbleControlFont: Font {
        scaledUiFont(textStyle: .caption1, weight: .semibold)
    }

    var bubbleModelFont: Font {
        // Use larger font on iPad for better readability
        let textStyle: UIFont.TextStyle = configuration.uiScale > 1.2 ? .callout : .caption2
        return scaledUiFont(textStyle: textStyle, weight: .regular)
    }

    var bubbleMenuFont: Font {
        scaledUiFont(textStyle: .callout, weight: .regular)
    }

    var bubbleIconFont: Font {
        scaledUiFont(textStyle: .caption1, weight: .semibold)
    }

    var bubbleControlPadding: CGFloat {
        6 * configuration.uiScale
    }

    // MARK: - Selector Button Styling (LLM & Voice pickers - 20% smaller on iPad)

    /// Scale factor for selector buttons (80% on iPad, 100% elsewhere)
    var selectorScale: CGFloat {
        configuration.uiScale > 1.2 ? 0.8 : 1.0
    }

    var bubbleSelectorIconFont: Font {
        #if os(iOS)
        let baseSize = UIFont.preferredFont(forTextStyle: .caption2).pointSize
        return .system(size: baseSize * configuration.uiScale * selectorScale, weight: .semibold)
        #else
        return bubbleIconFont
        #endif
    }

    var bubbleSelectorTextFont: Font {
        #if os(iOS)
        let baseSize = UIFont.preferredFont(forTextStyle: .caption2).pointSize
        return .system(size: baseSize * configuration.uiScale * selectorScale, weight: .regular)
        #else
        return bubbleModelFont
        #endif
    }

    var bubbleSelectorPaddingH: CGFloat {
        5 * configuration.uiScale * selectorScale
    }

    var bubbleSelectorPaddingV: CGFloat {
        4 * configuration.uiScale * selectorScale
    }

    #if os(iOS)
    /// Check if a specific control is keyboard-focused
    func isControlKeyboardFocused(_ control: iOSBubbleKeyboardControl) -> Bool {
        keyboardNavigator.isKeyboardFocusActive && keyboardNavigator.focusedControl == control
    }

    /// Border color for keyboard focus highlight
    var keyboardFocusBorderColor: Color {
        Color.cyan.opacity(0.9)
    }

    /// Border width for keyboard focus highlight
    var keyboardFocusBorderWidth: CGFloat {
        2 * selectorScale
    }
    #endif

    func scaledFont(textStyle: UIFont.TextStyle, weight: Font.Weight, autoScale: CGFloat = 1.0) -> Font {
        #if os(iOS) || os(tvOS)
        let baseSize = UIFont.preferredFont(forTextStyle: textStyle).pointSize
        return .system(size: baseSize * configuration.fontScale * autoScale, weight: weight)
        #else
        return .system(size: 16 * configuration.fontScale * autoScale, weight: weight)
        #endif
    }

    func scaledUiFont(textStyle: UIFont.TextStyle, weight: Font.Weight) -> Font {
        #if os(iOS) || os(tvOS)
        let baseSize = UIFont.preferredFont(forTextStyle: textStyle).pointSize
        return .system(size: baseSize * configuration.uiScale, weight: weight)
        #else
        return .system(size: 16 * configuration.uiScale, weight: weight)
        #endif
    }

    var bubbleBackground: Color {
        Color.black.opacity(0.75)
    }

    /// Text color for bubble content - always white since background is dark
    var bubbleTextColor: Color {
        .white
    }

    var bubbleCornerRadius: CGFloat {
        if configuration.edgeToEdgeStyle {
            return 0
        }
        #if os(tvOS)
        return 18
        #else
        return 14
        #endif
    }

    var bubbleMaxHeight: CGFloat {
        // Account for header row (~50pt on tvOS) + padding (24pt total) + spacing (10pt)
        // when calculating available height for the scroll content
        let headerAndPaddingHeight: CGFloat = {
            #if os(tvOS)
            return 100 // header row height (~60) + padding (12*2) + spacing (10) + margin
            #else
            return 60 // smaller on iOS
            #endif
        }()

        #if os(tvOS)
        // On tvOS, use availableHeight from configuration if provided
        if let availableHeight = configuration.availableHeight {
            return max(availableHeight - headerAndPaddingHeight, 100)
        }
        return UIScreen.main.bounds.height * 0.7 // Allow larger bubbles on tvOS
        #else
        if let maxHeight = configuration.maxContentHeight {
            // Subtract header/padding space from total to get scroll content height
            return max(maxHeight - headerAndPaddingHeight, 80)
        }
        // iPad: allow taller bubbles for definitions (up to 40% screen height)
        // iPhone: keep compact since bubble is shown as fullscreen overlay
        if UIDevice.current.userInterfaceIdiom == .pad {
            return UIScreen.main.bounds.height * 0.4
        }
        return 180
        #endif
    }

    var bubbleWidth: CGFloat {
        #if os(iOS) || os(tvOS)
        #if os(tvOS)
        return UIScreen.main.bounds.width * 0.95
        #else
        return UIScreen.main.bounds.width * configuration.widthMultiplier
        #endif
        #else
        return 420
        #endif
    }
}
