import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

/// Wrapper for Interactive Player that maintains the original API with FocusState binding.
/// Delegates to the shared LinguistBubbleView implementation.
struct MyLinguistBubbleView: View {
    let bubble: MyLinguistBubbleState
    let fontScale: CGFloat
    let canIncreaseFont: Bool
    let canDecreaseFont: Bool
    let lookupLanguage: String
    let lookupLanguageOptions: [String]
    let onLookupLanguageChange: (String) -> Void
    let llmModel: String
    let llmModelOptions: [String]
    let onLlmModelChange: (String) -> Void
    let onIncreaseFont: () -> Void
    let onDecreaseFont: () -> Void
    let onClose: () -> Void
    let isFocusEnabled: Bool
    let focusBinding: FocusState<InteractivePlayerFocusArea?>.Binding
    var useCompactLayout: Bool = false
    var fillWidth: Bool = false
    var hideTitle: Bool = false
    var edgeToEdgeStyle: Bool = false
    var maxContentHeight: CGFloat? = nil
    /// (tvOS) Available height for auto-scaling font to fill space
    var availableHeight: CGFloat? = nil

    private var isPad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    private var bubbleUiScale: CGFloat {
        #if os(iOS)
        return isPad ? 2.0 : 1.0
        #else
        return 1.0
        #endif
    }

    private var bubbleConfiguration: LinguistBubbleConfiguration {
        var config = LinguistBubbleConfiguration(
            fontScale: fontScale,
            canIncreaseFont: canIncreaseFont,
            canDecreaseFont: canDecreaseFont,
            lookupLanguage: lookupLanguage,
            lookupLanguageOptions: lookupLanguageOptions,
            llmModel: llmModel,
            llmModelOptions: llmModelOptions,
            uiScale: bubbleUiScale,
            useCompactLayout: isPad || useCompactLayout
        )
        if fillWidth {
            config.widthMultiplier = 1.0
        }
        config.hideTitle = hideTitle
        config.edgeToEdgeStyle = edgeToEdgeStyle
        config.maxContentHeight = maxContentHeight
        #if os(tvOS)
        // Enable auto-scaling on tvOS when available height is provided
        if let availableHeight {
            config.autoScaleFontToFit = true
            config.availableHeight = availableHeight
        }
        #endif
        return config
    }

    private var bubbleActions: LinguistBubbleActions {
        LinguistBubbleActions(
            onLookupLanguageChange: onLookupLanguageChange,
            onLlmModelChange: onLlmModelChange,
            onIncreaseFont: onIncreaseFont,
            onDecreaseFont: onDecreaseFont,
            onClose: onClose,
            onBubbleFocus: {
                #if os(tvOS)
                if focusBinding.wrappedValue != .bubble {
                    focusBinding.wrappedValue = .bubble
                }
                #endif
            }
        )
    }

    var body: some View {
        #if os(tvOS)
        LinguistBubbleView(
            state: bubble.asLinguistBubbleState,
            configuration: bubbleConfiguration,
            actions: bubbleActions,
            isFocusEnabled: isFocusEnabled
        )
        #else
        LinguistBubbleView(
            state: bubble.asLinguistBubbleState,
            configuration: bubbleConfiguration,
            actions: bubbleActions
        )
        #endif
    }
}
