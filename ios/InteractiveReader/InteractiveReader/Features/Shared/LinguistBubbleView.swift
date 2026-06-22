import SwiftUI
#if os(iOS) || os(tvOS)
import UIKit
#endif

// MARK: - Main View

struct LinguistBubbleView: View {
    let state: LinguistBubbleState
    let configuration: LinguistBubbleConfiguration
    let actions: LinguistBubbleActions

    #if os(tvOS)
    /// Whether focus is enabled for this bubble
    var isFocusEnabled: Bool = true
    #endif

    #if os(iOS)
    @State private var magnifyStartScale: CGFloat?
    @State private var measuredBubbleWidth: CGFloat = 0
    /// Optional keyboard navigator for iPad focus management
    @ObservedObject var keyboardNavigator: iOSBubbleKeyboardNavigator = iOSBubbleKeyboardNavigator()
    /// Active picker for keyboard-triggered selection (iOS)
    @State var iOSActivePicker: iOSBubblePicker?

    enum iOSBubblePicker: Hashable {
        case language
        case model
        case voice
    }

    var isPhone: Bool {
        UIDevice.current.userInterfaceIdiom == .phone
    }

    /// When the bubble is narrow (e.g. horizontal split with reduced width),
    /// collapse model and voice pills to icon-only.
    var useCompactPills: Bool {
        // Threshold: below 300pt, show icons only
        measuredBubbleWidth > 0 && measuredBubbleWidth < 300
    }
    #endif

    #if os(tvOS)
    @FocusState var focusedControl: BubbleHeaderControl?
    @State var activePicker: BubblePicker?
    @State var autoScaleFontScale: CGFloat = 1.0
    @State private var measuredContentHeight: CGFloat = 0
    @State private var lastContentLength: Int = 0

    enum BubbleHeaderControl: Hashable {
        case language
        case model
        case voice
        case playFromNarration
        case decreaseFont
        case increaseFont
        case pin
        case layout
        case close
    }

    enum BubblePicker: Hashable {
        case language
        case model
        case voice
    }
    #endif

    var body: some View {
        ZStack {
            bubbleBody
            #if os(tvOS)
            if activePicker != nil {
                pickerOverlay
            }
            #elseif os(iOS)
            if iOSActivePicker != nil {
                iOSPickerOverlay
            }
            #endif
        }
        #if os(tvOS)
        // In split mode, fill available space to maintain constant size during loading
        .frame(maxWidth: configuration.isSplitMode ? .infinity : nil,
               maxHeight: configuration.isSplitMode ? .infinity : nil,
               alignment: .top)
        #endif
        #if os(iOS)
        .onChange(of: keyboardNavigator.activationTrigger) { _, _ in
            // When Enter is pressed on a picker control, open the corresponding picker
            guard let control = keyboardNavigator.focusedControl else { return }
            switch control {
            case .language:
                iOSActivePicker = .language
            case .voice:
                iOSActivePicker = .voice
            case .model:
                iOSActivePicker = .model
            case .close:
                // Close is handled directly in handleBubbleKeyboardActivate
                break
            }
        }
        #endif
    }

    // MARK: - Bubble Body

    private var bubbleBody: some View {
        VStack(alignment: .leading, spacing: 10) {
            headerRow

            bubbleContent
                #if os(tvOS)
                // Smooth content transitions for loading states
                .animation(.easeInOut(duration: 0.2), value: state.status.isLoading)
                #endif
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        #if os(iOS)
        .background(
            GeometryReader { widthProxy in
                Color.clear.onChange(of: widthProxy.size.width) { _, newWidth in
                    measuredBubbleWidth = newWidth
                }
                .onAppear { measuredBubbleWidth = widthProxy.size.width }
            }
        )
        #endif
        #if os(tvOS)
        // In split mode, fill available height to prevent size changes during loading
        .frame(maxHeight: configuration.isSplitMode ? .infinity : nil, alignment: .top)
        .background(
            GeometryReader { contentProxy in
                Color.clear.preference(
                    key: LinguistBubbleContentHeightKey.self,
                    value: contentProxy.size.height
                )
            }
        )
        #endif
        .background(bubbleBackground)
        .overlay(
            RoundedRectangle(cornerRadius: bubbleCornerRadius)
                .stroke(Color.white.opacity(0.12), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: bubbleCornerRadius))
        .frame(maxWidth: bubbleWidth, alignment: .leading)
        .frame(maxWidth: .infinity, alignment: .center)
        #if os(tvOS)
        .focusEffectDisabled()
        .focusSection()
        .onAppear {
            if isFocusEnabled && focusedControl == nil {
                focusedControl = .language
            }
            // Initialize auto-scale if content length is available
            if configuration.autoScaleFontToFit {
                lastContentLength = (state.answer ?? "").count
            }
        }
        .onChange(of: isFocusEnabled) { _, enabled in
            if enabled {
                if focusedControl == nil {
                    focusedControl = .language
                }
            } else if focusedControl != nil {
                focusedControl = nil
            }
        }
        .onChange(of: activePicker) { _, newValue in
            if newValue == nil && isFocusEnabled && focusedControl == nil {
                focusedControl = .language
            }
        }
        .onChange(of: focusedControl) { _, newValue in
            if newValue != nil {
                actions.onBubbleFocus?()
            }
        }
        .onPreferenceChange(LinguistBubbleContentHeightKey.self) { height in
            guard configuration.autoScaleFontToFit else { return }
            measuredContentHeight = height
            recalculateAutoScale()
        }
        .onChange(of: state.answer) { _, newAnswer in
            guard configuration.autoScaleFontToFit else { return }
            let newLength = (newAnswer ?? "").count
            // Only recalculate if content length changed significantly
            if abs(newLength - lastContentLength) > 10 {
                lastContentLength = newLength
                // Reset scale to base and let measurement trigger recalculation
                autoScaleFontScale = 1.0
            }
        }
        .onChange(of: configuration.availableHeight) { _, _ in
            guard configuration.autoScaleFontToFit else { return }
            recalculateAutoScale()
        }
        #endif
        #if os(iOS)
        .applyMagnifyGesture(
            enabled: actions.onMagnify != nil,
            fontScale: configuration.fontScale,
            magnifyStartScale: $magnifyStartScale,
            onMagnify: actions.onMagnify
        )
        .gesture(
            DragGesture(minimumDistance: 30, coordinateSpace: .local)
                .onEnded { value in
                    let horizontalAmount = value.translation.width
                    let verticalAmount = value.translation.height
                    // Only handle horizontal swipes (ignore vertical)
                    guard abs(horizontalAmount) > abs(verticalAmount) else { return }
                    if horizontalAmount < 0 {
                        // Swipe left -> next token
                        actions.onNextToken?()
                    } else {
                        // Swipe right -> previous token
                        actions.onPreviousToken?()
                    }
                }
        )
        #endif
    }

    #if os(tvOS)
    /// Recalculate auto-scale factor to fill available height
    private func recalculateAutoScale() {
        guard configuration.autoScaleFontToFit,
              let availableHeight = configuration.availableHeight,
              measuredContentHeight > 0 else { return }

        // Calculate the ratio needed to fill available space
        // Add some padding tolerance (20px) to prevent overflow
        let targetHeight = availableHeight - 20
        let currentHeight = measuredContentHeight

        // Calculate new scale factor
        let ratio = targetHeight / currentHeight
        let newScale = autoScaleFontScale * ratio

        // Clamp to configured bounds
        let clampedScale = max(
            configuration.minAutoScaleFontScale,
            min(configuration.maxAutoScaleFontScale, newScale)
        )

        // Only update if change is significant (> 2%)
        if abs(clampedScale - autoScaleFontScale) > 0.02 {
            autoScaleFontScale = clampedScale
        }
    }

    #endif

}

// MARK: - iOS Magnify Gesture Extension

#if os(iOS)
private extension View {
    @ViewBuilder
    func applyMagnifyGesture(
        enabled: Bool,
        fontScale: CGFloat,
        magnifyStartScale: Binding<CGFloat?>,
        onMagnify: ((CGFloat) -> Void)?
    ) -> some View {
        if enabled, let onMagnify {
            self.simultaneousGesture(
                MagnificationGesture()
                    .onChanged { value in
                        if magnifyStartScale.wrappedValue == nil {
                            magnifyStartScale.wrappedValue = fontScale
                        }
                        let startScale = magnifyStartScale.wrappedValue ?? fontScale
                        onMagnify(startScale * value)
                    }
                    .onEnded { _ in
                        magnifyStartScale.wrappedValue = nil
                    },
                including: .gesture
            )
        } else {
            self
        }
    }
}
#endif
